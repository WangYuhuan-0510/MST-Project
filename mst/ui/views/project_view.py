from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QLabel, QPushButton,
    QStackedWidget, QFrame, QScrollArea, QSizePolicy,
    QTextEdit, QSplitter, QSpacerItem
)
from PySide6.QtCore import Qt, QSize, Signal
from PySide6.QtGui import QFont, QIcon, QColor


# ─────────────────────────────────────────────
#  Color palette & typography constants
# ─────────────────────────────────────────────
PALETTE = {
    "bg_sidebar":     "#F0EDF4",   # 浅紫灰，侧边栏底色
    "bg_main":        "#F7F5FA",   # 极浅灰紫，主区域底色
    "bg_card":        "#FFFFFF",   # 纯白卡片
    "bg_hover":       "#EAE4F0",   # 悬停浅紫
    "bg_active":      "#DDD4EA",   # 激活态淡紫
    "accent":         "#82318E",   # 清华紫（主色）
    "accent_dim":     "#5E2068",   # 深清华紫（按钮）
    "text_primary":   "#1A0D22",   # 深紫黑，主文字
    "text_secondary": "#5A4668",   # 中紫灰，副文字
    "text_muted":     "#9D89AA",   # 浅紫灰，弱提示
    "border":         "#DDD4EA",   # 边框浅紫
    "border_active":  "#82318E",   # 激活边框紫
    "danger":         "#C0394B",   # 危险红
    "success":        "#2E7D5E",   # 成功绿
    "warning":        "#B06A00",   # 警告橙
}

SIDEBAR_W = 220


# ─────────────────────────────────────────────
#  Sidebar action button  (Save / Close)
# ─────────────────────────────────────────────
class ActionButton(QPushButton):
    def __init__(self, label: str, icon_char: str, danger: bool = False, parent=None):
        super().__init__(parent)
        color = PALETTE["danger"] if danger else PALETTE["text_secondary"]
        hover = PALETTE["danger"] if danger else PALETTE["text_primary"]

        self.setText(f"{icon_char}  {label}")
        self.setFixedHeight(36)
        self.setCursor(Qt.PointingHandCursor)
        self.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                border: none;
                border-radius: 6px;
                color: {color};
                font-size: 13px;
                font-weight: 500;
                text-align: left;
                padding: 0 12px;
                letter-spacing: 0.2px;
            }}
            QPushButton:hover {{
                background: {PALETTE["bg_hover"]};
                color: {hover};
            }}
            QPushButton:pressed {{
                background: {PALETTE["bg_active"]};
            }}
        """)


# ─────────────────────────────────────────────
#  Experiment item in the sidebar list
# ─────────────────────────────────────────────
class ExperimentItem(QPushButton):
    def __init__(self, name: str, status: str = "draft", parent=None):
        super().__init__(parent)
        self.setCheckable(True)
        self.setFixedHeight(52)
        self.setCursor(Qt.PointingHandCursor)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        status_colors = {
            "draft":    PALETTE["text_muted"],
            "running":  PALETTE["warning"],
            "done":     PALETTE["success"],
            "failed":   PALETTE["danger"],
        }
        dot_color = status_colors.get(status, PALETTE["text_muted"])

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 0, 12, 0)
        layout.setSpacing(10)

        # Status dot
        dot = QLabel("●")
        dot.setStyleSheet(f"color: {dot_color}; font-size: 8px;")
        dot.setFixedWidth(10)

        # Name
        name_label = QLabel(name)
        name_label.setStyleSheet(f"""
            color: {PALETTE["text_primary"]};
            font-size: 13px;
            font-weight: 500;
        """)
        name_label.setAttribute(Qt.WA_TransparentForMouseEvents)

        # Tag
        tag = QLabel(status.upper())
        tag.setStyleSheet(f"""
            color: {dot_color};
            font-size: 9px;
            font-weight: 700;
            letter-spacing: 0.8px;
        """)
        tag.setAttribute(Qt.WA_TransparentForMouseEvents)

        layout.addWidget(dot)
        layout.addWidget(name_label, 1)
        layout.addWidget(tag)

        self.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                border: none;
                border-radius: 8px;
                text-align: left;
            }}
            QPushButton:hover {{
                background: {PALETTE["bg_hover"]};
            }}
            QPushButton:checked {{
                background: {PALETTE["bg_active"]};
                border-left: 2px solid {PALETTE["accent"]};
            }}
        """)


# ─────────────────────────────────────────────
#  "New Experiment" button
# ─────────────────────────────────────────────
class NewExperimentButton(QPushButton):
    def __init__(self, parent=None):
        super().__init__("＋  New Experiment", parent)
        self.setFixedHeight(40)
        self.setCursor(Qt.PointingHandCursor)
        self.setStyleSheet(f"""
            QPushButton {{
                background: {PALETTE["accent_dim"]};
                border: none;
                border-radius: 8px;
                color: {PALETTE["text_primary"]};
                font-size: 13px;
                font-weight: 600;
                letter-spacing: 0.3px;
            }}
            QPushButton:hover {{
                background: {PALETTE["accent"]};
            }}
            QPushButton:pressed {{
                background: {PALETTE["accent_dim"]};
            }}
        """)


# ─────────────────────────────────────────────
#  Page-switching tab row (Plan / Instructions / Results / Details)
# ─────────────────────────────────────────────
class PageTabBar(QWidget):
    page_changed = Signal(int)

    TABS = ["Plan", "Instructions", "Results", "Details"]

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(48)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(24, 0, 24, 0)
        layout.setSpacing(4)

        self._buttons: list[QPushButton] = []

        for i, name in enumerate(self.TABS):
            btn = QPushButton(name)
            btn.setCheckable(True)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setFixedHeight(32)
            btn.setStyleSheet(f"""
                QPushButton {{
                    background: transparent;
                    border: none;
                    border-radius: 6px;
                    color: {PALETTE["text_secondary"]};
                    font-size: 13px;
                    font-weight: 500;
                    padding: 0 16px;
                    letter-spacing: 0.2px;
                }}
                QPushButton:hover {{
                    background: {PALETTE["bg_hover"]};
                    color: {PALETTE["text_primary"]};
                }}
                QPushButton:checked {{
                    background: {PALETTE["bg_active"]};
                    color: {PALETTE["accent"]};
                    font-weight: 600;
                }}
            """)
            idx = i
            btn.clicked.connect(lambda _, x=idx: self._select(x))
            self._buttons.append(btn)
            layout.addWidget(btn)

        layout.addStretch()
        self._select(0)

    def _select(self, idx: int):
        for i, btn in enumerate(self._buttons):
            btn.setChecked(i == idx)
        self.page_changed.emit(idx)

class ExperimentInfoPanel(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(120)  # 固定高度
        self.setStyleSheet(f"""
            QFrame {{
                background: {PALETTE["bg_card"]};
                border-top: 1px solid {PALETTE["border"]};
            }}
        """)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(20, 12, 20, 12)
        layout.setSpacing(24)

        def item(title, value):
            vbox = QVBoxLayout()
            t = QLabel(title)
            t.setStyleSheet(f"""
                color: {PALETTE["text_muted"]};
                font-size: 10px;
                font-weight: 700;
            """)
            v = QLabel(value)
            v.setStyleSheet(f"""
                color: {PALETTE["text_primary"]};
                font-size: 13px;
                font-weight: 600;
            """)
            vbox.addWidget(t)
            vbox.addWidget(v)
            return vbox

        layout.addLayout(item("Experiment", "Exp-002"))
        layout.addLayout(item("Status", "Running"))
        layout.addLayout(item("Operator", "Alice"))
        layout.addLayout(item("Last Update", "2 min ago"))

        layout.addStretch()
# ─────────────────────────────────────────────
#  Individual page content widgets
# ─────────────────────────────────────────────
def _section_label(text: str) -> QLabel:
    lbl = QLabel(text)
    lbl.setStyleSheet(f"""
        color: {PALETTE["text_muted"]};
        font-size: 10px;
        font-weight: 700;
        letter-spacing: 1.2px;
        padding: 0;
        margin: 0;
    """)
    return lbl


def _card(title: str, body: str) -> QFrame:
    frame = QFrame()
    frame.setStyleSheet(f"""
        QFrame {{
            background: {PALETTE["bg_card"]};
            border: 1px solid {PALETTE["border"]};
            border-radius: 10px;
        }}
    """)
    vl = QVBoxLayout(frame)
    vl.setContentsMargins(20, 16, 20, 16)
    vl.setSpacing(6)

    t = QLabel(title)
    t.setStyleSheet(f"color: {PALETTE['text_primary']}; font-size: 14px; font-weight: 600;")
    b = QLabel(body)
    b.setWordWrap(True)
    b.setStyleSheet(f"color: {PALETTE['text_secondary']}; font-size: 13px; line-height: 1.5;")

    vl.addWidget(t)
    vl.addWidget(b)
    return frame


class PlanPage(QScrollArea):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFrameShape(QFrame.NoFrame)
        self.setWidgetResizable(True)
        self.setStyleSheet("background: transparent;")

        inner = QWidget()
        self.setWidget(inner)
        vl = QVBoxLayout(inner)
        vl.setContentsMargins(28, 28, 28, 28)
        vl.setSpacing(16)

        vl.addWidget(_section_label("EXPERIMENT PLAN"))
        vl.addWidget(_card("Objective",
            "Define what you want to measure and the hypothesis you are testing. "
            "A clear objective keeps the experiment focused and reproducible."))
        vl.addWidget(_card("Variables",
            "Independent variable: the factor you manipulate.\n"
            "Dependent variable: the outcome you measure.\n"
            "Control variables: factors kept constant."))
        vl.addWidget(_card("Timeline",
            "Estimate the duration of each phase: setup, execution, data collection, and analysis."))
        vl.addStretch()


class InstructionsPage(QScrollArea):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFrameShape(QFrame.NoFrame)
        self.setWidgetResizable(True)
        self.setStyleSheet("background: transparent;")

        inner = QWidget()
        self.setWidget(inner)
        vl = QVBoxLayout(inner)
        vl.setContentsMargins(28, 28, 28, 28)
        vl.setSpacing(16)

        vl.addWidget(_section_label("STEP-BY-STEP INSTRUCTIONS"))
        for i, step in enumerate([
            ("Prepare Materials", "Gather all equipment and reagents before starting. Check calibration dates on instruments."),
            ("Configure Environment", "Set temperature, humidity, and lighting to the values specified in the plan."),
            ("Run Protocol", "Follow the protocol in sequence. Record any deviations in real time."),
            ("Collect Data", "Export raw data immediately after each trial. Name files using the agreed convention."),
            ("Clean Up", "Dispose of waste according to lab safety guidelines and log the completion time."),
        ], 1):
            title, body = step
            frame = QFrame()
            frame.setStyleSheet(f"""
                QFrame {{
                    background: {PALETTE["bg_card"]};
                    border: 1px solid {PALETTE["border"]};
                    border-radius: 10px;
                }}
            """)
            hl = QHBoxLayout(frame)
            hl.setContentsMargins(20, 16, 20, 16)
            hl.setSpacing(16)

            num = QLabel(str(i))
            num.setFixedSize(28, 28)
            num.setAlignment(Qt.AlignCenter)
            num.setStyleSheet(f"""
                background: {PALETTE["accent_dim"]};
                border-radius: 14px;
                color: {PALETTE["text_primary"]};
                font-size: 12px;
                font-weight: 700;
            """)

            inner_vl = QVBoxLayout()
            inner_vl.setSpacing(4)
            t = QLabel(title)
            t.setStyleSheet(f"color: {PALETTE['text_primary']}; font-size: 14px; font-weight: 600;")
            b = QLabel(body)
            b.setWordWrap(True)
            b.setStyleSheet(f"color: {PALETTE['text_secondary']}; font-size: 13px;")
            inner_vl.addWidget(t)
            inner_vl.addWidget(b)

            hl.addWidget(num, 0, Qt.AlignTop)
            hl.addLayout(inner_vl)
            vl.addWidget(frame)

        vl.addStretch()


class ResultsPage(QScrollArea):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFrameShape(QFrame.NoFrame)
        self.setWidgetResizable(True)
        self.setStyleSheet("background: transparent;")

        inner = QWidget()
        self.setWidget(inner)
        vl = QVBoxLayout(inner)
        vl.setContentsMargins(28, 28, 28, 28)
        vl.setSpacing(16)

        vl.addWidget(_section_label("RESULTS"))

        # Metric cards row
        row = QHBoxLayout()
        row.setSpacing(12)
        for label, value, color in [
            ("Trials Run", "24", PALETTE["accent"]),
            ("Success Rate", "87.5 %", PALETTE["success"]),
            ("Avg. Duration", "4 m 12 s", PALETTE["warning"]),
        ]:
            card = QFrame()
            card.setStyleSheet(f"""
                QFrame {{
                    background: {PALETTE["bg_card"]};
                    border: 1px solid {PALETTE["border"]};
                    border-radius: 10px;
                }}
            """)
            cl = QVBoxLayout(card)
            cl.setContentsMargins(20, 16, 20, 16)
            v = QLabel(value)
            v.setStyleSheet(f"color: {color}; font-size: 28px; font-weight: 700;")
            l = QLabel(label)
            l.setStyleSheet(f"color: {PALETTE['text_secondary']}; font-size: 12px;")
            cl.addWidget(v)
            cl.addWidget(l)
            row.addWidget(card)
        vl.addLayout(row)

        # Notes area
        notes_label = _section_label("OBSERVATIONS")
        vl.addSpacerItem(QSpacerItem(0, 8))
        vl.addWidget(notes_label)
        notes = QTextEdit()
        notes.setPlaceholderText("Record your observations here…")
        notes.setFixedHeight(160)
        notes.setStyleSheet(f"""
            QTextEdit {{
                background: {PALETTE["bg_card"]};
                border: 1px solid {PALETTE["border"]};
                border-radius: 10px;
                color: {PALETTE["text_primary"]};
                font-size: 13px;
                padding: 12px;
            }}
            QTextEdit:focus {{
                border: 1px solid {PALETTE["border_active"]};
            }}
        """)
        vl.addWidget(notes)
        vl.addStretch()


class DetailsPage(QScrollArea):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFrameShape(QFrame.NoFrame)
        self.setWidgetResizable(True)
        self.setStyleSheet("background: transparent;")

        inner = QWidget()
        self.setWidget(inner)
        vl = QVBoxLayout(inner)
        vl.setContentsMargins(28, 28, 28, 28)
        vl.setSpacing(16)

        vl.addWidget(_section_label("EXPERIMENT DETAILS"))

        for key, val in [
            ("Experiment ID",    "EXP-2024-0042"),
            ("Created by",       "Alice Chen"),
            ("Created at",       "2024-11-15  09:32 UTC"),
            ("Last modified",    "2024-11-18  14:05 UTC"),
            ("Status",          "Running"),
            ("Project",         "Microfluidics Q4"),
            ("Tags",            "baseline, control, phase-2"),
            ("Storage path",    "/data/experiments/2024/EXP-2024-0042"),
        ]:
            row = QFrame()
            row.setStyleSheet(f"""
                QFrame {{
                    background: {PALETTE["bg_card"]};
                    border: 1px solid {PALETTE["border"]};
                    border-radius: 8px;
                }}
            """)
            hl = QHBoxLayout(row)
            hl.setContentsMargins(16, 12, 16, 12)

            k = QLabel(key)
            k.setFixedWidth(140)
            k.setStyleSheet(f"color: {PALETTE['text_muted']}; font-size: 12px; font-weight: 600; letter-spacing: 0.3px;")

            v = QLabel(val)
            v.setStyleSheet(f"color: {PALETTE['text_primary']}; font-size: 13px;")

            hl.addWidget(k)
            hl.addWidget(v, 1)
            vl.addWidget(row)

        vl.addStretch()


# ─────────────────────────────────────────────
#  Left Sidebar
# ─────────────────────────────────────────────
class Sidebar(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(SIDEBAR_W)
        self.setStyleSheet(f"background: {PALETTE['bg_sidebar']};")

        root = QVBoxLayout(self)
        root.setContentsMargins(12, 20, 12, 16)
        root.setSpacing(0)

        # ── App title
        title = QLabel("Lab")
        title.setStyleSheet(f"""
            color: {PALETTE["text_primary"]};
            font-size: 18px;
            font-weight: 700;
            letter-spacing: -0.3px;
            padding: 0 6px;
        """)
        sub = QLabel("Experiment Manager")
        sub.setStyleSheet(f"""
            color: {PALETTE["text_muted"]};
            font-size: 10px;
            font-weight: 500;
            letter-spacing: 0.5px;
            padding: 0 6px;
        """)
        root.addWidget(title)
        root.addWidget(sub)
        root.addSpacerItem(QSpacerItem(0, 20))

        # ── Action buttons
        self.save_btn  = ActionButton("Save",  "💾", danger=False)
        self.close_btn = ActionButton("Close", "✕",  danger=True)
        root.addWidget(self.save_btn)
        root.addWidget(self.close_btn)

        # ── Divider
        root.addSpacerItem(QSpacerItem(0, 16))
        divider = QFrame()
        divider.setFrameShape(QFrame.HLine)
        divider.setStyleSheet(f"color: {PALETTE['border']}; background: {PALETTE['border']}; border: none; min-height: 1px; max-height: 1px;")
        root.addWidget(divider)
        root.addSpacerItem(QSpacerItem(0, 12))

        # ── Experiments section label
        exp_label = QLabel("EXPERIMENTS")
        exp_label.setStyleSheet(f"""
            color: {PALETTE["text_muted"]};
            font-size: 10px;
            font-weight: 700;
            letter-spacing: 1.2px;
            padding: 0 6px;
        """)
        root.addWidget(exp_label)
        root.addSpacerItem(QSpacerItem(0, 8))

        # ── Experiment list
        self._exp_buttons: list[ExperimentItem] = []
        sample_exps = [
            ("Exp-001: Baseline",    "done"),
            ("Exp-002: Variable A",  "running"),
            ("Exp-003: Variable B",  "draft"),
            ("Exp-004: Control",     "failed"),
        ]
        for name, status in sample_exps:
            btn = ExperimentItem(name, status)
            btn.clicked.connect(lambda checked, b=btn: self._select_exp(b))
            self._exp_buttons.append(btn)
            root.addWidget(btn)

        root.addStretch()

        # ── New Experiment button
        self.new_btn = NewExperimentButton()
        root.addWidget(self.new_btn)

        # Select first by default
        if self._exp_buttons:
            self._exp_buttons[0].setChecked(True)

    def _select_exp(self, selected: ExperimentItem):
        for btn in self._exp_buttons:
            btn.setChecked(btn is selected)


# ─────────────────────────────────────────────
#  Main content area
# ─────────────────────────────────────────────
class ContentArea(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet(f"background: {PALETTE['bg_main']};")

        vl = QVBoxLayout(self)
        vl.setContentsMargins(0, 0, 0, 0)
        vl.setSpacing(0)

        # Tab bar
        self.tab_bar = PageTabBar()
        vl.addWidget(self.tab_bar)

        # Thin accent line under tab bar
        accent_line = QFrame()
        accent_line.setFixedHeight(1)
        accent_line.setStyleSheet(f"background: {PALETTE['border']};")
        vl.addWidget(accent_line)

        # Page stack
        self.stack = QStackedWidget()
        self.stack.setStyleSheet("background: transparent;")
        self.stack.addWidget(PlanPage())
        self.stack.addWidget(InstructionsPage())
        self.stack.addWidget(ResultsPage())
        self.stack.addWidget(DetailsPage())
        self.info_panel = ExperimentInfoPanel()

        # 加入布局
        vl.addWidget(self.stack, 1)     # 可伸缩
        vl.addWidget(self.info_panel)   # 固定区域

        self.tab_bar.page_changed.connect(self.stack.setCurrentIndex)


# ─────────────────────────────────────────────
#  ProjectView – top-level widget
# ─────────────────────────────────────────────
class ProjectView(QWidget):
    """
    实验管理主界面。
    左侧固定导航栏包含：保存/关闭操作按钮、实验列表、新建实验按钮。
    右侧内容区通过顶部标签在 Plan / Instructions / Results / Details 四页间切换。
    切换页面时左侧导航栏保持不变。
    """

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Experiment Manager")
        self.setMinimumSize(900, 620)
        self.setStyleSheet(f"background: {PALETTE['bg_main']};")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.sidebar = Sidebar()
        self.content = ContentArea()

        # Vertical separator line between sidebar and content
        sep = QFrame()
        sep.setFrameShape(QFrame.VLine)
        sep.setFixedWidth(1)
        sep.setStyleSheet(f"background: {PALETTE['border']}; border: none;")

        layout.addWidget(self.sidebar)
        layout.addWidget(sep)
        layout.addWidget(self.content, 1)

        # Wire up action buttons
        self.sidebar.save_btn.clicked.connect(self._on_save)
        self.sidebar.close_btn.clicked.connect(self._on_close)
        self.sidebar.new_btn.clicked.connect(self._on_new_experiment)

    # ── Slots ──────────────────────────────────
    def _on_save(self):
        print("[ProjectView] Save triggered")

    def _on_close(self):
        print("[ProjectView] Close triggered")

    def _on_new_experiment(self):
        print("[ProjectView] New experiment triggered")


# ─────────────────────────────────────────────
#  Standalone preview entry point
# ─────────────────────────────────────────────
if __name__ == "__main__":
    import sys
    from PySide6.QtWidgets import QApplication

    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    w = ProjectView()
    w.show()
    sys.exit(app.exec())