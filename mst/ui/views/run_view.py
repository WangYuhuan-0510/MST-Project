"""
run_view.py  （Results 页面）
──────────────────────────────
实时运行监控页面（模拟数据）— 沿用原有业务逻辑，套用项目统一风格。
"""
from __future__ import annotations

from collections import deque
from typing import Any, Dict, List, Optional

from PySide6.QtCore import QTimer, Slot
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QLabel,
    QGroupBox,
    QDoubleSpinBox,
    QCheckBox,
    QSizePolicy,
    QDialog,
    QFrame,
    QComboBox,
)

from mst.ui.viewmodels.run_analysis_vm import RunAnalysisViewModel
from mst.ui.widgets import CapillaryScanPlot, MSTTracePlot, DoseResponsePlot

from .ui_style import (
    PALETTE,
    primary_btn_style,
    secondary_btn_style,
    danger_btn_style,
    spinbox_style,
    groupbox_style,
    checkbox_style,
    label_style,
    section_label,
    divider,
)

# ── 串口相关（可选依赖，不影响模拟模式）─────────────────────────────────────
try:
    from mst.device.serial_worker import SerialWorker
    from mst.device.protocol import DataSample, MSTDataSample, N_CHANNELS
    from mst.device.transport import SerialTransport
    _SERIAL_AVAILABLE = True
except ImportError:
    _SERIAL_AVAILABLE = False
    N_CHANNELS = 16
    DataSample = object  # type: ignore[assignment]
    MSTDataSample = object  # type: ignore[assignment]


# ─────────────────────────────────────────────────────────────────────────────
#  串口数据缓冲（仅串口模式使用）
# ─────────────────────────────────────────────────────────────────────────────

class _SerialBuffer:
    """接收并缓存串口采样，提供与 RunAnalysisViewModel 相同接口的数据视图。"""
    MAX_SAMPLES = 3000

    def __init__(self, n_ch: int = N_CHANNELS) -> None:
        self.n_ch         = n_ch
        self.t_s:   deque = deque(maxlen=self.MAX_SAMPLES)  # 兼容旧数据流
        self.traces: List[deque] = [deque(maxlen=self.MAX_SAMPLES) for _ in range(n_ch)]
        self.mst_t_s: deque = deque(maxlen=self.MAX_SAMPLES)
        self.mst_traces: List[deque] = [deque(maxlen=self.MAX_SAMPLES) for _ in range(n_ch)]
        self.enabled_mask: List[bool] = [True] * n_ch
        self._latest: List[float] = [0.0] * n_ch         # 兼容旧数据流
        self._scan_latest: List[float] = [0.0] * n_ch    # 扫描图使用
        self._dist_min: Optional[float] = None
        self._dist_max: Optional[float] = None
        self.frame_count: int = 0
        self.last_t_ms: int = 0
        self.last_dist: float = 0.0
        self.last_fluo: float = 0.0
        self.last_idx: int = -1
        self.last_kind: str = "none"
        self.phase: str = "SCAN"
        self._ir_seen: bool = False
        self._mst_t0_ms: int = 0

    def append(self, sample) -> None:          # sample: DataSample
        # 兼容两种串口样本：
        # 1) DataSample: 一帧包含全通道
        # 2) MSTDataSample: 一帧只包含 distance/fluo 单点
        if isinstance(sample, DataSample):
            t_ms = int(sample.t_ms)
            for i, v in enumerate(sample.channels[:self.n_ch]):
                self._latest[i] = float(v)
            self.last_kind = "multi"
            self.last_idx = -1
        elif _SERIAL_AVAILABLE and isinstance(sample, MSTDataSample):
            t_ms = int(sample.t_ms)
            dist = float(sample.distance)
            self._dist_min = dist if self._dist_min is None else min(self._dist_min, dist)
            self._dist_max = dist if self._dist_max is None else max(self._dist_max, dist)

            # 兼容两类 distance：
            # 1) 已经是索引（0~n_ch-1）；
            # 2) 物理距离（如 mm），按观测范围动态归一化到索引。
            if 0.0 <= dist <= float(self.n_ch - 1):
                idx = int(round(dist))
            elif self._dist_min is not None and self._dist_max is not None and self._dist_max > self._dist_min:
                ratio = (dist - self._dist_min) / (self._dist_max - self._dist_min)
                idx = int(round(ratio * (self.n_ch - 1)))
            else:
                idx = 0
            if 0 <= idx < self.n_ch:
                self._scan_latest[idx] = float(sample.fluo)
                self.last_kind = "mst"
                self.last_idx = idx
                self.last_dist = dist
                self.last_fluo = float(sample.fluo)
                if bool(getattr(sample, "ir_on", False)):
                    self._enter_mst_if_needed(t_ms)
                    self.mst_traces[idx].append(float(sample.fluo))
                    self.mst_t_s.append((t_ms - self._mst_t0_ms) / 1000.0)
                    self.phase = "MST"
                else:
                    self.phase = "SCAN"
        else:
            return

        self.frame_count += 1
        self.last_t_ms = t_ms
        self.t_s.append(t_ms / 1000.0)
        for i in range(self.n_ch):
            self.traces[i].append(self._latest[i])

    def clear(self) -> None:
        self.t_s.clear()
        for d in self.traces:
            d.clear()
        self._latest = [0.0] * self.n_ch
        self._scan_latest = [0.0] * self.n_ch
        self._dist_min = None
        self._dist_max = None
        self.frame_count = 0
        self.last_t_ms = 0
        self.last_dist = 0.0
        self.last_fluo = 0.0
        self.last_idx = -1
        self.last_kind = "none"
        self.phase = "SCAN"
        self._ir_seen = False
        self._mst_t0_ms = 0
        self.mst_t_s.clear()
        for d in self.mst_traces:
            d.clear()

    def _enter_mst_if_needed(self, t_ms: int) -> None:
        if self._ir_seen:
            return
        self._ir_seen = True
        self._mst_t0_ms = int(t_ms)
        self.mst_t_s.clear()
        for d in self.mst_traces:
            d.clear()

    def time_list(self) -> List[float]:
        if self._ir_seen:
            return list(self.mst_t_s)
        return []

    def trace_matrix(self) -> List[List[float]]:
        if self._ir_seen:
            return [list(d) for d in self.mst_traces]
        return [[] for _ in range(self.n_ch)]

    def scan_center(self) -> List[float]:
        if self.last_kind == "mst":
            return list(self._scan_latest)
        return [d[-1] if d else 0.0 for d in self.traces]

    def debug_snapshot(self) -> str:
        dmin = "None" if self._dist_min is None else f"{self._dist_min:.3f}"
        dmax = "None" if self._dist_max is None else f"{self._dist_max:.3f}"
        return (
            f"frames={self.frame_count} | kind={self.last_kind} | "
            f"t_ms={self.last_t_ms} | dist={self.last_dist:.3f} | "
            f"fluo={self.last_fluo:.1f} | idx={self.last_idx} | "
            f"phase={self.phase} | dist_range=[{dmin}, {dmax}]"
        )


# ─────────────────────────────────────────────────────────────────────────────
#  RunView
# ─────────────────────────────────────────────────────────────────────────────

class RunView(QWidget):
    """
    实时运行监控页面（Results）。

    支持两种模式，通过控制栏左侧的切换按钮选择：
      · 模拟模式  — 使用 RunAnalysisViewModel 生成模拟数据（原有逻辑不变）
      · 串口模式  — 通过 SerialWorker 读取 STM32 真实荧光数据

    两种模式共用同一套图表区和 Review 对话框。
    """

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setStyleSheet(f"background: {PALETTE['bg_main']};")

        # ── 模拟模式 ViewModel ────────────────────────────────────────────
        self.vm = RunAnalysisViewModel(self)
        self._sim_timer = QTimer(self)
        self._sim_timer.setInterval(80)
        self._sim_timer.timeout.connect(self._on_tick)

        # ── 串口模式 ─────────────────────────────────────────────────────
        self._serial_worker: Optional["SerialWorker"] = None
        self._serial_buf    = _SerialBuffer()
        self._serial_error_count = 0
        self._serial_last_error = ""
        self._serial_rx_bytes = 0
        self._serial_rx_chunks = 0
        self._serial_ok_frames = 0
        self._serial_bad_frames = 0
        self._serial_last_chunk_hex = "-"
        self._serial_port_echo = "-"
        self._render_timer  = QTimer(self)
        self._render_timer.setInterval(80)
        self._render_timer.timeout.connect(self._render_serial)
        self._sim_paused = False
        self._serial_paused = False

        # 当前模式："sim" | "serial"
        self._mode = "sim"

        plot_box_height = 320
        root = QVBoxLayout(self)
        root.setContentsMargins(20, 20, 20, 20)
        root.setSpacing(16)

        # ── 标题行 ─────────────────────────────────────────────────────────
        root.addWidget(section_label("RESULTS  ·  LIVE RUN"))
        root.addWidget(divider())

        # ── 模式切换行 ────────────────────────────────────────────────────
        mode_bar = QFrame()
        mode_bar.setStyleSheet(
            f"background: {PALETTE['bg_card']};"
            f"border: 1px solid {PALETTE['border']};"
            "border-radius: 8px;"
        )
        mode_lo = QHBoxLayout(mode_bar)
        mode_lo.setContentsMargins(12, 6, 12, 6)
        mode_lo.setSpacing(8)

        mode_lbl = QLabel("数据来源：")
        mode_lbl.setStyleSheet(label_style(12, 500, "text_secondary"))
        mode_lo.addWidget(mode_lbl)

        self.btn_mode_sim = QPushButton("模拟数据")
        self.btn_mode_ser = QPushButton("串口 (STM32)")
        for btn in (self.btn_mode_sim, self.btn_mode_ser):
            btn.setFixedHeight(28)
            btn.setCheckable(True)
            btn.setCursor(__import__("PySide6.QtCore", fromlist=["Qt"]).Qt.PointingHandCursor)
        self.btn_mode_sim.setChecked(True)
        self.btn_mode_sim.clicked.connect(lambda: self._switch_mode("sim"))
        self.btn_mode_ser.clicked.connect(lambda: self._switch_mode("serial"))
        self._apply_mode_btn_style()

        if not _SERIAL_AVAILABLE:
            self.btn_mode_ser.setEnabled(False)
            self.btn_mode_ser.setToolTip("缺少 mst.device 模块，串口模式不可用")

        mode_lo.addWidget(self.btn_mode_sim)
        mode_lo.addWidget(self.btn_mode_ser)
        mode_lo.addStretch()
        root.addWidget(mode_bar)

        # ── 控制栏（模拟模式）─────────────────────────────────────────────
        self._sim_ctrl_card = QFrame()
        self._sim_ctrl_card.setStyleSheet(
            f"background: {PALETTE['bg_card']};"
            f"border: 1px solid {PALETTE['border']};"
            "border-radius: 10px;"
        )
        sim_ctrl = QHBoxLayout(self._sim_ctrl_card)
        sim_ctrl.setContentsMargins(16, 10, 16, 10)
        sim_ctrl.setSpacing(10)

        self.btn_start = QPushButton("▶  开始（模拟）")
        self.btn_start.setFixedHeight(34)
        self.btn_start.setStyleSheet(primary_btn_style())
        self.btn_start.clicked.connect(self.start)
        sim_ctrl.addWidget(self.btn_start)

        self.btn_stop = QPushButton("■  停止")
        self.btn_stop.setFixedHeight(34)
        self.btn_stop.setStyleSheet(danger_btn_style())
        self.btn_stop.clicked.connect(self.stop)
        self.btn_stop.setEnabled(False)
        sim_ctrl.addWidget(self.btn_stop)

        self.btn_pause = QPushButton("⏸  暂停")
        self.btn_pause.setFixedHeight(34)
        self.btn_pause.setStyleSheet(secondary_btn_style())
        self.btn_pause.clicked.connect(self.pause)
        self.btn_pause.setEnabled(False)
        sim_ctrl.addWidget(self.btn_pause)

        self.btn_resume = QPushButton("▶  继续")
        self.btn_resume.setFixedHeight(34)
        self.btn_resume.setStyleSheet(primary_btn_style())
        self.btn_resume.clicked.connect(self.resume)
        self.btn_resume.setEnabled(False)
        sim_ctrl.addWidget(self.btn_resume)

        sim_ctrl.addSpacing(8)
        t1_lbl = QLabel("T1 (s)")
        t1_lbl.setStyleSheet(label_style(12, 500, "text_secondary"))
        sim_ctrl.addWidget(t1_lbl)

        self.spin_t1 = QDoubleSpinBox()
        self.spin_t1.setRange(-5.0, 25.0)
        self.spin_t1.setDecimals(3)
        self.spin_t1.setSingleStep(0.1)
        self.spin_t1.setValue(float(self.vm.t1_s))
        self.spin_t1.setFixedHeight(32)
        self.spin_t1.setStyleSheet(spinbox_style())
        self.spin_t1.valueChanged.connect(lambda v: self.vm.set_t1(float(v)))
        sim_ctrl.addWidget(self.spin_t1)

        sim_ctrl.addSpacing(4)
        self.chk_exclude_selected = QCheckBox("剔除选中毛细管")
        self.chk_exclude_selected.setStyleSheet(checkbox_style())
        self.chk_exclude_selected.stateChanged.connect(self._on_toggle_exclude_selected)
        sim_ctrl.addWidget(self.chk_exclude_selected)

        sim_ctrl.addStretch(1)
        self.lbl_status = QLabel("就绪")
        self.lbl_status.setStyleSheet(label_style(12, 500, "text_muted"))
        sim_ctrl.addWidget(self.lbl_status)

        root.addWidget(self._sim_ctrl_card)

        # ── 控制栏（串口模式）─────────────────────────────────────────────
        self._ser_ctrl_card = QFrame()
        self._ser_ctrl_card.setStyleSheet(
            f"background: {PALETTE['bg_card']};"
            f"border: 1px solid {PALETTE['border']};"
            "border-radius: 10px;"
        )
        self._ser_ctrl_card.setVisible(False)
        ser_ctrl = QHBoxLayout(self._ser_ctrl_card)
        ser_ctrl.setContentsMargins(16, 10, 16, 10)
        ser_ctrl.setSpacing(10)

        port_lbl = QLabel("串口")
        port_lbl.setStyleSheet(label_style(12, 500, "text_secondary"))
        ser_ctrl.addWidget(port_lbl)

        self.cmb_port = QComboBox()
        self.cmb_port.setFixedWidth(100)
        self.cmb_port.setStyleSheet(f"""
            QComboBox {{
                background: {PALETTE['bg_card']};
                border: 1px solid {PALETTE['border']};
                border-radius: 6px;
                color: {PALETTE['text_primary']};
                font-size: 13px;
                padding: 3px 8px;
                min-height: 26px;
            }}
            QComboBox:focus {{ border: 1px solid {PALETTE['border_active']}; }}
            QComboBox::drop-down {{ border: none; width: 20px; }}
            QComboBox QAbstractItemView {{
                background: {PALETTE['bg_card']};
                border: 1px solid {PALETTE['border']};
                color: {PALETTE['text_primary']};
                selection-background-color: {PALETTE['bg_active']};
            }}
        """)
        ser_ctrl.addWidget(self.cmb_port)

        refresh_btn = QPushButton("↻")
        refresh_btn.setFixedSize(28, 28)
        refresh_btn.setStyleSheet(secondary_btn_style())
        refresh_btn.setToolTip("刷新串口列表")
        refresh_btn.clicked.connect(self._refresh_ports)
        ser_ctrl.addWidget(refresh_btn)

        baud_lbl = QLabel("波特率")
        baud_lbl.setStyleSheet(label_style(12, 500, "text_secondary"))
        ser_ctrl.addWidget(baud_lbl)

        self.cmb_baud = QComboBox()
        self.cmb_baud.addItems(["9600", "19200", "38400", "57600", "115200", "230400"])
        self.cmb_baud.setCurrentText("115200")
        self.cmb_baud.setFixedWidth(90)
        self.cmb_baud.setStyleSheet(self.cmb_port.styleSheet())
        ser_ctrl.addWidget(self.cmb_baud)

        self.btn_ser_connect = QPushButton("▶  连接并开始")
        self.btn_ser_connect.setFixedHeight(34)
        self.btn_ser_connect.setStyleSheet(primary_btn_style())
        self.btn_ser_connect.clicked.connect(self._on_serial_connect)
        ser_ctrl.addWidget(self.btn_ser_connect)

        self.btn_ser_stop = QPushButton("■  断开")
        self.btn_ser_stop.setFixedHeight(34)
        self.btn_ser_stop.setStyleSheet(danger_btn_style())
        self.btn_ser_stop.clicked.connect(self._on_serial_stop)
        self.btn_ser_stop.setEnabled(False)
        ser_ctrl.addWidget(self.btn_ser_stop)

        self.btn_ser_pause = QPushButton("⏸  暂停")
        self.btn_ser_pause.setFixedHeight(34)
        self.btn_ser_pause.setStyleSheet(secondary_btn_style())
        self.btn_ser_pause.clicked.connect(self._on_serial_pause)
        self.btn_ser_pause.setEnabled(False)
        ser_ctrl.addWidget(self.btn_ser_pause)

        self.btn_ser_resume = QPushButton("▶  继续")
        self.btn_ser_resume.setFixedHeight(34)
        self.btn_ser_resume.setStyleSheet(primary_btn_style())
        self.btn_ser_resume.clicked.connect(self._on_serial_resume)
        self.btn_ser_resume.setEnabled(False)
        ser_ctrl.addWidget(self.btn_ser_resume)

        ser_ctrl.addSpacing(8)
        t1_lbl2 = QLabel("T1 (s)")
        t1_lbl2.setStyleSheet(label_style(12, 500, "text_secondary"))
        ser_ctrl.addWidget(t1_lbl2)

        self.spin_t1_ser = QDoubleSpinBox()
        self.spin_t1_ser.setRange(-5.0, 60.0)
        self.spin_t1_ser.setDecimals(1)
        self.spin_t1_ser.setSingleStep(0.5)
        self.spin_t1_ser.setValue(5.0)
        self.spin_t1_ser.setFixedHeight(32)
        self.spin_t1_ser.setStyleSheet(spinbox_style())
        ser_ctrl.addWidget(self.spin_t1_ser)

        ser_ctrl.addStretch(1)
        self.lbl_ser_status = QLabel("未连接")
        self.lbl_ser_status.setStyleSheet(label_style(12, 500, "text_muted"))
        ser_ctrl.addWidget(self.lbl_ser_status)

        root.addWidget(self._ser_ctrl_card)
        self.lbl_ser_debug = QLabel("调试：未开始接收串口数据")
        self.lbl_ser_debug.setStyleSheet(label_style(11, 500, "text_muted"))
        self.lbl_ser_debug.setVisible(False)
        root.addWidget(self.lbl_ser_debug)

        # ── 三张图（两种模式共用）────────────────────────────────────────
        _gb = groupbox_style()
        plots = QHBoxLayout()
        plots.setSpacing(12)
        root.addLayout(plots)

        box_scan = QGroupBox("Capillary Scan")
        box_scan.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        box_scan.setFixedHeight(plot_box_height)
        box_scan.setStyleSheet(_gb)
        layout_scan = QVBoxLayout(box_scan)
        layout_scan.setContentsMargins(8, 18, 8, 8)
        self.plot_scan = CapillaryScanPlot(self)
        self.plot_scan.point_clicked.connect(self.vm.set_selected_capillary)
        layout_scan.addWidget(self.plot_scan)
        self.btn_review_scan = QPushButton("Review")
        self.btn_review_scan.setFixedHeight(30)
        self.btn_review_scan.setStyleSheet(secondary_btn_style())
        self.btn_review_scan.clicked.connect(lambda: self._open_review("scan"))
        layout_scan.addWidget(self.btn_review_scan)
        plots.addWidget(box_scan, 1)

        box_trace = QGroupBox("MST Traces（0s 开红外，拖动紫线调 T1）")
        box_trace.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        box_trace.setFixedHeight(plot_box_height)
        box_trace.setStyleSheet(_gb)
        layout_trace = QVBoxLayout(box_trace)
        layout_trace.setContentsMargins(8, 18, 8, 8)
        self.plot_trace = MSTTracePlot(self)
        self.plot_trace.t1_changed.connect(self.vm.set_t1)
        layout_trace.addWidget(self.plot_trace)
        self.btn_review_trace = QPushButton("Review")
        self.btn_review_trace.setFixedHeight(30)
        self.btn_review_trace.setStyleSheet(secondary_btn_style())
        self.btn_review_trace.clicked.connect(lambda: self._open_review("trace"))
        layout_trace.addWidget(self.btn_review_trace)
        plots.addWidget(box_trace, 1)

        box_dose = QGroupBox("Dose Response（点击点：剔除 / 恢复）")
        box_dose.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        box_dose.setFixedHeight(plot_box_height)
        box_dose.setStyleSheet(_gb)
        layout_dose = QVBoxLayout(box_dose)
        layout_dose.setContentsMargins(8, 18, 8, 8)
        self.plot_dose = DoseResponsePlot(self)
        self.plot_dose.point_clicked.connect(self.vm.toggle_enabled)
        layout_dose.addWidget(self.plot_dose)
        self.btn_review_dose = QPushButton("Review")
        self.btn_review_dose.setFixedHeight(30)
        self.btn_review_dose.setStyleSheet(secondary_btn_style())
        self.btn_review_dose.clicked.connect(lambda: self._open_review("dose"))
        layout_dose.addWidget(self.btn_review_dose)
        plots.addWidget(box_dose, 1)
        root.addStretch(1)

        # ── 信号连接（模拟模式）──────────────────────────────────────────
        self.vm.changed.connect(self._render)
        self.vm.selected_capillary_changed.connect(self._sync_selected_ui)
        self.vm.t1_changed.connect(self._sync_t1_ui)

        # ── 初始化串口列表 ────────────────────────────────────────────────
        self._refresh_ports()
        self._render()

    # ── 模式切换 ──────────────────────────────────────────────────────────

    def _switch_mode(self, mode: str) -> None:
        if mode == self._mode:
            return
        # 先停止当前运行
        if self._mode == "sim":
            self.stop()
        else:
            self._on_serial_stop()

        self._mode = mode
        is_serial = (mode == "serial")
        self._sim_ctrl_card.setVisible(not is_serial)
        self._ser_ctrl_card.setVisible(is_serial)
        self.lbl_ser_debug.setVisible(is_serial)
        self.btn_mode_sim.setChecked(not is_serial)
        self.btn_mode_ser.setChecked(is_serial)
        self._apply_mode_btn_style()

    def _apply_mode_btn_style(self) -> None:
        for btn, active in (
            (self.btn_mode_sim, self._mode == "sim"),
            (self.btn_mode_ser, self._mode == "serial"),
        ):
            if active:
                btn.setStyleSheet(f"""
                    QPushButton {{
                        background: {PALETTE['accent_dim']};
                        border: none;
                        border-radius: 6px;
                        color: #FFFFFF;
                        font-size: 12px;
                        font-weight: 600;
                        padding: 0 14px;
                        height: 28px;
                    }}
                """)
            else:
                btn.setStyleSheet(f"""
                    QPushButton {{
                        background: {PALETTE['bg_hover']};
                        border: 1px solid {PALETTE['border']};
                        border-radius: 6px;
                        color: {PALETTE['text_secondary']};
                        font-size: 12px;
                        padding: 0 14px;
                        height: 28px;
                    }}
                    QPushButton:hover {{
                        background: {PALETTE['bg_active']};
                        color: {PALETTE['text_primary']};
                    }}
                """)

    # ── 串口操作 ──────────────────────────────────────────────────────────

    def _refresh_ports(self) -> None:
        if not _SERIAL_AVAILABLE:
            return
        try:
            ports = SerialTransport.list_ports()
        except Exception:
            ports = []
        self.cmb_port.clear()
        self.cmb_port.addItems(ports if ports else ["COM3"])

    def _on_serial_connect(self) -> None:
        if not _SERIAL_AVAILABLE:
            self._set_ser_status("串口模块不可用", "danger")
            return
        port = self.cmb_port.currentText().strip()
        baud = int(self.cmb_baud.currentText())
        self._serial_buf.clear()
        self._serial_error_count = 0
        self._serial_last_error = ""
        self._serial_rx_bytes = 0
        self._serial_rx_chunks = 0
        self._serial_ok_frames = 0
        self._serial_bad_frames = 0
        self._serial_last_chunk_hex = "-"
        self._serial_port_echo = "-"
        self._serial_paused = False
        self._update_serial_debug()

        self._serial_worker = SerialWorker(port=port, baudrate=baud, parent=self)
        self._serial_worker.data_ready.connect(self._on_serial_data)
        self._serial_worker.status_changed.connect(self._set_ser_status_ok)
        self._serial_worker.error_occurred.connect(self._set_ser_status_err)
        self._serial_worker.debug_stats.connect(self._on_serial_debug_stats)
        self._serial_worker.finished.connect(self._on_serial_worker_finished)
        self._serial_worker.start()

        self.btn_ser_connect.setEnabled(False)
        self.btn_ser_stop.setEnabled(True)
        self.btn_ser_pause.setEnabled(True)
        self.btn_ser_resume.setEnabled(False)
        self._render_timer.start()

    def _on_serial_stop(self) -> None:
        self._render_timer.stop()
        if self._serial_worker:
            self._serial_worker.stop()
            self._serial_worker.wait(2000)
            self._serial_worker = None
        self.btn_ser_connect.setEnabled(True)
        self.btn_ser_stop.setEnabled(False)
        self.btn_ser_pause.setEnabled(False)
        self.btn_ser_resume.setEnabled(False)
        self._serial_paused = False
        self._set_ser_status("已断开", "text_muted")
        self._update_serial_debug()

    def _on_serial_worker_finished(self) -> None:
        self._render_timer.stop()
        self.btn_ser_connect.setEnabled(True)
        self.btn_ser_stop.setEnabled(False)
        self.btn_ser_pause.setEnabled(False)
        self.btn_ser_resume.setEnabled(False)
        self._serial_paused = False

    def _on_serial_pause(self) -> None:
        if self._serial_worker is None or self._serial_paused:
            return
        self._serial_paused = True
        self._render_timer.stop()
        self.btn_ser_pause.setEnabled(False)
        self.btn_ser_resume.setEnabled(True)
        self._set_ser_status("串口采集中（已暂停显示）", "warning")

    def _on_serial_resume(self) -> None:
        if self._serial_worker is None or (not self._serial_paused):
            return
        self._serial_paused = False
        self._render_timer.start()
        self.btn_ser_pause.setEnabled(True)
        self.btn_ser_resume.setEnabled(False)
        self._set_ser_status("串口采集中（已继续）", "success")

    # ── 串口数据槽 ────────────────────────────────────────────────────────

    @Slot(object)
    def _on_serial_data(self, sample) -> None:
        self._serial_buf.append(sample)
        self._update_serial_debug()

    @Slot(str)
    def _set_ser_status_ok(self, msg: str) -> None:
        self._set_ser_status(msg, "success")

    @Slot(object)
    def _on_serial_debug_stats(self, stats: object) -> None:
        if not isinstance(stats, dict):
            return
        self._serial_rx_bytes = int(stats.get("rx_bytes", 0))
        self._serial_rx_chunks = int(stats.get("rx_chunks", 0))
        self._serial_ok_frames = int(stats.get("ok_frames", 0))
        self._serial_bad_frames = int(stats.get("bad_frames", 0))
        self._serial_last_chunk_hex = str(stats.get("last_chunk_hex", "-"))
        port = stats.get("port")
        baudrate = stats.get("baudrate")
        bytesize = stats.get("bytesize")
        parity = stats.get("parity")
        stopbits = stats.get("stopbits")
        if port is not None:
            self._serial_port_echo = f"{port}@{baudrate},{bytesize},{parity},{stopbits}"
        self._update_serial_debug()

    @Slot(str)
    def _set_ser_status_err(self, msg: str) -> None:
        self._serial_error_count += 1
        self._serial_last_error = msg
        self._set_ser_status(f"⚠  {msg}", "danger")
        self._update_serial_debug()

    def _set_ser_status(self, text: str, color_key: str = "text_muted") -> None:
        self.lbl_ser_status.setText(text)
        self.lbl_ser_status.setStyleSheet(label_style(12, 500, color_key))

    def _update_serial_debug(self) -> None:
        err = self._serial_last_error if self._serial_last_error else "-"
        self.lbl_ser_debug.setText(
            f"调试：{self._serial_buf.debug_snapshot()} | errors={self._serial_error_count} | "
            f"last_err={err} | rx_bytes={self._serial_rx_bytes} | rx_chunks={self._serial_rx_chunks} | "
            f"ok_frames={self._serial_ok_frames} | bad_frames={self._serial_bad_frames} | "
            f"last_hex={self._serial_last_chunk_hex} | opened={self._serial_port_echo}"
        )

    def _render_serial(self) -> None:
        """串口模式的定时刷新（替代 _on_tick）。"""
        t   = self._serial_buf.time_list()
        mat = self._serial_buf.trace_matrix()
        sc  = self._serial_buf.scan_center()
        mask = self._serial_buf.enabled_mask
        sel  = self.vm.selected_capillary   # 复用 VM 的选中状态
        if self._serial_buf.phase == "SCAN":
            self._set_ser_status("串口采集中：毛细管扫描阶段（IR 关闭）", "warning")
        else:
            self._set_ser_status("串口采集中：MST 阶段（IR 已开启）", "success")

        self.plot_scan.set_scan(sc, enabled_mask=mask, selected_idx=sel)
        if not t:
            self.plot_trace.set_traces(
                [], [[] for _ in range(len(mask))],
                enabled_mask=mask,
                selected_idx=sel,
                t_ir_on_s=0.0,
                t1_s=self.spin_t1_ser.value(),
            )
            self.plot_dose.set_data(
                list(range(len(mask))), [0.0 for _ in range(len(mask))],
                enabled_mask=mask,
                selected_idx=sel,
                fit_curve=None,
            )
            self._update_serial_debug()
            return

        self.plot_trace.set_traces(
            t, mat,
            enabled_mask=mask,
            selected_idx=sel,
            t_ir_on_s=0.0,
            t1_s=self.spin_t1_ser.value(),
        )
        # 剂量响应：用 T1 时刻各通道值
        if len(t) >= 2:
            dt = t[1] - t[0]
            t1_s = self.spin_t1_ser.value()
            if dt > 0:
                t1_idx = max(0, min(int((t1_s - t[0]) / dt), len(t) - 1))
            else:
                t1_idx = 0
            y_t1 = [mat[i][t1_idx] if len(mat[i]) > t1_idx else 0.0
                    for i in range(len(mat))]
            self.plot_dose.set_data(
                list(range(len(mat))), y_t1,
                enabled_mask=mask,
                selected_idx=sel,
                fit_curve=None,
            )
        self._update_serial_debug()

    # ── Private helpers ───────────────────────────────────────────────────

    def _mw(self):
        return self.window()

    def _set_status(self, text: str, color_key: str = "text_muted") -> None:
        self.lbl_status.setText(text)
        self.lbl_status.setStyleSheet(label_style(12, 500, color_key))

    # ── Public slots ──────────────────────────────────────────────────────

    def start(self) -> None:
        self.btn_start.setEnabled(False)
        self.btn_stop.setEnabled(True)
        self.btn_pause.setEnabled(True)
        self.btn_resume.setEnabled(False)
        self._sim_paused = False
        self._set_status("采集中…", "warning")
        self.vm.start_simulation()
        self._sim_timer.start()

    def stop(self) -> None:
        self._sim_timer.stop()
        self.vm.stop()
        self.btn_start.setEnabled(True)
        self.btn_stop.setEnabled(False)
        self.btn_pause.setEnabled(False)
        self.btn_resume.setEnabled(False)
        self._sim_paused = False
        self._set_status("已停止（模拟）。可继续调整 T1 / 剔除点查看联动效果。", "success")

    def pause(self) -> None:
        if (not self.vm.running) or self._sim_paused:
            return
        self._sim_paused = True
        self._sim_timer.stop()
        self.btn_pause.setEnabled(False)
        self.btn_resume.setEnabled(True)
        self._set_status("模拟采集已暂停", "warning")

    def resume(self) -> None:
        if (not self.vm.running) or (not self._sim_paused):
            return
        self._sim_paused = False
        self._sim_timer.start()
        self.btn_pause.setEnabled(True)
        self.btn_resume.setEnabled(False)
        self._set_status("模拟采集中（已继续）", "warning")

    def _on_tick(self) -> None:
        self.vm.tick()
        if not self.vm.running:
            self.stop()
            return
        self._set_status(
            f"采集中… t={self.vm.t[-1]:.2f}s | T1={self.vm.t1_s:.2f}s", "warning"
        )

    def _render(self) -> None:
        self.plot_scan.set_scan(
            self.vm.scan_center,
            enabled_mask=self.vm.enabled_mask,
            selected_idx=self.vm.selected_capillary,
        )
        self.plot_trace.set_traces(
            self.vm.t,
            self.vm.traces,
            enabled_mask=self.vm.enabled_mask,
            selected_idx=self.vm.selected_capillary,
            t_ir_on_s=self.vm.t_ir_on_s,
            t1_s=self.vm.t1_s,
        )
        fit_curve = None
        if self.vm.fit is not None:
            fit_curve = (self.vm.fit.x_fit, self.vm.fit.y_fit, self.vm.fit.text)
        self.plot_dose.set_data(
            self.vm.concentrations,
            self.vm.feature_y,
            enabled_mask=self.vm.enabled_mask,
            selected_idx=self.vm.selected_capillary,
            fit_curve=fit_curve,
        )
        self._sync_selected_ui(self.vm.selected_capillary)

    def _sync_selected_ui(self, idx: int) -> None:
        idx = int(idx)
        enabled = True
        if 0 <= idx < len(self.vm.enabled_mask):
            enabled = bool(self.vm.enabled_mask[idx])
        self.chk_exclude_selected.blockSignals(True)
        self.chk_exclude_selected.setChecked(not enabled)
        self.chk_exclude_selected.blockSignals(False)

    def _sync_t1_ui(self, t1: float) -> None:
        self.spin_t1.blockSignals(True)
        self.spin_t1.setValue(float(t1))
        self.spin_t1.blockSignals(False)

    def _on_toggle_exclude_selected(self) -> None:
        idx = int(self.vm.selected_capillary)
        if idx < 0 or idx >= len(self.vm.enabled_mask):
            return
        should_exclude = bool(self.chk_exclude_selected.isChecked())
        currently_enabled = bool(self.vm.enabled_mask[idx])
        if should_exclude and currently_enabled:
            self.vm.toggle_enabled(idx)
        elif (not should_exclude) and (not currently_enabled):
            self.vm.toggle_enabled(idx)

    def _open_review(self, target: str) -> None:
        serial_snapshot: Optional[Dict[str, Any]] = None
        if self._mode == "serial":
            serial_snapshot = {
                "t": self._serial_buf.time_list(),
                "mat": self._serial_buf.trace_matrix(),
                "sc": self._serial_buf.scan_center(),
                "mask": list(self._serial_buf.enabled_mask),
                "sel": self.vm.selected_capillary,
                "t1": float(self.spin_t1_ser.value()),
            }
        dlg = _ReviewDialog(self, self.vm, target=target, serial_snapshot=serial_snapshot)
        dlg.exec()


# ─────────────────────────────────────────────────────────────────────────────
#  Review dialog  （逻辑不变，样式统一）
# ─────────────────────────────────────────────────────────────────────────────
class _ReviewDialog(QDialog):
    def __init__(
        self,
        parent: QWidget,
        vm: RunAnalysisViewModel,
        *,
        target: str,
        serial_snapshot: Optional[Dict[str, Any]] = None,
    ) -> None:
        super().__init__(parent)
        titles = {
            "scan": "Capillary Scan Review（缩放 / 平移可用）",
            "trace": "MST Traces Review（缩放 / 平移可用）",
            "dose": "Dose Response Review（缩放 / 平移可用）",
        }
        self._target = target if target in titles else "scan"
        self._serial_snapshot = serial_snapshot
        self.setWindowTitle(titles[self._target])
        self.resize(1100, 760)
        self.setStyleSheet(f"background: {PALETTE['bg_main']};")
        self._vm = vm

        root = QVBoxLayout(self)
        root.setContentsMargins(20, 20, 20, 20)
        root.setSpacing(12)

        _gb = groupbox_style()
        self.plot_scan = None
        self.plot_trace = None
        self.plot_dose = None

        if self._target == "scan":
            box = QGroupBox("Capillary Scan")
            box.setStyleSheet(_gb)
            lo = QVBoxLayout(box)
            lo.setContentsMargins(8, 18, 8, 8)
            self.plot_scan = CapillaryScanPlot(self, enable_zoom=True)
            lo.addWidget(self.plot_scan)
            root.addWidget(box, 1)
        elif self._target == "trace":
            box = QGroupBox("MST Traces")
            box.setStyleSheet(_gb)
            lo = QVBoxLayout(box)
            lo.setContentsMargins(8, 18, 8, 8)
            self.plot_trace = MSTTracePlot(self, enable_zoom=True)
            lo.addWidget(self.plot_trace)
            root.addWidget(box, 1)
        else:
            box = QGroupBox("Dose Response")
            box.setStyleSheet(_gb)
            lo = QVBoxLayout(box)
            lo.setContentsMargins(8, 18, 8, 8)
            self.plot_dose = DoseResponsePlot(self, enable_zoom=True)
            lo.addWidget(self.plot_dose)
            root.addWidget(box, 1)

        if self._serial_snapshot is None:
            self._vm.changed.connect(self._render)
        self._render()

    def closeEvent(self, event) -> None:
        if self._serial_snapshot is None:
            try:
                self._vm.changed.disconnect(self._render)
            except Exception:
                pass
        super().closeEvent(event)

    def _render(self) -> None:
        if self._serial_snapshot is None:
            sc = self._vm.scan_center
            mask = self._vm.enabled_mask
            sel = self._vm.selected_capillary
            t = self._vm.t
            mat = self._vm.traces
            t_ir = self._vm.t_ir_on_s
            t1 = self._vm.t1_s
            conc = self._vm.concentrations
            feat = self._vm.feature_y
            fit_curve = None
            if self._vm.fit is not None:
                fit_curve = (self._vm.fit.x_fit, self._vm.fit.y_fit, self._vm.fit.text)
        else:
            sc = self._serial_snapshot["sc"]
            mask = self._serial_snapshot["mask"]
            sel = self._serial_snapshot["sel"]
            t = self._serial_snapshot["t"]
            mat = self._serial_snapshot["mat"]
            t_ir = 0.0
            t1 = self._serial_snapshot["t1"]
            if len(t) >= 2:
                dt = t[1] - t[0]
                if dt > 0:
                    t1_idx = max(0, min(int((t1 - t[0]) / dt), len(t) - 1))
                else:
                    t1_idx = 0
                feat = [mat[i][t1_idx] if len(mat[i]) > t1_idx else 0.0 for i in range(len(mat))]
            else:
                feat = [0.0 for _ in range(len(mat))]
            conc = list(range(len(mat)))
            fit_curve = None

        if self.plot_scan is not None:
            self.plot_scan.set_scan(sc, enabled_mask=mask, selected_idx=sel)
        if self.plot_trace is not None:
            self.plot_trace.set_traces(
                t, mat,
                enabled_mask=mask,
                selected_idx=sel,
                t_ir_on_s=t_ir,
                t1_s=t1,
            )
        if self.plot_dose is not None:
            self.plot_dose.set_data(
                conc,
                feat,
                enabled_mask=mask,
                selected_idx=sel,
                fit_curve=fit_curve,
            )