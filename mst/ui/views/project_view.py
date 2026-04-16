"""
project_view.py
───────────────
实验管理主界面框架。
左侧固定侧边栏 + 右侧三标签页，切换页面时侧边栏保持不变。

页面映射
  Plan         →  ExperimentSetupView  (experiment_setup_view.py)
  Instructions →  InstructionsPage     (内联占位，可按需替换)
  Results      →  RunView              (run_view.py)
"""
from __future__ import annotations

from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QLabel, QPushButton,
    QStackedWidget, QFrame, QScrollArea, QSizePolicy, QSpacerItem,
    QGridLayout, QInputDialog,
)
from PySide6.QtCore import Qt, Signal, QTimer, QSize
from PySide6.QtGui import QPixmap

# ── 共享样式 ────────────────────────────────────────────────────────────────
from .ui_style import (
    PALETTE, SIDEBAR_W,
    label_style, section_label, divider,
)
from mst.core.experiment_schema import get_experiment_type_config, normalize_experiment_type_id

# ── 页面实现 ────────────────────────────────────────────────────────────────
from .experiment_setup_view import ExperimentSetupView   # Plan
from .run_view              import RunView               # Results
from .sidebar_experiment_item import ExperimentItem


# ─────────────────────────────────────────────
#  Sidebar: action button
# ─────────────────────────────────────────────
class ActionButton(QPushButton):
    def __init__(self, label: str, icon_char: str, danger: bool = False, parent=None):
        super().__init__(parent)
        color = PALETTE["danger"] if danger else PALETTE["text_secondary"]
        hover = PALETTE["danger"] if danger else PALETTE["text_primary"]
        border = PALETTE["danger"] if danger else PALETTE["border"]
        hover_border = PALETTE["danger"] if danger else PALETTE["accent"]
        self.setText(f"{icon_char}\n{label}")
        self.setFixedSize(84, 84)
        self.setCursor(Qt.PointingHandCursor)
        self.setStyleSheet(f"""
            QPushButton {{
                background: {PALETTE["bg_card"]};
                border: 1px solid {border};
                border-radius: 12px;
                color: {color};
                font-size: 13px;
                font-weight: 600;
                text-align: center;
                padding: 8px 6px;
                line-height: 1.4;
            }}
            QPushButton:hover {{
                background: {PALETTE["bg_hover"]};
                color: {hover};
                border-color: {hover_border};
            }}
            QPushButton:pressed {{
                background: {PALETTE["bg_active"]};
                border-color: {hover_border};
            }}
        """)


# ─────────────────────────────────────────────
#  Sidebar: experiment list item
# ─────────────────────────────────────────────


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
#  Tab bar  (Plan / Instructions / Results)
# ─────────────────────────────────────────────
class PageTabBar(QWidget):
    page_changed = Signal(int)
    TABS = ["Plan", "Instructions", "Results"]

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(52)
        self.setStyleSheet("background: transparent;")
        lo = QHBoxLayout(self)
        lo.setContentsMargins(0, 0, 0, 0)
        lo.setSpacing(8)
        self._buttons: list[QPushButton] = []
        self._current_idx = 0

        for i, name in enumerate(self.TABS):
            btn = QPushButton(f"{i + 1}  {name}")
            btn.setCheckable(True)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setFixedHeight(32)
            btn.setStyleSheet(f"""
                QPushButton {{
                    background: {PALETTE["bg_main"]};
                    border: 1px solid {PALETTE["border"]};
                    border-radius: 6px;
                    color: {PALETTE["text_secondary"]};
                    font-size: 13px;
                    font-weight: 600;
                    padding: 0 14px;
                    letter-spacing: 0.2px;
                }}
                QPushButton:hover {{
                    background: {PALETTE["bg_hover"]};
                    color: {PALETTE["text_primary"]};
                    border: 1px solid {PALETTE["accent"]};
                }}
                QPushButton:checked {{
                    background: {PALETTE["bg_active"]};
                    color: {PALETTE["accent"]};
                    font-weight: 600;
                    border: 1px solid {PALETTE["accent"]};
                }}
            """)
            btn.clicked.connect(lambda _, x=i: self._select(x))
            self._buttons.append(btn)
            lo.addWidget(btn)

        self._select(0)

    def _select(self, idx: int) -> None:
        self._current_idx = idx
        for i, btn in enumerate(self._buttons):
            btn.setChecked(i == idx)
        self.page_changed.emit(idx)

    def current_index(self) -> int:
        return self._current_idx


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
    experiment_selected = Signal(str)
    experiment_rename_requested = Signal(str)
    experiment_delete_requested = Signal(str)

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

        actions_row = QHBoxLayout()
        actions_row.setContentsMargins(6, 0, 6, 0)
        actions_row.setSpacing(10)
        self.save_btn  = ActionButton("Save",  "💾", danger=False)
        self.close_btn = ActionButton("Close", "✕",  danger=True)
        actions_row.addWidget(self.close_btn)
        actions_row.addWidget(self.save_btn)
        root.addLayout(actions_row)

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
        self._exp_container = QWidget()
        self._exp_layout = QVBoxLayout(self._exp_container)
        self._exp_layout.setContentsMargins(0, 0, 0, 0)
        self._exp_layout.setSpacing(8)
        root.addWidget(self._exp_container)

        root.addStretch()
        self.new_btn = NewExperimentButton()
        root.addWidget(self.new_btn)

    def _select_exp(self, selected: ExperimentItem) -> None:
        for btn in self._exp_buttons:
            btn.setChecked(btn is selected)
        if selected.experiment_id:
            self.experiment_selected.emit(selected.experiment_id)

    def set_experiments(self, experiments: list[object]) -> None:
        while self._exp_layout.count():
            item = self._exp_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        self._exp_buttons = []
        for item in experiments:
            btn = ExperimentItem(
                item.display_name,
                item.status,
                experiment_id=item.experiment_id,
                experiment_type_id=item.experiment_type_id,
                experiment_type_name=item.experiment_type_name,
                order_index=item.order_index,
                is_dirty=getattr(item, "is_dirty", False),
            )
            btn.clicked.connect(lambda _, b=btn: self._select_exp(b))
            btn.rename_requested.connect(self.experiment_rename_requested.emit)
            btn.delete_requested.connect(self.experiment_delete_requested.emit)
            self._exp_buttons.append(btn)
            self._exp_layout.addWidget(btn)

        if self._exp_buttons:
            self._exp_buttons[0].setChecked(True)

    def update_experiment_item(
        self,
        experiment_id: str,
        *,
        name: str,
        status: str,
        experiment_type_id: str,
        experiment_type_name: str,
        order_index: int,
        is_dirty: bool = False,
    ) -> bool:
        wanted = str(experiment_id or "").strip()
        for btn in self._exp_buttons:
            if btn.experiment_id != wanted:
                continue
            btn.update_display(
                name=name,
                status=status,
                experiment_type_id=experiment_type_id,
                experiment_type_name=experiment_type_name,
                order_index=order_index,
                is_dirty=is_dirty,
            )
            return True
        return False

    def select_experiment(self, experiment_id: str) -> None:
        wanted = str(experiment_id or "").strip()
        for btn in self._exp_buttons:
            btn.setChecked(btn.experiment_id == wanted)


# ─────────────────────────────────────────────
#  Bottom Data Panel  (固定，不随页面切换变化)
# ─────────────────────────────────────────────

def _vsep() -> QFrame:
    f = QFrame()
    f.setFrameShape(QFrame.VLine)
    f.setFixedWidth(1)
    f.setStyleSheet(f"background: {PALETTE['border']}; border: none;")
    return f


class _InfoBlock(QWidget):
    """
    单个信息块：图标 + 小标题（灰）+ 粗体数值，无边框。
    参照截图中的横排展示风格。
    """
    def __init__(self, icon: str, label: str, value: str = "—",
                 min_w: int = 140, parent=None):
        super().__init__(parent)
        self.setMinimumWidth(min_w)
        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
        self.setStyleSheet("background: transparent;")

        lo = QHBoxLayout(self)
        lo.setContentsMargins(12, 0, 12, 0)
        lo.setSpacing(10)

        icon_lbl = QLabel(icon)
        icon_lbl.setStyleSheet(
            f"color: {PALETTE['text_muted']}; font-size: 18px;"
        )
        icon_lbl.setFixedWidth(22)
        icon_lbl.setAlignment(Qt.AlignCenter)

        text_blk = QVBoxLayout()
        text_blk.setSpacing(1)

        self._label_lbl = QLabel(label)
        self._label_lbl.setStyleSheet(
            f"color: {PALETTE['text_muted']}; font-size: 10px; font-weight: 500;"
            " letter-spacing: 0.3px;"
        )

        self._value_lbl = QLabel(value)
        self._value_lbl.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self._value_lbl.setMinimumWidth(0)
        self._value_lbl.setWordWrap(False)
        self._value_lbl.setStyleSheet(
            f"color: {PALETTE['text_primary']}; font-size: 13px; font-weight: 700;"
        )

        text_blk.addWidget(self._label_lbl)
        text_blk.addWidget(self._value_lbl)

        lo.addWidget(icon_lbl)
        lo.addLayout(text_blk, 1)

    def set_value(self, value: str) -> None:
        self._value_lbl.setText(value)

    def set_label(self, label: str) -> None:
        self._label_lbl.setText(label)


class DataPanel(QFrame):
    """
    底部固定数据面板。
    显示：分析物种类+浓度 / 配体种类+最高浓度 / 缓冲液+毛细管 / 激发光+MST功率。
    不属于任何标签页，页面切换时完全不受影响。
    每秒自动从 ExperimentSetupView.get_params() 读取最新参数。
    """
    PANEL_H = 72

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(self.PANEL_H)
        self.setStyleSheet(
            f"background: {PALETTE['bg_sidebar']};"
            f"border-top: 1px solid {PALETTE['border']};"
        )

        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── 六个信息块，用竖分隔线隔开；按内容长度自适应宽度 ─────────────
        self._blk_target = _InfoBlock("◕", "分析物", "—", 110)
        self._blk_ligand = _InfoBlock("◆", "配体", "—", 110)
        self._blk_buf = _InfoBlock("⬛", "缓冲液", "—", 300)
        self._blk_cap = _InfoBlock("▮", "毛细管", "—", 220)
        self._blk_excit = _InfoBlock("☀", "激发光功率", "—", 280)
        self._blk_mst = _InfoBlock("✳", "MST 功率", "—", 90)

        blocks = [
            self._blk_target,
            self._blk_ligand,
            self._blk_buf,
            self._blk_cap,
            self._blk_excit,
            self._blk_mst,
        ]

        for blk in blocks:
            root.addWidget(blk, 0)
            root.addWidget(_vsep())

        # 移除最后一根多余的分隔线
        item = root.itemAt(root.count() - 1)
        if item and item.widget():
            item.widget().hide()

        # ── 每秒刷新 ──────────────────────────────────────────────
        self._timer = QTimer(self)
        self._timer.setInterval(1000)
        self._timer.timeout.connect(self._auto_refresh)
        self._timer.start()

    # ── 内部刷新 ─────────────────────────────────────────────────────────

    def _auto_refresh(self) -> None:
        """从主窗口的 ContentArea.stack[0] (ExperimentSetupView) 读取最新参数。"""
        try:
            # DataPanel → ContentArea → ProjectView → MainWindow
            content_area = self.parent()          # ContentArea
            setup: ExperimentSetupView = content_area.stack.widget(0)
            params = setup.get_params()
            self.update_from_params(params)
        except Exception:
            pass

    # ── 公共更新接口 ──────────────────────────────────────────────────────

    def update_from_params(self, params: dict) -> None:
        """根据 ExperimentSetupView.get_params() 返回值刷新所有块。"""
        target  = params.get("target", "—")
        t_assay = params.get("target_assay", "—") or "—"
        self._blk_target.set_label(target)
        self._blk_target.set_value(t_assay)

        ligand   = params.get("ligand", "—")
        hi_conc  = params.get("hi_conc", "—") or "—"
        self._blk_ligand.set_label(ligand)
        self._blk_ligand.set_value(hi_conc + " µM" if hi_conc != "—" else "—")

        buf = params.get("buffer", "—") or "—"
        self._blk_buf.set_label("缓冲液")
        self._blk_buf.set_value(buf)

        cap = params.get("capillary", "—") or "—"
        # 只显示型号关键词
        cap_short = cap.replace("Monolith ", "").replace(" Capillary", "")
        self._blk_cap.set_label("毛细管")
        self._blk_cap.set_value(cap_short)

        auto = params.get("excitation_auto", True)
        ex_pct = params.get("excitation_pct", 20)
        excitation = str(params.get("excitation", "RED") or "RED").upper()
        ex_text = f"Auto-detect  {ex_pct} % {excitation}" if auto else f"{ex_pct} % {excitation}"
        self._blk_excit.set_label("激发光功率")
        self._blk_excit.set_value(ex_text)

        mst = params.get("mst_power", "—")
        self._blk_mst.set_label("MST 功率")
        self._blk_mst.set_value(mst if mst else "—")


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

        header_row = QHBoxLayout()
        header_row.setContentsMargins(28, 4, 28, 4)
        header_row.setSpacing(16)

        self.page_title = QLabel("")
        self.page_title.setStyleSheet(
            f"color: {PALETTE['accent']};"
            "font-size: 24px; font-weight: 800;"
            "padding: 0px;"
            "letter-spacing: 0.2px;"
        )
        header_row.addWidget(self.page_title, 0, Qt.AlignVCenter | Qt.AlignLeft)
        # 让 tab 组落在中间偏左，而不是贴到最右侧
        header_row.addSpacing(120)

        self.tab_bar = PageTabBar()
        header_row.addWidget(self.tab_bar, 0, Qt.AlignVCenter | Qt.AlignLeft)
        header_row.addStretch()
        vl.addLayout(header_row)

        sep = QFrame()
        sep.setFixedHeight(1)
        sep.setStyleSheet(f"background: {PALETTE['border']};")
        vl.addWidget(sep)

        body = QHBoxLayout()
        body.setContentsMargins(0, 0, 0, 0)
        body.setSpacing(0)

        self.stack = QStackedWidget()
        self.stack.setStyleSheet("background: transparent;")
        self.stack.addWidget(ExperimentSetupView())  # 0 – Plan
        self.stack.addWidget(InstructionsPage())      # 1 – Instructions
        self.stack.addWidget(RunView())               # 2 – Results
        body.addWidget(self.stack, 1)

        # 右侧独立空白区：与实验设置同层并排，不覆盖内容
        self.right_blank_panel = QFrame()
        self.right_blank_panel.setFixedWidth(260)
        self.right_blank_panel.setStyleSheet(
            f"background: {PALETTE['bg_sidebar']};"
            f"border-left: 1px solid {PALETTE['border']};"
            "border-top: none; border-right: none; border-bottom: none;"
        )
        body.addWidget(self.right_blank_panel)
        vl.addLayout(body, 1)

        self.tab_bar.page_changed.connect(self._on_page_changed)

        # ── 底部固定数据面板（不属于任何标签页）──────────────────────
        self.data_panel = DataPanel()
        vl.addWidget(self.data_panel)

        self._on_page_changed(self.tab_bar.current_index())

    def _on_page_changed(self, idx: int) -> None:
        self.stack.setCurrentIndex(idx)
        self.page_title.setText(f"{idx + 1}. {self.tab_bar.TABS[idx]}")


# ─────────────────────────────────────────────
#  ProjectView  – top-level widget
# ─────────────────────────────────────────────
class ProjectView(QWidget):
    """
    实验管理主界面。
    左侧固定侧边栏（保存 / 关闭 / 实验列表 / 新建实验）。
    右侧内容区在 Plan / Instructions / Results 三页间切换；
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

    def set_experiments(self, experiments: list[tuple[str, str, str, str, str, int]]) -> None:
        self.sidebar.set_experiments(experiments)

    def select_experiment(self, experiment_id: str) -> None:
        self.sidebar.select_experiment(experiment_id)

    def prompt_rename(self, current_name: str) -> tuple[str, bool]:
        name, ok = QInputDialog.getText(self, "修改实验名称", "实验名称：", text=current_name)
        return str(name).strip(), bool(ok)

    def update_metadata(self, metadata: dict) -> None:
        if not isinstance(metadata, dict):
            return

        params = {
            "target": str(metadata.get("target", "?") or "?"),
            "target_assay": str(metadata.get("target_assay", "?") or "?"),
            "ligand": str(metadata.get("ligand", "?") or "?"),
            "hi_conc": str(metadata.get("hi_conc", "?") or "?"),
            "buffer": str(metadata.get("buffer", "?") or "?"),
            "capillary": str(metadata.get("capillary", "?") or "?"),
            "excitation": str(metadata.get("excitation", "RED") or "RED"),
            "experiment_type": str(metadata.get("experiment_type", "Pre-test") or "Pre-test"),
            "excitation_auto": str(metadata.get("excitation_auto", "True") or "True").lower() in {"1", "true", "yes", "on"},
            "excitation_pct": metadata.get("excitation_pct", metadata.get("led_power", 20)),
            "mst_power": str(metadata.get("mst_power", "?") or "?"),
        }
        self.content.data_panel.update_from_params(params)

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