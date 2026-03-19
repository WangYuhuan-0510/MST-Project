from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional


@dataclass
class SimulationConfig:
    kd_true: float = 2.0
    r_max_true: float = 5.0
    noise_std: float = 0.05
    n_points: int = 60
    x_min: float = 0.05
    x_max: float = 10.0


@dataclass
class LastRun:
    x: List[float] = field(default_factory=list)
    y: List[float] = field(default_factory=list)
    fit_kd: Optional[float] = None
    fit_r_squared: Optional[float] = None


@dataclass
class AppState:
    """
    用于 UI 页面间共享的最小状态容器（先模拟跑通用）。
    """

    workspace_dir: Path = field(default_factory=lambda: Path.cwd())
    sim: SimulationConfig = field(default_factory=SimulationConfig)
    last_run: LastRun = field(default_factory=LastRun)

