from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

from sqlalchemy import select

from .db import session_scope
from .models import ExperimentRecord, Project, RunRecord


@dataclass
class Repository:
    """
    数据访问接口，占位实现。
    """

    def create_project(self, name: str) -> Project:
        with session_scope() as s:
            p = Project(name=name)
            s.add(p)
            s.flush()
            return p

    def list_projects(self) -> List[Project]:
        with session_scope() as s:
            return list(s.scalars(select(Project).order_by(Project.created_at.desc())))

    def create_experiment(self, project_id: int, name: str) -> ExperimentRecord:
        with session_scope() as s:
            exp = ExperimentRecord(project_id=project_id, name=name)
            s.add(exp)
            s.flush()
            return exp

    def add_run(self, experiment_id: int, kd: float | None = None, r_squared: float | None = None) -> RunRecord:
        with session_scope() as s:
            run = RunRecord(experiment_id=experiment_id, kd=kd, r_squared=r_squared)
            s.add(run)
            s.flush()
            return run

    def get_latest_run(self, experiment_id: int) -> Optional[RunRecord]:
        with session_scope() as s:
            stmt = select(RunRecord).where(RunRecord.experiment_id == experiment_id).order_by(RunRecord.created_at.desc())
            return s.scalars(stmt).first()

