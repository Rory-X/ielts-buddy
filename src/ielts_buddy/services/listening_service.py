"""听力服务：听力资源浏览、听写测验生成"""

from __future__ import annotations

import json
import random
from importlib import resources
from pathlib import Path

from ielts_buddy.core.models import Word
from ielts_buddy.services.vocab_service import VocabService

# 资源文件名
_RESOURCES_FILE = "listening_resources.json"


def _load_resources() -> list[dict]:
    """加载听力资源 JSON"""
    data_pkg = resources.files("ielts_buddy") / "data"
    path = Path(str(data_pkg / _RESOURCES_FILE))
    with open(path, encoding="utf-8") as f:
        return json.load(f)


class ListeningService:
    """听力资源与听写测验服务"""

    def __init__(self) -> None:
        self._resources: list[dict] | None = None

    def _ensure_resources(self) -> list[dict]:
        """懒加载资源列表"""
        if self._resources is None:
            self._resources = _load_resources()
        return self._resources

    def get_resources(
        self,
        type: str | None = None,
        difficulty: str | None = None,
    ) -> list[dict]:
        """获取资源列表，支持按类型和难度筛选

        Args:
            type: 资源类型 (podcast/video/course/website)
            difficulty: 难度 (beginner/intermediate/advanced)

        Returns:
            匹配的资源列表
        """
        items = self._ensure_resources()
        if type is not None:
            items = [r for r in items if r["type"] == type.lower()]
        if difficulty is not None:
            items = [r for r in items if r["difficulty"] == difficulty.lower()]
        return items

    def get_resource_detail(self, idx: int) -> dict | None:
        """获取资源详情（按索引，从 1 开始）

        Args:
            idx: 资源序号 (1-based)

        Returns:
            资源字典，或 None（索引越界）
        """
        items = self._ensure_resources()
        if idx < 1 or idx > len(items):
            return None
        return items[idx - 1]

    def generate_dictation(
        self,
        words: list[Word],
        count: int = 10,
    ) -> list[dict]:
        """从给定单词列表中生成听写测验

        Args:
            words: 候选单词列表
            count: 抽取数量

        Returns:
            听写题列表，每项包含 word, phonetic, definition
        """
        if not words:
            return []
        count = min(count, len(words))
        selected = random.sample(words, count)
        return [
            {
                "word": w.word,
                "phonetic": w.phonetic,
                "definition": w.meaning,
            }
            for w in selected
        ]
