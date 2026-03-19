from __future__ import annotations

from dataclasses import dataclass
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

