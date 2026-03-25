from __future__ import annotations

import struct
from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable


@runtime_checkable
class Transport(Protocol):
    """
    通讯底层抽象接口，方便后续切换串口/TCP 或使用模拟设备。
    """

    def open(self) -> None: ...

    def close(self) -> None: ...

    def send(self, data: bytes) -> None: ...

    def receive(self, size: int = 4096) -> bytes: ...


@dataclass
class MockTransport:
    """
    简单内存缓冲实现，主要用于单元测试。
    """

    buffer: bytes = b""

    def open(self) -> None:
        self.buffer = b""

    def close(self) -> None:
        self.buffer = b""

    def send(self, data: bytes) -> None:
        self.buffer += data

    def receive(self, size: int = 4096) -> bytes:
        data, self.buffer = self.buffer[:size], self.buffer[size:]
        return data


class SerialTransport:
    """
    真实串口实现，依赖 pyserial。
    使用前请安装：pip install pyserial

    参数：
      port      串口号，如 "COM3"（Windows）或 "/dev/ttyUSB0"（Linux）
      baudrate  波特率，需与 STM32 端一致，默认 115200
      timeout   单次 receive() 阻塞超时秒数，默认 0.05s（非阻塞读）
    """

    def __init__(self, port: str = "COM3",
                 baudrate: int = 115200,
                 timeout: float = 0.05) -> None:
        self._port     = port
        self._baudrate = baudrate
        self._timeout  = timeout
        self._ser      = None   # serial.Serial 实例，open() 后赋值

    # ── Transport 接口实现 ────────────────────────────────────────────────

    def open(self) -> None:
        try:
            import serial
        except ImportError as e:
            raise ImportError(
                "pyserial 未安装，请执行：pip install pyserial"
            ) from e
        self._ser = serial.Serial(
            port=self._port,
            baudrate=self._baudrate,
            timeout=self._timeout,
        )

    def close(self) -> None:
        if self._ser and self._ser.is_open:
            self._ser.close()
        self._ser = None

    def send(self, data: bytes) -> None:
        if self._ser is None or not self._ser.is_open:
            raise RuntimeError("串口未打开，请先调用 open()")
        self._ser.write(data)

    def receive(self, size: int = 4096) -> bytes:
        if self._ser is None or not self._ser.is_open:
            return b""
        waiting = self._ser.in_waiting
        if waiting == 0:
            return b""
        return self._ser.read(min(waiting, size))

    # ── 额外便捷属性 ──────────────────────────────────────────────────────

    @property
    def is_open(self) -> bool:
        return self._ser is not None and self._ser.is_open

    @property
    def port(self) -> str:
        return self._port

    @staticmethod
    def list_ports() -> list[str]:
        """返回当前系统所有可用串口名称列表。"""
        try:
            from serial.tools import list_ports
            return [p.device for p in list_ports.comports()]
        except ImportError:
            return []