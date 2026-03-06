# Phase 3 — 大词库集成 + 性能优化

先读 CLAUDE.md 了解项目。

## 背景
词库从 526 词扩充到 4485 词（vocab_master.json, 1.3MB）。
需要集成新词库并优化读写检索性能。

## 任务

### 1. 改造 vocab_service.py — 统一词库加载
- 新增 `vocab_master.json` 为主词库（4485 词）
- 保留 `vocab_band[5-9].json` 作为精选子集（原有 526 词，标记为 curated）
- `load_words()` 默认加载 master 词库
- `load_words(curated=True)` 只加载精选词库
- 新增 `--source master/curated` 参数给 vocab 相关命令

### 2. 性能优化 — 索引和缓存
vocab_master.json 有 4485 词 / 1.3MB，直接遍历搜索会慢。设计优化方案：

**a) 启动加速：懒加载**
- 词库不在 import 时加载，改为首次访问时加载
- 加载后缓存到模块级变量

**b) 搜索加速：内存索引**
- 加载时构建：
  - `_word_index: dict[str, Word]` — 精确查找 O(1)
  - `_band_index: dict[int, list[Word]]` — 按 Band 分组
  - `_topic_index: dict[str, list[Word]]` — 按主题分组
  - `_search_index: list[tuple[str, Word]]` — (word+definition 拼接的小写文本, Word)，用于模糊搜索
- search 用 index 而非全量遍历

**c) 可选：SQLite 词库缓存**
- 首次加载 JSON 后写入 `~/.ib/vocab_cache.db` (SQLite)
- 后续加载直接读 SQLite（比解析 1.3MB JSON 快）
- JSON 修改时间变化时重建缓存
- 创建索引: CREATE INDEX idx_word ON vocab(word); CREATE INDEX idx_band ON vocab(band);

### 3. 更新所有命令
- `ib vocab random` / `ib vocab quiz` / `ib vocab review` 默认用大词库
- `ib vocab list` / `ib vocab search` / `ib vocab info` 适配大词库
- 增加 `--curated` flag 可切换回精选词库
- `ib vocab info` 显示大词库统计

### 4. 更新测试
- 确保 350 个旧测试通过（可能需要调整部分断言数字）
- 新增大词库相关测试

## 约束
- 不删除旧 JSON（向后兼容）
- 中文注释
- Rich 美化
- 性能目标：搜索 <100ms，加载 <500ms
