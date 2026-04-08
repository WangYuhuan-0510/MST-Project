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
from mst.core.data_manager import DataManager
from mst.core.experiment_schema import list_experiment_types, normalize_experiment_type_id
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
        self.current_project_dir: Path | None = None
        self.current_experiment_id: str | None = None
        self.current_experiment_path: str | None = None
        self.current_excitation: str = "RED"
        self.current_experiment_type: str = "Pre-test"
        self.current_experiment_type_id: str = "pre_test"
        self._experiment_status_by_id: dict[str, str] = {}

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
            self.project_view.sidebar.experiment_selected.connect(self._on_experiment_selected)
        return self.project_view

    def _experiment_dir(self, experiment_id: str) -> Path | None:
        if self.current_project_dir is None:
            return None
        return self.current_project_dir / str(experiment_id).strip()

    def _experiment_h5_path(self, experiment_id: str) -> Path | None:
        exp_dir = self._experiment_dir(experiment_id)
        if exp_dir is None:
            return None
        return exp_dir / "experiment.h5"

    def _refresh_sidebar_experiments(self) -> None:
        if self.project_view is None or self.current_project_dir is None:
            return

        experiments: list[tuple[str, str, str]] = []
        for child in sorted(self.current_project_dir.iterdir(), key=lambda p: p.name.lower()):
            if not child.is_dir():
                continue
            h5_path = child / "experiment.h5"
            if not h5_path.exists():
                continue
            exp = Experiment.load_h5(h5_path)
            exp_id = str(exp.id or child.name)
            exp_name = str(exp.name or child.name)
            status = self._experiment_status_by_id.get(exp_id, "draft")
            experiments.append((exp_id, exp_name, status))

        self.project_view.set_experiments(experiments)
        if self.current_experiment_id:
            self.project_view.select_experiment(self.current_experiment_id)

    def _load_experiment_from_id(self, experiment_id: str) -> None:
        if self.project_view is None:
            return
        h5_path = self._experiment_h5_path(experiment_id)
        if h5_path is None or not h5_path.exists():
            QMessageBox.warning(self, "打开提示", f"未找到实验文件：\n{h5_path}")
            return
        self.current_experiment_id = str(experiment_id).strip()
        self.current_experiment_path = str(h5_path)
        self._load_experiment_into_ui(str(h5_path), self.project_view)
        self._refresh_sidebar_experiments()

    def _on_experiment_selected(self, experiment_id: str) -> None:
        selected = str(experiment_id or "").strip()
        if not selected:
            return
        if selected == (self.current_experiment_id or "") and self.current_experiment_path and Path(self.current_experiment_path).exists():
            return
        self._load_experiment_from_id(selected)

    # ── Slots ─────────────────────────────────────────────────────────────

    def _on_session_opened(self, experiment_path: str) -> None:
        """WelcomeView 选择/创建文件 → 进入向导。"""
        self.current_project_dir = Path(experiment_path).parent
        self.current_experiment_path = experiment_path
        loaded = Experiment.load_h5(experiment_path)
        self.current_experiment_id = loaded.id
        self.setWindowTitle(f"PW-MST  —  {experiment_path}")
        self.wizard.reset()
        self._stack.setCurrentIndex(1)

    def _on_wizard_completed(self, excitation: str, experiment_type_id: str) -> None:
        """向导完成 → 进入主界面。"""
        self.current_excitation = excitation
        self.current_experiment_type_id = normalize_experiment_type_id(experiment_type_id)

        type_items = list_experiment_types()
        name_by_id = {t.get("id"): t.get("name", "") for t in type_items}
        self.current_experiment_type = str(name_by_id.get(self.current_experiment_type_id, "Pre-test"))

        self.state.current_session.experiment_type_id = self.current_experiment_type_id

        pv = self._ensure_project_view()
        self._refresh_sidebar_experiments()
        setup_view = pv.content.stack.widget(0)
        run_view = pv.content.stack.widget(2)
        if hasattr(setup_view, "set_experiment_type"):
            setup_view.set_experiment_type(self.current_experiment_type_id)

        if self.current_project_dir is not None and hasattr(run_view, "data_manager"):
            dm: DataManager = run_view.data_manager
            dm.bind_experiment_by_id(
                self.current_experiment_id or "",
                project_dir=self.current_project_dir,
                name=Path(self.current_experiment_path or "experiment.h5").stem,
            )
            self.current_experiment_path = dm.current_h5_path

        self._stack.setCurrentIndex(2)

        path = self.current_experiment_path
        if path and Path(path).exists():
            self._load_experiment_into_ui(path, pv)

    def _go_welcome(self) -> None:
        """返回欢迎页。"""
        self.current_project_dir = None
        self.current_experiment_id = None
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
            dm: DataManager = run_view.data_manager
            if self.current_project_dir is None:
                raise ValueError("当前没有项目目录。")
            if self.current_experiment_id is None:
                self.current_experiment_id = dm.current_experiment_id or Experiment.load_h5(self.current_experiment_path).id

            dm.bind_experiment_by_id(
                self.current_experiment_id,
                project_dir=self.current_project_dir,
                name=Path(self.current_experiment_path or "experiment.h5").stem,
            )
            self.current_experiment_path = dm.current_h5_path
            setup_params = setup_view.get_params() if hasattr(setup_view, "get_params") else {}

            exp = Experiment.from_ui(
                name=Path(self.current_experiment_path).parent.name,
                setup_params=setup_params,
                excitation=self.current_excitation,
                experiment_type=self.current_experiment_type,
                experiment_type_id=self.current_experiment_type_id,
                experiment_id=self.current_experiment_id,
            )
            exp.capture_from_run_view(run_view)
            exp.save_h5(self.current_experiment_path)

            QMessageBox.information(self, "保存成功", f"实验已保存到：\n{self.current_experiment_path}")
            self._experiment_status_by_id[exp.id] = "done"
            self._refresh_sidebar_experiments()
        except Exception as e:
            QMessageBox.critical(self, "保存失败", f"保存过程中发生错误：\n{e}")

    def _on_new_exp(self) -> None:
        if self.project_view and self.current_project_dir is not None:
            self.current_experiment_id = Experiment().id
            exp_dir = self.current_project_dir / self.current_experiment_id
            self.current_experiment_path = str(exp_dir / "experiment.h5")
            self.project_view.content.stack.setCurrentIndex(0)
            setup_view = self.project_view.content.stack.widget(0)
            run_view = self.project_view.content.stack.widget(2)
            if hasattr(run_view, "data_manager"):
                run_view.data_manager.bind_experiment_by_id(
                    self.current_experiment_id,
                    project_dir=self.current_project_dir,
                    name=exp_dir.name,
                )
            self._experiment_status_by_id[self.current_experiment_id] = "draft"
            self._refresh_sidebar_experiments()
            self.project_view.select_experiment(self.current_experiment_id)
            self.state.current_session.setup_data = {}
            if hasattr(setup_view, "set_experiment_type"):
                setup_view.set_experiment_type(self.current_experiment_type_id)

    def _load_experiment_into_ui(self, path: str, pv: ProjectView) -> None:
        try:
            exp = Experiment.load_h5(path)
            setup_view = pv.content.stack.widget(0)
            run_view = pv.content.stack.widget(2)

            loaded_type_id = normalize_experiment_type_id(
                str(exp.metadata.get("experiment_type_id") or exp.metadata.get("experiment_type") or self.current_experiment_type_id)
            )
            self.current_experiment_type_id = loaded_type_id

            type_items = list_experiment_types()
            name_by_id = {t.get("id"): t.get("name", "") for t in type_items}
            self.current_experiment_type = str(name_by_id.get(loaded_type_id, self.current_experiment_type))

            self.state.current_session.experiment_type_id = loaded_type_id
            self.state.current_session.setup_data = dict(exp.setup_data or {})
            self.current_experiment_id = exp.id

            if hasattr(run_view, "clear_view_state"):
                run_view.clear_view_state()

            self._experiment_status_by_id[exp.id] = "done"

            if hasattr(run_view, "data_manager") and self.current_project_dir is not None:
                run_view.data_manager.bind_experiment(exp, base_dir=Path(path).parent)
                self.current_experiment_path = run_view.data_manager.current_h5_path

            if hasattr(setup_view, "set_experiment_type"):
                setup_view.set_experiment_type(loaded_type_id)
            exp.apply_to_setup_view(setup_view)

            if hasattr(run_view, "load_replay_file"):
                run_view.load_replay_file(path)
            else:
                exp.apply_to_run_view(run_view)

            self._refresh_sidebar_experiments()
            pv.select_experiment(exp.id)

            self.current_excitation = str(exp.metadata.get("excitation", self.current_excitation) or self.current_excitation)
            self.current_experiment_type = str(exp.metadata.get("experiment_type", self.current_experiment_type) or self.current_experiment_type)
        except Exception as e:
            QMessageBox.warning(self, "打开提示", f"实验文件已选中，但部分数据加载失败：\n{e}")
