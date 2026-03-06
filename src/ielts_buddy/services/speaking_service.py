"""口语练习服务：话题浏览、随机抽题、话题词汇"""

from __future__ import annotations

import json
import random
from importlib import resources
from pathlib import Path


def _builtin_data_path(filename: str) -> Path:
    """获取内置数据文件路径"""
    data_pkg = resources.files("ielts_buddy") / "data"
    return Path(str(data_pkg / filename))


def _load_json(filename: str) -> list[dict]:
    """加载内置 JSON 数据文件"""
    path = _builtin_data_path(filename)
    with open(path, encoding="utf-8") as f:
        return json.load(f)


class SpeakingService:
    """口语练习服务"""

    def __init__(self) -> None:
        self._topics: list[dict] | None = None

    def _ensure_topics(self) -> list[dict]:
        """延迟加载话题数据"""
        if self._topics is None:
            self._topics = _load_json("speaking_topics.json")
        return self._topics

    # ── 话题列表 ──

    def get_topics(self, part: int | None = None) -> list[dict]:
        """获取口语话题列表，可按 Part 筛选"""
        topics = self._ensure_topics()
        if part is not None:
            topics = [t for t in topics if t["part"] == part]
        return topics

    # ── 话题详情 ──

    def get_topic_detail(self, topic_id: int) -> dict | None:
        """获取话题详情（按索引，从 1 开始）"""
        topics = self._ensure_topics()
        idx = topic_id - 1
        if 0 <= idx < len(topics):
            return topics[idx]
        return None

    # ── 随机抽题 ──

    def get_random_topic(self, part: int | None = None) -> dict | None:
        """随机抽取一个口语话题"""
        topics = self.get_topics(part)
        if not topics:
            return None
        return random.choice(topics)

    # ── 话题词汇 ──

    def get_speaking_vocab(self, topic: str) -> dict | None:
        """获取话题关键词汇，按话题名模糊匹配"""
        topics = self._ensure_topics()
        topic_lower = topic.lower()
        for t in topics:
            if topic_lower in t["topic"].lower():
                return {
                    "part": t["part"],
                    "topic": t["topic"],
                    "vocab": t["vocab"],
                    "questions": t["questions"],
                }
        return None

    # ── 统计 ──

    def get_parts(self) -> list[int]:
        """获取所有可用的 Part 编号"""
        topics = self._ensure_topics()
        return sorted({t["part"] for t in topics})

    def count(self, part: int | None = None) -> int:
        """统计话题数量"""
        return len(self.get_topics(part))
