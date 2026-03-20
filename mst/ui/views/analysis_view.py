"""
analysis_view.py  （Details 页面）
────────────────────────────────────
数据分析与结果展示页面 — 沿用原有业务逻辑，套用项目统一风格。
"""
from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QLabel,
    QMessageBox,
    QFrame,
    QScrollArea,
)
from PySide6.QtCore import Qt

from mst.core.fitting import fit_binding_curve
from mst.reporting.export_csv import export_xy_csv
from mst.reporting.export_pdf import export_simple_report
from mst.ui.widgets.plot_widget import PlotStyle, PlotWidget

from .ui_style import (
    PALETTE,
    primary_btn_style,
    secondary_btn_style,
    card_style,
    label_style,
    section_label,
    divider,
)


class AnalysisView(QScrollArea):
    """
    数据分析与结果展示页面（Details）。
    原有业务逻辑保持不变，应用项目统一视觉风格。
    """

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setFrameShape(QFrame.NoFrame)
        self.setWidgetResizable(True)
        self.setStyleSheet(f"background: {PALETTE['bg_main']};")

        inner = QWidget()
        inner.setStyleSheet(f"background: {PALETTE['bg_main']};")
        self.setWidget(inner)

        root = QVBoxLayout(inner)
        root.setContentsMargins(28, 28, 28, 28)
        root.setSpacing(16)

        # ── 标题区 ─────────────────────────────────────────────────────────
        root.addWidget(section_label("DETAILS  ·  ANALYSIS"))

        title_lbl = QLabel("数据分析与结果")
        title_lbl.setStyleSheet(
            f"color: {PALETTE['text_primary']};"
            "font-size: 20px;"
            "font-weight: 700;"
            "letter-spacing: -0.3px;"
        )
        root.addWidget(title_lbl)
        root.addWidget(divider())

        # ── 操作栏 ─────────────────────────────────────────────────────────
        actions_card = QFrame()
        actions_card.setStyleSheet(card_style(10))
        actions_row = QHBoxLayout(actions_card)
        actions_row.setContentsMargins(16, 12, 16, 12)
        actions_row.setSpacing(10)

        self.btn_refresh = QPushButton("↺  刷新数据")
        self.btn_refresh.setFixedHeight(34)
        self.btn_refresh.setStyleSheet(secondary_btn_style())
        self.btn_refresh.clicked.connect(self.refresh)
        actions_row.addWidget(self.btn_refresh)

        self.btn_fit = QPushButton("⌖  拟合 Kd")
        self.btn_fit.setFixedHeight(34)
        self.btn_fit.setStyleSheet(primary_btn_style())
        self.btn_fit.clicked.connect(self.fit)
        actions_row.addWidget(self.btn_fit)

        self.btn_export_csv = QPushButton("↓  导出 CSV")
        self.btn_export_csv.setFixedHeight(34)
        self.btn_export_csv.setStyleSheet(secondary_btn_style())
        self.btn_export_csv.clicked.connect(self.export_csv)
        actions_row.addWidget(self.btn_export_csv)

        self.btn_export_pdf = QPushButton("↓  导出 PDF")
        self.btn_export_pdf.setFixedHeight(34)
        self.btn_export_pdf.setStyleSheet(secondary_btn_style())
        self.btn_export_pdf.clicked.connect(self.export_pdf)
        actions_row.addWidget(self.btn_export_pdf)

        actions_row.addStretch(1)
        root.addWidget(actions_card)

        # ── 状态信息标签 ────────────────────────────────────────────────────
        info_card = QFrame()
        info_card.setStyleSheet(card_style(8))
        info_layout = QHBoxLayout(info_card)
        info_layout.setContentsMargins(16, 10, 16, 10)

        self.lbl_info = QLabel('暂无数据。请先到"运行"页面开始（模拟）')
        self.lbl_info.setStyleSheet(label_style(13, 400, "text_secondary"))
        info_layout.addWidget(self.lbl_info)
        root.addWidget(info_card)

        # ── 图表区 ─────────────────────────────────────────────────────────
        plot_card = QFrame()
        plot_card.setStyleSheet(card_style(10))
        plot_layout = QVBoxLayout(plot_card)
        plot_layout.setContentsMargins(12, 12, 12, 12)

        self.plot = PlotWidget(
            inner,
            style=PlotStyle(title="", x_label="x (浓度)", y_label="y (响应)"),
        )
        plot_layout.addWidget(self.plot)
        root.addWidget(plot_card, 1)

        self.refresh()

    # ── Private helpers ───────────────────────────────────────────────────

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

    def _set_info(self, text: str, color_key: str = "text_secondary") -> None:
        self.lbl_info.setText(text)
        self.lbl_info.setStyleSheet(label_style(13, 400, color_key))

    # ── Public slots ──────────────────────────────────────────────────────

    def refresh(self) -> None:
        state, x, y = self._get_xy()
        if state is None or not x or not y:
            self._set_info('暂无数据。请先到"运行"页面开始（模拟）', "text_muted")
            self.plot.clear()
            return
        self.plot.set_data(x, y)
        extra = ""
        if state.last_run.fit_kd is not None:
            extra = (
                f"  ·  拟合：Kd = {state.last_run.fit_kd:.6g}，"
                f"R² = {state.last_run.fit_r_squared:.4f}"
            )
        self._set_info(f"数据点：{len(x)}{extra}", "text_primary")

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