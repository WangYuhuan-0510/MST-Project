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

    N_CAPS = 16
    RAW_BASELINE_MIN = 20.0  # 去除 0~20 的底噪段

    def __init__(
        self,
        parent=None,
        *,
        enable_zoom: bool = False,
        show_capillary_index: bool = True,
    ) -> None:
        super().__init__(parent)
        self._enable_zoom = bool(enable_zoom)
        self._show_capillary_index = bool(show_capillary_index)

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

        # 当前显示曲线（x 轴统一为 1~16 索引坐标）
        self._scan_xs: List[float] = []
        self._scan_ys: List[float] = []

        self._frozen: bool = False

        self._canvas.mpl_connect("button_press_event", self._on_click)
        self._redraw()

    def _to_index_x(self, distance_x: float) -> float:
        """将串口距离坐标（0~15）映射到索引坐标（1~16）。"""
        return float(distance_x) + 1.0

    def _init_axes(self) -> None:
        self._ax.set_title("Capillary Scan (Raw Serial Data)")
        if self._show_capillary_index:
            self._ax.set_xlabel("Capillary Index")
            self._ax.set_xticks(list(range(1, self.N_CAPS + 1)))
            self._ax.set_xticklabels([str(i) for i in range(1, self.N_CAPS + 1)])
        else:
            self._ax.set_xlabel("Scan Position")
            self._ax.set_xticks([])

        self._ax.set_ylabel("Signal Intensity")
        self._ax.set_xlim(0.5, 16.5)
        self._ax.set_ylim(0, 180)
        self._ax.grid(True, alpha=0.25)

    @Slot(object)
    def handle_sample(self, sample: MSTDataSample) -> None:
        if sample.mst_stream:
            self.freeze()
            return
        if self._frozen:
            return

        x = self._to_index_x(float(sample.distance))
        y = float(sample.fluo)
        if y < self.RAW_BASELINE_MIN:
            return

        self._scan_xs.append(x)
        self._scan_ys.append(y)
        self._redraw()

    def freeze(self) -> None:
        self._frozen = True
        self._redraw()

    def set_selection(self, idx: Optional[int]) -> None:
        self._selected_idx = idx

    def set_enabled_mask(self, mask: List[bool]) -> None:
        self._enabled_mask = mask

    def set_raw_scan(
        self,
        xs: Sequence[float],
        ys: Sequence[float],
        enabled_mask: Optional[List[bool]] = None,
        selected_idx: Optional[int] = None,
        frozen: bool = False,
    ) -> None:
        """按串口原始扫描点绘制；过滤 0~20 低值段；峰顶显示到 1~16 索引。"""
        n = min(len(xs), len(ys))
        fx: List[float] = []
        fy: List[float] = []
        for i in range(n):
            x = self._to_index_x(float(xs[i]))
            y = float(ys[i])
            if y < self.RAW_BASELINE_MIN:
                continue
            fx.append(x)
            fy.append(y)

        self._scan_xs = fx
        self._scan_ys = fy
        self._enabled_mask = enabled_mask
        self._selected_idx = selected_idx
        self._frozen = bool(frozen)
        self._redraw()

    def set_scan(
        self,
        y_center: Iterable[float],
        enabled_mask: Optional[List[bool]] = None,
        selected_idx: Optional[int] = None,
    ) -> None:
        """兼容模拟模式：16 通道强度合成高斯峰，峰顶与索引 1~16 对齐。"""
        ys = [float(v) for v in y_center][: self.N_CAPS]
        if len(ys) < self.N_CAPS:
            ys.extend([0.0] * (self.N_CAPS - len(ys)))

        self._enabled_mask = enabled_mask
        self._selected_idx = selected_idx
        self._frozen = True

        sigma = 0.16
        x_dense = np.linspace(0.5, 16.5, 600)
        y_dense = np.zeros_like(x_dense)
        for i, amp in enumerate(ys):
            mu = float(i + 1)
            y_dense += amp * np.exp(-((x_dense - mu) ** 2) / (2 * sigma * sigma))

        self._scan_xs = x_dense.tolist()
        self._scan_ys = y_dense.tolist()
        self._redraw()

    def _redraw(self) -> None:
        self._ax.clear()
        self._init_axes()

        if self._scan_xs:
            self._ax.plot(self._scan_xs, self._scan_ys, color="#1f77b4", lw=1.2, alpha=0.85)

        self._canvas.draw_idle()

    def _on_click(self, event) -> None:
        if event.inaxes != self._ax or event.xdata is None:
            return
        idx = int(round(float(event.xdata))) - 1
        if 0 <= idx < self.N_CAPS:
            self.point_clicked.emit(idx)
