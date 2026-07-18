"""
认证路由 —— 学号+密码登录，只能是已开通的三个学生之一。

登录用教务真登录验证密码（顺手把库里存的加密密码/令牌刷新成最新），
成功才签发会话令牌。
"""
from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session as DbSession

from ..database import get_db
from ..models import Student
from ..services.auth import do_login, encrypt_password
from ..services.session import (create_session, destroy_session, require_session,
                                SESSION_HOURS)

router = APIRouter(prefix="/api/auth", tags=["auth"])


class LoginBody(BaseModel):
    student_id: str
    password: str


@router.post("/login")
def login(body: LoginBody, db: DbSession = Depends(get_db)):
    sid = (body.student_id or "").strip()
    pwd = body.password or ""
    if not sid or not pwd:
        raise HTTPException(400, "请输入学号和密码")

    # 只放行已开通(库里已添加)的学生
    student = db.query(Student).filter(Student.student_id == sid).first()
    if not student:
        raise HTTPException(403, "该学号未开通，请联系管理员添加")

    # 用教务真登录验证密码（最可靠；顺便刷新令牌/学生信息）
    result = do_login(sid, pwd)
    if not result:
        raise HTTPException(401, "学号或密码错误")

    # 密码正确 —— 更新库里存的加密密码(可能改过密码)与令牌/学生信息
    student.password = encrypt_password(pwd)
    student.res_token = result["resToken"]
    student.session = result["session"]
    student.authcode = result["authcode"]
    student.token_expires_at = result["token_expires_at"]
    student.name = result.get("name") or student.name
    student.major = result.get("major") or student.major
    student.grade = result.get("grade") or student.grade
    db.commit()

    token = create_session(db, sid)
    return {"token": token, "student_id": sid, "name": student.name or sid,
            "expires_hours": SESSION_HOURS}


@router.post("/logout")
def logout(x_session_token: str = Header(default=""), db: DbSession = Depends(get_db)):
    if x_session_token:
        destroy_session(db, x_session_token)
    return {"ok": True}


@router.get("/me")
def me(current: Student = Depends(require_session)):
    return {"student_id": current.student_id, "name": current.name or current.student_id,
            "major": current.major, "grade": current.grade}
