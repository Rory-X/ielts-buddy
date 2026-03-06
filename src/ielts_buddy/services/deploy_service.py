"""部署服务：GitHub Pages 初始化 + 自动部署"""

from __future__ import annotations

import subprocess
from datetime import datetime
from pathlib import Path

from ielts_buddy.core.config import get_app_dir
from ielts_buddy.services.report_service import ReportService


def _get_site_dir() -> Path:
    """获取静态站点目录"""
    return get_app_dir() / "site"


_PAGES_WORKFLOW = """\
name: Deploy to GitHub Pages

on:
  push:
    branches: [gh-pages]

permissions:
  contents: read
  pages: write
  id-token: write

concurrency:
  group: "pages"
  cancel-in-progress: false

jobs:
  deploy:
    environment:
      name: github-pages
      url: ${{ steps.deployment.outputs.page_url }}
    runs-on: ubuntu-latest
    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Setup Pages
        uses: actions/configure-pages@v5

      - name: Upload artifact
        uses: actions/upload-pages-artifact@v3
        with:
          path: "."

      - name: Deploy to GitHub Pages
        id: deployment
        uses: actions/deploy-pages@v4
"""


class DeployService:
    """GitHub Pages 部署服务"""

    def __init__(self) -> None:
        self._site_dir = _get_site_dir()

    def setup_github_pages(self, repo_url: str) -> Path:
        """初始化 GitHub Pages 仓库

        在 ~/.ib/site/ 下：
        1. git init（如果尚未初始化）
        2. 设置 remote
        3. 创建 .github/workflows/pages.yml
        4. 创建初始 .nojekyll 文件
        """
        self._site_dir.mkdir(parents=True, exist_ok=True)

        # git init
        if not (self._site_dir / ".git").exists():
            self._run_git("init")
            self._run_git("checkout", "-b", "gh-pages")

        # 设置 remote
        try:
            self._run_git("remote", "get-url", "origin")
            # remote 已存在，更新
            self._run_git("remote", "set-url", "origin", repo_url)
        except RuntimeError:
            self._run_git("remote", "add", "origin", repo_url)

        # 创建 workflow
        workflow_dir = self._site_dir / ".github" / "workflows"
        workflow_dir.mkdir(parents=True, exist_ok=True)
        (workflow_dir / "pages.yml").write_text(_PAGES_WORKFLOW, encoding="utf-8")

        # .nojekyll
        (self._site_dir / ".nojekyll").touch()

        return self._site_dir

    def deploy_to_pages(self) -> str:
        """构建报告并推送到 GitHub Pages

        返回 commit message
        """
        # 先调 report build 生成 HTML
        svc = ReportService()
        svc.build_site()
        svc.close()

        # git add + commit + push
        now = datetime.now().strftime("%Y-%m-%d %H:%M")
        commit_msg = f"更新学习报告 {now}"

        self._run_git("add", "-A")

        # 检查是否有变更
        try:
            self._run_git("diff", "--cached", "--quiet")
            # 没有变更
            return "无新变更，跳过部署"
        except RuntimeError:
            pass  # 有变更，继续

        self._run_git("commit", "-m", commit_msg)
        self._run_git("push", "-u", "origin", "gh-pages", "--force")

        return commit_msg

    def get_status(self) -> dict:
        """获取部署状态"""
        status = {
            "site_dir": str(self._site_dir),
            "initialized": (self._site_dir / ".git").exists(),
            "has_remote": False,
            "remote_url": "",
            "html_count": 0,
            "last_commit": "",
        }

        if not status["initialized"]:
            return status

        try:
            url = self._run_git("remote", "get-url", "origin")
            status["has_remote"] = True
            status["remote_url"] = url.strip()
        except RuntimeError:
            pass

        html_files = list(self._site_dir.glob("*.html"))
        status["html_count"] = len(html_files)

        try:
            log = self._run_git("log", "-1", "--format=%s (%ci)")
            status["last_commit"] = log.strip()
        except RuntimeError:
            pass

        return status

    def _run_git(self, *args: str) -> str:
        """在 site_dir 下执行 git 命令"""
        result = subprocess.run(
            ["git", *args],
            cwd=str(self._site_dir),
            capture_output=True,
            text=True,
            timeout=60,
        )
        if result.returncode != 0:
            raise RuntimeError(result.stderr.strip() or f"git {args[0]} 失败")
        return result.stdout
