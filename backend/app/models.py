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
    """登录会话 —— 令牌到学号的映射。存 DB 所以服务重启不掉线。
    is_admin=True 为管理员会话（可看所有人 + 管理监控），student_id 存 'admin'。"""
    __tablename__ = "sessions"

    token = Column(String(64), primary_key=True)
    student_id = Column(String(20), nullable=False, index=True)
    is_admin = Column(Boolean, default=False)
    expires_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=now)


class CourseGradeStat(Base):
    """历年给分分布 —— 按 (年份, 课程, 老师) 聚合后的成绩分布。

    数据来自学校公布的成绩汇总（宽表：每列一个教学班，行含课名/老师/课号/各生成绩）。
    只存聚合量，不存单个学生分数。评价核心是 86+ / 90+ 占比。
    course_key / teacher_key 是归一化后的匹配键，见 services/coursematch.py，
    导入与查询共用同一套归一化，否则课程池里的课对不上历史数据。
    """
    __tablename__ = "course_grade_stats"

    id           = Column(Integer, primary_key=True, autoincrement=True)
    year         = Column(String(8), nullable=False, index=True)   # "2025" / "2024" ...
    course_name  = Column(String(200), default="")                 # 原始课名
    course_key   = Column(String(200), default="", index=True)     # 归一化课名(精确匹配)
    course_loose = Column(String(200), default="", index=True)     # 去括号后的宽松 key(兜底匹配)
    teacher      = Column(String(100), default="")                 # 原始老师名
    teacher_key  = Column(String(100), default="", index=True)     # 归一化老师名
    n_graded     = Column(Integer, default=0)                      # 有效数字成绩人数
    ge86         = Column(Integer, default=0)                      # ≥86 人数
    ge90         = Column(Integer, default=0)                      # ≥90 人数
    n_pass       = Column(Integer, default=0)                      # 记 P(通过) 的人数
    avg          = Column(Float, default=0)                        # 数字成绩均分
    sections     = Column(Integer, default=0)                      # 合并了几个教学班
    created_at   = Column(DateTime, default=now)

    __table_args__ = (UniqueConstraint("year", "course_key", "teacher_key",
                                       name="uq_course_grade_stat"),)


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
