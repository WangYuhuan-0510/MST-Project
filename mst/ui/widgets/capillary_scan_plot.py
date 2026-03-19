from __future__ import annotations

from typing import Iterable, List, Optional

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
        self._ax.set_title("Capillary Scan")
        self._ax.set_xlabel("Capillary")
        self._ax.set_ylabel("F(center)")
        self._ax.grid(True, alpha=0.25)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        if self._enable_zoom:
            from matplotlib.backends.backend_qtagg import NavigationToolbar2QT as NavigationToolbar

            layout.addWidget(NavigationToolbar(self._canvas, self))
        layout.addWidget(self._canvas)

        self._bars = None
        self._selected_idx: Optional[int] = None

        self._canvas.mpl_connect("button_press_event", self._on_click)

    def set_scan(
        self,
        y_center: Iterable[float],
        enabled_mask: Optional[List[bool]] = None,
        selected_idx: Optional[int] = None,
    ) -> None:
        ys = list(y_center)
        n = len(ys)
        enabled = enabled_mask if enabled_mask is not None else [True] * n
        self._selected_idx = selected_idx

        self._ax.clear()
        self._ax.set_title("Capillary Scan")
        self._ax.set_xlabel("Capillary")
        self._ax.set_ylabel("F(center)")
        self._ax.grid(True, alpha=0.25)

        # 横坐标显示为 1..n（更贴近实验毛细管编号）
        xs = list(range(1, n + 1))
        colors = []
        for i in range(n):
            if not enabled[i]:
                colors.append("#c7c7c7")
            elif selected_idx is not None and i == selected_idx:
                colors.append("#2ca02c")
            else:
                colors.append("#1f77b4")

        self._bars = self._ax.bar(xs, ys, color=colors, width=0.8)
        self._ax.set_xlim(0.4, n + 0.6)
        self._ax.set_xticks(xs)
        self._canvas.draw_idle()

    def _on_click(self, event) -> None:
        if event.inaxes != self._ax or event.xdata is None:
            return
        cap_no = int(round(float(event.xdata)))
        idx = cap_no - 1
        if idx < 0:
            return
        self.point_clicked.emit(idx)

