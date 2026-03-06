# Phase 2.5a — 写作辅助

先读 CLAUDE.md 了解项目。

## 任务

### 1. 新建 src/ielts_buddy/data/writing_topics.json
雅思写作 Task 2 话题库（40+ 话题），格式：
```json
[{"topic": "话题名", "question": "英文题目", "category": "education/environment/technology/health/society/culture/economy", "keywords": ["关键词"], "band7_vocab": ["高分词汇"]}]
```

### 2. 新建 src/ielts_buddy/data/writing_templates.json
高分句型模板（30+ 条），格式：
```json
[{"type": "introduction/body/conclusion/transition", "template": "英文句型", "translation": "中文翻译", "example": "使用示例"}]
```

### 3. 新建 src/ielts_buddy/data/synonyms.json
常用词同义替换（50+ 组），格式：
```json
[{"common": "important", "synonyms": ["crucial", "vital", "pivotal"], "context": "使用场景说明"}]
```

### 4. 新建 src/ielts_buddy/services/writing_service.py
- `get_topics(category=None)` — 获取话题列表
- `get_topic_detail(topic_id)` — 话题详情+对应词汇
- `get_templates(type=None)` — 获取句型模板
- `get_synonyms(word=None)` — 同义替换查询
- `get_writing_vocab(topic)` — 话题对应的高分词汇

### 5. 新建 src/ielts_buddy/commands/write.py
- `ib write topics [--category education]` — 浏览写作话题
- `ib write templates [--type introduction]` — 查看句型模板
- `ib write synonyms [word]` — 同义替换查询
- `ib write vocab <topic>` — 话题词汇
- 在 cli.py 注册

### 6. 写测试，确保全部 252 个旧测试不破坏

## 约束
- Rich 美化
- 中文注释和提示
- 向后兼容
