"""
session_wizard.py
─────────────────
新建实验向导：
  Step 1 — 选择激发光颜色（RED / BLUE）
  Step 2 — 选择实验类型（由 schema 配置驱动）
"""
from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from mst.core.experiment_schema import list_experiment_types
from .ui_style import PALETTE, SIDEBAR_W, divider, secondary_btn_style


def _sidebar_action_btn(icon: str, text: str, danger: bool = False) -> QPushButton:
    color = PALETTE["danger"] if danger else PALETTE["text_secondary"]
    hover = PALETTE["danger"] if danger else PALETTE["text_primary"]
    border = PALETTE["danger"] if danger else PALETTE["border"]
    hover_border = PALETTE["danger"] if danger else PALETTE["accent"]
    btn = QPushButton(f"{icon}\n{text}")
    btn.setFixedSize(84, 84)
    btn.setCursor(Qt.PointingHandCursor)
    btn.setStyleSheet(f"""
        QPushButton {{
            background: {PALETTE['bg_card']};
            border: 1px solid {border};
            border-radius: 12px;
            color: {color};
            font-size: 13px;
            font-weight: 600;
            text-align: center;
            padding: 8px 6px;
        }}
        QPushButton:hover {{
            background: {PALETTE['bg_hover']};
            color: {hover};
            border-color: {hover_border};
        }}
        QPushButton:pressed {{
            background: {PALETTE['bg_active']};
            border-color: {hover_border};
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


class _WizardSidebar(QWidget):
    close_clicked = Signal()
    save_clicked = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(SIDEBAR_W)
        self.setStyleSheet(f"background: {PALETTE['bg_sidebar']};")

        lo = QVBoxLayout(self)
        lo.setContentsMargins(12, 16, 12, 16)

        title = QLabel("Session\nOverview")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet(f"color: {PALETTE['text_muted']}; font-size: 11px; font-weight: 700;")
        lo.addWidget(title)
        lo.addSpacing(16)

        btn_row = QHBoxLayout()
        btn_row.setContentsMargins(6, 0, 6, 0)
        btn_row.setSpacing(10)
        self.btn_close = _sidebar_action_btn("✕", "Close", danger=True)
        self.btn_save = _sidebar_action_btn("💾", "Save", danger=False)
        self.btn_close.clicked.connect(self.close_clicked)
        self.btn_save.clicked.connect(self.save_clicked)
        btn_row.addWidget(self.btn_close)
        btn_row.addWidget(self.btn_save)
        lo.addLayout(btn_row)
        lo.addStretch()


class _ExcitationPage(QWidget):
    color_selected = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet(f"background: {PALETTE['bg_main']};")

        top = QFrame()
        top.setFixedHeight(44)
        top.setStyleSheet(f"background: {PALETTE['bg_card']}; border-bottom: 1px solid {PALETTE['border']};")
        top_lo = QHBoxLayout(top)
        top_lo.setContentsMargins(24, 0, 24, 0)
        top_lo.addWidget(QLabel("Device: PW-MST"))
        top_lo.addStretch()

        center = QVBoxLayout()
        center.setAlignment(Qt.AlignCenter)
        center.setSpacing(18)

        t = QLabel("Select Excitation Color")
        t.setAlignment(Qt.AlignCenter)
        t.setStyleSheet(f"color: {PALETTE['text_muted']}; font-size: 32px; font-weight: 300;")
        center.addWidget(t)

        btn_red = self._choice_btn("🔴  Nano - RED", "#C0394B")
        btn_blue = self._choice_btn("🔵  Nano - BLUE", "#2255CC")
        btn_red.clicked.connect(lambda: self.color_selected.emit("RED"))
        btn_blue.clicked.connect(lambda: self.color_selected.emit("BLUE"))

        for b in (btn_red, btn_blue):
            row = QHBoxLayout()
            row.setAlignment(Qt.AlignCenter)
            row.setSpacing(10)
            row.addWidget(b)
            row.addWidget(_help_btn())
            center.addLayout(row)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        root.addWidget(top)
        root.addStretch()
        root.addLayout(center)
        root.addStretch(2)

    @staticmethod
    def _choice_btn(text: str, accent: str) -> QPushButton:
        btn = QPushButton(text)
        btn.setFixedSize(220, 44)
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
            QPushButton:hover {{ border: 2px solid {accent}; color: {accent}; }}
        """)
        return btn


class _ExperimentPage(QWidget):
    experiment_selected = Signal(str)  # experiment_type_id

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet(f"background: {PALETTE['bg_main']};")

        self._type_items = list_experiment_types()

        top = QFrame()
        top.setFixedHeight(84)
        top.setStyleSheet(f"background: {PALETTE['bg_card']}; border-bottom: 1px solid {PALETTE['border']};")
        top_lo = QVBoxLayout(top)
        top_lo.setContentsMargins(24, 8, 24, 8)

        row1 = QHBoxLayout()
        row1.addWidget(QLabel("Device：PW-MST"))
        row1.addStretch()
        top_lo.addLayout(row1)
        top_lo.addWidget(divider())

        row2 = QHBoxLayout()
        self.excitation_lbl = QLabel("☀   Excitation: Nano - RED")
        self._change_btn = QPushButton("Change")
        self._change_btn.setFixedHeight(28)
        self._change_btn.setStyleSheet(secondary_btn_style())
        row2.addWidget(self.excitation_lbl)
        row2.addWidget(self._change_btn)
        row2.addStretch()
        top_lo.addLayout(row2)

        center = QWidget()
        center_lo = QVBoxLayout(center)
        center_lo.setAlignment(Qt.AlignCenter)
        center_lo.setSpacing(12)

        title = QLabel("Select Experiment Type:")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet(f"color: {PALETTE['text_muted']}; font-size: 28px; font-weight: 300;")
        center_lo.addWidget(title)

        for item in self._type_items:
            exp_id = str(item.get("id", "pre_test"))
            name = str(item.get("name", exp_id))
            if name.casefold() == "binding test":
                name = "Binding Check"
            icon = str(item.get("icon", "●"))

            row = QHBoxLayout()
            row.setAlignment(Qt.AlignCenter)
            row.setSpacing(10)

            btn = QPushButton(f"  {icon}   {name}")
            btn.setFixedSize(300, 70)
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
            """)
            btn.clicked.connect(lambda _, x=exp_id: self.experiment_selected.emit(x))
            row.addWidget(btn)
            row.addWidget(_help_btn())
            center_lo.addLayout(row)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        root.addWidget(top)
        root.addStretch()
        root.addWidget(center)
        root.addStretch()

    def set_excitation(self, color: str) -> None:
        icon = "☀" if color == "RED" else "💙"
        self.excitation_lbl.setText(f"{icon}   Excitation: Nano - {color}")


class SessionWizard(QWidget):
    """wizard_completed(excitation, experiment_type_id)"""

    wizard_completed = Signal(str, str)
    close_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet(f"background: {PALETTE['bg_main']};")

        self._excitation = "RED"

        self.sidebar = _WizardSidebar()
        self.sidebar.close_clicked.connect(self.close_requested)

        self._stack = QStackedWidget()
        self._page1 = _ExcitationPage()
        self._page2 = _ExperimentPage()
        self._page1.color_selected.connect(self._on_color_selected)
        self._page2.experiment_selected.connect(self._on_experiment_selected)
        self._page2._change_btn.clicked.connect(lambda: self._stack.setCurrentIndex(0))

        self._stack.addWidget(self._page1)
        self._stack.addWidget(self._page2)

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

    def _on_color_selected(self, color: str) -> None:
        self._excitation = color
        self._page2.set_excitation(color)
        self._stack.setCurrentIndex(1)

    def _on_experiment_selected(self, experiment_type_id: str) -> None:
        self.wizard_completed.emit(self._excitation, experiment_type_id)

    def reset(self) -> None:
        self._excitation = "RED"
        self._stack.setCurrentIndex(0)
