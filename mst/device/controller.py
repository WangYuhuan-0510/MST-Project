from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from .protocol import ProtocolFrame
from .transport import Transport


@dataclass
class DeviceController:
    """
    设备高层控制接口，占位实现。
    """

    transport: Transport

    def connect(self) -> None:
        self.transport.open()

    def disconnect(self) -> None:
        self.transport.close()

    def start_experiment(self) -> None:
        frame = ProtocolFrame(command=0x01)
        self.transport.send(frame.to_bytes())

    def stop_experiment(self) -> None:
        frame = ProtocolFrame(command=0x02)
        self.transport.send(frame.to_bytes())

    def read_status(self) -> Optional[bytes]:
        data = self.transport.receive()
        return data or None

