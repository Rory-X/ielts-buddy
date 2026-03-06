"""测试学习计划服务"""

from __future__ import annotations

import json
from datetime import date, timedelta
from pathlib import Path

import pytest

from ielts_buddy.core.models import StudyPlan
from ielts_buddy.services.plan_service import PlanService


class TestPlanServiceNoPlan:
    """测试未设置计划时的行为"""

    def test_get_plan_none(self, tmp_path: Path):
        svc = PlanService(plan_path=tmp_path / "plan.json")
        assert svc.get_plan() is None

    def test_days_until_exam_none(self, tmp_path: Path):
        svc = PlanService(plan_path=tmp_path / "plan.json")
        assert svc.days_until_exam() is None

    def test_delete_plan_no_file(self, tmp_path: Path):
        svc = PlanService(plan_path=tmp_path / "plan.json")
        assert svc.delete_plan() is False


class TestPlanServiceSetPlan:
    """测试设置学习计划"""

    def test_set_plan_new(self, tmp_path: Path):
        svc = PlanService(plan_path=tmp_path / "plan.json")
        plan = svc.set_plan(target_band=7, daily_new=30)
        assert plan.target_band == 7
        assert plan.daily_new == 30
        assert plan.created_at is not None

    def test_set_plan_with_exam_date(self, tmp_path: Path):
        svc = PlanService(plan_path=tmp_path / "plan.json")
        plan = svc.set_plan(target_band=6, daily_new=20, exam_date="2026-06-01")
        assert plan.exam_date == "2026-06-01"
        assert plan.target_band == 6

    def test_set_plan_defaults(self, tmp_path: Path):
        svc = PlanService(plan_path=tmp_path / "plan.json")
        plan = svc.set_plan()
        assert plan.target_band == 7
        assert plan.daily_new == 30

    def test_set_plan_update(self, tmp_path: Path):
        svc = PlanService(plan_path=tmp_path / "plan.json")
        svc.set_plan(target_band=6, daily_new=20)
        plan = svc.set_plan(target_band=7)
        assert plan.target_band == 7
        assert plan.daily_new == 20  # 保持原值

    def test_set_plan_update_daily(self, tmp_path: Path):
        svc = PlanService(plan_path=tmp_path / "plan.json")
        svc.set_plan(target_band=6, daily_new=20)
        plan = svc.set_plan(daily_new=50)
        assert plan.target_band == 6  # 保持原值
        assert plan.daily_new == 50

    def test_set_plan_update_exam_date(self, tmp_path: Path):
        svc = PlanService(plan_path=tmp_path / "plan.json")
        svc.set_plan(target_band=7, daily_new=30)
        plan = svc.set_plan(exam_date="2026-09-01")
        assert plan.exam_date == "2026-09-01"
        assert plan.target_band == 7

    def test_set_plan_updates_timestamp(self, tmp_path: Path):
        svc = PlanService(plan_path=tmp_path / "plan.json")
        plan1 = svc.set_plan(target_band=7)
        plan2 = svc.set_plan(daily_new=50)
        assert plan2.updated_at is not None
        assert plan2.created_at == plan1.created_at


class TestPlanServiceGetPlan:
    """测试获取学习计划"""

    def test_get_plan_after_set(self, tmp_path: Path):
        svc = PlanService(plan_path=tmp_path / "plan.json")
        svc.set_plan(target_band=8, daily_new=40, exam_date="2026-12-01")
        plan = svc.get_plan()
        assert plan is not None
        assert plan.target_band == 8
        assert plan.daily_new == 40
        assert plan.exam_date == "2026-12-01"

    def test_get_plan_corrupted_json(self, tmp_path: Path):
        plan_path = tmp_path / "plan.json"
        plan_path.write_text("invalid json{{{", encoding="utf-8")
        svc = PlanService(plan_path=plan_path)
        assert svc.get_plan() is None

    def test_save_and_load_plan(self, tmp_path: Path):
        plan_path = tmp_path / "plan.json"
        svc = PlanService(plan_path=plan_path)
        plan = StudyPlan(target_band=9, daily_new=50, exam_date="2026-06-01")
        svc.save_plan(plan)
        loaded = svc.get_plan()
        assert loaded is not None
        assert loaded.target_band == 9
        assert loaded.daily_new == 50


class TestPlanServiceDelete:
    """测试删除学习计划"""

    def test_delete_plan(self, tmp_path: Path):
        svc = PlanService(plan_path=tmp_path / "plan.json")
        svc.set_plan(target_band=7)
        assert svc.delete_plan() is True
        assert svc.get_plan() is None

    def test_delete_plan_twice(self, tmp_path: Path):
        svc = PlanService(plan_path=tmp_path / "plan.json")
        svc.set_plan(target_band=7)
        svc.delete_plan()
        assert svc.delete_plan() is False


class TestPlanServiceExamDate:
    """测试考试日期相关功能"""

    def test_days_until_exam_future(self, tmp_path: Path):
        svc = PlanService(plan_path=tmp_path / "plan.json")
        future = (date.today() + timedelta(days=30)).isoformat()
        svc.set_plan(exam_date=future)
        days = svc.days_until_exam()
        assert days == 30

    def test_days_until_exam_today(self, tmp_path: Path):
        svc = PlanService(plan_path=tmp_path / "plan.json")
        svc.set_plan(exam_date=date.today().isoformat())
        days = svc.days_until_exam()
        assert days == 0

    def test_days_until_exam_past(self, tmp_path: Path):
        svc = PlanService(plan_path=tmp_path / "plan.json")
        past = (date.today() - timedelta(days=10)).isoformat()
        svc.set_plan(exam_date=past)
        days = svc.days_until_exam()
        assert days == 0

    def test_days_until_exam_no_date(self, tmp_path: Path):
        svc = PlanService(plan_path=tmp_path / "plan.json")
        svc.set_plan(target_band=7)
        assert svc.days_until_exam() is None

    def test_days_until_exam_invalid_date(self, tmp_path: Path):
        plan_path = tmp_path / "plan.json"
        plan_path.write_text(
            json.dumps({"target_band": 7, "daily_new": 30, "exam_date": "not-a-date"}),
            encoding="utf-8",
        )
        svc = PlanService(plan_path=plan_path)
        assert svc.days_until_exam() is None


class TestStudyPlanModel:
    """测试 StudyPlan 模型"""

    def test_default_values(self):
        plan = StudyPlan()
        assert plan.target_band == 7
        assert plan.daily_new == 30
        assert plan.exam_date is None

    def test_custom_values(self):
        plan = StudyPlan(target_band=8, daily_new=50, exam_date="2026-06-01")
        assert plan.target_band == 8
        assert plan.daily_new == 50
        assert plan.exam_date == "2026-06-01"

    def test_band_validation_low(self):
        with pytest.raises(Exception):
            StudyPlan(target_band=4)

    def test_band_validation_high(self):
        with pytest.raises(Exception):
            StudyPlan(target_band=10)

    def test_daily_new_validation(self):
        with pytest.raises(Exception):
            StudyPlan(daily_new=0)

    def test_serialization(self):
        plan = StudyPlan(target_band=7, daily_new=30, exam_date="2026-06-01")
        data = json.loads(plan.model_dump_json())
        assert data["target_band"] == 7
        assert data["daily_new"] == 30
        assert data["exam_date"] == "2026-06-01"
