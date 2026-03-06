# Phase 2.5b — 口语练习

先读 CLAUDE.md 了解项目。

## 任务

### 1. 新建 src/ielts_buddy/data/speaking_topics.json
口语话题库（Part 1/2/3 各 20+ 话题），格式：
```json
[{"part": 1, "topic": "话题名", "questions": ["问题1","问题2"], "vocab": ["关键词汇"], "sample_answer": "范文片段", "tips": "答题技巧"}]
```

### 2. 新建 src/ielts_buddy/services/speaking_service.py
- `get_topics(part=None)` — 获取口语话题
- `get_topic_detail(topic_id)` — 话题详情
- `get_random_topic(part=None)` — 随机抽题练习
- `get_speaking_vocab(topic)` — 话题关键词汇

### 3. 新建 src/ielts_buddy/commands/speak.py
- `ib speak topics [--part 2]` — 浏览口语话题
- `ib speak practice [--part 2]` — 随机抽题练习（显示题目+词汇+范文+技巧）
- `ib speak vocab <topic>` — 话题词汇
- 在 cli.py 注册

### 4. 写测试，确保全部 301 个旧测试不破坏

## 约束
- Rich 美化，中文注释
- 向后兼容
