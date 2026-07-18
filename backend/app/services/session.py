"""
登录会话 —— 令牌生成/校验 + FastAPI 依赖。

两种身份：
  · 学生会话  is_admin=False，只能看自己学号
  · 管理员会话 is_admin=True，可看所有人 + 管理监控/设置

访问控制依赖（去掉 nginx 共享密码墙后，这是唯一的门，每个数据接口都要挂）：
  · get_current_session —— 校验令牌，返回会话（学生或管理员）
  · require_owner       —— 带 {student_id} 的接口：学生只能访问自己；管理员放行任意
  · require_admin       —— 管理/跨学生接口：管理员会话 或 ADMIN_TOKEN 头
"""
import os
import secrets
from datetime import timedelta

from fastapi import Depends, Header, HTTPException, Path
from sqlalchemy.orm import Session as DbSession

from ..database import get_db
from ..models import Session as SessionModel, Student, now

SESSION_HOURS = 12
ADMIN_SID = "admin"   # 管理员会话的 student_id 占位


def create_session(db: DbSession, student_id: str, is_admin: bool = False) -> str:
    """签发新令牌，顺手清理该身份的旧令牌与过期令牌。"""
    db.query(SessionModel).filter(
        (SessionModel.student_id == student_id) | (SessionModel.expires_at < now())
    ).delete(synchronize_session=False)
    token = secrets.token_urlsafe(32)
    db.add(SessionModel(token=token, student_id=student_id, is_admin=is_admin,
                        expires_at=now() + timedelta(hours=SESSION_HOURS)))
    db.commit()
    return token


def destroy_session(db: DbSession, token: str):
    db.query(SessionModel).filter(SessionModel.token == token).delete()
    db.commit()


def get_current_session(
    x_session_token: str = Header(default=""),
    db: DbSession = Depends(get_db),
) -> SessionModel:
    """校验令牌，返回会话。无效/过期 -> 401。"""
    if not x_session_token:
        raise HTTPException(401, "未登录")
    s = db.query(SessionModel).filter(SessionModel.token == x_session_token).first()
    if not s:
        raise HTTPException(401, "登录已失效，请重新登录")
    if s.expires_at < now():
        db.query(SessionModel).filter(SessionModel.token == x_session_token).delete()
        db.commit()
        raise HTTPException(401, "登录已过期，请重新登录")
    return s


def require_session(sess: SessionModel = Depends(get_current_session)) -> SessionModel:
    return sess


def require_owner(
    student_id: str = Path(...),
    sess: SessionModel = Depends(get_current_session),
) -> SessionModel:
    """带 {student_id} 的接口：管理员放行任意；学生只能访问自己，否则 403。"""
    if sess.is_admin:
        return sess
    if student_id != sess.student_id:
        raise HTTPException(403, "无权访问其他学号的数据")
    return sess


def require_admin(
    x_admin_token: str = Header(default=""),
    x_session_token: str = Header(default=""),
    db: DbSession = Depends(get_db),
):
    """管理接口：管理员会话 或 ADMIN_TOKEN 头。"""
    # 1) 管理员会话
    if x_session_token:
        s = db.query(SessionModel).filter(SessionModel.token == x_session_token).first()
        if s and s.is_admin and s.expires_at >= now():
            return True
    # 2) ADMIN_TOKEN 头（供 CLI/脚本）
    expected = os.getenv("ADMIN_TOKEN", "")
    if expected and secrets.compare_digest(x_admin_token, expected):
        return True
    raise HTTPException(403, "需要管理员权限")
