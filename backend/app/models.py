import json
from datetime import datetime, timezone, timedelta
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, Text, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship

from .database import Base

TZ = timezone(timedelta(hours=8))


def now():
    return datetime.now(TZ).replace(tzinfo=None)


class Student(Base):
    __tablename__ = "students"

    id = Column(Integer, primary_key=True, autoincrement=True)
    student_id = Column(String(20), unique=True, nullable=False, index=True)
    name = Column(String(50), default="")
    password = Column(Text, nullable=False)
    email = Column(String(100), default="")
    major = Column(String(100), default="")
    grade = Column(String(20), default="")
    res_token = Column(Text, default="")
    session = Column(String(100), default="")
    authcode = Column(String(20), default="")
    token_expires_at = Column(DateTime, nullable=True)
    is_active = Column(Boolean, default=True)
    is_monitored = Column(Boolean, default=False)
    created_at = Column(DateTime, default=now)
    updated_at = Column(DateTime, default=now, onupdate=now)

    grades = relationship("Grade", back_populates="student", cascade="all, delete-orphan")


class Grade(Base):
    __tablename__ = "grades"

    id = Column(Integer, primary_key=True, autoincrement=True)
    student_id = Column(String(20), ForeignKey("students.student_id", ondelete="CASCADE"), nullable=False, index=True)
    cjgl016id = Column(String(50), nullable=False)
    course_code = Column(String(50), default="")
    course_name = Column(String(200), default="")
    __table_args__ = (UniqueConstraint("student_id", "cjgl016id", name="uq_student_grade"),)
    score = Column(String(20), default="")
    daily_score = Column(String(20), default="")
    midterm_score = Column(String(20), default="")
    final_score = Column(String(20), default="")
    credit = Column(Float, default=0)
    grade_point = Column(Float, default=0)
    semester = Column(String(50), default="")
    category = Column(String(100), default="")
    course_module = Column(String(100), default="")
    teacher = Column(String(50), default="")
    dept = Column(String(100), default="")
    exam_type = Column(String(50), default="")
    grade_note = Column(String(50), default="")
    cjfscode = Column(String(5), default="1")
    first_seen_at = Column(DateTime, default=now)
    last_updated_at = Column(DateTime, default=now, onupdate=now)

    student = relationship("Student", back_populates="grades")


class NotificationLog(Base):
    __tablename__ = "notification_log"

    id = Column(Integer, primary_key=True, autoincrement=True)
    student_id = Column(String(20), nullable=False, index=True)
    grade_ids = Column(Text, default="[]")
    change_type = Column(String(20), default="new")
    sent_at = Column(DateTime, default=now)

    def get_grade_ids(self):
        return json.loads(self.grade_ids) if self.grade_ids else []


class MonitorLog(Base):
    __tablename__ = "monitor_log"

    id = Column(Integer, primary_key=True, autoincrement=True)
    student_id = Column(String(20), nullable=False, index=True)
    status = Column(String(20), default="ok")   # ok / fail / noop
    message = Column(Text, default="")
    created_at = Column(DateTime, default=now)


class Setting(Base):
    __tablename__ = "settings"

    key = Column(String(50), primary_key=True)
    value = Column(Text, default="")


class Session(Base):
    """登录会话 —— 令牌到学号的映射。存 DB 所以服务重启不掉线。"""
    __tablename__ = "sessions"

    token = Column(String(64), primary_key=True)
    student_id = Column(String(20), nullable=False, index=True)
    expires_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=now)


class GrabTarget(Base):
    """抢课目标 —— 某学生想抢的某门课（的某个班）。

    抢课器每轮用 kclbcode 重新拉该类别课程列表，靠 course_key 定位到这门课，
    检测余额；course_json 保存该课完整快照，供提交(第二段)与前端展示时间/地点。
    """
    __tablename__ = "grab_targets"

    id = Column(Integer, primary_key=True, autoincrement=True)
    student_id = Column(String(20), ForeignKey("students.student_id", ondelete="CASCADE"),
                        nullable=False, index=True)
    course_key = Column(String(64), nullable=False)   # 课程唯一标识(kth)，轮询时用来定位
    kclbcode = Column(String(20), default="")         # 课程类别码，决定查哪个课程池
    pool_params = Column(Text, default="{}")          # 子类别维度参数(跨学科的honerItemId/kkdwid等)，重拉池子时透传
    course_name = Column(String(200), default="")
    class_name = Column(String(200), default="")       # 教学班名(ktmc_name)
    teacher = Column(String(100), default="")
    credit = Column(Float, default=0)
    priority = Column(Integer, default=0)              # 数字越小越优先
    # waiting(等待窗口/名额) / grabbing(有名额正在抢) / success(已抢到) / failed / stopped
    status = Column(String(20), default="waiting")
    message = Column(Text, default="")                 # 最近一次状态详情
    course_json = Column(Text, default="{}")           # 课程完整快照(提交/展示用)
    attempts = Column(Integer, default=0)              # 已尝试提交次数
    created_at = Column(DateTime, default=now)
    updated_at = Column(DateTime, default=now, onupdate=now)

    __table_args__ = (UniqueConstraint("student_id", "course_key", name="uq_grab_target"),)
