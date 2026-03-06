"""词库服务：加载 JSON 词库、随机抽词、按 band 筛选、内存索引加速"""

from __future__ import annotations

import json
import os
import random
import sqlite3
import time
from importlib import resources
from pathlib import Path

from ielts_buddy.core.config import get_app_dir
from ielts_buddy.core.models import Word


# 内置词库文件映射（精选子集）
_BAND_FILES = {
    5: "vocab_band5.json",
    6: "vocab_band6.json",
    7: "vocab_band7.json",
    8: "vocab_band8.json",
    9: "vocab_band9.json",
}

# 大词库文件
_MASTER_FILE = "vocab_master.json"


def _load_json_file(path: Path) -> list[dict]:
    """从 JSON 文件加载词条列表"""
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _builtin_data_path(filename: str) -> Path:
    """获取内置数据文件路径"""
    data_pkg = resources.files("ielts_buddy") / "data"
    return Path(str(data_pkg / filename))


def _normalize_master_entry(item: dict) -> dict:
    """将 master 词库的字段格式统一为 Word 模型格式

    master 词库使用 'definition' 而非 'meaning'，
    'example' 是 {en, zh} 字典而非纯字符串。
    """
    normalized = dict(item)

    # definition → meaning
    if "definition" in normalized and "meaning" not in normalized:
        raw_def = normalized.pop("definition")
        # 清理前导 '] n. ' 等噪音
        if isinstance(raw_def, str):
            # 去掉开头的 '] ' 或 '] n. ' 等模式
            cleaned = raw_def.lstrip("] ").strip()
            # 如果清理后以 'n. ' / 'v. ' / 'a. ' 等开头，再去掉词性前缀
            for prefix in ("n. ", "v. ", "a. ", "ad. ", "vt. ", "vi. ", "adj. ", "adv. "):
                if cleaned.lower().startswith(prefix):
                    cleaned = cleaned[len(prefix):]
                    break
            normalized["meaning"] = cleaned
        else:
            normalized["meaning"] = str(raw_def)

    # example: {en, zh} → example + example_cn
    example = normalized.get("example")
    if isinstance(example, dict):
        normalized["example"] = example.get("en", "")
        normalized["example_cn"] = example.get("zh", "")

    return normalized


# ---- SQLite 词库缓存 ----

_CACHE_SCHEMA = """
CREATE TABLE IF NOT EXISTS vocab_cache (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    word TEXT NOT NULL,
    phonetic TEXT DEFAULT '',
    meaning TEXT NOT NULL,
    pos TEXT DEFAULT '',
    band INTEGER NOT NULL,
    topic TEXT DEFAULT '',
    example TEXT DEFAULT '',
    example_cn TEXT DEFAULT '',
    collocations TEXT DEFAULT '[]',
    synonyms TEXT DEFAULT '[]',
    etymology TEXT DEFAULT ''
);
CREATE INDEX IF NOT EXISTS idx_vocab_word ON vocab_cache(word);
CREATE INDEX IF NOT EXISTS idx_vocab_band ON vocab_cache(band);
CREATE INDEX IF NOT EXISTS idx_vocab_topic ON vocab_cache(topic);

CREATE TABLE IF NOT EXISTS cache_meta (
    key TEXT PRIMARY KEY,
    value TEXT
);
"""


def _get_cache_db_path() -> Path:
    """获取词库缓存 SQLite 路径"""
    return get_app_dir() / "vocab_cache.db"


def _master_json_mtime() -> float:
    """获取 master JSON 的修改时间"""
    try:
        path = _builtin_data_path(_MASTER_FILE)
        return os.path.getmtime(path)
    except (FileNotFoundError, OSError):
        return 0.0


def _cache_is_valid(cache_path: Path) -> bool:
    """检查缓存是否有效（JSON 未修改）"""
    if not cache_path.exists():
        return False
    try:
        conn = sqlite3.connect(str(cache_path))
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            "SELECT value FROM cache_meta WHERE key = 'json_mtime'"
        ).fetchone()
        conn.close()
        if row is None:
            return False
        cached_mtime = float(row["value"])
        return cached_mtime == _master_json_mtime()
    except Exception:
        return False


def _build_cache(words: list[Word], cache_path: Path) -> None:
    """将词库写入 SQLite 缓存"""
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    # 删除旧缓存重建
    if cache_path.exists():
        cache_path.unlink()

    conn = sqlite3.connect(str(cache_path))
    conn.executescript(_CACHE_SCHEMA)

    rows = [
        (
            w.word, w.phonetic, w.meaning, w.pos, w.band, w.topic,
            w.example, w.example_cn,
            json.dumps(w.collocations, ensure_ascii=False),
            json.dumps(w.synonyms, ensure_ascii=False),
            w.etymology,
        )
        for w in words
    ]
    conn.executemany(
        """INSERT INTO vocab_cache
           (word, phonetic, meaning, pos, band, topic, example, example_cn,
            collocations, synonyms, etymology)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        rows,
    )
    conn.execute(
        "INSERT OR REPLACE INTO cache_meta (key, value) VALUES ('json_mtime', ?)",
        (str(_master_json_mtime()),),
    )
    conn.commit()
    conn.close()


def _load_from_cache(cache_path: Path) -> list[Word]:
    """从 SQLite 缓存加载词库"""
    conn = sqlite3.connect(str(cache_path))
    conn.row_factory = sqlite3.Row
    rows = conn.execute("SELECT * FROM vocab_cache").fetchall()
    conn.close()

    words = []
    for row in rows:
        words.append(Word(
            word=row["word"],
            phonetic=row["phonetic"],
            meaning=row["meaning"],
            pos=row["pos"],
            band=row["band"],
            topic=row["topic"],
            example=row["example"],
            example_cn=row["example_cn"],
            collocations=json.loads(row["collocations"]) if row["collocations"] else [],
            synonyms=json.loads(row["synonyms"]) if row["synonyms"] else [],
            etymology=row["etymology"],
        ))
    return words


class VocabService:
    """词库服务，支持大词库 + 精选词库，内置内存索引加速搜索"""

    def __init__(self) -> None:
        self._words: list[Word] = []
        self._loaded_bands: set[int] = set()
        self._source: str = ""  # "master" / "curated" / ""

        # 内存索引（懒构建）
        self._word_index: dict[str, Word] | None = None
        self._band_index: dict[int, list[Word]] | None = None
        self._topic_index: dict[str, list[Word]] | None = None
        self._search_index: list[tuple[str, Word]] | None = None

    def _invalidate_indexes(self) -> None:
        """词库变更时清除索引缓存"""
        self._word_index = None
        self._band_index = None
        self._topic_index = None
        self._search_index = None

    def _ensure_word_index(self) -> dict[str, Word]:
        """确保 word 精确查找索引已构建"""
        if self._word_index is None:
            self._word_index = {w.word.lower(): w for w in self._words}
        return self._word_index

    def _ensure_band_index(self) -> dict[int, list[Word]]:
        """确保 band 分组索引已构建"""
        if self._band_index is None:
            idx: dict[int, list[Word]] = {}
            for w in self._words:
                idx.setdefault(w.band, []).append(w)
            self._band_index = idx
        return self._band_index

    def _ensure_topic_index(self) -> dict[str, list[Word]]:
        """确保 topic 分组索引已构建"""
        if self._topic_index is None:
            idx: dict[str, list[Word]] = {}
            for w in self._words:
                key = w.topic.lower()
                idx.setdefault(key, []).append(w)
            self._topic_index = idx
        return self._topic_index

    def _ensure_search_index(self) -> list[tuple[str, Word]]:
        """确保模糊搜索索引已构建（word+meaning 拼接小写文本）"""
        if self._search_index is None:
            self._search_index = [
                (f"{w.word.lower()} {w.meaning.lower()} {w.topic.lower()}", w)
                for w in self._words
            ]
        return self._search_index

    # ---- 加载方法 ----

    def load_band(self, band: int) -> None:
        """加载指定 band 等级的内置精选词库"""
        if band in self._loaded_bands:
            return
        filename = _BAND_FILES.get(band)
        if filename is None:
            raise ValueError(f"不支持的 band 等级: {band}，可选: {sorted(_BAND_FILES)}")
        path = _builtin_data_path(filename)
        raw = _load_json_file(path)
        for item in raw:
            item.setdefault("band", band)
            self._words.append(Word(**item))
        self._loaded_bands.add(band)
        self._invalidate_indexes()

    def load_all(self) -> None:
        """加载所有内置精选词库（curated）"""
        for band in _BAND_FILES:
            self.load_band(band)
        self._source = "curated"

    def load_master(self) -> None:
        """加载大词库（vocab_master.json），优先使用 SQLite 缓存"""
        if self._source == "master":
            return  # 已加载

        cache_path = _get_cache_db_path()
        if _cache_is_valid(cache_path):
            # 从缓存加载
            cached_words = _load_from_cache(cache_path)
            self._words = cached_words
        else:
            # 从 JSON 加载并构建缓存
            path = _builtin_data_path(_MASTER_FILE)
            raw = _load_json_file(path)
            self._words = []
            for item in raw:
                normalized = _normalize_master_entry(item)
                self._words.append(Word(**normalized))
            # 异步写缓存（不阻塞主流程）
            try:
                _build_cache(self._words, cache_path)
            except Exception:
                pass  # 缓存写入失败不影响使用

        self._loaded_bands = {w.band for w in self._words}
        self._source = "master"
        self._invalidate_indexes()

    def load_custom(self, path: Path) -> None:
        """加载用户自定义词库文件"""
        raw = _load_json_file(path)
        for item in raw:
            item["is_custom"] = True
            self._words.append(Word(**item))
        self._invalidate_indexes()

    @property
    def source(self) -> str:
        """当前加载的词库来源: 'master' / 'curated' / ''"""
        return self._source

    @property
    def words(self) -> list[Word]:
        return list(self._words)

    # ---- 查询方法（使用索引加速）----

    def filter_by_band(self, band: int) -> list[Word]:
        """按 band 等级筛选（使用索引 O(1) 查找）"""
        idx = self._ensure_band_index()
        return list(idx.get(band, []))

    def filter_by_topic(self, topic: str) -> list[Word]:
        """按主题筛选（使用索引 O(1) 查找）"""
        idx = self._ensure_topic_index()
        return list(idx.get(topic.lower(), []))

    def search(self, keyword: str) -> list[Word]:
        """按关键词搜索（使用搜索索引）"""
        kw = keyword.lower()

        # 精确匹配优先
        word_idx = self._ensure_word_index()
        if kw in word_idx:
            exact = word_idx[kw]
            # 还需要收集其他匹配（meaning/topic 包含关键词的）
            search_idx = self._ensure_search_index()
            others = [w for text, w in search_idx if kw in text and w is not exact]
            return [exact] + others

        # 模糊搜索
        search_idx = self._ensure_search_index()
        return [w for text, w in search_idx if kw in text]

    def search_words(self, keyword: str) -> list[Word]:
        """按关键词模糊搜索（匹配 word、meaning 或 topic）"""
        return self.search(keyword)

    def get_word(self, word: str) -> Word | None:
        """精确查找单词（O(1)）"""
        idx = self._ensure_word_index()
        return idx.get(word.lower())

    def list_words(
        self,
        band: int | None = None,
        topic: str | None = None,
        page: int = 1,
        per_page: int = 20,
    ) -> tuple[list[Word], int]:
        """分页列表，返回 (当前页单词列表, 总数)"""
        # 使用索引快速筛选
        if band is not None and topic is not None:
            # 双条件：取 band 索引的交集
            band_words = set(id(w) for w in self.filter_by_band(band))
            pool = [w for w in self.filter_by_topic(topic) if id(w) in band_words]
        elif band is not None:
            pool = self.filter_by_band(band)
        elif topic is not None:
            pool = self.filter_by_topic(topic)
        else:
            pool = list(self._words)

        total = len(pool)
        start = (page - 1) * per_page
        end = start + per_page
        return pool[start:end], total

    def get_vocab_stats(self) -> dict:
        """获取词库统计信息：各 band 数量、主题分布"""
        band_idx = self._ensure_band_index()
        topic_idx = self._ensure_topic_index()

        band_counts = {band: len(words) for band, words in sorted(band_idx.items())}
        topic_counts = {topic: len(words) for topic, words in sorted(topic_idx.items())}

        # 过滤空 topic key
        topic_counts = {k: v for k, v in topic_counts.items() if k}

        return {
            "total": len(self._words),
            "bands": band_counts,
            "topics": topic_counts,
            "source": self._source,
        }

    def random_words(self, count: int = 10, band: int | None = None) -> list[Word]:
        """随机抽取指定数量的单词"""
        pool = self.filter_by_band(band) if band else self._words
        if not pool:
            return []
        count = min(count, len(pool))
        return random.sample(pool, count)

    def get_topics(self) -> list[str]:
        """获取所有可用主题"""
        idx = self._ensure_topic_index()
        return sorted(k for k in idx if k)

    def get_bands(self) -> list[int]:
        """获取所有已加载的 band 等级"""
        return sorted(self._loaded_bands)

    def count(self, band: int | None = None) -> int:
        """统计单词数量"""
        if band is not None:
            return len(self.filter_by_band(band))
        return len(self._words)
