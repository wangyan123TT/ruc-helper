"""
预选课程表路由 — 待筛选志愿课程

【只读】只调教务查询接口，不会改动任何人的选课状态。

凭据复用 students 表里已加密存储的密码（与成绩监控同一套），
所以用户不需要再输一次密码。
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Student
from ..services.auth import decrypt_password, do_login
from ..services.xk import ApiError, Jw, LoginError, build_payload, fetch

router = APIRouter(prefix="/api/timetable", tags=["timetable"])


@router.get("/{student_id}")
def get_timetable(student_id: str, db: Session = Depends(get_db)):
    """抓取该学生当前选课活动中「待筛选」的志愿课程，返回课表数据"""
    student = db.query(Student).filter(Student.student_id == student_id).first()
    if not student:
        raise HTTPException(404, "学生不存在")

    # 与 monitor 一致：每次重新登录拿新 token，不赌 DB 里的会不会过期
    try:
        password = decrypt_password(student.password)
    except Exception:
        raise HTTPException(500, "密码解密失败，CIPHER_KEY 可能已变更，请重新添加该学生")

    result = do_login(student_id, password)
    del password
    if not result:
        raise HTTPException(502, "登录教务系统失败，请检查密码是否已修改")

    # 顺手刷新 token 和学生信息，跟 monitor 保持一致
    student.res_token = result["resToken"]
    student.session = result["session"]
    student.authcode = result["authcode"]
    student.token_expires_at = result["token_expires_at"]
    student.name = result.get("name") or student.name
    student.major = result.get("major") or student.major
    student.grade = result.get("grade") or student.grade
    db.commit()

    jw = Jw.from_token(result["resToken"], result["session"], result["authcode"])

    try:
        ctx, courses, nopass = fetch(jw)
    except ApiError as e:
        # 没有选课活动 / 接口报错 —— 属于正常业务情况，不是 500
        raise HTTPException(409, str(e))
    except LoginError as e:
        raise HTTPException(502, str(e))

    payload = build_payload(ctx, courses)
    payload["nopass_count"] = len(nopass)
    return payload
