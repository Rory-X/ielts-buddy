"""邮件服务：生成每日学习报告 HTML 邮件并发送"""

from __future__ import annotations

import json
import smtplib
from datetime import date, datetime, timedelta
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from ielts_buddy.core.config import get_app_dir
from ielts_buddy.services.review_service import ReviewService
from ielts_buddy.services.stats_service import StatsService
from ielts_buddy.services.vocab_service import VocabService


def _template_dir() -> Path:
    """获取模板目录"""
    return Path(__file__).parent.parent / "templates"


def _round_pct(value: float) -> str:
    """将 0.0~1.0 的浮点数格式化为百分比字符串"""
    return f"{value * 100:.0f}%"


def _get_email_config_path() -> Path:
    """邮件配置文件路径 ~/.ib/email.json"""
    return get_app_dir() / "email.json"


def load_email_config() -> dict:
    """加载邮件配置

    配置文件格式 (~/.ib/email.json):
    {
        "smtp_host": "smtp.example.com",
        "smtp_port": 465,
        "smtp_ssl": true,
        "username": "user@example.com",
        "password": "app_password",
        "from_addr": "user@example.com",
        "to_addr": "user@example.com",
        "subject_prefix": "[IELTS Buddy]"
    }
    """
    config_path = _get_email_config_path()
    if not config_path.exists():
        raise FileNotFoundError(
            f"邮件配置文件不存在: {config_path}\n"
            f"请创建配置文件，格式参考: ib email preview --help"
        )
    return json.loads(config_path.read_text(encoding="utf-8"))


class EmailService:
    """每日邮件服务"""

    def __init__(self, template_dir: Path | None = None) -> None:
        tpl_dir = template_dir or _template_dir()
        self._env = Environment(
            loader=FileSystemLoader(str(tpl_dir)),
            autoescape=True,
        )
        self._env.filters["round_pct"] = _round_pct

    def _gather_data(self) -> dict:
        """收集邮件所需的全部数据"""
        today = date.today()

        # 统计数据
        stats_svc = StatsService()
        try:
            total = stats_svc.total_stats()
            today_stats = stats_svc.today_stats()
            due_count = stats_svc.due_count()
            current_streak, max_streak = stats_svc.get_streak()
            band_progress = stats_svc.get_band_progress()

            # 获取昨日数据（近似：用 get_history 取最近2天）
            history = stats_svc.get_history(days=2)
            if len(history) >= 2:
                yesterday_data = history[0]  # 倒数第二天
            else:
                yesterday_data = {"new_words": 0, "reviewed_words": 0}
        finally:
            stats_svc.close()

        # 待复习单词
        review_svc = ReviewService()
        try:
            due_items = review_svc.get_due_words(limit=10)
            due_words = []
            for item in due_items:
                w = item["word_data"]
                r = item["record"]
                due_words.append({
                    "word": w.word,
                    "phonetic": w.phonetic,
                    "meaning": w.meaning,
                    "memory_level": r.memory_level,
                })
        finally:
            review_svc.close()

        # 推荐新词（随机抽取未学过的词）
        vocab_svc = VocabService()
        vocab_svc.load_all()
        recommended = vocab_svc.random_words(count=5)
        recommended_words = [
            {"word": w.word, "phonetic": w.phonetic, "meaning": w.meaning, "band": w.band}
            for w in recommended
        ]

        return {
            "date": today.isoformat(),
            "yesterday": yesterday_data,
            "total": total,
            "streak": {"current": current_streak, "max": max_streak},
            "due_words": due_words,
            "recommended_words": recommended_words,
            "band_progress": [
                {"band": b, "total": t, "mastered": m, "ratio": r}
                for b, t, m, r in band_progress
            ],
        }

    def generate_daily_email(self, data: dict | None = None) -> str:
        """生成每日邮件 HTML 内容

        Args:
            data: 可选，自定义数据（测试用）。为 None 时自动收集数据。

        Returns:
            HTML 字符串
        """
        if data is None:
            data = self._gather_data()
        template = self._env.get_template("daily_email.html")
        return template.render(**data)

    def send_email(self, html_content: str, config: dict | None = None) -> None:
        """发送 HTML 邮件

        Args:
            html_content: 邮件 HTML 内容
            config: 邮件配置，为 None 时从配置文件加载
        """
        if config is None:
            config = load_email_config()

        subject_prefix = config.get("subject_prefix", "[IELTS Buddy]")
        subject = f"{subject_prefix} {date.today().isoformat()} 每日学习报告"

        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = config["from_addr"]
        msg["To"] = config["to_addr"]
        msg.attach(MIMEText(html_content, "html", "utf-8"))

        smtp_port = config.get("smtp_port", 465)
        smtp_ssl = config.get("smtp_ssl", True)

        if smtp_ssl:
            server = smtplib.SMTP_SSL(config["smtp_host"], smtp_port)
        else:
            server = smtplib.SMTP(config["smtp_host"], smtp_port)
            server.starttls()

        try:
            server.login(config["username"], config["password"])
            server.sendmail(config["from_addr"], [config["to_addr"]], msg.as_string())
        finally:
            server.quit()
