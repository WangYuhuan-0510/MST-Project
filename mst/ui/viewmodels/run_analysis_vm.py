from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import numpy as np
from PySide6.QtCore import QObject, Signal

from mst.core.fitting import fit_4pl_curve


@dataclass(frozen=True)
class DoseFit:
    x_fit: List[float]
    y_fit: List[float]
    text: str
    params: Dict[str, float]


def _sigmoid_4pl(x: np.ndarray, bottom: float, top: float, ec50: float, hill: float) -> np.ndarray:
    x = np.asarray(x, dtype=float)
    x_safe = np.maximum(x, 1e-12)
    ec50_safe = max(float(ec50), 1e-12)
    return bottom + (top - bottom) / (1.0 + (x_safe / ec50_safe) ** (-hill))


class RunAnalysisViewModel(QObject):
    """
    运行/分析共享 ViewModel：统一管理三图联动所需状态与派生数据。

    目标：
    - Scan：每根毛细管中心荧光值（可选择/剔除）
    - Trace：每根毛细管 F(t)，包含 0s(IR on) 与可拖动 T1
    - Dose：用 T1 特征值形成散点，并拟合一条 S 型曲线（4PL）
    """

    changed = Signal()
    selected_capillary_changed = Signal(int)
    t1_changed = Signal(float)

    def __init__(self, parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self._running: bool = False

        self.n_capillaries: int = 16
        self.selected_capillary: int = 0
        self.enabled_mask: List[bool] = [True] * self.n_capillaries

        self.scan_center: List[float] = [0.0] * self.n_capillaries

        self.t: List[float] = []
        self.traces: List[List[float]] = [[] for _ in range(self.n_capillaries)]
        self.t_ir_on_s: float = 0.0
        self.t1_s: float = 2.0

        self.concentrations: List[float] = []
        self.feature_y: List[float] = []
        self.fit: Optional[DoseFit] = None

        self._sim_time_s: float = -5.0
        self._sim_dt_s: float = 0.08
        self._sim_total_s: float = 25.0

        self._sim_ec50: float = 2.0
        self._sim_bottom: float = 0.2
        self._sim_top: float = 1.0
        self._sim_hill: float = 1.2
        self._sim_noise: float = 0.01

    @property
    def running(self) -> bool:
        return self._running

    def start_simulation(self) -> None:
        self._running = True
        self._sim_time_s = -5.0

        self.concentrations = np.logspace(-2, 1, self.n_capillaries).tolist()
        self.enabled_mask = [True] * self.n_capillaries
        self.selected_capillary = 0

        base = 800.0
        drift = np.linspace(-40, 40, self.n_capillaries)
        i = np.arange(self.n_capillaries, dtype=float)
        denom = max(self.n_capillaries - 1, 1)
        peaks = 35.0 * np.sin((i / denom) * np.pi * 4.0) ** 2
        self.scan_center = (base + drift + peaks + np.random.normal(0, 8, self.n_capillaries)).tolist()

        self.t = []
        self.traces = [[] for _ in range(self.n_capillaries)]
        self.fit = None
        self._recompute_features_and_fit()

        self.changed.emit()
        self.selected_capillary_changed.emit(self.selected_capillary)
        self.t1_changed.emit(float(self.t1_s))

    def stop(self) -> None:
        self._running = False
        self.changed.emit()

    def clear(self) -> None:
        self._running = False
        self.selected_capillary = 0
        self.enabled_mask = [True] * self.n_capillaries
        self.scan_center = [0.0] * self.n_capillaries
        self.t = []
        self.traces = [[] for _ in range(self.n_capillaries)]
        self.concentrations = []
        self.feature_y = []
        self.fit = None
        self._sim_time_s = -5.0
        self.changed.emit()
        self.selected_capillary_changed.emit(self.selected_capillary)
        self.t1_changed.emit(float(self.t1_s))

    def tick(self) -> None:
        if not self._running:
            return
        if self._sim_time_s >= self._sim_total_s:
            self.stop()
            return

        self._sim_time_s = self._sim_time_s + self._sim_dt_s
        t = float(self._sim_time_s)
        self.t.append(t)

        x = np.asarray(self.concentrations, dtype=float)
        bind = _sigmoid_4pl(x, self._sim_bottom, self._sim_top, self._sim_ec50, self._sim_hill)

        for i in range(self.n_capillaries):
            baseline = 1.0 + 0.002 * (i - self.n_capillaries / 2)
            if t < self.t_ir_on_s:
                y = baseline + np.random.normal(0.0, self._sim_noise)
            else:
                tau = 0.7 + 0.03 * i
                amp = 0.12 + 0.25 * float(bind[i])
                y = baseline - amp * (1.0 - np.exp(-(t - self.t_ir_on_s) / tau))
                y += np.random.normal(0.0, self._sim_noise)
            self.traces[i].append(float(y))

        self._recompute_features_and_fit()
        self.changed.emit()

    def set_selected_capillary(self, idx: int) -> None:
        idx = int(idx)
        idx = max(0, min(self.n_capillaries - 1, idx))
        if idx == self.selected_capillary:
            return
        self.selected_capillary = idx
        self.selected_capillary_changed.emit(idx)
        self.changed.emit()

    def set_t1(self, t1_s: float) -> None:
        t1_s = float(t1_s)
        t1_s = max(-0.5, min(self._sim_total_s, t1_s))
        if abs(t1_s - self.t1_s) < 1e-9:
            return
        self.t1_s = t1_s
        self._recompute_features_and_fit()
        self.t1_changed.emit(float(self.t1_s))
        self.changed.emit()

    def toggle_enabled(self, idx: int) -> None:
        idx = int(idx)
        if idx < 0 or idx >= self.n_capillaries:
            return
        self.enabled_mask[idx] = not self.enabled_mask[idx]
        self._recompute_features_and_fit()
        self.changed.emit()

    def _recompute_features_and_fit(self) -> None:
        self.feature_y = []
        if not self.t:
            self.fit = None
            return

        t_arr = np.asarray(self.t, dtype=float)
        j = int(np.argmin(np.abs(t_arr - float(self.t1_s))))

        y = np.asarray([trace[j] if len(trace) > j else np.nan for trace in self.traces], dtype=float)
        self.feature_y = y.tolist()

        mask = np.asarray(self.enabled_mask, dtype=bool) & np.isfinite(y)
        x_fit = np.asarray(self.concentrations, dtype=float)[mask]
        y_fit = y[mask]
        if x_fit.size < 4:
            self.fit = None
            return

        try:
            res = fit_4pl_curve(x_fit.tolist(), y_fit.tolist())
        except Exception:
            self.fit = None
            return

        self.fit = DoseFit(
            x_fit=[float(v) for v in res.x_fit],
            y_fit=[float(v) for v in res.y_fit],
            text=(
                f"4PL: Bottom={res.bottom:.4g}, Top={res.top:.4g}, "
                f"EC50={res.ec50:.4g}, Hill={res.hill:.3g}, R²={res.r_squared:.4f}"
            ),
            params={
                "bottom": float(res.bottom),
                "top": float(res.top),
                "ec50": float(res.ec50),
                "hill": float(res.hill),
                "r_squared": float(res.r_squared),
            },
        )
