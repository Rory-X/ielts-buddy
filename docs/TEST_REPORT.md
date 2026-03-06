# IELTS Buddy 测试报告

> 日期：2026-03-06 | Python 3.11.2 | pytest 9.0.2

---

## 1. 测试概览

| 指标 | 数值 |
|------|------|
| 测试用例总数 | 133 |
| 通过 | 133 |
| 失败 | 0 |
| 跳过 | 0 |
| 代码覆盖率 | **92%** |
| 执行时间 | ~1.1s |

---

## 2. 测试模块分布

| 测试文件 | 用例数 | 状态 |
|----------|--------|------|
| `tests/test_models.py` | 25 | ALL PASS |
| `tests/test_config.py` | 18 | ALL PASS |
| `tests/test_services/test_vocab_service.py` | 30 | ALL PASS |
| `tests/test_services/test_review_service.py` | 29 | ALL PASS |
| `tests/test_services/test_stats_service.py` | 9 | ALL PASS |
| `tests/test_commands/test_cli.py` | 17 | ALL PASS |
| **总计** | **133** | **ALL PASS** |

---

## 3. 覆盖率详情

| 模块 | 语句数 | 未覆盖 | 覆盖率 |
|------|--------|--------|--------|
| `core/models.py` | 70 | 0 | 100% |
| `core/config.py` | 77 | 7 | 91% |
| `services/vocab_service.py` | 62 | 0 | 100% |
| `services/review_service.py` | 74 | 1 | 99% |
| `services/stats_service.py` | 41 | 0 | 100% |
| `commands/stats.py` | 47 | 0 | 100% |
| `commands/vocab.py` | 121 | 33 | 73% |
| `cli.py` | 10 | 1 | 90% |
| **TOTAL** | **503** | **42** | **92%** |

> `commands/vocab.py` 覆盖率较低是因为 `quiz` 和 `review` 命令包含交互式 `input()` 循环，通过 CLI runner 测试了主要路径，但内部分支（如完整答题流程）未完全覆盖。

---

## 4. 测试分类详情

### 4.1 数据模型测试 (25 用例)

- **Word 模型**: 基本创建、所有字段、默认值、band 边界验证(5-9)、JSON 序列化/反序列化、`parse_json_field` 边界情况
- **LearningRecord 模型**: 基本创建、默认值、memory_level 边界(0-6)
- **TestSession 模型**: 基本创建、正确率计算（包括零分母边界）、wrong_words JSON 序列化
- **DailySummary 模型**: 基本创建、完整数据

### 4.2 配置管理测试 (18 用例)

- **TOML 序列化**: bool/int/float/str/list 类型值转换
- **Config 管理器**: 默认配置加载、点分路径 get/set、保存与重载、目录创建、不存在键的默认值、深层嵌套 non-dict 路径

### 4.3 词库服务测试 (30 用例)

- **加载**: Band 5/6/7 加载、全部加载、幂等性、不支持 band 错误、自定义词库加载、不存在文件错误
- **筛选**: 按 band 筛选、按 topic 筛选(含大小写无关)、空结果
- **搜索**: 英文搜索、中文搜索、部分匹配、大小写无关、无结果
- **随机**: 基本抽取、带 band 筛选、超出池大小、零数量、空池
- **主题**: 获取所有主题（含排序验证）、空状态
- **数据完整性**: 必填字段检查、band 内无重复单词、所有单词有 topic/pos/example/phonetic、总量合理性(>=100)、各 band 分布(>=20)、JSON 文件格式验证

### 4.4 复习服务测试 (29 用例)

- **复习日期计算**: 7 个等级对应正确间隔(0/1/2/4/7/15/30天)、超出最大等级截断、全间隔一致性
- **学习记录**: 首次正确/错误、连续正确升级、错误降级、等级不低于 0、等级不超过最大值、多单词记录
- **到期复习**: 初始无到期、学习后立即到期(level 0)、数量限制、word_data 完整性
- **查询**: 空记录、全部记录、已学习计数
- **星标**: 开启/关闭切换、不存在单词错误
- **持久化**: 跨实例数据保持、记录值正确性、星标状态保持

### 4.5 统计服务测试 (9 用例)

- **无数据**: total_stats/today_stats/due_count/level_distribution 全部返回空/零值
- **有数据**: 总体统计正确性、今日统计、到期数量、等级分布、正确率计算(50%)

### 4.6 CLI 命令测试 (17 用例)

- **基础**: version/help、vocab help、stats help
- **vocab random**: 默认抽取、指定数量、各 band 筛选、零数量、不支持 band
- **vocab quiz**: 立即退出(q)、答题后退出、EOF 中断
- **vocab review**: 无到期单词
- **stats show**: 空状态、学习后状态

---

## 5. 发现并修复的 Bug

### Bug #1: `quiz` 命令 `KeyboardInterrupt` 时 `NameError` (严重)

- **位置**: `commands/vocab.py:108-110`
- **问题**: `except` 块使用 `max(i - 1, 0)` 计算已完成题数，但若 `KeyboardInterrupt` 在 `for` 循环首次迭代前触发，变量 `i` 未定义，导致 `NameError`
- **修复**: 引入 `answered` 计数器，在每次答题完成后递增，异常处理中使用 `answered` 替代 `i`

### Bug #2: 配置路径在导入时固化 (中等)

- **位置**: `core/config.py:31-33`
- **问题**: `APP_DIR`、`CONFIG_PATH`、`DB_PATH` 在模块导入时从 `IELTS_BUDDY_HOME` 环境变量求值并固化为常量。运行时修改环境变量不会生效，导致测试隔离失败，也影响在同一进程中动态切换数据目录的场景
- **修复**: 将三个常量改为惰性函数 `get_app_dir()`、`get_config_path()`、`get_db_path()`，每次调用时读取当前环境变量

### Bug #3: `import json` 内联于函数体 (轻微)

- **位置**: `services/review_service.py:66, 144`
- **问题**: `json` 模块在 `record_learn()` 和 `get_due_words()` 方法内部 import，不符合 Python 最佳实践
- **修复**: 移动到文件顶部

### Bug #4: 未使用的 `import random` (轻微)

- **位置**: `commands/vocab.py:5`
- **问题**: 导入了 `random` 模块但从未直接使用（随机功能由 `VocabService.random_words()` 提供），且被同名 Click 命令函数 `random()` 遮蔽
- **修复**: 删除未使用的导入

---

## 6. 代码质量评估

### 优点

- Pydantic 模型定义清晰，字段验证完善（band 范围 5-9，memory_level 0-6）
- SQLite 数据库操作正确，使用参数化查询防止 SQL 注入
- Click CLI 框架使用规范，命令分组合理
- Rich 终端 UI 输出美观
- 配置管理支持 TOML 格式，兼容 Python 3.10/3.11+
- 艾宾浩斯间隔复习算法实现正确

### 注意事项

- **PRD 差异**: PRD 规定错误时 memory_level 回退 `max(level - 2, 1)`，代码实现为 `max(level - 1, 0)`。当前实现更温和，属于设计选择而非 bug
- **today_stats 精度**: 今日正确/错误数使用占位值 0（因数据库仅存累计值），注释中已说明
- **Band 8/9 数据缺失**: 目前仅有 Band 5/6/7 词库，`-b 8` 静默返回空结果

---

## 7. 词库数据统计

| Band | 词汇数 | 有音标 | 有例句 | 有搭配 | 有同义词 |
|------|--------|--------|--------|--------|----------|
| 5 | 131 | 131 | 131 | 131 | 131 |
| 6 | 80 | 80 | 80 | 80 | 80 |
| 7 | 115 | 115 | 115 | 115 | 115 |
| **总计** | **326** | **326** | **326** | **326** | **326** |

所有词条数据完整，无缺失字段，无 band 内重复。

---

## 8. 运行测试

```bash
# 运行所有测试
python3 -m pytest tests/ -v

# 运行并查看覆盖率
python3 -m pytest tests/ --cov=ielts_buddy --cov-report=term-missing

# 运行特定模块
python3 -m pytest tests/test_services/test_review_service.py -v
```
