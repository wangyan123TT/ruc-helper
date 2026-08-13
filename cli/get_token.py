#!/usr/bin/env python3
"""
人大教务系统 — 通过账号密码获取 Token

调用 /secService/login 登录，获取 JWT + SESSION 后自动写入 config.json，
供 auto_grade.py 使用。

用法:
    uv run get_token.py
    python get_token.py
"""
import json
import requests
import sys
import os
from datetime import datetime, timezone, timedelta

sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]

TZ = timezone(timedelta(hours=8))
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(SCRIPT_DIR)
CONFIG_FILE = os.path.join(ROOT_DIR, "config.json")

LOGIN_URL = "https://jw.ruc.edu.cn/secService/login"

LOGIN_HEADERS = {
    "Content-Type": "application/json",
    "Accept": "application/json",
    "KAPTCHA-KEY-GENERATOR-REDIS": "securityKaptchaRedisServiceAdapter",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
}


def ts():
    return datetime.now(TZ).strftime("%H:%M:%S")


def load_config():
    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_config(cfg):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)
    print(f"  [{ts()}] 已写入 {CONFIG_FILE}")


def do_login(username: str, password: str):
    """执行登录，返回 (token, session_cookie) 或 None"""
    payload = {
        "userCode": username,
        "password": password,
        "kaptcha": "testa",
        "userCodeType": "ldap",
    }

    resp = requests.post(LOGIN_URL, json=payload, headers=LOGIN_HEADERS, timeout=15)
    data = resp.json()

    if data.get("errorCode") != "success":
        print(f"  [{ts()}] 登录失败: {data.get('errorMessage', '未知错误')}")
        return None

    token = data["data"]["token"]
    session_cookie = resp.cookies.get("SESSION")
    authcode = data["data"].get("authcode", username)

    print(f"  [{ts()}] 登录成功! 账号: {authcode}")
    return token, session_cookie, authcode


def main():
    cfg = load_config()

    print("=" * 50)
    print("人大教务系统 — Token 获取工具")
    print(f"{datetime.now(TZ).strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 50)

    username = input("学号: ").strip()
    if not username:
        print("学号不能为空")
        return

    password = input("密码: ").strip()
    if not password:
        print("密码不能为空")
        return

    result = do_login(username, password)
    if not result:
        return

    token, session_cookie, authcode = result

    cfg["auth"]["resToken"] = token
    cfg["auth"]["session"] = session_cookie
    cfg["auth"]["authcode"] = authcode
    cfg["student"]["id"] = authcode

    save_config(cfg)
    print(f"  [{ts()}] resToken / session / authcode 已写入 config.json")
    print(f"  [{ts()}] 可运行 auto_grade.py（成绩查询）")


if __name__ == "__main__":
    main()
