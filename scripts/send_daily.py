#!/usr/bin/env python3
"""send_daily.py — 发送每日雅思词汇 HTML 邮件

读取 ~/.ielts-buddy/email.json 里的 SMTP 配置（不在仓库里存任何凭据），
用 ielts_buddy 的 EmailService 现场生成当天邮件并发送。

用法:
    python3 scripts/send_daily.py
    python3 scripts/send_daily.py --count 20
    python3 scripts/send_daily.py --dry-run     # 只生成 HTML，不发送
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from ielts_buddy.services.email_service import EmailService, load_email_config  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="发送每日雅思词汇邮件")
    parser.add_argument("-n", "--count", type=int, default=20, help="推送词数（默认 20）")
    parser.add_argument("--dry-run", action="store_true", help="只生成 HTML，不发送")
    args = parser.parse_args()

    service = EmailService()
    print("[send] 正在生成邮件内容…")
    html = service.generate_daily_email(word_count=args.count)
    print(f"[send] HTML 已生成，{len(html)} 字符")

    if args.dry_run:
        out = Path.home() / ".ielts-buddy" / "email_preview.html"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(html, encoding="utf-8")
        print(f"[send] dry-run：已写入 {out}")
        return 0

    try:
        config = load_email_config()
    except FileNotFoundError as error:
        print(f"[send] ❌ {error}", file=sys.stderr)
        return 1

    print("[send] 正在发送…")
    service.send_email(html, config)
    print("[send] ✅ 发送成功")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
