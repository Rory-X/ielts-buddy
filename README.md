# 📚 IELTS Buddy

> **在你写代码的地方，顺便把雅思考了。**

IELTS Buddy 是一款面向程序员的雅思备考 CLI 工具，将词汇学习、写作辅助、口语练习和科学复习整合到终端中。

![Python](https://img.shields.io/badge/Python-3.10+-blue?logo=python)
![Tests](https://img.shields.io/badge/Tests-350%20passed-brightgreen)
![License](https://img.shields.io/badge/License-MIT-yellow)

## ✨ 功能一览

| 模块 | 命令 | 说明 |
|------|------|------|
| 📖 词汇学习 | `ib vocab random` | 随机抽词，展示音标/释义/例句/搭配/词源 |
| 🔍 词库搜索 | `ib vocab search` | 按单词/释义/主题模糊搜索 |
| 📋 词库浏览 | `ib vocab list` | 按 Band/Topic 分页浏览 |
| 📊 词库概览 | `ib vocab info` | 各级别数量 + 主题分布柱状图 |
| ✏️ 英译中测验 | `ib vocab quiz` | 答对/答错自动记录 |
| 🔄 中译英测验 | `ib vocab quiz --mode zh2en` | 双向测验，提升主动产出 |
| 🧠 艾宾浩斯复习 | `ib vocab review` | 间隔重复 (0/1/2/4/7/15/30天) |
| 📈 学习统计 | `ib stats show` | 今日/总计/正确率/记忆等级分布 |
| 📉 趋势分析 | `ib stats trend` | 每日学习量 ASCII 柱状图 |
| 🎯 Band 进度 | `ib stats progress` | 各 Band 掌握比例进度条 |
| 📅 学习计划 | `ib plan show/set` | 目标 Band + 每日学习量 + 考试倒计时 |
| 🔗 数据导出 | `ib sync all` | 导出学习数据为 JSON（供飞书等平台导入） |
| 📧 每日邮件 | `ib email send` | HTML 学习报告邮件（昨日成果 + 待复习 + 推荐新词） |
| ✍️ 写作话题 | `ib write topics` | 40+ Task 2 话题库 |
| 📝 高分句型 | `ib write templates` | 30+ 句型模板 |
| 🔀 同义替换 | `ib write synonyms` | 50+ 组高分同义词 |
| 🎤 口语话题 | `ib speak topics` | Part 1/2/3 共 60+ 话题 |
| 🎯 口语练习 | `ib speak practice` | 随机抽题（题目 + 词汇 + 范文 + 技巧） |

## 🚀 快速开始

```bash
# 安装
git clone https://github.com/Rory-X/ielts-buddy.git
cd ielts-buddy
pip install -e .

# 开始学习
ib vocab random -n 5          # 随机学 5 个词
ib vocab quiz -n 10           # 英译中测验 10 题
ib vocab quiz --mode zh2en    # 中译英测验
ib vocab review               # 复习到期单词
ib stats show                 # 查看学习统计
```

## 📖 词库

内置 **526 个** 雅思核心词汇，覆盖 Band 5-9：

| Band | 数量 | 特征 |
|------|------|------|
| Band 5 | 131 | 基础高频词 |
| Band 6 | 80 | 进阶常用词 |
| Band 7 | 115 | 高分核心词 |
| Band 8 | 120 | 学术高阶词 |
| Band 9 | 80 | 低频冲刺词 |

每个词包含：音标、词性、中文释义、英文例句、中文翻译、常用搭配、同义词、词源分析、主题分类。

覆盖 12 个主题：education, environment, technology, health, society, culture, economy, science, media, travel, crime, government

## 🧠 艾宾浩斯复习

基于遗忘曲线的智能复习调度：

```
首次学习 → 1天后 → 2天后 → 4天后 → 7天后 → 15天后 → 30天后
```

每次复习根据答对/答错自动调整间隔，直到单词进入长期记忆。

## ✍️ 写作辅助

```bash
ib write topics                        # 浏览所有话题
ib write topics --category technology  # 按类别筛选
ib write templates --type introduction # 查看开头句型
ib write synonyms important            # 查同义替换
ib write vocab "人工智能"               # 话题高分词汇
```

## 🎤 口语练习

```bash
ib speak topics --part 2     # 浏览 Part 2 话题
ib speak practice --part 2   # 随机抽题练习
ib speak vocab "旅行"         # 话题关键词汇
```

每题包含：题目、关键词汇、参考范文、答题技巧。

## 📈 统计面板

```bash
ib stats show      # 概览（今日/累计/正确率/streak）
ib stats trend     # 每日学习趋势（7/30天）
ib stats progress  # Band 掌握进度条
ib stats history   # 学习日志
```

## 📧 每日邮件

```bash
ib email preview   # 预览邮件内容
ib email send      # 发送学习报告
```

HTML 邮件包含：昨日学习成果、今日待复习单词、推荐新词、Band 进度条。

## 📅 学习计划

```bash
ib plan set --band 7 --daily 30               # 设置目标
ib plan set --exam-date 2026-06-01            # 设置考试日期
ib plan show                                   # 查看今日计划
```

## 🔗 数据同步

```bash
ib sync vocab     # 导出词库（含掌握状态）
ib sync records   # 导出学习记录
ib sync stats     # 导出统计摘要
ib sync all       # 全部导出
```

导出为 JSON 格式到 `~/.ib/sync/`，可导入飞书多维表格等平台。

## 🛠 技术栈

- **CLI**: [Click](https://click.palletsprojects.com/)
- **美化**: [Rich](https://github.com/Textualize/rich)
- **数据模型**: [Pydantic](https://docs.pydantic.dev/)
- **存储**: SQLite + JSON
- **模板**: Jinja2
- **测试**: pytest (350 tests, 92%+ coverage)

## 📁 项目结构

```
src/ielts_buddy/
├── cli.py                 # CLI 入口
├── commands/
│   ├── vocab.py           # 词汇命令 (random/quiz/review/search/list/info)
│   ├── stats.py           # 统计命令 (show/trend/progress/history)
│   ├── plan.py            # 计划命令 (show/set)
│   ├── sync.py            # 同步命令 (vocab/records/stats/all)
│   ├── email.py           # 邮件命令 (preview/send)
│   ├── write.py           # 写作命令 (topics/templates/synonyms/vocab)
│   └── speak.py           # 口语命令 (topics/practice/vocab)
├── services/
│   ├── vocab_service.py   # 词库服务
│   ├── review_service.py  # 复习服务 (艾宾浩斯)
│   ├── stats_service.py   # 统计服务
│   ├── plan_service.py    # 计划服务
│   ├── sync_service.py    # 同步服务
│   ├── email_service.py   # 邮件服务
│   ├── writing_service.py # 写作服务
│   └── speaking_service.py# 口语服务
├── data/
│   ├── vocab_band[5-9].json    # 词库 (526词)
│   ├── writing_topics.json     # 写作话题 (40+)
│   ├── writing_templates.json  # 句型模板 (30+)
│   ├── synonyms.json           # 同义替换 (50+)
│   └── speaking_topics.json    # 口语话题 (60+)
└── templates/
    └── daily_email.html   # 邮件模板
```

## 🧪 测试

```bash
pytest                           # 运行全部 350 个测试
pytest --cov=ielts_buddy         # 覆盖率报告
pytest tests/test_services/      # 只跑服务层测试
pytest tests/test_commands/      # 只跑 CLI 测试
```

## 📋 开发路线

- [x] Phase 1 — MVP 核心闭环 (词汇/测验/复习/统计)
- [x] Phase 1.5 — 词库扩充/搜索/中译英/统计增强/学习计划
- [x] Phase 2 — 飞书同步/邮件升级
- [x] Phase 2.5 — 写作辅助/口语练习
- [ ] Phase 3 — 听力资源/网页报告/GitHub Pages

## 📄 License

MIT
