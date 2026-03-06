# IELTS Buddy — 产品需求文档 (PRD)

> 版本：v1.0 | 日期：2026-03-06

---

## 1. 产品定位与目标用户

### 1.1 产品定位

**IELTS Buddy** 是一款面向雅思考生的命令行英语学习工具。它将雅思核心词汇、记忆科学、学习数据管理和多媒体资源整合到一个简洁的 CLI 界面中，让备考者能够在终端中高效完成日常英语学习闭环。

核心理念：**在你写代码的地方，顺便把雅思考了。**

### 1.2 目标用户

| 用户画像 | 描述 |
|---------|------|
| **主要用户** | 正在备考雅思的程序员 / 技术人员，习惯在终端工作 |
| **次要用户** | 使用飞书办公、希望将英语学习融入日常工作流的职场人 |
| **潜在用户** | 任何喜欢 CLI 工具、追求效率的英语学习者 |

### 1.3 核心价值主张

- **零切换成本**：不需要打开 App，在终端中直接学习
- **科学记忆**：基于艾宾浩斯遗忘曲线的智能复习调度
- **飞书协同**：将学习数据同步到飞书多维表格，支持团队学习
- **数据驱动**：完整的学习数据追踪，生成可视化学习报告网页

---

## 2. 核心功能模块

共 10 个功能模块，按优先级排列：

| # | 模块名称 | 优先级 | MVP |
|---|---------|--------|-----|
| 1 | 词库管理 | P0 | Yes |
| 2 | 单词学习 | P0 | Yes |
| 3 | 单词测试 | P0 | Yes |
| 4 | 记忆复习（艾宾浩斯） | P0 | Yes |
| 5 | 学习统计 | P0 | Yes |
| 6 | 飞书多维表格集成 | P1 | No |
| 7 | 每日学习网页生成 | P1 | No |
| 8 | 听力练习资源 | P1 | No |
| 9 | 写作练习辅助 | P2 | No |
| 10 | 口语话题练习 | P2 | No |

---

## 3. 功能详细设计

### 3.1 词库管理

**描述**：内置雅思核心词汇库，按 Band 5-9 分级，支持按场景主题分类。用户可查看、筛选、搜索词库内容，也可以添加自定义单词。

**用户故事**：
- 作为雅思考生，我想浏览目标 Band 分数段的词汇，以便制定学习计划
- 作为用户，我想搜索某个单词是否在雅思词库中，以及它属于哪个级别
- 作为用户，我想添加自己遇到的生词到个人词库

**CLI 命令设计**：

```bash
# 查看词库概览（各级别词汇数量统计）
ielts vocab stats

# 按 Band 级别列出单词（支持分页）
ielts vocab list --band 7 --page 1

# 按主题场景筛选
ielts vocab list --topic education

# 搜索单词
ielts vocab search "abundant"

# 添加自定义单词
ielts vocab add "ubiquitous" --meaning "无处不在的" --band 8 --topic technology

# 导入/导出词库
ielts vocab export --format csv --output my_words.csv
ielts vocab import --file my_words.csv
```

**词库分类体系**：

- **按 Band 分级**：Band 5 (基础) → Band 6 (进阶) → Band 7 (高分) → Band 8-9 (冲刺)
- **按主题场景**：education, environment, technology, health, society, culture, economy, science, media, travel, crime, government

---

### 3.2 单词学习

**描述**：随机或按规则抽取单词进行学习。以交互式卡片形式展示单词的释义、例句、搭配和助记信息。

**用户故事**：
- 作为考生，我想每天随机学习 50 个新词，逐步扩大词汇量
- 作为考生，我想专注学习某个 Band 级别或主题的词汇
- 作为考生，我想看到单词在雅思真题语境中的用法

**CLI 命令设计**：

```bash
# 随机学习 50 个单词（默认）
ielts learn

# 指定数量和级别
ielts learn --count 30 --band 7

# 按主题学习
ielts learn --topic environment --count 20

# 只学习新词（排除已学过的）
ielts learn --new-only

# 交互模式：逐个展示，按回车翻页，输入 y 标记为已掌握
ielts learn --interactive
```

**交互式学习流程**：

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  📖  Word 1/50  |  Band 7  |  education
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  scrutinize  /ˈskruːtənaɪz/

  [名词] 仔细审查，详细检查

  例句: The examiner will scrutinize your essay
        for grammatical accuracy.

  搭配: scrutinize closely / scrutinize the data

  词根: scrutin- (检查) + -ize (动词后缀)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  [Enter] 下一个  [y] 已掌握  [s] 收藏  [q] 退出
```

---

### 3.3 单词测试

**描述**：提供多种测试模式检验学习效果，包括英译中、中译英、拼写测试、选择题。测试结果记录到学习历史中。

**用户故事**：
- 作为考生，我想通过测试检验自己对单词的掌握程度
- 作为考生，我想重点测试自己标记为"困难"的单词
- 作为考生，我想看到测试后的正确率统计

**CLI 命令设计**：

```bash
# 默认测试（50 个单词，混合题型）
ielts test

# 指定测试类型
ielts test --mode spelling     # 拼写测试：看中文写英文
ielts test --mode meaning      # 释义测试：看英文选中文
ielts test --mode choice       # 四选一选择题
ielts test --mode context      # 完形填空：在句子中填入正确单词

# 指定范围
ielts test --band 7 --count 30

# 只测试收藏/困难词
ielts test --difficult
ielts test --starred

# 测试今天学过的词
ielts test --today
```

**测试结果输出**：

```
━━━━━━━━━━━━  测试报告  ━━━━━━━━━━━━━
  总题数: 50
  正确:   38 (76%)
  错误:   12 (24%)

  Band 7 正确率: 82%
  Band 8 正确率: 64%

  易错词:
    - ubiquitous   (连续 3 次错误)
    - exacerbate   (连续 2 次错误)
    - pragmatic    (首次错误)

  建议: 重点复习 Band 8 词汇，
        易错词已自动加入明日复习计划。
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

---

### 3.4 记忆复习（艾宾浩斯）

**描述**：基于艾宾浩斯遗忘曲线算法，自动计算每个单词的最佳复习时间，在合适的间隔提醒用户复习。复习间隔为：1天、2天、4天、7天、15天、30天。

**用户故事**：
- 作为考生，我想每天打开终端就知道今天需要复习哪些单词
- 作为考生，我想让系统根据我的记忆情况自动调整复习频率
- 作为考生，我想看到每个单词的记忆强度

**CLI 命令设计**：

```bash
# 开始今日复习（自动加载需要复习的单词）
ielts review

# 查看复习计划（今天/本周待复习数量）
ielts review plan

# 查看某个单词的记忆曲线
ielts review status "scrutinize"

# 重置某个单词的记忆进度
ielts review reset "scrutinize"
```

**记忆等级**：

| 等级 | 状态 | 复习间隔 | 说明 |
|-----|------|---------|------|
| 0 | 新词 | - | 尚未学习 |
| 1 | 初识 | 1 天 | 第一次学习后 |
| 2 | 熟悉 | 2 天 | 第一次复习正确 |
| 3 | 记住 | 4 天 | 第二次复习正确 |
| 4 | 掌握 | 7 天 | 第三次复习正确 |
| 5 | 牢固 | 15 天 | 第四次复习正确 |
| 6 | 精通 | 30 天 | 第五次复习正确 |

规则：复习正确 → 等级 +1；复习错误 → 等级回退到 max(当前等级 - 2, 1)。

---

### 3.5 学习统计

**描述**：追踪并展示学习数据，包括每日学习量、词汇掌握进度、测试正确率趋势等，支持终端内图表展示。

**用户故事**：
- 作为考生，我想直观看到自己的学习进度和趋势
- 作为考生，我想知道距离目标 Band 分数还有多少词汇需要掌握
- 作为考生，我想看到自己的连续学习天数，保持学习动力

**CLI 命令设计**：

```bash
# 查看总览统计
ielts stats

# 查看今日学习详情
ielts stats today

# 查看本周/本月统计
ielts stats --period week
ielts stats --period month

# 查看 Band 级别掌握进度
ielts stats band

# 查看学习趋势图（终端柱状图）
ielts stats chart

# 查看学习日历（打卡热力图）
ielts stats calendar
```

**统计面板示例**：

```
━━━━━━━━━━  IELTS Buddy 学习统计  ━━━━━━━━━━

  🔥 连续学习: 12 天
  📅 累计学习: 45 天
  📝 总学习词数: 1,250 / 3,000

  Band 进度:
    Band 5  ████████████████████  100%  (500/500)
    Band 6  ██████████████░░░░░░   70%  (420/600)
    Band 7  ████████░░░░░░░░░░░░   40%  (280/700)
    Band 8  ██░░░░░░░░░░░░░░░░░░   10%  (50/500)
    Band 9  ░░░░░░░░░░░░░░░░░░░░    0%  (0/700)

  今日:
    新学: 50 词  |  复习: 32 词  |  测试: 82%

  本周正确率趋势:
    Mon ████████████████ 80%
    Tue ██████████████████ 90%
    Wed ████████████████ 82%
    Thu █████████████████ 85%
    Fri ██████████████████ 92%
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

---

### 3.6 飞书多维表格集成

**描述**：将词库和学习数据双向同步到飞书多维表格 (Bitable)，支持在飞书中查看、编辑和管理单词。支持飞书机器人发送每日学习提醒。

**用户故事**：
- 作为用户，我想把学习数据同步到飞书，方便在手机上查看
- 作为用户，我想在飞书多维表格中批量编辑和管理我的词库
- 作为团队管理者，我想在飞书群中看到组员的学习打卡情况
- 作为用户，我想通过飞书机器人收到每日复习提醒

**CLI 命令设计**：

```bash
# 配置飞书连接
ielts feishu config --app-id <id> --app-secret <secret> --bitable-url <url>

# 验证飞书连接
ielts feishu ping

# 将本地词库推送到飞书多维表格
ielts feishu push --vocab

# 将学习记录推送到飞书
ielts feishu push --records

# 全量推送
ielts feishu push --all

# 从飞书拉取数据（比如在飞书中新增的自定义单词）
ielts feishu pull

# 双向同步
ielts feishu sync

# 发送今日学习报告到飞书群
ielts feishu report --webhook <webhook_url>
```

**飞书多维表格结构**：

- **词库表**：单词、音标、释义、Band 级别、主题、例句、记忆等级、下次复习日期
- **学习记录表**：日期、学习词数、复习词数、测试正确率、学习时长
- **错题本表**：单词、错误次数、最近错误日期、错误类型

---

### 3.7 每日学习网页生成

**描述**：自动生成每日英语学习静态网页，包含今日学习的单词、例句、学习统计图表等，通过 GitHub Pages 部署。支持生成历史学习日历页面。

**用户故事**：
- 作为考生，我想把每天的学习内容生成网页分享给朋友
- 作为考生，我想在手机浏览器上回顾今天学的单词
- 作为考生，我想有一个持续更新的学习档案页面

**CLI 命令设计**：

```bash
# 生成今日学习页面
ielts page generate

# 生成指定日期的页面
ielts page generate --date 2026-03-05

# 生成首页（含学习日历和统计总览）
ielts page index

# 全量重新生成所有页面
ielts page rebuild

# 部署到 GitHub Pages（git add + commit + push）
ielts page deploy

# 一键生成 + 部署
ielts page publish

# 本地预览
ielts page preview --port 8080
```

**网页内容**：
- 今日新学单词列表（含释义、例句、音标）
- 今日复习单词列表
- 学习数据统计卡片（学习词数、正确率、连续天数）
- 学习日历热力图
- 支持暗色/亮色主题切换

---

### 3.8 听力练习资源

**描述**：管理和索引美剧/英剧剪辑视频资源，按雅思听力场景分类，提供带字幕的听力练习。支持从配置的资源目录中扫描视频文件。

**用户故事**：
- 作为考生，我想找到与雅思听力场景相关的美剧片段
- 作为考生，我想按场景主题筛选听力材料（如学术讨论、日常对话）
- 作为考生，我想做听写练习来提升听力能力

**CLI 命令设计**：

```bash
# 扫描并索引本地视频资源
ielts listen scan --dir ~/videos/english

# 列出可用的听力材料
ielts listen list

# 按场景筛选
ielts listen list --scene academic
ielts listen list --scene daily

# 随机播放一个片段
ielts listen play --random

# 开始听写练习（播放音频，用户输入听到的内容）
ielts listen dictation

# 查看听力练习记录
ielts listen stats
```

**场景分类**：
- academic（学术讨论/讲座）
- daily（日常对话）
- travel（旅行/住宿）
- workplace（职场/面试）
- news（新闻报道）

---

### 3.9 写作练习辅助

**描述**：提供雅思写作相关的词汇和句型辅助。包括 Task 1（图表描述）和 Task 2（议论文）的常用表达、话题词汇、高分句型模板。

**用户故事**：
- 作为考生，我想随时查阅雅思写作高分表达
- 作为考生，我想针对特定写作话题获取相关词汇和句型
- 作为考生，我想练习同义替换能力

**CLI 命令设计**：

```bash
# 随机获取一个写作话题
ielts write topic

# 获取某话题的写作词汇和表达
ielts write vocab --topic education

# 查看高分句型模板
ielts write templates --task 2

# Task 1 图表描述常用表达
ielts write templates --task 1

# 同义替换练习
ielts write synonym "important"

# 查看连接词/过渡词列表
ielts write connectors
```

---

### 3.10 口语话题练习

**描述**：内置雅思口语 Part 1/2/3 话题库，随机抽取话题进行练习，提供答题框架和参考词汇。

**用户故事**：
- 作为考生，我想随机抽取口语话题进行模拟练习
- 作为考生，我想查看某个话题的答题思路和高分词汇
- 作为考生，我想记录自己练习过的话题

**CLI 命令设计**：

```bash
# 随机抽取 Part 1 话题
ielts speak --part 1

# 随机抽取 Part 2 话题卡（含提示问题）
ielts speak --part 2

# Part 3 深度讨论话题
ielts speak --part 3

# 按话题分类筛选
ielts speak --part 2 --topic technology

# 查看当季高频话题
ielts speak hot

# 标记话题为已练习
ielts speak done <topic_id>

# 查看练习记录
ielts speak history
```

**Part 2 话题卡示例**：

```
━━━━━━━━━━  IELTS Speaking Part 2  ━━━━━━━━━━

  Describe a book that you have read recently.

  You should say:
    - what the book was about
    - why you decided to read it
    - how long it took you to read it
  and explain whether you would recommend it.

  ─────────────────────────────────────────
  参考词汇: page-turner, compelling, thought-provoking,
            captivating, narrative, plot twist

  答题框架:
    1. 开头引入（书名+类型）
    2. 内容概述（2-3句）
    3. 阅读原因
    4. 阅读体验
    5. 推荐理由 + 总结

  准备时间: 1 分钟  |  答题时间: 1-2 分钟
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

---

## 4. 数据模型设计

### 4.1 词库数据结构

```python
class Word:
    word: str              # 单词
    phonetic: str          # 音标
    meaning: str           # 中文释义
    pos: str               # 词性 (n./v./adj./adv. 等)
    band: int              # 雅思 Band 级别 (5-9)
    topic: str             # 主题场景
    example: str           # 例句
    example_cn: str        # 例句翻译
    collocations: list     # 常用搭配
    synonyms: list         # 同义词
    etymology: str         # 词根词缀/助记
    is_custom: bool        # 是否用户自定义词汇
```

### 4.2 学习记录结构

```python
class LearningRecord:
    word: str              # 单词
    memory_level: int      # 记忆等级 (0-6)
    next_review: date      # 下次复习日期
    learn_count: int       # 学习次数
    correct_count: int     # 正确次数
    wrong_count: int       # 错误次数
    first_learned: datetime # 首次学习时间
    last_reviewed: datetime # 最近复习时间
    is_starred: bool       # 是否收藏
    is_difficult: bool     # 是否标记为困难
```

### 4.3 测试记录结构

```python
class TestSession:
    session_id: str        # 测试会话 ID
    test_date: datetime    # 测试时间
    test_mode: str         # 测试模式
    total_count: int       # 总题数
    correct_count: int     # 正确数
    wrong_words: list      # 错误的单词列表
    duration: int          # 测试用时（秒）
    band_filter: int       # 测试的 Band 范围
    topic_filter: str      # 测试的主题范围
```

### 4.4 每日学习摘要

```python
class DailySummary:
    date: date             # 日期
    new_words: int         # 新学词数
    reviewed_words: int    # 复习词数
    test_accuracy: float   # 测试正确率
    study_minutes: int     # 学习时长（分钟）
    streak_days: int       # 连续学习天数
```

### 4.5 口语话题结构

```python
class SpeakingTopic:
    topic_id: str          # 话题 ID
    part: int              # Part 1/2/3
    question: str          # 主问题
    sub_questions: list    # 子问题/提示
    category: str          # 话题分类
    season: str            # 所属考季
    vocab_hints: list      # 参考词汇
    framework: str         # 答题框架
    is_hot: bool           # 是否当季高频
```

### 4.6 存储方案

本地数据使用 **SQLite** 存储，数据库文件位于 `~/.ielts-buddy/data.db`。

内置词库以 **JSON** 文件打包在项目中，首次运行时导入数据库。

配置文件使用 **TOML** 格式，位于 `~/.ielts-buddy/config.toml`。

```
~/.ielts-buddy/
├── config.toml          # 用户配置
├── data.db              # SQLite 数据库
└── pages/               # 生成的静态网页
```

---

## 5. 技术方案概述

### 5.1 技术栈

| 组件 | 技术选型 | 说明 |
|-----|---------|------|
| CLI 框架 | Click | 命令行参数解析与交互 |
| 数据库 | SQLite3 | 本地数据持久化 |
| 终端 UI | Rich | 彩色输出、表格、进度条、面板 |
| HTTP 客户端 | httpx | 飞书 API 调用 |
| 模板引擎 | Jinja2 | 静态网页生成 |
| 数据模型 | Pydantic | 数据验证与序列化 |
| 配置管理 | tomli / tomllib | TOML 配置读写 |
| 打包分发 | setuptools / PyPI | CLI 工具安装 |
| 测试 | pytest | 单元测试与集成测试 |

### 5.2 项目结构

```
ielts-buddy/
├── pyproject.toml
├── requirements.txt
├── src/
│   └── ielts_buddy/
│       ├── __init__.py
│       ├── cli.py              # CLI 入口与命令注册
│       ├── commands/
│       │   ├── vocab.py        # 词库管理命令
│       │   ├── learn.py        # 学习命令
│       │   ├── test.py         # 测试命令
│       │   ├── review.py       # 复习命令
│       │   ├── stats.py        # 统计命令
│       │   ├── feishu.py       # 飞书集成命令
│       │   ├── page.py         # 网页生成命令
│       │   ├── listen.py       # 听力练习命令
│       │   ├── write.py        # 写作辅助命令
│       │   └── speak.py        # 口语练习命令
│       ├── core/
│       │   ├── database.py     # 数据库操作
│       │   ├── models.py       # 数据模型
│       │   ├── scheduler.py    # 艾宾浩斯调度器
│       │   └── config.py       # 配置管理
│       ├── services/
│       │   ├── feishu.py       # 飞书 API 服务
│       │   └── page_builder.py # 网页构建服务
│       ├── data/
│       │   ├── vocab_band5.json
│       │   ├── vocab_band6.json
│       │   ├── vocab_band7.json
│       │   ├── vocab_band8.json
│       │   ├── vocab_band9.json
│       │   ├── speaking_topics.json
│       │   └── writing_templates.json
│       └── templates/
│           ├── daily.html      # 每日学习页面模板
│           └── index.html      # 首页模板
├── tests/
├── docs/
└── .github/
    └── workflows/
        └── pages.yml           # GitHub Pages 自动部署
```

### 5.3 飞书集成方案

1. 用户在飞书开放平台创建自建应用，获取 App ID 和 App Secret
2. 使用飞书 Bitable API（多维表格 API）进行数据读写
3. 认证方式：tenant_access_token（应用凭证）
4. 使用飞书 Webhook 发送群消息（学习报告/提醒）

API 调用流程：
```
获取 tenant_access_token → 操作多维表格（CRUD）→ 发送 Webhook 消息
```

### 5.4 GitHub Pages 部署方案

1. 使用 Jinja2 模板引擎生成静态 HTML
2. 内置 CSS 样式（轻量级，无框架依赖）
3. 生成的文件输出到 `~/.ielts-buddy/pages/` 目录
4. 用户可配置 GitHub Pages 仓库路径
5. `ielts page deploy` 自动执行 git add → commit → push
6. 可选配 GitHub Actions 自动化流程

---

## 6. MVP 范围定义

### Phase 1 — MVP（核心学习闭环）

**目标**：实现"学习 → 测试 → 复习"的完整闭环。

| 功能 | 范围 |
|-----|------|
| 词库管理 | 内置 500+ 高频词（Band 5-9），支持查看和搜索 |
| 单词学习 | 随机抽取学习，交互式卡片展示 |
| 单词测试 | 拼写测试 + 释义测试，结果统计 |
| 记忆复习 | 艾宾浩斯遗忘曲线，自动调度复习 |
| 学习统计 | 基础统计面板（今日/累计/连续天数） |

**交付物**：可 `pip install` 安装并运行的 CLI 工具。

### Phase 2 — 数据打通

**目标**：学习数据可视化与飞书生态集成。

| 功能 | 范围 |
|-----|------|
| 飞书集成 | 词库同步 + 学习记录同步 + 群消息报告 |
| 网页生成 | 每日学习页面 + 首页日历 + GitHub Pages 部署 |
| 统计增强 | 终端图表、趋势分析、Band 进度可视化 |
| 词库扩展 | 自定义单词、导入导出、词库扩充到 3000 词 |

### Phase 3 — 全面备考

**目标**：覆盖听说读写四项技能。

| 功能 | 范围 |
|-----|------|
| 听力练习 | 视频资源索引、听写练习 |
| 写作辅助 | 话题词汇、高分句型、同义替换 |
| 口语练习 | Part 1/2/3 话题库、答题框架 |
| 飞书增强 | 机器人提醒、团队排行榜 |

---

## 7. 创新功能建议

### 7.1 词根词缀智能拆解

为每个单词提供词根词缀分析，帮助用户理解构词规律，实现"学一个记十个"。

```bash
ielts vocab root "predict"
```

```
  predict  →  pre- (之前) + dict (说/言)
                           ↓
  同根词: dictionary, dictate, contradict, verdict, indicate
  同前缀: preview, prevent, prepare, precaution
```

**价值**：将死记硬背转化为理解性记忆，大幅提升长期记忆效果。

### 7.2 考试倒计时与智能学习计划

设定雅思考试日期和目标分数，系统自动生成个性化每日学习计划，动态调整学习节奏。

```bash
# 设定考试目标
ielts plan set --exam-date 2026-06-15 --target-band 7.0

# 查看今日计划
ielts plan today

# 查看整体进度
ielts plan progress
```

```
━━━━━━━━━━━━  学习计划  ━━━━━━━━━━━━━
  目标: Band 7.0  |  考试日: 2026-06-15
  剩余: 101 天

  今日计划:
    [ ] 学习 30 个 Band 7 新词
    [ ] 复习 45 个到期单词
    [ ] 完成 1 组拼写测试
    [ ] 练习 1 个 Part 2 口语话题

  整体进度: ██████████░░░░░░  62%
  预计达标: 按当前速度可在考前完成
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

**价值**：将碎片化学习转化为有目标、有节奏的系统备考。

### 7.3 飞书学习社群机器人

在飞书群内部署学习机器人，实现团队学习互动：

- **每日推送**：每天定时推送 5 个"今日单词"到群内
- **打卡排行榜**：展示群内成员学习排行（连续天数、词汇量）
- **每周挑战**：发起群内单词挑战赛，成员通过机器人答题 PK
- **错题共享**：汇总群内成员的共同易错词，发起专项复习

```bash
# 配置飞书机器人
ielts feishu bot setup --webhook <url>

# 发送每日单词到群
ielts feishu bot daily-words

# 生成并发送周报
ielts feishu bot weekly-report
```

**价值**：利用社交压力和群体动力提升学习坚持率，结合飞书工作场景降低学习门槛。

### 7.4 场景化情景记忆

将单词放入雅思考试的真实场景中学习，而非孤立记忆。按照雅思听力/阅读的常见场景（图书馆、租房、学术讲座等）组织词汇。

```bash
# 进入场景模式
ielts learn --scene library
ielts learn --scene campus-tour
ielts learn --scene academic-lecture
```

```
━━━━━  场景: University Library  ━━━━━

  你正在大学图书馆办理借书卡...

  相关词汇:
  1. catalogue  → 目录
  2. periodical → 期刊
  3. overdue    → 逾期的
  4. renewal    → 续借
  5. reference  → 参考书/工具书
  ...

  场景对话:
  "I'd like to renew this book. Is there
   an overdue fine if I return it late?"
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

**价值**：模拟真实考试场景，词汇学习与听力/阅读能力同步提升。

### 7.5 易混词辨析引擎

自动识别并推送容易混淆的近义词/形近词对比，帮助考生精准用词。

```bash
ielts vocab confuse "affect"
```

```
━━━━━━━━  易混词辨析  ━━━━━━━━

  affect  vs  effect

  affect (v.) 影响
    → The weather affects my mood.

  effect (n.) 效果，影响
    → The effect of the policy was significant.

  记忆技巧:
    Affect = Action (动词，A 开头)
    Effect = End result (名词，结果)

  雅思常见搭配:
    - adversely affect / significantly affect
    - have an effect on / side effect
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

**价值**：解决雅思写作和口语中的精准用词问题，直击高分瓶颈。

---

## 附录：命令速查表

```bash
# 核心命令
ielts learn              # 学习新词
ielts test               # 单词测试
ielts review             # 复习到期单词
ielts stats              # 学习统计

# 词库管理
ielts vocab stats        # 词库概览
ielts vocab list         # 列出单词
ielts vocab search       # 搜索单词
ielts vocab add          # 添加单词
ielts vocab root         # 词根分析

# 飞书集成
ielts feishu config      # 配置连接
ielts feishu sync        # 双向同步
ielts feishu report      # 发送报告

# 网页生成
ielts page generate      # 生成今日页面
ielts page deploy        # 部署到 GitHub Pages
ielts page publish       # 一键生成 + 部署

# 听说读写
ielts listen             # 听力练习
ielts write              # 写作辅助
ielts speak              # 口语练习

# 学习计划
ielts plan set           # 设定目标
ielts plan today         # 今日计划
```
