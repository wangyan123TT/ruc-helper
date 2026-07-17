#!/usr/bin/env python3
"""
待筛选课程表 — HTML 渲染（命令行版 xk_timetable.py 与独立网页版 xk_web.py 共用）

数据逻辑在 backend/app/services/xk.py（放那儿是因为后端 Docker 只 COPY app/）。
成绩监控 App 的前端用 Vue 自己渲染，不走这里。
"""
import os
import sys
from html import escape as E

_SVC = os.path.join(os.path.dirname(os.path.abspath(__file__)), "backend", "app", "services")
if _SVC not in sys.path:
    sys.path.insert(0, _SVC)

from xk import CAT_CLASS, WEEK, sig  # noqa: E402

CSS = """
:root {
  --paper:#fdfdfe; --panel:#fff; --ink:#151c26; --ink-2:#3d4757;
  --muted:#78838f; --rule:#e2e7ed; --rule-2:#eef1f5; --shade:#f5f7f9;
  --pol:#b03a2e; --core:#1a5fa0; --elec:#0d7361;
  --gen:#8a5a2b; --lang:#66459b; --pe:#4a7c2f; --misc:#5a6472;
  --tint:10%; --glow:0 1px 2px rgba(21,28,38,.05);
}
@media (prefers-color-scheme:dark) {
  :root {
    --paper:#0e1319; --panel:#151b23; --ink:#e8edf3; --ink-2:#b3bdc9;
    --muted:#7d8896; --rule:#252e39; --rule-2:#1c242d; --shade:#131920;
    --pol:#e8776a; --core:#6aa9e8; --elec:#4bc0a8;
    --gen:#d3a06a; --lang:#a98ada; --pe:#8ec46a; --misc:#8e98a6;
    --tint:16%; --glow:0 1px 2px rgba(0,0,0,.3);
  }
}
*{box-sizing:border-box}
body {
  margin:0; padding:28px 20px 56px; background:var(--paper); color:var(--ink);
  font:15px/1.55 -apple-system,BlinkMacSystemFont,"PingFang SC","Hiragino Sans GB",
       "Microsoft YaHei","Source Han Sans SC",sans-serif;
  -webkit-font-smoothing:antialiased;
}
.num {font-variant-numeric:tabular-nums;
  font-family:ui-monospace,"SF Mono",Menlo,Consolas,"PingFang SC",monospace}
.wrap {max-width:1120px; margin:0 auto; display:flex; flex-direction:column; gap:20px}
.top {display:flex; flex-direction:column; gap:6px}
.eyebrow {font-size:11px; letter-spacing:.14em; text-transform:uppercase;
  color:var(--muted); font-weight:600}
h1 {margin:0; font-size:27px; font-weight:750; letter-spacing:-.02em; text-wrap:balance}
h1 small {font-weight:450; color:var(--muted); font-size:15px; letter-spacing:0; margin-left:9px}
.who {color:var(--ink-2); font-size:13.5px; margin:0}
.who b {font-weight:600; color:var(--ink)}
.stats {display:flex; flex-wrap:wrap; background:var(--panel); border:1px solid var(--rule);
  border-radius:11px; overflow:hidden; box-shadow:var(--glow)}
.st {flex:1 1 116px; padding:11px 15px; border-right:1px solid var(--rule-2);
  display:flex; flex-direction:column; gap:1px}
.st:last-child {border-right:0}
.st b {font-size:20px; font-weight:700; letter-spacing:-.01em}
.st span {font-size:11px; color:var(--muted); letter-spacing:.03em}
.st.live b {color:var(--pol)}
.legend {display:flex; gap:7px; flex-wrap:wrap; align-items:center}
.legend .lb {font-size:11.5px; color:var(--muted); margin-right:2px}
.lg {font-size:11.5px; padding:2.5px 9px; border-radius:20px; font-weight:550; border:1px solid;
  color:var(--c); border-color:color-mix(in srgb,var(--c) 32%,transparent);
  background:color-mix(in srgb,var(--c) var(--tint),transparent)}
.pol{--c:var(--pol)} .core{--c:var(--core)} .elec{--c:var(--elec)}
.gen{--c:var(--gen)} .lang{--c:var(--lang)} .pe{--c:var(--pe)} .misc{--c:var(--misc)}
.scroll {overflow-x:auto; border:1px solid var(--rule); border-radius:11px;
  background:var(--panel); box-shadow:var(--glow)}
table {width:100%; min-width:660px; border-collapse:collapse; table-layout:fixed}
caption {caption-side:top; text-align:left; padding:11px 14px 9px; font-size:12.5px;
  color:var(--muted); border-bottom:1px solid var(--rule-2)}
thead th {background:var(--shade); padding:8px; font-size:12.5px; font-weight:650;
  border-bottom:1px solid var(--rule); border-right:1px solid var(--rule-2); color:var(--ink-2)}
thead th:last-child {border-right:0}
td,tbody th {border-right:1px solid var(--rule-2); border-bottom:1px solid var(--rule-2);
  vertical-align:top}
td:last-child,tbody th:last-child {border-right:0}
.ph {width:46px; background:var(--shade); text-align:center; padding:5px 2px}
.pn {display:block; font-size:11.5px; color:var(--muted); font-weight:600;
  font-variant-numeric:tabular-nums}
.pt {display:block; font-size:9.5px; color:var(--muted); opacity:.62;
  font-family:ui-monospace,Menlo,monospace}
.empty {height:33px}
.slot {padding:7px 8px; background:color-mix(in srgb,var(--c) var(--tint),var(--panel));
  border-left:3px solid var(--c)}
.cn {display:block; font-weight:650; color:var(--c); font-size:12.5px; line-height:1.32;
  margin-bottom:3px; text-wrap:balance}
.meta {display:block; font-size:10.5px; color:var(--muted); line-height:1.42}
.badges {display:flex; gap:4px; align-items:center; margin-top:4px; flex-wrap:wrap}
.pref {font-size:9.5px; font-weight:650; background:var(--c); color:var(--panel);
  padding:1px 5px; border-radius:3px; letter-spacing:.02em}
.vs {font-size:9.5px; color:var(--muted)}
.slot.ghost {background:repeating-linear-gradient(135deg,transparent 0 6px,
  color-mix(in srgb,var(--c) 7%,transparent) 6px 12px);
  border-left:3px dashed var(--c); opacity:.9}
.ghost .cn {font-weight:550}
.gh {display:block; font-size:9.5px; font-weight:650; color:var(--c); letter-spacing:.02em;
  margin-bottom:2px; opacity:.85}
h2 {margin:6px 0 0; font-size:16px; font-weight:700; letter-spacing:-.01em}
.sub {font-size:12.5px; color:var(--muted); margin:2px 0 0}
.cards {display:grid; grid-template-columns:repeat(auto-fill,minmax(268px,1fr)); gap:10px}
.card {background:var(--panel); border:1px solid var(--rule); border-left:3px solid var(--c);
  border-radius:9px; padding:11px 13px; box-shadow:var(--glow)}
.card header {display:flex; align-items:baseline; justify-content:space-between; gap:8px}
.card h3 {margin:0; font-size:13.5px; font-weight:650; color:var(--c); text-wrap:balance}
.cr {font-size:11px; color:var(--muted); flex-shrink:0}
.cr::after {content:" 学分"}
.ct {margin:2px 0 7px; font-size:10.5px; color:var(--muted)}
.card ol {margin:0; padding:0; list-style:none; display:flex; flex-direction:column; gap:3px}
.card li {display:flex; gap:6px; align-items:baseline; font-size:11px; color:var(--ink-2);
  flex-wrap:wrap}
.card li b {font-size:9.5px; font-weight:650; color:var(--c);
  background:color-mix(in srgb,var(--c) var(--tint),transparent);
  padding:1px 4px; border-radius:3px; flex-shrink:0}
.cls {flex:1; min-width:0}
.tc,.rm {color:var(--muted); font-size:10px}
.card li.diff em {flex-basis:100%; font-style:normal; font-size:10px; color:var(--pol);
  font-weight:600}
.card li.diff em::before {content:"↳ 时间不同 · "; font-weight:450}
.note {background:var(--panel); border:1px solid var(--rule); border-radius:9px;
  padding:12px 14px; font-size:12.5px; color:var(--ink-2); line-height:1.62}
.note b {color:var(--ink)}
.note code {font-family:ui-monospace,Menlo,monospace; font-size:11.5px;
  background:var(--shade); padding:1px 4px; border-radius:3px}
.stamp {margin-top:6px; font-size:11px; color:var(--muted)}
@media (max-width:640px) {
  body {padding:16px 12px 40px}
  h1 {font-size:22px}
  h1 small {display:block; margin:2px 0 0}
}
"""


def render_body(ctx, first, alts, ghosts, back_link=False):
    days = [1, 2, 3, 4, 5]
    starts, covered = {}, set()
    for c in first.values():
        for s in c["slots"]:
            ps = s["periods"]
            starts[(s["day"], ps[0])] = (c, s, len(ps), False)
            covered.update((s["day"], k) for k in ps[1:])
    for c in ghosts:
        for s in c["slots"]:
            ps = s["periods"]
            if (s["day"], ps[0]) in starts:
                continue
            starts[(s["day"], ps[0])] = (c, s, len(ps), True)
            covered.update((s["day"], k) for k in ps[1:])

    maxp = max([p for _, p in starts] + [p for _, p in covered] + [1])
    pmap = {sub: b for b in ctx["periods"] for sub in b["subs"]}

    rows = ""
    for p in range(1, maxp + 1):
        b = pmap.get(p)
        head = f'<span class="pn">{p}</span>'
        if b and b["subs"][0] == p:
            head += f'<span class="pt">{E(b["start"])}</span>'
        rows += f'<tr><th class="ph" scope="row">{head}</th>'
        for day in days:
            if (day, p) in covered:
                continue
            cell = starts.get((day, p))
            if not cell:
                rows += '<td class="empty"></td>'
                continue
            c, s, span, ghost = cell
            cls = CAT_CLASS.get(c["category"], "misc")
            if ghost:
                rows += (f'<td rowspan="{span}" class="slot ghost {cls}">'
                         f'<span class="gh">志愿{c["pref"]} · 备选落点</span>'
                         f'<span class="cn">{E(c["name"])}</span>'
                         f'<span class="meta">{E(s["room"])} · {E(c["teacher"][:14])}</span>'
                         f'<span class="meta num">{E(s["start"])}–{E(s["end"])}</span></td>')
            else:
                n_alt = len(alts[c["name"]])
                badge = (f'<span class="pref">志愿{c["pref"]}</span>'
                         f'<span class="vs">/{n_alt + 1}班竞争</span>') if n_alt else ""
                rows += (f'<td rowspan="{span}" class="slot {cls}">'
                         f'<span class="cn">{E(c["name"])}</span>'
                         f'<span class="meta">{E(s["room"])}</span>'
                         f'<span class="meta">{E(c["teacher"][:14])}</span>'
                         f'<span class="meta num">{E(s["start"])}–{E(s["end"])}</span>'
                         f'<span class="badges">{badge}</span></td>')
        rows += "</tr>"

    order = list(CAT_CLASS)
    used = sorted({c["category"] for c in first.values()},
                  key=lambda x: order.index(x) if x in order else 99)
    legend = "".join(f'<span class="lg {CAT_CLASS.get(k, "misc")}">{E(k)}</span>' for k in used)

    cards = ""
    for n in sorted(first, key=lambda x: (-first[x]["credit"], x)):
        c = first[n]
        cls = CAT_CLASS.get(c["category"], "misc")
        li = ""
        for x in [c] + alts[n]:
            diff = sig(x) != sig(c)
            t = " / ".join(f"周{WEEK[s['day'] - 1]}{min(s['periods'])}–{max(s['periods'])}节"
                           for s in x["slots"])
            li += (f'<li{" class=\"diff\"" if diff else ""}><b>志愿{x["pref"]}</b>'
                   f'<span class="cls">{E(x["class_name"])}</span>'
                   f'<span class="tc">{E(x["teacher"][:20])}</span>'
                   f'<span class="rm num">{E(x["slots"][0]["room"]) if x["slots"] else "—"}</span>'
                   + (f'<em class="num">{E(t)}</em>' if diff else "") + "</li>")
        cards += (f'<article class="card {cls}"><header><h3>{E(n)}</h3>'
                  f'<span class="cr num">{c["credit"]:g}</span></header>'
                  f'<p class="ct">{E(c["category"])} · {E(c["dept"])}</p>'
                  f'<ol>{li}</ol></article>')

    total = sum(c["credit"] for c in first.values())
    npref = sum(c["n_pref"] for c in first.values())
    gnames = "、".join(sorted({g["name"] for g in ghosts}))
    gnote = (f'<b>其中{E(gnames)}</b>的各志愿上课时间完全不同，图中已用虚线块标出备选落点。'
             if ghosts else '所有课程的平行班时间都一致，筛选结果不会改变课表布局。')
    back = ('<p class="sub"><a href="/" style="color:var(--muted)">← 查询其他账号</a></p>'
            if back_link else '')

    return f"""<div class="wrap">
  <div class="top">
    <span class="eyebrow">RUC · 选课中心 · 进入选课</span>
    <h1>待筛选课程表<small>{E(ctx['hd_name'])}</small></h1>
    <p class="who"><b>{E(ctx['name'])}</b> · {E(ctx['sid'])} · {E(ctx['major'])}</p>
    {back}
  </div>
  <div class="stats">
    <div class="st"><b class="num">{len(first)}</b><span>门课</span></div>
    <div class="st"><b class="num">{npref}</b><span>个志愿</span></div>
    <div class="st"><b class="num">{total:g}</b><span>学分</span></div>
    <div class="st"><b>{E(ctx['mode'])}制</b><span>{E(ctx['ctrl'])}</span></div>
    <div class="st live"><b class="num" id="cd">—</b><span>距选课截止 {E(ctx['xkjssj'])}</span></div>
  </div>
  <div class="legend"><span class="lb">课程类别</span>{legend}</div>
  <div class="scroll"><table>
    <caption>按<b>第一志愿</b>排布 · 虚线块 = 备选志愿的另一个落点</caption>
    <thead><tr><th class="ph">节</th>{''.join(f'<th>周{WEEK[x-1]}</th>' for x in days)}</tr></thead>
    <tbody>{rows}</tbody>
  </table></div>
  <div>
    <h2>志愿明细</h2>
    <p class="sub">同一门课报多个平行班 = 多个志愿，筛选后每门只会中一个</p>
  </div>
  <div class="cards">{cards}</div>
  <div class="note">
    <b>这是志愿，不是结果。</b>全部 {npref} 个志愿状态均为「待筛选」——志愿制下人人可报，
    超额由系统筛选。课表按第一志愿排布：平行班上课时间通常相同，所以筛上哪个班一般不改变格子位置。
    {gnote}
    <div class="stamp">数据抓取于 {E(ctx['now'])} · 选课窗口 {E(ctx['xkkssj'])} – {E(ctx['xkjssj'])}
      · 来源 <code>findXkResList → kcCahe</code></div>
  </div>
</div>
<script>
(function () {{
  var end = new Date("{ctx['xkjssj'].replace('-', '/')}").getTime(),
      el = document.getElementById("cd");
  function tick() {{
    var ms = end - Date.now();
    if (ms <= 0) {{ el.textContent = "已截止"; return; }}
    var d = Math.floor(ms / 864e5), h = Math.floor(ms / 36e5) % 24, m = Math.floor(ms / 6e4) % 60;
    el.textContent = (d > 0 ? d + "天" : "") + h + "时" + m + "分";
  }}
  tick(); setInterval(tick, 3e4);
}})();
</script>"""


def render_page(ctx, first, alts, ghosts, back_link=False):
    return (f'<!doctype html>\n<html lang="zh-CN"><head><meta charset="utf-8">\n'
            f'<meta name="viewport" content="width=device-width,initial-scale=1">\n'
            f'<title>待筛选课程表 · {E(ctx["xnxq"])}</title>\n<style>{CSS}</style></head><body>\n'
            + render_body(ctx, first, alts, ghosts, back_link)
            + "\n</body></html>\n")
