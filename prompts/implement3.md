实现 ielts-buddy CLI 工具。这是一个雅思英语学习CLI。

项目已有：
- pyproject.toml
- src/ielts_buddy/core/models.py (Pydantic数据模型)
- src/ielts_buddy/core/config.py (配置管理)
- src/ielts_buddy/data/vocab_band5.json (Band5词库)
- src/ielts_buddy/data/vocab_band6.json (Band6词库)

请按以下顺序逐个实现（每完成一个就写入文件）：

1. src/ielts_buddy/data/vocab_band7.json — Band7词库，至少100个词，格式同band5
2. src/ielts_buddy/services/vocab_service.py — 加载JSON词库、随机抽词、按band筛选
3. src/ielts_buddy/services/review_service.py — 艾宾浩斯复习（SQLite存储学习记录）
4. src/ielts_buddy/services/stats_service.py — 学习统计（今日/总计/正确率）
5. src/ielts_buddy/commands/vocab.py — Click命令：ib vocab random/quiz/review
6. src/ielts_buddy/commands/stats.py — Click命令：ib stats show
7. src/ielts_buddy/cli.py — Click group入口
8. 更新 pyproject.toml 添加 entry_points console_scripts ib=ielts_buddy.cli:cli

先读现有的 models.py 和 config.py 理解数据结构，然后开始写代码。
