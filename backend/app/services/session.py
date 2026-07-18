"""
登录会话 —— 令牌生成/校验 + FastAPI 依赖。

访问控制的核心：
  · require_session  —— 任何接口都要带有效令牌（登录除外）
  · require_owner    —— 带 {student_id} 的接口，令牌必须属于该学号（只能看自己）
去掉了 nginx 那道共享密码墙后，这两个依赖是唯一的门，务必每个数据接口都挂上。
"""
import os
import secrets
from datetime import timedelta

from fastapi import Depends, Header, HTTPException, Path
from sqlalchemy.orm import Session as DbSession

from ..database import get_db
from ..models import Session as SessionModel, Student, now

SESSION_HOURS = 12


def create_session(db: DbSession, student_id: str) -> str:
    """签发新令牌，顺手清理该学号的旧令牌与过期令牌。"""
    db.query(SessionModel).filter(
        (SessionModel.student_id == student_id) | (SessionModel.expires_at < now())
    ).delete(synchronize_session=False)
    token = secrets.token_urlsafe(32)
    db.add(SessionModel(token=token, student_id=student_id,
                        expires_at=now() + timedelta(hours=SESSION_HOURS)))
    db.commit()
    return token


def destroy_session(db: DbSession, token: str):
    db.query(SessionModel).filter(SessionModel.token == token).delete()
    db.commit()


def require_session(
    x_session_token: str = Header(default=""),
    db: DbSession = Depends(get_db),
) -> Student:
    """校验令牌，返回登录学生。无效/过期 -> 401。"""
    if not x_session_token:
        raise HTTPException(401, "未登录")
    s = db.query(SessionModel).filter(SessionModel.token == x_session_token).first()
    if not s:
        raise HTTPException(401, "登录已失效，请重新登录")
    if s.expires_at < now():
        db.query(SessionModel).filter(SessionModel.token == x_session_token).delete()
        db.commit()
        raise HTTPException(401, "登录已过期，请重新登录")
    student = db.query(Student).filter(Student.student_id == s.student_id).first()
    if not student:
        raise HTTPException(401, "账号不存在")
    return student


def require_owner(
    student_id: str = Path(...),
    current: Student = Depends(require_session),
) -> Student:
    """带 {student_id} 的接口：令牌必须属于该学号，否则 403（越权访问别人）。"""
    if student_id != current.student_id:
        raise HTTPException(403, "无权访问其他学号的数据")
    return current


def require_admin(x_admin_token: str = Header(default="")):
    """管理接口（加学生/监控/SMTP/跨学生日志）：需 ADMIN_TOKEN。
    未配置 ADMIN_TOKEN 时一律拒绝（安全默认），界面已不再调用这些接口。"""
    expected = os.getenv("ADMIN_TOKEN", "")
    if not expected or not secrets.compare_digest(x_admin_token, expected):
        raise HTTPException(403, "需要管理员权限")
    return True
