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


def _sem_sort_key(s: str) -> int:
    """学期时间序键：学年首年*10 + 学期序(秋1 春2 夏3)。越大越新，同学年内 秋<春<夏。"""
    import re
    m = re.search(r"20\d{2}", s or "")
    y = int(m.group()) if m else 0
    if re.search(r"秋|第?一学期", s or ""):
        t = 1
    elif re.search(r"春|第?二学期", s or ""):
        t = 2
    elif re.search(r"夏|第?三学期", s or ""):
        t = 3
    else:
        t = 0
    return y * 10 + t


def compute_semester_gpa(grades: list) -> list[dict]:
    """按学期算 GPA，口径同 compute_real_gpa（不含 P/F，Σ学分绩点/Σ学分），与前端页面一致。
    新学期在前。用于成绩通知邮件的「各学期汇总」，避免用教务含 P/F 的 pjxfjd 造成前后不一致。"""
    groups: dict[str, list] = {}
    for g in grades:
        groups.setdefault(g.semester or "其他", []).append(g)
    out = []
    for sem, gs in groups.items():
        pts = crd = wsum = rsum = 0.0
        n = 0
        credits_all = 0.0
        for g in gs:
            credits_all += g.credit or 0
            if g.cjfscode == "3" or g.score in ("P", "-", ""):
                continue
            try:
                sc = float(g.score)
            except (ValueError, TypeError):
                continue
            pts += g.grade_point or 0
            crd += g.credit or 0
            wsum += sc * (g.credit or 0)
            rsum += sc
            n += 1
        out.append({
            "semester": sem,
            "courses": len(gs),
            "credits": round(credits_all, 1),
            "gpa": round(pts / crd, 2) if crd else None,
            "avg": round(rsum / n, 1) if n else None,
        })
    out.sort(key=lambda x: _sem_sort_key(x["semester"]), reverse=True)
    return out


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


def build_grade_email_html(student_name: str, new_grades: list, updated_grades: list,
                           ranking: dict | None = None, real_gpa: dict | None = None,
                           all_grades: list | None = None):
    """拼成绩通知邮件 -> (标题, html)。与发送解耦，便于预览/测试。"""
    from . import notify

    now_str = datetime.now(TZ).strftime("%Y-%m-%d %H:%M:%S")
    mr = (ranking or {}).get("major_rank", {}) or {}
    avg_r = (ranking or {}).get("avg_rank", {}) or {}
    wgt_r = (ranking or {}).get("weighted_rank", {}) or {}
    sems = compute_semester_gpa(all_grades or [])   # 口径同页面（不含 P/F），非教务含 P/F 的 pjxfjd
    rg = real_gpa or {}

    INK, DIM, LINE = notify.INK, notify.INK_DIM, notify.LINE
    gpa_val = rg.get("gpa") or mr.get("pjxfjd") or "—"   # 与页面 hero 一致：真实 GPA（不含 P/F）优先
    info = f"{mr.get('ndzy_name', '')} {mr.get('skdw_name', '')}".strip()

    # 顶部高亮
    pills = ""
    if new_grades:
        pills += notify.pill(f"新出 {len(new_grades)} 门", notify.JADE)
    if updated_grades:
        pills += notify.pill(f"更新 {len(updated_grades)} 门", notify.GOLD)
    body = f"<div style='margin:8px 0 2px'>{pills}</div>" if pills else ""

    # 成绩卡：分档着色 + 左侧色条
    def _card(g, tag, tag_color):
        c = notify.score_color(getattr(g, "score", ""))
        sub = f"{g.credit}学分 · {g.teacher or '—'}"
        extra = []
        if g.daily_score:
            extra.append(f"平时{g.daily_score}")
        if g.midterm_score:
            extra.append(f"期中{g.midterm_score}")
        if g.final_score:
            extra.append(f"期末{g.final_score}")
        if extra:
            sub += " · " + " ".join(extra)
        if g.grade_point not in (None, ""):
            sub += f" · 绩点{g.grade_point}"
        score = getattr(g, "score", "—")
        return (
            f"<table role='presentation' width='100%' cellpadding='0' cellspacing='0' "
            f"style='border:1px solid {LINE};border-left:3px solid {c};border-radius:10px;margin:0 0 8px'>"
            f"<tr><td style='padding:11px 14px'>"
            f"<div style='font-size:15px;font-weight:600;color:{INK}'>{g.course_name}"
            f"<span style='font-size:10px;font-weight:700;color:{tag_color};margin-left:8px'>{tag}</span></div>"
            f"<div style='font-size:12px;color:{DIM};margin-top:3px'>{sub}</div></td>"
            f"<td width='58' align='right' style='padding:11px 16px 11px 4px;vertical-align:middle'>"
            f"<span style='font-size:26px;font-weight:700;color:{c}'>{score}</span></td>"
            f"</tr></table>"
        )

    cards = "".join(_card(g, "新", notify.JADE) for g in (new_grades or []))
    cards += "".join(_card(g, "更新", notify.GOLD) for g in (updated_grades or []))
    if cards:
        body += notify.section("这次的变动", cards)

    # 学业总览
    def _stat(label, val, rank, big=True):
        vs = "20px" if big else "17px"
        return (
            f"<tr><td style='padding:9px 0;border-bottom:1px solid {LINE};font-size:13px;color:{INK}'>{label}</td>"
            f"<td align='right' style='padding:9px 0;border-bottom:1px solid {LINE};font-size:{vs};font-weight:700;color:{INK}'>{val}</td>"
            f"<td align='right' style='padding:9px 0 9px 14px;border-bottom:1px solid {LINE};font-size:12px;color:{DIM};white-space:nowrap'>{rank or ''}</td></tr>"
        )

    rank1 = []
    if mr.get("pm"):
        rank1.append(f"专业第{mr['pm']}")
    if mr.get("bjpm"):
        rank1.append(f"班级第{mr['bjpm']}")
    gpa_tbl = "<table role='presentation' width='100%' cellpadding='0' cellspacing='0'>"
    gpa_tbl += _stat("平均学分绩点", gpa_val, " · ".join(rank1))
    if mr.get("pjxfj") or rg.get("weighted_avg"):
        gpa_tbl += _stat("学分加权均分", mr.get("pjxfj") or rg.get("weighted_avg"),
                         f"班级第{wgt_r['pm']}" if wgt_r.get("pm") else "", big=False)
    if avg_r.get("xssscj") or rg.get("simple_avg"):
        gpa_tbl += _stat("算术平均分", avg_r.get("xssscj") or rg.get("simple_avg"),
                         f"班级第{avg_r['pm']}" if avg_r.get("pm") else "", big=False)
    gpa_tbl += "</table>"
    if rg.get("courses"):
        gpa_tbl += f"<div style='margin:10px 0 0;font-size:11px;color:{DIM}'>{rg.get('courses', '')} 门 · {rg.get('credits', '')} 学分累计</div>"
    body += notify.section("学业总览", gpa_tbl)

    # 各学期汇总（口径同页面：不含 P/F，Σ学分绩点/Σ学分；新学期在前）
    if sems:
        th = f"padding:7px 8px;font-size:11px;color:{DIM};text-align:right;border-bottom:2px solid {LINE}"
        td = f"padding:6px 8px;font-size:12px;color:{INK};text-align:right;border-bottom:1px solid {LINE}"
        rows = (f"<tr><th style='{th};text-align:left'>学期</th><th style='{th}'>课程</th>"
                f"<th style='{th}'>学分</th><th style='{th}'>学期GPA</th><th style='{th}'>均分</th></tr>")
        for s in sems:
            gpa_txt = s["gpa"] if s["gpa"] is not None else "—"
            avg_txt = s["avg"] if s["avg"] is not None else "—"
            rows += (f"<tr><td style='{td};text-align:left'>{s['semester']}</td>"
                     f"<td style='{td}'>{s['courses']}门</td><td style='{td}'>{s['credits']}</td>"
                     f"<td style='{td}'>{gpa_txt}</td><td style='{td}'>{avg_txt}</td></tr>")
        sem_tbl = (f"<table role='presentation' width='100%' cellpadding='0' cellspacing='0' style='border-collapse:collapse'>{rows}</table>"
                   f"<div style='margin:8px 0 0;font-size:11px;color:{DIM}'>学期 GPA 与页面口径一致：不含 P/F 课。</div>")
        body += notify.section("各学期汇总", sem_tbl)

    # 标题 / 主题
    if new_grades and updated_grades:
        title = f"新出 {len(new_grades)} 门 · 更新 {len(updated_grades)} 门"
    elif new_grades:
        title = f"新出 {len(new_grades)} 门成绩"
    elif updated_grades:
        title = f"{len(updated_grades)} 门成绩更新"
    else:
        title = "成绩有变动"
    parts = [student_name, info]
    if gpa_val != "—":
        parts.append(f"当前 GPA {gpa_val}")
    parts.append(now_str)
    intro = " · ".join(x for x in parts if x)

    html = notify.render_email(kicker="成绩通知", title=title, intro=intro, body=body, accent=notify.CINNABAR)
    return title, html


def send_grade_email(to_address: str, student_name: str, new_grades: list, updated_grades: list,
                     ranking: dict | None = None, real_gpa: dict | None = None,
                     all_grades: list | None = None):
    """发送成绩变动通知邮件（品牌化，走通用通道 notify）。"""
    from . import notify
    title, html = build_grade_email_html(student_name, new_grades, updated_grades,
                                         ranking, real_gpa, all_grades)
    return notify.send_html(to_address, f"选课助手 · {title}", html)


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
