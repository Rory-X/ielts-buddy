"""个人词库服务：管理用户自定义单词和分类，SQLite 存储"""

from __future__ import annotations

import csv
import io
import json
import sqlite3
from datetime import datetime
from pathlib import Path

from ielts_buddy.core.config import get_db_path
from ielts_buddy.core.models import PersonalWord, VocabCategory, Word


_SCHEMA = """
CREATE TABLE IF NOT EXISTS personal_vocab (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    word TEXT UNIQUE NOT NULL,
    phonetic TEXT DEFAULT '',
    meaning TEXT DEFAULT '',
    pos TEXT DEFAULT '',
    band INTEGER DEFAULT 5,
    topic TEXT DEFAULT '',
    example TEXT DEFAULT '',
    example_cn TEXT DEFAULT '',
    note TEXT DEFAULT '',
    source TEXT DEFAULT 'manual',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS vocab_categories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL,
    description TEXT DEFAULT '',
    is_system INTEGER DEFAULT 0,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS vocab_category_words (
    category_id INTEGER NOT NULL,
    word_id INTEGER NOT NULL,
    added_at TEXT NOT NULL,
    PRIMARY KEY (category_id, word_id),
    FOREIGN KEY (category_id) REFERENCES vocab_categories(id) ON DELETE CASCADE,
    FOREIGN KEY (word_id) REFERENCES personal_vocab(id) ON DELETE CASCADE
);
"""

# 系统内置分类
_SYSTEM_CATEGORIES = [
    ("favorites", "收藏夹"),
    ("mistakes", "错词本"),
]


class PersonalVocabService:
    """个人词库管理服务"""

    def __init__(self, db_path: Path | None = None) -> None:
        self._db_path = db_path or get_db_path()
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(self._db_path))
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA foreign_keys = ON")
        self._init_db()

    def _init_db(self) -> None:
        self._conn.executescript(_SCHEMA)
        # 确保系统分类存在
        now = datetime.now().isoformat(timespec="seconds")
        for name, desc in _SYSTEM_CATEGORIES:
            self._conn.execute(
                """INSERT OR IGNORE INTO vocab_categories (name, description, is_system, created_at)
                   VALUES (?, ?, 1, ?)""",
                (name, desc, now),
            )
        self._conn.commit()

    def close(self) -> None:
        self._conn.close()

    # ---- 单词 CRUD ----

    def add_word(self, word: PersonalWord) -> PersonalWord:
        """添加单词到个人词库，返回带 id 的 PersonalWord"""
        now = datetime.now().isoformat(timespec="seconds")
        try:
            self._conn.execute(
                """INSERT INTO personal_vocab
                   (word, phonetic, meaning, pos, band, topic, example, example_cn, note, source, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    word.word, word.phonetic, word.meaning, word.pos,
                    word.band, word.topic, word.example, word.example_cn,
                    word.note, word.source, now, now,
                ),
            )
            self._conn.commit()
        except sqlite3.IntegrityError:
            raise ValueError(f"单词 '{word.word}' 已存在于个人词库中")
        return self._get_word_by_name(word.word)

    def edit_word(self, word_name: str, **kwargs) -> PersonalWord:
        """编辑个人词库中的单词字段"""
        existing = self._get_word_by_name(word_name)
        if existing is None:
            raise ValueError(f"单词 '{word_name}' 不在个人词库中")

        allowed_fields = {"phonetic", "meaning", "pos", "band", "topic", "example", "example_cn", "note"}
        updates = {k: v for k, v in kwargs.items() if k in allowed_fields and v is not None}
        if not updates:
            return existing

        now = datetime.now().isoformat(timespec="seconds")
        updates["updated_at"] = now

        set_clause = ", ".join(f"{k} = ?" for k in updates)
        values = list(updates.values()) + [word_name]
        self._conn.execute(
            f"UPDATE personal_vocab SET {set_clause} WHERE word = ?",
            values,
        )
        self._conn.commit()
        return self._get_word_by_name(word_name)

    def delete_word(self, word_name: str) -> bool:
        """删除个人词库中的单词，返回是否成功"""
        cursor = self._conn.execute(
            "DELETE FROM personal_vocab WHERE word = ?", (word_name,)
        )
        self._conn.commit()
        return cursor.rowcount > 0

    def get_word(self, word_name: str) -> PersonalWord | None:
        """查询个人词库中的单词"""
        return self._get_word_by_name(word_name)

    def list_words(
        self,
        category: str | None = None,
        page: int = 1,
        per_page: int = 20,
    ) -> tuple[list[PersonalWord], int]:
        """列出个人词库单词，支持按分类筛选和分页"""
        if category:
            # 先获取分类 id
            cat_row = self._conn.execute(
                "SELECT id FROM vocab_categories WHERE name = ?", (category,)
            ).fetchone()
            if cat_row is None:
                return [], 0
            cat_id = cat_row["id"]

            count_row = self._conn.execute(
                """SELECT COUNT(*) as cnt FROM personal_vocab p
                   JOIN vocab_category_words cw ON p.id = cw.word_id
                   WHERE cw.category_id = ?""",
                (cat_id,),
            ).fetchone()
            total = count_row["cnt"]

            offset = (page - 1) * per_page
            rows = self._conn.execute(
                """SELECT p.* FROM personal_vocab p
                   JOIN vocab_category_words cw ON p.id = cw.word_id
                   WHERE cw.category_id = ?
                   ORDER BY p.created_at DESC
                   LIMIT ? OFFSET ?""",
                (cat_id, per_page, offset),
            ).fetchall()
        else:
            count_row = self._conn.execute(
                "SELECT COUNT(*) as cnt FROM personal_vocab"
            ).fetchone()
            total = count_row["cnt"]

            offset = (page - 1) * per_page
            rows = self._conn.execute(
                """SELECT * FROM personal_vocab
                   ORDER BY created_at DESC
                   LIMIT ? OFFSET ?""",
                (per_page, offset),
            ).fetchall()

        return [self._row_to_personal_word(r) for r in rows], total

    def get_word_count(self) -> int:
        """获取个人词库总词数"""
        row = self._conn.execute("SELECT COUNT(*) as cnt FROM personal_vocab").fetchone()
        return row["cnt"]

    # ---- 分类管理 ----

    def create_category(self, name: str, description: str = "") -> VocabCategory:
        """创建新分类"""
        now = datetime.now().isoformat(timespec="seconds")
        try:
            self._conn.execute(
                """INSERT INTO vocab_categories (name, description, is_system, created_at)
                   VALUES (?, ?, 0, ?)""",
                (name, description, now),
            )
            self._conn.commit()
        except sqlite3.IntegrityError:
            raise ValueError(f"分类 '{name}' 已存在")
        return self._get_category_by_name(name)

    def delete_category(self, name: str) -> bool:
        """删除分类（系统分类不可删除）"""
        cat = self._get_category_by_name(name)
        if cat is None:
            raise ValueError(f"分类 '{name}' 不存在")
        if cat.is_system:
            raise ValueError(f"系统分类 '{name}' 不可删除")
        self._conn.execute("DELETE FROM vocab_categories WHERE name = ?", (name,))
        self._conn.commit()
        return True

    def list_categories(self) -> list[VocabCategory]:
        """列出所有分类及其词数"""
        rows = self._conn.execute(
            """SELECT c.*, COUNT(cw.word_id) as word_count
               FROM vocab_categories c
               LEFT JOIN vocab_category_words cw ON c.id = cw.category_id
               GROUP BY c.id
               ORDER BY c.is_system DESC, c.name ASC"""
        ).fetchall()
        return [
            VocabCategory(
                id=r["id"],
                name=r["name"],
                description=r["description"],
                is_system=bool(r["is_system"]),
                word_count=r["word_count"],
                created_at=r["created_at"],
            )
            for r in rows
        ]

    def add_word_to_category(self, word_name: str, category_name: str) -> bool:
        """将单词添加到分类"""
        word = self._get_word_by_name(word_name)
        if word is None:
            raise ValueError(f"单词 '{word_name}' 不在个人词库中")
        cat = self._get_category_by_name(category_name)
        if cat is None:
            raise ValueError(f"分类 '{category_name}' 不存在")

        now = datetime.now().isoformat(timespec="seconds")
        try:
            self._conn.execute(
                """INSERT INTO vocab_category_words (category_id, word_id, added_at)
                   VALUES (?, ?, ?)""",
                (cat.id, word.id, now),
            )
            self._conn.commit()
        except sqlite3.IntegrityError:
            return False  # 已在该分类中
        return True

    def remove_word_from_category(self, word_name: str, category_name: str) -> bool:
        """从分类中移除单词"""
        word = self._get_word_by_name(word_name)
        if word is None:
            raise ValueError(f"单词 '{word_name}' 不在个人词库中")
        cat = self._get_category_by_name(category_name)
        if cat is None:
            raise ValueError(f"分类 '{category_name}' 不存在")

        cursor = self._conn.execute(
            "DELETE FROM vocab_category_words WHERE category_id = ? AND word_id = ?",
            (cat.id, word.id),
        )
        self._conn.commit()
        return cursor.rowcount > 0

    def get_word_categories(self, word_name: str) -> list[VocabCategory]:
        """获取单词所属的所有分类"""
        word = self._get_word_by_name(word_name)
        if word is None:
            return []
        rows = self._conn.execute(
            """SELECT c.* FROM vocab_categories c
               JOIN vocab_category_words cw ON c.id = cw.category_id
               WHERE cw.word_id = ?
               ORDER BY c.name""",
            (word.id,),
        ).fetchall()
        return [
            VocabCategory(
                id=r["id"],
                name=r["name"],
                description=r["description"],
                is_system=bool(r["is_system"]),
                created_at=r["created_at"],
            )
            for r in rows
        ]

    def add_mistake(self, word: Word | PersonalWord, source: str = "quiz_mistake") -> PersonalWord:
        """将错词添加到个人词库的 mistakes 分类（去重）"""
        existing = self._get_word_by_name(word.word)
        if existing is None:
            # 新建个人词库条目
            pw = PersonalWord(
                word=word.word,
                phonetic=getattr(word, "phonetic", ""),
                meaning=getattr(word, "meaning", ""),
                pos=getattr(word, "pos", ""),
                band=getattr(word, "band", 5),
                topic=getattr(word, "topic", ""),
                example=getattr(word, "example", ""),
                example_cn=getattr(word, "example_cn", ""),
                source=source,
            )
            existing = self.add_word(pw)

        # 添加到 mistakes 分类（去重由 PRIMARY KEY 约束保证）
        self.add_word_to_category(existing.word, "mistakes")
        return existing

    def add_from_grading(
        self, word: str, context: str = "", suggestion: str = "", comment: str = "",
    ) -> PersonalWord:
        """从写作批改结果中添加单词到个人词库

        Args:
            word: 单词或短语
            context: 原文语境（作为 example）
            suggestion: 修改建议（作为 example_cn）
            comment: 问题说明（作为 note）

        Returns:
            添加的 PersonalWord
        """
        existing = self._get_word_by_name(word)
        if existing is not None:
            return existing

        pw = PersonalWord(
            word=word,
            example=context,
            example_cn=suggestion,
            note=comment,
            source="grading",
        )
        return self.add_word(pw)

    def to_word(self, pw: PersonalWord) -> Word:
        """将 PersonalWord 转换为 Word 对象（用于复习系统集成）"""
        return Word(
            word=pw.word,
            phonetic=pw.phonetic,
            meaning=pw.meaning,
            pos=pw.pos,
            band=pw.band,
            topic=pw.topic,
            example=pw.example,
            example_cn=pw.example_cn,
            is_custom=True,
        )

    # ---- 统计 ----

    def get_category_stats(self) -> list[dict]:
        """获取各分类的统计信息

        Returns:
            [{"name": ..., "description": ..., "is_system": bool, "word_count": int}, ...]
        """
        cats = self.list_categories()
        return [
            {
                "name": c.name,
                "description": c.description,
                "is_system": c.is_system,
                "word_count": c.word_count,
            }
            for c in cats
        ]

    def get_source_distribution(self) -> dict[str, int]:
        """获取词库来源分布"""
        rows = self._conn.execute(
            """SELECT source, COUNT(*) as cnt
               FROM personal_vocab
               GROUP BY source
               ORDER BY cnt DESC"""
        ).fetchall()
        return {row["source"]: row["cnt"] for row in rows}

    def get_band_distribution(self) -> dict[int, int]:
        """获取个人词库的 band 分布"""
        rows = self._conn.execute(
            """SELECT band, COUNT(*) as cnt
               FROM personal_vocab
               GROUP BY band
               ORDER BY band"""
        ).fetchall()
        return {row["band"]: row["cnt"] for row in rows}

    # ---- 批量导入导出 ----

    def import_words(self, file_path: Path, vocab_service=None) -> dict[str, int]:
        """批量导入单词，支持 JSON / CSV / 纯文本格式

        JSON: [{"word": "...", "meaning": "...", ...}, ...]
        CSV: word,meaning,pos,band,topic (首行为表头)
        纯文本: 每行一个单词（自动从内置词库匹配）

        Args:
            file_path: 导入文件路径
            vocab_service: VocabService 实例（纯文本模式用于自动匹配）

        Returns:
            {"imported": N, "skipped": N, "failed": N}
        """
        suffix = file_path.suffix.lower()
        content = file_path.read_text(encoding="utf-8").strip()
        if not content:
            return {"imported": 0, "skipped": 0, "failed": 0}

        if suffix == ".json":
            words = self._parse_import_json(content)
        elif suffix == ".csv":
            words = self._parse_import_csv(content)
        else:
            words = self._parse_import_plain(content, vocab_service)

        return self._do_import(words)

    def export_words(
        self,
        fmt: str = "json",
        category: str | None = None,
    ) -> str:
        """导出个人词库为 JSON 或 CSV 字符串

        Args:
            fmt: 输出格式 "json" 或 "csv"
            category: 仅导出指定分类的词

        Returns:
            格式化的字符串内容
        """
        words, _ = self.list_words(category=category, page=1, per_page=999999)
        if not words:
            return "[]" if fmt == "json" else ""

        if fmt == "csv":
            return self._export_csv(words)
        return self._export_json(words)

    def _parse_import_json(self, content: str) -> list[PersonalWord]:
        """解析 JSON 格式导入"""
        try:
            data = json.loads(content)
        except json.JSONDecodeError:
            return []
        if not isinstance(data, list):
            return []
        result = []
        for item in data:
            if not isinstance(item, dict) or "word" not in item:
                continue
            try:
                pw = PersonalWord(
                    word=item["word"],
                    meaning=item.get("meaning", ""),
                    phonetic=item.get("phonetic", ""),
                    pos=item.get("pos", ""),
                    band=item.get("band", 5),
                    topic=item.get("topic", ""),
                    example=item.get("example", ""),
                    example_cn=item.get("example_cn", ""),
                    note=item.get("note", ""),
                    source="import",
                )
                result.append(pw)
            except Exception:
                continue
        return result

    def _parse_import_csv(self, content: str) -> list[PersonalWord]:
        """解析 CSV 格式导入（首行为表头）"""
        reader = csv.DictReader(io.StringIO(content))
        result = []
        for row in reader:
            if "word" not in row:
                continue
            try:
                band = int(row.get("band", 5))
                band = max(5, min(9, band))
            except (ValueError, TypeError):
                band = 5
            try:
                pw = PersonalWord(
                    word=row["word"].strip(),
                    meaning=row.get("meaning", "").strip(),
                    phonetic=row.get("phonetic", "").strip(),
                    pos=row.get("pos", "").strip(),
                    band=band,
                    topic=row.get("topic", "").strip(),
                    example=row.get("example", "").strip(),
                    example_cn=row.get("example_cn", "").strip(),
                    note=row.get("note", "").strip(),
                    source="import",
                )
                result.append(pw)
            except Exception:
                continue
        return result

    def _parse_import_plain(self, content: str, vocab_service=None) -> list[PersonalWord]:
        """解析纯文本格式（每行一个单词，自动匹配内置词库）"""
        lines = [line.strip() for line in content.splitlines() if line.strip()]
        result = []
        for word_text in lines:
            if vocab_service:
                builtin = vocab_service.get_word(word_text)
                if builtin:
                    pw = PersonalWord(
                        word=builtin.word,
                        phonetic=builtin.phonetic,
                        meaning=builtin.meaning,
                        pos=builtin.pos,
                        band=builtin.band,
                        topic=builtin.topic,
                        example=builtin.example,
                        example_cn=builtin.example_cn,
                        source="import",
                    )
                    result.append(pw)
                    continue
            pw = PersonalWord(word=word_text, source="import")
            result.append(pw)
        return result

    def _do_import(self, words: list[PersonalWord]) -> dict[str, int]:
        """执行批量导入"""
        imported = 0
        skipped = 0
        failed = 0
        for pw in words:
            if not pw.word.strip():
                failed += 1
                continue
            try:
                self.add_word(pw)
                imported += 1
            except ValueError:
                skipped += 1  # 已存在
            except Exception:
                failed += 1
        return {"imported": imported, "skipped": skipped, "failed": failed}

    def _export_json(self, words: list[PersonalWord]) -> str:
        """导出为 JSON"""
        data = []
        for w in words:
            data.append({
                "word": w.word,
                "phonetic": w.phonetic,
                "meaning": w.meaning,
                "pos": w.pos,
                "band": w.band,
                "topic": w.topic,
                "example": w.example,
                "example_cn": w.example_cn,
                "note": w.note,
            })
        return json.dumps(data, ensure_ascii=False, indent=2)

    def _export_csv(self, words: list[PersonalWord]) -> str:
        """导出为 CSV"""
        output = io.StringIO()
        writer = csv.DictWriter(
            output,
            fieldnames=["word", "phonetic", "meaning", "pos", "band", "topic", "example", "example_cn", "note"],
        )
        writer.writeheader()
        for w in words:
            writer.writerow({
                "word": w.word,
                "phonetic": w.phonetic,
                "meaning": w.meaning,
                "pos": w.pos,
                "band": w.band,
                "topic": w.topic,
                "example": w.example,
                "example_cn": w.example_cn,
                "note": w.note,
            })
        return output.getvalue()

    # ---- 内部方法 ----

    def _get_word_by_name(self, word_name: str) -> PersonalWord | None:
        row = self._conn.execute(
            "SELECT * FROM personal_vocab WHERE word = ?", (word_name,)
        ).fetchone()
        if row is None:
            return None
        return self._row_to_personal_word(row)

    def _get_category_by_name(self, name: str) -> VocabCategory | None:
        row = self._conn.execute(
            "SELECT * FROM vocab_categories WHERE name = ?", (name,)
        ).fetchone()
        if row is None:
            return None
        return VocabCategory(
            id=row["id"],
            name=row["name"],
            description=row["description"],
            is_system=bool(row["is_system"]),
            created_at=row["created_at"],
        )

    @staticmethod
    def _row_to_personal_word(row: sqlite3.Row) -> PersonalWord:
        return PersonalWord(
            id=row["id"],
            word=row["word"],
            phonetic=row["phonetic"],
            meaning=row["meaning"],
            pos=row["pos"],
            band=row["band"],
            topic=row["topic"],
            example=row["example"],
            example_cn=row["example_cn"],
            note=row["note"],
            source=row["source"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )
