# Phase 4a — 每日学习网页报告

先读 CLAUDE.md 了解项目。

## 任务

### 1. 新建 src/ielts_buddy/services/report_service.py
- `generate_daily_report(date=None)` — 生成指定日期的学习报告数据
  - 包含：当日学习量、测验结果、新学单词列表、复习单词列表、正确率、streak
- `generate_calendar_data(months=3)` — 生成最近 N 月的日历热力图数据
  - 格式: [{date: "2026-03-06", count: 25, level: 3}, ...] (level 0-4)
- `generate_index_data()` — 生成首页数据（总览+日历）

### 2. 新建 src/ielts_buddy/templates/daily_report.html
- 每日学习报告页面模板（Jinja2）
- 内容：日期标题、统计卡片（学习量/正确率/streak）、单词列表（新学+复习）、Band进度条
- 风格：简洁学术，蓝白配色，响应式
- 底部导航：← 前一天 | 首页 | 后一天 →

### 3. 新建 src/ielts_buddy/templates/index.html
- 首页模板
- 内容：学习日历热力图（类似 GitHub contribution graph）、总体统计、最近学习记录
- 日历每个格子可点击跳转到当日报告

### 4. 新建 src/ielts_buddy/commands/report.py
- `ib report daily [--date 2026-03-06]` — 生成某天的报告 HTML
- `ib report build` — 生成全部报告（所有有数据的日期 + 首页）到 `~/.ib/site/`
- `ib report serve` — 本地预览（python -m http.server）
- 在 cli.py 注册

### 5. 写测试，确保旧 399 个测试不破坏

## 约束
- Jinja2 模板，纯静态 HTML+CSS（不依赖 JS 框架）
- 日历热力图用纯 CSS 实现（grid + background-color）
- 中文界面
- Rich 终端美化
