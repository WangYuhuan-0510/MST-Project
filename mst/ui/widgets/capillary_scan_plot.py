from __future__ import annotations

from typing import Iterable, List, Optional
import numpy as np

from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from PySide6.QtCore import Signal, Slot
from PySide6.QtWidgets import QWidget, QVBoxLayout

from mst.device.protocol import MSTDataSample

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
        
        # --- 核心改动 1: 初始化数据状态 ---
        self._n_caps: int = 16  # 默认 16 根毛细管
        self._y_data: List[float] = [0.0] * self._n_caps # 初始强度全为 0
        
        # 控制峰的形状
        self._sigma = 0.15      # 峰宽
        self._offset_step = 1.0 # 每个capillary间距

        self._canvas.mpl_connect("button_press_event", self._on_click)
        
        # 初始化显示空图表
        self._init_plot()

    def _init_plot(self) -> None:
        """初始化绘图参数"""
        self._ax.set_title("Capillary Scan (Gaussian Peaks)")
        self._ax.set_xlabel("Scan Position")
        self._ax.set_ylabel("Signal Intensity")
        self._ax.set_ylim(0, 120) # 固定 Y 轴范围
        self._ax.grid(True, alpha=0.25)

    # --- 核心改动 2: 处理 SerialWorker 发来的信号 ---
    @Slot(object)
    def handle_sample(self, sample: MSTDataSample) -> None:
        """
        处理单点数据更新。
        SerialWorker.data_ready 应该连接到这个 Slot。
        """
        # 1. 提取数据
        dist = sample.distance
        fluo = sample.fluo
        
        # 2. 映射逻辑：将 distance 映射到毛细管索引 (0-15)
        # 假设 STM32 发送的 distance 就是 index (0, 1, 2...) 
        # 或者通过 round(dist / offset_step) 计算
        idx = int(round(dist / self._offset_step))
        
        if 0 <= idx < self._n_caps:
            # 更新该位置的最新强度值
            self._y_data[idx] = fluo
            
            # 3. 触发重绘（调用现有的 set_scan 逻辑）
            # 为了性能，可以考虑只在所有点更新完后再重绘，或者降低重绘频率
            self.set_scan(self._y_data, selected_idx=self._selected_idx)

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
        self._y_data = ys # 同步内部数据

        self._ax.clear()
        self._init_plot()

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

        # 绘制中心点标记
        for i in range(n):
            x0 = i * self._offset_step
            y0 = ys[i]
            size = 60 if (selected_idx is not None and i == selected_idx) else 30
            self._ax.scatter(x0, y0, color="white", edgecolors="black", s=size, zorder=3)

        self._canvas.draw_idle()

    def _on_click(self, event) -> None:
        if event.inaxes != self._ax or event.xdata is None:
            return
        clicked_x = float(event.xdata)
        idx = int(round(clicked_x / self._offset_step))
        if 0 <= idx < self._n_caps:
            self.point_clicked.emit(idx)