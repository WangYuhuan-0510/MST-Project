"""
main_window.py
──────────────
应用程序主窗口。
启动时显示 WelcomeView，选择/创建文件后切换到 ProjectView。
"""
from __future__ import annotations

from PySide6.QtWidgets import QMainWindow, QStackedWidget

from mst.core.app_state import AppState
from .views.welcome_view import WelcomeView
from .views.project_view import ProjectView


class MainWindow(QMainWindow):
    """
    应用程序主窗口。

    页面切换逻辑：
      WelcomeView  —→  (选择/创建 .moc)  —→  ProjectView

    ProjectView 内部继续管理：
      侧边栏  — 实验列表 / 保存 / 关闭 / 新建实验
      标签页  — 实验设置 / 说明 / 结果 / 分析
    """

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("PW-MST 实验控制平台")
        self.resize(1200, 800)

        # ── 全局应用状态，供各 View 通过 self.window().state 访问 ──
        self.state = AppState()
        self.current_moc: str | None = None   # 当前打开的 .moc 文件路径

        # ── 堆叠页面：0=欢迎页  1=主界面 ─────────────────────────────
        self._stack = QStackedWidget(self)
        self.setCentralWidget(self._stack)

        # 欢迎页
        self.welcome_view = WelcomeView()
        self.welcome_view.session_opened.connect(self._on_session_opened)
        self._stack.addWidget(self.welcome_view)   # index 0

        # 主界面（延迟到首次打开文件时才创建，节省启动时间）
        self.project_view: ProjectView | None = None

        # 默认显示欢迎页
        self._stack.setCurrentIndex(0)

    # ── 私有方法 ──────────────────────────────────────────────────────────────

    def _ensure_project_view(self) -> ProjectView:
        """首次调用时创建 ProjectView 并接入信号。"""
        if self.project_view is None:
            self.project_view = ProjectView(self)
            self._stack.addWidget(self.project_view)  # index 1

            self.project_view.sidebar.save_btn.clicked.connect(self._on_save)
            self.project_view.sidebar.close_btn.clicked.connect(self._on_close)
            self.project_view.sidebar.new_btn.clicked.connect(self._on_new_experiment)
        return self.project_view

    # ── Slots ─────────────────────────────────────────────────────────────────

    def _on_session_opened(self, moc_path: str) -> None:
        """WelcomeView 发出信号后，切换到 ProjectView。"""
        self.current_moc = moc_path
        self.setWindowTitle(f"PW-MST  —  {moc_path}")

        pv = self._ensure_project_view()
        # 可在此将 moc_path 写入 state，供持久化层使用
        if hasattr(self.state, "moc_path"):
            self.state.moc_path = moc_path

        self._stack.setCurrentWidget(pv)

    def _on_save(self) -> None:
        """保存当前实验状态（占位，接入持久化层后实现）。"""
        print(f"[MainWindow] Save → {self.current_moc}")

    def _on_close(self) -> None:
        """关闭当前实验，返回欢迎页。"""
        self.current_moc = None
        self.setWindowTitle("PW-MST 实验控制平台")
        self._stack.setCurrentIndex(0)
        # 刷新最近文件列表
        self.welcome_view._populate_recent()

    def _on_new_experiment(self) -> None:
        """新建实验：跳转到 Plan 标签页（索引 0）。"""
        if self.project_view:
            self.project_view.content.stack.setCurrentIndex(0)