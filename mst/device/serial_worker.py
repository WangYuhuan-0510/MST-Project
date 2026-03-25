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
    HEADER, CMD_DATA_FRAME, N_CHANNELS,
    ProtocolFrame, DataSample, parse_data_frame,
    build_start_frame, build_stop_frame,
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

    def __init__(self, port: str = "COM3",
                 baudrate: int = 115200,
                 parent=None) -> None:
        super().__init__(parent)
        self._port     = port
        self._baudrate = baudrate
        self._running  = False
        self._transport: SerialTransport | None = None

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
        self.status_changed.emit(f"已连接到 {self._port}，波特率 {self._baudrate}")

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
                continue

            if frame.command == CMD_DATA_FRAME:
                try:
                    sample = parse_data_frame(frame)
                    self.data_ready.emit(sample)
                except ValueError as e:
                    self.error_occurred.emit(f"数据帧解析失败：{e}")

        return buf