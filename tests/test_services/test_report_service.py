"""测试 ReportService"""

from __future__ import annotations

import json
import sqlite3
from datetime import date, datetime, timedelta
from pathlib import Path

import pytest

from ielts_buddy.services.report_service import ReportService, _get_jinja_env, _round_pct, _weekday


# ---- Fixtures ----

@pytest.fixture
def tmp_db(tmp_path: Path) -> Path:
    return tmp_path / "test_data.db"


@pytest.fixture
def report_service(tmp_db: Path) -> ReportService:
    svc = ReportService(db_path=tmp_db)
    yield svc
    svc.close()


def _init_db(db_path: Path) -> sqlite3.Connection:
    """创建 learning_records 表并返回连接"""
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
    conn.commit()
    return conn


def _insert_word(conn: sqlite3.Connection, word: str, band: int = 5,
                 meaning: str = "测试", memory_level: int = 1,
                 first_learned: str | None = None,
                 last_reviewed: str | None = None,
                 correct_count: int = 1, wrong_count: int = 0) -> None:
    now = datetime.now().isoformat(timespec="seconds")
    first_learned = first_learned or now
    last_reviewed = last_reviewed or now
    word_data = json.dumps({
        "word": word, "meaning": meaning, "band": band,
        "phonetic": "/test/", "pos": "n.",
    }, ensure_ascii=False)
    conn.execute(
        """INSERT INTO learning_records
           (word, word_data, memory_level, next_review, learn_count,
            correct_count, wrong_count, first_learned, last_reviewed)
           VALUES (?, ?, ?, ?, 1, ?, ?, ?, ?)""",
        (word, word_data, memory_level, "2099-01-01", correct_count, wrong_count,
         first_learned, last_reviewed),
    )
    conn.commit()


# ---- Tests: generate_daily_report ----

class TestGenerateDailyReport:

    def test_empty_db(self, report_service: ReportService):
        data = report_service.generate_daily_report(date.today())
        assert data["date"] == date.today().isoformat()
        assert data["new_count"] == 0
        assert data["review_count"] == 0
        assert data["total_count"] == 0
        assert data["accuracy"] == 0.0
        assert data["prev_date"] is None
        assert data["next_date"] is None

    def test_with_new_words(self, tmp_db: Path):
        conn = _init_db(tmp_db)
        today = date.today().isoformat()
        now = f"{today}T10:00:00"
        _insert_word(conn, "hello", first_learned=now, last_reviewed=now)
        _insert_word(conn, "world", first_learned=now, last_reviewed=now)
        conn.close()

        svc = ReportService(db_path=tmp_db)
        data = svc.generate_daily_report(date.today())
        svc.close()

        assert data["new_count"] == 2
        assert len(data["new_words"]) == 2
        assert data["new_words"][0]["word"] in ("hello", "world")

    def test_with_reviewed_words(self, tmp_db: Path):
        conn = _init_db(tmp_db)
        today = date.today().isoformat()
        yesterday = (date.today() - timedelta(days=1)).isoformat()
        _insert_word(conn, "review_word",
                     first_learned=f"{yesterday}T10:00:00",
                     last_reviewed=f"{today}T10:00:00",
                     memory_level=3)
        conn.close()

        svc = ReportService(db_path=tmp_db)
        data = svc.generate_daily_report(date.today())
        svc.close()

        assert data["review_count"] == 1
        assert data["reviewed_words"][0]["word"] == "review_word"
        assert data["reviewed_words"][0]["memory_level"] == 3

    def test_accuracy(self, tmp_db: Path):
        conn = _init_db(tmp_db)
        today = date.today().isoformat()
        now = f"{today}T10:00:00"
        _insert_word(conn, "w1", correct_count=3, wrong_count=1,
                     first_learned=now, last_reviewed=now)
        conn.close()

        svc = ReportService(db_path=tmp_db)
        data = svc.generate_daily_report(date.today())
        svc.close()

        assert data["accuracy"] == 0.75

    def test_default_date_is_today(self, report_service: ReportService):
        data = report_service.generate_daily_report()
        assert data["date"] == date.today().isoformat()

    def test_adjacent_dates(self, tmp_db: Path):
        conn = _init_db(tmp_db)
        d1 = (date.today() - timedelta(days=2)).isoformat()
        d2 = (date.today() - timedelta(days=1)).isoformat()
        d3 = date.today().isoformat()
        _insert_word(conn, "w1", first_learned=f"{d1}T10:00:00", last_reviewed=f"{d1}T10:00:00")
        _insert_word(conn, "w2", first_learned=f"{d2}T10:00:00", last_reviewed=f"{d2}T10:00:00")
        _insert_word(conn, "w3", first_learned=f"{d3}T10:00:00", last_reviewed=f"{d3}T10:00:00")
        conn.close()

        svc = ReportService(db_path=tmp_db)
        data = svc.generate_daily_report(date.today() - timedelta(days=1))
        svc.close()

        assert data["prev_date"] == d1
        assert data["next_date"] == d3


# ---- Tests: generate_calendar_data ----

class TestGenerateCalendarData:

    def test_empty_db(self, report_service: ReportService):
        data = report_service.generate_calendar_data(months=1)
        assert len(data) > 0
        assert all(d["count"] == 0 for d in data)
        assert all(d["level"] == 0 for d in data)

    def test_with_data(self, tmp_db: Path):
        conn = _init_db(tmp_db)
        today = date.today().isoformat()
        now = f"{today}T10:00:00"
        for i in range(10):
            _insert_word(conn, f"word_{i}", first_learned=now, last_reviewed=now)
        conn.close()

        svc = ReportService(db_path=tmp_db)
        data = svc.generate_calendar_data(months=1)
        svc.close()

        today_entry = [d for d in data if d["date"] == today]
        assert len(today_entry) == 1
        assert today_entry[0]["count"] == 10
        assert today_entry[0]["level"] == 4  # 最高 level

    def test_level_distribution(self, tmp_db: Path):
        conn = _init_db(tmp_db)
        today = date.today()
        # Day 1: 2 words, Day 2: 8 words
        d1 = (today - timedelta(days=1)).isoformat()
        d2 = today.isoformat()
        for i in range(2):
            _insert_word(conn, f"a_{i}", first_learned=f"{d1}T10:00:00",
                         last_reviewed=f"{d1}T10:00:00")
        for i in range(8):
            _insert_word(conn, f"b_{i}", first_learned=f"{d2}T10:00:00",
                         last_reviewed=f"{d2}T10:00:00")
        conn.close()

        svc = ReportService(db_path=tmp_db)
        data = svc.generate_calendar_data(months=1)
        svc.close()

        d1_entry = [d for d in data if d["date"] == d1][0]
        d2_entry = [d for d in data if d["date"] == d2][0]
        assert d1_entry["level"] < d2_entry["level"]


# ---- Tests: generate_index_data ----

class TestGenerateIndexData:

    def test_empty_db(self, report_service: ReportService):
        data = report_service.generate_index_data()
        assert data["total_words"] == 0
        assert data["total_reviews"] == 0
        assert data["accuracy"] == 0.0
        assert data["mastered"] == 0
        assert data["streak"]["current"] == 0
        assert isinstance(data["calendar"], list)
        assert isinstance(data["recent_days"], list)
        assert isinstance(data["band_progress"], list)
        assert data["active_dates"] == []

    def test_with_data(self, tmp_db: Path):
        conn = _init_db(tmp_db)
        today = date.today().isoformat()
        now = f"{today}T10:00:00"
        _insert_word(conn, "hello", correct_count=5, wrong_count=1,
                     memory_level=5, first_learned=now, last_reviewed=now)
        conn.close()

        svc = ReportService(db_path=tmp_db)
        data = svc.generate_index_data()
        svc.close()

        assert data["total_words"] == 1
        assert data["mastered"] == 1
        assert data["accuracy"] > 0
        assert today in data["active_dates"]

    def test_recent_days_length(self, report_service: ReportService):
        data = report_service.generate_index_data()
        assert len(data["recent_days"]) == 14


# ---- Tests: count_to_level ----

class TestCountToLevel:

    def test_zero(self):
        assert ReportService._count_to_level(0, 100) == 0

    def test_zero_max(self):
        assert ReportService._count_to_level(5, 0) == 0

    def test_low(self):
        assert ReportService._count_to_level(1, 10) == 1

    def test_mid_low(self):
        assert ReportService._count_to_level(4, 10) == 2

    def test_mid_high(self):
        assert ReportService._count_to_level(6, 10) == 3

    def test_high(self):
        assert ReportService._count_to_level(10, 10) == 4


# ---- Tests: helpers ----

class TestHelpers:

    def test_round_pct(self):
        assert _round_pct(0.75) == "75.0%"
        assert _round_pct(0.0) == "0.0%"
        assert _round_pct(1.0) == "100.0%"

    def test_weekday(self):
        # 2026-03-06 is a Friday = weekday 4
        assert _weekday("2026-03-06") == 4

    def test_jinja_env(self):
        env = _get_jinja_env()
        assert "round_pct" in env.filters
        assert "_weekday" in env.globals


# ---- Tests: render HTML ----

class TestRenderHTML:

    def test_render_daily_report(self, report_service: ReportService):
        html = report_service.render_daily_report(date.today())
        assert "IELTS Buddy" in html
        assert date.today().isoformat() in html
        assert "学习概览" in html

    def test_render_index(self, report_service: ReportService):
        html = report_service.render_index()
        assert "IELTS Buddy" in html
        assert "学习总览" in html
        assert "学习日历" in html

    def test_render_daily_with_data(self, tmp_db: Path):
        conn = _init_db(tmp_db)
        today = date.today().isoformat()
        now = f"{today}T10:00:00"
        _insert_word(conn, "example", meaning="例子", first_learned=now, last_reviewed=now)
        conn.close()

        svc = ReportService(db_path=tmp_db)
        html = svc.render_daily_report(date.today())
        svc.close()

        assert "example" in html
        assert "例子" in html


# ---- Tests: build_site ----

class TestBuildSite:

    def test_build_empty(self, report_service: ReportService, tmp_path: Path, monkeypatch):
        monkeypatch.setenv("IELTS_BUDDY_HOME", str(tmp_path / ".ielts-buddy"))
        # Re-create service with patched env
        from ielts_buddy.services.report_service import _get_site_dir
        svc = ReportService(db_path=tmp_path / "test.db")
        site_dir = svc.build_site()
        svc.close()

        assert (site_dir / "index.html").exists()

    def test_build_with_data(self, tmp_path: Path, monkeypatch):
        monkeypatch.setenv("IELTS_BUDDY_HOME", str(tmp_path / ".ielts-buddy"))
        db_path = tmp_path / ".ielts-buddy" / "data.db"
        db_path.parent.mkdir(parents=True, exist_ok=True)

        conn = _init_db(db_path)
        today = date.today().isoformat()
        now = f"{today}T10:00:00"
        _insert_word(conn, "test_word", first_learned=now, last_reviewed=now)
        conn.close()

        svc = ReportService(db_path=db_path)
        site_dir = svc.build_site()
        svc.close()

        assert (site_dir / "index.html").exists()
        assert (site_dir / f"{today}.html").exists()


# ---- Tests: streak ----

class TestStreak:

    def test_streak_consecutive(self, tmp_db: Path):
        conn = _init_db(tmp_db)
        today = date.today()
        for i in range(3):
            d = (today - timedelta(days=i)).isoformat()
            _insert_word(conn, f"streak_{i}",
                         first_learned=f"{d}T10:00:00",
                         last_reviewed=f"{d}T10:00:00")
        conn.close()

        svc = ReportService(db_path=tmp_db)
        data = svc.generate_daily_report(today)
        svc.close()

        assert data["streak"]["current"] == 3

    def test_streak_broken(self, tmp_db: Path):
        conn = _init_db(tmp_db)
        today = date.today()
        # Today and 3 days ago (gap)
        _insert_word(conn, "s1",
                     first_learned=f"{today.isoformat()}T10:00:00",
                     last_reviewed=f"{today.isoformat()}T10:00:00")
        d3 = (today - timedelta(days=3)).isoformat()
        _insert_word(conn, "s2",
                     first_learned=f"{d3}T10:00:00",
                     last_reviewed=f"{d3}T10:00:00")
        conn.close()

        svc = ReportService(db_path=tmp_db)
        data = svc.generate_daily_report(today)
        svc.close()

        assert data["streak"]["current"] == 1
