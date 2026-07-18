"""
抢课路由

【只读为主 + 目标管理】本路由不含任何选课/退课写操作。
真正的提交在 services/grab.py 的后台循环里，且当前处于未接入(段1)状态。
凭据复用 students 表已加密存储的密码。
"""
import json

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import GrabTarget, Student, now
from ..services.auth import decrypt_password
from ..services import grab as grab_svc
from ..services import xk

router = APIRouter(prefix="/api/grab", tags=["grab"])


# ---------- schemas ----------
class AddTarget(BaseModel):
    kclbcode: str
    course_key: str
    course_name: str = ""
    class_name: str = ""
    teacher: str = ""
    credit: float = 0
    priority: int = 0
    course_json: str = "{}"
    pool_params: dict = {}   # 子类别维度参数(跨学科的 honerItemId/kkdwid 等)


def _target_out(t: GrabTarget) -> dict:
    return {
        "id": t.id, "student_id": t.student_id,
        "course_key": t.course_key, "kclbcode": t.kclbcode,
        "course_name": t.course_name, "class_name": t.class_name,
        "teacher": t.teacher, "credit": t.credit, "priority": t.priority,
        "status": t.status, "message": t.message, "attempts": t.attempts,
        "updated_at": t.updated_at.isoformat() if t.updated_at else None,
    }


def _login(student: Student):
    """复用加密密码登录，返回 (jw, ctx)"""
    try:
        pwd = decrypt_password(student.password)
    except Exception:
        raise HTTPException(500, "密码解密失败，请重新添加该学生")
    try:
        jw = xk.Jw(student.student_id, pwd)
    except xk.LoginError as e:
        raise HTTPException(502, f"登录教务失败：{e}")
    finally:
        pwd = None
    try:
        ctx = xk.fetch_grab_context(jw)
    except xk.ApiError as e:
        raise HTTPException(409, str(e))
    return jw, ctx


def _student_or_404(db, student_id):
    s = db.query(Student).filter(Student.student_id == student_id).first()
    if not s:
        raise HTTPException(404, "学生不存在")
    return s


# ---------- 浏览课程池（供前端选目标） ----------
@router.get("/{student_id}/categories")
def categories(student_id: str, db: Session = Depends(get_db)):
    """课程类别列表 + 选课模式信息"""
    s = _student_or_404(db, student_id)
    jw, ctx = _login(s)
    return {
        "mode": ctx["mode"], "mode_code": ctx["mode_code"], "ctrl": ctx["ctrl"],
        "hd_name": ctx["hd_name"], "xkkssj": ctx["xkkssj"], "xkjssj": ctx["xkjssj"],
        "now": ctx["now"], "is_time_priority": ctx["mode_code"] == "0",
        "categories": xk.fetch_categories(jw, ctx),
    }


@router.get("/{student_id}/pool")
def pool(student_id: str, kclbcode: str,
         xxklbcode: str = "", honerItemId: str = "", kkdwid: str = "", isSxrz: str = "",
         db: Session = Depends(get_db)):
    """某类别（可选子类别参数）的可选课程池（带余额、时间、是否与已选课冲突）"""
    s = _student_or_404(db, student_id)
    jw, ctx = _login(s)
    params = {k: v for k, v in
              {"xxklbcode": xxklbcode, "honerItemId": honerItemId,
               "kkdwid": kkdwid, "isSxrz": isSxrz}.items() if v}
    courses = xk.fetch_pool(jw, ctx, kclbcode, params)
    held = set(ctx["held_cells"])
    chosen = {t.course_key for t in db.query(GrabTarget).filter(
        GrabTarget.student_id == student_id).all()}
    out = []
    for c in courses:
        conflict = sorted(xk.slot_cells(c["slots"]) & held)
        out.append({
            "course_key": c["course_key"], "kclbcode": c["kclbcode"],
            "name": c["name"], "class_name": c["class_name"], "teacher": c["teacher"],
            "credit": c["credit"], "dept": c["dept"],
            "cap": c["cap"], "enrolled": c["enrolled"], "surplus": c["surplus"],
            "slots": c["slots"],
            "conflict": [{"day": d, "period": p} for d, p in conflict],
            "already_target": c["course_key"] in chosen,
        })
    return {"mode_code": ctx["mode_code"], "courses": out}


# ---------- 目标管理 ----------
@router.get("/{student_id}/targets")
def list_targets(student_id: str, db: Session = Depends(get_db)):
    _student_or_404(db, student_id)
    ts = db.query(GrabTarget).filter(GrabTarget.student_id == student_id)\
        .order_by(GrabTarget.priority, GrabTarget.id).all()
    return [_target_out(t) for t in ts]


@router.post("/{student_id}/targets")
def add_target(student_id: str, body: AddTarget, db: Session = Depends(get_db)):
    _student_or_404(db, student_id)
    exists = db.query(GrabTarget).filter(
        GrabTarget.student_id == student_id,
        GrabTarget.course_key == body.course_key).first()
    if exists:
        raise HTTPException(409, "该课程已在目标列表中")
    t = GrabTarget(
        student_id=student_id, course_key=body.course_key, kclbcode=body.kclbcode,
        pool_params=json.dumps(body.pool_params or {}),
        course_name=body.course_name, class_name=body.class_name, teacher=body.teacher,
        credit=body.credit, priority=body.priority, status="waiting",
        message="已加入，等待抢课", course_json=body.course_json,
    )
    db.add(t)
    db.commit()
    db.refresh(t)
    return _target_out(t)


@router.delete("/{student_id}/targets/{target_id}")
def remove_target(student_id: str, target_id: int, db: Session = Depends(get_db)):
    t = db.query(GrabTarget).filter(
        GrabTarget.id == target_id, GrabTarget.student_id == student_id).first()
    if not t:
        raise HTTPException(404, "目标不存在")
    db.delete(t)
    db.commit()
    return {"ok": True}


# ---------- 全局状态 ----------
@router.get("/status")
def status(db: Session = Depends(get_db)):
    total = db.query(GrabTarget).count()
    by = {}
    for t in db.query(GrabTarget).all():
        by[t.status] = by.get(t.status, 0) + 1
    return {
        "running": grab_svc.is_running(),
        "armed": grab_svc.is_armed(),   # False = 只检测不提交(段1)
        "total_targets": total,
        "by_status": by,
    }
