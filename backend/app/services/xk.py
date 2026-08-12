"""
选课 — 待筛选课程数据核心（登录 / 抓取 / 解析 / 聚合）

【只读】只调教务查询接口，绝不改动选课状态。
        写操作 (saveStuXkByRmdx / saveStuTxByRmdx) 本模块不涉及。

放在 services/ 下是因为 backend/Dockerfile 只 COPY app/，放项目根目录容器里读不到。

本文件刻意不含任何 HTML 渲染，也不写相对 import —— 这样三个地方都能用:
  - 后端路由:  from .xk import fetch, group
  - 命令行:    sys.path 加上本目录后 import xk
  - 独立网页:  同上
HTML 渲染在项目根的 xk_render.py。

接口路径的来历见 CONTEXT.md「第二套系统」一节。
"""
from collections import defaultdict

import requests

BASE = "https://jw.ruc.edu.cn"
RES = f"{BASE}/resService"
XK = "/jwxtpt/v1/xsd/stuCourseCenterController"
CC = "jw.xsd.courseCenter.controller.StuCourseCenterController"

WEEK = "一二三四五六日"

# 课程类别 -> css 类名。按类别上色是真实语义分组，非随机配色。
CAT_CLASS = {
    "思想政治理论课": "pol",
    "专业核心课": "core",
    "专业选修课": "elec",
    "通识核心课": "gen",
    "公共外语": "lang",
    "公共体育": "pe",
}


class LoginError(Exception):
    pass


class ApiError(Exception):
    pass


class Jw:
    """一个教务登录态。密码不会被保存为属性。"""

    def __init__(self, sid=None, pwd=None, token=None, session="", authcode=""):
        if token:
            self.token, self.session, self.authcode = token, session, authcode
            return
        try:
            r = requests.post(
                f"{BASE}/secService/login",
                json={"userCode": sid, "password": pwd,
                      "kaptcha": "testa", "userCodeType": "ldap"},
                headers={
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                    "KAPTCHA-KEY-GENERATOR-REDIS": "securityKaptchaRedisServiceAdapter",
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                },
                timeout=20,
            )
            d = r.json()
        except Exception as e:
            raise LoginError(f"连接教务系统失败：{e}")
        if d.get("errorCode") != "success":
            msg = (d.get("errorMessage") or "").strip()
            # 教务对「密码错误」返回没头没脑的 Internal Server Error，翻译成人话
            if not msg or msg.lower() in ("internal server error", "error"):
                msg = "学号或密码错误"
            raise LoginError(msg)
        self.token = d["data"]["token"]
        self.session = r.cookies.get("SESSION", "")
        self.authcode = d["data"].get("authcode", sid)
        # 注意：不保存 pwd

    @classmethod
    def from_token(cls, token, session, authcode):
        """复用已有登录态（后端 DB 里存着 token 时用）"""
        return cls(token=token, session=session, authcode=authcode)

    def post(self, path, api_code, body=None, res_code="XSMH0303"):
        url = f"{RES}{path}?resourceCode={res_code}&apiCode={api_code}"
        h = {
            "Content-Type": "application/json",
            "Accept": "application/json, text/plain, */*",
            "app": "PCWEB",
            "locale": "zh_CN",
            "token": self.token,
            "userrolecode": "student",
            "Cookie": f"SESSION={self.session}; authcode={self.authcode}",
            "Referer": f"{BASE}/Njw2017/index.html",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        }
        last = ""
        for _ in range(3):
            try:
                r = requests.post(url, json=body or {}, headers=h, timeout=30)
                d = r.json()
            except Exception as e:
                last = str(e)
                continue
            if d.get("errorCode") != "success":
                raise ApiError(f"{path.rsplit('/', 1)[-1]}: {d.get('errorMessage')}")
            return d.get("data")
        raise ApiError(f"{path.rsplit('/', 1)[-1]} 请求失败（重试3次）：{last}")

    def write(self, path, api_code, body, res_code="XSMH0303"):
        """写操作：单次请求，绝不重试（避免网络抖动造成重复提交）。返回 (ok, message)。"""
        url = f"{RES}{path}?resourceCode={res_code}&apiCode={api_code}"
        h = {
            "Content-Type": "application/json",
            "Accept": "application/json, text/plain, */*",
            "app": "PCWEB", "locale": "zh_CN", "token": self.token,
            "userrolecode": "student",
            "Cookie": f"SESSION={self.session}; authcode={self.authcode}",
            "Referer": f"{BASE}/Njw2017/index.html",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        }
        r = requests.post(url, json=body or {}, headers=h, timeout=30)
        d = r.json()
        return (d.get("errorCode") == "success"), (d.get("errorMessage") or "")


def _parse_weeks(s):
    """周次串 -> 周次整数集合。兼容 '1,2,3' 展开式与 '1-16'/'1-8,10-16' 区间式。"""
    out = set()
    for part in (s or "").replace("周", "").split(","):
        part = part.strip()
        if not part:
            continue
        if "-" in part:
            try:
                a, b = part.split("-")[:2]
                out.update(range(int(a), int(b) + 1))
                continue
            except ValueError:
                pass
        if part.isdigit():
            out.add(int(part))
    return out


def parse_kbinfo(s):
    """
    kbinfo 是教务自定义编码，无文档，'~' 分隔时段，'@' 分隔字段:
      [0]周次显示 [1]周次列表 [2]星期节次串 [3]节次列表 [4]教室
      [5]开始时间 [6]结束时间 [7]标志 [8]校区 [9]楼id [10]楼名
    节次列表每项 = 星期(1位) + 节次(2位)，例: '401'=周四第1节, '107'=周一第7节
    """
    out = []
    for seg in (s or "").split("~"):
        seg = seg.strip()
        if not seg:
            continue
        f = seg.split("@")
        if len(f) < 8:
            continue
        slots = [x for x in f[3].split(",") if x]
        if not slots:
            continue
        try:
            day = int(slots[0][0])
            periods = sorted(int(x[1:]) for x in slots)
        except ValueError:
            continue
        out.append({
            "weeks": f[0], "weeks_list": sorted(_parse_weeks(f[1] or f[0])),
            "day": day, "periods": periods, "room": f[4],
            "start": f"{f[5][:-2] or '0'}:{f[5][-2:]}",
            "end": f"{f[6][:-2] or '0'}:{f[6][-2:]}",
            "campus": f[8] if len(f) > 8 else "",
            "building": f[10] if len(f) > 10 else "",
        })
    return out


def fetch(jw):
    """返回 (ctx, courses, nopass)。无进行中的选课活动抛 ApiError。"""
    act = jw.post(f"{XK}/findXsxkjdList", f"{CC}.findXsxkjdList",
                  {"page": {"pageIndex": 1, "pageSize": 0, "orderBy": ""}})
    items = (act.get("resRmd") or {}).get("items") or []
    if not items:
        raise ApiError("当前没有进行中的选课活动")
    a = items[0]
    ctx = {"jczy013id": a["jczy013id"], "xkgl017id": a["xkgl017id"], "xkgl019id": a["id"],
           "hd_name": a["hd_name"], "xnxq": a["xnxq_name"],
           "xkkssj": a["xkkssj"], "xkjssj": a["xkjssj"], "now": a["checkTime"]}

    ent = jw.post(f"{XK}/findZxxkByEntry", f"{CC}.findZxxkByEntry",
                  {"resCode": "XSMH0303", "language": "zh",
                   **{k: ctx[k] for k in ("jczy013id", "xkgl017id", "xkgl019id")}})
    ctx["name"] = ent.get("xs_name") or ""
    ctx["sid"] = ent.get("xsxh") or ""
    ctx["major"] = ((ent.get("bllsList") or [{}])[0]).get("name", "")
    ctx["mode"] = (ent.get("xkkzMap") or {}).get("trfs_name", "")
    ctx["ctrl"] = (ent.get("xkkzMap") or {}).get("xtkz_name", "")

    periods = []
    for m in (ent.get("kbSj") or []):
        for d in (m.get("pkgl00201list") or []):
            subs = [int(x) for x in (d.get("zyxjs") or "").split(",") if x.strip()]
            if subs:
                periods.append({"name": d.get("djname1"), "start": d.get("djkssj"),
                                "end": d.get("djjssj"), "subs": subs})
        if periods:
            break
    ctx["periods"] = sorted(periods, key=lambda p: p["subs"][0])

    res = jw.post(f"{XK}/findXkResList", f"{CC}.findXkResList",
                  {**{k: ctx[k] for k in ("jczy013id", "xkgl017id", "xkgl019id")},
                   "page": {"pageIndex": 1, "pageSize": 0, "orderBy": ""}})

    courses = [{
        "name": c.get("kcmc_name") or "?",
        "class_name": c.get("ktmc_name") or "",
        "teacher": c.get("skls_name") or "",
        "category": c.get("kclb_name") or "",
        "kclbcode": str(c.get("kclbcode") or ""),
        "dept": c.get("kkdw_name") or "",
        "credit": float(c.get("zxf") or 0),
        "pref": int(c.get("xkzy_name") or 0),
        "status": c.get("xkzt_name") or "",
        "code": c.get("kcbh") or "",
        "slots": parse_kbinfo(c.get("kbinfo")),
    } for c in (res.get("kcCahe") or [])]

    # 单选类别（ms==1，如公共体育）：里面多个志愿是二选一，不算冲突
    ctx["single_select"] = fetch_single_select_cats(jw, ctx)
    return ctx, courses, res.get("noPassKcCache") or []


def fetch_single_select_cats(jw, ctx) -> set:
    """
    返回「只选 1 门」的类别码集合（findXsxkjdByOne 里 ms==1 的类别）。
    这些类别下的多个志愿是互斥备选（如公共体育的养生/健美），不应判为时间冲突。
    """
    try:
        d = jw.post(f"{XK}/findXsxkjdByOne", f"{CC}.findXsxkjdByOne",
                    {"jczy013id": ctx["jczy013id"], "xkgl017id": ctx["xkgl017id"],
                     "id": ctx["xkgl019id"]})
    except ApiError:
        return set()
    m = d.get("xfyqMap") or d.get("xfyqNoXnxq") or {}
    single = set()
    for lst in (m.get("xkgl011011List") or []):
        for c in (lst.get("xkgl011021List") or []):
            if _int(c.get("ms")) == 1:
                single.add(str(c.get("kclbcode")))
    return single


def sig(c):
    return tuple(sorted((s["day"], tuple(s["periods"])) for s in c["slots"]))


def group(courses, single_select=None):
    """
    志愿归并，志愿号最小者为主。返回 (first, alts, ghosts)。
    归并键：
      · 普通类别：按课程名（同一门课的多个平行班 -> 一组备选）
      · 单选类别(ms==1，如公共体育)：按类别码（养生/健美等不同名课也归为一组备选，
        因为只选 1 门，互斥不冲突）
    first 的键统一用展示名，避免不同键指向同一门课。
    """
    single_select = single_select or set()
    g = defaultdict(list)
    for c in courses:
        code = c.get("kclbcode") or ""
        key = f"cat:{code}" if code in single_select else f"name:{c['name']}"
        g[key].append(c)

    first, alts, ghosts = {}, {}, []
    for key, l in g.items():
        head = min(l, key=lambda c: c["pref"] or 99)
        name = head["name"]
        first[name] = head
        alts[name] = sorted((c for c in l if c is not head), key=lambda c: c["pref"] or 99)
        head["n_pref"] = len(l)
        head["same_time"] = len({sig(c) for c in l}) == 1
        ghosts += [c for c in alts[name] if sig(c) != sig(head)]
    return first, alts, ghosts


def conflicts(first):
    """照搬教务 kcjcct 的判定：同星期 + 节次时间相交 + 周次相交 + 不同课，才算冲突。
    教务原逻辑是「待选课 vs 已选课」，这里用于预选课表的第一志愿互查（提醒若都选上会撞）。
    - 同一门课多老师/多重叠时段会在同格出现多次，但课不自冲突（按课名去重）。
    - 志愿池互斥：单选类别(ms=1)已在 group() 处理；跨课志愿池数据未抓，暂不判。
    - 周次不相交（如 1-8 周 vs 9-16 周）不算冲突；缺周次数据则保守判冲突。
    """
    occ = defaultdict(list)   # (星期,节次) -> [(课名, 周次集合)]
    for n, c in first.items():
        for s in c["slots"]:
            ws = set(s.get("weeks_list") or [])
            for p in s["periods"]:
                occ[(s["day"], p)].append((n, ws))
    out = []
    for (d, p), entries in sorted(occ.items()):
        clash = set()
        for i in range(len(entries)):
            ni, wi = entries[i]
            for j in range(i + 1, len(entries)):
                nj, wj = entries[j]
                if ni == nj:
                    continue                          # 同课不自冲突
                if (not wi) or (not wj) or (wi & wj):  # 周次相交（缺数据则保守）
                    clash.add(ni)
                    clash.add(nj)
        if len(clash) > 1:
            out.append((d, p, sorted(clash)))
    return out


def build_payload(ctx, courses):
    """组装成前端好渲染的结构（供 API 返回）"""
    first, alts, ghosts = group(courses, ctx.get("single_select"))
    gset = {id(g) for g in ghosts}

    out = []
    for n in sorted(first):
        c = first[n]
        out.append({
            "name": n,
            "category": c["category"],
            "cat_class": CAT_CLASS.get(c["category"], "misc"),
            "credit": c["credit"],
            "dept": c["dept"],
            "n_pref": c["n_pref"],
            "same_time": c["same_time"],
            "primary": {
                "pref": c["pref"], "class_name": c["class_name"], "teacher": c["teacher"],
                "slots": c["slots"], "is_ghost": False,
            },
            "alts": [{
                "pref": a["pref"], "class_name": a["class_name"], "teacher": a["teacher"],
                "slots": a["slots"], "is_ghost": id(a) in gset,
            } for a in alts[n]],
        })

    cf = [{"day": d, "period": p, "names": names} for d, p, names in conflicts(first)]
    return {
        "context": {k: ctx[k] for k in
                    ("name", "sid", "major", "hd_name", "xnxq", "mode", "ctrl",
                     "xkkssj", "xkjssj", "now", "periods")},
        "courses": out,
        "conflicts": cf,
        "total_credit": sum(c["credit"] for c in first.values()),
        "n_courses": len(first),
        "n_prefs": len(courses),
    }


# ======================= 抢课用只读函数 =======================
# 全部只调查询接口。提交(saveStuXkByRmdx)不在本文件，单独隔离。

def _int(v):
    try:
        return int(v)
    except (TypeError, ValueError):
        return None


# 「已选上/通过」的选课状态码。来自选课结果页 JS：退课按钮仅在这些状态出现，
# 即真正选到手的课。110=待筛选(志愿未筛)，不算已选。
PASSED_CODES = {"1", "111", "211", "311"}


def is_passed(c) -> bool:
    """该选课记录是否为「通过/已选上」（区别于待筛选、未通过）"""
    code = str(c.get("xkztcode") or "")
    name = c.get("xkzt_name") or ""
    if code in PASSED_CODES:
        return True
    return ("通过" in name) or ("已选" in name)   # 名称兜底


_ALL_WEEKS = tuple(range(1, 26))


def slot_cells(slots):
    """课程时间 -> {(星期, 节次, 周次)} 三元组集合，用于冲突比对。
    对齐教务：冲突要求周次也相交，故把周次也纳入格子；缺周次数据时保守覆盖全学期。"""
    cells = set()
    for s in slots:
        weeks = s.get("weeks_list") or _ALL_WEEKS
        for p in s["periods"]:
            for w in weeks:
                cells.add((s["day"], p, w))
    return cells


def fetch_grab_context(jw):
    """
    抢课上下文（只读）：选课活动、专业id、模式判据、当前已选课占用的时间格。
      mode_code: xkcscode12 —— "0"=时间优先(即选即得,抢课有效) / "1"=志愿(筛选制)
    无进行中的选课活动抛 ApiError。
    """
    act = jw.post(f"{XK}/findXsxkjdList", f"{CC}.findXsxkjdList",
                  {"page": {"pageIndex": 1, "pageSize": 0, "orderBy": ""}})
    items = (act.get("resRmd") or {}).get("items") or []
    if not items:
        raise ApiError("当前没有进行中的选课活动")
    a = items[0]
    ctx = {"jczy013id": a["jczy013id"], "xkgl017id": a["xkgl017id"], "xkgl019id": a["id"],
           "hd_name": a["hd_name"], "xnxq": a["xnxq_name"],
           "xkkssj": a["xkkssj"], "xkjssj": a["xkjssj"], "now": a["checkTime"]}

    ent = jw.post(f"{XK}/findZxxkByEntry", f"{CC}.findZxxkByEntry",
                  {"resCode": "XSMH0303", "language": "zh",
                   **{k: ctx[k] for k in ("jczy013id", "xkgl017id", "xkgl019id")}})
    km = ent.get("xkkzMap") or {}
    ctx["name"] = ent.get("xs_name") or ""
    ctx["sid"] = ent.get("xsxh") or ""
    ctx["major"] = ((ent.get("bllsList") or [{}])[0]).get("name", "")
    ctx["bllsZyId"] = ((ent.get("bllsList") or [{}])[0]).get("jczy005id") or ""
    ctx["xklbbh"] = str(((ent.get("showXklbList") or [{}])[0]).get("xkgl003id") or "16")
    ctx["mode_code"] = str(km.get("xkcscode12"))
    ctx["mode"] = km.get("trfs_name") or ""
    ctx["ctrl"] = km.get("xtkz_name") or ""
    # 提交(saveStuXkByRmdx)所需的活动级字段，逆向自选课页 basicSet 的 payload
    ctx["xkcscode7"] = str(km.get("xkcscode7") or "0")
    ctx["xkcscode23"] = str(km.get("xkcscode23") or "0")
    ctx["xkfs_name"] = km.get("xkfs_name") or ""
    ctx["xkfscode"] = str(km.get("xkfscode") or "")   # -> 提交里的 xkfsid
    ctx["km_xkgl017id"] = km.get("xkgl017id") or ctx["xkgl017id"]
    ctx["isTqxd"] = ent.get("isTqxd")
    ctx["language"] = ent.get("language") or ""

    periods = []
    for m in (ent.get("kbSj") or []):
        for d in (m.get("pkgl00201list") or []):
            subs = [int(x) for x in (d.get("zyxjs") or "").split(",") if x.strip()]
            if subs:
                periods.append({"name": d.get("djname1"), "start": d.get("djkssj"),
                                "end": d.get("djjssj"), "subs": subs})
        if periods:
            break
    ctx["periods"] = sorted(periods, key=lambda p: p["subs"][0])

    # 已选课 = 选课状态为「通过」的课（待筛选的志愿不算，因为可能没选上，下阶段还要抢）。
    # 冲突检测只跟这些真已选的课比。
    enrolled = fetch_enrolled_from_reslist(
        jw.post(f"{XK}/findXkResList", f"{CC}.findXkResList",
                {**{k: ctx[k] for k in ("jczy013id", "xkgl017id", "xkgl019id")},
                 "page": {"pageIndex": 1, "pageSize": 0, "orderBy": ""}}))
    held_cells = set()
    for c in enrolled:
        held_cells |= slot_cells(c["slots"])
    ctx["held_cells"] = held_cells
    ctx["held_names"] = [c["name"] for c in enrolled]
    ctx["enrolled"] = enrolled
    return ctx


def fetch_enrolled_from_reslist(res) -> list:
    """从 findXkResList 结果里提取「已选上/通过」的课（含解析后的时间）。"""
    out = []
    for c in (res.get("kcCahe") or []):
        if not is_passed(c):
            continue
        out.append({
            "name": c.get("kcmc_name") or "?",
            "class_name": c.get("ktmc_name") or "",
            "teacher": c.get("skls_name") or "",
            "category": c.get("kclb_name") or "",
            "dept": c.get("kkdw_name") or "",
            "credit": float(c.get("zxf") or 0),
            "pref": 1,
            "status": c.get("xkzt_name") or "已选",
            "code": c.get("kcbh") or "",
            "slots": parse_kbinfo(c.get("kbinfo")),
        })
    return out


def fetch_enrolled(jw):
    """
    已选课程表数据（只读）：只含选课状态为「通过」的课。
    志愿阶段尚未筛选时通常为空 —— 这是正确的，那些志愿还不算已选。
    """
    ctx = fetch_grab_context(jw)
    courses = ctx.get("enrolled") or []
    return ctx, courses


# 拉课程池时可透传的子类别参数（不同一级类别用不同维度切分）
POOL_PARAM_KEYS = ("xxklbcode", "honerItemId", "kkdwid", "isSxrz")


def fetch_categories(jw, ctx):
    """
    课程类别列表（有课的）+ 子类别，供前端浏览课程池。只读。

    子类别分三种维度（放在 sub['params'] 里，拉课程池时原样透传）：
      · 通识核心课/一般通识课: kclbMap 给出「科学与技术」等 -> {xxklbcode}
      · 跨学科专业选修·双选认证: 按开课学院切 -> {kkdwid, isSxrz:'0'}
      · 跨学科专业选修·荣誉选课: 按荣誉辅修项目切 -> {honerItemId}
    不切分会把不同子类别混在一起，或（跨学科）直接拉不到课。
    """
    d = jw.post(f"{XK}/findXsxkjdByOne", f"{CC}.findXsxkjdByOne",
                {"jczy013id": ctx["jczy013id"], "xkgl017id": ctx["xkgl017id"],
                 "id": ctx["xkgl019id"]})
    m = d.get("xfyqMap") or d.get("xfyqNoXnxq") or {}
    lst = [e for e in (m.get("xkgl011011List") or []) if str(e.get("xklbbh")) == ctx["xklbbh"]]
    cats = (lst[0].get("xkgl011021List") if lst else []) or []
    kclb_map = d.get("kclbMap") or {}
    sx_kkwd = d.get("sx_kkwdList") or []   # ["113700,数学学院", ...] 双选认证的开课学院

    out = []
    for c in cats:
        if not (_int(c.get("ms")) and str(c.get("sfxkcode")) != "0"):
            continue
        code = str(c.get("kclbcode"))
        name = c.get("kclb_name") or ""
        subs = []

        # A) kclbMap 二级子类别（通识核心课 / 一般通识课）
        for s in (kclb_map.get(code) or []):
            if s.get("xxklbcode"):
                subs.append({"name": s.get("xxklb_name") or "", "group": "子类别",
                             "params": {"xxklbcode": s["xxklbcode"]}})

        # B) 跨学科专业选修 —— 双选认证(按学院) + 荣誉选课(按项目)
        if name.strip() == "跨学科专业选修":
            for it in sx_kkwd:
                parts = it.split(",", 1) if isinstance(it, str) else []
                if len(parts) == 2:
                    subs.append({"name": parts[1], "group": "双选认证·按学院",
                                 "params": {"kkdwid": parts[0], "isSxrz": "0"}})
            try:
                honors = jw.post(f"{XK}/findHonerItemByRy", f"{CC}.findHonerItemByRy",
                                 {"xkgl019id": ctx["xkgl019id"], "jczy013id": ctx["jczy013id"]})
                for h in (honors or []):
                    if h.get("id"):
                        subs.append({"name": h.get("item_name") or "", "group": "荣誉选课",
                                     "params": {"honerItemId": h["id"]}})
            except ApiError:
                pass

        out.append({"kclbcode": code, "name": name,
                    "count": _int(c.get("ms")) or 0, "subs": subs})
    return out


def fetch_pool(jw, ctx, kclbcode, params=None):
    """某类别（可选子类别 params）的可选课程池（带余额）。只读。"""
    body = {
        "jczy013id": ctx["jczy013id"], "xkfl": [], "xklbbh": ctx["xklbbh"],
        "xkgl017id": ctx["xkgl017id"], "xkgl019id": ctx["xkgl019id"],
        "bllsZyId": ctx["bllsZyId"], "kclbCodeMapper": str(kclbcode),
        "page": {"pageIndex": 1, "pageSize": 0, "orderBy": ""},
    }
    for k in POOL_PARAM_KEYS:            # 透传子类别维度参数
        v = (params or {}).get(k)
        if v not in (None, ""):
            body[k] = v
    d = jw.post(f"{XK}/findKcInfoByflByRmdx", f"{CC}.findKcInfoByflByRmdx", body)
    sfjc = d.get("sfjcxskbcode")          # 提交里的 xkcscode1（该池统一）
    out = []
    for c in (d.get("showKclist") or []):
        cap = _int(c.get("xxrs"))          # 限选人数(容量)
        enrolled = _int(c.get("xkrs"))     # 已选人数
        slots = parse_kbinfo(c.get("kbinfo"))
        out.append({
            "course_key": c.get("kth") or c.get("id") or "",
            "kclbcode": str(c.get("kclbcode") or kclbcode),
            "name": c.get("kcmc_name") or "",
            "class_name": c.get("ktmc_name") or "",
            "teacher": c.get("skls_name") or "",
            "credit": float(c.get("zxf") or 0),
            "dept": c.get("kkdw_name") or "",
            "cap": cap,
            "enrolled": enrolled,
            # 时间优先阶段 surplus 才有意义；志愿阶段 enrolled 可远超 cap
            "surplus": (cap - enrolled) if (cap is not None and enrolled is not None) else None,
            "slots": slots,
            "raw": c,
            "sfjcxskbcode": sfjc,
            "pool_params": params or {},
        })
    return out


def _numstr(v):
    """对齐前端 a.zxs.toString()：整数值去掉 .0（32.0 -> '32'，2.5 -> '2.5'）。"""
    if v in (None, ""):
        return ""
    try:
        f = float(v)
        return str(int(f)) if f == int(f) else str(f)
    except (TypeError, ValueError):
        return str(v)


def _sksj_from_kbinfo(s):
    """把 kbinfo 还原成提交体里的 sksj 数组，完全照搬选课页 analystsURL 的构造：
    每段 '@' 分隔，[0]周次显示 [1]周次明细 [2]星期(1位)+节次 [5]开始 [6]结束。"""
    week_cn = {1: "星期一", 2: "星期二", 3: "星期三", 4: "星期四",
               5: "星期五", 6: "星期六", 7: "星期日"}
    out = []
    for seg in (s or "").split("~"):
        seg = seg.strip()
        if not seg:
            continue
        e = seg.split("@")
        if len(e) < 3:
            continue
        zc, zcmx = e[0], (e[1] if len(e) > 1 else "")
        xq, jc = e[2][:1], e[2][1:]
        if not (zc and xq and jc):
            continue
        kssj = int(e[5]) if len(e) > 5 and e[5].isdigit() else ""
        jssj = int(e[6]) if len(e) > 6 and e[6].isdigit() else ""
        try:
            wname = week_cn.get(int(xq), "")
        except ValueError:
            wname = ""
        name = f"{wname} {jc[:2]}-{jc[-2:]}节 {zc}周"
        out.append({"zc": zc, "zcmx": zcmx, "kssj": kssj, "jssj": jssj,
                    "xq": xq, "jc": jc, "name": name})
    return out


def submit_course(jw, ctx, course):
    """时间优先阶段提交选课（saveStuXkByRmdx）。仅由抢课服务在护栏内调用。

    提交体逐字段对齐选课页 JS 的 basicSet -> saveStuXk(i)：约 50 字段，来源分三处 ——
      · 课程行(raw)：kkdwbh/tzdlb_name/kkdw_name/skls_name/kkdwid/kcbh/ktmc_name/…/kbinfo→sksj
      · 活动(ctx，取自 xkkzMap/entry)：xkcscode7/23、xkfs_name、xkfsid、isTqxd、xkgl017id
      · 课程池响应：sfjcxskbcode -> xkcscode1
    单次请求、不重试；本函数只选不退（saveStuTxByRmdx 全项目不写）。返回 (ok, msg)。"""
    raw = course.get("raw") or {}
    if not raw.get("id"):
        return False, "缺教学班 id，跳过提交"
    params = course.get("pool_params") or {}
    kclb_mapper = str(raw.get("kclbMapper") or raw.get("kclbcode")
                      or course.get("kclbcode") or "")
    body = {
        "xkcscode7": ctx.get("xkcscode7"),
        "kkdwbh": raw.get("kkdwbh"),
        "xkfl": [],
        "tzdlb_name": raw.get("tzdlb_name"),
        "xkfs_name": ctx.get("xkfs_name"),
        "kkdw_name": raw.get("kkdw_name"),
        "skls_name": raw.get("skls_name"),
        "jczy007ids": raw.get("jczy007ids"),
        "jczy003id": raw.get("kkdwid"),
        "kcbh": raw.get("kcbh"),
        "ktmc_name": raw.get("ktmc_name"),
        "kcxz_name": raw.get("kcxz_name"),
        "kcmc_name": raw.get("kcmc_name"),
        "kcxz": raw.get("kcxzcode"),
        "xq_name": raw.get("xq_name"),
        "id": raw.get("id"),
        "jczy013id": ctx.get("jczy013id"),
        "zxs": _numstr(raw.get("zxs")),
        "zxf": _numstr(raw.get("zxf")),
        "kcdl": raw.get("kcdlcode"),
        "kclb": raw.get("kclbcode"),
        "khfs": raw.get("khfscode"),
        "kkgl00401id": raw.get("xnkkgl00401id"),
        "szkclb": raw.get("szkclbcode"),
        "falb": "1",
        "xkfsid": ctx.get("xkfscode"),
        "xkgl017id": raw.get("xkgl017id") or ctx.get("km_xkgl017id") or ctx.get("xkgl017id"),
        "xkgl019id": ctx.get("xkgl019id"),
        "isTqxd": ctx.get("isTqxd"),
        "xkzy": "",
        "trz": "",
        "tzdlb": raw.get("tzdlbcode"),
        "jczy010id": raw.get("jczy010id"),
        "skfscode": raw.get("skfscode"),
        "skfs_name": raw.get("skfs_name"),
        "sksj": _sksj_from_kbinfo(raw.get("kbinfo")),
        "xkcscode1": str(course.get("sfjcxskbcode") if course.get("sfjcxskbcode") is not None else "1"),
        "xkcscode23": ctx.get("xkcscode23"),
        "sfglymkccode": False,
        "sfglctkccode": False,
        "kclbMapper": kclb_mapper,
        "xklbbh": ctx.get("xklbbh"),
        "bllsZyId": ctx.get("bllsZyId"),
        "isSxrz": params.get("isSxrz") or "",
        "language": ctx.get("language") or "",
        "xxklbcode": params.get("xxklbcode") or raw.get("xxklbcode") or "",
    }
    # 特殊课程类型字段：仅当课程行里确有该键才带（对齐前端 JSON 丢弃 undefined 的行为）
    for k in ("yyBfb", "yyjf", "pyfa01201id", "zc"):
        if k in raw:
            body[k] = raw.get(k)
    if params.get("honerItemId"):
        body["honerItemId"] = params["honerItemId"]

    try:
        ok, msg = jw.write(f"{XK}/saveStuXkByRmdx", f"{CC}.saveStuXkByRmdx", body)
    except Exception as e:
        return False, f"提交异常: {str(e)[:60]}"
    return ok, (msg or ("提交成功" if ok else "提交被拒"))


def find_in_pool(pool, course_key):
    for c in pool:
        if c["course_key"] == course_key:
            return c
    return None
