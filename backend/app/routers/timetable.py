"""
课程表路由
  /api/timetable/{sid}            预选课程表 —— 待筛选志愿课程
  /api/timetable/{sid}/enrolled   已选课程表 —— 只含选课状态为「通过」的课

【只读】只调教务查询接口，不会改动任何人的选课状态。
凭据复用 students 表里已加密存储的密码，用户不需要再输一次。
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Student
from ..services.auth import decrypt_password, do_login
from ..services.xk import (ApiError, Jw, LoginError, build_payload, fetch,
                           fetch_enrolled)

router = APIRouter(prefix="/api/timetable", tags=["timetable"])


def _login_as(student_id: str, db: Session) -> Jw:
    """复用加密密码登录，顺手刷新 token/学生信息。返回 Jw。"""
    student = db.query(Student).filter(Student.student_id == student_id).first()
    if not student:
        raise HTTPException(404, "学生不存在")
    try:
        password = decrypt_password(student.password)
    except Exception:
        raise HTTPException(500, "密码解密失败，CIPHER_KEY 可能已变更，请重新添加该学生")
    result = do_login(student_id, password)
    del password
    if not result:
        raise HTTPException(502, "登录教务系统失败，请检查密码是否已修改")
    student.res_token = result["resToken"]
    student.session = result["session"]
    student.authcode = result["authcode"]
    student.token_expires_at = result["token_expires_at"]
    student.name = result.get("name") or student.name
    student.major = result.get("major") or student.major
    student.grade = result.get("grade") or student.grade
    db.commit()
    return Jw.from_token(result["resToken"], result["session"], result["authcode"])


@router.get("/{student_id}")
def get_timetable(student_id: str, db: Session = Depends(get_db)):
    """预选课程表：当前选课活动中「待筛选」的志愿课程"""
    jw = _login_as(student_id, db)
    try:
        ctx, courses, nopass = fetch(jw)
    except ApiError as e:
        raise HTTPException(409, str(e))
    except LoginError as e:
        raise HTTPException(502, str(e))
    payload = build_payload(ctx, courses)
    payload["nopass_count"] = len(nopass)
    payload["kind"] = "preselect"
    return payload


@router.get("/{student_id}/enrolled")
def get_enrolled(student_id: str, db: Session = Depends(get_db)):
    """已选课程表：只含选课状态为「通过」的课（志愿未筛选时通常为空）"""
    jw = _login_as(student_id, db)
    try:
        ctx, courses = fetch_enrolled(jw)
    except ApiError as e:
        raise HTTPException(409, str(e))
    except LoginError as e:
        raise HTTPException(502, str(e))
    payload = build_payload(ctx, courses)
    payload["nopass_count"] = 0
    payload["kind"] = "enrolled"
    return payload
