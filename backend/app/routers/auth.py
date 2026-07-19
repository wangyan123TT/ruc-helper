"""
认证路由 —— 学号+密码登录，只能是已开通的三个学生之一。

登录用教务真登录验证密码（顺手把库里存的加密密码/令牌刷新成最新），
成功才签发会话令牌。
"""
import os

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session as DbSession

from ..database import get_db
from ..models import Session as SessionModel, Student
from ..services.auth import do_login, encrypt_password
from ..services.ratelimit import throttle, is_locked, record_fail, record_success
from ..services.session import (create_session, destroy_session, get_current_session,
                                ADMIN_SID, SESSION_HOURS)

router = APIRouter(prefix="/api/auth", tags=["auth"])

# 管理员账号（可改：改 .env 的 ADMIN_USERNAME / ADMIN_PASSWORD）
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "")

# 登录限流：每 IP 5 分钟内最多 30 次；单账号连续失败 5 次锁 15 分钟
_IP_MAX, _IP_WINDOW = 30, 300
_FAIL_MAX, _LOCK_SEC = 5, 900


def _client_ip(request: Request) -> str:
    """真实客户端 IP：优先 nginx 传的 X-Real-IP / X-Forwarded-For。"""
    xff = request.headers.get("x-forwarded-for", "")
    return (request.headers.get("x-real-ip")
            or (xff.split(",")[0].strip() if xff else "")
            or (request.client.host if request.client else "?"))


class LoginBody(BaseModel):
    student_id: str
    password: str


@router.post("/login")
def login(body: LoginBody, request: Request, db: DbSession = Depends(get_db)):
    import secrets
    # ① 按 IP 滑动窗口限流（挡广撒网爆破）
    wait = throttle(f"login:ip:{_client_ip(request)}", _IP_MAX, _IP_WINDOW)
    if wait:
        raise HTTPException(429, f"登录尝试过于频繁，请约 {wait} 秒后再试")

    uid = (body.student_id or "").strip()
    pwd = body.password or ""
    if not uid or not pwd:
        raise HTTPException(400, "请输入账号和密码")

    # ② 按账号失败锁定（挡定点爆破，尤其管理员）
    acct = f"login:acct:{uid.lower()}"
    locked = is_locked(acct)
    if locked:
        raise HTTPException(429, f"该账号失败次数过多，已临时锁定，请约 {locked // 60 + 1} 分钟后再试")

    # ── 管理员登录 ──
    if uid == ADMIN_USERNAME:
        if not ADMIN_PASSWORD or not secrets.compare_digest(pwd, ADMIN_PASSWORD):
            record_fail(acct, _FAIL_MAX, _LOCK_SEC)
            raise HTTPException(401, "管理员密码错误")
        record_success(acct)
        token = create_session(db, ADMIN_SID, is_admin=True)
        return {"token": token, "student_id": ADMIN_SID, "name": "管理员",
                "is_admin": True, "expires_hours": SESSION_HOURS}

    # ── 学生登录 ── 只放行已开通(库里已添加)的学生
    student = db.query(Student).filter(Student.student_id == uid).first()
    if not student:
        record_fail(acct, _FAIL_MAX, _LOCK_SEC)
        raise HTTPException(403, "该学号未开通，请联系管理员添加")

    # 用教务真登录验证密码（最可靠；顺便刷新令牌/学生信息）
    result = do_login(uid, pwd)
    if not result:
        record_fail(acct, _FAIL_MAX, _LOCK_SEC)
        raise HTTPException(401, "学号或密码错误")

    record_success(acct)

    student.password = encrypt_password(pwd)
    student.res_token = result["resToken"]
    student.session = result["session"]
    student.authcode = result["authcode"]
    student.token_expires_at = result["token_expires_at"]
    student.name = result.get("name") or student.name
    student.major = result.get("major") or student.major
    student.grade = result.get("grade") or student.grade
    db.commit()

    token = create_session(db, uid, is_admin=False)
    return {"token": token, "student_id": uid, "name": student.name or uid,
            "is_admin": False, "expires_hours": SESSION_HOURS}


@router.post("/logout")
def logout(x_session_token: str = Header(default=""), db: DbSession = Depends(get_db)):
    if x_session_token:
        destroy_session(db, x_session_token)
    return {"ok": True}


@router.get("/me")
def me(sess: SessionModel = Depends(get_current_session), db: DbSession = Depends(get_db)):
    if sess.is_admin:
        return {"student_id": ADMIN_SID, "name": "管理员", "is_admin": True,
                "major": "", "grade": ""}
    s = db.query(Student).filter(Student.student_id == sess.student_id).first()
    if not s:
        raise HTTPException(401, "账号不存在")
    return {"student_id": s.student_id, "name": s.name or s.student_id,
            "is_admin": False, "major": s.major, "grade": s.grade}
