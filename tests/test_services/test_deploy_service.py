"""测试 DeployService"""

from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from ielts_buddy.services.deploy_service import DeployService, _PAGES_WORKFLOW


# ---- Fixtures ----

@pytest.fixture(autouse=True)
def _tmp_home(tmp_path):
    """每个测试使用独立的临时数据目录"""
    os.environ["IELTS_BUDDY_HOME"] = str(tmp_path / ".ielts-buddy")
    yield
    os.environ.pop("IELTS_BUDDY_HOME", None)


@pytest.fixture
def deploy_service() -> DeployService:
    return DeployService()


# ---- Tests: setup_github_pages ----

class TestSetupGitHubPages:

    @patch("ielts_buddy.services.deploy_service.subprocess.run")
    def test_setup_creates_site_dir(self, mock_run, deploy_service: DeployService, tmp_path):
        mock = MagicMock()
        mock.returncode = 0
        mock.stdout = ""
        mock.stderr = ""
        mock_run.return_value = mock

        # remote get-url 会失败（不存在），所以第 3 次调用让它失败
        def side_effect(*args, **kwargs):
            cmd = args[0]
            m = MagicMock()
            m.stdout = ""
            m.stderr = ""
            if "get-url" in cmd:
                m.returncode = 1
                m.stderr = "not found"
                raise_err = RuntimeError("not found")
                # We need to actually return error code
                return MagicMock(returncode=1, stderr="not found", stdout="")
            m.returncode = 0
            return m

        mock_run.side_effect = side_effect

        site_dir = deploy_service.setup_github_pages("https://github.com/user/repo.git")
        assert site_dir.exists()

    @patch("ielts_buddy.services.deploy_service.subprocess.run")
    def test_setup_creates_workflow(self, mock_run, deploy_service: DeployService):
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

        # 让 remote get-url 失败
        def side_effect(*args, **kwargs):
            cmd = args[0]
            if "get-url" in cmd:
                return MagicMock(returncode=1, stderr="not found", stdout="")
            return MagicMock(returncode=0, stdout="", stderr="")

        mock_run.side_effect = side_effect

        site_dir = deploy_service.setup_github_pages("https://github.com/user/repo.git")
        workflow = site_dir / ".github" / "workflows" / "pages.yml"
        assert workflow.exists()

    @patch("ielts_buddy.services.deploy_service.subprocess.run")
    def test_setup_creates_nojekyll(self, mock_run, deploy_service: DeployService):
        def side_effect(*args, **kwargs):
            cmd = args[0]
            if "get-url" in cmd:
                return MagicMock(returncode=1, stderr="not found", stdout="")
            return MagicMock(returncode=0, stdout="", stderr="")

        mock_run.side_effect = side_effect

        site_dir = deploy_service.setup_github_pages("https://github.com/user/repo.git")
        assert (site_dir / ".nojekyll").exists()


# ---- Tests: get_status ----

class TestGetStatus:

    def test_status_not_initialized(self, deploy_service: DeployService):
        status = deploy_service.get_status()
        assert not status["initialized"]
        assert not status["has_remote"]
        assert status["html_count"] == 0

    def test_status_keys(self, deploy_service: DeployService):
        status = deploy_service.get_status()
        assert "site_dir" in status
        assert "initialized" in status
        assert "has_remote" in status
        assert "remote_url" in status
        assert "html_count" in status
        assert "last_commit" in status


# ---- Tests: deploy_to_pages ----

class TestDeployToPages:

    @patch("ielts_buddy.services.deploy_service.subprocess.run")
    @patch("ielts_buddy.services.deploy_service.ReportService")
    def test_deploy_no_changes(self, mock_report_cls, mock_run, deploy_service: DeployService):
        """没有变更时跳过"""
        # 先初始化 site dir 和 .git
        site_dir = deploy_service._site_dir
        site_dir.mkdir(parents=True, exist_ok=True)
        (site_dir / ".git").mkdir()

        mock_svc = MagicMock()
        mock_svc.build_site.return_value = site_dir
        mock_report_cls.return_value = mock_svc

        # git add 成功，git diff --cached --quiet 成功（无变更）
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

        msg = deploy_service.deploy_to_pages()
        assert "无新变更" in msg

    @patch("ielts_buddy.services.deploy_service.subprocess.run")
    @patch("ielts_buddy.services.deploy_service.ReportService")
    def test_deploy_with_changes(self, mock_report_cls, mock_run, deploy_service: DeployService):
        """有变更时执行 commit + push"""
        site_dir = deploy_service._site_dir
        site_dir.mkdir(parents=True, exist_ok=True)
        (site_dir / ".git").mkdir()

        mock_svc = MagicMock()
        mock_svc.build_site.return_value = site_dir
        mock_report_cls.return_value = mock_svc

        def side_effect(*args, **kwargs):
            cmd = args[0]
            # diff --cached --quiet 返回 1 (有变更)
            if "diff" in cmd and "--quiet" in cmd:
                return MagicMock(returncode=1, stderr="changes", stdout="")
            return MagicMock(returncode=0, stdout="", stderr="")

        mock_run.side_effect = side_effect

        msg = deploy_service.deploy_to_pages()
        assert "更新学习报告" in msg


# ---- Tests: _PAGES_WORKFLOW content ----

class TestPagesWorkflow:

    def test_workflow_has_trigger(self):
        assert "gh-pages" in _PAGES_WORKFLOW

    def test_workflow_has_deploy_step(self):
        assert "actions/deploy-pages@v4" in _PAGES_WORKFLOW

    def test_workflow_has_upload_step(self):
        assert "actions/upload-pages-artifact@v3" in _PAGES_WORKFLOW

    def test_workflow_has_checkout(self):
        assert "actions/checkout@v4" in _PAGES_WORKFLOW

    def test_workflow_has_permissions(self):
        assert "pages: write" in _PAGES_WORKFLOW
        assert "id-token: write" in _PAGES_WORKFLOW
