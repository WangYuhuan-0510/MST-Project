"""
main_window.py
──────────────
应用程序主窗口。

页面流程：
  WelcomeView  →  SessionWizard  →  ProjectView
       ↑ Close/返回        ↑ Close/返回
"""
from __future__ import annotations

from PySide6.QtWidgets import QMainWindow, QStackedWidget

from mst.core.app_state import AppState
from .views.welcome_view   import WelcomeView
from .views.session_wizard import SessionWizard
from .views.project_view   import ProjectView


class MainWindow(QMainWindow):

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("PW-MST 实验控制平台")
        self.resize(1200, 800)

        self.state = AppState()
        self.current_moc: str | None = None

        # ── 堆叠页面 ──────────────────────────────────────────────────────
        self._stack = QStackedWidget(self)
        self.setCentralWidget(self._stack)

        # index 0 — 欢迎页
        self.welcome_view = WelcomeView()
        self.welcome_view.session_opened.connect(self._on_session_opened)
        self._stack.addWidget(self.welcome_view)

        # index 1 — 向导
        self.wizard = SessionWizard()
        self.wizard.wizard_completed.connect(self._on_wizard_completed)
        self.wizard.close_requested.connect(self._go_welcome)
        self._stack.addWidget(self.wizard)

        # index 2 — 主界面（首次选完实验类型后懒加载）
        self.project_view: ProjectView | None = None

        self._stack.setCurrentIndex(0)

    # ── 懒加载 ProjectView ────────────────────────────────────────────────

    def _ensure_project_view(self) -> ProjectView:
        if self.project_view is None:
            self.project_view = ProjectView(self)
            self._stack.addWidget(self.project_view)  # index 2
            self.project_view.sidebar.save_btn.clicked.connect(self._on_save)
            self.project_view.sidebar.close_btn.clicked.connect(self._go_welcome)
            self.project_view.sidebar.new_btn.clicked.connect(self._on_new_exp)
        return self.project_view

    # ── Slots ─────────────────────────────────────────────────────────────

    def _on_session_opened(self, moc_path: str) -> None:
        """WelcomeView 选择/创建文件 → 进入向导。"""
        self.current_moc = moc_path
        self.setWindowTitle(f"PW-MST  —  {moc_path}")
        self.wizard.reset()
        self._stack.setCurrentIndex(1)          # 切换到向导页

    def _on_wizard_completed(self, excitation: str, experiment: str) -> None:
        """向导完成 → 进入主界面。"""
        print(f"[MainWindow] excitation={excitation}  experiment={experiment}")
        pv = self._ensure_project_view()
        self._stack.setCurrentIndex(2)

    def _go_welcome(self) -> None:
        """返回欢迎页。"""
        self.current_moc = None
        self.setWindowTitle("PW-MST 实验控制平台")
        self._stack.setCurrentIndex(0)
        self.welcome_view._populate_recent()

    def _on_save(self) -> None:
        print(f"[MainWindow] Save → {self.current_moc}")

    def _on_new_exp(self) -> None:
        if self.project_view:
            self.project_view.content.stack.setCurrentIndex(0)