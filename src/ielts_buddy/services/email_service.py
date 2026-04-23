"""邮件服务：生成每日词汇推送 HTML 邮件并发送"""

from __future__ import annotations

import json
import smtplib
from datetime import date
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from ielts_buddy.core.config import get_app_dir
from ielts_buddy.services.stats_service import StatsService
from ielts_buddy.services.vocab_service import VocabService


def _template_dir() -> Path:
    """获取模板目录"""
    return Path(__file__).parent.parent / "templates"


def _round_pct(value: float) -> str:
    """将 0.0~1.0 的浮点数格式化为百分比字符串"""
    return f"{value * 100:.0f}%"


# Band 元信息
_BAND_LABELS = {
    5: "基础词汇",
    6: "进阶词汇",
    7: "核心词汇",
    8: "高阶词汇",
    9: "精英词汇",
}


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

    def _gather_data(self, word_count: int = 20) -> dict:
        """收集词汇推送邮件所需的全部数据

        Args:
            word_count: 今日推送单词数量，默认 20
        """
        today = date.today()

        # 获取累计天数和累计词汇数
        stats_svc = StatsService()
        try:
            total_stats = stats_svc.total_stats()
            day_num = total_stats.get("total_days", 1)
            cumulative_words = total_stats.get("total_words", 0)
            # 如果今天刚开始，累计天数至少为 1
            if day_num == 0:
                day_num = 1
        except Exception:
            day_num = 1
            cumulative_words = 0
        finally:
            stats_svc.close()

        # 随机抽取今日词汇（按 Band 分布抽取）
        vocab_svc = VocabService()
        vocab_svc.load_master()

        # 按 Band 比例分配：5(15%), 6(25%), 7(15%), 8(35%), 9(10%)
        band_ratios = {5: 0.15, 6: 0.25, 7: 0.15, 8: 0.35, 9: 0.10}
        band_counts = {}
        allocated = 0
        for band, ratio in band_ratios.items():
            cnt = max(0, round(word_count * ratio))
            band_counts[band] = cnt
            allocated += cnt
        # 补齐到 word_count（多余分给 Band 8）
        diff = word_count - allocated
        band_counts[8] = band_counts.get(8, 0) + diff

        word_groups = []
        for band in sorted(band_counts.keys()):
            cnt = band_counts[band]
            if cnt <= 0:
                continue
            words = vocab_svc.random_words(cnt, band)
            if not words:
                continue
            word_groups.append({
                "band": band,
                "label": _BAND_LABELS.get(band, ""),
                "words": [
                    {
                        "word": w.word,
                        "phonetic": w.phonetic,
                        "pos": w.pos,
                        "meaning": w.meaning,
                        "topic": w.topic,
                        "example": w.example,
                    }
                    for w in words
                ],
            })

        # 统计实际推送词数
        total_words = sum(len(g["words"]) for g in word_groups)
        cumulative_words += total_words

        # 生成学习建议
        high_band_words = [
            w["word"]
            for g in word_groups if g["band"] >= 8
            for w in g["words"]
        ][:3]
        if high_band_words:
            tip_words = "、".join(f"<strong style='color:{'#f97316' if i == 0 else '#ef4444'};'>{w}</strong>"
                                  for i, w in enumerate(high_band_words))
            study_tip = (
                f"重点记忆 Band 8-9 的高分词汇（{tip_words}）。"
                f"建议搭配例句一起记忆，写作时尝试使用高分词替换常见词，"
                f"大幅提升雅思写作得分。"
            )
        else:
            study_tip = "今日词汇以基础词汇为主，打好词汇基础是提高雅思成绩的关键。建议每个词写 3 遍，加深记忆。"

        return {
            "date": today.strftime("%Y年%m月%d日"),
            "day_num": day_num,
            "total_words": total_words,
            "cumulative_words": cumulative_words,
            "word_groups": word_groups,
            "study_tip": study_tip,
        }

    def generate_daily_email(self, data: dict | None = None, word_count: int = 20) -> str:
        """生成每日词汇推送邮件 HTML 内容

        Args:
            data: 可选，自定义数据（测试用）。为 None 时自动收集数据。
            word_count: 推送词数，默认 20

        Returns:
            HTML 字符串
        """
        if data is None:
            data = self._gather_data(word_count=word_count)
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
        subject = f"{subject_prefix} 📚 每日雅思词汇推送 · {date.today().strftime('%Y年%m月%d日')}"

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
