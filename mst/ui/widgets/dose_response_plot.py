from __future__ import annotations

from typing import Iterable, List, Optional, Tuple

from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from PySide6.QtCore import Signal
from PySide6.QtWidgets import QWidget, QVBoxLayout


class DoseResponsePlot(QWidget):
    point_clicked = Signal(int)

    def __init__(self, parent=None, *, enable_zoom: bool = False) -> None:
        super().__init__(parent)
        self._enable_zoom = bool(enable_zoom)
        self._fig = Figure(figsize=(4, 3), tight_layout=True)
        self._canvas = FigureCanvas(self._fig)
        self._ax = self._fig.add_subplot(111)
        self._ax.set_title("Dose Response")
        self._ax.set_xlabel("Concentration")
        self._ax.set_ylabel("Feature @ T1")
        self._ax.grid(True, alpha=0.25)
        self._ax.set_xscale("log")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        if self._enable_zoom:
            from matplotlib.backends.backend_qtagg import NavigationToolbar2QT as NavigationToolbar

            layout.addWidget(NavigationToolbar(self._canvas, self))
        layout.addWidget(self._canvas)

        self._x: List[float] = []
        self._y: List[float] = []

        self._canvas.mpl_connect("button_press_event", self._on_click)

    def set_data(
        self,
        x: Iterable[float],
        y: Iterable[float],
        enabled_mask: Optional[List[bool]] = None,
        selected_idx: Optional[int] = None,
        fit_curve: Optional[Tuple[List[float], List[float], str]] = None,
    ) -> None:
        self._x = list(x)
        self._y = list(y)
        n = min(len(self._x), len(self._y))
        enabled = enabled_mask if enabled_mask is not None else [True] * n

        self._ax.clear()
        self._ax.set_title("Dose Response")
        self._ax.set_xlabel("Concentration")
        self._ax.set_ylabel("Feature @ T1")
        self._ax.grid(True, alpha=0.25)
        self._ax.set_xscale("log")

        xs = self._x[:n]
        ys = self._y[:n]
        for i in range(n):
            if not enabled[i]:
                c = "#c7c7c7"
                a = 0.5
                s = 25
            elif selected_idx is not None and i == selected_idx:
                c = "#2ca02c"
                a = 1.0
                s = 55
            else:
                c = "#1f77b4"
                a = 0.9
                s = 35
            self._ax.scatter([xs[i]], [ys[i]], color=c, alpha=a, s=s, zorder=3)

        if fit_curve is not None:
            xf, yf, text = fit_curve
            self._ax.plot(xf, yf, color="#ff7f0e", lw=2.0, zorder=2)
            self._ax.text(
                0.02,
                0.98,
                text,
                transform=self._ax.transAxes,
                va="top",
                ha="left",
                fontsize=9,
                bbox=dict(boxstyle="round,pad=0.25", fc="white", ec="#dddddd", alpha=0.85),
            )

        self._canvas.draw_idle()

    def _on_click(self, event) -> None:
        if event.inaxes != self._ax or event.xdata is None or event.ydata is None:
            return
        if not self._x or not self._y:
            return
        # 找到最近的散点（在 log-x 空间更合理）
        x = float(event.xdata)
        y = float(event.ydata)
        xs = self._x
        ys = self._y
        # 防止 log(0)
        lx = 0.0
        if x > 0:
            import math

            lx = math.log10(x)
        else:
            return

        best_i = None
        best_d = None
        import math

        for i in range(min(len(xs), len(ys))):
            if xs[i] <= 0:
                continue
            d = (math.log10(xs[i]) - lx) ** 2 + (ys[i] - y) ** 2
            if best_d is None or d < best_d:
                best_d = d
                best_i = i
        if best_i is not None:
            self.point_clicked.emit(int(best_i))

