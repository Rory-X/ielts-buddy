# Phase 6 — 模拟考试 + 飞书 Bitable 直连

先读 CLAUDE.md 了解项目。

## 任务 A：模拟考试模式

### 1. 新建 src/ielts_buddy/services/exam_service.py
- `create_exam(band=None, count=30, time_limit=20)` — 生成模拟考试
  - 从词库随机选 count 个词，混合 en2zh/zh2en
  - 返回 ExamSession 对象: {id, questions, time_limit, started_at}
- `submit_answer(session, q_index, answer)` — 提交单题答案
  - 返回 {correct: bool, answer: str}
- `finish_exam(session)` — 结束考试，生成报告
  - 返回 ExamReport: {score, total, accuracy, band_breakdown, weak_words, duration}
- `get_exam_history(limit=10)` — 历史考试记录 (SQLite)

### 2. 新建 src/ielts_buddy/commands/exam.py
- `ib exam start [-n 30] [-b 7] [--time 20]` — 开始考试
  - 显示倒计时，逐题作答，超时自动提交
  - 用 Rich Live 显示倒计时
- `ib exam history [-n 10]` — 历史记录
- 在 cli.py 注册

### 3. 数据模型
在 core/models.py 新增 ExamSession, ExamQuestion, ExamReport

## 任务 B：飞书 Bitable 直连

### 4. 新建 src/ielts_buddy/services/feishu_service.py
- `sync_to_bitable(app_token, table_id)` — 同步学习数据到飞书表
  - 字段: 单词/Band/掌握等级/正确次数/错误次数/上次复习/下次复习
- `create_bitable_schema(app_token, table_id)` — 自动建表（如果为空）
- `sync_stats_to_bitable(app_token, table_id)` — 同步统计数据
  - 字段: 日期/学习量/正确率/新学/复习/streak

### 5. 新建 src/ielts_buddy/commands/feishu.py
- `ib feishu sync --app-token XXX --table-id YYY` — 同步词汇数据
- `ib feishu stats --app-token XXX --table-id YYY` — 同步统计
- `ib feishu setup` — 交互式配置（保存到 ~/.ib/feishu.json）
- 在 cli.py 注册

注意: feishu_service.py 不能直接调用飞书 API（sandbox 环境）。
改为：导出 JSON 到 ~/.ib/sync/feishu/ 目录，格式兼容飞书 Bitable 批量导入。
同时生成一个 `sync_instructions.md` 说明如何导入。

### 6. 写测试，确保旧 532 个测试不破坏

## 约束
- Rich 终端美化，中文界面
- 模拟考试计时器用简单的 time.time() 对比即可（非交互环境不需要 Live）
- 倒计时在每题提示中显示剩余时间
