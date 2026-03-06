# Phase 1.5a — 词库扩充 + 搜索 + 中译英

你正在开发 ielts-buddy CLI 工具的 v0.2.0 版本。先读 CLAUDE.md 了解项目。

## 任务清单

### 1. 词库扩充
- 创建 `src/ielts_buddy/data/vocab_band8.json` — 120+ 个 Band 8 高阶学术词汇
- 创建 `src/ielts_buddy/data/vocab_band9.json` — 80+ 个 Band 9 冲刺词汇
- 词汇格式与现有 band5/6/7 完全一致：
  ```json
  {
    "word": "xxx",
    "phonetic": "/xxx/",
    "pos": "n./v./adj./adv.",
    "definition": "中文释义",
    "example": {"en": "英文例句", "zh": "中文翻译"},
    "collocations": ["搭配1", "搭配2"],
    "synonyms": ["同义词1", "同义词2"],
    "etymology": "词源分析",
    "topic": "主题"
  }
  ```
- Band 8 词汇特征：学术高频但不常见（如 exacerbate, ubiquitous, pragmatic）
- Band 9 词汇特征：低频高分（如 obfuscate, quintessential, sycophant）
- 主题覆盖：education, environment, technology, health, society, culture, economy, science

### 2. 词库搜索命令
- 在 `commands/vocab.py` 中新增 `ib vocab search <keyword>` 命令
- 支持按 word / definition / topic 模糊搜索
- 结果用 Rich 表格展示

### 3. 词库浏览命令
- 新增 `ib vocab list --band 7 --topic education` 命令
- 支持 --band 和 --topic 筛选，分页显示（默认每页 20 个）
- 新增 `ib vocab info` 命令显示词库概览（各 Band 数量、主题分布）

### 4. 中译英测验
- 在 `commands/vocab.py` 中扩展 quiz 命令
- `ib vocab quiz --mode en2zh` 英译中（现有）
- `ib vocab quiz --mode zh2en` 中译英（新增）
- `ib vocab quiz --mode mix` 混合模式（随机选方向）
- 中译英时显示中文释义，用户输入英文单词
- 拼写校验：忽略大小写、首尾空格

### 5. vocab_service.py 更新
- `search_words(keyword)` — 模糊搜索
- `list_words(band=None, topic=None, page=1, per_page=20)` — 分页列表
- `get_vocab_stats()` — 词库统计信息
- 自动加载 band8/band9 词库

### 6. 更新测试
- 为所有新功能编写 pytest 测试
- 确保现有 133 个测试不被破坏

## 重要约束
- 不要修改现有文件的接口（向后兼容）
- 词库 JSON 文件必须是有效的 JSON array
- 所有中文注释和提示信息
- 用 Rich 做终端美化
