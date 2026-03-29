from __future__ import annotations

from typing import Iterable, List, Optional, Sequence

import numpy as np
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from PySide6.QtCore import Signal
from PySide6.QtWidgets import QWidget, QVBoxLayout


class MSTTracePlot(QWidget):
    t1_changed = Signal(float)

    def __init__(self, parent=None, *, enable_zoom: bool = False) -> None:
        super().__init__(parent)
        self._enable_zoom = bool(enable_zoom)
        self._fig = Figure(figsize=(4, 3), tight_layout=True)
        self._canvas = FigureCanvas(self._fig)
        self._toolbar = None
        self._ax = self._fig.add_subplot(111)
        self._ax.set_title("MST Traces")
        self._ax.set_xlabel("t (s)")
        self._ax.set_ylabel("F(t)")
        self._ax.grid(True, alpha=0.25)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        if self._enable_zoom:
            from matplotlib.backends.backend_qtagg import NavigationToolbar2QT as NavigationToolbar

            self._toolbar = NavigationToolbar(self._canvas, self)
            layout.addWidget(self._toolbar)
        layout.addWidget(self._canvas)

        self._t1_line = None
        self._dragging_t1 = False
        self._t1 = 2.0
        self._xlim = (-5.0, 25.0)

        self._canvas.mpl_connect("button_press_event", self._on_press)
        self._canvas.mpl_connect("button_release_event", self._on_release)
        self._canvas.mpl_connect("motion_notify_event", self._on_motion)

    def set_traces(
        self,
        t: Iterable[float],
        traces: List[List[float]],
        enabled_mask: Optional[List[bool]] = None,
        selected_idx: Optional[int] = None,
        t_ir_on_s: float = 0.0,
        t1_s: float = 2.0,
        t_per_trace: Optional[Sequence[Sequence[float]]] = None,
    ) -> None:
        ts = list(t)
        n = len(traces)
        enabled = enabled_mask if enabled_mask is not None else [True] * n
        self._t1 = float(t1_s)

        self._ax.clear()
        self._ax.set_title("MST Traces")
        self._ax.set_xlabel("t (s)")
        self._ax.set_ylabel("F(t)")
        self._ax.grid(True, alpha=0.25)

        # 固定横坐标范围 -5..25，并每 5s 一个刻度
        self._ax.set_xlim(self._xlim[0], self._xlim[1])
        self._ax.set_xticks(np.arange(self._xlim[0], self._xlim[1] + 0.1, 5.0))

        for i in range(n):
            ys = traces[i]
            if not ys:
                continue
            if not enabled[i]:
                color = "#c7c7c7"
                alpha = 0.5
                lw = 0.8
            elif selected_idx is not None and i == selected_idx:
                color = "#2ca02c"
                alpha = 1.0
                lw = 2.0
            else:
                color = "#1f77b4"
                alpha = 0.35
                lw = 1.0
            if t_per_trace is not None and i < len(t_per_trace):
                t_i = list(t_per_trace[i])
                if t_i:
                    self._ax.plot(t_i[: len(ys)], ys, color=color, alpha=alpha, lw=lw)
                    continue
            self._ax.plot(ts[: len(ys)], ys, color=color, alpha=alpha, lw=lw)

        self._ax.axvline(float(t_ir_on_s), color="#d62728", lw=1.2, ls="--")
        self._t1_line = self._ax.axvline(self._t1, color="#9467bd", lw=1.6)

        self._canvas.draw_idle()

    def _near_t1(self, x: float) -> bool:
        if self._t1_line is None:
            return False
        # 以坐标轴宽度的 2% 为吸附范围
        x0, x1 = self._ax.get_xlim()
        tol = 0.02 * max(1e-9, (x1 - x0))
        return abs(x - self._t1) <= tol

    def _on_press(self, event) -> None:
        if event.inaxes != self._ax or event.xdata is None:
            return
        x = float(event.xdata)
        if self._near_t1(x):
            self._dragging_t1 = True

    def _on_release(self, event) -> None:
        if not self._dragging_t1:
            return
        self._dragging_t1 = False
        self.t1_changed.emit(float(self._t1))

    def _on_motion(self, event) -> None:
        if not self._dragging_t1:
            return
        if event.inaxes != self._ax or event.xdata is None:
            return
        self._t1 = float(event.xdata)
        if self._t1_line is not None:
            self._t1_line.set_xdata([self._t1, self._t1])
        self._canvas.draw_idle()

