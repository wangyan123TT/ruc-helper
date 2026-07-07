"""
成绩查询 + 比对 + 排名 + 邮件通知
"""
import json
import requests
import smtplib
import time
from datetime import datetime, timezone, timedelta
from email.mime.text import MIMEText
from sqlalchemy.orm import Session

from ..models import Student, Grade, NotificationLog, now
from ..schemas import GradeResponse

BASE_URL = "https://jw.ruc.edu.cn"
GRADE_API_PATH = "/resService/jwxtpt/v1/xsd/cjgl_xsxdsq/findKccjList"
RANK_API_PATH = "/resService/jwxtpt/v1/xsd/cjgl_xsxdsq/professionalRankingQuery"
SUMMARY_API_PATH = "/resService/jwxtpt/v1/xsd/cjgl_xsxdsq/findKccjTjsjList"
RANK_PJXFJD_PATH = "/resService/jwxtpt/v1/xsd/xsd_cjpmck/findCjglpjxfjdpm"
RANK_SSPJ_PATH = "/resService/jwxtpt/v1/xsd/xsd_cjpmck/findCjglsspjcjpm"
RANK_XFJQ_PATH = "/resService/jwxtpt/v1/xsd/xsd_cjpmck/findCjglxfjqpjcjpm"

RESOURCE_0526 = "XSMH0526"
RESOURCE_0527 = "XSMH0527"
RESOURCE_0511 = "XSMH0511"

TZ = timezone(timedelta(hours=8))

# 全局邮件配置（环境变量优先，可通过 API 动态覆盖）
import os
EMAIL_CONFIG = {
    "smtpHost": os.getenv("SMTP_HOST", "smtp.qq.com"),
    "smtpPort": int(os.getenv("SMTP_PORT", "587")),
    "smtpUsername": os.getenv("SMTP_USERNAME", ""),
    "smtpPassword": os.getenv("SMTP_PASSWORD", ""),
    "fromAddress": os.getenv("SMTP_FROM", ""),
}


def reload_email_config():
    """从数据库加载 SMTP 配置，覆盖环境变量中的空值"""
    try:
        from ..database import SessionLocal
        from ..models import Setting
        db = SessionLocal()
        for k in ["smtpHost", "smtpPort", "smtpUsername", "smtpPassword", "fromAddress"]:
            s = db.query(Setting).filter(Setting.key == k).first()
            if s and s.value:
                EMAIL_CONFIG[k] = int(s.value) if k == "smtpPort" else s.value
        db.close()
    except Exception:
        pass


def update_email_config(config: dict):
    """更新邮件配置（从 config.json 或环境变量加载后调用）"""
    EMAIL_CONFIG.update(config)


def build_headers(res_token: str, session: str, authcode: str) -> dict:
    return {
        "Content-Type": "application/json",
        "Accept": "application/json, text/plain, */*",
        "app": "PCWEB",
        "locale": "zh_CN",
        "token": res_token,
        "userrolecode": "student",
        "Cookie": f"SESSION={session}; authcode={authcode}",
        "Referer": "https://jw.ruc.edu.cn/Njw2017/index.html",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    }


def fetch_grades_from_api(res_token: str, session: str, authcode: str) -> list[dict] | None:
    """从教务 API 拉取成绩原始数据"""
    url = f"{BASE_URL}{GRADE_API_PATH}?resourceCode={RESOURCE_0526}&apiCode=jw.xsd.xsdInfo.controller.CjglKccjckController.findKccjList"
    headers = build_headers(res_token, session, authcode)
    return _post_json(url, {}, headers)


def fetch_ranking(res_token: str, session: str, authcode: str) -> dict | None:
    """并行拉取专业排名 + 学期汇总 + 三种排名"""
    from concurrent.futures import ThreadPoolExecutor, as_completed
    headers = build_headers(res_token, session, authcode)
    result = {}

    def _fetch(name, url):
        r = _post_json(url, {}, headers)
        return name, r

    urls = [
        ("major_rank", f"{BASE_URL}{RANK_API_PATH}?resourceCode={RESOURCE_0527}&apiCode=jw.xsd.xsdInfo.controller.CjglKccjckController.professionalRankingQuery"),
        ("semester_summary", f"{BASE_URL}{SUMMARY_API_PATH}?resourceCode={RESOURCE_0526}&apiCode=jw.xsd.xsdInfo.controller.CjglKccjckController.findKccjTjsjList"),
        ("gpa_rank", f"{BASE_URL}{RANK_PJXFJD_PATH}?resourceCode={RESOURCE_0511}&apiCode=jw.xsd.xsdInfo.controller.XsdCjpmckController.findCjglpjxfjdpm"),
        ("avg_rank", f"{BASE_URL}{RANK_SSPJ_PATH}?resourceCode={RESOURCE_0511}&apiCode=jw.xsd.xsdInfo.controller.XsdCjpmckController.findCjglsspjcjpm"),
        ("weighted_rank", f"{BASE_URL}{RANK_XFJQ_PATH}?resourceCode={RESOURCE_0511}&apiCode=jw.xsd.xsdInfo.controller.XsdCjpmckController.findCjglxfjqpjcjpm"),
    ]

    with ThreadPoolExecutor(max_workers=5) as ex:
        futures = {ex.submit(_fetch, name, url): name for name, url in urls}
        for f in as_completed(futures):
            name, r = f.result()
            if r:
                if name == "major_rank" and len(r) > 0:
                    result[name] = r[0]
                elif name == "semester_summary":
                    result[name] = r
                elif r.get("items"):
                    result[name] = r["items"][0]

    return result if result else None


def _post_json(url: str, body: dict, headers: dict) -> any:
    """POST JSON，3次重试"""
    for attempt in range(3):
        try:
            resp = requests.post(url, json=body, headers=headers, timeout=30)
        except Exception as e:
            print(f"[grade] 网络异常 (尝试{attempt+1}/3): {e}")
            if attempt < 2:
                time.sleep(3)
                continue
            return None

        if resp.status_code != 200:
            print(f"[grade] HTTP {resp.status_code}: {resp.text[:200]}")
            if attempt < 2:
                time.sleep(3)
                continue
            return None

        data = resp.json()
        if data.get("errorCode") != "success":
            print(f"[grade] API 错误: {data.get('errorMessage', data.get('errorCode'))}")
            if attempt < 2:
                time.sleep(3)
                continue
            return None

        return data.get("data", [])
    return None


def compute_real_gpa(grades: list[Grade]) -> dict:
    """计算真实 GPA（排除 P/F 课 cjfscode=3）"""
    total_points = 0.0
    total_credits = 0.0
    total_weighted_score = 0.0
    total_raw_score = 0.0
    course_count = 0

    for g in grades:
        if g.cjfscode == "3" or g.score in ("P", "-", ""):
            continue
        try:
            score = float(g.score)
        except (ValueError, TypeError):
            continue
        total_points += g.grade_point if g.grade_point else 0  # grade_point 已是 绩点×学分
        total_credits += g.credit
        total_weighted_score += score * g.credit
        total_raw_score += score
        course_count += 1

    return {
        "gpa": round(total_points / total_credits, 2) if total_credits > 0 else 0,
        "weighted_avg": round(total_weighted_score / total_credits, 1) if total_credits > 0 else 0,
        "simple_avg": round(total_raw_score / course_count, 1) if course_count > 0 else 0,
        "credits": total_credits,
        "courses": course_count,
    }


def sync_grades(db: Session, student: Student, raw_grades: list[dict]) -> dict:
    """将原始成绩数据同步到数据库，返回变动摘要"""
    student_id = student.student_id
    existing = db.query(Grade).filter(Grade.student_id == student_id).all()
    existing_map = {g.cjgl016id: g for g in existing}

    new_grades = []
    updated_grades = []
    current_ids = set()

    for item in raw_grades:
        cjgl016id = item.get("cjgl016id", "")
        course_name = item.get("kcname")
        # 跳过空记录（无 ID 或无课程名）
        if not cjgl016id or not course_name:
            continue
        current_ids.add(cjgl016id)

        cjfscode = str(item.get("cjfscode", "1"))
        # P/F 课程用等级制显示 (P/F)，而非百分制分数 (61)
        if cjfscode == "3":
            score = item.get("zcjname1") or item.get("cjxm3") or "P"
        else:
            raw_score = item.get("zcj")
            score = str(raw_score) if raw_score is not None else "-"
        gp = float(item.get("jd", 0) or 0)

        if cjgl016id in existing_map:
            grade_obj = existing_map[cjgl016id]
            new_score = str(score)
            new_daily = str(item.get("cjxm1") or "")
            new_mid = str(item.get("cjxm2") or "")
            new_final = str(item.get("cjxm3") or "")
            new_teacher = item.get("jsname") or ""

            changed = (
                grade_obj.score != new_score
                or grade_obj.grade_point != gp
                or grade_obj.daily_score != new_daily
                or grade_obj.midterm_score != new_mid
                or grade_obj.final_score != new_final
                or grade_obj.teacher != new_teacher
            )
            if changed:
                grade_obj.score = new_score
                grade_obj.grade_point = gp
                grade_obj.daily_score = new_daily
                grade_obj.midterm_score = new_mid
                grade_obj.final_score = new_final
                grade_obj.teacher = new_teacher
                grade_obj.category = item.get("kclbname") or item.get("kcxzname") or grade_obj.category
                grade_obj.grade_note = str(item.get("cjbzname") or "")
                grade_obj.last_updated_at = now()
                updated_grades.append(grade_obj)
        else:
            grade_obj = Grade(
                student_id=student_id,
                cjgl016id=cjgl016id,
                course_code=item.get("kcbh") or "",
                course_name=item.get("kcname") or "",
                score=str(score),
                daily_score=str(item.get("cjxm1") or ""),
                midterm_score=str(item.get("cjxm2") or ""),
                final_score=str(item.get("cjxm3") or ""),
                credit=float(item.get("xf", 0) or 0),
                grade_point=gp,
                semester=item.get("xnxq") or item.get("cjlrxq") or "",
                category=item.get("kclbname") or item.get("kcxzname") or "",
                course_module=item.get("kcmk") or item.get("kcmk_name") or "",
                teacher=item.get("jsname") or "",
                dept=item.get("kkdwname") or "",
                exam_type=item.get("ksxzname") or "",
                grade_note=str(item.get("cjbzname") or ""),
                cjfscode=str(item.get("cjfscode", "1")),
                first_seen_at=now(),
                last_updated_at=now(),
            )
            db.add(grade_obj)
            new_grades.append(grade_obj)

    db.commit()
    return {
        "total": len(current_ids),
        "new_count": len(new_grades),
        "updated_count": len(updated_grades),
        "new_grades": new_grades,
        "updated_grades": updated_grades,
    }


def send_grade_email(to_address: str, student_name: str, new_grades: list, updated_grades: list,
                     ranking: dict | None = None, real_gpa: dict | None = None):
    """发送成绩变动通知邮件"""
    if not EMAIL_CONFIG.get("smtpUsername"):
        print("[email] 未配置 SMTP，跳过邮件发送")
        return False
    if not to_address:
        print("[email] 未配置收件邮箱")
        return False

    now_str = datetime.now(TZ).strftime("%Y-%m-%d %H:%M:%S")

    # ── 样式 ──
    css = "body{margin:0;padding:0;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;color:#1a1a2e;line-height:1.5}"
    box = "border-radius:10px;padding:20px;margin:16px 0"
    th_style = "padding:8px 12px;text-align:left;font-size:12px;font-weight:600;color:#666;border-bottom:2px solid #e0e0e0"
    td_style = "padding:8px 12px;border-bottom:1px solid #f0f0f0;font-size:13px"
    num = ";text-align:right;font-variant-numeric:tabular-nums"
    h3 = "margin:0 0 12px;font-size:15px"

    # ── GPA 分组表 ──
    mr = (ranking or {}).get("major_rank", {}) or {}
    gpa_r = (ranking or {}).get("gpa_rank", {}) or {}
    avg_r = (ranking or {}).get("avg_rank", {}) or {}
    wgt_r = (ranking or {}).get("weighted_rank", {}) or {}
    ss = (ranking or {}).get("semester_summary", []) or []

    gpa_rows = ""
    # Group 1: GPA
    gpa_rows += f"<tr><td style='{td_style};font-weight:600'>平均学分绩点</td>"
    gpa_rows += f"<td style='{td_style}{num};font-size:20px;font-weight:700;color:#1a1a2e'>{mr.get('pjxfjd','') or (real_gpa or {}).get('gpa','')}</td>"
    gpa_rows += f"<td style='{td_style}{num}'>专业第{mr.get('pm','?')}</td>"
    gpa_rows += f"<td style='{td_style}{num}'>班级第{mr.get('bjpm','?')}</td></tr>"

    if gpa_r:
        gpa_rows += f"<tr><td style='{td_style};color:#999'>  └ 含P/F课</td>"
        gpa_rows += f"<td style='{td_style}{num};color:#999'>{gpa_r.get('pjxfjd','')}</td>"
        gpa_rows += f"<td style='{td_style}{num}'colspan=2>班级第{gpa_r.get('pm','?')}</td></tr>"

    # Group 2: Weighted avg
    gpa_rows += f"<tr><td style='{td_style};font-weight:600'>学分加权平均分</td>"
    gpa_rows += f"<td style='{td_style}{num};font-size:18px;font-weight:600'>{mr.get('pjxfj','') or (real_gpa or {}).get('weighted_avg','')}</td>"
    gpa_rows += f"<td style='{td_style}{num}'colspan=2>{'班级第'+str(wgt_r.get('pm','?')) if wgt_r else ''}</td></tr>"

    # Group 3: Simple avg
    gpa_rows += f"<tr><td style='{td_style};font-weight:600'>算术平均分</td>"
    gpa_rows += f"<td style='{td_style}{num};font-size:18px;font-weight:600'>{avg_r.get('xssscj','') or (real_gpa or {}).get('simple_avg','')}</td>"
    gpa_rows += f"<td style='{td_style}{num}'colspan=2>{'班级第'+str(avg_r.get('pm','?')) if avg_r else ''}</td></tr>"

    # Semester summary
    sem_rows = ""
    if ss:
        for s in ss:
            sem_rows += f"<tr><td style='{td_style}'>{s.get('jczy013id','')}</td><td style='{td_style}{num}'>{s.get('kcnum','')}门</td><td style='{td_style}{num}'>{s.get('zxf','')}学分</td><td style='{td_style}{num}'>GPA {s.get('pjxfjd','')}</td><td style='{td_style}{num}'>均分{s.get('pjxfj','')}</td></tr>"

    info = f"{mr.get('ndzy_name','')} {mr.get('skdw_name','')}" if mr else ""
    courses_info = f"{(real_gpa or {}).get('courses','')}门 / {(real_gpa or {}).get('credits','')}学分" if real_gpa else ""

    # ── 成绩变动表格 ──
    grade_rows = ""
    for g in (new_grades or []):
        grade_rows += f"<tr style='background:#f2faf5'>"
        grade_rows += f"<td style='{td_style}'>{g.course_name}</td>"
        grade_rows += f"<td style='{td_style}{num};font-weight:700;font-size:16px'>{getattr(g,'score','-')}</td>"
        grade_rows += f"<td style='{td_style}{num}'>{g.credit}</td>"
        grade_rows += f"<td style='{td_style}{num}'>{g.daily_score or '-'}</td>"
        grade_rows += f"<td style='{td_style}{num}'>{g.midterm_score or '-'}</td>"
        grade_rows += f"<td style='{td_style}{num}'>{g.final_score or '-'}</td>"
        grade_rows += f"<td style='{td_style}{num}'>{g.grade_point}</td>"
        grade_rows += f"<td style='{td_style}'>{g.teacher}</td></tr>"

    for g in (updated_grades or []):
        grade_rows += f"<tr style='background:#fef9f0'>"
        grade_rows += f"<td style='{td_style}'>{g.course_name}</td>"
        grade_rows += f"<td style='{td_style}{num};font-weight:700;font-size:16px'>{getattr(g,'score','-')}</td>"
        grade_rows += f"<td style='{td_style}{num}'>{g.credit}</td>"
        grade_rows += f"<td style='{td_style}{num}'>{g.daily_score or '-'}</td>"
        grade_rows += f"<td style='{td_style}{num}'>{g.midterm_score or '-'}</td>"
        grade_rows += f"<td style='{td_style}{num}'>{g.final_score or '-'}</td>"
        grade_rows += f"<td style='{td_style}{num}'>{g.grade_point}</td>"
        grade_rows += f"<td style='{td_style}'>{g.teacher}</td></tr>"

    # ── 组装 ──
    body = f"""<html><head><meta charset=utf-8><style>{css}</style></head><body>
    <div style='max-width:640px;margin:0 auto;padding:20px'>

    <h2 style='margin:0 0 4px;font-size:20px'>成绩变动通知</h2>
    <p style='margin:0 0 20px;color:#999;font-size:13px'>{student_name} · {now_str} · {info} · {courses_info}</p>

    <div style='background:#f8f9fb;{box}'>
    <h3 style='{h3};color:#1a1a2e'>当前成绩总览</h3>
    <table style='width:100%;border-collapse:collapse'>
    <tr><th style='{th_style}'>指标</th><th style='{th_style}{num}'>分数</th><th style='{th_style}{num}'>排名</th><th style='{th_style}{num}'>排名2</th></tr>
    {gpa_rows}
    </table>
    </div>"""

    if grade_rows:
        body += f"""
        <div style='{box}'>
        <h3 style='{h3};color:#1a1a2e'>成绩变动</h3>
        <table style='width:100%;border-collapse:collapse'>
        <tr><th style='{th_style}'>课程</th><th style='{th_style}{num}'>成绩</th><th style='{th_style}{num}'>学分</th><th style='{th_style}{num}'>平时</th><th style='{th_style}{num}'>期中</th><th style='{th_style}{num}'>期末</th><th style='{th_style}{num}'>绩点</th><th style='{th_style}'>教师</th></tr>
        {grade_rows}
        </table>
        </div>"""

    if sem_rows:
        body += f"""
        <div style='background:#f8f9fb;{box}'>
        <h3 style='{h3};color:#1a1a2e'>各学期汇总</h3>
        <p style='margin:0 0 8px;font-size:11px;color:#999'>系统核算（含P/F课按1.0绩点计入），真实GPA见上方总览</p>
        <table style='width:100%;border-collapse:collapse'>
        <tr><th style='{th_style}'>学期</th><th style='{th_style}{num}'>课程</th><th style='{th_style}{num}'>学分</th><th style='{th_style}{num}'>GPA</th><th style='{th_style}{num}'>均分</th></tr>
        {sem_rows}
        </table></div>"""

    body += """<p style='margin-top:24px;font-size:11px;color:#bbb'>RUC Helper 自动发送</p></div></body></html>"""

    try:
        msg = MIMEText(body, "html", "utf-8")
        msg["From"] = EMAIL_CONFIG["fromAddress"]
        msg["To"] = to_address
        subj = []
        if new_grades: subj.append(f"新出{len(new_grades)}门")
        if updated_grades: subj.append(f"更新{len(updated_grades)}门")
        msg["Subject"] = f"[成绩通知] {'，'.join(subj)}" if subj else "[成绩通知]"
        server = smtplib.SMTP(EMAIL_CONFIG["smtpHost"], EMAIL_CONFIG["smtpPort"], timeout=15)
        server.starttls()
        server.login(EMAIL_CONFIG["smtpUsername"], EMAIL_CONFIG["smtpPassword"])
        server.sendmail(EMAIL_CONFIG["fromAddress"], [to_address], msg.as_string())
        server.quit()
        print(f"[email] 已发送至 {to_address}")
        return True
    except Exception as e:
        print(f"[email] 发送失败: {e}")
        return False


def _grade_to_response(g: Grade, is_new: bool = False) -> GradeResponse:
    return GradeResponse(
        id=g.id,
        student_id=g.student_id,
        cjgl016id=g.cjgl016id,
        course_code=g.course_code,
        course_name=g.course_name,
        score=g.score,
        daily_score=g.daily_score or "",
        midterm_score=g.midterm_score or "",
        final_score=g.final_score or "",
        credit=g.credit,
        grade_point=g.grade_point,
        semester=g.semester,
        category=g.category,
        course_module=g.course_module or "",
        teacher=g.teacher,
        dept=g.dept,
        exam_type=g.exam_type,
        grade_note=g.grade_note or "",
        cjfscode=g.cjfscode or "1",
        is_new=is_new,
        first_seen_at=g.first_seen_at,
        last_updated_at=g.last_updated_at,
    )
