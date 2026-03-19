from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Callable, Dict, Optional


class WorkflowState(Enum):
    IDLE = auto()
    INITIALIZING = auto()
    ACQUIRING = auto()
    PROCESSING = auto()
    FITTING = auto()
    EXPORTING = auto()
    UI_UPDATING = auto()
    FINISHED = auto()
    CANCELLED = auto()
    ERROR = auto()


class WorkflowError(RuntimeError):
    pass


Context = Dict[str, Any]
StepFn = Callable[[Context], Context]
HookFn = Callable[[WorkflowState, Context], None]


@dataclass(frozen=True)
class Pipeline:
    """
    初始化 → 采集数据 → 数据处理 → 拟合 → 结果输出 → UI更新

    约定：
    - step 输入 ctx，返回 ctx（可就地修改，但建议返回新 dict 以便调试/回溯）
    - core 层不依赖 UI；UI 通过 hook 获取状态与数据
    """

    initialize: StepFn
    acquire: StepFn
    process: StepFn
    fit: StepFn
    export: StepFn
    ui_update: StepFn


def _identity(ctx: Context) -> Context:
    return ctx


def default_pipeline() -> Pipeline:
    """
    默认占位 pipeline：用于先跑通状态机与 UI 联动。
    """

    return Pipeline(
        initialize=_identity,
        acquire=_identity,
        process=_identity,
        fit=_identity,
        export=_identity,
        ui_update=_identity,
    )


def mock_device_pipeline(
    *,
    t1_s: float = 2.0,
    ui_callback: Optional[Callable[[Context], None]] = None,
) -> Pipeline:
    """
    将 pipeline 填成：mock_device → process → fit → UI显示（export 作为可选占位）。

    ctx 约定输出字段：
    - raw: MockMSTRun
    - feature_y: list[float]
    - fit4pl: Fit4PLResult
    """

    from mst.core.fitting import fit_4pl_curve
    from mst.core.processing import extract_feature_at_time
    from mst.device.mock_device import simulate_mst_time_fluorescence

    def initialize(ctx: Context) -> Context:
        out = dict(ctx)
        out["t1_s"] = float(out.get("t1_s", t1_s))
        if ui_callback is not None:
            out["ui_callback"] = ui_callback
        return out

    def acquire(ctx: Context) -> Context:
        out = dict(ctx)
        raw = simulate_mst_time_fluorescence()
        out["raw"] = raw
        return out

    def process(ctx: Context) -> Context:
        out = dict(ctx)
        raw = out["raw"]
        out["feature_y"] = extract_feature_at_time(raw.t_s, raw.traces, t_feature_s=float(out["t1_s"]))
        out["concentrations"] = raw.concentrations
        out["scan_center"] = raw.scan_center
        return out

    def fit(ctx: Context) -> Context:
        out = dict(ctx)
        x = out["concentrations"]
        y = out["feature_y"]
        out["fit4pl"] = fit_4pl_curve(x, y)
        return out

    def export(ctx: Context) -> Context:
        # 这里先不做文件输出，占位保留扩展点
        return dict(ctx)

    def ui_update(ctx: Context) -> Context:
        out = dict(ctx)
        cb = out.get("ui_callback")
        if callable(cb):
            cb(out)
        return out

    return Pipeline(
        initialize=initialize,
        acquire=acquire,
        process=process,
        fit=fit,
        export=export,
        ui_update=ui_update,
    )


@dataclass
class Workflow:
    """
    状态机 + Pipeline 的 Workflow。

    - **状态机**：约束流程顺序；失败进入 ERROR；支持 CANCELLED
    - **Pipeline**：每一步可注入真实实现（设备采集、信号处理、拟合、导出、UI刷新）
    """

    state: WorkflowState = WorkflowState.IDLE
    pipeline: Pipeline = field(default_factory=default_pipeline)
    ctx: Context = field(default_factory=dict)

    # hooks：用于 UI 更新 / 日志 / 指标
    on_state_enter: Optional[HookFn] = None
    on_state_exit: Optional[HookFn] = None
    on_error: Optional[Callable[[Exception, WorkflowState, Context], None]] = None

    _cancel_requested: bool = False

    def start(self) -> None:
        if self.state is not WorkflowState.IDLE:
            raise WorkflowError(f"cannot start from state={self.state}")
        self._cancel_requested = False
        self._transition(WorkflowState.INITIALIZING)

    def cancel(self) -> None:
        self._cancel_requested = True

    def tick(self) -> None:
        """
        执行“当前状态对应的一步”，并迁移到下一状态。
        UI 中可用定时器或工作线程循环调用 tick()。
        """

        if self.state in (WorkflowState.IDLE, WorkflowState.FINISHED, WorkflowState.ERROR, WorkflowState.CANCELLED):
            return
        if self._cancel_requested:
            self._transition(WorkflowState.CANCELLED)
            return

        try:
            if self.state is WorkflowState.INITIALIZING:
                self.ctx = self.pipeline.initialize(self.ctx)
                self._transition(WorkflowState.ACQUIRING)
            elif self.state is WorkflowState.ACQUIRING:
                self.ctx = self.pipeline.acquire(self.ctx)
                self._transition(WorkflowState.PROCESSING)
            elif self.state is WorkflowState.PROCESSING:
                self.ctx = self.pipeline.process(self.ctx)
                self._transition(WorkflowState.FITTING)
            elif self.state is WorkflowState.FITTING:
                self.ctx = self.pipeline.fit(self.ctx)
                self._transition(WorkflowState.EXPORTING)
            elif self.state is WorkflowState.EXPORTING:
                self.ctx = self.pipeline.export(self.ctx)
                self._transition(WorkflowState.UI_UPDATING)
            elif self.state is WorkflowState.UI_UPDATING:
                self.ctx = self.pipeline.ui_update(self.ctx)
                self._transition(WorkflowState.FINISHED)
            else:
                raise WorkflowError(f"unexpected state={self.state}")
        except Exception as e:
            self._fail(e)

    def run(self) -> Context:
        """
        同步执行整个流程（适合单测/脚本）。
        """

        if self.state is WorkflowState.IDLE:
            self.start()
        while self.state not in (WorkflowState.FINISHED, WorkflowState.ERROR, WorkflowState.CANCELLED):
            self.tick()
        if self.state is WorkflowState.ERROR:
            raise WorkflowError("workflow failed")
        return self.ctx

    def reset(self) -> None:
        self._cancel_requested = False
        self.ctx.clear()
        self._transition(WorkflowState.IDLE)

    def _transition(self, new_state: WorkflowState) -> None:
        old = self.state
        if self.on_state_exit is not None and old is not new_state:
            self.on_state_exit(old, self.ctx)
        self.state = new_state
        if self.on_state_enter is not None:
            self.on_state_enter(new_state, self.ctx)

    def _fail(self, e: Exception) -> None:
        if self.on_error is not None:
            try:
                self.on_error(e, self.state, self.ctx)
            except Exception:
                pass
        self._transition(WorkflowState.ERROR)

