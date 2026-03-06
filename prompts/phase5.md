# Phase 5 — AI 写作批改 + GitHub Pages 自动部署

先读 CLAUDE.md 了解项目。

## 任务 A：AI 写作批改

### 1. 新建 src/ielts_buddy/services/grading_service.py
- `grade_essay(essay_text, topic=None)` — 调用 LLM 批改作文
  - 输入：作文文本 + 可选话题
  - 输出：GradeResult 对象，包含：
    - overall_score: float (1-9)
    - task_response: {score, comment}
    - coherence: {score, comment}
    - lexical_resource: {score, comment}
    - grammar: {score, comment}
    - suggestions: list[str] — 逐条改进建议
    - rewrite: str — 高分改写示例（可选）
  - LLM 调用：用 subprocess 调 grok.py，system prompt 设为雅思考官
  - 降级：grok 失败自动用备用服务

### 2. 新建 src/ielts_buddy/commands/grade.py
- `ib grade essay` — 交互式输入作文（多行输入，空行+Ctrl-D 结束）
- `ib grade file <path>` — 从文件读取作文
- `ib grade essay --topic "Some people think..."` — 指定话题
- 输出用 Rich Panel 展示：
  - 四维评分条（彩色进度条）
  - 总分（大字）
  - 改进建议（编号列表）
  - 高分改写（可折叠）
- `ib grade history` — 查看历史批改记录（存 SQLite）
- 在 cli.py 注册 grade 命令组

### 3. 数据模型
在 core/models.py 新增 GradeResult, GradeDimension pydantic 模型

## 任务 B：GitHub Pages 自动部署

### 4. 新建 src/ielts_buddy/services/deploy_service.py
- `setup_github_pages(repo_url)` — 初始化 GitHub Pages
  - 在 ~/.ib/site/ 下初始化 git repo
  - 创建 .github/workflows/pages.yml
- `deploy_to_pages()` — 部署
  - 先调 report build 生成全部 HTML
  - git add + commit + push 到 gh-pages 分支

### 5. 新建 src/ielts_buddy/commands/deploy.py
- `ib deploy setup --repo https://github.com/user/ielts-report` — 初始化
- `ib deploy push` — 构建 + 推送到 GitHub Pages
- `ib deploy status` — 查看部署状态
- 在 cli.py 注册

### 6. 新建 .github/workflows/pages.yml (项目根目录)
- GitHub Actions workflow
- 触发：push to gh-pages branch
- 步骤：checkout → setup pages → upload artifact → deploy

### 7. 写测试，确保旧 470 个测试不破坏

## 约束
- grok.py 路径: /home/node/clawd/tools/grok.py
- grok.py 用法: `python3 /home/node/clawd/tools/grok.py "prompt" -s "system prompt" --json`
- 返回 JSON: {"content": "...", "model": "...", "usage": {...}}
- Rich 终端美化，中文界面
- 批改 prompt 要求 LLM 返回 JSON 格式，方便解析
- GitHub Pages workflow 用标准 actions/deploy-pages
