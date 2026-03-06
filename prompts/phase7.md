# Phase 7 — 智能学习推荐 + GitHub Actions CI

先读 CLAUDE.md 了解项目。

## 任务 A：智能学习推荐

### 1. 新建 src/ielts_buddy/services/recommend_service.py
- `get_weak_words(limit=20)` — 获取薄弱词（错误率最高的词）
  - 从 SQLite 复习记录中统计，按错误率排序
- `get_due_words(limit=20)` — 获取到期需复习的词
- `get_recommended_new(band=None, count=10)` — 推荐新词
  - 排除已学过的词，优先推荐目标 Band 的词
- `predict_mastery(days=7)` — 预测 N 天后的掌握率
  - 基于当前复习间隔和遗忘曲线计算
- `get_study_suggestion()` — 综合学习建议
  - 返回: {weak_count, due_count, suggested_new, priority_band, message}

### 2. 新建 src/ielts_buddy/commands/recommend.py
- `ib recommend` — 显示今日智能推荐
  - 薄弱词提醒、推荐学习计划、预测掌握率
- `ib recommend weak [-n 20]` — 查看薄弱词
- `ib recommend new [-n 10] [-b 7]` — 推荐新词
- 在 cli.py 注册

## 任务 B：GitHub Actions CI

### 3. 新建 .github/workflows/ci.yml
```yaml
name: CI
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v4
    - uses: actions/setup-python@v5
      with: {python-version: '3.11'}
    - run: pip install -e ".[dev]"
    - run: pytest --tb=short
```

### 4. 更新 pyproject.toml / setup.cfg
- 添加 [dev] extras: pytest, pytest-cov

### 5. 写测试，确保旧测试不破坏

## 约束
- 推荐算法基于已有 SQLite 数据，不需要额外依赖
- CI workflow 简洁，只跑 pytest
