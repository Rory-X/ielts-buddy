# Phase 4b — 听力资源 + 听写模式

先读 CLAUDE.md 了解项目。

## 任务

### 1. 新建 src/ielts_buddy/data/listening_resources.json
听力练习资源索引（30+ 条），格式：
```json
[{
  "title": "资源名称",
  "type": "podcast/video/course/website",
  "url": "链接",
  "difficulty": "beginner/intermediate/advanced",
  "description": "简短描述",
  "topics": ["education", "science"],
  "free": true
}]
```
包含：BBC Learning English, TED Talks, IELTS Listening Practice 等主流资源

### 2. 新建 src/ielts_buddy/services/listening_service.py
- `get_resources(type=None, difficulty=None)` — 获取资源列表
- `get_resource_detail(idx)` — 资源详情
- `generate_dictation(words, count=10)` — 生成听写测验的单词列表
  - 从词库选词，返回 word + phonetic + definition
  - 用户需根据读音拼写单词

### 3. 新建 src/ielts_buddy/commands/listen.py
- `ib listen resources [--type podcast] [--difficulty intermediate]` — 浏览听力资源
- `ib listen dictation [-n 10] [-b 7]` — 听写模式
  - 显示中文释义和音标提示
  - 用户输入英文拼写
  - 记录正确/错误
- 在 cli.py 注册

### 4. 写测试，确保旧测试不破坏

## 约束
- 听写模式不需要真正播放音频（CLI 环境），用音标+释义提示代替
- Rich 美化
- 中文注释
