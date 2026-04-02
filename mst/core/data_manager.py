from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

from PySide6.QtCore import QObject, QTimer, Signal

from mst.core.experiments import Experiment
from mst.device.protocol import MSTDataSample
from mst.device.serial_worker import SerialWorker
from mst.device.transport import SerialTransport


def _get_logger() -> logging.Logger:
    logger = logging.getLogger("mst.data_manager")
    if logger.handlers:
        return logger

    logger.setLevel(logging.INFO)
    log_path = Path.cwd() / "data_manager.log"
    fh = logging.FileHandler(log_path, encoding="utf-8")
    fh.setLevel(logging.INFO)
    fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s - %(message)s")
    fh.setFormatter(fmt)
    logger.addHandler(fh)
    logger.propagate = False
    logger.info("logger initialized, file=%s", log_path)
    return logger


_LOG = _get_logger()


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
        _LOG.info("SerialRealtimeDataSource.start port=%s baudrate=%s", self._port, self._baudrate)
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
            _LOG.info("SerialRealtimeDataSource.stop ignored: no worker")
            return
        _LOG.info("SerialRealtimeDataSource.stop")
        self._worker.stop()
        self._worker.wait(2000)
        self._worker = None
        self._paused = False
        self.finished.emit()

    def pause(self) -> None:
        self._paused = True
        _LOG.info("SerialRealtimeDataSource.pause")
        self.status_changed.emit("串口采集中（已暂停显示）")

    def resume(self) -> None:
        self._paused = False
        _LOG.info("SerialRealtimeDataSource.resume")
        self.status_changed.emit("串口采集中（已继续）")

    def _on_finished(self) -> None:
        _LOG.info("SerialRealtimeDataSource.finished")
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
        self._tick_count = 0

    def _build_samples(self) -> None:
        _LOG.info("H5ReplayDataSource._build_samples path=%s", self._h5_path)
        exp = Experiment.load_h5(self._h5_path)
        t_axis = [float(v) for v in (exp.run_data.get("t", []) or [])]
        if not t_axis:
            _LOG.error("H5ReplayDataSource build failed: empty run/t")
            raise ValueError("回放失败：h5 中没有 run/t 时间轴数据")

        raw = exp.raw or {}
        traces: list[list[float]] = []
        n_ch = 16
        for i in range(n_ch):
            traces.append([float(v) for v in raw.get(f"capillary_{i + 1}", [])])

        self._samples = []

        # 先注入一帧“扫描阶段”样本，保证 Capillary Scan 可重现
        min_t = min(t_axis)
        scan_t_ms = int(min_t * 1000.0) - 1
        for i in range(n_ch):
            trace_i = traces[i]
            if not trace_i:
                continue
            self._samples.append(
                MSTDataSample(
                    t_ms=scan_t_ms,
                    distance=float(i) + 0.5,
                    fluo=int(max(trace_i)),
                    reserved=0,
                    ir_on=False,
                    mst_stream=False,
                )
            )
        for j, t_s in enumerate(t_axis):
            # 直接使用保存的 t(s) 还原为 ms，避免横轴右移
            t_ms = int(t_s * 1000.0)
            for i in range(n_ch):
                if j >= len(traces[i]):
                    continue
                fluo = int(traces[i][j])
                distance = float(i) + 0.5
                self._samples.append(
                    MSTDataSample(
                        t_ms=t_ms,
                        distance=distance,
                        fluo=fluo,
                        reserved=3,
                        ir_on=True,
                        mst_stream=True,
                    )
                )

        _LOG.info(
            "H5ReplayDataSource samples built: t_points=%s channels=%s total_samples=%s",
            len(t_axis),
            n_ch,
            len(self._samples),
        )

    def start(self) -> None:
        _LOG.info("H5ReplayDataSource.start path=%s interval_ms=%s", self._h5_path, self._interval_ms)
        self.stop()
        self._paused = False
        self._cursor = 0
        self._tick_count = 0
        self._build_samples()
        self.status_changed.emit("开始回放 .h5 实验数据")
        self.debug_stats.emit({"source": "h5_replay", "total_samples": len(self._samples), "cursor": self._cursor})
        self._timer.start()

    def stop(self) -> None:
        if self._timer.isActive():
            _LOG.info("H5ReplayDataSource.stop active_timer=true cursor=%s", self._cursor)
        else:
            _LOG.info("H5ReplayDataSource.stop active_timer=false")
        self._timer.stop()
        self._paused = False
        self.finished.emit()

    def pause(self) -> None:
        self._paused = True
        _LOG.info("H5ReplayDataSource.pause cursor=%s", self._cursor)
        self.status_changed.emit("回放已暂停")

    def resume(self) -> None:
        self._paused = False
        _LOG.info("H5ReplayDataSource.resume cursor=%s", self._cursor)
        self.status_changed.emit("回放已继续")

    def _on_tick(self) -> None:
        self._tick_count += 1
        if self._paused:
            if self._tick_count % 50 == 0:
                _LOG.info("H5ReplayDataSource.tick paused cursor=%s", self._cursor)
            return

        if self._cursor >= len(self._samples):
            _LOG.info("H5ReplayDataSource.replay_completed total=%s", len(self._samples))
            self._timer.stop()
            self.status_changed.emit("回放完成")
            self.finished.emit()
            return

        batch = 32
        start = self._cursor
        end = min(start + batch, len(self._samples))
        for i in range(start, end):
            self.data_ready.emit(self._samples[i])
        self._cursor = end

        if self._tick_count <= 5 or self._tick_count % 20 == 0:
            _LOG.info(
                "H5ReplayDataSource.tick tick=%s emitted=%s cursor=%s/%s",
                self._tick_count,
                end - start,
                self._cursor,
                len(self._samples),
            )
        self.debug_stats.emit({"source": "h5_replay", "cursor": self._cursor, "total_samples": len(self._samples)})


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
        ports = SerialTransport.list_ports()
        _LOG.info("DataManager.list_serial_ports ports=%s", ports)
        return ports

    def use_realtime_serial(self, *, port: str, baudrate: int) -> None:
        _LOG.info("DataManager.use_realtime_serial port=%s baudrate=%s", port, baudrate)
        self.stop()
        self._set_source(SerialRealtimeDataSource(port=port, baudrate=baudrate, parent=self))

    def use_h5_replay(self, *, h5_path: str, interval_ms: int = 40) -> None:
        _LOG.info("DataManager.use_h5_replay path=%s interval_ms=%s", h5_path, interval_ms)
        self.stop()
        self._set_source(H5ReplayDataSource(h5_path=h5_path, interval_ms=interval_ms, parent=self))

    def start(self) -> None:
        if self._source is None:
            msg = "DataManager 未配置数据源"
            _LOG.error(msg)
            self.error_occurred.emit(msg)
            return
        _LOG.info("DataManager.start source=%s", type(self._source).__name__)
        try:
            self._source.start()
        except Exception as e:
            _LOG.exception("DataManager.start failed: %s", e)
            self.error_occurred.emit(str(e))

    def stop(self) -> None:
        if self._source is not None:
            _LOG.info("DataManager.stop source=%s", type(self._source).__name__)
            self._source.stop()

    def pause(self) -> None:
        if self._source is not None:
            _LOG.info("DataManager.pause source=%s", type(self._source).__name__)
            self._source.pause()

    def resume(self) -> None:
        if self._source is not None:
            _LOG.info("DataManager.resume source=%s", type(self._source).__name__)
            self._source.resume()

    def _set_source(self, source: BaseDataSource) -> None:
        _LOG.info("DataManager._set_source source=%s", type(source).__name__)
        self._source = source
        source.data_ready.connect(self.data_ready.emit)
        source.status_changed.connect(self.status_changed.emit)
        source.error_occurred.connect(self.error_occurred.emit)
        source.debug_stats.connect(self.debug_stats.emit)
        source.finished.connect(self.finished.emit)
