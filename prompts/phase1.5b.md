# Phase 1.5b — 统计增强 + 学习计划

你正在开发 ielts-buddy CLI 工具的 v0.2.0 版本。先读 CLAUDE.md 了解项目。

## 任务清单

### 1. 学习统计增强
在 `services/stats_service.py` 和 `commands/stats.py` 中扩展：

- **连续学习天数 (streak)**：计算当前连续学习天数 + 历史最长记录
- **每日趋势**：`ib stats trend` — 过去 7/30 天的学习量（用 Rich 的 bar chart 或 ASCII 图）
- **Band 进度**：`ib stats progress` — 每个 Band 的掌握比例进度条
  - 掌握定义：记忆等级 >= 4（30天间隔）
  - 用 Rich 的 Progress bar 展示
- **学习历史**：`ib stats history [-n 7]` — 查看最近 N 天的学习日志

### 2. 学习计划
新增 `src/ielts_buddy/commands/plan.py` 和 `services/plan_service.py`：

- `ib plan` — 显示今日学习计划（待复习数 + 建议新学数）
- `ib plan set --band 7 --daily 30` — 设置目标 Band 和每日学习量
- `ib plan set --exam-date 2026-06-01` — 设置考试日期
- 配置存储在 `~/.ib/plan.json`
- 每次启动 CLI 时自动显示待办提醒（在 cli.py 中加 hook）

### 3. 统计服务扩展
在 `services/stats_service.py` 中新增方法：
- `get_streak()` → (current_streak, max_streak)
- `get_daily_trend(days=7)` → [(date, count, correct_rate), ...]
- `get_band_progress()` → [(band, total, mastered, ratio), ...]
- `get_history(days=7)` → [DailyRecord, ...]

### 4. 更新测试
- 为所有新功能编写 pytest 测试
- 确保现有测试不被破坏

## 重要约束
- plan 配置用 JSON 文件存储（不用 SQLite）
- 所有中文注释和提示信息
- 用 Rich 做终端美化（Progress, Table, Panel）
- 不要修改现有接口
