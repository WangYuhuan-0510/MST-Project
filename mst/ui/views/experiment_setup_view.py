"""
experiment_setup_view.py  （Plan 页面）
────────────────────────────────────────
实验参数设置页面 — 沿用原有业务逻辑，套用项目统一风格。
"""
from __future__ import annotations

from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QFormLayout,
    QDoubleSpinBox,
    QSpinBox,
    QPushButton,
    QLabel,
    QHBoxLayout,
    QFrame,
    QScrollArea,
)
from PySide6.QtCore import Qt

from .ui_style import (
    PALETTE,
    page_base_style,
    card_style,
    primary_btn_style,
    spinbox_style,
    label_style,
    section_label,
    divider,
)


class ExperimentSetupView(QScrollArea):
    """
    实验参数设置页面（Plan）。
    原有业务逻辑保持不变，应用项目统一视觉风格。
    """

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setFrameShape(QFrame.NoFrame)
        self.setWidgetResizable(True)
        self.setStyleSheet(f"background: {PALETTE['bg_main']};")

        # ── 内部可滚动容器 ──────────────────────────
        inner = QWidget()
        inner.setStyleSheet(f"background: {PALETTE['bg_main']};")
        self.setWidget(inner)

        root = QVBoxLayout(inner)
        root.setContentsMargins(28, 28, 28, 28)
        root.setSpacing(20)

        # ── 标题区 ──────────────────────────────────
        root.addWidget(section_label("EXPERIMENT PLAN"))

        title_lbl = QLabel("模拟实验参数", inner)
        title_lbl.setStyleSheet(
            f"color: {PALETTE['text_primary']};"
            "font-size: 20px;"
            "font-weight: 700;"
            "letter-spacing: -0.3px;"
        )
        root.addWidget(title_lbl)
        root.addWidget(divider())

        # ── 参数卡片 ────────────────────────────────
        card = QFrame(inner)
        card.setStyleSheet(card_style(10))
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(24, 20, 24, 20)
        card_layout.setSpacing(4)

        params_label = section_label("PARAMETERS")
        card_layout.addWidget(params_label)
        card_layout.addSpacing(10)

        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignRight | Qt.AlignVCenter)
        form.setFormAlignment(Qt.AlignLeft | Qt.AlignTop)
        form.setHorizontalSpacing(20)
        form.setVerticalSpacing(12)
        card_layout.addLayout(form)

        # ── 共用 spinbox 样式 ────────────────────────
        _sp = spinbox_style()
        _lbl_ss = label_style(13, 500, "text_secondary")

        def _row_label(text: str) -> QLabel:
            l = QLabel(text)
            l.setStyleSheet(_lbl_ss)
            return l

        # Kd (true)
        self.kd = QDoubleSpinBox(inner)
        self.kd.setRange(1e-6, 1e6)
        self.kd.setDecimals(6)
        self.kd.setValue(2.0)
        self.kd.setStyleSheet(_sp)
        form.addRow(_row_label("Kd (true)"), self.kd)

        # Rmax (true)
        self.rmax = QDoubleSpinBox(inner)
        self.rmax.setRange(1e-6, 1e6)
        self.rmax.setDecimals(6)
        self.rmax.setValue(5.0)
        self.rmax.setStyleSheet(_sp)
        form.addRow(_row_label("Rmax (true)"), self.rmax)

        # 噪声
        self.noise = QDoubleSpinBox(inner)
        self.noise.setRange(0.0, 10.0)
        self.noise.setDecimals(4)
        self.noise.setSingleStep(0.01)
        self.noise.setValue(0.05)
        self.noise.setStyleSheet(_sp)
        form.addRow(_row_label("噪声标准差"), self.noise)

        # 采样点数
        self.n_points = QSpinBox(inner)
        self.n_points.setRange(5, 5000)
        self.n_points.setValue(60)
        self.n_points.setStyleSheet(_sp)
        form.addRow(_row_label("采样点数"), self.n_points)

        # x_min
        self.x_min = QDoubleSpinBox(inner)
        self.x_min.setRange(0.0, 1e6)
        self.x_min.setDecimals(6)
        self.x_min.setValue(0.05)
        self.x_min.setStyleSheet(_sp)
        form.addRow(_row_label("x_min"), self.x_min)

        # x_max
        self.x_max = QDoubleSpinBox(inner)
        self.x_max.setRange(1e-6, 1e6)
        self.x_max.setDecimals(6)
        self.x_max.setValue(10.0)
        self.x_max.setStyleSheet(_sp)
        form.addRow(_row_label("x_max"), self.x_max)

        root.addWidget(card)

        # ── 操作栏 ──────────────────────────────────
        actions = QHBoxLayout()
        actions.setSpacing(10)

        self.btn_apply = QPushButton("应用到模拟器", inner)
        self.btn_apply.setFixedHeight(36)
        self.btn_apply.setStyleSheet(primary_btn_style())
        self.btn_apply.clicked.connect(self.apply_to_state)
        actions.addWidget(self.btn_apply)
        actions.addStretch(1)
        root.addLayout(actions)

        # ── 状态提示 ────────────────────────────────
        self.status = QLabel("", inner)
        self.status.setStyleSheet(
            f"color: {PALETTE['success']};"
            "font-size: 12px;"
            "font-weight: 500;"
            f"background: transparent;"
        )
        root.addWidget(self.status)
        root.addStretch()

        # ── 初始化加载 ──────────────────────────────
        self._load_from_state()

    # ── Private helpers ──────────────────────────────────────────────────────

    def _mw(self):
        return self.window()

    def _load_from_state(self) -> None:
        mw = self._mw()
        if not hasattr(mw, "state"):
            return
        sim = mw.state.sim
        self.kd.setValue(sim.kd_true)
        self.rmax.setValue(sim.r_max_true)
        self.noise.setValue(sim.noise_std)
        self.n_points.setValue(sim.n_points)
        self.x_min.setValue(sim.x_min)
        self.x_max.setValue(sim.x_max)

    # ── Public slots ─────────────────────────────────────────────────────────

    def apply_to_state(self) -> None:
        mw = self._mw()
        if not hasattr(mw, "state"):
            self.status.setText("未找到主窗口状态（state）")
            self.status.setStyleSheet(
                f"color: {PALETTE['danger']}; font-size: 12px; font-weight: 500;"
            )
            return
        sim = mw.state.sim
        sim.kd_true    = float(self.kd.value())
        sim.r_max_true = float(self.rmax.value())
        sim.noise_std  = float(self.noise.value())
        sim.n_points   = int(self.n_points.value())
        sim.x_min      = float(self.x_min.value())
        sim.x_max      = float(self.x_max.value())
        self.status.setText("✓  已应用：运行页将按此参数生成模拟数据。")
        self.status.setStyleSheet(
            f"color: {PALETTE['success']}; font-size: 12px; font-weight: 500; background: transparent;"
        )