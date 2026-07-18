"""
成绩查询路由
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Student, Grade
from ..services.session import require_owner
from ..schemas import GradeResponse, GradeRefreshResult, GpaSummary
from ..services.grade import (
    fetch_grades_from_api, fetch_ranking, sync_grades, _grade_to_response,
)

router = APIRouter(prefix="/api/grades", tags=["grades"],
                   dependencies=[Depends(require_owner)])   # 只能查自己学号


@router.get("/{student_id}", response_model=list[GradeResponse])
def get_grades(student_id: str, db: Session = Depends(get_db)):
    student = db.query(Student).filter(Student.student_id == student_id).first()
    if not student:
        raise HTTPException(404, "学生不存在")

    grades = db.query(Grade).filter(Grade.student_id == student_id)\
        .order_by(Grade.semester.desc(), Grade.course_name).all()
    return [_grade_to_response(g) for g in grades]


@router.get("/{student_id}/summary", response_model=GpaSummary)
def get_summary(student_id: str, db: Session = Depends(get_db)):
    """排名 + GPA 汇总（使用教务 API 原生数据）"""
    student = db.query(Student).filter(Student.student_id == student_id).first()
    if not student:
        raise HTTPException(404, "学生不存在")
    if not student.res_token:
        raise HTTPException(400, "请先重新登录获取 token")

    ranking = fetch_ranking(student.res_token, student.session, student.authcode)
    if not ranking:
        raise HTTPException(502, "拉取排名数据失败")

    mr = ranking.get("major_rank", {}) or {}
    gpa_r = ranking.get("gpa_rank", {}) or {}
    avg_r = ranking.get("avg_rank", {}) or {}
    wgt_r = ranking.get("weighted_rank", {}) or {}

    return GpaSummary(
        student_id=student_id,
        gpa=float(mr.get("pjxfjd", 0)),
        weighted_avg=float(mr.get("pjxfj", 0)),
        simple_avg=float(avg_r.get("xssscj", 0)),
        credits=float(mr.get("sdxf", 0)),
        courses=int(mr.get("countnum", 0)),
        api_gpa=float(gpa_r.get("pjxfjd", 0)) if gpa_r else None,
        major_name=str(mr.get("ndzy_name", "")),
        dept_name=str(mr.get("skdw_name", "")),
        class_rank=str(mr.get("bjpm", "")),
        major_rank=str(mr.get("pm", "")),
        gpa_rank=str(gpa_r.get("pm", "")),
        avg_rank=str(avg_r.get("pm", "")),
        weighted_rank=str(wgt_r.get("pm", "")),
        gpa_rank_score=str(gpa_r.get("pjxfjd", "")),
        avg_rank_score=str(avg_r.get("xssscj", "")),
        weighted_rank_score=str(wgt_r.get("xfjqpjcj", "")),
        semester_summary=ranking.get("semester_summary", []) or [],
    )


@router.post("/{student_id}/refresh", response_model=GradeRefreshResult)
def refresh_grades(student_id: str, db: Session = Depends(get_db)):
    student = db.query(Student).filter(Student.student_id == student_id).first()
    if not student:
        raise HTTPException(404, "学生不存在")

    raw = fetch_grades_from_api(student.res_token, student.session, student.authcode)
    if raw is None:
        raise HTTPException(502, "拉取成绩失败，请尝试重新登录")

    result = sync_grades(db, student, raw)

    return GradeRefreshResult(
        student_id=student_id,
        total=result["total"],
        new_count=result["new_count"],
        updated_count=result["updated_count"],
        new_grades=[_grade_to_response(g, is_new=True) for g in result["new_grades"]],
        updated_grades=[_grade_to_response(g) for g in result["updated_grades"]],
    )
