"""词库服务：加载 JSON 词库、随机抽词、按 band 筛选"""

from __future__ import annotations

import json
import random
from importlib import resources
from pathlib import Path

from ielts_buddy.core.models import Word


# 内置词库文件映射
_BAND_FILES = {
    5: "vocab_band5.json",
    6: "vocab_band6.json",
    7: "vocab_band7.json",
}


def _load_json_file(path: Path) -> list[dict]:
    """从 JSON 文件加载词条列表"""
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _builtin_data_path(filename: str) -> Path:
    """获取内置数据文件路径"""
    data_pkg = resources.files("ielts_buddy") / "data"
    return Path(str(data_pkg / filename))


class VocabService:
    """词库服务"""

    def __init__(self) -> None:
        self._words: list[Word] = []
        self._loaded_bands: set[int] = set()

    def load_band(self, band: int) -> None:
        """加载指定 band 等级的内置词库"""
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

    def load_all(self) -> None:
        """加载所有内置词库"""
        for band in _BAND_FILES:
            self.load_band(band)

    def load_custom(self, path: Path) -> None:
        """加载用户自定义词库文件"""
        raw = _load_json_file(path)
        for item in raw:
            item["is_custom"] = True
            self._words.append(Word(**item))

    @property
    def words(self) -> list[Word]:
        return list(self._words)

    def filter_by_band(self, band: int) -> list[Word]:
        """按 band 等级筛选"""
        return [w for w in self._words if w.band == band]

    def filter_by_topic(self, topic: str) -> list[Word]:
        """按主题筛选"""
        topic_lower = topic.lower()
        return [w for w in self._words if w.topic.lower() == topic_lower]

    def search(self, keyword: str) -> list[Word]:
        """按关键词搜索（匹配 word 或 meaning）"""
        kw = keyword.lower()
        return [
            w for w in self._words
            if kw in w.word.lower() or kw in w.meaning
        ]

    def random_words(self, count: int = 10, band: int | None = None) -> list[Word]:
        """随机抽取指定数量的单词"""
        pool = self.filter_by_band(band) if band else self._words
        if not pool:
            return []
        count = min(count, len(pool))
        return random.sample(pool, count)

    def get_topics(self) -> list[str]:
        """获取所有可用主题"""
        return sorted({w.topic for w in self._words if w.topic})

    def get_bands(self) -> list[int]:
        """获取所有已加载的 band 等级"""
        return sorted(self._loaded_bands)

    def count(self, band: int | None = None) -> int:
        """统计单词数量"""
        if band is not None:
            return len(self.filter_by_band(band))
        return len(self._words)
