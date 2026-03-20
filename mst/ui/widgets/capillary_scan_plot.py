from __future__ import annotations

from typing import Iterable, List, Optional
import numpy as np

from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from PySide6.QtCore import Signal
from PySide6.QtWidgets import QWidget, QVBoxLayout


class CapillaryScanPlot(QWidget):
    point_clicked = Signal(int)

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
        self._n_caps: int = 0

        # 控制峰的形状
        self._sigma = 0.15      # 峰宽
        self._offset_step = 1.0 # 每个capillary间距

        self._canvas.mpl_connect("button_press_event", self._on_click)

    def set_scan(
        self,
        y_center: Iterable[float],  # 每个cap的峰中心（强度）
        enabled_mask: Optional[List[bool]] = None,
        selected_idx: Optional[int] = None,
    ) -> None:
        ys = list(y_center)
        n = len(ys)
        enabled = enabled_mask if enabled_mask is not None else [True] * n

        self._selected_idx = selected_idx
        self._n_caps = n

        self._ax.clear()
        self._ax.set_title("Capillary Scan (Gaussian Peaks)")
        self._ax.set_xlabel("Scan Position")
        self._ax.set_ylabel("Signal Intensity")
        self._ax.grid(True, alpha=0.25)

        if n == 0:
            self._canvas.draw_idle()
            return

        # 基础x（局部峰）
        x_local = np.linspace(-0.5, 0.5, 120)

        for i in range(n):
            # 颜色逻辑
            if not enabled[i]:
                color = "#c7c7c7"
                alpha = 0.4
            elif selected_idx is not None and i == selected_idx:
                color = "#2ca02c"
                alpha = 1.0
            else:
                color = "#1f77b4"
                alpha = 0.8

            # 高斯峰（用y_center作为幅值）
            A = ys[i]
            y = A * np.exp(-(x_local ** 2) / (2 * self._sigma ** 2))

            # 横向平移 → 不同capillary
            x_shifted = x_local + i * self._offset_step

            self._ax.plot(x_shifted, y, color=color, alpha=alpha, linewidth=2)

        # 设置范围
        self._ax.set_xlim(-0.5, (n - 1) * self._offset_step + 0.5)
        self._ax.set_ylim(0, max(ys) * 1.2 if ys else 1)

        # 可选：标记中心点
        for i in range(n):
            x0 = i * self._offset_step
            y0 = ys[i]

            if selected_idx is not None and i == selected_idx:
                size = 60
            else:
                size = 30

            self._ax.scatter(x0, y0, color="white", edgecolors="black", s=size, zorder=3)

        self._canvas.draw_idle()

    def _on_click(self, event) -> None:
        if event.inaxes != self._ax or event.xdata is None:
            return

        clicked_x = float(event.xdata)

        # 找最近的capillary
        idx = int(round(clicked_x / self._offset_step))

        if idx < 0 or idx >= self._n_caps:
            return

        self.point_clicked.emit(idx)