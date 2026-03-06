"""学习报告服务：生成每日报告数据、日历热力图数据、首页数据"""

from __future__ import annotations

import json
import sqlite3
from datetime import date, datetime, timedelta
from pathlib import Path

from jinja2 import Environment, PackageLoader

from ielts_buddy.core.config import get_app_dir, get_db_path


def _get_site_dir() -> Path:
    """获取静态站点输出目录"""
    return get_app_dir() / "site"


class ReportService:
    """学习报告服务"""

    def __init__(self, db_path: Path | None = None) -> None:
        self._db_path = db_path or get_db_path()
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(self._db_path))
        self._conn.row_factory = sqlite3.Row

    def close(self) -> None:
        self._conn.close()

    def _table_exists(self, table: str = "learning_records") -> bool:
        row = self._conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
            (table,),
        ).fetchone()
        return row is not None

    # ---- 每日报告数据 ----

    def generate_daily_report(self, target_date: date | None = None) -> dict:
        """生成指定日期的学习报告数据

        返回:
            {
                "date": "2026-03-06",
                "new_words": [{word, phonetic, meaning, pos, band}, ...],
                "reviewed_words": [{word, phonetic, meaning, pos, band, memory_level}, ...],
                "new_count": int,
                "review_count": int,
                "total_count": int,
                "correct": int,
                "wrong": int,
                "accuracy": float,
                "streak": {"current": int, "max": int},
                "band_progress": [{band, total, mastered, ratio}, ...],
                "prev_date": str | None,
                "next_date": str | None,
            }
        """
        target = target_date or date.today()
        target_str = target.isoformat()

        new_words = self._get_new_words(target_str)
        reviewed_words = self._get_reviewed_words(target_str)
        correct, wrong = self._get_day_accuracy(target_str)
        total_attempts = correct + wrong
        accuracy = correct / total_attempts if total_attempts > 0 else 0.0
        streak_current, streak_max = self._get_streak(target)
        band_progress = self._get_band_progress()
        prev_date, next_date = self._get_adjacent_dates(target)

        return {
            "date": target_str,
            "new_words": new_words,
            "reviewed_words": reviewed_words,
            "new_count": len(new_words),
            "review_count": len(reviewed_words),
            "total_count": len(new_words) + len(reviewed_words),
            "correct": correct,
            "wrong": wrong,
            "accuracy": accuracy,
            "streak": {"current": streak_current, "max": streak_max},
            "band_progress": band_progress,
            "prev_date": prev_date,
            "next_date": next_date,
        }

    def _get_new_words(self, date_str: str) -> list[dict]:
        """获取指定日期新学的单词"""
        if not self._table_exists():
            return []
        rows = self._conn.execute(
            """SELECT word, word_data, memory_level
               FROM learning_records
               WHERE DATE(first_learned) = ?
               ORDER BY first_learned""",
            (date_str,),
        ).fetchall()
        return [self._parse_word_row(row) for row in rows]

    def _get_reviewed_words(self, date_str: str) -> list[dict]:
        """获取指定日期复习的单词（排除当日新学的）"""
        if not self._table_exists():
            return []
        rows = self._conn.execute(
            """SELECT word, word_data, memory_level
               FROM learning_records
               WHERE DATE(last_reviewed) = ? AND DATE(first_learned) != ?
               ORDER BY last_reviewed""",
            (date_str, date_str),
        ).fetchall()
        return [self._parse_word_row(row) for row in rows]

    def _parse_word_row(self, row: sqlite3.Row) -> dict:
        """解析 learning_records 行为字典"""
        try:
            data = json.loads(row["word_data"])
        except (json.JSONDecodeError, TypeError):
            data = {}
        return {
            "word": row["word"],
            "phonetic": data.get("phonetic", ""),
            "meaning": data.get("meaning", data.get("definition", "")),
            "pos": data.get("pos", ""),
            "band": data.get("band", 0),
            "memory_level": row["memory_level"],
        }

    def _get_day_accuracy(self, date_str: str) -> tuple[int, int]:
        """获取指定日期的正确/错误次数

        注意：数据库只存累计值，无法精确拆分每日。
        这里用当日新学+复习的单词的累计正确/错误作为近似。
        """
        if not self._table_exists():
            return (0, 0)
        row = self._conn.execute(
            """SELECT COALESCE(SUM(correct_count), 0) as correct,
                      COALESCE(SUM(wrong_count), 0) as wrong
               FROM learning_records
               WHERE DATE(last_reviewed) = ?""",
            (date_str,),
        ).fetchone()
        return (row["correct"], row["wrong"])

    def _get_streak(self, target: date) -> tuple[int, int]:
        """计算到指定日期为止的连续学习天数"""
        if not self._table_exists():
            return (0, 0)

        rows = self._conn.execute(
            """SELECT DISTINCT DATE(last_reviewed) as study_date
               FROM learning_records
               WHERE last_reviewed IS NOT NULL
               ORDER BY study_date DESC"""
        ).fetchall()

        if not rows:
            return (0, 0)

        dates = [date.fromisoformat(row["study_date"]) for row in rows]

        # 当前连续天数（从 target 或其前一天开始）
        current_streak = 0
        if dates[0] >= target or dates[0] == target - timedelta(days=1):
            # 找到 <= target 的日期起点
            filtered = [d for d in dates if d <= target]
            if filtered:
                current_streak = 1
                for i in range(1, len(filtered)):
                    if filtered[i] == filtered[i - 1] - timedelta(days=1):
                        current_streak += 1
                    else:
                        break

        # 历史最长
        max_streak = 1 if dates else 0
        streak = 1
        for i in range(1, len(dates)):
            if dates[i] == dates[i - 1] - timedelta(days=1):
                streak += 1
                max_streak = max(max_streak, streak)
            else:
                streak = 1

        return (current_streak, max_streak)

    def _get_band_progress(self) -> list[dict]:
        """获取各 Band 掌握进度"""
        from ielts_buddy.services.vocab_service import VocabService

        vocab_svc = VocabService()
        vocab_svc.load_all()
        band_totals = vocab_svc.get_vocab_stats()["bands"]

        band_mastered: dict[int, int] = {}
        if self._table_exists():
            rows = self._conn.execute(
                "SELECT word_data, memory_level FROM learning_records"
            ).fetchall()
            for row in rows:
                try:
                    data = json.loads(row["word_data"])
                    band = data.get("band", 0)
                    if row["memory_level"] >= 4:
                        band_mastered[band] = band_mastered.get(band, 0) + 1
                except (json.JSONDecodeError, KeyError):
                    continue

        result = []
        for band, total in sorted(band_totals.items()):
            mastered = band_mastered.get(band, 0)
            ratio = mastered / total if total > 0 else 0.0
            result.append({
                "band": band,
                "total": total,
                "mastered": mastered,
                "ratio": ratio,
            })
        return result

    def _get_adjacent_dates(self, target: date) -> tuple[str | None, str | None]:
        """获取有数据的前一天和后一天日期"""
        if not self._table_exists():
            return (None, None)

        target_str = target.isoformat()

        prev_row = self._conn.execute(
            """SELECT DISTINCT DATE(last_reviewed) as d
               FROM learning_records
               WHERE DATE(last_reviewed) < ?
               ORDER BY d DESC LIMIT 1""",
            (target_str,),
        ).fetchone()

        next_row = self._conn.execute(
            """SELECT DISTINCT DATE(last_reviewed) as d
               FROM learning_records
               WHERE DATE(last_reviewed) > ?
               ORDER BY d ASC LIMIT 1""",
            (target_str,),
        ).fetchone()

        prev_date = prev_row["d"] if prev_row else None
        next_date = next_row["d"] if next_row else None
        return (prev_date, next_date)

    # ---- 日历热力图数据 ----

    def generate_calendar_data(self, months: int = 3) -> list[dict]:
        """生成最近 N 月的日历热力图数据

        返回:
            [{date: "2026-03-06", count: 25, level: 3}, ...]
            level 0-4: 0=无, 1=少, 2=中, 3=多, 4=极多
        """
        today = date.today()
        start = today - timedelta(days=months * 30)
        start_str = start.isoformat()

        if not self._table_exists():
            return self._fill_calendar(start, today, {})

        # 统计每天学习的单词数（last_reviewed 在该日期的记录数）
        rows = self._conn.execute(
            """SELECT DATE(last_reviewed) as study_date, COUNT(*) as cnt
               FROM learning_records
               WHERE DATE(last_reviewed) >= ?
               GROUP BY DATE(last_reviewed)""",
            (start_str,),
        ).fetchall()

        date_counts = {row["study_date"]: row["cnt"] for row in rows}
        return self._fill_calendar(start, today, date_counts)

    def _fill_calendar(
        self, start: date, end: date, date_counts: dict[str, int]
    ) -> list[dict]:
        """填充日历数据，计算每天的 level"""
        if date_counts:
            max_count = max(date_counts.values())
        else:
            max_count = 0

        result = []
        current = start
        while current <= end:
            d = current.isoformat()
            count = date_counts.get(d, 0)
            level = self._count_to_level(count, max_count)
            result.append({"date": d, "count": count, "level": level})
            current += timedelta(days=1)
        return result

    @staticmethod
    def _count_to_level(count: int, max_count: int) -> int:
        """将学习数量映射到 0-4 等级"""
        if count == 0:
            return 0
        if max_count == 0:
            return 0
        ratio = count / max_count
        if ratio <= 0.25:
            return 1
        if ratio <= 0.50:
            return 2
        if ratio <= 0.75:
            return 3
        return 4

    # ---- 首页数据 ----

    def generate_index_data(self) -> dict:
        """生成首页数据（总览+日历）

        返回:
            {
                "total_words": int,
                "total_reviews": int,
                "accuracy": float,
                "mastered": int,
                "streak": {"current": int, "max": int},
                "calendar": [...],
                "recent_days": [{date, new_words, reviewed_words}, ...],
                "band_progress": [...],
                "active_dates": [str, ...],  # 所有有数据的日期
            }
        """
        total = self._get_total_stats()
        streak = self._get_streak(date.today())
        calendar = self.generate_calendar_data(months=3)
        recent = self._get_recent_days(14)
        band_progress = self._get_band_progress()
        active_dates = self._get_all_active_dates()

        return {
            "total_words": total["total_words"],
            "total_reviews": total["total_reviews"],
            "accuracy": total["accuracy"],
            "mastered": total["mastered"],
            "streak": {"current": streak[0], "max": streak[1]},
            "calendar": calendar,
            "recent_days": recent,
            "band_progress": band_progress,
            "active_dates": active_dates,
        }

    def _get_total_stats(self) -> dict:
        """获取总体统计"""
        if not self._table_exists():
            return {
                "total_words": 0,
                "total_reviews": 0,
                "accuracy": 0.0,
                "mastered": 0,
            }
        row = self._conn.execute(
            """SELECT
               COUNT(*) as total_words,
               COALESCE(SUM(learn_count), 0) as total_reviews,
               COALESCE(SUM(correct_count), 0) as total_correct,
               COALESCE(SUM(wrong_count), 0) as total_wrong,
               COUNT(CASE WHEN memory_level >= 5 THEN 1 END) as mastered
               FROM learning_records"""
        ).fetchone()

        total_attempts = row["total_correct"] + row["total_wrong"]
        accuracy = row["total_correct"] / total_attempts if total_attempts > 0 else 0.0

        return {
            "total_words": row["total_words"],
            "total_reviews": row["total_reviews"],
            "accuracy": accuracy,
            "mastered": row["mastered"],
        }

    def _get_recent_days(self, days: int = 14) -> list[dict]:
        """获取最近 N 天学习概况"""
        today = date.today()
        start = today - timedelta(days=days - 1)

        if not self._table_exists():
            return [
                {"date": (start + timedelta(days=i)).isoformat(), "new_words": 0, "reviewed_words": 0}
                for i in range(days)
            ]

        new_rows = self._conn.execute(
            """SELECT DATE(first_learned) as d, COUNT(*) as cnt
               FROM learning_records WHERE DATE(first_learned) >= ?
               GROUP BY DATE(first_learned)""",
            (start.isoformat(),),
        ).fetchall()

        review_rows = self._conn.execute(
            """SELECT DATE(last_reviewed) as d, COUNT(*) as cnt
               FROM learning_records WHERE DATE(last_reviewed) >= ?
               GROUP BY DATE(last_reviewed)""",
            (start.isoformat(),),
        ).fetchall()

        new_counts = {row["d"]: row["cnt"] for row in new_rows}
        review_counts = {row["d"]: row["cnt"] for row in review_rows}

        result = []
        for i in range(days):
            d = (start + timedelta(days=i)).isoformat()
            result.append({
                "date": d,
                "new_words": new_counts.get(d, 0),
                "reviewed_words": review_counts.get(d, 0),
            })
        return result

    def _get_all_active_dates(self) -> list[str]:
        """获取所有有学习记录的日期（用于 build 全部报告）"""
        if not self._table_exists():
            return []
        rows = self._conn.execute(
            """SELECT DISTINCT DATE(last_reviewed) as d
               FROM learning_records
               WHERE last_reviewed IS NOT NULL
               ORDER BY d"""
        ).fetchall()
        return [row["d"] for row in rows]

    # ---- 渲染 HTML ----

    def render_daily_report(self, target_date: date | None = None) -> str:
        """渲染每日报告 HTML"""
        data = self.generate_daily_report(target_date)
        env = _get_jinja_env()
        template = env.get_template("daily_report.html")
        return template.render(**data)

    def render_index(self) -> str:
        """渲染首页 HTML"""
        data = self.generate_index_data()
        env = _get_jinja_env()
        template = env.get_template("index.html")
        return template.render(**data)

    def build_site(self) -> Path:
        """生成全部报告到站点目录，返回站点路径"""
        site_dir = _get_site_dir()
        site_dir.mkdir(parents=True, exist_ok=True)

        # 生成首页
        index_html = self.render_index()
        (site_dir / "index.html").write_text(index_html, encoding="utf-8")

        # 生成每日报告
        active_dates = self._get_all_active_dates()
        for date_str in active_dates:
            target = date.fromisoformat(date_str)
            html = self.render_daily_report(target)
            (site_dir / f"{date_str}.html").write_text(html, encoding="utf-8")

        return site_dir


def _get_jinja_env() -> Environment:
    """创建 Jinja2 环境"""
    env = Environment(
        loader=PackageLoader("ielts_buddy", "templates"),
        autoescape=True,
    )
    env.filters["round_pct"] = _round_pct
    env.globals["_weekday"] = _weekday
    env.globals["range"] = range
    return env


def _round_pct(value: float) -> str:
    """将小数转为百分比字符串"""
    return f"{value * 100:.1f}%"


def _weekday(date_str: str) -> int:
    """返回星期几 (0=Monday, 6=Sunday)"""
    return date.fromisoformat(date_str).weekday()
