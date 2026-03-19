from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QLabel,
    QMessageBox,
)

from mst.core.fitting import fit_binding_curve
from mst.reporting.export_csv import export_xy_csv
from mst.reporting.export_pdf import export_simple_report
from mst.ui.widgets.plot_widget import PlotStyle, PlotWidget


class AnalysisView(QWidget):
    """
    数据分析与结果展示页面（读取最后一次模拟数据）。
    """

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        root = QVBoxLayout(self)

        actions = QHBoxLayout()
        root.addLayout(actions)

        self.btn_refresh = QPushButton("刷新数据", self)
        self.btn_refresh.clicked.connect(self.refresh)
        actions.addWidget(self.btn_refresh)

        self.btn_fit = QPushButton("拟合 Kd", self)
        self.btn_fit.clicked.connect(self.fit)
        actions.addWidget(self.btn_fit)

        self.btn_export_csv = QPushButton("导出 CSV", self)
        self.btn_export_csv.clicked.connect(self.export_csv)
        actions.addWidget(self.btn_export_csv)

        self.btn_export_pdf = QPushButton("导出 PDF", self)
        self.btn_export_pdf.clicked.connect(self.export_pdf)
        actions.addWidget(self.btn_export_pdf)

        actions.addStretch(1)

        self.lbl_info = QLabel("暂无数据。请先到“运行”页面开始（模拟）", self)
        root.addWidget(self.lbl_info)

        self.plot = PlotWidget(self, style=PlotStyle(title="", x_label="x (浓度)", y_label="y (响应)"))
        root.addWidget(self.plot, 1)

        self.refresh()

    def _mw(self):
        return self.window()

    def _get_xy(self):
        mw = self._mw()
        state = getattr(mw, "state", None)
        if state is None:
            return None, None, None
        x = state.last_run.x
        y = state.last_run.y
        return state, x, y

    def refresh(self) -> None:
        state, x, y = self._get_xy()
        if state is None or not x or not y:
            self.lbl_info.setText("暂无数据。请先到“运行”页面开始（模拟）")
            self.plot.clear()
            return
        self.plot.set_data(x, y)

        extra = ""
        if state.last_run.fit_kd is not None:
            extra = f" | 拟合：Kd={state.last_run.fit_kd:.6g}, R²={state.last_run.fit_r_squared:.4f}"
        self.lbl_info.setText(f"数据点：{len(x)}{extra}")

    def fit(self) -> None:
        state, x, y = self._get_xy()
        if state is None or not x or not y:
            QMessageBox.information(self, "提示", "没有可拟合的数据，请先运行一次模拟采集。")
            return
        try:
            res = fit_binding_curve(x, y)
        except Exception as e:
            QMessageBox.critical(self, "拟合失败", str(e))
            return
        state.last_run.fit_kd = float(res.kd)
        state.last_run.fit_r_squared = float(res.r_squared)
        self.refresh()

    def export_csv(self) -> None:
        state, x, y = self._get_xy()
        if state is None or not x or not y:
            QMessageBox.information(self, "提示", "没有可导出的数据。")
            return
        out = Path(state.workspace_dir) / "exports" / "last_run.csv"
        export_xy_csv(out, zip(x, y))
        QMessageBox.information(self, "已导出", f"CSV 已导出到：\n{out}")

    def export_pdf(self) -> None:
        state, x, y = self._get_xy()
        if state is None or not x or not y:
            QMessageBox.information(self, "提示", "没有可导出的数据。")
            return
        out = Path(state.workspace_dir) / "exports" / "report.pdf"
        kv = [("Points", str(len(x)))]
        if state.last_run.fit_kd is not None:
            kv.append(("Kd", f"{state.last_run.fit_kd:.6g}"))
            kv.append(("R²", f"{state.last_run.fit_r_squared:.4f}"))
        export_simple_report(out, title="MST 模拟报告", kv=kv)
        QMessageBox.information(self, "已导出", f"PDF 已导出到：\n{out}")

