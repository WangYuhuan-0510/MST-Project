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
)

from mst.ui.viewmodels.run_analysis_vm import RunAnalysisViewModel
from mst.ui.widgets import CapillaryScanPlot, MSTTracePlot, DoseResponsePlot


class RunView(QWidget):
    """
    实时运行监控页面（模拟数据）。
    """

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.vm = RunAnalysisViewModel(self)
        plot_box_height = 320  # 三张图整体高度：约为原来的一半（可按需微调）
        self._timer = QTimer(self)
        self._timer.setInterval(80)  # ms
        self._timer.timeout.connect(self._on_tick)

        root = QVBoxLayout(self)

        controls = QHBoxLayout()
        root.addLayout(controls)

        self.btn_start = QPushButton("开始（模拟）", self)
        self.btn_start.clicked.connect(self.start)
        controls.addWidget(self.btn_start)

        self.btn_stop = QPushButton("停止", self)
        self.btn_stop.clicked.connect(self.stop)
        self.btn_stop.setEnabled(False)
        controls.addWidget(self.btn_stop)

        controls.addSpacing(12)

        controls.addWidget(QLabel("T1 (s)", self))
        self.spin_t1 = QDoubleSpinBox(self)
        self.spin_t1.setRange(-5.0, 25.0)
        self.spin_t1.setDecimals(3)
        self.spin_t1.setSingleStep(0.1)
        self.spin_t1.setValue(float(self.vm.t1_s))
        self.spin_t1.valueChanged.connect(lambda v: self.vm.set_t1(float(v)))
        controls.addWidget(self.spin_t1)

        self.chk_exclude_selected = QCheckBox("剔除选中毛细管", self)
        self.chk_exclude_selected.stateChanged.connect(self._on_toggle_exclude_selected)
        controls.addWidget(self.chk_exclude_selected)

        controls.addStretch(1)

        self.lbl_status = QLabel("就绪", self)
        controls.addWidget(self.lbl_status)

        plots = QHBoxLayout()
        root.addLayout(plots, 1)

        box_scan = QGroupBox("Capillary Scan", self)
        box_scan.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        box_scan.setFixedHeight(plot_box_height)
        layout_scan = QVBoxLayout(box_scan)
        self.plot_scan = CapillaryScanPlot(self)
        self.plot_scan.point_clicked.connect(self.vm.set_selected_capillary)
        layout_scan.addWidget(self.plot_scan)
        plots.addWidget(box_scan, 1)

        box_trace = QGroupBox("MST Traces（0s 开红外，拖动紫线调 T1）", self)
        box_trace.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        box_trace.setFixedHeight(plot_box_height)
        layout_trace = QVBoxLayout(box_trace)
        self.plot_trace = MSTTracePlot(self)
        self.plot_trace.t1_changed.connect(self.vm.set_t1)
        layout_trace.addWidget(self.plot_trace)
        plots.addWidget(box_trace, 1)

        box_dose = QGroupBox("Dose Response（点击点：剔除/恢复）", self)
        box_dose.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        box_dose.setFixedHeight(plot_box_height)
        layout_dose = QVBoxLayout(box_dose)
        self.plot_dose = DoseResponsePlot(self)
        self.plot_dose.point_clicked.connect(self.vm.toggle_enabled)
        layout_dose.addWidget(self.plot_dose)
        plots.addWidget(box_dose, 1)

        self.vm.changed.connect(self._render)
        self.vm.selected_capillary_changed.connect(self._sync_selected_ui)
        self.vm.t1_changed.connect(self._sync_t1_ui)
        self._render()

        actions_bottom = QHBoxLayout()
        root.addLayout(actions_bottom)
        actions_bottom.addStretch(1)
        self.btn_review = QPushButton("Review", self)
        self.btn_review.clicked.connect(self._open_review)
        actions_bottom.addWidget(self.btn_review)

    def _mw(self):
        return self.window()

    def start(self) -> None:
        self.btn_start.setEnabled(False)
        self.btn_stop.setEnabled(True)
        self.lbl_status.setText("采集中…")
        self.vm.start_simulation()
        self._timer.start()

    def stop(self) -> None:
        self._timer.stop()
        self.vm.stop()
        self.btn_start.setEnabled(True)
        self.btn_stop.setEnabled(False)
        self.lbl_status.setText("已停止（模拟）。你可以继续调整 T1/剔除点查看联动效果。")

    def _on_tick(self) -> None:
        self.vm.tick()
        if not self.vm.running:
            self.stop()
            return
        self.lbl_status.setText(f"采集中… t={self.vm.t[-1]:.2f}s | T1={self.vm.t1_s:.2f}s")

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


class _ReviewDialog(QDialog):
    def __init__(self, parent: QWidget, vm: RunAnalysisViewModel) -> None:
        super().__init__(parent)
        self.setWindowTitle("Review（缩放/平移可用）")
        self.resize(1400, 900)
        self._vm = vm

        root = QVBoxLayout(self)
        plots = QHBoxLayout()
        root.addLayout(plots, 1)

        box_scan = QGroupBox("Capillary Scan", self)
        layout_scan = QVBoxLayout(box_scan)
        self.plot_scan = CapillaryScanPlot(self, enable_zoom=True)
        layout_scan.addWidget(self.plot_scan)
        plots.addWidget(box_scan, 1)

        box_trace = QGroupBox("MST Traces", self)
        layout_trace = QVBoxLayout(box_trace)
        self.plot_trace = MSTTracePlot(self, enable_zoom=True)
        layout_trace.addWidget(self.plot_trace)
        plots.addWidget(box_trace, 1)

        box_dose = QGroupBox("Dose Response", self)
        layout_dose = QVBoxLayout(box_dose)
        self.plot_dose = DoseResponsePlot(self, enable_zoom=True)
        layout_dose.addWidget(self.plot_dose)
        plots.addWidget(box_dose, 1)

        # 放大视图仅用于查看与缩放，不在对话框里修改状态；跟随主界面刷新
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

