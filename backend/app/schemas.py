from datetime import datetime
from pydantic import BaseModel, Field


# ── Student ──

class StudentCreate(BaseModel):
    student_id: str = Field(..., min_length=1, description="学号")
    password: str = Field(..., min_length=1, description="密码")
    email: str = Field(default="", description="通知邮箱")


class StudentResponse(BaseModel):
    id: int
    student_id: str
    name: str
    email: str
    major: str
    grade: str
    is_active: bool
    is_monitored: bool = False
    token_expires_at: datetime | None
    grade_count: int = 0
    last_change_at: datetime | None = None
    created_at: datetime | None = None

    model_config = {"from_attributes": True}


# ── Grade ──

class GradeResponse(BaseModel):
    id: int
    student_id: str
    cjgl016id: str
    course_code: str
    course_name: str
    score: str
    daily_score: str = ""
    midterm_score: str = ""
    final_score: str = ""
    credit: float
    grade_point: float
    semester: str
    category: str
    course_module: str = ""
    teacher: str
    dept: str
    exam_type: str
    grade_note: str = ""
    cjfscode: str = "1"
    is_new: bool = False
    first_seen_at: datetime | None = None
    last_updated_at: datetime | None = None

    model_config = {"from_attributes": True}


class GradeRefreshResult(BaseModel):
    student_id: str
    total: int
    new_count: int
    updated_count: int
    new_grades: list[GradeResponse] = []
    updated_grades: list[GradeResponse] = []


# ── Monitor ──

class MonitorStatus(BaseModel):
    running: bool
    poll_interval: int
    active_students: int


class MonitorHistoryItem(BaseModel):
    id: int
    student_id: str
    change_type: str
    grade_ids: list[str]
    sent_at: datetime

    model_config = {"from_attributes": True}


# ── GPA Summary ──

class GpaSummary(BaseModel):
    student_id: str
    gpa: float = 0
    weighted_avg: float = 0
    simple_avg: float = 0
    credits: float = 0
    courses: int = 0
    api_gpa: float | None = None       # 系统 GPA（含P/F课）
    major_name: str = ""
    dept_name: str = ""
    class_rank: str = ""                # 班级排名
    major_rank: str = ""                # 专业排名
    gpa_rank: str = ""                  # GPA班排
    avg_rank: str = ""                  # 算术平均班排
    weighted_rank: str = ""             # 学分加权班排
    gpa_rank_score: str = ""            # GPA班排分数
    avg_rank_score: str = ""            # 算术平均班排分数
    weighted_rank_score: str = ""       # 学分加权班排分数
    semester_summary: list[dict] = []   # 各学期汇总

    model_config = {"from_attributes": True}


# ── Common ──

class MessageResponse(BaseModel):
    message: str
