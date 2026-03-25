from __future__ import annotations

import struct
from dataclasses import dataclass
from typing import List


HEADER = 0xAA

# ── 命令字定义 ────────────────────────────────────────────────────────────────
CMD_START      = 0x01   # 主机 → STM32：开始采集
CMD_STOP       = 0x02   # 主机 → STM32：停止采集
CMD_ACK_START  = 0x81   # STM32 → 主机：开始确认
CMD_ACK_STOP   = 0x82   # STM32 → 主机：停止确认
CMD_DATA_FRAME = 0x10   # STM32 → 主机：荧光数据帧（主要数据命令）
CMD_ERROR      = 0xFF   # STM32 → 主机：错误回包

# ── 数据帧 PAYLOAD 格式（CMD=0x10）────────────────────────────────────────────
# [t_ms : uint32, 4 bytes] + [ch0..chN-1 : float32, 4×N bytes]
# 总长度 = 4 + 4*N bytes
# 默认 N=16 通道（对应 MockMSTRun 的 16 根毛细管）
N_CHANNELS = 16


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


@dataclass(frozen=True)
class DataSample:
    """解析后的一帧采样数据。"""
    t_ms:     int          # 时间戳，单位毫秒（来自 STM32 的 HAL_GetTick()）
    channels: List[float]  # 各通道荧光值，长度 = N_CHANNELS


def parse_data_frame(frame: ProtocolFrame) -> DataSample:
    """
    从 CMD_DATA_FRAME 帧中解析出 DataSample。

    PAYLOAD 格式（小端）：
      [uint32 t_ms][float32 ch0][float32 ch1]...[float32 ch_{N-1}]
    共 4 + 4*N_CHANNELS = 68 bytes（N=16 时）
    """
    expected = 4 + 4 * N_CHANNELS
    if len(frame.payload) < expected:
        raise ValueError(
            f"数据帧 payload 长度不足：期望 {expected}，实际 {len(frame.payload)}"
        )
    t_ms = struct.unpack_from("<I", frame.payload, 0)[0]
    channels = list(struct.unpack_from(f"<{N_CHANNELS}f", frame.payload, 4))
    return DataSample(t_ms=t_ms, channels=channels)


def build_start_frame() -> bytes:
    return ProtocolFrame(command=CMD_START).to_bytes()


def build_stop_frame() -> bytes:
    return ProtocolFrame(command=CMD_STOP).to_bytes()