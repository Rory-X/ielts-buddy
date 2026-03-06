# Phase 2b — 每日邮件升级

你正在开发 ielts-buddy CLI 工具的 v0.3.0 版本。先读 CLAUDE.md 了解项目。

## 背景
现有每日邮件脚本 scripts/daily-ielts-mail.py 每天发 20 个随机单词。
需要升级为更丰富的学习邮件。

## 任务清单

### 1. 邮件内容服务
创建 `src/ielts_buddy/services/email_service.py`：
- `generate_daily_email()` — 生成每日学习邮件内容
- 邮件包含：
  - 昨日学习成果总结（学了几个词、测验正确率、streak）
  - 今日待复习单词列表（根据艾宾浩斯到期的）
  - 今日推荐新词（根据学习计划的目标 Band 推荐）
  - 学习进度条（各 Band 掌握比例）
- 输出为 HTML 格式（美观的邮件模板）

### 2. 邮件模板
创建 `src/ielts_buddy/templates/daily_email.html`：
- 简洁美观的 HTML 邮件模板
- 响应式设计（手机端可读）
- 配色：蓝白色调，学术风格
- 包含：标题、统计面板、单词卡片、进度条

### 3. 邮件命令
在命令中新增：
- `ib email preview` — 预览今日邮件内容（终端渲染）
- `ib email send` — 立即发送今日邮件（使用 smtplib）
- 邮件配置存 `~/.ib/email.json`（smtp server/port/user/pass/to）

### 4. 更新测试
为所有新功能编写 pytest 测试。

## 重要约束
- HTML 模板用 Jinja2
- 邮件用 smtplib + email.mime
- 所有中文内容
- 不破坏现有功能
