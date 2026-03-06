"""学习计划服务：管理学习目标和每日计划"""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

from ielts_buddy.core.config import get_app_dir
from ielts_buddy.core.models import StudyPlan


class PlanService:
    """学习计划服务"""

    def __init__(self, plan_path: Path | None = None) -> None:
        self._path = plan_path or get_app_dir() / "plan.json"

    def get_plan(self) -> StudyPlan | None:
        """获取当前学习计划，未设置返回 None"""
        if not self._path.exists():
            return None
        try:
            data = json.loads(self._path.read_text(encoding="utf-8"))
            return StudyPlan(**data)
        except (json.JSONDecodeError, Exception):
            return None

    def save_plan(self, plan: StudyPlan) -> None:
        """保存学习计划"""
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(
            plan.model_dump_json(indent=2),
            encoding="utf-8",
        )

    def set_plan(
        self,
        target_band: int | None = None,
        daily_new: int | None = None,
        exam_date: str | None = None,
    ) -> StudyPlan:
        """设置/更新学习计划"""
        existing = self.get_plan()
        now = date.today().isoformat()

        if existing is None:
            plan = StudyPlan(
                target_band=target_band or 7,
                daily_new=daily_new or 30,
                exam_date=exam_date,
                created_at=now,
                updated_at=now,
            )
        else:
            if target_band is not None:
                existing.target_band = target_band
            if daily_new is not None:
                existing.daily_new = daily_new
            if exam_date is not None:
                existing.exam_date = exam_date
            existing.updated_at = now
            plan = existing

        self.save_plan(plan)
        return plan

    def delete_plan(self) -> bool:
        """删除学习计划"""
        if self._path.exists():
            self._path.unlink()
            return True
        return False

    def days_until_exam(self) -> int | None:
        """获取距离考试的天数"""
        plan = self.get_plan()
        if plan is None or not plan.exam_date:
            return None
        try:
            exam = date.fromisoformat(plan.exam_date)
            delta = (exam - date.today()).days
            return max(0, delta)
        except ValueError:
            return None
