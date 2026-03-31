from __future__ import annotations

from typing import Iterable, List, Optional, Sequence

import numpy as np
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from PySide6.QtCore import Signal, Slot
from PySide6.QtWidgets import QWidget, QVBoxLayout

from mst.device.protocol import MSTDataSample


class CapillaryScanPlot(QWidget):
    point_clicked = Signal(int)

    X_MIN = 0.0
    X_MAX = 15.0
    N_CAPS = 16
    CAP_WIDTH = (X_MAX - X_MIN) / N_CAPS

    def __init__(self, parent=None, *, enable_zoom: bool = False) -> None:
        super().__init__(parent)
        self._enable_zoom = bool(enable_zoom)
        self._fig = Figure(figsize=(4, 3), tight_layout=True)
        self._canvas = FigureCanvas(self._fig)
        self._ax = self._fig.add_subplot(111)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        if self._enable_zoom:
            from matplotlib.backends.backend_qtagg import NavigationToolbar2QT as NavigationToolbar
            layout.addWidget(NavigationToolbar(self._canvas, self))
        layout.addWidget(self._canvas)

        self._selected_idx: Optional[int] = None
        self._enabled_mask: Optional[List[bool]] = None

        # 当前显示的扫描原始点（严格按串口原始数据）
        self._scan_xs: List[float] = []
        self._scan_ys: List[float] = []

        # 每通道峰值标记（由原始点统计得到）
        self._cap_peaks: List[float] = [0.0] * self.N_CAPS
        self._cap_peak_x: List[float] = [
            self.X_MIN + (i + 0.5) * self.CAP_WIDTH for i in range(self.N_CAPS)
        ]

        self._frozen: bool = False

        self._canvas.mpl_connect("button_press_event", self._on_click)
        self._redraw()

    def _init_axes(self) -> None:
        self._ax.set_title("Capillary Scan (Raw Serial Data)")
        self._ax.set_xlabel("Scan Position")
        self._ax.set_ylabel("Signal Intensity")
        self._ax.set_xlim(self.X_MIN - 0.3, self.X_MAX + 0.3)
        self._ax.set_ylim(0, 130)
        self._ax.grid(True, alpha=0.25)

    def _recompute_peaks_from_raw(self) -> None:
        self._cap_peaks = [0.0] * self.N_CAPS
        for x, y in zip(self._scan_xs, self._scan_ys):
            ch = int((x - self.X_MIN) / self.CAP_WIDTH)
            if 0 <= ch < self.N_CAPS and y > self._cap_peaks[ch]:
                self._cap_peaks[ch] = y

    @Slot(object)
    def handle_sample(self, sample: MSTDataSample) -> None:
        """兼容直接单点喂入：仅用于原始串口扫描帧。"""
        if sample.mst_stream:
            self.freeze()
            return
        if self._frozen:
            return

        self._scan_xs.append(float(sample.distance))
        self._scan_ys.append(float(sample.fluo))
        self._recompute_peaks_from_raw()
        self._redraw()

    def freeze(self) -> None:
        self._frozen = True
        self._redraw()

    def set_selection(self, idx: Optional[int]) -> None:
        self._selected_idx = idx
        self._redraw()

    def set_enabled_mask(self, mask: List[bool]) -> None:
        self._enabled_mask = mask
        self._redraw()

    def set_raw_scan(
        self,
        xs: Sequence[float],
        ys: Sequence[float],
        enabled_mask: Optional[List[bool]] = None,
        selected_idx: Optional[int] = None,
        frozen: bool = False,
    ) -> None:
        """按原始串口扫描点绘制，不做任何高斯合成。"""
        n = min(len(xs), len(ys))
        self._scan_xs = [float(v) for v in xs[:n]]
        self._scan_ys = [float(v) for v in ys[:n]]
        self._enabled_mask = enabled_mask
        self._selected_idx = selected_idx
        self._frozen = bool(frozen)
        self._recompute_peaks_from_raw()
        self._redraw()

    def set_scan(
        self,
        y_center: Iterable[float],
        enabled_mask: Optional[List[bool]] = None,
        selected_idx: Optional[int] = None,
    ) -> None:
        """
        兼容旧接口（模拟模式）：由 16 通道强度合成高斯峰。
        串口模式请使用 set_raw_scan()。
        """
        ys = [float(v) for v in y_center][: self.N_CAPS]
        if len(ys) < self.N_CAPS:
            ys.extend([0.0] * (self.N_CAPS - len(ys)))

        self._enabled_mask = enabled_mask
        self._selected_idx = selected_idx
        self._frozen = True
        self._cap_peaks = ys

        sigma = self.CAP_WIDTH * 0.16
        x_dense = np.linspace(self.X_MIN, self.X_MAX, 500)
        y_dense = np.zeros_like(x_dense)
        for i, amp in enumerate(ys):
            mu = self.X_MIN + (i + 0.5) * self.CAP_WIDTH
            y_dense += amp * np.exp(-((x_dense - mu) ** 2) / (2 * sigma * sigma))

        self._scan_xs = x_dense.tolist()
        self._scan_ys = y_dense.tolist()
        self._redraw()

    def _redraw(self) -> None:
        self._ax.clear()
        self._init_axes()

        if self._scan_xs:
            self._ax.plot(self._scan_xs, self._scan_ys, color="#1f77b4", lw=1.2, alpha=0.85)

        mask = self._enabled_mask or [True] * self.N_CAPS
        for i in range(self.N_CAPS):
            py = self._cap_peaks[i]
            if py < 1.0:
                continue

            px = self._cap_peak_x[i]
            if not mask[i]:
                color, ec, sz = "#c7c7c7", "#999999", 25
            elif self._selected_idx is not None and i == self._selected_idx:
                color, ec, sz = "#2ca02c", "#2ca02c", 60
            else:
                color, ec, sz = "white", "black", 30

            self._ax.scatter(px, py, color=color, edgecolors=ec, s=sz, zorder=4)

        self._canvas.draw_idle()

    def _on_click(self, event) -> None:
        if event.inaxes != self._ax or event.xdata is None:
            return
        ch = int((float(event.xdata) - self.X_MIN) / self.CAP_WIDTH)
        if 0 <= ch < self.N_CAPS:
            self.point_clicked.emit(ch)
