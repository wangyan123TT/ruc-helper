#!/usr/bin/env python3
"""
微人大待筛选课程表 — 网页版（多用户，每人查自己的）

设计原则:
  1. 【不存密码】密码只在处理这一次请求时存在于内存，用完即弃。
     不写文件、不进数据库、不写日志。服务器被攻破也偷不到密码。
  2. 【只读】只调教务查询接口，绝不改动任何人的选课状态。
  3. 【无会话】不发 cookie、不留登录态。关掉页面就什么都不剩。

零依赖，只用 Python 标准库 + requests。

用法:
  python3 xk_web.py                 # 监听 127.0.0.1:8090
  python3 xk_web.py --port 8090
  python3 xk_web.py --host 0.0.0.0  # 对外开放（务必先读下面的警告）

⚠️ 对外开放前必读:
  - 必须套 HTTPS。明文 HTTP 传密码，同网络的人可以直接抓到。
  - 你在收集同学的统一身份认证密码。这是很重的信任，出事你担责。
  - 先确认学校 IT 规定是否允许。
"""
import argparse
import html
import os
import sys
import threading
import time
import urllib.parse
from collections import defaultdict, deque
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(ROOT, "backend", "app", "services"))

from xk import ApiError, Jw, LoginError, fetch, group  # noqa: E402
from xk_render import CSS, render_body  # noqa: E402

# ---------- 限流：防止本服务被当成撞库跳板 ----------
RATE_WINDOW = 300      # 5 分钟
RATE_MAX = 10          # 每 IP 最多 10 次登录尝试
_hits = defaultdict(deque)
_lock = threading.Lock()


def rate_ok(ip):
    now = time.time()
    with _lock:
        q = _hits[ip]
        while q and now - q[0] > RATE_WINDOW:
            q.popleft()
        if len(q) >= RATE_MAX:
            return False
        q.append(now)
        return True


LOGIN_CSS = CSS + """
.login {max-width:420px; margin:8vh auto; display:flex; flex-direction:column; gap:18px}
.card-box {background:var(--panel); border:1px solid var(--rule); border-radius:12px;
  padding:22px 24px; box-shadow:var(--glow)}
form {display:flex; flex-direction:column; gap:13px}
label {display:flex; flex-direction:column; gap:5px; font-size:12.5px; color:var(--ink-2);
  font-weight:600}
input {padding:9px 11px; font-size:15px; border:1px solid var(--rule); border-radius:7px;
  background:var(--paper); color:var(--ink); font-family:inherit}
input:focus {outline:2px solid var(--core); outline-offset:1px; border-color:transparent}
button {padding:10px; font-size:14.5px; font-weight:650; background:var(--core);
  color:#fff; border:0; border-radius:7px; cursor:pointer; font-family:inherit;
  margin-top:3px}
button:hover {filter:brightness(1.08)}
button:disabled {opacity:.55; cursor:progress}
.err {background:color-mix(in srgb,var(--pol) 12%,transparent);
  border:1px solid color-mix(in srgb,var(--pol) 35%,transparent); color:var(--pol);
  border-radius:7px; padding:9px 11px; font-size:12.5px; font-weight:600}
.disc {font-size:11.5px; color:var(--muted); line-height:1.65}
.disc b {color:var(--ink-2)}
.disc ul {margin:6px 0 0; padding-left:17px}
.disc li {margin:2px 0}
.brand {text-align:center}
.brand h1 {font-size:22px}
.brand p {margin:5px 0 0; font-size:12.5px; color:var(--muted)}
"""


def page(title, body, css=CSS):
    return (f'<!doctype html>\n<html lang="zh-CN"><head><meta charset="utf-8">\n'
            f'<meta name="viewport" content="width=device-width,initial-scale=1">\n'
            f'<title>{html.escape(title)}</title>\n<style>{css}</style></head><body>\n'
            f'{body}\n</body></html>\n')


def login_page(error=""):
    err = f'<div class="err">{html.escape(error)}</div>' if error else ""
    return page("待筛选课程表 · 登录", f"""<div class="login">
  <div class="brand">
    <h1>待筛选课程表</h1>
    <p>把「选课中心 → 进入选课」里的志愿课程，排成一张课表</p>
  </div>
  <div class="card-box">
    <form method="post" action="/" autocomplete="off">
      {err}
      <label>学号
        <input name="sid" inputmode="numeric" required autofocus
               autocomplete="username" placeholder="10 位学号">
      </label>
      <label>微人大密码
        <input name="pwd" type="password" required autocomplete="current-password">
      </label>
      <button type="submit">查询我的待筛选课表</button>
    </form>
  </div>
  <div class="card-box disc">
    <b>关于你的密码，说明白：</b>
    <ul>
      <li>本站<b>不保存</b>你的密码——只用它登录教务系统一次，拿到课表就丢掉。
          不写文件、不进数据库、不写进任何日志。</li>
      <li>本站<b>不改动</b>你的选课。只读，一个字都不会改。</li>
      <li>不发 cookie、不留登录态，关掉页面什么都不剩。</li>
      <li>服务器日志只记录访问时间和 IP，<b>不记录你是谁、查了什么课</b>。</li>
    </ul>
    <b style="display:block;margin-top:9px">但你仍然应该谨慎：</b>
    <ul>
      <li>这是<b>同学自己搭的工具，不是学校官方网站</b>。</li>
      <li>你输的是统一身份认证密码，邮箱、VPN 都是这一套。</li>
      <li>不放心就别用——这很合理。你也可以要源码自己跑一份。</li>
    </ul>
  </div>
</div>
<script>
document.querySelector("form").addEventListener("submit", function (e) {{
  var b = e.target.querySelector("button");
  b.disabled = true; b.textContent = "登录教务系统中…（约需 5 秒）";
}});
</script>""", LOGIN_CSS)


class Handler(BaseHTTPRequestHandler):
    server_version = "xk-timetable"

    def log_message(self, fmt, *args):
        # 只记方法和路径，绝不记 body（body 里有密码）
        print(f"  [{self.address_string()}] {fmt % args}")

    def _send(self, code, body, ctype="text/html; charset=utf-8"):
        data = body.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")   # 别让浏览器/代理缓存别人的课表
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        if self.path.split("?")[0] != "/":
            self._send(404, page("404", '<div class="login"><div class="card-box">'
                                        '页面不存在。<a href="/">返回</a></div></div>', LOGIN_CSS))
            return
        self._send(200, login_page())

    def do_POST(self):
        if self.path.split("?")[0] != "/":
            self._send(404, login_page("页面不存在"))
            return

        ip = self.address_string()
        if not rate_ok(ip):
            self._send(429, login_page("尝试太频繁，请 5 分钟后再试。"))
            return

        try:
            n = int(self.headers.get("Content-Length") or 0)
        except ValueError:
            n = 0
        if n <= 0 or n > 4096:
            self._send(400, login_page("请求无效。"))
            return

        form = urllib.parse.parse_qs(self.rfile.read(n).decode("utf-8", "replace"))
        sid = (form.get("sid") or [""])[0].strip()
        pwd = (form.get("pwd") or [""])[0]
        if not sid or not pwd:
            self._send(400, login_page("学号和密码都要填。"))
            return

        try:
            jw = Jw(sid, pwd)          # 密码只在这里用一次
        except LoginError as e:
            self._send(200, login_page(f"登录失败：{e}"))
            return
        finally:
            pwd = None                 # 立刻解除引用

        try:
            ctx, courses, _ = fetch(jw)
        except ApiError as e:
            self._send(200, login_page(f"抓取失败：{e}"))
            return
        except Exception as e:
            self._send(200, login_page(f"出错了：{e}"))
            return

        if not courses:
            self._send(200, login_page(
                "这个账号在当前选课活动里没有「待筛选」的志愿课程——"
                "可能还没报，也可能筛选已经结束了。"))
            return

        first, alts, ghosts = group(courses)
        self._send(200, page(f"待筛选课程表 · {ctx['xnxq']}",
                             render_body(ctx, first, alts, ghosts, back_link=True)))
        # 只记成功与否，不记是谁 —— 「谁查过课表」本身也是隐私
        print(f"  [{ip}] 查询成功 ({len(first)}门)")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8090)
    ap.add_argument("--host", default="127.0.0.1",
                    help="默认只监听本机。设 0.0.0.0 对外开放（先读文件顶部警告）")
    args = ap.parse_args()

    ThreadingHTTPServer.allow_reuse_address = True
    srv = ThreadingHTTPServer((args.host, args.port), Handler)
    print("=" * 64)
    print(f"  待筛选课程表 网页版  ->  http://localhost:{args.port}")
    print(f"  监听 {args.host}:{args.port}")
    if args.host != "127.0.0.1":
        print("  ⚠ 已对外开放：务必套 HTTPS，明文传密码非常危险")
    else:
        print("  仅本机可访问。VSCode 会自动转发端口到你的电脑。")
    print(f"  限流: 每 IP {RATE_MAX} 次 / {RATE_WINDOW // 60} 分钟")
    print("  密码不保存、不记日志。Ctrl+C 停止。")
    print("=" * 64)
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("\n已停止。")
        srv.server_close()


if __name__ == "__main__":
    main()
