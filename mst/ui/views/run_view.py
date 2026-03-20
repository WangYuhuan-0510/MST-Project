"""
run_view.py  （Results 页面）
──────────────────────────────
实时运行监控页面（模拟数据）— 沿用原有业务逻辑，套用项目统一风格。
"""
from __future__ import annotations

from PySide6.QtCore import QTimer
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


class RunView(QWidget):
    """
    实时运行监控页面（Results）。
    原有业务逻辑保持不变，应用项目统一视觉风格。
    """

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setStyleSheet(f"background: {PALETTE['bg_main']};")

        self.vm = RunAnalysisViewModel(self)
        plot_box_height = 320
        self._timer = QTimer(self)
        self._timer.setInterval(80)
        self._timer.timeout.connect(self._on_tick)

        root = QVBoxLayout(self)
        root.setContentsMargins(20, 20, 20, 20)
        root.setSpacing(16)

        # ── 标题行 ─────────────────────────────────────────────────────────
        root.addWidget(section_label("RESULTS  ·  LIVE RUN"))
        root.addWidget(divider())

        # ── 1 控制栏 ───────────────────────────────────────────────────────
        ctrl_card = QFrame()
        ctrl_card.setStyleSheet(
            f"background: {PALETTE['bg_card']};"
            f"border: 1px solid {PALETTE['border']};"
            "border-radius: 10px;"
        )
        controls = QHBoxLayout(ctrl_card)
        controls.setContentsMargins(16, 10, 16, 10)
        controls.setSpacing(10)

        self.btn_start = QPushButton("▶  开始（模拟）")
        self.btn_start.setFixedHeight(34)
        self.btn_start.setStyleSheet(primary_btn_style())
        self.btn_start.clicked.connect(self.start)
        controls.addWidget(self.btn_start)

        self.btn_stop = QPushButton("■  停止")
        self.btn_stop.setFixedHeight(34)
        self.btn_stop.setStyleSheet(danger_btn_style())
        self.btn_stop.clicked.connect(self.stop)
        self.btn_stop.setEnabled(False)
        controls.addWidget(self.btn_stop)

        controls.addSpacing(8)

        t1_lbl = QLabel("T1 (s)")
        t1_lbl.setStyleSheet(label_style(12, 500, "text_secondary"))
        controls.addWidget(t1_lbl)

        self.spin_t1 = QDoubleSpinBox()
        self.spin_t1.setRange(-5.0, 25.0)
        self.spin_t1.setDecimals(3)
        self.spin_t1.setSingleStep(0.1)
        self.spin_t1.setValue(float(self.vm.t1_s))
        self.spin_t1.setFixedHeight(32)
        self.spin_t1.setStyleSheet(spinbox_style())
        self.spin_t1.valueChanged.connect(lambda v: self.vm.set_t1(float(v)))
        controls.addWidget(self.spin_t1)

        controls.addSpacing(4)

        self.chk_exclude_selected = QCheckBox("剔除选中毛细管")
        self.chk_exclude_selected.setStyleSheet(checkbox_style())
        self.chk_exclude_selected.stateChanged.connect(self._on_toggle_exclude_selected)
        controls.addWidget(self.chk_exclude_selected)

        controls.addStretch(1)

        self.lbl_status = QLabel("就绪")
        self.lbl_status.setStyleSheet(label_style(12, 500, "text_muted"))
        controls.addWidget(self.lbl_status)

        root.addWidget(ctrl_card)

        # ── 2 三张图 ──────────────────────────────────────────────────────
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

        # ── 3 Review 按钮 ─────────────────────────────────────────────────
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

        # ── 信号连接 ──────────────────────────────────────────────────────
        self.vm.changed.connect(self._render)
        self.vm.selected_capillary_changed.connect(self._sync_selected_ui)
        self.vm.t1_changed.connect(self._sync_t1_ui)

        self._render()

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
        self._timer.start()

    def stop(self) -> None:
        self._timer.stop()
        self.vm.stop()
        self.btn_start.setEnabled(True)
        self.btn_stop.setEnabled(False)
        self._set_status("已停止（模拟）。可继续调整 T1 / 剔除点查看联动效果。", "success")

    # ── Private slots ─────────────────────────────────────────────────────

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