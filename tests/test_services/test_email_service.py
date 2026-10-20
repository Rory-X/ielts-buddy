"""测试邮件服务"""

from __future__ import annotations

import json
import os
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from ielts_buddy.services.email_service import EmailService, _round_pct, load_email_config


@pytest.fixture(autouse=True)
def _tmp_home(tmp_path):
    """每个测试使用独立的临时数据目录"""
    os.environ["IELTS_BUDDY_HOME"] = str(tmp_path / ".ielts-buddy")
    yield
    os.environ.pop("IELTS_BUDDY_HOME", None)


@pytest.fixture
def email_service() -> EmailService:
    """使用项目内模板的 EmailService"""
    return EmailService()


@pytest.fixture
def sample_email_data() -> dict:
    """测试用邮件数据（与 _gather_data 的输出契约一致）"""
    return {
        "date": "2026-03-06",
        "day_num": 12,
        "total_words": 4,
        "cumulative_words": 240,
        "word_groups": [
            {
                "band": 7,
                "label": "核心词汇",
                "words": [
                    {"word": "contribute", "phonetic": "/kənˈtrɪbjuːt/", "pos": "v.", "meaning": "贡献，促成", "topic": "education", "example": "Everyone can contribute."},
                    {"word": "analyze", "phonetic": "/ˈænəlaɪz/", "pos": "v.", "meaning": "分析", "topic": "science", "example": "Analyze the data."},
                ],
            },
            {
                "band": 8,
                "label": "高阶词汇",
                "words": [
                    {"word": "phenomenon", "phonetic": "/fɪˈnɒmɪnən/", "pos": "n.", "meaning": "现象", "topic": "science", "example": "A natural phenomenon."},
                    {"word": "emphasize", "phonetic": "/ˈemfəsaɪz/", "pos": "v.", "meaning": "强调", "topic": "writing", "example": "Emphasize the point."},
                ],
            },
        ],
        "study_tip": "重点记忆 Band 8-9 的高分词汇（phenomenon、emphasize）。建议搭配例句一起记忆。",
    }


class TestRoundPct:
    """测试百分比格式化"""

    def test_zero(self):
        assert _round_pct(0.0) == "0%"

    def test_one(self):
        assert _round_pct(1.0) == "100%"

    def test_fraction(self):
        assert _round_pct(0.85) == "85%"

    def test_small(self):
        assert _round_pct(0.043) == "4%"


class TestGenerateDailyEmail:
    """测试邮件 HTML 生成（与当前暗色词汇推送模板的字段契约一致）"""

    def test_generates_html(self, email_service: EmailService, sample_email_data: dict):
        html = email_service.generate_daily_email(data=sample_email_data)
        assert isinstance(html, str)
        assert len(html) > 0

    def test_contains_date(self, email_service: EmailService, sample_email_data: dict):
        html = email_service.generate_daily_email(data=sample_email_data)
        assert "2026-03-06" in html

    def test_contains_day_and_totals(self, email_service: EmailService, sample_email_data: dict):
        html = email_service.generate_daily_email(data=sample_email_data)
        assert "Day 12" in html
        assert "240" in html  # cumulative_words

    def test_contains_all_words(self, email_service: EmailService, sample_email_data: dict):
        html = email_service.generate_daily_email(data=sample_email_data)
        for word in ("contribute", "analyze", "phenomenon", "emphasize"):
            assert word in html

    def test_contains_band_sections(self, email_service: EmailService, sample_email_data: dict):
        html = email_service.generate_daily_email(data=sample_email_data)
        assert "Band 7" in html
        assert "Band 8" in html
        assert "核心词汇" in html
        assert "高阶词汇" in html

    def test_contains_study_tip(self, email_service: EmailService, sample_email_data: dict):
        html = email_service.generate_daily_email(data=sample_email_data)
        assert "重点记忆 Band 8-9" in html

    def test_html_structure(self, email_service: EmailService, sample_email_data: dict):
        html = email_service.generate_daily_email(data=sample_email_data)
        assert "<html" in html
        assert "<head>" in html
        assert "<body>" in html
        assert "</html>" in html

    def test_empty_word_groups(self, email_service: EmailService, sample_email_data: dict):
        """无今日词汇时不渲染单词卡，但邮件结构仍完整"""
        sample_email_data["word_groups"] = []
        html = email_service.generate_daily_email(data=sample_email_data)
        assert 'class="word-card' not in html
        assert "<html" in html

    def test_partial_data_defaults_day_num(self, email_service: EmailService):
        """旧调用方只传部分字段时 day_num 缺省为 1，不再抛 UndefinedError"""
        html = email_service.generate_daily_email(data={"date": "2026-03-06", "word_groups": []})
        assert "Day 1" in html

    def test_auto_gather_data(self, email_service: EmailService):
        html = email_service.generate_daily_email()
        assert isinstance(html, str)
        assert "<html" in html


class TestLoadEmailConfig:
    """测试邮件配置加载"""

    def test_missing_config_raises(self):
        """配置文件不存在时应抛出 FileNotFoundError"""
        with pytest.raises(FileNotFoundError):
            load_email_config()

    def test_load_valid_config(self, tmp_path):
        """应正确加载配置文件"""
        os.environ["IELTS_BUDDY_HOME"] = str(tmp_path)
        config = {
            "smtp_host": "smtp.test.com",
            "smtp_port": 465,
            "smtp_ssl": True,
            "username": "test@test.com",
            "password": "secret",
            "from_addr": "test@test.com",
            "to_addr": "user@test.com",
        }
        config_path = tmp_path / "email.json"
        config_path.write_text(json.dumps(config), encoding="utf-8")

        loaded = load_email_config()
        assert loaded["smtp_host"] == "smtp.test.com"
        assert loaded["to_addr"] == "user@test.com"


class TestSendEmail:
    """测试邮件发送"""

    def test_send_email_ssl(self, email_service: EmailService):
        """SSL 模式发送邮件"""
        config = {
            "smtp_host": "smtp.test.com",
            "smtp_port": 465,
            "smtp_ssl": True,
            "username": "test@test.com",
            "password": "secret",
            "from_addr": "test@test.com",
            "to_addr": "user@test.com",
        }
        mock_server = MagicMock()
        with patch("ielts_buddy.services.email_service.smtplib.SMTP_SSL", return_value=mock_server):
            email_service.send_email("<html>test</html>", config=config)
            mock_server.login.assert_called_once_with("test@test.com", "secret")
            mock_server.sendmail.assert_called_once()
            mock_server.quit.assert_called_once()

    def test_send_email_starttls(self, email_service: EmailService):
        """STARTTLS 模式发送邮件"""
        config = {
            "smtp_host": "smtp.test.com",
            "smtp_port": 587,
            "smtp_ssl": False,
            "username": "test@test.com",
            "password": "secret",
            "from_addr": "test@test.com",
            "to_addr": "user@test.com",
        }
        mock_server = MagicMock()
        with patch("ielts_buddy.services.email_service.smtplib.SMTP", return_value=mock_server):
            email_service.send_email("<html>test</html>", config=config)
            mock_server.starttls.assert_called_once()
            mock_server.login.assert_called_once()
            mock_server.quit.assert_called_once()
