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
CMD_DATA_FRAME = 0x10   # STM32 → 主机：旧版多通道荧光数据帧（兼容保留）
CMD_MST_DATA   = 0x15   # STM32 → 主机：MST 单点数据帧（当前使用）
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

@dataclass(frozen=True)
class MSTDataSample:
    """解析后的 MST 单点数据"""
    t_ms:     int      # 时间戳 (毫秒)
    distance: float    # 扫描距离 (还原后的小数)
    fluo:     int      # 荧光强度
    reserved: int      # 预留位数据

def parse_mst_frame(frame: ProtocolFrame) -> MSTDataSample:
    """
    解析 CMD_MST_DATA 帧。
    Payload 格式 (< 代表小端模式):
      [I: uint32 t_ms] [H: uint16 pos] [H: uint16 fluo] [I: uint32 reserved]
    """
    if frame.command != CMD_MST_DATA:
        raise ValueError(f"命令字错误：期望 0x{CMD_MST_DATA:02X}，实际 0x{frame.command:02X}")
    if len(frame.payload) != 12:
        raise ValueError(f"MST 数据帧 payload 长度不足：期望 12，实际 {len(frame.payload)}")
    
    # 使用 struct 解包：I=4字节无符号，H=2字节无符号
    t_ms, pos_raw, fluo, reserved = struct.unpack_from("<I H H I", frame.payload, 0)
    
    # 还原距离数据
    distance = pos_raw / 100.0
    
    return MSTDataSample(t_ms=t_ms, distance=distance, fluo=fluo, reserved=reserved)