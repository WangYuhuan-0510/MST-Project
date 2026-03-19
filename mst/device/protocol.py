from __future__ import annotations

from dataclasses import dataclass


HEADER = 0xAA


@dataclass
class ProtocolFrame:
    command: int
    payload: bytes = b""

    def to_bytes(self) -> bytes:
        length = len(self.payload)
        checksum = (HEADER + self.command + length + sum(self.payload)) & 0xFF
        return bytes([HEADER, self.command, length]) + self.payload + bytes([checksum])

    @staticmethod
    def parse(raw: bytes) -> "ProtocolFrame":
        if len(raw) < 4:
            raise ValueError("frame too short")
        if raw[0] != HEADER:
            raise ValueError("invalid header")
        cmd = raw[1]
        length = raw[2]
        expected_len = 4 + length  # header(1)+cmd(1)+len(1)+payload+checksum(1)
        if len(raw) != expected_len:
            raise ValueError("invalid frame length")
        payload = raw[3 : 3 + length]
        checksum = raw[-1]
        calc = (HEADER + cmd + length + sum(payload)) & 0xFF
        if checksum != calc:
            raise ValueError("checksum mismatch")
        return ProtocolFrame(command=cmd, payload=payload)

