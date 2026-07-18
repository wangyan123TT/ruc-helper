"""
抢课服务 —— 后台循环，窗口感知，检测目标课余额。

【硬约束】
  1. 只抢课，永不退课。saveStuTxByRmdx(退选) 本项目一行不写。
  2. 时间冲突即停：目标课与该生已选课撞时间 -> 标记 conflict，绝不提交。
  3. 只处理库里已有的三个学生的目标。

【两段式安全设计】
  段1(本文件当前状态): 只检测余额、判冲突、更新状态，**不提交**。
      有名额时把状态标成 ready，等人确认。
  段2(待接入): 真正调用 saveStuXkByRmdx 提交。需先追踪 payload 契约 +
      在志愿窗口做一次受控测试。由 _ARMED 开关 + 时间优先模式双重门控。

节奏:
  时间优先窗口内 & 07:00-23:00  -> 每 2 秒轮询(教务的"延迟释放"机制决定了
                                   夜间 23:00-07:00 不放名额，空转纯浪费)
  其余                          -> 每 30 秒探一次(等窗口/等白天)
"""
import asyncio
import json
from datetime import datetime, time, timezone, timedelta

from ..database import SessionLocal
from ..models import GrabTarget, Student, now
from .auth import decrypt_password
from . import xk

TZ = timezone(timedelta(hours=8))

FAST_INTERVAL = 2       # 时间优先窗口内的轮询间隔(秒)
IDLE_INTERVAL = 30      # 非窗口/夜间的探测间隔(秒)
DAY_START = time(7, 0)  # 白天释放名额时段
DAY_END = time(23, 0)

_grab_task: "asyncio.Task | None" = None
# 段2 的总扳机：False = 只检测不提交(当前)。段2 接入并测试后才允许置 True。
_ARMED = False

# 活跃状态：还在争取的目标（success/stopped/conflict 都算已了结）
ACTIVE = ("waiting", "ready", "grabbing")


def is_running() -> bool:
    return _grab_task is not None and not _grab_task.done()


def is_armed() -> bool:
    return _ARMED


def _daytime(dt: datetime) -> bool:
    return DAY_START <= dt.timetz().replace(tzinfo=None) <= DAY_END


def _parse_dt(s: str):
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M"):
        try:
            return datetime.strptime(s, fmt)
        except (ValueError, TypeError):
            continue
    return None


def _in_grab_window(ctx) -> bool:
    """时间优先(xkcscode12==0) 且当前在选课起止时间内"""
    if ctx.get("mode_code") != "0":
        return False
    now_dt = _parse_dt(ctx.get("now") or "")
    ks, js = _parse_dt(ctx.get("xkkssj") or ""), _parse_dt(ctx.get("xkjssj") or "")
    if now_dt and ks and js:
        return ks <= now_dt <= js
    return True   # 时间字段缺失时，以 mode_code 为准


def _set(db, t: GrabTarget, status: str, msg: str):
    if t.status != status or t.message != msg:
        t.status = status
        t.message = msg
        t.updated_at = now()
        db.commit()


def _submit(jw, ctx, target, course) -> tuple[bool, str]:
    """
    段2 占位：真正的提交在这里接入 saveStuXkByRmdx。
    当前未接入 —— 返回 (False, 原因)，绝不产生任何写操作。
    """
    if not _ARMED:
        return False, "检测到名额（提交功能未启用，请手动确认或等待段2接入）"
    # --- 段2 将在此调用 xk.submit_course(jw, ctx, course) ---
    return False, "提交通道未接入"


def poll_student_targets(db, student: Student) -> dict:
    """对一个学生的所有活跃目标跑一轮。返回摘要。"""
    targets = db.query(GrabTarget).filter(
        GrabTarget.student_id == student.student_id,
        GrabTarget.status.in_(ACTIVE),
    ).order_by(GrabTarget.priority).all()
    if not targets:
        return {"active": 0, "in_window": False}

    try:
        pwd = decrypt_password(student.password)
        jw = xk.Jw(student.student_id, pwd)
    except Exception as e:
        for t in targets:
            _set(db, t, t.status, f"登录失败: {str(e)[:40]}")
        return {"active": len(targets), "in_window": False, "error": "login"}
    finally:
        pwd = None

    try:
        ctx = xk.fetch_grab_context(jw)
    except xk.ApiError as e:
        for t in targets:
            _set(db, t, t.status, str(e))
        return {"active": len(targets), "in_window": False, "error": "context"}

    in_window = _in_grab_window(ctx)
    grabbed_cells = set(ctx["held_cells"])   # 本轮内动态累加，防止一次抢到两门互撞
    enrolled_names = set(ctx.get("held_names") or [])  # 已选上(通过)的课程名

    # 按需拉课程池（同 类别+子类别参数 只拉一次）
    pool_cache: dict = {}

    def pool_for(kclbcode, params):
        key = kclbcode + "|" + json.dumps(params, sort_keys=True)
        if key not in pool_cache:
            try:
                pool_cache[key] = xk.fetch_pool(jw, ctx, kclbcode, params)
            except xk.ApiError:
                pool_cache[key] = []
        return pool_cache[key]

    for t in targets:
        # 这门课已经选上了 -> 自动停止争抢（无论抢到/筛选通过/手动选，都算已到手）
        if t.course_name and t.course_name in enrolled_names:
            _set(db, t, "success", f"已选上「{t.course_name}」，自动停止争抢")
            continue

        try:
            params = json.loads(t.pool_params or "{}")
        except (ValueError, TypeError):
            params = {}
        course = xk.find_in_pool(pool_for(t.kclbcode, params), t.course_key)
        if not course:
            _set(db, t, "waiting", "课程未在当前列表中（可能未开放/已结束）")
            continue

        # 冲突检测（对已选课 + 本轮已抢到的课）
        conflict = sorted(xk.slot_cells(course["slots"]) & grabbed_cells)
        if conflict:
            human = "、".join(f"周{'一二三四五六日'[d-1]}第{p}节" for d, p in conflict)
            _set(db, t, "conflict", f"与已选课时间冲突（{human}），已停止")
            continue

        if not in_window:
            tip = ("等待时间优先窗口开启"
                   if ctx.get("mode_code") == "1" else "不在选课时间内")
            _set(db, t, "waiting", f"{tip}｜{course['name']} 已选{course['enrolled']}/容量{course['cap']}")
            continue

        surplus = course["surplus"]
        if surplus is not None and surplus > 0:
            t.attempts = (t.attempts or 0) + 1
            ok, msg = _submit(jw, ctx, t, course)
            if ok:
                grabbed_cells |= xk.slot_cells(course["slots"])
                _set(db, t, "success", f"已抢到！{course['class_name']}")
            else:
                _set(db, t, "ready", f"有名额（余{surplus}）· {msg}")
        else:
            _set(db, t, "grabbing", f"盯着·余{surplus if surplus is not None else '?'}"
                 f"（已选{course['enrolled']}/容量{course['cap']}）")

    remaining = db.query(GrabTarget).filter(
        GrabTarget.student_id == student.student_id,
        GrabTarget.status.in_(ACTIVE),
    ).count()
    return {"active": len(targets), "remaining": remaining, "in_window": in_window,
            "mode_code": ctx.get("mode_code")}


async def _loop():
    print("[grab] 抢课检测循环启动")
    while True:
        interval = IDLE_INTERVAL
        try:
            db = SessionLocal()
            students = (db.query(Student)
                        .join(GrabTarget, GrabTarget.student_id == Student.student_id)
                        .filter(GrabTarget.status.in_(ACTIVE))
                        .distinct().all())
            any_window = False
            for s in students:
                try:
                    r = await asyncio.to_thread(poll_student_targets, db, s)
                    any_window = any_window or r.get("in_window")
                except Exception as e:
                    print(f"[grab] 轮询 {s.student_id} 异常: {e}")
            db.close()
            # 时间优先窗口 & 白天 -> 快节奏；否则慢节奏
            if any_window and _daytime(datetime.now(TZ)):
                interval = FAST_INTERVAL
        except Exception as e:
            print(f"[grab] 循环异常: {e}")
        await asyncio.sleep(interval)


def start_grab():
    global _grab_task
    if is_running():
        return False
    _grab_task = asyncio.create_task(_loop())
    print("[grab] 已启动")
    return True


def stop_grab():
    global _grab_task
    if _grab_task and not _grab_task.done():
        _grab_task.cancel()
    print("[grab] 已停止")
    return True
