from __future__ import annotations

from typing import Optional

from PySide6.QtCore import QObject, QTimer, Signal

from mst.core.experiments import Experiment
from mst.device.protocol import MSTDataSample
from mst.device.serial_worker import SerialWorker
from mst.device.transport import SerialTransport


class BaseDataSource(QObject):
    """统一数据源接口：实时串口/文件回放都实现 start/stop/pause/resume。"""

    data_ready = Signal(object)
    status_changed = Signal(str)
    error_occurred = Signal(str)
    debug_stats = Signal(object)
    finished = Signal()

    def start(self) -> None:  # pragma: no cover - interface
        raise NotImplementedError

    def stop(self) -> None:  # pragma: no cover - interface
        raise NotImplementedError

    def pause(self) -> None:  # pragma: no cover - interface
        raise NotImplementedError

    def resume(self) -> None:  # pragma: no cover - interface
        raise NotImplementedError


class SerialRealtimeDataSource(BaseDataSource):
    def __init__(self, *, port: str, baudrate: int, parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self._port = port
        self._baudrate = baudrate
        self._worker: Optional[SerialWorker] = None
        self._paused = False

    def start(self) -> None:
        self.stop()
        self._paused = False
        self._worker = SerialWorker(port=self._port, baudrate=self._baudrate, parent=self)
        self._worker.data_ready.connect(self.data_ready.emit)
        self._worker.status_changed.connect(self.status_changed.emit)
        self._worker.error_occurred.connect(self.error_occurred.emit)
        self._worker.debug_stats.connect(self.debug_stats.emit)
        self._worker.finished.connect(self._on_finished)
        self._worker.start()

    def stop(self) -> None:
        if self._worker is None:
            return
        self._worker.stop()
        self._worker.wait(2000)
        self._worker = None
        self._paused = False
        self.finished.emit()

    def pause(self) -> None:
        self._paused = True
        self.status_changed.emit("串口采集中（已暂停显示）")

    def resume(self) -> None:
        self._paused = False
        self.status_changed.emit("串口采集中（已继续）")

    def _on_finished(self) -> None:
        self._worker = None
        self.finished.emit()


class H5ReplayDataSource(BaseDataSource):
    """从 experiment.h5 回放：读取 -> 逐帧发射 MSTDataSample。"""

    def __init__(self, *, h5_path: str, interval_ms: int = 40, parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self._h5_path = h5_path
        self._interval_ms = max(10, int(interval_ms))
        self._timer = QTimer(self)
        self._timer.setInterval(self._interval_ms)
        self._timer.timeout.connect(self._on_tick)
        self._paused = False

        self._samples: list[MSTDataSample] = []
        self._cursor = 0

    def _build_samples(self) -> None:
        exp = Experiment.load_h5(self._h5_path)
        t_axis = [float(v) for v in (exp.run_data.get("t", []) or [])]
        if not t_axis:
            raise ValueError("回放失败：h5 中没有 run/t 时间轴数据")

        raw = exp.raw or {}
        traces: list[list[float]] = []
        n_ch = 16
        for i in range(n_ch):
            traces.append([float(v) for v in raw.get(f"capillary_{i + 1}", [])])

        self._samples = []
        for j, t_s in enumerate(t_axis):
            t_ms = int(max(0.0, t_s) * 1000.0)
            for i in range(n_ch):
                if j >= len(traces[i]):
                    continue
                fluo = int(traces[i][j])
                # 与 RunView._SerialBuffer 映射一致：distance in [0,16)
                distance = float(i) + 0.5
                self._samples.append(
                    MSTDataSample(
                        t_ms=t_ms,
                        distance=distance,
                        fluo=fluo,
                        reserved=3,  # mst_stream + ir_on
                        ir_on=True,
                        mst_stream=True,
                    )
                )

    def start(self) -> None:
        self.stop()
        self._paused = False
        self._cursor = 0
        self._build_samples()
        self.status_changed.emit("开始回放 .h5 实验数据")
        self.debug_stats.emit({"source": "h5_replay", "total_samples": len(self._samples)})
        self._timer.start()

    def stop(self) -> None:
        self._timer.stop()
        self._paused = False
        self.finished.emit()

    def pause(self) -> None:
        self._paused = True
        self.status_changed.emit("回放已暂停")

    def resume(self) -> None:
        self._paused = False
        self.status_changed.emit("回放已继续")

    def _on_tick(self) -> None:
        if self._paused:
            return
        if self._cursor >= len(self._samples):
            self._timer.stop()
            self.status_changed.emit("回放完成")
            self.finished.emit()
            return

        # 每 tick 推送一小批，兼顾 UI 流畅与速度
        batch = 32
        end = min(self._cursor + batch, len(self._samples))
        for i in range(self._cursor, end):
            self.data_ready.emit(self._samples[i])
        self._cursor = end


class DataManager(QObject):
    """核心模块：统一管理数据源，向 UI 提供统一信号接口。"""

    data_ready = Signal(object)
    status_changed = Signal(str)
    error_occurred = Signal(str)
    debug_stats = Signal(object)
    finished = Signal()

    def __init__(self, parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self._source: Optional[BaseDataSource] = None

    @staticmethod
    def list_serial_ports() -> list[str]:
        return SerialTransport.list_ports()

    def use_realtime_serial(self, *, port: str, baudrate: int) -> None:
        self.stop()
        self._set_source(SerialRealtimeDataSource(port=port, baudrate=baudrate, parent=self))

    def use_h5_replay(self, *, h5_path: str, interval_ms: int = 40) -> None:
        self.stop()
        self._set_source(H5ReplayDataSource(h5_path=h5_path, interval_ms=interval_ms, parent=self))

    def start(self) -> None:
        if self._source is None:
            self.error_occurred.emit("DataManager 未配置数据源")
            return
        try:
            self._source.start()
        except Exception as e:
            self.error_occurred.emit(str(e))

    def stop(self) -> None:
        if self._source is not None:
            self._source.stop()

    def pause(self) -> None:
        if self._source is not None:
            self._source.pause()

    def resume(self) -> None:
        if self._source is not None:
            self._source.resume()

    def _set_source(self, source: BaseDataSource) -> None:
        self._source = source
        source.data_ready.connect(self.data_ready.emit)
        source.status_changed.connect(self.status_changed.emit)
        source.error_occurred.connect(self.error_occurred.emit)
        source.debug_stats.connect(self.debug_stats.emit)
        source.finished.connect(self.finished.emit)
