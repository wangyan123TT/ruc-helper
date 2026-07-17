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
            "weeks": f[0], "day": day, "periods": periods, "room": f[4],
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
        "dept": c.get("kkdw_name") or "",
        "credit": float(c.get("zxf") or 0),
        "pref": int(c.get("xkzy_name") or 0),
        "status": c.get("xkzt_name") or "",
        "code": c.get("kcbh") or "",
        "slots": parse_kbinfo(c.get("kbinfo")),
    } for c in (res.get("kcCahe") or [])]

    return ctx, courses, res.get("noPassKcCache") or []


def sig(c):
    return tuple(sorted((s["day"], tuple(s["periods"])) for s in c["slots"]))


def group(courses):
    """同名课程归并，志愿号最小者为主。返回 (first, alts, ghosts)"""
    g = defaultdict(list)
    for c in courses:
        g[c["name"]].append(c)
    first = {n: min(l, key=lambda c: c["pref"] or 99) for n, l in g.items()}
    alts, ghosts = {}, []
    for n, l in g.items():
        alts[n] = sorted((c for c in l if c is not first[n]), key=lambda c: c["pref"] or 99)
        first[n]["n_pref"] = len(l)
        first[n]["same_time"] = len({sig(c) for c in l}) == 1
        # 时间与第一志愿不同的备选班 -> 课表上画"备选落点"
        ghosts += [c for c in alts[n] if sig(c) != sig(first[n])]
    return first, alts, ghosts


def conflicts(first):
    occ = defaultdict(list)
    for n, c in first.items():
        for s in c["slots"]:
            for p in s["periods"]:
                occ[(s["day"], p)].append(n)
    return [(d, p, names) for (d, p), names in sorted(occ.items()) if len(names) > 1]


def build_payload(ctx, courses):
    """组装成前端好渲染的结构（供 API 返回）"""
    first, alts, ghosts = group(courses)
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
