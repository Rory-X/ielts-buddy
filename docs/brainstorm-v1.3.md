# v1.3 设计文档 — 写作批改增强 & 个人词库

> 日期: 2026-03-17 | 状态: 草案

---

## 一、写作批改增强 (Enhanced Writing Grading)

### 现状分析

当前 `GradingService` 提供：
- Task 2 四维评分（TR / CC / LR / GRA）
- 整体建议列表（`suggestions: list[str]`）
- 高分改写（`rewrite: str`）
- 历史记录存储（SQLite `grade_history` 表）

**痛点**：反馈粒度太粗——只有维度级 comment，学生无法定位具体句子的问题；不支持 Task 1（图表描述/信件）。

---

### 子特性列表

| # | 子特性 | 优先级 | 工作量 | 说明 |
|---|--------|--------|--------|------|
| 1.1 | **句级标注 (Sentence Annotations)** | P0 | L | LLM 返回每句的问题标注（语法错误、用词不当、逻辑断裂），附修改建议。新增 `SentenceAnnotation` 模型，包含 `sentence_index`, `original`, `issue_type`, `comment`, `suggestion`。prompt 改为要求 JSON 中包含 `annotations` 数组。 |
| 1.2 | **段落结构分析 (Paragraph Analysis)** | P0 | M | 对每段输出结构评价：是否有 topic sentence、论证是否充分、衔接词使用。新增 `ParagraphAnalysis` 模型（`para_index`, `role`[intro/body/conclusion], `structure_score`, `comment`）。 |
| 1.3 | **Task 1 支持** | P0 | L | 新增 `task_type` 参数（`task1_academic` / `task1_general` / `task2`）。Task 1 Academic 的评分维度与 Task 2 相同但 prompt 不同（需要评估数据描述准确性、趋势概括、关键特征选取）。Task 1 General（信件）需评估语气/格式。为每种类型维护独立 system prompt。 |
| 1.4 | **错误分类统计** | P1 | S | 从句级标注中聚合错误类型分布（如 grammar 40%, vocabulary 30%, coherence 30%），存入 `grade_history`，支持跨次批改趋势分析。 |
| 1.5 | **高亮差异对比 (Diff View)** | P1 | M | 将原文与改写版本做 diff，在 Rich 终端中用颜色标注删改。可复用 `difflib.SequenceMatcher`，输出 Rich `Text` 对象。 |
| 1.6 | **批改历史对比** | P2 | M | 支持查看同一 topic 下多次批改的分数变化趋势图（Rich sparkline 或 ASCII chart）。需在 `grade_history` 表加 `task_type` 列。 |
| 1.7 | **离线/缓存模式** | P2 | S | 对相同作文内容做 hash 去重，避免重复调用 LLM。`grade_history` 加 `essay_hash` 列，命中则直接返回历史结果。 |

### 数据模型变更

```python
class SentenceAnnotation(BaseModel):
    sentence_index: int          # 句子序号（从 0 开始）
    original: str                # 原句
    issue_type: str              # grammar / vocabulary / coherence / style
    severity: str = "minor"      # minor / major / critical
    comment: str                 # 问题说明（中文）
    suggestion: str = ""         # 修改建议（英文）

class ParagraphAnalysis(BaseModel):
    para_index: int
    role: str                    # introduction / body / conclusion
    has_topic_sentence: bool
    structure_score: float       # 1-9
    cohesion_devices: list[str]  # 检测到的衔接词
    comment: str

class GradeResult(BaseModel):  # 扩展现有模型
    # ... 现有字段 ...
    task_type: str = "task2"
    annotations: list[SentenceAnnotation] = []
    paragraphs: list[ParagraphAnalysis] = []
    error_summary: dict[str, int] = {}  # {"grammar": 5, "vocabulary": 3, ...}
```

### DB 迁移

```sql
ALTER TABLE grade_history ADD COLUMN task_type TEXT DEFAULT 'task2';
ALTER TABLE grade_history ADD COLUMN essay_hash TEXT DEFAULT '';
CREATE INDEX IF NOT EXISTS idx_grade_essay_hash ON grade_history(essay_hash);
```

### 实现要点

- **Prompt 工程**：句级标注要求 LLM 返回 `annotations` 数组，需严格约束 JSON schema。考虑分两轮调用：第一轮评分+段落分析，第二轮句级标注（避免单次 prompt 过长导致质量下降）。
- **向后兼容**：`annotations` 和 `paragraphs` 默认空列表，旧记录反序列化不受影响。
- **Task 1 prompt 差异**：Academic 需要评估 "overview statement"、数据准确性；General 需要评估语气（formal/semi-formal/informal）和信件格式。

---

## 二、个人词库 (Personal Vocabulary Book)

### 现状分析

当前 `VocabService` 支持：
- 内置词库加载（band 5-9 精选 + master 大词库）
- `load_custom(path)` 可加载外部 JSON 文件
- `Word.is_custom` 标记自定义词

`ReviewService` 支持：
- 按单词名（`word` 字段）记录学习状态
- 艾宾浩斯间隔（0/1/2/4/7/15/30 天）
- 星标 / 难词标记

**痛点**：没有持久化的个人词库管理——用户无法在 CLI 中添加/编辑/删除自定义单词；无法创建分类（如 "写作高频词"、"听力场景词"）；自定义词与复习系统没有深度集成。

---

### 子特性列表

| # | 子特性 | 优先级 | 工作量 | 说明 |
|---|--------|--------|--------|------|
| 2.1 | **个人词库 CRUD** | P0 | M | 新增 `personal_vocab` SQLite 表，支持 `ib vocab add <word> [--meaning ...] [--band ...]`、`ib vocab edit`、`ib vocab delete`。添加时如果内置词库中有该词，自动填充 phonetic/example 等字段。 |
| 2.2 | **分类管理 (Categories)** | P0 | M | 新增 `vocab_categories` 表和 `vocab_category_words` 关联表。支持 `ib vocab category create/list/delete`。一个词可属于多个分类。内置默认分类：`favorites`（收藏）、`mistakes`（错词本）。 |
| 2.3 | **错词自动收录** | P0 | S | quiz / review / exam 中答错的词自动加入 `mistakes` 分类。在 `ReviewService.record_learn(correct=False)` 中触发。 |
| 2.4 | **复习系统集成** | P0 | M | 个人词库中的词自动进入艾宾浩斯复习队列。`ib vocab review` 支持 `--category` 参数，只复习指定分类的词。需在 `learning_records` 表加 `source` 列（`builtin` / `personal`）。 |
| 2.5 | **批量导入导出** | P1 | M | `ib vocab import <file>` 支持 JSON / CSV / 纯文本（每行一个词）。纯文本模式自动从内置词库匹配释义。`ib vocab export [--category ...] [--format json/csv]`。 |
| 2.6 | **写作批改联动** | P1 | S | 批改结果中标注的生词/高级替换词，一键加入个人词库。在 `GradeResult` 展示时提供 `[+] 加入词库` 交互。 |
| 2.7 | **分类统计面板** | P1 | S | `ib stats show` 中新增个人词库统计：各分类词数、复习进度、掌握率。复用现有 `stats_service.py` 框架。 |
| 2.8 | **智能推荐关联** | P2 | S | 基于个人词库中的薄弱 topic 和 band 分布，增强 `recommend_service.py` 的推荐逻辑。 |
| 2.9 | **词库分享** | P2 | M | 导出分类为可分享格式（JSON + 元数据），其他用户可通过 `ib vocab import --shared` 导入。 |

### 数据模型变更

```python
class PersonalWord(BaseModel):
    id: Optional[int] = None
    word: str
    phonetic: str = ""
    meaning: str = ""
    pos: str = ""
    band: int = 5
    topic: str = ""
    example: str = ""
    example_cn: str = ""
    note: str = ""               # 用户笔记
    source: str = "manual"       # manual / quiz_mistake / grading / import
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

class VocabCategory(BaseModel):
    id: Optional[int] = None
    name: str
    description: str = ""
    is_system: bool = False      # 系统内置分类不可删除
    word_count: int = 0
    created_at: Optional[str] = None
```

### DB Schema

```sql
CREATE TABLE IF NOT EXISTS personal_vocab (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    word TEXT UNIQUE NOT NULL,
    phonetic TEXT DEFAULT '',
    meaning TEXT DEFAULT '',
    pos TEXT DEFAULT '',
    band INTEGER DEFAULT 5,
    topic TEXT DEFAULT '',
    example TEXT DEFAULT '',
    example_cn TEXT DEFAULT '',
    note TEXT DEFAULT '',
    source TEXT DEFAULT 'manual',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS vocab_categories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL,
    description TEXT DEFAULT '',
    is_system INTEGER DEFAULT 0,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS vocab_category_words (
    category_id INTEGER NOT NULL,
    word_id INTEGER NOT NULL,
    added_at TEXT NOT NULL,
    PRIMARY KEY (category_id, word_id),
    FOREIGN KEY (category_id) REFERENCES vocab_categories(id) ON DELETE CASCADE,
    FOREIGN KEY (word_id) REFERENCES personal_vocab(id) ON DELETE CASCADE
);

-- learning_records 扩展
ALTER TABLE learning_records ADD COLUMN source TEXT DEFAULT 'builtin';
```

### 实现要点

- **自动填充**：`ib vocab add contribute` 时，先在 VocabService 中查找，命中则预填所有字段，用户可覆盖。
- **与 ReviewService 集成**：个人词库的词需要构造为 `Word` 对象才能传入 `record_learn()`。`PersonalWord` → `Word` 转换是轻量的。
- **错词收录去重**：同一个词只在 `mistakes` 分类中出现一次，重复答错只更新 `learning_records`。
- **系统分类保护**：`favorites` 和 `mistakes` 标记 `is_system=True`，禁止删除/重命名。

---

## 三、工作量估算参考

| 标记 | 含义 | 大致范围 |
|------|------|----------|
| S | Small | 模型 + service 改动，< 100 行新增代码 |
| M | Medium | 涉及 DB 迁移 + service + CLI 命令，100-300 行 |
| L | Large | 新 prompt 体系 + 模型 + 解析逻辑 + 测试，300+ 行 |

## 四、建议实施顺序

**Phase 1 (v1.3.0)**：所有 P0 特性
1. 个人词库 CRUD (2.1) + 分类管理 (2.2) → 基础设施
2. 错词自动收录 (2.3) + 复习集成 (2.4) → 闭环
3. Task 1 支持 (1.3) → 覆盖更多题型
4. 句级标注 (1.1) + 段落分析 (1.2) → 批改质量飞跃

**Phase 2 (v1.3.1)**：P1 特性
5. 批量导入导出 (2.5)
6. 写作联动 (2.6) + 分类统计 (2.7)
7. 错误分类统计 (1.4) + Diff View (1.5)

**Phase 3 (v1.4.0)**：P2 特性
8. 批改历史对比 (1.6) + 缓存去重 (1.7)
9. 智能推荐关联 (2.8) + 词库分享 (2.9)
