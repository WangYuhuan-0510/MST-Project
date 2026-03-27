"""
serial_worker.py
────────────────
后台线程，持续从串口读取数据并解析成 DataSample，
通过 Qt Signal 推送给主线程的 UI 组件。

使用方式：
    worker = SerialWorker(port="COM3", baudrate=115200)
    worker.data_ready.connect(my_slot)      # DataSample
    worker.status_changed.connect(my_slot)  # str
    worker.error_occurred.connect(my_slot)  # str
    worker.start()
    ...
    worker.stop()
"""
from __future__ import annotations

import struct
import time
from typing import List

from PySide6.QtCore import QThread, Signal

from .protocol import (
    HEADER,    
    CMD_DATA_FRAME,   #0x15
    CMD_MST_DATA,
    ProtocolFrame,
    parse_data_frame,
    parse_mst_frame,
    build_start_frame,
    build_stop_frame,
)
from .transport import SerialTransport


class SerialWorker(QThread):
    """
    独立读取线程，职责：
      1. 打开串口
      2. 发送 CMD_START
      3. 循环读取字节 → 帧同步 → 解析 DataSample → emit data_ready
      4. 收到 stop() 后发 CMD_STOP 并关闭串口
    """

    # ── Qt Signals ────────────────────────────────────────────────────────
    data_ready      = Signal(object)   # DataSample
    status_changed  = Signal(str)      # "连接成功" / "已断开" 等
    error_occurred  = Signal(str)      # 错误描述字符串
    debug_stats     = Signal(object)   # 串口底层统计信息(dict)

    def __init__(self, port: str = "COM3",
                 baudrate: int = 115200,
                 parent=None) -> None:
        super().__init__(parent)
        self._port     = port
        self._baudrate = baudrate
        self._running  = False
        self._transport: SerialTransport | None = None
        self._rx_bytes = 0
        self._rx_chunks = 0
        self._ok_frames = 0
        self._bad_frames = 0
        self._last_chunk_hex = "-"

    # ── 公共控制接口 ──────────────────────────────────────────────────────

    def stop(self) -> None:
        """请求线程退出（线程安全）。"""
        self._running = False

    # ── QThread.run() ─────────────────────────────────────────────────────

    def run(self) -> None:
        # 1. 打开串口
        transport = SerialTransport(port=self._port, baudrate=self._baudrate,
                                    timeout=0.05)
        try:
            transport.open()
        except Exception as e:
            self.error_occurred.emit(f"串口打开失败：{e}")
            return

        self._transport = transport
        self._running   = True
        self._rx_bytes = 0
        self._rx_chunks = 0
        self._ok_frames = 0
        self._bad_frames = 0
        self._last_chunk_hex = "-"
        self.status_changed.emit(f"已连接到 {self._port}，波特率 {self._baudrate}")
        try:
            ser = getattr(transport, "_ser", None)
            if ser is not None:
                self.debug_stats.emit({
                    **self._snapshot_stats(),
                    "port": str(getattr(ser, "port", self._port)),
                    "baudrate": int(getattr(ser, "baudrate", self._baudrate)),
                    "bytesize": int(getattr(ser, "bytesize", 8)),
                    "parity": str(getattr(ser, "parity", "N")),
                    "stopbits": str(getattr(ser, "stopbits", 1)),
                })
        except Exception:
            pass

        # 2. 发送启动命令
        try:
            transport.send(build_start_frame())
        except Exception as e:
            self.error_occurred.emit(f"启动命令发送失败：{e}")
            transport.close()
            return

        # 3. 循环读取
        rx_buf = bytearray()
        try:
            while self._running:
                chunk = transport.receive(256)
                if chunk:
                    self._rx_chunks += 1
                    self._rx_bytes += len(chunk)
                    self._last_chunk_hex = chunk[:16].hex(" ")
                    self.debug_stats.emit(self._snapshot_stats())
                    rx_buf.extend(chunk)
                    rx_buf = self._process_buffer(rx_buf)
                else:
                    # 无数据时短暂休眠，降低 CPU 占用
                    time.sleep(0.01)
        except Exception as e:
            self.error_occurred.emit(f"读取异常：{e}")
        finally:
            # 4. 发送停止命令并关闭串口
            try:
                transport.send(build_stop_frame())
            except Exception:
                pass
            transport.close()
            self._transport = None
            self.status_changed.emit("串口已关闭")

    # ── 帧同步与解析 ──────────────────────────────────────────────────────

    def _process_buffer(self, buf: bytearray) -> bytearray:
        """
        从字节缓冲区中尝试提取完整帧并解析。
        帧格式：[0xAA][CMD][LEN][PAYLOAD(LEN bytes)][CHECKSUM]
        最小帧长度 = 4 bytes（LEN=0 时）
        """
        while len(buf) >= 4:
            # 查找帧头 0xAA
            if buf[0] != HEADER:
                buf = buf[1:]
                continue

            length = buf[2]
            frame_len = 4 + length  # header+cmd+len+payload+checksum

            if len(buf) < frame_len:
                break   # 数据不够，等待更多字节

            raw = bytes(buf[:frame_len])
            buf = buf[frame_len:]

            try:
                frame = ProtocolFrame.parse(raw)
            except ValueError:
                # 帧校验失败，丢弃这一帧继续
                self._bad_frames += 1
                self.debug_stats.emit(self._snapshot_stats())
                continue

            if frame.command == CMD_MST_DATA:
                try:
                    sample = parse_mst_frame(frame)
                    self._ok_frames += 1
                    self.debug_stats.emit(self._snapshot_stats())
                    self.data_ready.emit(sample)
                except ValueError as e:
                    self._bad_frames += 1
                    self.debug_stats.emit(self._snapshot_stats())
                    self.error_occurred.emit(f"MST数据帧解析失败：{e}")
            elif frame.command == CMD_DATA_FRAME:
                try:
                    sample = parse_data_frame(frame)
                    self._ok_frames += 1
                    self.debug_stats.emit(self._snapshot_stats())
                    self.data_ready.emit(sample)
                except ValueError as e:
                    self._bad_frames += 1
                    self.debug_stats.emit(self._snapshot_stats())
                    self.error_occurred.emit(f"数据帧解析失败：{e}")

        return buf

    def _snapshot_stats(self) -> dict:
        return {
            "rx_bytes": int(self._rx_bytes),
            "rx_chunks": int(self._rx_chunks),
            "ok_frames": int(self._ok_frames),
            "bad_frames": int(self._bad_frames),
            "last_chunk_hex": self._last_chunk_hex,
        }