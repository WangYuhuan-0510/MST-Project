"""
main_window.py
──────────────
应用程序主窗口。

页面流程：
  WelcomeView  →  SessionWizard  →  ProjectView
       ↑ Close/返回        ↑ Close/返回
"""
from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import QMainWindow, QStackedWidget, QMessageBox

from mst.core.app_state import AppState
from mst.core.experiments import Experiment
from .views.welcome_view import WelcomeView
from .views.session_wizard import SessionWizard
from .views.project_view import ProjectView


class MainWindow(QMainWindow):

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("PW-MST 实验控制平台")
        self.resize(1200, 800)

        self.state = AppState()
        self.current_experiment_path: str | None = None
        self.current_excitation: str = "RED"
        self.current_experiment_type: str = "Pre-test"

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

    def _on_session_opened(self, experiment_path: str) -> None:
        """WelcomeView 选择/创建文件 → 进入向导。"""
        self.current_experiment_path = experiment_path
        self.setWindowTitle(f"PW-MST  —  {experiment_path}")
        self.wizard.reset()
        self._stack.setCurrentIndex(1)

    def _on_wizard_completed(self, excitation: str, experiment: str) -> None:
        """向导完成 → 进入主界面。"""
        self.current_excitation = excitation
        self.current_experiment_type = experiment
        pv = self._ensure_project_view()
        self._stack.setCurrentIndex(2)

        path = self.current_experiment_path
        if path and Path(path).exists():
            self._load_experiment_into_ui(path, pv)

    def _go_welcome(self) -> None:
        """返回欢迎页。"""
        self.current_experiment_path = None
        self.setWindowTitle("PW-MST 实验控制平台")
        self._stack.setCurrentIndex(0)
        self.welcome_view._populate_recent()

    def _on_save(self) -> None:
        if self.project_view is None:
            QMessageBox.warning(self, "保存失败", "主界面尚未初始化，无法保存。")
            return
        if not self.current_experiment_path:
            QMessageBox.warning(self, "保存失败", "当前没有实验文件路径。")
            return

        try:
            setup_view = self.project_view.content.stack.widget(0)
            run_view = self.project_view.content.stack.widget(2)
            setup_params = setup_view.get_params() if hasattr(setup_view, "get_params") else {}

            exp = Experiment.from_ui(
                name=Path(self.current_experiment_path).stem,
                setup_params=setup_params,
                excitation=self.current_excitation,
                experiment_type=self.current_experiment_type,
            )
            exp.capture_from_run_view(run_view)
            exp.save_h5(self.current_experiment_path)

            QMessageBox.information(self, "保存成功", f"实验已保存到：\n{self.current_experiment_path}")
        except Exception as e:
            QMessageBox.critical(self, "保存失败", f"保存过程中发生错误：\n{e}")

    def _on_new_exp(self) -> None:
        if self.project_view:
            self.project_view.content.stack.setCurrentIndex(0)

    def _load_experiment_into_ui(self, path: str, pv: ProjectView) -> None:
        try:
            exp = Experiment.load_h5(path)
            setup_view = pv.content.stack.widget(0)
            run_view = pv.content.stack.widget(2)
            exp.apply_to_setup_view(setup_view)

            if hasattr(run_view, "load_replay_file"):
                run_view.load_replay_file(path)
            else:
                exp.apply_to_run_view(run_view)

            self.current_excitation = str(exp.metadata.get("excitation", self.current_excitation) or self.current_excitation)
            self.current_experiment_type = str(exp.metadata.get("experiment_type", self.current_experiment_type) or self.current_experiment_type)
        except Exception as e:
            QMessageBox.warning(self, "打开提示", f"实验文件已选中，但部分数据加载失败：\n{e}")
