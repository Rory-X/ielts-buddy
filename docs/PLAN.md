# IELTS Buddy — 开发计划

> 版本：v1.0 | 日期：2026-03-06 | 基于 PRD v1.0

---

## 1. 项目结构设计

```
ielts-buddy/
├── pyproject.toml                  # 项目元数据、依赖、构建配置
├── README.md                       # 项目说明
├── LICENSE
├── .github/
│   └── workflows/
│       └── pages.yml               # GitHub Pages 自动部署
│
├── docs/
│   ├── PRD.md                      # 产品需求文档
│   └── PLAN.md                     # 本开发计划
│
├── prompts/                        # Claude Code 提示词
│
├── src/
│   └── ielts_buddy/
│       ├── __init__.py             # 版本号、包信息
│       ├── cli.py                  # Click CLI 入口，注册所有命令组
│       │
│       ├── commands/               # CLI 命令实现（每个模块一个文件）
│       │   ├── __init__.py
│       │   ├── vocab.py            # ielts vocab *
│       │   ├── learn.py            # ielts learn *
│       │   ├── test.py             # ielts test *
│       │   ├── review.py           # ielts review *
│       │   ├── stats.py            # ielts stats *
│       │   ├── feishu.py           # ielts feishu *
│       │   ├── page.py             # ielts page *
│       │   ├── listen.py           # ielts listen *
│       │   ├── write.py            # ielts write *
│       │   └── speak.py            # ielts speak *
│       │
│       ├── core/                   # 核心业务逻辑
│       │   ├── __init__.py
│       │   ├── database.py         # SQLite 数据库初始化与连接管理
│       │   ├── models.py           # Pydantic 数据模型
│       │   ├── scheduler.py        # 艾宾浩斯遗忘曲线调度器
│       │   ├── config.py           # TOML 配置管理
│       │   └── vocab_loader.py     # 内置词库加载与导入
│       │
│       ├── services/               # 外部服务集成
│       │   ├── __init__.py
│       │   ├── feishu.py           # 飞书 API 客户端（认证、Bitable、Webhook）
│       │   └── page_builder.py     # Jinja2 静态网页生成
│       │
│       ├── data/                   # 内置数据文件（JSON）
│       │   ├── vocab_band5.json
│       │   ├── vocab_band6.json
│       │   ├── vocab_band7.json
│       │   ├── vocab_band8.json
│       │   ├── vocab_band9.json
│       │   ├── speaking_topics.json
│       │   └── writing_templates.json
│       │
│       └── templates/              # Jinja2 HTML 模板
│           ├── base.html           # 基础布局模板
│           ├── daily.html          # 每日学习页面
│           └── index.html          # 首页（日历 + 统计总览）
│
└── tests/
    ├── conftest.py                 # pytest fixtures（内存数据库等）
    ├── test_database.py
    ├── test_models.py
    ├── test_scheduler.py
    ├── test_vocab_loader.py
    ├── test_commands/
    │   ├── test_vocab.py
    │   ├── test_learn.py
    │   ├── test_test.py
    │   ├── test_review.py
    │   └── test_stats.py
    ├── test_services/
    │   ├── test_feishu.py
    │   └── test_page_builder.py
    └── data/
        └── test_vocab.json         # 测试用小规模词库
```

---

## 2. 分阶段开发计划

### Phase 1 — MVP（核心学习闭环）

**目标**：实现 `学习 → 测试 → 复习` 的完整闭环，可 `pip install` 安装运行。

**范围**：P0 模块 — 词库管理、单词学习、单词测试、记忆复习、学习统计。

### Phase 2 — 数据打通

**目标**：学习数据可视化 + 飞书生态集成 + GitHub Pages 学习日志。

**范围**：P1 模块 — 飞书集成、网页生成、统计增强、词库扩展。

### Phase 3 — 全面备考

**目标**：覆盖听说读写四项技能，完善飞书社群功能。

**范围**：P2 模块 — 听力练习、写作辅助、口语练习、飞书增强。

---

## 3. 每阶段具体任务清单

### Phase 1 — MVP

#### 1.1 项目基础设施

| # | 任务 | 说明 |
|---|------|------|
| 1.1.1 | 初始化项目结构 | pyproject.toml、src layout、`ielts` CLI 入口点 |
| 1.1.2 | 配置管理 (`core/config.py`) | TOML 读写，`~/.ielts-buddy/config.toml` 自动创建 |
| 1.1.3 | 数据库初始化 (`core/database.py`) | SQLite 连接管理、建表迁移、`~/.ielts-buddy/data.db` |
| 1.1.4 | 数据模型 (`core/models.py`) | Word、LearningRecord、TestSession、DailySummary Pydantic 模型 |
| 1.1.5 | CLI 框架搭建 (`cli.py`) | Click group 注册，版本号、全局选项 |
| 1.1.6 | 测试基础设施 | conftest.py、内存 SQLite fixture、CLI runner fixture |

#### 1.2 词库管理

| # | 任务 | 说明 |
|---|------|------|
| 1.2.1 | 准备内置词库数据 | 制作 vocab_band5-9.json，每 Band 100+ 词 |
| 1.2.2 | 词库加载器 (`core/vocab_loader.py`) | 首次运行检测并导入 JSON → SQLite |
| 1.2.3 | `ielts vocab stats` | 各级别词汇数量统计，Rich 表格输出 |
| 1.2.4 | `ielts vocab list` | --band、--topic 筛选，分页展示 |
| 1.2.5 | `ielts vocab search` | 模糊搜索，展示匹配结果 |
| 1.2.6 | `ielts vocab add` | 添加自定义单词到数据库 |
| 1.2.7 | `ielts vocab export / import` | CSV 格式导入导出 |

#### 1.3 单词学习

| # | 任务 | 说明 |
|---|------|------|
| 1.3.1 | `ielts learn` 基础命令 | --count、--band、--topic、--new-only 参数 |
| 1.3.2 | 交互式学习模式 (`--interactive`) | Rich 面板逐词展示，Enter/y/s/q 交互 |
| 1.3.3 | 学习记录写入 | 学习完成后更新 LearningRecord |

#### 1.4 单词测试

| # | 任务 | 说明 |
|---|------|------|
| 1.4.1 | `ielts test --mode spelling` | 看中文写英文，Levenshtein 容错判定 |
| 1.4.2 | `ielts test --mode meaning` | 看英文选中文（四选一） |
| 1.4.3 | `ielts test --mode choice` | 混合四选一选择题 |
| 1.4.4 | `ielts test --mode context` | 完形填空，句中填词 |
| 1.4.5 | 测试结果统计与输出 | Rich 面板展示正确率、易错词，写入 TestSession |
| 1.4.6 | --difficult / --starred / --today 过滤 | 从 LearningRecord 筛选测试范围 |

#### 1.5 记忆复习（艾宾浩斯）

| # | 任务 | 说明 |
|---|------|------|
| 1.5.1 | 遗忘曲线调度器 (`core/scheduler.py`) | 根据 memory_level 计算 next_review，等级升降逻辑 |
| 1.5.2 | `ielts review` | 加载今日到期单词，交互式复习 |
| 1.5.3 | `ielts review plan` | 展示今日/本周待复习数量 |
| 1.5.4 | `ielts review status <word>` | 查看单词的记忆等级和复习历史 |
| 1.5.5 | `ielts review reset <word>` | 重置记忆进度 |

#### 1.6 学习统计

| # | 任务 | 说明 |
|---|------|------|
| 1.6.1 | `ielts stats` | 总览面板：连续天数、累计词数、Band 进度条 |
| 1.6.2 | `ielts stats today` | 今日详情：新学/复习/测试正确率 |
| 1.6.3 | `ielts stats --period week/month` | 按时间段聚合统计 |
| 1.6.4 | DailySummary 自动写入 | 每次学习/测试/复习后更新当日摘要 |

---

### Phase 2 — 数据打通

#### 2.1 飞书多维表格集成

| # | 任务 | 说明 |
|---|------|------|
| 2.1.1 | 飞书 API 客户端 (`services/feishu.py`) | token 获取、请求封装、错误处理 |
| 2.1.2 | `ielts feishu config` | 保存 App ID / Secret / Bitable URL 到 config.toml |
| 2.1.3 | `ielts feishu ping` | 验证 token 获取及 Bitable 访问 |
| 2.1.4 | `ielts feishu push --vocab` | 词库表同步：本地 → 飞书 |
| 2.1.5 | `ielts feishu push --records` | 学习记录表同步：本地 → 飞书 |
| 2.1.6 | `ielts feishu pull` | 从飞书拉取新增/修改的自定义单词 |
| 2.1.7 | `ielts feishu sync` | 双向同步（冲突策略：以最新修改时间为准） |
| 2.1.8 | `ielts feishu report` | 通过 Webhook 发送每日学习报告卡片到飞书群 |

#### 2.2 每日学习网页生成

| # | 任务 | 说明 |
|---|------|------|
| 2.2.1 | HTML/CSS 模板设计 | base.html 布局、响应式 CSS、暗色/亮色主题 |
| 2.2.2 | 网页构建服务 (`services/page_builder.py`) | Jinja2 渲染逻辑 |
| 2.2.3 | `ielts page generate` | 生成今日/指定日期的学习页面 |
| 2.2.4 | `ielts page index` | 生成首页：学习日历热力图 + 统计总览 |
| 2.2.5 | `ielts page preview` | 启动本地 HTTP 服务器预览 |
| 2.2.6 | `ielts page deploy` | git add + commit + push 到 GitHub Pages 仓库 |
| 2.2.7 | `ielts page publish` | generate + index + deploy 一键完成 |
| 2.2.8 | GitHub Actions 配置 | .github/workflows/pages.yml 自动部署 |

#### 2.3 统计增强 & 词库扩展

| # | 任务 | 说明 |
|---|------|------|
| 2.3.1 | `ielts stats chart` | 终端柱状图（Rich 或自定义 ASCII） |
| 2.3.2 | `ielts stats calendar` | 打卡热力图 |
| 2.3.3 | `ielts stats band` | Band 级别掌握进度详情 |
| 2.3.4 | 词库扩充到 3000 词 | 补充各 Band 级别词汇数据 |

---

### Phase 3 — 全面备考

#### 3.1 听力练习

| # | 任务 | 说明 |
|---|------|------|
| 3.1.1 | `ielts listen scan` | 扫描本地视频目录，提取元数据索引 |
| 3.1.2 | `ielts listen list` | 列出已索引材料，支持 --scene 筛选 |
| 3.1.3 | `ielts listen play` | 调用系统播放器播放片段 |
| 3.1.4 | `ielts listen dictation` | 听写练习模式：播放 → 输入 → 对比 |

#### 3.2 写作辅助

| # | 任务 | 说明 |
|---|------|------|
| 3.2.1 | 写作数据准备 | writing_templates.json：话题、句型、连接词 |
| 3.2.2 | `ielts write topic` | 随机话题 |
| 3.2.3 | `ielts write vocab --topic` | 话题相关写作词汇 |
| 3.2.4 | `ielts write templates` | Task 1/2 高分句型 |
| 3.2.5 | `ielts write synonym` | 同义替换练习 |
| 3.2.6 | `ielts write connectors` | 连接词列表 |

#### 3.3 口语练习

| # | 任务 | 说明 |
|---|------|------|
| 3.3.1 | 口语数据准备 | speaking_topics.json：Part 1/2/3 话题库 |
| 3.3.2 | `ielts speak --part 1/2/3` | 随机抽取话题卡 |
| 3.3.3 | `ielts speak hot` | 当季高频话题 |
| 3.3.4 | `ielts speak done / history` | 练习记录追踪 |

#### 3.4 飞书增强

| # | 任务 | 说明 |
|---|------|------|
| 3.4.1 | 飞书机器人每日提醒 | 定时推送今日复习任务 |
| 3.4.2 | 群内每日单词推送 | 发送 5 个"今日单词"卡片到飞书群 |
| 3.4.3 | 周报生成与推送 | 汇总本周学习数据，生成卡片消息 |

---

## 4. 技术选型确认

### 运行环境

- Python >= 3.10（使用 `tomllib` 标准库）
- SQLite3（Python 内置）

### 核心依赖

| 依赖 | 版本约束 | 用途 | 引入阶段 |
|------|---------|------|---------|
| `click` | >=8.0 | CLI 框架，命令/参数解析 | Phase 1 |
| `rich` | >=13.0 | 终端 UI：表格、面板、进度条、颜色 | Phase 1 |
| `pydantic` | >=2.0 | 数据模型验证与序列化 | Phase 1 |
| `httpx` | >=0.27 | 飞书 API HTTP 客户端（异步支持） | Phase 2 |
| `jinja2` | >=3.1 | HTML 模板引擎 | Phase 2 |

### 开发依赖

| 依赖 | 用途 |
|------|------|
| `pytest` | 单元测试框架 |
| `pytest-cov` | 测试覆盖率 |
| `ruff` | 代码检查与格式化 |

### pyproject.toml 入口点配置

```toml
[project.scripts]
ielts = "ielts_buddy.cli:cli"
```

---

## 5. API / 数据接口设计

### 5.1 SQLite 数据库 Schema

```sql
-- 词库表
CREATE TABLE words (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    word        TEXT NOT NULL UNIQUE,
    phonetic    TEXT,
    meaning     TEXT NOT NULL,
    pos         TEXT,                    -- 词性
    band        INTEGER NOT NULL,        -- 5-9
    topic       TEXT,                    -- education, environment, ...
    example     TEXT,                    -- 英文例句
    example_cn  TEXT,                    -- 例句中文翻译
    collocations TEXT,                   -- JSON array
    synonyms    TEXT,                    -- JSON array
    etymology   TEXT,                    -- 词根词缀/助记
    is_custom   INTEGER DEFAULT 0,       -- 0=内置, 1=用户自定义
    created_at  TEXT DEFAULT (datetime('now'))
);

CREATE INDEX idx_words_band ON words(band);
CREATE INDEX idx_words_topic ON words(topic);

-- 学习记录表
CREATE TABLE learning_records (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    word_id       INTEGER NOT NULL REFERENCES words(id),
    memory_level  INTEGER DEFAULT 0,     -- 0-6
    next_review   TEXT,                  -- ISO 日期
    learn_count   INTEGER DEFAULT 0,
    correct_count INTEGER DEFAULT 0,
    wrong_count   INTEGER DEFAULT 0,
    first_learned TEXT,
    last_reviewed TEXT,
    is_starred    INTEGER DEFAULT 0,
    is_difficult  INTEGER DEFAULT 0,
    UNIQUE(word_id)
);

CREATE INDEX idx_lr_next_review ON learning_records(next_review);
CREATE INDEX idx_lr_memory_level ON learning_records(memory_level);

-- 测试会话表
CREATE TABLE test_sessions (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id    TEXT NOT NULL UNIQUE,
    test_date     TEXT NOT NULL,
    test_mode     TEXT NOT NULL,          -- spelling/meaning/choice/context
    total_count   INTEGER NOT NULL,
    correct_count INTEGER NOT NULL,
    wrong_words   TEXT,                   -- JSON array of word strings
    duration      INTEGER,               -- 秒
    band_filter   INTEGER,
    topic_filter  TEXT
);

-- 每日摘要表
CREATE TABLE daily_summaries (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    date            TEXT NOT NULL UNIQUE,  -- YYYY-MM-DD
    new_words       INTEGER DEFAULT 0,
    reviewed_words  INTEGER DEFAULT 0,
    test_accuracy   REAL,
    study_minutes   INTEGER DEFAULT 0,
    streak_days     INTEGER DEFAULT 0
);

-- 口语练习记录表（Phase 3）
CREATE TABLE speaking_history (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    topic_id   TEXT NOT NULL,
    part       INTEGER NOT NULL,
    practiced  TEXT NOT NULL,              -- ISO datetime
    notes      TEXT
);
```

### 5.2 核心内部接口

#### database.py

```python
class Database:
    def __init__(self, db_path: str): ...
    def initialize(self) -> None:                          # 建表迁移
    def get_words(self, band=None, topic=None, page=1, per_page=20) -> list[Word]: ...
    def search_words(self, query: str) -> list[Word]: ...
    def add_word(self, word: Word) -> None: ...
    def get_learning_record(self, word_id: int) -> LearningRecord | None: ...
    def upsert_learning_record(self, record: LearningRecord) -> None: ...
    def get_due_reviews(self, date: str) -> list[tuple[Word, LearningRecord]]: ...
    def save_test_session(self, session: TestSession) -> None: ...
    def get_daily_summary(self, date: str) -> DailySummary | None: ...
    def upsert_daily_summary(self, summary: DailySummary) -> None: ...
    def get_stats(self, period: str) -> dict: ...
```

#### scheduler.py

```python
REVIEW_INTERVALS = {0: 0, 1: 1, 2: 2, 3: 4, 4: 7, 5: 15, 6: 30}  # 天

class Scheduler:
    @staticmethod
    def calculate_next_review(memory_level: int, today: date) -> date: ...
    @staticmethod
    def on_correct(record: LearningRecord) -> LearningRecord: ...  # level +1
    @staticmethod
    def on_wrong(record: LearningRecord) -> LearningRecord: ...    # level = max(level-2, 1)
```

#### config.py

```python
class Config:
    def __init__(self, config_path: str = "~/.ielts-buddy/config.toml"): ...
    def get(self, key: str, default=None) -> Any: ...
    def set(self, key: str, value: Any) -> None: ...
    def save(self) -> None: ...

# config.toml 结构
# [general]
# daily_count = 50
# default_band = 7
#
# [feishu]
# app_id = ""
# app_secret = ""
# bitable_url = ""
# webhook_url = ""
#
# [pages]
# output_dir = "~/.ielts-buddy/pages"
# github_repo = ""
# theme = "light"
```

### 5.3 内置词库 JSON 格式

```json
[
  {
    "word": "scrutinize",
    "phonetic": "/ˈskruːtənaɪz/",
    "meaning": "仔细审查，详细检查",
    "pos": "v.",
    "band": 7,
    "topic": "education",
    "example": "The examiner will scrutinize your essay for grammatical accuracy.",
    "example_cn": "考官会仔细审查你文章的语法准确性。",
    "collocations": ["scrutinize closely", "scrutinize the data"],
    "synonyms": ["examine", "inspect", "analyze"],
    "etymology": "scrutin- (检查) + -ize (动词后缀)"
  }
]
```

---

## 6. 飞书集成方案详细设计

### 6.1 认证流程

```
┌─────────────────────────────────────────────────────┐
│  1. 用户在飞书开放平台创建自建应用                        │
│     → 获取 App ID + App Secret                       │
│                                                      │
│  2. ielts feishu config 保存到 config.toml            │
│                                                      │
│  3. 运行时获取 tenant_access_token                     │
│     POST https://open.feishu.cn/open-apis/auth/v3/   │
│          tenant_access_token/internal                 │
│     Body: { "app_id": "...", "app_secret": "..." }   │
│     → 返回 tenant_access_token（有效期 2 小时）         │
│                                                      │
│  4. 缓存 token，过期前自动刷新                           │
└─────────────────────────────────────────────────────┘
```

### 6.2 飞书多维表格 (Bitable) 操作

**API 基础路径**：`https://open.feishu.cn/open-apis/bitable/v1`

**三张表结构**：

| 表名 | 字段 | 飞书字段类型 |
|------|------|------------|
| **词库表** | word(文本), phonetic(文本), meaning(文本), band(数字), topic(单选), example(文本), memory_level(数字), next_review(日期) | - |
| **学习记录表** | date(日期), new_words(数字), reviewed_words(数字), test_accuracy(数字), study_minutes(数字), streak_days(数字) | - |
| **错题本表** | word(文本), wrong_count(数字), last_wrong_date(日期), wrong_types(多选) | - |

**核心 API 调用**：

```python
class FeishuClient:
    BASE_URL = "https://open.feishu.cn/open-apis"

    def __init__(self, app_id: str, app_secret: str, bitable_app_token: str): ...

    # 认证
    def _get_token(self) -> str: ...
    def _refresh_if_expired(self) -> None: ...

    # 多维表格 CRUD
    def list_tables(self) -> list[dict]: ...
    def create_table(self, name: str, fields: list[dict]) -> str: ...
    def list_records(self, table_id: str, filter: str = None) -> list[dict]: ...
    def create_records(self, table_id: str, records: list[dict]) -> None: ...
    def update_record(self, table_id: str, record_id: str, fields: dict) -> None: ...
    def batch_create_records(self, table_id: str, records: list[dict]) -> None: ...

    # Webhook 消息
    def send_webhook(self, webhook_url: str, content: dict) -> None: ...
```

### 6.3 同步策略

**Push（本地 → 飞书）**：
1. 读取本地数据库全量/增量数据
2. 将不存在的记录 batch_create 到飞书表
3. 已存在的记录按 `word` 字段匹配后 update

**Pull（飞书 → 本地）**：
1. list_records 拉取飞书表中所有记录
2. 比对本地数据库，将飞书中新增/修改的自定义单词写入本地

**Sync（双向）**：
1. 以 `last_modified` 时间戳为准，较新方覆盖较旧方
2. 新增记录双向写入

### 6.4 Webhook 消息格式

使用飞书互动卡片（Interactive Card）发送每日报告：

```json
{
  "msg_type": "interactive",
  "card": {
    "header": {
      "title": { "tag": "plain_text", "content": "IELTS Buddy 每日学习报告" },
      "template": "blue"
    },
    "elements": [
      {
        "tag": "div",
        "text": {
          "tag": "lark_md",
          "content": "**日期**: 2026-03-06\n**新学**: 50 词 | **复习**: 32 词\n**测试正确率**: 82%\n**连续学习**: 12 天"
        }
      }
    ]
  }
}
```

---

## 7. GitHub Pages 部署方案

### 7.1 页面生成流程

```
┌──────────────────────────────────────────────────────┐
│  1. ielts page generate                               │
│     → 查询今日 DailySummary + 学习的 Word 列表          │
│     → Jinja2 渲染 daily.html → output_dir/YYYY-MM-DD/ │
│                                                       │
│  2. ielts page index                                  │
│     → 查询所有 DailySummary                            │
│     → 生成日历热力图数据                                 │
│     → Jinja2 渲染 index.html → output_dir/index.html   │
│                                                       │
│  3. ielts page deploy                                 │
│     → cd output_dir                                   │
│     → git add . && git commit && git push             │
│                                                       │
│  4. GitHub Pages 自动部署（或手动 / Actions 触发）       │
└──────────────────────────────────────────────────────┘
```

### 7.2 输出目录结构

```
~/.ielts-buddy/pages/
├── index.html              # 首页：学习日历 + 统计总览
├── style.css               # 全局样式
├── 2026-03-05/
│   └── index.html          # 2026-03-05 学习页面
├── 2026-03-06/
│   └── index.html          # 2026-03-06 学习页面
└── ...
```

### 7.3 HTML 技术方案

- **纯静态 HTML/CSS**，无 JavaScript 框架依赖
- CSS 变量实现暗色/亮色主题切换（`prefers-color-scheme` media query）
- 响应式布局，移动端友好
- 日历热力图使用 CSS Grid 实现
- 统计图表使用内联 SVG 生成

### 7.4 GitHub Actions 自动部署

```yaml
# .github/workflows/pages.yml
name: Deploy to GitHub Pages

on:
  push:
    branches: [gh-pages]

permissions:
  contents: read
  pages: write
  id-token: write

jobs:
  deploy:
    runs-on: ubuntu-latest
    environment:
      name: github-pages
      url: ${{ steps.deployment.outputs.page_url }}
    steps:
      - uses: actions/checkout@v4
        with:
          ref: gh-pages
      - uses: actions/configure-pages@v4
      - uses: actions/upload-pages-artifact@v3
        with:
          path: '.'
      - id: deployment
        uses: actions/deploy-pages@v4
```

### 7.5 部署流程

用户配置一次 GitHub Pages 仓库后，日常使用：

```bash
# 每日学习结束后
ielts page publish    # = generate + index + deploy
```

或配置 git hook / cron 自动化。

---

## 8. 测试策略

### 8.1 测试分层

| 层级 | 工具 | 覆盖范围 | 目标覆盖率 |
|------|------|---------|-----------|
| **单元测试** | pytest | 数据模型、调度器、数据库操作、配置管理 | >= 90% |
| **命令测试** | Click CliRunner | 所有 CLI 命令的参数解析与输出 | >= 80% |
| **集成测试** | pytest + fixtures | 完整学习流程（学习→测试→复习→统计） | 关键路径 |
| **服务测试** | pytest + mock | 飞书 API 调用（mock httpx）、网页生成 | >= 80% |

### 8.2 测试基础设施

```python
# tests/conftest.py
import pytest
from ielts_buddy.core.database import Database

@pytest.fixture
def db(tmp_path):
    """内存 SQLite 数据库，每个测试独立。"""
    database = Database(":memory:")
    database.initialize()
    return database

@pytest.fixture
def db_with_vocab(db):
    """预置测试词库的数据库。"""
    # 导入 tests/data/test_vocab.json
    ...
    return db

@pytest.fixture
def cli_runner():
    """Click CLI 测试 runner。"""
    from click.testing import CliRunner
    return CliRunner()

@pytest.fixture
def config(tmp_path):
    """临时配置文件。"""
    ...
```

### 8.3 各模块测试要点

**core/scheduler.py**：
- 各等级 next_review 日期计算正确
- on_correct: level 0→1→2→...→6 逐级升级
- on_wrong: level 回退逻辑 `max(level-2, 1)`
- 边界：level=6 再 correct 保持 6；level=1 再 wrong 保持 1

**core/database.py**：
- CRUD 操作完整性
- 筛选查询（band/topic/日期范围）
- 唯一约束（word 不重复、daily_summary 日期唯一）
- 首次运行建表幂等性

**commands/**：
- 每个命令的正常路径输出验证
- 参数组合（--band + --topic + --count）
- 空数据库时的友好提示
- 无效输入的错误处理

**services/feishu.py**：
- Token 获取和缓存逻辑（mock HTTP）
- Bitable CRUD 请求参数和格式
- Webhook 消息发送
- 网络错误和 API 错误处理

**services/page_builder.py**：
- HTML 输出包含预期内容
- 日期格式正确
- 空数据日期的优雅处理
- 暗色/亮色主题 CSS 切换

### 8.4 测试执行

```bash
# 运行全部测试
pytest

# 带覆盖率
pytest --cov=ielts_buddy --cov-report=term-missing

# 只运行某个模块的测试
pytest tests/test_scheduler.py -v

# 只运行标记的测试
pytest -m "not slow"
```

### 8.5 CI 集成

在 pyproject.toml 中配置 pytest：

```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
markers = ["slow: marks tests as slow"]

[tool.ruff]
line-length = 100
target-version = "py310"
```

---

## 附录：关键设计决策

| 决策 | 选择 | 原因 |
|------|------|------|
| 数据库 | SQLite | 零配置、单文件、Python 内置、适合单用户桌面工具 |
| CLI 框架 | Click | 成熟稳定、嵌套命令组支持好、与 Rich 配合良好 |
| 配置格式 | TOML | Python 3.11+ 标准库支持、可读性好 |
| 词库格式 | JSON | 易于手工编辑和版本控制 |
| 网页方案 | 纯静态 HTML | 无需构建工具链、GitHub Pages 直接托管 |
| 飞书认证 | tenant_access_token | 自建应用最简方案、无需用户授权 |
