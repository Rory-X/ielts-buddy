"""测试 report CLI 命令"""

from __future__ import annotations

import json
import os
import sqlite3
from datetime import date, datetime, timedelta
from pathlib import Path

import pytest
from click.testing import CliRunner

from ielts_buddy.cli import cli


@pytest.fixture(autouse=True)
def _tmp_home(tmp_path):
    """每个测试使用独立的临时数据目录"""
    os.environ["IELTS_BUDDY_HOME"] = str(tmp_path / ".ielts-buddy")
    yield
    os.environ.pop("IELTS_BUDDY_HOME", None)


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


def _setup_db(tmp_path: Path) -> None:
    """在临时目录创建带数据的数据库"""
    db_dir = tmp_path / ".ielts-buddy"
    db_dir.mkdir(parents=True, exist_ok=True)
    db_path = db_dir / "data.db"
    conn = sqlite3.connect(str(db_path))
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS learning_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            word TEXT UNIQUE NOT NULL,
            word_data TEXT NOT NULL,
            memory_level INTEGER DEFAULT 0,
            next_review TEXT,
            learn_count INTEGER DEFAULT 0,
            correct_count INTEGER DEFAULT 0,
            wrong_count INTEGER DEFAULT 0,
            first_learned TEXT,
            last_reviewed TEXT,
            is_starred INTEGER DEFAULT 0,
            is_difficult INTEGER DEFAULT 0
        );
    """)
    today = date.today().isoformat()
    now = f"{today}T10:00:00"
    word_data = json.dumps({"word": "test", "meaning": "测试", "band": 5,
                            "phonetic": "/test/", "pos": "n."}, ensure_ascii=False)
    conn.execute(
        """INSERT INTO learning_records
           (word, word_data, memory_level, next_review, learn_count,
            correct_count, wrong_count, first_learned, last_reviewed)
           VALUES (?, ?, 1, '2099-01-01', 1, 1, 0, ?, ?)""",
        ("test", word_data, now, now),
    )
    conn.commit()
    conn.close()


class TestReportHelp:

    def test_report_help(self, runner: CliRunner):
        result = runner.invoke(cli, ["report", "--help"])
        assert result.exit_code == 0
        assert "daily" in result.output
        assert "build" in result.output
        assert "serve" in result.output

    def test_report_in_main_help(self, runner: CliRunner):
        result = runner.invoke(cli, ["--help"])
        assert result.exit_code == 0
        assert "report" in result.output


class TestReportDaily:

    def test_daily_default(self, runner: CliRunner, tmp_path: Path):
        result = runner.invoke(cli, ["report", "daily"])
        assert result.exit_code == 0
        assert "已生成报告" in result.output

    def test_daily_with_date(self, runner: CliRunner, tmp_path: Path):
        _setup_db(tmp_path)
        today = date.today().isoformat()
        result = runner.invoke(cli, ["report", "daily", "-d", today])
        assert result.exit_code == 0
        assert "已生成报告" in result.output

    def test_daily_invalid_date(self, runner: CliRunner):
        result = runner.invoke(cli, ["report", "daily", "-d", "not-a-date"])
        assert result.exit_code == 0
        assert "无效日期格式" in result.output

    def test_daily_creates_file(self, runner: CliRunner, tmp_path: Path):
        runner.invoke(cli, ["report", "daily"])
        site_dir = tmp_path / ".ielts-buddy" / "site"
        today = date.today().isoformat()
        assert (site_dir / f"{today}.html").exists()


class TestReportBuild:

    def test_build_empty(self, runner: CliRunner, tmp_path: Path):
        result = runner.invoke(cli, ["report", "build"])
        assert result.exit_code == 0
        assert "站点已生成" in result.output

    def test_build_with_data(self, runner: CliRunner, tmp_path: Path):
        _setup_db(tmp_path)
        result = runner.invoke(cli, ["report", "build"])
        assert result.exit_code == 0
        assert "站点已生成" in result.output

        site_dir = tmp_path / ".ielts-buddy" / "site"
        assert (site_dir / "index.html").exists()

    def test_build_creates_daily_files(self, runner: CliRunner, tmp_path: Path):
        _setup_db(tmp_path)
        runner.invoke(cli, ["report", "build"])
        site_dir = tmp_path / ".ielts-buddy" / "site"
        today = date.today().isoformat()
        assert (site_dir / f"{today}.html").exists()
