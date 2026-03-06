# Phase 2a — 飞书同步 + 邮件升级

先读 CLAUDE.md 了解项目。

## 任务

### 1. 新建 src/ielts_buddy/services/sync_service.py
导出学习数据为 JSON 文件，供外部飞书 API 工具导入：
- `export_vocab(output_dir)` — 导出全部词库为 JSON（含掌握状态）
- `export_records(output_dir)` — 导出学习记录
- `export_stats(output_dir)` — 导出统计摘要
- 输出到 `~/.ib/sync/` 目录

### 2. 新建 src/ielts_buddy/commands/sync.py  
- `ib sync vocab` / `ib sync records` / `ib sync stats` / `ib sync all`
- 在 cli.py 中注册

### 3. 新建 src/ielts_buddy/services/email_service.py
- `generate_daily_email()` — 生成 HTML 邮件内容
- 包含：昨日学习成果、今日待复习单词、推荐新词、Band进度
- 用 Jinja2 模板

### 4. 新建 src/ielts_buddy/templates/daily_email.html
- 简洁美观的 HTML 邮件模板（蓝白学术风）
- 响应式，手机可读

### 5. 新建 src/ielts_buddy/commands/email.py
- `ib email preview` — 终端预览邮件
- `ib email send` — 发送邮件（smtplib）
- 邮件配置：`~/.ib/email.json`
- 在 cli.py 中注册

### 6. 写测试，确保全部通过

## 约束
- 不破坏现有 201 个测试
- 中文注释和提示
- Rich 美化终端输出
