"""
main_window.py
──────────────
应用程序主窗口。

页面流程：
  WelcomeView  →  SessionWizard  →  ProjectView
       ↑ Close/返回        ↑ Close/返回
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
import shutil

from PySide6.QtWidgets import QMainWindow, QStackedWidget, QMessageBox


_EDIT_UNLOCK_TITLE = "修改数据确认"
_EDIT_UNLOCK_TEXT = "修改 Plan 数据将重新标记当前实验为未保存状态，是否继续？"


from mst.core.app_state import AppState
from mst.core.data_manager import DataManager
from mst.core.experiment_schema import default_setup_data, get_experiment_type_config, list_experiment_types, normalize_experiment_type_id
from mst.core.experiments import Experiment
from .views.welcome_view import WelcomeView
from .views.session_wizard import SessionWizard
from .views.project_view import ProjectView


@dataclass
class ExperimentSessionState:
    experiment_id: str
    display_name: str = "experiment"
    excitation: str = "RED"
    experiment_type_id: str = "pre_test"
    experiment_type_name: str = "Pre-test"
    plan_snapshot: dict[str, Any] = field(default_factory=dict)
    is_dirty: bool = False
    lifecycle_status: str = "draft"


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
        self._experiment_order_by_id: dict[str, int] = {}
        self._next_experiment_order: int = 1
        self._pending_new_experiment_id: str | None = None
        self._plan_snapshot_by_experiment_key: dict[str, dict] = {}
        self._experiment_display_name_by_id: dict[str, str] = {}
        self._session_state_by_experiment_id: dict[str, ExperimentSessionState] = {}
        self._base_window_title = "PW-MST 实验控制平台"

        # ── 堆叠页面 ──────────────────────────────────────────────────────
        self._stack = QStackedWidget(self)
        self.setCentralWidget(self._stack)

        # index 0 — 欢迎页
        self.welcome_view = WelcomeView()
        self.welcome_view.session_opened.connect(self._on_session_opened)
        self.welcome_view.new_experiment_requested.connect(self._on_new_experiment_requested)
        self._stack.addWidget(self.welcome_view)

        # index 1 — 向导
        self.wizard = SessionWizard()
        self.wizard.wizard_completed.connect(self._on_wizard_completed)
        self.wizard.close_requested.connect(self._go_welcome)
        self._stack.addWidget(self.wizard)

        # index 2 — 主界面（首次选完实验类型后懒加载）
        self.project_view: ProjectView | None = None

        self._stack.setCurrentIndex(0)
        self._refresh_window_title()

    # ── 懒加载 ProjectView ────────────────────────────────────────────────

    def _ensure_project_view(self) -> ProjectView:
        if self.project_view is None:
            self.project_view = ProjectView(self)
            self._stack.addWidget(self.project_view)  # index 2
            self.project_view.sidebar.save_btn.clicked.connect(self._on_save)
            self.project_view.sidebar.close_btn.clicked.connect(self._go_welcome)
            self.project_view.sidebar.new_btn.clicked.connect(self._on_new_exp)
            self.project_view.sidebar.experiment_selected.connect(self._on_experiment_selected)
            self.project_view.sidebar.experiment_rename_requested.connect(self._on_experiment_rename_requested)
            self.project_view.sidebar.experiment_delete_requested.connect(self._on_experiment_delete_requested)
            self.project_view.content.tab_bar.page_changed.connect(self._on_project_tab_changed)
            self._bind_plan_autosave()
        return self.project_view

    def _ensure_session_state(self, experiment_id: str, *, display_name: str | None = None) -> ExperimentSessionState:
        exp_id = str(experiment_id or "").strip()
        if not exp_id:
            raise ValueError("experiment_id is required")
        state = self._session_state_by_experiment_id.get(exp_id)
        if state is None:
            state = ExperimentSessionState(
                experiment_id=exp_id,
                display_name=str(display_name or self._experiment_display_name_by_id.get(exp_id) or "experiment"),
                excitation=self.current_excitation,
                experiment_type_id=self.current_experiment_type_id,
                experiment_type_name=self.current_experiment_type,
            )
            self._session_state_by_experiment_id[exp_id] = state
        elif display_name:
            state.display_name = str(display_name)
        return state

    def _sync_current_session_state(self) -> None:
        if not self.current_experiment_id:
            return
        state = self._ensure_session_state(
            self.current_experiment_id,
            display_name=self._experiment_display_name_by_id.get(self.current_experiment_id, "experiment"),
        )
        state.excitation = self.current_excitation
        state.experiment_type_id = self.current_experiment_type_id
        state.experiment_type_name = self.current_experiment_type

    def _apply_session_state(self, state: ExperimentSessionState) -> None:
        self.current_excitation = str(state.excitation or "RED")
        self.current_experiment_type_id = normalize_experiment_type_id(state.experiment_type_id or "pre_test")
        self.current_experiment_type = str(
            state.experiment_type_name
            or get_experiment_type_config(self.current_experiment_type_id).get("name")
            or "Pre-test"
        )

    def _any_dirty(self) -> bool:
        return any(state.is_dirty for state in self._session_state_by_experiment_id.values())

    def _refresh_window_title(self) -> None:
        title = self._base_window_title
        if self._any_dirty():
            title = f"* {title}"
        self.setWindowTitle(title)

    def _set_base_window_title_for_path(self, path: str | None) -> None:
        if path:
            self._base_window_title = f"PW-MST-{path}"
        else:
            self._base_window_title = "PW-MST 实验控制平台"
        self._refresh_window_title()

    def _mark_dirty(self, experiment_id: str, dirty: bool = True) -> None:
        exp_id = str(experiment_id or "").strip()
        if not exp_id:
            return
        state = self._ensure_session_state(exp_id)
        state.is_dirty = bool(dirty)
        self._refresh_window_title()

    def _apply_setup_lock_state(self) -> None:
        if self.project_view is None or not self.current_experiment_id:
            return
        setup_view = self.project_view.content.stack.widget(0)
        state = self._ensure_session_state(self.current_experiment_id)
        locked = state.lifecycle_status != "draft"
        if hasattr(setup_view, "set_plan_lock_state"):
            setup_view.set_plan_lock_state(locked=locked, allow_plan_edit=False)

    def _unlock_plan_for_current_experiment(self) -> None:
        if self.project_view is None or not self.current_experiment_id:
            return
        state = self._ensure_session_state(self.current_experiment_id)
        if state.lifecycle_status == "draft":
            return
        answer = QMessageBox.question(
            self,
            _EDIT_UNLOCK_TITLE,
            _EDIT_UNLOCK_TEXT,
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if answer != QMessageBox.Yes:
            return
        setup_view = self.project_view.content.stack.widget(0)
        if hasattr(setup_view, "set_plan_lock_state"):
            setup_view.set_plan_lock_state(locked=True, allow_plan_edit=True)
        self._mark_dirty(self.current_experiment_id, True)

    def _set_lifecycle_status(self, experiment_id: str, status: str) -> None:
        exp_id = str(experiment_id or "").strip()
        if not exp_id:
            return
        state = self._ensure_session_state(exp_id)
        state.lifecycle_status = str(status or "draft")
        self._experiment_status_by_id[exp_id] = "draft" if state.lifecycle_status == "draft" else "done"
        self._apply_setup_lock_state()

    def _experiment_dir(self, experiment_id: str) -> Path | None:
        if self.current_project_dir is None:
            return None
        return self.current_project_dir / str(experiment_id).strip()

    def _experiment_h5_path(self, experiment_id: str) -> Path | None:
        exp_dir = self._experiment_dir(experiment_id)
        if exp_dir is None:
            return None
        return exp_dir / "experiment.h5"

    def _experiment_key(self, experiment_id: str | None = None, path: str | Path | None = None) -> str:
        if path:
            return str(Path(path).parent.name).strip()
        return str(experiment_id or "").strip()

    def _get_or_assign_experiment_order(self, experiment_id: str, preferred_order: int | None = None) -> int:
        exp_id = str(experiment_id or "").strip()
        if not exp_id:
            return 0
        if exp_id in self._experiment_order_by_id:
            return self._experiment_order_by_id[exp_id]

        order = int(preferred_order or 0)
        if order > 0 and order not in self._experiment_order_by_id.values():
            self._experiment_order_by_id[exp_id] = order
            self._next_experiment_order = max(self._next_experiment_order, order + 1)
        else:
            self._experiment_order_by_id[exp_id] = self._next_experiment_order
            self._next_experiment_order += 1
        return self._experiment_order_by_id[exp_id]

    def _capture_current_plan_snapshot(self) -> None:
        if self.project_view is None or not self.current_experiment_id:
            return
        setup_view = self.project_view.content.stack.widget(0)
        if hasattr(setup_view, "get_params"):
            key = self._experiment_key(experiment_id=self.current_experiment_id, path=self.current_experiment_path)
            snapshot = dict(setup_view.get_params() or {})
            self._plan_snapshot_by_experiment_key[key] = snapshot
            self.state.current_session.setup_data = dict(snapshot)
            state = self._ensure_session_state(
                self.current_experiment_id,
                display_name=self._experiment_display_name_by_id.get(self.current_experiment_id, self._default_display_name(self.current_experiment_id)),
            )
            state.plan_snapshot = dict(snapshot)
            self._sync_current_session_state()
            self._mark_dirty(self.current_experiment_id, True)

    def _default_display_name(self, experiment_id: str) -> str:
        order = self._get_or_assign_experiment_order(experiment_id)
        return f"E{order:02d}"

    def _select_sidebar_experiment(self, experiment_id: str | None) -> None:
        if self.project_view is None:
            return
        self.project_view.select_experiment(str(experiment_id or ""))

    def _bind_plan_autosave(self) -> None:
        if self.project_view is None:
            return
        setup_view = self.project_view.content.stack.widget(0)

        def remember(*_args) -> None:
            self._capture_current_plan_snapshot()

        watched_widgets = [
            "cmb_target",
            "chk_histag",
            "edit_target_stock",
            "cmb_target_unit",
            "edit_target_assay",
            "cmb_buffer",
            "cmb_capillary",
            "cmb_ligand",
            "edit_kd",
            "cmb_kd_unit",
            "edit_lig_stock",
            "cmb_lig_unit",
            "chk_dmso",
            "edit_hi_conc",
            "chk_auto",
            "spin_excitation",
            "cmb_mst",
        ]

        for name in watched_widgets:
            widget = getattr(setup_view, name, None)
            if widget is None:
                continue
            if hasattr(widget, "currentTextChanged"):
                widget.currentTextChanged.connect(remember)
            if hasattr(widget, "textChanged"):
                widget.textChanged.connect(remember)
            if hasattr(widget, "toggled"):
                widget.toggled.connect(remember)
            if hasattr(widget, "valueChanged"):
                widget.valueChanged.connect(remember)

        if hasattr(setup_view, "edit_requested"):
            setup_view.edit_requested.connect(self._unlock_plan_for_current_experiment)


    def _refresh_sidebar_experiments(self) -> None:
        if self.project_view is None or self.current_project_dir is None:
            return

        experiments: list[tuple[int, str, str, str, str, str]] = []
        children = [child for child in self.current_project_dir.iterdir() if child.is_dir()]
        for child in children:
            h5_path = child / "experiment.h5"
            if not h5_path.exists():
                continue
            exp = Experiment.load_h5(h5_path)
            exp_id = str(child.name).strip()
            exp_name = str(self._experiment_display_name_by_id.get(exp_id) or exp.metadata.get("display_name") or exp.name or child.name)
            self._experiment_display_name_by_id[exp_id] = exp_name
            state = self._ensure_session_state(exp_id, display_name=exp_name)
            status = self._experiment_status_by_id.get(exp.id, self._experiment_status_by_id.get(exp_id, state.lifecycle_status))
            exp_type_id = normalize_experiment_type_id(
                str(exp.metadata.get("experiment_type_id") or exp.metadata.get("experiment_type") or state.experiment_type_id or "pre_test")
            )
            exp_type_name = str(
                exp.metadata.get("experiment_type") or state.experiment_type_name or get_experiment_type_config(exp_type_id).get("name") or "Pre-test"
            )
            state.experiment_type_id = exp_type_id
            state.experiment_type_name = exp_type_name
            state.excitation = str(exp.metadata.get("excitation") or state.excitation or "RED")
            metadata_order = int(str(exp.metadata.get("experiment_order") or "0") or "0")
            order_index = self._get_or_assign_experiment_order(exp_id, metadata_order)
            experiments.append((order_index, exp_id, exp_name, status, exp_type_id, exp_type_name))

        experiments.sort(key=lambda item: item[0])
        self.project_view.set_experiments([
            (exp_id, exp_name, status, exp_type_id, exp_type_name, order_index)
            for order_index, exp_id, exp_name, status, exp_type_id, exp_type_name in experiments
        ])
        self._select_sidebar_experiment(self.current_experiment_id or self._pending_new_experiment_id)

    def _save_experiment_by_id(self, experiment_id: str) -> bool:
        exp_id = str(experiment_id or "").strip()
        if not exp_id or self.current_project_dir is None or self.project_view is None:
            return False

        h5_path = self._experiment_h5_path(exp_id)
        if h5_path is None:
            return False

        setup_view = self.project_view.content.stack.widget(0)
        run_view = self.project_view.content.stack.widget(2)
        key = self._experiment_key(experiment_id=exp_id, path=h5_path)
        state = self._ensure_session_state(exp_id)

        if exp_id == (self.current_experiment_id or "") and hasattr(setup_view, "get_params"):
            setup_params = dict(setup_view.get_params() or {})
            excitation = self.current_excitation
            exp_type_id = self.current_experiment_type_id
            exp_type_name = self.current_experiment_type
        else:
            setup_params = dict(self._plan_snapshot_by_experiment_key.get(key) or state.plan_snapshot or {})
            excitation = state.excitation
            exp_type_id = state.experiment_type_id
            exp_type_name = state.experiment_type_name

        if h5_path.exists():
            loaded = Experiment.load_h5(h5_path)
            excitation = str(loaded.metadata.get("excitation") or excitation or "RED")
            exp_type_id = normalize_experiment_type_id(
                str(loaded.metadata.get("experiment_type_id") or loaded.metadata.get("experiment_type") or exp_type_id)
            )
            exp_type_name = str(loaded.metadata.get("experiment_type") or get_experiment_type_config(exp_type_id).get("name") or exp_type_name)
        display_name = self._experiment_display_name_by_id.get(exp_id, self._default_display_name(exp_id))

        exp = Experiment.from_ui(
            name=display_name,
            setup_params=setup_params,
            excitation=excitation,
            experiment_type=exp_type_name,
            experiment_type_id=exp_type_id,
            experiment_id=exp_id,
        )
        exp.metadata["experiment_order"] = str(self._get_or_assign_experiment_order(exp_id))

        if exp_id == (self.current_experiment_id or ""):
            exp.capture_from_run_view(run_view)
        elif h5_path.exists():
            loaded = Experiment.load_h5(h5_path)
            exp.raw = dict(loaded.raw or {})
            exp.processed = dict(loaded.processed or {})
            exp.run_data = dict(loaded.run_data or {})
            exp.protocol.update(dict(loaded.protocol or {}))
            exp.metadata.update({
                k: v for k, v in dict(loaded.metadata or {}).items()
                if k not in {"display_name", "timestamp", "experiment_id", "experiment_type", "experiment_type_id", "excitation"}
            })

        exp.save_h5(h5_path)
        state.display_name = str(display_name)
        state.excitation = excitation
        state.experiment_type_id = exp_type_id
        state.experiment_type_name = exp_type_name
        state.plan_snapshot = dict(setup_params)
        state.is_dirty = False
        self._experiment_status_by_id[exp_id] = "done"
        self._refresh_window_title()
        return True

    def _on_project_tab_changed(self, idx: int) -> None:
        if not self.current_experiment_id:
            return
        if idx in (1, 2):
            self._capture_current_plan_snapshot()
            self._save_experiment_by_id(self.current_experiment_id)
            self._set_lifecycle_status(self.current_experiment_id, "prepared")
            self._refresh_sidebar_experiments()

    def _load_experiment_from_id(self, experiment_id: str) -> None:
        if self.project_view is None:
            return
        h5_path = self._experiment_h5_path(experiment_id)
        if h5_path is None or not h5_path.exists():
            QMessageBox.warning(self, "打开提示", f"未找到实验文件：\n{h5_path}")
            return
        self.current_experiment_id = str(experiment_id).strip()
        self.current_experiment_path = str(h5_path)
        self._set_base_window_title_for_path(self.current_experiment_path)
        self._load_experiment_into_ui(str(h5_path), self.project_view)
        self._refresh_sidebar_experiments()

    def _on_experiment_selected(self, experiment_id: str) -> None:
        selected = str(experiment_id or "").strip()
        if not selected:
            return
        self._capture_current_plan_snapshot()
        if selected == (self.current_experiment_id or "") and self.current_experiment_path and Path(self.current_experiment_path).exists():
            return
        self._load_experiment_from_id(selected)

    def _on_experiment_rename_requested(self, experiment_id: str) -> None:
        if self.project_view is None:
            return
        exp_id = str(experiment_id or "").strip()
        if not exp_id:
            return
        h5_path = self._experiment_h5_path(exp_id)
        if h5_path is None or not h5_path.exists():
            return

        exp = Experiment.load_h5(h5_path)
        current_name = str(self._experiment_display_name_by_id.get(exp_id) or exp.metadata.get("display_name") or exp.name or "experiment")
        new_name, ok = self.project_view.prompt_rename(current_name)
        if not ok or not new_name:
            return

        exp.name = new_name
        exp.metadata["display_name"] = new_name
        exp.save_h5(h5_path)
        self._experiment_display_name_by_id[exp_id] = new_name
        self._ensure_session_state(exp_id, display_name=new_name).display_name = new_name
        self._refresh_sidebar_experiments()
        if exp_id == (self.current_experiment_id or ""):
            self.project_view.select_experiment(exp_id)

    def _on_experiment_delete_requested(self, experiment_id: str) -> None:
        exp_id = str(experiment_id or "").strip()
        if not exp_id or self.current_project_dir is None:
            return

        exp_dir = self._experiment_dir(exp_id)
        if exp_dir is None or not exp_dir.exists():
            return

        was_current = exp_id == (self.current_experiment_id or "")
        h5_path = exp_dir / "experiment.h5"

        if h5_path.exists():
            try:
                h5_path.unlink()
            except Exception:
                pass

        try:
            exp_dir.rmdir()
        except Exception:
            pass

        self._experiment_status_by_id.pop(exp_id, None)
        self._experiment_order_by_id.pop(exp_id, None)
        self._experiment_display_name_by_id.pop(exp_id, None)
        self._plan_snapshot_by_experiment_key.pop(exp_id, None)
        self._session_state_by_experiment_id.pop(exp_id, None)

        if was_current:
            self.current_experiment_id = None
            self.current_experiment_path = None
            self._set_base_window_title_for_path(None)

        self._refresh_sidebar_experiments()

        if was_current and self.project_view is not None:
            remaining = [btn.experiment_id for btn in self.project_view.sidebar._exp_buttons if btn.experiment_id]
            if remaining:
                self._load_experiment_from_id(remaining[0])

    def _prepare_new_experiment_session(self, target_path: str | None = None) -> bool:
        if target_path:
            target_h5 = Path(target_path)
            self.current_project_dir = target_h5.parent
            self.current_experiment_path = str(target_h5)
        if self.current_project_dir is None:
            QMessageBox.warning(self, "新建实验失败", "未选择实验项目目录")
            return False

        self._pending_new_experiment_id = Experiment().id
        self._get_or_assign_experiment_order(self._pending_new_experiment_id)
        new_exp_dir = self.current_project_dir / self._pending_new_experiment_id
        if target_path:
            target_h5 = Path(target_path)
            self.current_project_dir = target_h5.parent
            self.current_experiment_path = str(target_h5)
        else:
            self.current_experiment_path = str(new_exp_dir / "experiment.h5")
        default_name = self._default_display_name(self._pending_new_experiment_id)
        self._experiment_status_by_id[self._pending_new_experiment_id] = "draft"
        self._experiment_display_name_by_id[self._pending_new_experiment_id] = default_name

        state = ExperimentSessionState(
            experiment_id=self._pending_new_experiment_id,
            display_name=default_name,
            excitation="RED",
            experiment_type_id="pre_test",
            experiment_type_name="Pre-test",
            plan_snapshot={},
            is_dirty=True,
            lifecycle_status="draft",
        )
        self._session_state_by_experiment_id[self._pending_new_experiment_id] = state
        self.current_experiment_id = self._pending_new_experiment_id
        self._experiment_display_name_by_id[self.current_experiment_id] = default_name
        self.current_excitation = state.excitation
        self.current_experiment_type_id = state.experiment_type_id
        self.current_experiment_type = state.experiment_type_name
        self.state.current_session.experiment_type_id = state.experiment_type_id
        self.state.current_session.setup_data = default_setup_data(state.experiment_type_id)
        self._set_base_window_title_for_path(self.current_experiment_path)
        self._refresh_window_title()
        return True

    # ── Slots ─────────────────────────────────────────────────────────────

    def _on_session_opened(self, experiment_path: str) -> None:
        """欢迎页打开已有实验，直接进入主界面"""
        self.current_project_dir = Path(experiment_path).parent
        self.current_experiment_path = experiment_path
        self._pending_new_experiment_id = None
        loaded = Experiment.load_h5(experiment_path)
        self.current_experiment_id = loaded.id
        self._get_or_assign_experiment_order(self.current_experiment_id)
        self._set_base_window_title_for_path(experiment_path)
        self.current_excitation = str(loaded.metadata.get("excitation") or self.current_excitation)
        self.current_experiment_type_id = normalize_experiment_type_id(
            str(loaded.metadata.get("experiment_type_id") or loaded.metadata.get("experiment_type") or self.current_experiment_type_id)
        )
        self.current_experiment_type = str(
            loaded.metadata.get("experiment_type") or get_experiment_type_config(self.current_experiment_type_id).get("name") or self.current_experiment_type
        )
        state = self._ensure_session_state(
            loaded.id,
            display_name=str(loaded.metadata.get("display_name") or loaded.name or Path(experiment_path).parent.name),
        )
        state.excitation = self.current_excitation
        state.experiment_type_id = self.current_experiment_type_id
        state.experiment_type_name = self.current_experiment_type
        pv = self._ensure_project_view()
        self._stack.setCurrentIndex(2)
        self._load_experiment_into_ui(experiment_path, pv)
        self._select_sidebar_experiment(self.current_experiment_id)

    def _on_new_experiment_requested(self, experiment_path: str) -> None:
        if not self._prepare_new_experiment_session(experiment_path):
            return
        self.wizard.reset()
        self._refresh_sidebar_experiments()
        self._select_sidebar_experiment(self._pending_new_experiment_id)
        self._stack.setCurrentIndex(1)

    def _on_wizard_completed(self, excitation: str, experiment_type_id: str) -> None:
        """实验向导配置完成"""
        self.current_excitation = excitation
        self.current_experiment_type_id = normalize_experiment_type_id(experiment_type_id)

        if not self._pending_new_experiment_id or not self.current_experiment_id:
            QMessageBox.warning(self, "新建实验失败", "未找到待创建的实验会话")
            return

        type_items = list_experiment_types()
        name_by_id = {t.get("id"): t.get("name", "") for t in type_items}
        self.current_experiment_type = str(name_by_id.get(self.current_experiment_type_id, "Pre-test"))

        self.state.current_session.experiment_type_id = self.current_experiment_type_id
        self.state.current_session.setup_data = default_setup_data(self.current_experiment_type_id)

        pv = self._ensure_project_view()
        setup_view = pv.content.stack.widget(0)
        run_view = pv.content.stack.widget(2)
        if hasattr(setup_view, "set_experiment_type"):
            setup_view.set_experiment_type(self.current_experiment_type_id)
            setup_view.set_plan_lock_state(locked=False, allow_plan_edit=False)
        if hasattr(setup_view, "set_excitation_color"):
            setup_view.set_excitation_color(self.current_excitation)

        if self.current_project_dir is not None and hasattr(run_view, "data_manager"):
            dm: DataManager = run_view.data_manager
            dm.bind_experiment_by_id(
                self.current_experiment_id or "",
                project_dir=self.current_project_dir,
                name=Path(self.current_experiment_path or "experiment.h5").stem,
            )
            self.current_experiment_path = dm.current_h5_path
            self._set_base_window_title_for_path(self.current_experiment_path)

        if self.current_experiment_id:
            state = self._ensure_session_state(
                self.current_experiment_id,
                display_name=self._experiment_display_name_by_id.get(self.current_experiment_id, self._default_display_name(self.current_experiment_id)),
            )
            state.excitation = self.current_excitation
            state.experiment_type_id = self.current_experiment_type_id
            state.experiment_type_name = self.current_experiment_type
            state.lifecycle_status = "draft"
            state.is_dirty = True

        self._refresh_sidebar_experiments()
        self._select_sidebar_experiment(self.current_experiment_id)
        self._stack.setCurrentIndex(2)

        path = self.current_experiment_path
        should_reload_saved_experiment = bool(path and Path(path).exists() and self.current_experiment_id and self.current_experiment_id in self._session_state_by_experiment_id and self._session_state_by_experiment_id[self.current_experiment_id].plan_snapshot)
        if should_reload_saved_experiment:
            self._load_experiment_into_ui(path, pv)
        else:
            self._apply_setup_lock_state()
            self._refresh_window_title()
            if self.current_experiment_id:
                self._sync_current_session_state()
                pv.update_metadata({
                    "experiment_type": self.current_experiment_type,
                    "excitation": self.current_excitation,
                    **dict(self.state.current_session.setup_data or {}),
                })

        self._pending_new_experiment_id = None

    def _go_welcome(self) -> None:
        """返回欢迎页"""
        self.current_project_dir = None
        self.current_experiment_id = None
        self.current_experiment_path = None
        self._pending_new_experiment_id = None
        self._set_base_window_title_for_path(None)
        self._stack.setCurrentIndex(0)
        self.welcome_view._populate_recent()

    def _on_save(self) -> None:
        if self.project_view is None:
            QMessageBox.warning(self, "保存失败", "未加载实验项目界面")
            return
        if self.current_project_dir is None:
            QMessageBox.warning(self, "保存失败", "未选择实验项目目录")
            return

        try:
            self._capture_current_plan_snapshot()
            dirty_ids = [exp_id for exp_id, state in self._session_state_by_experiment_id.items() if state.is_dirty]
            if not dirty_ids:
                QMessageBox.information(self, "保存提示", "所有实验数据均已保存，无需重复保存")
                return

            for exp_id in dirty_ids:
                self._save_experiment_by_id(exp_id)

            self._refresh_sidebar_experiments()
            self._refresh_window_title()
            QMessageBox.information(self, "保存成功", f"已成功保存 {len(dirty_ids)} 项实验数据")
        except Exception as e:
            QMessageBox.critical(self, "保存错误", f"实验数据保存失败\n{e}")

    def _on_new_exp(self) -> None:
        if self.project_view is None or self.current_project_dir is None:
            QMessageBox.warning(self, "新建实验失败", "未加载实验项目界面或未选择实验项目目录")
            return

        self._capture_current_plan_snapshot()
        if not self._prepare_new_experiment_session():
            return

        self.wizard.reset()
        self._refresh_sidebar_experiments()
        self._select_sidebar_experiment(self._pending_new_experiment_id)
        self._stack.setCurrentIndex(1)

    def _load_experiment_into_ui(self, path: str, pv: ProjectView) -> None:
        try:
            exp = Experiment.load_h5(path)
            setup_view = pv.content.stack.widget(0)
            run_view = pv.content.stack.widget(2)

            loaded_type_id = normalize_experiment_type_id(
                str(exp.metadata.get("experiment_type_id") or exp.metadata.get("experiment_type") or self.current_experiment_type_id)
            )
            self.current_experiment_type_id = loaded_type_id
            self.current_excitation = str(exp.metadata.get("excitation") or self.current_excitation or "RED")

            type_items = list_experiment_types()
            name_by_id = {t.get("id"): t.get("name", "") for t in type_items}
            self.current_experiment_type = str(name_by_id.get(loaded_type_id, self.current_experiment_type))

            self.state.current_session.experiment_type_id = loaded_type_id
            self.state.current_session.setup_data = dict(exp.setup_data or {})
            self.current_experiment_id = str(Path(path).parent.name)
            self._get_or_assign_experiment_order(self.current_experiment_id)
            display_name = str(exp.metadata.get("display_name") or exp.name or Path(path).parent.name)
            self._experiment_display_name_by_id[self.current_experiment_id] = display_name
            state = self._ensure_session_state(self.current_experiment_id, display_name=display_name)
            state.excitation = self.current_excitation
            state.experiment_type_id = loaded_type_id
            state.experiment_type_name = str(exp.metadata.get("experiment_type") or get_experiment_type_config(loaded_type_id).get("name") or self.current_experiment_type)
            if not state.plan_snapshot:
                state.plan_snapshot = dict(exp.setup_data or {})

            if hasattr(run_view, "clear_view_state"):
                run_view.clear_view_state()

            self._experiment_status_by_id[self.current_experiment_id] = "draft" if state.lifecycle_status == "draft" else "done"

            if hasattr(run_view, "data_manager") and self.current_project_dir is not None:
                run_view.data_manager.bind_experiment(exp, base_dir=Path(path).parent)
                self.current_experiment_path = run_view.data_manager.current_h5_path
                self._set_base_window_title_for_path(self.current_experiment_path)

            if hasattr(setup_view, "set_experiment_type"):
                setup_view.set_experiment_type(loaded_type_id)
            if hasattr(setup_view, "set_excitation_color"):
                setup_view.set_excitation_color(self.current_excitation)
            snapshot = self._plan_snapshot_by_experiment_key.get(self._experiment_key(path=path, experiment_id=self.current_experiment_id)) or state.plan_snapshot
            if snapshot and hasattr(setup_view, "set_data"):
                setup_view.set_data(snapshot)
            else:
                exp.apply_to_setup_view(setup_view)

            self._apply_setup_lock_state()

            if hasattr(run_view, "load_replay_file"):
                run_view.load_replay_file(path)
            else:
                exp.apply_to_run_view(run_view)

            self._refresh_sidebar_experiments()
            pv.select_experiment(self.current_experiment_id)
            pv.update_metadata({**dict(exp.metadata or {}), **dict(exp.setup_data or {}), **dict(exp.protocol or {})})

            self.current_excitation = str(exp.metadata.get("excitation", self.current_excitation) or self.current_excitation)
            self.current_experiment_type = str(exp.metadata.get("experiment_type", self.current_experiment_type) or self.current_experiment_type)
            self._refresh_window_title()
        except Exception as e:
            QMessageBox.warning(self, "加载失败", f"实验数据加载失败，请检查文件完整性\n{e}")