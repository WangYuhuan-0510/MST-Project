"""
session_wizard.py
─────────────────
新建实验向导，共两步：
  Step 1 — 选择激发光颜色（RED / BLUE）
  Step 2 — 选择实验类型（预测试 / 结合检验 / 结合亲和力 / 专家模式）

发出 wizard_completed(excitation, experiment) 信号，由 MainWindow 接收并进入 ProjectView。
"""
from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QLabel,
    QPushButton, QFrame, QSizePolicy, QSpacerItem,
    QStackedWidget,
)

from .ui_style import PALETTE, SIDEBAR_W, divider, secondary_btn_style


# ─────────────────────────────────────────────────────────────────────────────
#  Shared style helpers
# ─────────────────────────────────────────────────────────────────────────────

def _sidebar_action_btn(icon: str, text: str, danger: bool = False) -> QPushButton:
    color = PALETTE["danger"] if danger else PALETTE["text_secondary"]
    hover = PALETTE["danger"] if danger else PALETTE["text_primary"]
    btn = QPushButton()
    btn.setFixedSize(56, 56)
    btn.setCursor(Qt.PointingHandCursor)

    lo = QVBoxLayout(btn)
    lo.setContentsMargins(0, 6, 0, 4)
    lo.setSpacing(2)

    icon_lbl = QLabel(icon)
    icon_lbl.setAlignment(Qt.AlignCenter)
    icon_lbl.setStyleSheet(
        f"color: {color}; font-size: 20px; background: transparent; border: none;"
    )
    icon_lbl.setAttribute(Qt.WA_TransparentForMouseEvents)

    text_lbl = QLabel(text)
    text_lbl.setAlignment(Qt.AlignCenter)
    text_lbl.setStyleSheet(
        f"color: {color}; font-size: 10px; font-weight: 600;"
        " background: transparent; border: none; letter-spacing: 0.3px;"
    )
    text_lbl.setAttribute(Qt.WA_TransparentForMouseEvents)

    lo.addWidget(icon_lbl)
    lo.addWidget(text_lbl)

    btn.setStyleSheet(f"""
        QPushButton {{
            background: transparent;
            border: none;
            border-radius: 8px;
        }}
        QPushButton:hover {{
            background: {PALETTE['bg_hover']};
        }}
        QPushButton:hover QLabel {{
            color: {hover};
        }}
        QPushButton:pressed {{
            background: {PALETTE['bg_active']};
        }}
    """)
    return btn


def _help_btn() -> QPushButton:
    btn = QPushButton("?")
    btn.setFixedSize(28, 28)
    btn.setCursor(Qt.PointingHandCursor)
    btn.setStyleSheet(f"""
        QPushButton {{
            background: {PALETTE['bg_hover']};
            border: 1px solid {PALETTE['border']};
            border-radius: 6px;
            color: {PALETTE['text_muted']};
            font-size: 12px;
            font-weight: 700;
        }}
        QPushButton:hover {{
            background: {PALETTE['bg_active']};
            color: {PALETTE['accent']};
            border-color: {PALETTE['accent']};
        }}
    """)
    return btn


# ─────────────────────────────────────────────────────────────────────────────
#  Wizard Sidebar  (Close + Save，左侧固定)
# ─────────────────────────────────────────────────────────────────────────────

class _WizardSidebar(QWidget):
    close_clicked = Signal()
    save_clicked  = Signal()

    def __init__(self, session_name: str = "1", parent=None):
        super().__init__(parent)
        self.setFixedWidth(SIDEBAR_W)
        self.setStyleSheet(f"background: {PALETTE['bg_sidebar']};")

        lo = QVBoxLayout(self)
        lo.setContentsMargins(12, 16, 12, 16)
        lo.setSpacing(0)

        # Session 标题
        title = QLabel("Session")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet(
            f"color: {PALETTE['text_muted']}; font-size: 11px; font-weight: 700;"
            " letter-spacing: 0.8px;"
        )
        overview = QLabel("Overview")
        overview.setAlignment(Qt.AlignCenter)
        overview.setStyleSheet(
            f"color: {PALETTE['text_muted']}; font-size: 11px; font-weight: 700;"
            " letter-spacing: 0.8px;"
        )
        lo.addWidget(title)
        lo.addWidget(overview)
        lo.addSpacing(16)

        # Close / Save
        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)
        btn_row.setAlignment(Qt.AlignCenter)

        self.btn_close = _sidebar_action_btn("✕", "Close", danger=True)
        self.btn_save  = _sidebar_action_btn("💾", "Save",  danger=False)
        self.btn_close.clicked.connect(self.close_clicked)
        self.btn_save.clicked.connect(self.save_clicked)

        btn_row.addWidget(self.btn_close)
        btn_row.addWidget(self.btn_save)
        lo.addLayout(btn_row)

        lo.addStretch()


# ─────────────────────────────────────────────────────────────────────────────
#  Step 1 — Select Excitation Color
# ─────────────────────────────────────────────────────────────────────────────

class _ExcitationPage(QWidget):
    color_selected = Signal(str)   # "RED" or "BLUE"

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet(f"background: {PALETTE['bg_main']};")

        # 顶部 Device 信息栏
        top_bar = QFrame()
        top_bar.setFixedHeight(44)
        top_bar.setStyleSheet(
            f"background: {PALETTE['bg_card']};"
            f"border-bottom: 1px solid {PALETTE['border']};"
        )
        top_lo = QHBoxLayout(top_bar)
        top_lo.setContentsMargins(24, 0, 24, 0)
        device_lbl = QLabel("Device: PW-MST")
        device_lbl.setStyleSheet(
            f"color: {PALETTE['text_secondary']}; font-size: 13px;"
        )
        top_lo.addWidget(device_lbl)
        top_lo.addStretch()

        # 中央内容
        center = QWidget()
        center.setStyleSheet("background: transparent;")
        center_lo = QVBoxLayout(center)
        center_lo.setAlignment(Qt.AlignCenter)
        center_lo.setSpacing(24)

        title = QLabel("Select Excitation Color")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet(
            f"color: {PALETTE['text_muted']}; font-size: 32px; font-weight: 300;"
            " letter-spacing: -0.5px;"
        )

        subtitle = QLabel(
            "Select the excitation color for your experiment"
        )
        subtitle.setAlignment(Qt.AlignCenter)
        subtitle.setStyleSheet(
            f"color: {PALETTE['text_muted']}; font-size: 13px; line-height: 1.6;"
        )

        # RED 按钮
        red_row = QHBoxLayout()
        red_row.setSpacing(10)
        red_row.setAlignment(Qt.AlignCenter)
        self.btn_red = self._choice_btn("🔴  Nano - RED", accent="#C0394B")
        self.btn_red.clicked.connect(lambda: self.color_selected.emit("RED"))
        red_row.addWidget(self.btn_red)
        red_row.addWidget(_help_btn())

        # BLUE 按钮
        blue_row = QHBoxLayout()
        blue_row.setSpacing(10)
        blue_row.setAlignment(Qt.AlignCenter)
        self.btn_blue = self._choice_btn("🔵  Nano - BLUE", accent="#2255CC")
        self.btn_blue.clicked.connect(lambda: self.color_selected.emit("BLUE"))
        blue_row.addWidget(self.btn_blue)
        blue_row.addWidget(_help_btn())

        center_lo.addWidget(title)
        center_lo.addWidget(subtitle)
        center_lo.addSpacing(16)
        center_lo.addLayout(red_row)
        center_lo.addLayout(blue_row)

        # 整体竖向布局
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        root.addWidget(top_bar)
        root.addStretch()
        root.addWidget(center)
        root.addStretch(2)

    @staticmethod
    def _choice_btn(text: str, accent: str) -> QPushButton:
        btn = QPushButton(text)
        btn.setFixedSize(200, 44)
        btn.setCursor(Qt.PointingHandCursor)
        btn.setStyleSheet(f"""
            QPushButton {{
                background: {PALETTE['bg_card']};
                border: 1px solid {PALETTE['border']};
                border-radius: 7px;
                color: {PALETTE['text_primary']};
                font-size: 14px;
                font-weight: 600;
                text-align: left;
                padding-left: 16px;
            }}
            QPushButton:hover {{
                border: 2px solid {accent};
                color: {accent};
                background: {PALETTE['bg_hover']};
            }}
            QPushButton:pressed {{
                background: {PALETTE['bg_active']};
            }}
        """)
        return btn


# ─────────────────────────────────────────────────────────────────────────────
#  Step 2 — Choose an Experiment
# ─────────────────────────────────────────────────────────────────────────────

_EXPERIMENT_DESCS = {
    "Pre-test": "Select the <b>Pre-test</b> experiment, for checking fluorescence and optimizing the determination conditions.",
    "Binding Test": "Select the <b>Binding Test</b> experiment, for obtaining the yes/no interaction results and widely optimizing the determination conditions.",
    "Binding Affinity": "Select the <b>Binding Affinity</b> experiment, for quantifying the interaction and extracting the Kd value.",
    "Expert Mode": "Select the <b>Expert Mode</b>, for all other custom experiment scenarios.",
}

_EXPERIMENT_ICONS = {
    "Pre-test":   "☀",
    "Binding Check": "◕",
    "Binding Affinity": "◈",
    "Expert Mode": "⚙",
}


class _ExperimentPage(QWidget):
    experiment_selected = Signal(str)   # experiment name

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet(f"background: {PALETTE['bg_main']};")
        self._excitation = "RED"

        # 顶部 Device + Excitation 信息栏
        top_bar = QFrame()
        top_bar.setFixedHeight(84)
        top_bar.setStyleSheet(
            f"background: {PALETTE['bg_card']};"
            f"border-bottom: 1px solid {PALETTE['border']};"
        )
        top_lo = QVBoxLayout(top_bar)
        top_lo.setContentsMargins(24, 8, 24, 8)
        top_lo.setSpacing(4)

        dev_row = QHBoxLayout()
        self.device_lbl = QLabel("仪器：PW-MST")
        self.device_lbl.setStyleSheet(
            f"color: {PALETTE['text_secondary']}; font-size: 13px;"
        )
        dev_row.addWidget(self.device_lbl)
        dev_row.addStretch()

        ex_row = QHBoxLayout()
        self.excitation_lbl = QLabel("☀   Excitation: Nano - RED")
        self.excitation_lbl.setStyleSheet(
            f"color: {PALETTE['text_secondary']}; font-size: 13px;"
        )
        change_btn = QPushButton("Change")
        change_btn.setFixedHeight(28)
        change_btn.setStyleSheet(secondary_btn_style())
        # 真正的连接在 SessionWizard.__init__ 里完成（back_to_step1 信号）
        self._change_btn = change_btn
        ex_row.addWidget(self.excitation_lbl)
        ex_row.addWidget(change_btn)
        ex_row.addStretch()

        top_lo.addLayout(dev_row)
        top_lo.addWidget(divider())
        top_lo.addLayout(ex_row)

        # 右侧描述面板
        desc_panel = QFrame()
        desc_panel.setFixedWidth(260)
        desc_panel.setStyleSheet(
            f"background: {PALETTE['bg_sidebar']};"
            f"border-left: 1px solid {PALETTE['border']};"
        )
        desc_lo = QVBoxLayout(desc_panel)
        desc_lo.setContentsMargins(20, 24, 20, 24)
        desc_lo.setSpacing(16)

        self._desc_labels: dict[str, QLabel] = {}
        for name, desc in _EXPERIMENT_DESCS.items():
            lbl = QLabel(desc)
            lbl.setWordWrap(True)
            lbl.setStyleSheet(
                f"color: {PALETTE['text_secondary']}; font-size: 12px; line-height: 1.6;"
                " background: transparent;"
            )
            self._desc_labels[name] = lbl
            desc_lo.addWidget(lbl)
        desc_lo.addStretch()

        # 中央选择区
        center = QWidget()
        center.setStyleSheet("background: transparent;")
        center_lo = QVBoxLayout(center)
        center_lo.setAlignment(Qt.AlignCenter)
        center_lo.setSpacing(12)

        title = QLabel("Select Experiment Type:")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet(
            f"color: {PALETTE['text_muted']}; font-size: 28px; font-weight: 300;"
        )
        center_lo.addWidget(title)
        center_lo.addSpacing(8)

        self._exp_btns: list[QPushButton] = []
        for name in _EXPERIMENT_DESCS:
            row = QHBoxLayout()
            row.setSpacing(10)
            row.setAlignment(Qt.AlignCenter)

            btn = self._exp_btn(name)
            btn.clicked.connect(lambda _, n=name: self.experiment_selected.emit(n))
            self._exp_btns.append(btn)
            row.addWidget(btn)
            row.addWidget(_help_btn())
            center_lo.addLayout(row)

        # 主体布局：center | desc_panel
        body = QHBoxLayout()
        body.setContentsMargins(0, 0, 0, 0)
        body.setSpacing(0)
        body.addStretch()
        body.addWidget(center)
        body.addStretch()
        body.addWidget(desc_panel)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        root.addWidget(top_bar)
        root.addLayout(body, 1)

    def set_excitation(self, color: str) -> None:
        self._excitation = color
        icon = "☀" if color == "RED" else "💙"
        self.excitation_lbl.setText(f"{icon}   Excitation: Nano - {color}")

    @staticmethod
    def _exp_btn(name: str) -> QPushButton:
        icon = _EXPERIMENT_ICONS.get(name, "●")
        btn = QPushButton(f"  {icon}   {name}")
        btn.setFixedSize(280, 70)
        btn.setCursor(Qt.PointingHandCursor)
        btn.setStyleSheet(f"""
            QPushButton {{
                background: {PALETTE['bg_card']};
                border: 1px solid {PALETTE['border']};
                border-radius: 8px;
                color: {PALETTE['text_primary']};
                font-size: 15px;
                font-weight: 600;
                text-align: left;
                padding-left: 20px;
            }}
            QPushButton:hover {{
                border: 2px solid {PALETTE['accent']};
                background: {PALETTE['bg_hover']};
                color: {PALETTE['accent']};
            }}
            QPushButton:pressed {{
                background: {PALETTE['bg_active']};
            }}
        """)
        return btn


# ─────────────────────────────────────────────────────────────────────────────
#  SessionWizard  — 组合侧边栏 + 两步页面
# ─────────────────────────────────────────────────────────────────────────────

class SessionWizard(QWidget):
    """
    启动向导（新建实验后显示）。
    wizard_completed(excitation: str, experiment: str) 信号携带用户选择，
    由 MainWindow 接收并进入 ProjectView。
    close_requested 信号触发返回欢迎页。
    """
    wizard_completed = Signal(str, str)   # (excitation, experiment)
    close_requested  = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet(f"background: {PALETTE['bg_main']};")

        self._excitation = "RED"

        # ── 侧边栏 ─────────────────────────────────────────────────────────
        self.sidebar = _WizardSidebar()
        self.sidebar.close_clicked.connect(self.close_requested)
        self.sidebar.save_clicked.connect(lambda: print("[Wizard] Save"))

        # ── 内容页 ─────────────────────────────────────────────────────────
        self._stack = QStackedWidget()

        self._page1 = _ExcitationPage()
        self._page1.color_selected.connect(self._on_color_selected)

        self._page2 = _ExperimentPage()
        self._page2.experiment_selected.connect(self._on_experiment_selected)
        self._page2._change_btn.clicked.connect(lambda: self._stack.setCurrentIndex(0))

        self._stack.addWidget(self._page1)   # 0
        self._stack.addWidget(self._page2)   # 1
        self._stack.setCurrentIndex(0)

        # 竖分隔线
        sep = QFrame()
        sep.setFrameShape(QFrame.VLine)
        sep.setFixedWidth(1)
        sep.setStyleSheet(f"background: {PALETTE['border']}; border: none;")

        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        root.addWidget(self.sidebar)
        root.addWidget(sep)
        root.addWidget(self._stack, 1)

    # ── 槽 ────────────────────────────────────────────────────────────────

    def _on_color_selected(self, color: str) -> None:
        self._excitation = color
        self._page2.set_excitation(color)
        self._stack.setCurrentIndex(1)

    def _on_experiment_selected(self, experiment: str) -> None:
        self.wizard_completed.emit(self._excitation, experiment)

    # ── 重置（每次进入新建流程时调用）────────────────────────────────────

    def reset(self) -> None:
        self._excitation = "RED"
        self._stack.setCurrentIndex(0)