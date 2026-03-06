你是一个 Python 开发者。在当前项目中继续实现 ielts-buddy CLI 工具的 Phase 1 MVP。

已有文件：
- docs/PRD.md — 产品需求文档
- docs/PLAN.md — 开发计划
- src/ielts_buddy/core/models.py — Pydantic 数据模型
- src/ielts_buddy/core/config.py — 配置管理
- src/ielts_buddy/data/vocab_band5.json — Band 5 词库
- src/ielts_buddy/data/vocab_band6.json — Band 6 词库

还需要实现：
1. 补充 Band 7/8/9 词库 JSON 文件（每个至少100个词）
2. src/ielts_buddy/services/vocab_service.py — 词库加载、随机抽词、按 band 筛选
3. src/ielts_buddy/services/review_service.py — 艾宾浩斯记忆曲线复习系统（用 SQLite）
4. src/ielts_buddy/services/stats_service.py — 学习统计
5. src/ielts_buddy/commands/vocab.py — 单词学习命令（ib vocab random/quiz/review）
6. src/ielts_buddy/commands/stats.py — 统计命令（ib stats show/today）
7. src/ielts_buddy/cli.py — CLI 入口（Click group）
8. 更新 pyproject.toml 的 entry_points
9. README.md

先读现有代码理解结构，然后逐个实现。确保代码能直接 pip install -e . && ib --help 运行。
