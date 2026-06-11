#!/usr/bin/env python3
"""
send_daily.py — 发送预构建好的每日雅思词汇 HTML 邮件

在 9:00 精确运行，读取提前构建好的 HTML 文件直接发出。
如果 HTML 文件不存在（8:50 预构建失败），则现场构建一个。

用法:
    python3 scripts/send_daily.py
    python3 scripts/send_daily.py --date 2026-05-11
"""

import argparse
import os
import sys
import smtplib
import subprocess
from datetime import date, datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
sys.path.insert(0, PROJECT_ROOT)

# 邮件配置
SMTP_HOST = "smtp.qq.com"
SMTP_PORT = 465
SMTP_USER = "2673157458@qq.com"
SMTP_PASS = "akuwtdbpjidrdjci"
MAIL_TO   = "2109764731@qq.com"

START_DATE = date(2026, 4, 12)


def compute_day_num(target_date: date) -> int:
    return (target_date - START_DATE).days + 1


def send_email(subject: str, html_content: str) -> None:
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"]    = SMTP_USER
    msg["To"]      = MAIL_TO
    msg.attach(MIMEText(html_content, "html", "utf-8"))

    import ssl
    ctx = ssl.create_default_context()
    with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT, context=ctx) as server:
        server.login(SMTP_USER, SMTP_PASS)
        server.sendmail(SMTP_USER, [MAIL_TO], msg.as_string())


def main():
    parser = argparse.ArgumentParser(description="发送每日雅思词汇邮件")
    parser.add_argument("--date", default=None, help="目标日期 YYYY-MM-DD，默认今天")
    args = parser.parse_args()

    if args.date:
        target_date = datetime.strptime(args.date, "%Y-%m-%d").date()
    else:
        target_date = date.today()

    date_str   = target_date.strftime("%Y-%m-%d")
    day_num    = compute_day_num(target_date)
    html_path  = os.path.join(PROJECT_ROOT, f"{date_str}.html")

    # 如果文件不存在，说明预构建没跑，立即补建
    if not os.path.exists(html_path):
        print(f"[send] ⚠️  预构建文件不存在，立即现场构建: {html_path}")
        result = subprocess.run(
            [sys.executable, os.path.join(SCRIPT_DIR, "prebuild_daily.py"), "--date", date_str],
            capture_output=True, text=True
        )
        print(result.stdout)
        if result.returncode != 0:
            print(f"[send] ❌ 现场构建失败:\n{result.stderr}", file=sys.stderr)
            sys.exit(1)

    with open(html_path, "r", encoding="utf-8") as f:
        html_content = f.read()

    subject = f"📚 每日雅思词汇 · Day {day_num} · 20词推送"
    print(f"[send] 发送邮件: {subject} → {MAIL_TO}")

    send_email(subject, html_content)
    print(f"[send] ✅ 邮件发送成功！")


if __name__ == "__main__":
    main()
