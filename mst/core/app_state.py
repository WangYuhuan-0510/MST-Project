from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict

from mst.core.experiment_schema import default_setup_data


@dataclass
class ExperimentSession:
    """实验实例数据（与实验类型定义分离）。"""

    experiment_type_id: str = "pre_test"
    setup_data: Dict[str, Any] = field(default_factory=lambda: default_setup_data("pre_test"))


@dataclass
class AppState:
    """用于 UI 页面间共享状态。"""

    workspace_dir: Path = field(default_factory=lambda: Path.cwd())
    current_session: ExperimentSession = field(default_factory=ExperimentSession)
