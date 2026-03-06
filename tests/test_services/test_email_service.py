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
    """测试用邮件数据"""
    return {
        "date": "2026-03-06",
        "yesterday": {"new_words": 15, "reviewed_words": 30},
        "total": {
            "total_words": 100,
            "total_reviews": 500,
            "total_correct": 400,
            "total_wrong": 100,
            "accuracy": 0.8,
            "mastered": 25,
        },
        "streak": {"current": 7, "max": 14},
        "due_words": [
            {"word": "contribute", "phonetic": "/kənˈtrɪbjuːt/", "meaning": "贡献，促成", "memory_level": 2},
            {"word": "analyze", "phonetic": "/ˈænəlaɪz/", "meaning": "分析", "memory_level": 1},
        ],
        "recommended_words": [
            {"word": "phenomenon", "phonetic": "/fɪˈnɒmɪnən/", "meaning": "现象", "band": 7},
            {"word": "emphasize", "phonetic": "/ˈemfəsaɪz/", "meaning": "强调", "band": 6},
        ],
        "band_progress": [
            {"band": 5, "total": 131, "mastered": 50, "ratio": 0.382},
            {"band": 6, "total": 80, "mastered": 20, "ratio": 0.25},
            {"band": 7, "total": 115, "mastered": 5, "ratio": 0.043},
        ],
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
    """测试邮件 HTML 生成"""

    def test_generates_html(self, email_service: EmailService, sample_email_data: dict):
        """应生成 HTML 字符串"""
        html = email_service.generate_daily_email(data=sample_email_data)
        assert isinstance(html, str)
        assert len(html) > 0

    def test_contains_date(self, email_service: EmailService, sample_email_data: dict):
        """HTML 应包含日期"""
        html = email_service.generate_daily_email(data=sample_email_data)
        assert "2026-03-06" in html

    def test_contains_yesterday_stats(self, email_service: EmailService, sample_email_data: dict):
        """HTML 应包含昨日学习数据"""
        html = email_service.generate_daily_email(data=sample_email_data)
        assert "15" in html  # new_words
        assert "30" in html  # reviewed_words

    def test_contains_due_words(self, email_service: EmailService, sample_email_data: dict):
        """HTML 应包含待复习单词"""
        html = email_service.generate_daily_email(data=sample_email_data)
        assert "contribute" in html
        assert "analyze" in html

    def test_contains_recommended_words(self, email_service: EmailService, sample_email_data: dict):
        """HTML 应包含推荐新词"""
        html = email_service.generate_daily_email(data=sample_email_data)
        assert "phenomenon" in html
        assert "emphasize" in html

    def test_contains_band_progress(self, email_service: EmailService, sample_email_data: dict):
        """HTML 应包含 Band 进度"""
        html = email_service.generate_daily_email(data=sample_email_data)
        assert "Band 5" in html
        assert "Band 6" in html
        assert "Band 7" in html

    def test_contains_streak(self, email_service: EmailService, sample_email_data: dict):
        """HTML 应包含连续学习天数"""
        html = email_service.generate_daily_email(data=sample_email_data)
        assert "7" in html  # current streak

    def test_html_structure(self, email_service: EmailService, sample_email_data: dict):
        """HTML 应包含基本结构标签"""
        html = email_service.generate_daily_email(data=sample_email_data)
        assert "<html" in html
        assert "<head>" in html
        assert "<body>" in html
        assert "</html>" in html

    def test_empty_due_words(self, email_service: EmailService, sample_email_data: dict):
        """无待复习时应显示提示信息"""
        sample_email_data["due_words"] = []
        html = email_service.generate_daily_email(data=sample_email_data)
        assert "暂无待复习单词" in html

    def test_empty_recommended(self, email_service: EmailService, sample_email_data: dict):
        """无推荐词时应显示提示"""
        sample_email_data["recommended_words"] = []
        html = email_service.generate_daily_email(data=sample_email_data)
        assert "今日无新词推荐" in html

    def test_no_streak(self, email_service: EmailService, sample_email_data: dict):
        """无连续学习时不显示 streak badge"""
        sample_email_data["streak"]["current"] = 0
        html = email_service.generate_daily_email(data=sample_email_data)
        assert "连续学习" not in html

    def test_auto_gather_data(self, email_service: EmailService):
        """不传 data 时应自动收集数据"""
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
