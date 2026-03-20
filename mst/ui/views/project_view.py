"""
project_view.py
───────────────
实验管理主界面框架。
左侧固定侧边栏 + 右侧四标签页，切换页面时侧边栏保持不变。

页面映射
  Plan         →  ExperimentSetupView  (experiment_setup_view.py)
  Instructions →  InstructionsPage     (内联占位，可按需替换)
  Results      →  RunView              (run_view.py)
  Details      →  AnalysisView         (analysis_view.py)
"""
from __future__ import annotations

from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QLabel, QPushButton,
    QStackedWidget, QFrame, QScrollArea, QSizePolicy, QSpacerItem,
    QGridLayout,
)
from PySide6.QtCore import Qt, Signal, QTimer

# ── 共享样式 ────────────────────────────────────────────────────────────────
from .ui_style import (
    PALETTE, SIDEBAR_W,
    label_style, section_label, divider,
)

# ── 页面实现 ────────────────────────────────────────────────────────────────
from .experiment_setup_view import ExperimentSetupView   # Plan
from .run_view              import RunView               # Results
from .analysis_view         import AnalysisView          # Details


# ─────────────────────────────────────────────
#  Sidebar: action button
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
#  Sidebar: experiment list item
# ─────────────────────────────────────────────
class ExperimentItem(QPushButton):
    def __init__(self, name: str, status: str = "draft", parent=None):
        super().__init__(parent)
        self.setCheckable(True)
        self.setFixedHeight(52)
        self.setCursor(Qt.PointingHandCursor)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        status_colors = {
            "draft":   PALETTE["text_muted"],
            "running": PALETTE["warning"],
            "done":    PALETTE["success"],
            "failed":  PALETTE["danger"],
        }
        dot_color = status_colors.get(status, PALETTE["text_muted"])

        lo = QHBoxLayout(self)
        lo.setContentsMargins(12, 0, 12, 0)
        lo.setSpacing(10)

        dot = QLabel("●")
        dot.setStyleSheet(f"color: {dot_color}; font-size: 8px;")
        dot.setFixedWidth(10)

        name_lbl = QLabel(name)
        name_lbl.setStyleSheet(
            f"color: {PALETTE['text_primary']}; font-size: 13px; font-weight: 500;"
        )
        name_lbl.setAttribute(Qt.WA_TransparentForMouseEvents)

        tag = QLabel(status.upper())
        tag.setStyleSheet(
            f"color: {dot_color}; font-size: 9px; font-weight: 700; letter-spacing: 0.8px;"
        )
        tag.setAttribute(Qt.WA_TransparentForMouseEvents)

        lo.addWidget(dot)
        lo.addWidget(name_lbl, 1)
        lo.addWidget(tag)

        self.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                border: none;
                border-radius: 8px;
                text-align: left;
            }}
            QPushButton:hover  {{ background: {PALETTE["bg_hover"]}; }}
            QPushButton:checked {{
                background: {PALETTE["bg_active"]};
                border-left: 2px solid {PALETTE["accent"]};
            }}
        """)


# ─────────────────────────────────────────────
#  Sidebar: new-experiment button
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
                color: #FFFFFF;
                font-size: 13px;
                font-weight: 600;
                letter-spacing: 0.3px;
            }}
            QPushButton:hover   {{ background: {PALETTE["accent"]}; }}
            QPushButton:pressed {{ background: {PALETTE["accent_dim"]}; }}
        """)


# ─────────────────────────────────────────────
#  Tab bar  (Plan / Instructions / Results / Details)
# ─────────────────────────────────────────────
class PageTabBar(QWidget):
    page_changed = Signal(int)
    TABS = ["Plan", "Instructions", "Results", "Details"]

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(48)
        lo = QHBoxLayout(self)
        lo.setContentsMargins(24, 0, 24, 0)
        lo.setSpacing(4)
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
            btn.clicked.connect(lambda _, x=i: self._select(x))
            self._buttons.append(btn)
            lo.addWidget(btn)

        lo.addStretch()
        self._select(0)

    def _select(self, idx: int) -> None:
        for i, btn in enumerate(self._buttons):
            btn.setChecked(i == idx)
        self.page_changed.emit(idx)


# ─────────────────────────────────────────────
#  Instructions page  （占位，可按需替换为真实实现）
# ─────────────────────────────────────────────
class InstructionsPage(QScrollArea):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFrameShape(QFrame.NoFrame)
        self.setWidgetResizable(True)
        self.setStyleSheet(f"background: {PALETTE['bg_main']};")

        inner = QWidget()
        inner.setStyleSheet(f"background: {PALETTE['bg_main']};")
        self.setWidget(inner)
        vl = QVBoxLayout(inner)
        vl.setContentsMargins(28, 28, 28, 28)
        vl.setSpacing(16)

        vl.addWidget(section_label("INSTRUCTIONS"))

        for i, (title, body) in enumerate([
            ("Prepare Materials",
             "Gather all equipment and reagents before starting. Check calibration dates."),
            ("Configure Environment",
             "Set temperature, humidity, and lighting to values specified in the Plan."),
            ("Run Protocol",
             "Follow the protocol in sequence. Record any deviations in real time."),
            ("Collect Data",
             "Export raw data immediately after each trial using the agreed file convention."),
            ("Clean Up",
             "Dispose of waste per lab safety guidelines and log the completion time."),
        ], 1):
            frame = QFrame()
            frame.setStyleSheet(
                f"background: {PALETTE['bg_card']};"
                f"border: 1px solid {PALETTE['border']};"
                "border-radius: 10px;"
            )
            hl = QHBoxLayout(frame)
            hl.setContentsMargins(20, 16, 20, 16)
            hl.setSpacing(16)

            num = QLabel(str(i))
            num.setFixedSize(28, 28)
            num.setAlignment(Qt.AlignCenter)
            num.setStyleSheet(
                f"background: {PALETTE['accent_dim']}; border-radius: 14px;"
                " color: #FFFFFF; font-size: 12px; font-weight: 700;"
            )

            inner_vl = QVBoxLayout()
            inner_vl.setSpacing(4)
            t = QLabel(title)
            t.setStyleSheet(
                f"color: {PALETTE['text_primary']}; font-size: 14px; font-weight: 600;"
            )
            b = QLabel(body)
            b.setWordWrap(True)
            b.setStyleSheet(f"color: {PALETTE['text_secondary']}; font-size: 13px;")
            inner_vl.addWidget(t)
            inner_vl.addWidget(b)

            hl.addWidget(num, 0, Qt.AlignTop)
            hl.addLayout(inner_vl)
            vl.addWidget(frame)

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

        title = QLabel("Lab")
        title.setStyleSheet(
            f"color: {PALETTE['text_primary']}; font-size: 18px; font-weight: 700;"
            " letter-spacing: -0.3px; padding: 0 6px;"
        )
        sub = QLabel("Experiment Manager")
        sub.setStyleSheet(
            f"color: {PALETTE['text_muted']}; font-size: 10px; font-weight: 500;"
            " letter-spacing: 0.5px; padding: 0 6px;"
        )
        root.addWidget(title)
        root.addWidget(sub)
        root.addSpacerItem(QSpacerItem(0, 20))

        self.save_btn  = ActionButton("Save",  "💾", danger=False)
        self.close_btn = ActionButton("Close", "✕",  danger=True)
        root.addWidget(self.save_btn)
        root.addWidget(self.close_btn)

        root.addSpacerItem(QSpacerItem(0, 16))
        root.addWidget(divider())
        root.addSpacerItem(QSpacerItem(0, 12))

        exp_label = QLabel("EXPERIMENTS")
        exp_label.setStyleSheet(
            f"color: {PALETTE['text_muted']}; font-size: 10px; font-weight: 700;"
            " letter-spacing: 1.2px; padding: 0 6px;"
        )
        root.addWidget(exp_label)
        root.addSpacerItem(QSpacerItem(0, 8))

        self._exp_buttons: list[ExperimentItem] = []
        for name, status in [
            ("Exp-001: Baseline",   "done"),
            ("Exp-002: Variable A", "running"),
            ("Exp-003: Variable B", "draft"),
            ("Exp-004: Control",    "failed"),
        ]:
            btn = ExperimentItem(name, status)
            btn.clicked.connect(lambda _, b=btn: self._select_exp(b))
            self._exp_buttons.append(btn)
            root.addWidget(btn)

        root.addStretch()
        self.new_btn = NewExperimentButton()
        root.addWidget(self.new_btn)

        if self._exp_buttons:
            self._exp_buttons[0].setChecked(True)

    def _select_exp(self, selected: ExperimentItem) -> None:
        for btn in self._exp_buttons:
            btn.setChecked(btn is selected)


# ─────────────────────────────────────────────
#  Bottom Data Panel  (固定，不随页面切换变化)
# ─────────────────────────────────────────────
class _MetricCard(QFrame):
    """单个指标卡：标题 + 数值 + 可选单位标签。"""
    def __init__(self, title: str, value: str = "—", unit: str = "", parent=None):
        super().__init__(parent)
        self.setStyleSheet(
            f"background: {PALETTE['bg_card']};"
            f"border: 1px solid {PALETTE['border']};"
            "border-radius: 8px;"
        )
        vl = QVBoxLayout(self)
        vl.setContentsMargins(14, 10, 14, 10)
        vl.setSpacing(2)

        self._title_lbl = QLabel(title)
        self._title_lbl.setStyleSheet(
            f"color: {PALETTE['text_muted']}; font-size: 10px;"
            " font-weight: 700; letter-spacing: 0.8px;"
        )

        val_row = QHBoxLayout()
        val_row.setSpacing(4)
        self._val_lbl = QLabel(value)
        self._val_lbl.setStyleSheet(
            f"color: {PALETTE['text_primary']}; font-size: 18px; font-weight: 700;"
        )
        self._unit_lbl = QLabel(unit)
        self._unit_lbl.setStyleSheet(
            f"color: {PALETTE['text_muted']}; font-size: 11px; font-weight: 500;"
        )
        self._unit_lbl.setAlignment(Qt.AlignBottom)
        val_row.addWidget(self._val_lbl)
        val_row.addWidget(self._unit_lbl)
        val_row.addStretch()

        vl.addWidget(self._title_lbl)
        vl.addLayout(val_row)

    def set_value(self, value: str, color_key: str = "text_primary") -> None:
        self._val_lbl.setText(value)
        self._val_lbl.setStyleSheet(
            f"color: {PALETTE[color_key]}; font-size: 18px; font-weight: 700;"
        )


class DataPanel(QFrame):
    """
    底部固定数据面板。
    直接挂在 ContentArea 布局末尾，不属于任何标签页，
    页面切换时完全不受影响。

    通过 update_from_state(state) 刷新显示；
    也可在外部直接调用各 set_* 方法单独更新。
    """

    PANEL_H = 110   # 面板固定高度（px）

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(self.PANEL_H)
        self.setStyleSheet(
            f"background: {PALETTE['bg_sidebar']};"
            f"border-top: 1px solid {PALETTE['border']};"
        )

        root = QHBoxLayout(self)
        root.setContentsMargins(20, 12, 20, 12)
        root.setSpacing(12)

        # ── 左侧：实验标识 ──────────────────────────────────────────
        id_block = QVBoxLayout()
        id_block.setSpacing(3)

        self._exp_name = QLabel("— 未选择实验 —")
        self._exp_name.setStyleSheet(
            f"color: {PALETTE['text_primary']}; font-size: 14px; font-weight: 700;"
        )
        self._exp_id = QLabel("ID: —")
        self._exp_id.setStyleSheet(
            f"color: {PALETTE['text_muted']}; font-size: 11px;"
        )
        self._exp_status = QLabel("●  —")
        self._exp_status.setStyleSheet(
            f"color: {PALETTE['text_muted']}; font-size: 11px; font-weight: 600;"
        )
        id_block.addWidget(self._exp_name)
        id_block.addWidget(self._exp_id)
        id_block.addWidget(self._exp_status)
        id_block.addStretch()

        root.addLayout(id_block)

        # ── 竖分隔线 ───────────────────────────────────────────────
        def _vsep():
            f = QFrame()
            f.setFrameShape(QFrame.VLine)
            f.setFixedWidth(1)
            f.setStyleSheet(f"background: {PALETTE['border']}; border: none;")
            return f

        root.addWidget(_vsep())

        # ── 中间：指标卡网格（2行×4列）─────────────────────────────
        grid_widget = QWidget()
        grid_widget.setStyleSheet("background: transparent;")
        grid = QGridLayout(grid_widget)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setSpacing(8)

        self._card_kd      = _MetricCard("Kd (拟合)",    "—",  "µM")
        self._card_r2      = _MetricCard("R²",           "—",  "")
        self._card_points  = _MetricCard("数据点",       "—",  "pts")
        self._card_rmax    = _MetricCard("Rmax",         "—",  "")
        self._card_noise   = _MetricCard("噪声 σ",       "—",  "")
        self._card_npts    = _MetricCard("采样设定",     "—",  "pts")
        self._card_xmin    = _MetricCard("x_min",        "—",  "")
        self._card_xmax    = _MetricCard("x_max",        "—",  "")

        cards = [
            self._card_kd,     self._card_r2,
            self._card_points, self._card_rmax,
            self._card_noise,  self._card_npts,
            self._card_xmin,   self._card_xmax,
        ]
        for idx, card in enumerate(cards):
            grid.addWidget(card, idx // 4, idx % 4)

        root.addWidget(grid_widget, 1)

        root.addWidget(_vsep())

        # ── 右侧：时间戳 ────────────────────────────────────────────
        ts_block = QVBoxLayout()
        ts_block.setSpacing(4)

        ts_header = QLabel("LAST UPDATED")
        ts_header.setStyleSheet(
            f"color: {PALETTE['text_muted']}; font-size: 9px;"
            " font-weight: 700; letter-spacing: 1px;"
        )
        self._ts_lbl = QLabel("—")
        self._ts_lbl.setStyleSheet(
            f"color: {PALETTE['text_secondary']}; font-size: 12px;"
        )
        ts_block.addWidget(ts_header)
        ts_block.addWidget(self._ts_lbl)
        ts_block.addStretch()

        root.addLayout(ts_block)

        # ── 自动刷新计时器（每秒从主窗口 state 读取）──────────────
        self._timer = QTimer(self)
        self._timer.setInterval(1000)
        self._timer.timeout.connect(self._auto_refresh)
        self._timer.start()

    # ── 自动刷新 ─────────────────────────────────────────────────────────

    def _auto_refresh(self) -> None:
        mw = self.window()
        state = getattr(mw, "state", None)
        if state is not None:
            self.update_from_state(state)

    # ── 公共更新接口 ──────────────────────────────────────────────────────

    def update_from_state(self, state) -> None:
        """从 AppState 对象读取数据并刷新所有指标。"""
        from datetime import datetime

        # 实验识别
        sim = getattr(state, "sim", None)
        run = getattr(state, "last_run", None)

        if sim is not None:
            self._card_rmax.set_value(f"{sim.r_max_true:.4g}")
            self._card_noise.set_value(f"{sim.noise_std:.4g}")
            self._card_npts.set_value(str(sim.n_points))
            self._card_xmin.set_value(f"{sim.x_min:.4g}")
            self._card_xmax.set_value(f"{sim.x_max:.4g}")

        if run is not None:
            pts = len(run.x) if run.x else 0
            self._card_points.set_value(str(pts) if pts else "—")

            if run.fit_kd is not None:
                self._card_kd.set_value(f"{run.fit_kd:.4g}", "accent")
                self._card_r2.set_value(
                    f"{run.fit_r_squared:.4f}",
                    "success" if run.fit_r_squared >= 0.95 else "warning",
                )
            else:
                self._card_kd.set_value("—", "text_muted")
                self._card_r2.set_value("—", "text_muted")

        self._ts_lbl.setText(datetime.now().strftime("%H:%M:%S"))

    def set_experiment(self, name: str, exp_id: str,
                       status: str = "draft") -> None:
        """更新左侧实验标识区。"""
        status_colors = {
            "draft":   PALETTE["text_muted"],
            "running": PALETTE["warning"],
            "done":    PALETTE["success"],
            "failed":  PALETTE["danger"],
        }
        color = status_colors.get(status, PALETTE["text_muted"])
        self._exp_name.setText(name)
        self._exp_id.setText(f"ID: {exp_id}")
        self._exp_status.setText(f"●  {status.upper()}")
        self._exp_status.setStyleSheet(
            f"color: {color}; font-size: 11px; font-weight: 600;"
        )


# ─────────────────────────────────────────────
#  Content area  (tab bar + page stack)
# ─────────────────────────────────────────────
class ContentArea(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet(f"background: {PALETTE['bg_main']};")

        vl = QVBoxLayout(self)
        vl.setContentsMargins(0, 0, 0, 0)
        vl.setSpacing(0)

        self.tab_bar = PageTabBar()
        vl.addWidget(self.tab_bar)

        sep = QFrame()
        sep.setFixedHeight(1)
        sep.setStyleSheet(f"background: {PALETTE['border']};")
        vl.addWidget(sep)

        self.stack = QStackedWidget()
        self.stack.setStyleSheet("background: transparent;")
        self.stack.addWidget(ExperimentSetupView())  # 0 – Plan
        self.stack.addWidget(InstructionsPage())      # 1 – Instructions
        self.stack.addWidget(RunView())               # 2 – Results
        self.stack.addWidget(AnalysisView())          # 3 – Details
        vl.addWidget(self.stack, 1)

        self.tab_bar.page_changed.connect(self.stack.setCurrentIndex)

        # ── 底部固定数据面板（不属于任何标签页）──────────────────────
        self.data_panel = DataPanel()
        vl.addWidget(self.data_panel)


# ─────────────────────────────────────────────
#  ProjectView  – top-level widget
# ─────────────────────────────────────────────
class ProjectView(QWidget):
    """
    实验管理主界面。
    左侧固定侧边栏（保存 / 关闭 / 实验列表 / 新建实验）。
    右侧内容区在 Plan / Instructions / Results / Details 四页间切换；
    切换时侧边栏完全不受影响。
    """

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Experiment Manager")
        self.setMinimumSize(960, 640)
        self.setStyleSheet(f"background: {PALETTE['bg_main']};")

        lo = QHBoxLayout(self)
        lo.setContentsMargins(0, 0, 0, 0)
        lo.setSpacing(0)

        self.sidebar = Sidebar()
        self.content = ContentArea()

        sep = QFrame()
        sep.setFrameShape(QFrame.VLine)
        sep.setFixedWidth(1)
        sep.setStyleSheet(f"background: {PALETTE['border']}; border: none;")

        lo.addWidget(self.sidebar)
        lo.addWidget(sep)
        lo.addWidget(self.content, 1)

        self.sidebar.save_btn.clicked.connect(self._on_save)
        self.sidebar.close_btn.clicked.connect(self._on_close)
        self.sidebar.new_btn.clicked.connect(self._on_new_experiment)

    def _on_save(self) -> None:
        print("[ProjectView] Save triggered")

    def _on_close(self) -> None:
        print("[ProjectView] Close triggered")

    def _on_new_experiment(self) -> None:
        print("[ProjectView] New experiment triggered")


# ─────────────────────────────────────────────
#  Standalone preview
# ─────────────────────────────────────────────
if __name__ == "__main__":
    import sys
    from PySide6.QtWidgets import QApplication

    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    w = ProjectView()
    w.show()
    sys.exit(app.exec())