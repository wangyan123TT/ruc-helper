#!/usr/bin/env python3
"""
微人大选课 — 待筛选课程课程表（命令行版，只查 .env 里配的那个账号）

多用户网页版见项目根目录的 xk_web.py。
核心逻辑在 xk_core.py，两者共用。

【只读】只调查询类接口，不会改动任何选课状态。

用法:
  python3 cli/xk_timetable.py                  # 终端摘要 + 生成 timetable.html
  python3 cli/xk_timetable.py --json out.json  # 另存原始数据
  python3 cli/xk_timetable.py --no-html        # 只看终端摘要，不落盘

注意: 生成的 timetable.html 含姓名/学号，已在 .gitignore 中。
"""
import argparse
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)                                        # xk_render
sys.path.insert(0, os.path.join(ROOT, "backend", "app", "services"))  # xk

from xk import (WEEK, ApiError, Jw, LoginError, conflicts,  # noqa: E402
                fetch, group)
from xk_render import render_page  # noqa: E402


def load_env_creds(root):
    """从 .env 读凭据"""
    env = {}
    path = os.path.join(root, ".env")
    if os.path.exists(path):
        for line in open(path, encoding="utf-8"):
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                env[k.strip()] = v.strip().strip('"').strip("'")
    sid, pwd = env.get("RUC_STUDENT_ID"), env.get("RUC_PASSWORD")
    if not sid or not pwd:
        import getpass
        print("[.env 未配置凭据，手动输入 — 密码不回显]")
        sid = sid or input("学号: ").strip()
        pwd = pwd or getpass.getpass("密码: ")
    return sid, pwd


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", help="另存原始数据到指定文件")
    ap.add_argument("--html", default=os.path.join(ROOT, "timetable.html"), help="网页输出路径")
    ap.add_argument("--no-html", action="store_true", help="不生成 HTML")
    args = ap.parse_args()

    sid, pwd = load_env_creds(ROOT)
    print(f"[1/3] 登录 {sid} ...")
    try:
        jw = Jw(sid, pwd)
    except LoginError as e:
        sys.exit(f"[!] {e}")
    del pwd

    print("[2/3] 抓取选课活动 + 待筛选课程 ...")
    try:
        ctx, courses, nopass = fetch(jw)
    except ApiError as e:
        sys.exit(f"[!] {e}")

    if not courses:
        sys.exit("[!] 当前选课活动里没有「待筛选」的志愿课程")

    print(f"[3/3] 解析 {len(courses)} 个志愿 ...")
    first, alts, ghosts = group(courses)
    cf = conflicts(first)

    print("\n" + "=" * 62)
    print(f"  {ctx['name']} / {ctx['sid']}   {ctx['major']}")
    print(f"  {ctx['hd_name']}")
    print(f"  {ctx['mode']}制 ({ctx['ctrl']})   选课窗口: {ctx['xkkssj']} ~ {ctx['xkjssj']}")
    print(f"  服务器时间: {ctx['now']}")
    print("=" * 62)

    total = sum(c["credit"] for c in first.values())
    print(f"\n待筛选: {len(first)} 门课 / {len(courses)} 个志愿 / {total:g} 学分"
          + (f"   未通过: {len(nopass)} 门" if nopass else ""))

    for n, c in sorted(first.items(),
                       key=lambda kv: (kv[1]["slots"][0]["day"], kv[1]["slots"][0]["periods"][0])
                       if kv[1]["slots"] else (9, 9)):
        ts = " + ".join(f"周{WEEK[s['day'] - 1]}{min(s['periods'])}-{max(s['periods'])}节"
                        for s in c["slots"])
        npf = f"({c['n_pref']}个志愿)" if c["n_pref"] > 1 else ""
        warn = "" if c["same_time"] else "  ⚠平行班时间不一致"
        room = c["slots"][0]["room"] if c["slots"] else ""
        print(f"  {n:<24} {c['credit']:g}学分  {ts:<24} {room:<10} "
              f"{c['teacher'][:12]:<14} 志愿{c['pref']}{npf}{warn}")

    if cf:
        print(f"\n⚠ 第一志愿存在 {len(cf)} 处时间冲突:")
        for day, p, names in cf:
            print(f"    周{WEEK[day - 1]}第{p}节: {' × '.join(names)}")
    else:
        print("\n✓ 第一志愿课程之间无时间冲突")

    if args.json:
        with open(args.json, "w", encoding="utf-8") as f:
            json.dump({"context": ctx, "courses": courses, "nopass_count": len(nopass)},
                      f, ensure_ascii=False, indent=2)
        print(f"\n原始数据 -> {args.json}")

    if not args.no_html:
        with open(args.html, "w", encoding="utf-8") as f:
            f.write(render_page(ctx, first, alts, ghosts))
        print(f"课程表 -> {args.html}  (含姓名学号，已 gitignore)")


if __name__ == "__main__":
    main()
