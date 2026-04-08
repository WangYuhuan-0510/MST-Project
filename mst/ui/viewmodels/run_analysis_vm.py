from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Sequence, Tuple

import numpy as np
from PySide6.QtCore import QObject, Signal


@dataclass(frozen=True)
class DoseFit:
    x_fit: List[float]
    y_fit: List[float]
    text: str


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

        # Scan
        self.scan_center: List[float] = [0.0] * self.n_capillaries

        # Trace
        self.t: List[float] = []
        self.traces: List[List[float]] = [[] for _ in range(self.n_capillaries)]
        self.t_ir_on_s: float = 0.0
        self.t1_s: float = 2.0

        # Dose response (x: concentration, y: feature at T1)
        self.concentrations: List[float] = []
        self.feature_y: List[float] = []
        self.fit: Optional[DoseFit] = None

        # 内部：模拟参数（后续可以接入真实设备/协议）
        # MST trace 时间范围：-5s ~ 25s
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

        # 浓度按对数均匀（更贴近真实剂量反应排布）
        self.concentrations = np.logspace(-2, 1, self.n_capillaries).tolist()
        self.enabled_mask = [True] * self.n_capillaries
        self.selected_capillary = 0

        # Scan：沿扫描方向多峰类高斯包络 + 漂移/噪声（与 mock_device.simulate_mst_time_fluorescence 一致）
        base = 800.0
        drift = np.linspace(-40, 40, self.n_capillaries)
        i = np.arange(self.n_capillaries, dtype=float)
        denom = max(self.n_capillaries - 1, 1)
        peaks = 35.0 * np.sin((i / denom) * np.pi * 4.0) ** 2
        self.scan_center = (base + drift + peaks + np.random.normal(0, 8, self.n_capillaries)).tolist()

        # Trace：清空
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

        # 每根毛细管的“结合程度”由浓度通过 4PL 决定，再映射到 trace 的热泳响应幅度
        x = np.asarray(self.concentrations, dtype=float)
        bind = _sigmoid_4pl(x, self._sim_bottom, self._sim_top, self._sim_ec50, self._sim_hill)

        for i in range(self.n_capillaries):
            # baseline + IR on 后的指数响应（非常简化）
            baseline = 1.0 + 0.002 * (i - self.n_capillaries / 2)
            if t < self.t_ir_on_s:
                y = baseline + np.random.normal(0.0, self._sim_noise)
            else:
                tau = 0.7 + 0.03 * i
                amp = 0.12 + 0.25 * float(bind[i])  # binding 越强，幅度越大（仅模拟）
                y = baseline - amp * (1.0 - np.exp(-(t - self.t_ir_on_s) / tau))
                y += np.random.normal(0.0, self._sim_noise)
            self.traces[i].append(float(y))

        # T1 特征点与拟合
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
        # 允许稍早于 0s，但不允许超过采集总时长
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

        # 找到最接近 T1 的时间点
        t_arr = np.asarray(self.t, dtype=float)
        j = int(np.argmin(np.abs(t_arr - float(self.t1_s))))

        # 取 T1 的荧光值作为剂量反应 y（你后续可替换为 ΔF/F 等）
        y = np.asarray([trace[j] if len(trace) > j else np.nan for trace in self.traces], dtype=float)
        self.feature_y = y.tolist()

        # 仅对 enabled 且有效点拟合
        mask = np.asarray(self.enabled_mask, dtype=bool) & np.isfinite(y)
        x_fit = np.asarray(self.concentrations, dtype=float)[mask]
        y_fit = y[mask]
        if x_fit.size < 4:
            self.fit = None
            return

        # 简单的 4PL 拟合：用粗略初值 + 最小二乘（避免引入更多依赖，先用 numpy 迭代）
        # 注：这里是“UI demo 级别”的拟合，占位；后续建议迁移到 mst/core/fitting.py 用 scipy.curve_fit
        bottom0 = float(np.nanmin(y_fit))
        top0 = float(np.nanmax(y_fit))
        ec500 = float(np.median(x_fit))
        hill0 = 1.0

        p = np.array([bottom0, top0, ec500, hill0], dtype=float)
        lr = 0.05
        for _ in range(80):
            # 数值梯度下降（足够演示 UI；真实分析请用 curve_fit）
            pred = _sigmoid_4pl(x_fit, *p)
            err = pred - y_fit
            loss = float(np.mean(err**2))
            if not np.isfinite(loss):
                break
            grad = np.zeros_like(p)
            eps = 1e-4
            for k in range(4):
                p2 = p.copy()
                p2[k] += eps
                pred2 = _sigmoid_4pl(x_fit, *p2)
                loss2 = float(np.mean((pred2 - y_fit) ** 2))
                grad[k] = (loss2 - loss) / eps
            p = p - lr * grad

            # 简单约束，避免跑飞
            p[2] = float(np.clip(p[2], np.min(x_fit), np.max(x_fit)))
            p[3] = float(np.clip(p[3], 0.1, 5.0))

        x_dense = np.logspace(np.log10(max(1e-6, float(np.min(self.concentrations)))), np.log10(float(np.max(self.concentrations))), 200)
        y_dense = _sigmoid_4pl(x_dense, *p)
        text = f"4PL: Bottom={p[0]:.4g}, Top={p[1]:.4g}, EC50={p[2]:.4g}, Hill={p[3]:.3g}"
        self.fit = DoseFit(x_fit=x_dense.tolist(), y_fit=y_dense.tolist(), text=text)

