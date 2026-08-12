"""
通用通知通道 —— 与「发什么」解耦，谁都能复用。

分三层：
  send_html(to, subject, html)          纯 SMTP 发送机制
  render_email(kicker,title,...,body)   品牌化邮件外壳（朱砂头 + 印章 + 页脚），email 安全
  各业务自己拼 body → 套 render_email → send_html

成绩通知在 grade.send_grade_email。抢课通知（抢到/有名额/冲突）用 send_grab_email，
以后抢课系统接上就能直接发，不用再碰 SMTP 细节 —— 这就是「可拓展」的落点。

注意：邮件客户端对 CSS 支持很差，一律用 table 布局 + 内联样式 + 十六进制色，
不用 flex/grid/CSS 变量。传统色沿用 app：朱砂 #c41e3a / 玉 #1a7a5a / 金 #b8860b。
"""
from datetime import datetime

INK = "#1a1a2e"
INK_DIM = "#8b8ba8"
PAPER = "#f0eee9"
LINE = "#eceaf1"
CINNABAR = "#c41e3a"
JADE = "#1a7a5a"
GOLD = "#b8860b"
APP_URL = "http://49.233.204.197:8080/"


def send_html(to_address: str, subject: str, html: str) -> bool:
    """纯发送机制。SMTP 配置从 grade.EMAIL_CONFIG 现取（惰性导入避免循环依赖）。"""
    import smtplib
    from email.mime.text import MIMEText
    from email.header import Header
    from email.utils import formataddr
    from .grade import EMAIL_CONFIG

    if not EMAIL_CONFIG.get("smtpUsername"):
        print("[email] 未配置 SMTP，跳过发送")
        return False
    if not to_address:
        print("[email] 无收件邮箱")
        return False
    try:
        msg = MIMEText(html, "html", "utf-8")
        msg["From"] = formataddr((str(Header("选课助手", "utf-8")), EMAIL_CONFIG["fromAddress"]))
        msg["To"] = to_address
        msg["Subject"] = str(Header(subject, "utf-8"))
        server = smtplib.SMTP(EMAIL_CONFIG["smtpHost"], int(EMAIL_CONFIG["smtpPort"]), timeout=15)
        server.starttls()
        server.login(EMAIL_CONFIG["smtpUsername"], EMAIL_CONFIG["smtpPassword"])
        server.sendmail(EMAIL_CONFIG["fromAddress"], [to_address], msg.as_string())
        server.quit()
        print(f"[email] 已发送至 {to_address}")
        return True
    except Exception as e:
        print(f"[email] 发送失败: {e}")
        return False


def score_color(score) -> str:
    """分数分档着色，跟前端一致：90+ 玉 / 85-89 墨 / <85 金。"""
    try:
        n = float(score)
    except (TypeError, ValueError):
        return INK
    return JADE if n >= 90 else (INK if n >= 85 else GOLD)


def pill(text: str, color: str = CINNABAR) -> str:
    bg = _tint(color)
    return (f"<span style=\"display:inline-block;padding:4px 12px;border-radius:20px;"
            f"background:{bg};color:{color};font-size:12px;font-weight:600;margin:0 6px 6px 0\">{text}</span>")


def section(title: str, inner: str, accent: str = CINNABAR) -> str:
    """一个带竖条标题的内容块。"""
    return (f"<div style=\"margin:22px 0 0\">"
            f"<div style=\"font-size:14px;font-weight:600;color:{INK};margin:0 0 12px;"
            f"border-left:3px solid {accent};padding-left:9px\">{title}</div>{inner}</div>")


def _tint(hex_color: str) -> str:
    """把强调色淡化成浅底（近似前端的 -light）。"""
    return {CINNABAR: "#fde8ec", JADE: "#e6f4ef", GOLD: "#fef7e6"}.get(hex_color, "#f4f2f7")


def render_email(*, kicker: str, title: str, intro: str = "", body: str = "",
                 accent: str = CINNABAR, footer_note: str = "") -> str:
    """品牌化邮件外壳。body 由各业务自己拼好传入。"""
    footer_note = footer_note or "选课助手自动发送 · 回复本邮件无效"
    return f"""<!doctype html><html><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width"></head>
<body style="margin:0;padding:0;background:{PAPER};font-family:-apple-system,BlinkMacSystemFont,'Segoe UI','Noto Sans SC',sans-serif;">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:{PAPER}"><tr>
<td align="center" style="padding:26px 12px">
  <table role="presentation" width="600" cellpadding="0" cellspacing="0"
         style="max-width:600px;width:100%;background:#ffffff;border-radius:14px;overflow:hidden;box-shadow:0 4px 18px rgba(15,15,35,.08)">
    <!-- 头band：朱砂 + 印章 -->
    <tr><td style="background:{accent};padding:20px 26px">
      <table role="presentation" cellpadding="0" cellspacing="0"><tr>
        <td style="width:36px;height:36px;background:rgba(255,255,255,.16);border:1px solid rgba(255,255,255,.45);
                   border-radius:7px;text-align:center;vertical-align:middle;color:#fff;font-size:18px;font-weight:700">选</td>
        <td style="padding-left:12px;vertical-align:middle">
          <div style="color:#fff;font-size:15px;font-weight:600;letter-spacing:.5px">选课助手</div>
          <div style="color:rgba(255,255,255,.78);font-size:11px;letter-spacing:1px">微人大 · RUC</div>
        </td>
      </tr></table>
    </td></tr>
    <!-- 标题 -->
    <tr><td style="padding:26px 28px 0">
      <div style="font-size:11px;letter-spacing:2px;text-transform:uppercase;color:{accent};font-weight:700">{kicker}</div>
      <div style="margin:7px 0 0;font-size:22px;font-weight:700;color:{INK};line-height:1.25">{title}</div>
      {f'<div style="margin:7px 0 0;color:{INK_DIM};font-size:13px">{intro}</div>' if intro else ''}
    </td></tr>
    <!-- 正文 -->
    <tr><td style="padding:8px 28px 6px">{body}</td></tr>
    <!-- 页脚 -->
    <tr><td style="padding:18px 28px 26px;border-top:1px solid {LINE}">
      <a href="{APP_URL}" style="display:inline-block;font-size:12px;color:{accent};text-decoration:none;font-weight:600">打开选课助手 →</a>
      <div style="margin:8px 0 0;font-size:11px;color:#b8b8cc">{footer_note}</div>
    </td></tr>
  </table>
  <div style="margin:14px 0 0;font-size:11px;color:#b8b8cc">RUC · 选课助手</div>
</td></tr></table></body></html>"""


def send_grab_email(to_address: str, student_name: str, event: str,
                    course_name: str, detail: str = "") -> bool:
    """抢课通知（预留给抢课系统，已可用）。event: 'success' 抢到 / 'ready' 有名额 / 'conflict' 冲突。"""
    meta = {
        "success": ("抢课成功", f"已抢到「{course_name}」", JADE),
        "ready": ("出现名额", f"「{course_name}」有名额了", GOLD),
        "conflict": ("时间冲突", f"「{course_name}」与已选课冲突，已停止", CINNABAR),
        "failed": ("抢课异常", f"「{course_name}」有名额却提交失败，已停止", CINNABAR),
    }.get(event, ("抢课通知", course_name, CINNABAR))
    kicker, title, accent = meta
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    body = (f"<div style='font-size:14px;color:{INK};line-height:1.7'>{detail or ''}</div>"
            f"<div style='margin:14px 0 0;font-size:12px;color:{INK_DIM}'>{student_name} · {now}</div>")
    html = render_email(kicker=kicker, title=title, body=body, accent=accent,
                        footer_note="抢课状态变动通知 · 选课助手自动发送")
    return send_html(to_address, f"选课助手 · {kicker}：{course_name}", html)
