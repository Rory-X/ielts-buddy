# CLAUDE.md — ielts-buddy 项目指南

## 项目概述
IELTS 雅思词汇学习 CLI 工具，支持随机抽词、英译中测验、艾宾浩斯间隔重复复习和学习统计。

## 技术栈
- Python 3.10+, Click CLI, Rich (终端美化), Pydantic (数据模型)
- SQLite (复习记录存储)
- 安装: `pip install -e .` → CLI 命令 `ib` 或 `ielts`

## 目录结构
```
src/ielts_buddy/
├── __init__.py       # 版本号
├── cli.py            # Click group 入口，注册 vocab + stats
├── core/
│   ├── config.py     # 配置管理 (~/.ib/, 环境变量 IELTS_BUDDY_HOME)
│   └── models.py     # Pydantic 数据模型 (Word, ReviewRecord, Stats)
├── data/
│   ├── vocab_band5.json  # Band 5 词库 (131词)
│   ├── vocab_band6.json  # Band 6 词库 (80词)
│   └── vocab_band7.json  # Band 7 词库 (115词)
├── services/
│   ├── vocab_service.py   # 词库加载/随机抽词/搜索/按band筛选
│   ├── review_service.py  # 艾宾浩斯复习 (间隔: 0/1/2/4/7/15/30天, SQLite)
│   └── stats_service.py   # 学习统计 (今日/总计/正确率/等级分布)
└── commands/
    ├── vocab.py      # vocab random/quiz/review 命令
    └── stats.py      # stats show 命令

tests/
├── conftest.py             # 测试 fixtures (tmp_path, mock数据)
├── test_models.py          # 数据模型测试 (25个)
├── test_config.py          # 配置测试 (18个)
└── test_services/
    ├── test_vocab_service.py   # 词库服务测试 (30个)
    ├── test_review_service.py  # 复习服务测试 (29个)
    └── test_stats_service.py   # 统计服务测试 (9个)
└── test_commands/
    └── test_cli.py             # CLI命令测试 (17个)
```

## 关键命令
```bash
ib vocab random [-n 5] [-b 7]   # 随机抽词，支持按band筛选
ib vocab quiz [-n 10] [-b 7]    # 英译中测验，自动记录到SQLite
ib vocab review [-n 20]         # 复习到期单词（艾宾浩斯算法）
ib stats show                   # 学习统计面板
ib --version                    # 版本信息
```

## 测试
```bash
pytest                         # 运行全部 133 个测试
pytest --cov=ielts_buddy       # 覆盖率报告 (92%)
pytest tests/test_services/    # 只跑服务层测试
```

## 数据存储
- 词库: `src/ielts_buddy/data/vocab_band*.json` (JSON, 随包分发)
- 用户数据: `~/.ib/` (默认) 或 `$IELTS_BUDDY_HOME/`
  - `reviews.db` — SQLite, 复习记录

## 词库格式 (JSON)
```json
{
  "word": "contribute",
  "phonetic": "/kənˈtrɪbjuːt/",
  "pos": "v.",
  "definition": "贡献，促成",
  "example": {"en": "Many factors contribute...", "zh": "很多因素..."},
  "collocations": ["contribute to", "contribute significantly"],
  "synonyms": ["add to", "assist", "donate"],
  "etymology": "con- (一起) + tribute (给予) → 贡献",
  "topic": "society"
}
```

## 注意事项
- config.py 中 DB_PATH/APP_DIR 是延迟求值（函数调用），不在模块导入时固化
- quiz 命令的 KeyboardInterrupt 已处理（不会 crash）
- 词库没有重复词，所有字段 100% 完整
- Rich 表格在窄终端可能换行，建议 ≥80 列

## 未来迭代方向 (参考 docs/PRD.md)
- Phase 2: 听力练习、写作模板、口语话题
- Phase 3: AI 批改、模拟考试
- 更多词库 (Band 8+, 专题词库)
- 每日学习计划/提醒

## 相关文件
- PRD: docs/PRD.md (923行)
- 开发计划: docs/PLAN.md (761行)
- 测试报告: docs/TEST_REPORT.md
- 每日邮件: /home/node/clawd/scripts/daily-ielts-mail.py
