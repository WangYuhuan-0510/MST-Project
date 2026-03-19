from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Optional

from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from PySide6.QtWidgets import QWidget, QVBoxLayout


@dataclass
class PlotStyle:
    title: str = ""
    x_label: str = "x"
    y_label: str = "y"


class PlotWidget(QWidget):
    """
    基于 matplotlib 的轻量曲线控件（先模拟跑通用）。
    """

    def __init__(self, parent=None, style: Optional[PlotStyle] = None) -> None:
        super().__init__(parent)
        self._style = style or PlotStyle()

        self._fig = Figure(figsize=(5, 3), tight_layout=True)
        self._canvas = FigureCanvas(self._fig)
        self._ax = self._fig.add_subplot(111)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._canvas)

        self._apply_style()
        (self._line,) = self._ax.plot([], [], lw=1.5)

    def _apply_style(self) -> None:
        self._ax.set_title(self._style.title)
        self._ax.set_xlabel(self._style.x_label)
        self._ax.set_ylabel(self._style.y_label)
        self._ax.grid(True, alpha=0.25)

    def set_data(self, x: Iterable[float], y: Iterable[float]) -> None:
        xs = list(x)
        ys = list(y)
        self._line.set_data(xs, ys)
        self._ax.relim()
        self._ax.autoscale_view()
        self._canvas.draw_idle()

    def clear(self) -> None:
        self.set_data([], [])

