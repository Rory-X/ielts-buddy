"""写作辅助服务：话题、句型模板、同义替换"""

from __future__ import annotations

import json
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


class WritingService:
    """写作辅助服务"""

    def __init__(self) -> None:
        self._topics: list[dict] | None = None
        self._templates: list[dict] | None = None
        self._synonyms: list[dict] | None = None

    def _ensure_topics(self) -> list[dict]:
        """延迟加载话题数据"""
        if self._topics is None:
            self._topics = _load_json("writing_topics.json")
        return self._topics

    def _ensure_templates(self) -> list[dict]:
        """延迟加载模板数据"""
        if self._templates is None:
            self._templates = _load_json("writing_templates.json")
        return self._templates

    def _ensure_synonyms(self) -> list[dict]:
        """延迟加载同义替换数据"""
        if self._synonyms is None:
            self._synonyms = _load_json("synonyms.json")
        return self._synonyms

    # ── 话题相关 ──

    def get_topics(self, category: str | None = None) -> list[dict]:
        """获取话题列表，可按分类筛选"""
        topics = self._ensure_topics()
        if category:
            cat_lower = category.lower()
            topics = [t for t in topics if t["category"].lower() == cat_lower]
        return topics

    def get_categories(self) -> list[str]:
        """获取所有话题分类"""
        topics = self._ensure_topics()
        return sorted({t["category"] for t in topics})

    def get_topic_detail(self, topic_id: int) -> dict | None:
        """获取话题详情（按索引，从 1 开始）"""
        topics = self._ensure_topics()
        idx = topic_id - 1
        if 0 <= idx < len(topics):
            return topics[idx]
        return None

    # ── 句型模板相关 ──

    def get_templates(self, type: str | None = None) -> list[dict]:
        """获取句型模板，可按类型筛选"""
        templates = self._ensure_templates()
        if type:
            type_lower = type.lower()
            templates = [t for t in templates if t["type"].lower() == type_lower]
        return templates

    def get_template_types(self) -> list[str]:
        """获取所有模板类型"""
        templates = self._ensure_templates()
        return sorted({t["type"] for t in templates})

    # ── 同义替换相关 ──

    def get_synonyms(self, word: str | None = None) -> list[dict]:
        """查询同义替换，可按常用词筛选（模糊匹配）"""
        synonyms = self._ensure_synonyms()
        if word:
            word_lower = word.lower()
            synonyms = [
                s for s in synonyms
                if word_lower in s["common"].lower()
                or any(word_lower in syn.lower() for syn in s["synonyms"])
            ]
        return synonyms

    # ── 话题词汇 ──

    def get_writing_vocab(self, topic: str) -> dict | None:
        """获取话题对应的高分词汇，按话题名模糊匹配"""
        topics = self._ensure_topics()
        topic_lower = topic.lower()
        for t in topics:
            if topic_lower in t["topic"].lower() or topic_lower in t["question"].lower():
                return {
                    "topic": t["topic"],
                    "question": t["question"],
                    "category": t["category"],
                    "keywords": t["keywords"],
                    "band7_vocab": t["band7_vocab"],
                }
        return None
