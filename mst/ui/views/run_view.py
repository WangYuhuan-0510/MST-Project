"""
run_view.py  （Results 页面）
──────────────────────────────
实时运行监控页面（模拟数据）— 沿用原有业务逻辑，套用项目统一风格。
"""
from __future__ import annotations

from collections import deque
from typing import List, Optional

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
    from mst.device.protocol import DataSample, N_CHANNELS
    from mst.device.transport import SerialTransport
    _SERIAL_AVAILABLE = True
except ImportError:
    _SERIAL_AVAILABLE = False
    N_CHANNELS = 16


# ─────────────────────────────────────────────────────────────────────────────
#  串口数据缓冲（仅串口模式使用）
# ─────────────────────────────────────────────────────────────────────────────

class _SerialBuffer:
    """接收并缓存串口采样，提供与 RunAnalysisViewModel 相同接口的数据视图。"""
    MAX_SAMPLES = 3000

    def __init__(self, n_ch: int = N_CHANNELS) -> None:
        self.n_ch         = n_ch
        self.t_s:   deque = deque(maxlen=self.MAX_SAMPLES)
        self.traces: List[deque] = [deque(maxlen=self.MAX_SAMPLES) for _ in range(n_ch)]
        self.enabled_mask: List[bool] = [True] * n_ch

    def append(self, sample) -> None:          # sample: DataSample
        self.t_s.append(sample.t_ms / 1000.0)
        for i, v in enumerate(sample.channels[:self.n_ch]):
            self.traces[i].append(float(v))

    def clear(self) -> None:
        self.t_s.clear()
        for d in self.traces:
            d.clear()

    def time_list(self)   -> List[float]:       return list(self.t_s)
    def trace_matrix(self) -> List[List[float]]: return [list(d) for d in self.traces]
    def scan_center(self) -> List[float]:
        return [d[-1] if d else 0.0 for d in self.traces]


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
        self._render_timer  = QTimer(self)
        self._render_timer.setInterval(80)
        self._render_timer.timeout.connect(self._render_serial)

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
        plots.addWidget(box_dose, 1)

        # ── Review 按钮 ───────────────────────────────────────────────────
        actions = QHBoxLayout()
        actions.addStretch(1)
        self.btn_review = QPushButton("Review")
        self.btn_review.setFixedHeight(34)
        self.btn_review.setStyleSheet(secondary_btn_style())
        self.btn_review.clicked.connect(self._open_review)
        actions.addWidget(self.btn_review)
        actions.addStretch(1)
        root.addLayout(actions)
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

        self._serial_worker = SerialWorker(port=port, baudrate=baud, parent=self)
        self._serial_worker.data_ready.connect(self._on_serial_data)
        self._serial_worker.status_changed.connect(self._set_ser_status_ok)
        self._serial_worker.error_occurred.connect(self._set_ser_status_err)
        self._serial_worker.finished.connect(self._on_serial_worker_finished)
        self._serial_worker.start()

        self.btn_ser_connect.setEnabled(False)
        self.btn_ser_stop.setEnabled(True)
        self._render_timer.start()

    def _on_serial_stop(self) -> None:
        self._render_timer.stop()
        if self._serial_worker:
            self._serial_worker.stop()
            self._serial_worker.wait(2000)
            self._serial_worker = None
        self.btn_ser_connect.setEnabled(True)
        self.btn_ser_stop.setEnabled(False)
        self._set_ser_status("已断开", "text_muted")

    def _on_serial_worker_finished(self) -> None:
        self._render_timer.stop()
        self.btn_ser_connect.setEnabled(True)
        self.btn_ser_stop.setEnabled(False)

    # ── 串口数据槽 ────────────────────────────────────────────────────────

    @Slot(object)
    def _on_serial_data(self, sample) -> None:
        self._serial_buf.append(sample)

    @Slot(str)
    def _set_ser_status_ok(self, msg: str) -> None:
        self._set_ser_status(msg, "success")

    @Slot(str)
    def _set_ser_status_err(self, msg: str) -> None:
        self._set_ser_status(f"⚠  {msg}", "danger")

    def _set_ser_status(self, text: str, color_key: str = "text_muted") -> None:
        self.lbl_ser_status.setText(text)
        self.lbl_ser_status.setStyleSheet(label_style(12, 500, color_key))

    def _render_serial(self) -> None:
        """串口模式的定时刷新（替代 _on_tick）。"""
        t   = self._serial_buf.time_list()
        mat = self._serial_buf.trace_matrix()
        sc  = self._serial_buf.scan_center()
        mask = self._serial_buf.enabled_mask
        sel  = self.vm.selected_capillary   # 复用 VM 的选中状态

        if not t:
            return

        self.plot_scan.set_scan(sc, enabled_mask=mask, selected_idx=sel)
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
        self._set_status("采集中…", "warning")
        self.vm.start_simulation()
        self._sim_timer.start()

    def stop(self) -> None:
        self._sim_timer.stop()
        self.vm.stop()
        self.btn_start.setEnabled(True)
        self.btn_stop.setEnabled(False)
        self._set_status("已停止（模拟）。可继续调整 T1 / 剔除点查看联动效果。", "success")

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

    def _open_review(self) -> None:
        dlg = _ReviewDialog(self, self.vm)
        dlg.exec()


# ─────────────────────────────────────────────────────────────────────────────
#  Review dialog  （逻辑不变，样式统一）
# ─────────────────────────────────────────────────────────────────────────────
class _ReviewDialog(QDialog):
    def __init__(self, parent: QWidget, vm: RunAnalysisViewModel) -> None:
        super().__init__(parent)
        self.setWindowTitle("Review（缩放 / 平移可用）")
        self.resize(1400, 900)
        self.setStyleSheet(f"background: {PALETTE['bg_main']};")
        self._vm = vm

        root = QVBoxLayout(self)
        root.setContentsMargins(20, 20, 20, 20)
        root.setSpacing(12)

        _gb = groupbox_style()
        plots = QHBoxLayout()
        plots.setSpacing(12)
        root.addLayout(plots, 1)

        box_scan = QGroupBox("Capillary Scan")
        box_scan.setStyleSheet(_gb)
        layout_scan = QVBoxLayout(box_scan)
        layout_scan.setContentsMargins(8, 18, 8, 8)
        self.plot_scan = CapillaryScanPlot(self, enable_zoom=True)
        layout_scan.addWidget(self.plot_scan)
        plots.addWidget(box_scan, 1)

        box_trace = QGroupBox("MST Traces")
        box_trace.setStyleSheet(_gb)
        layout_trace = QVBoxLayout(box_trace)
        layout_trace.setContentsMargins(8, 18, 8, 8)
        self.plot_trace = MSTTracePlot(self, enable_zoom=True)
        layout_trace.addWidget(self.plot_trace)
        plots.addWidget(box_trace, 1)

        box_dose = QGroupBox("Dose Response")
        box_dose.setStyleSheet(_gb)
        layout_dose = QVBoxLayout(box_dose)
        layout_dose.setContentsMargins(8, 18, 8, 8)
        self.plot_dose = DoseResponsePlot(self, enable_zoom=True)
        layout_dose.addWidget(self.plot_dose)
        plots.addWidget(box_dose, 1)

        self._vm.changed.connect(self._render)
        self._render()

    def closeEvent(self, event) -> None:
        try:
            self._vm.changed.disconnect(self._render)
        except Exception:
            pass
        super().closeEvent(event)

    def _render(self) -> None:
        self.plot_scan.set_scan(
            self._vm.scan_center,
            enabled_mask=self._vm.enabled_mask,
            selected_idx=self._vm.selected_capillary,
        )
        self.plot_trace.set_traces(
            self._vm.t,
            self._vm.traces,
            enabled_mask=self._vm.enabled_mask,
            selected_idx=self._vm.selected_capillary,
            t_ir_on_s=self._vm.t_ir_on_s,
            t1_s=self._vm.t1_s,
        )
        fit_curve = None
        if self._vm.fit is not None:
            fit_curve = (self._vm.fit.x_fit, self._vm.fit.y_fit, self._vm.fit.text)
        self.plot_dose.set_data(
            self._vm.concentrations,
            self._vm.feature_y,
            enabled_mask=self._vm.enabled_mask,
            selected_idx=self._vm.selected_capillary,
            fit_curve=fit_curve,
        )