"""
main_window.py
──────────────
应用程序主窗口。
导航由 ProjectView 内置的侧边栏 + 标签页完整处理，
MainWindow 只负责窗口初始化和全局状态注入。
"""
from __future__ import annotations

from PySide6.QtWidgets import QMainWindow

from mst.core.app_state import AppState
from .views.project_view import ProjectView


class MainWindow(QMainWindow):
    """
    应用程序主窗口。

    页面结构完全由 ProjectView 管理：
      侧边栏  — 实验列表 / 保存 / 关闭 / 新建实验
      标签页  — Plan (ExperimentSetupView)
              / Instructions
              / Results (RunView)
              / Details (AnalysisView)
    """

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("PW-MST 实验控制平台")
        self.resize(1200, 800)

        # ── 全局应用状态，供各 View 通过 self.window().state 访问 ──
        self.state = AppState()

        # ── ProjectView 作为唯一中心 widget ──────────────────────────
        self.project_view = ProjectView(self)
        self.setCentralWidget(self.project_view)

        # ── 将侧边栏的 Save / Close / New 信号接入主窗口逻辑 ─────────
        self.project_view.sidebar.save_btn.clicked.connect(self._on_save)
        self.project_view.sidebar.close_btn.clicked.connect(self._on_close)
        self.project_view.sidebar.new_btn.clicked.connect(self._on_new_experiment)

    # ── Slots ─────────────────────────────────────────────────────────────

    def _on_save(self) -> None:
        """保存当前实验状态（占位，接入持久化层后实现）。"""
        print("[MainWindow] Save triggered")

    def _on_close(self) -> None:
        """关闭当前实验并返回空白状态（占位）。"""
        print("[MainWindow] Close triggered")

    def _on_new_experiment(self) -> None:
        """新建实验：重置 state 并跳转到 Plan 页（占位）。"""
        print("[MainWindow] New experiment triggered")
        # 切换到 Plan 标签页（索引 0）
        self.project_view.content.stack.setCurrentIndex(0)