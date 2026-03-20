from __future__ import annotations

from dataclasses import dataclass
from typing import List, Sequence

import numpy as np

from .protocol import ProtocolFrame
from .transport import MockTransport


@dataclass
class MockDevice:
    """
    简单的模拟设备，直接与 `MockTransport` 交互。
    主要用于开发阶段联调和单元测试。
    """

    transport: MockTransport

    def step(self) -> None:
        raw = self.transport.receive()
        if not raw:
            return
        frame = ProtocolFrame.parse(raw)
        # 根据命令生成一个简单的回包，这里仅占位
        if frame.command == 0x01:  # start
            reply = ProtocolFrame(command=0x81, payload=b"\x01")
        elif frame.command == 0x02:  # stop
            reply = ProtocolFrame(command=0x82, payload=b"\x00")
        else:
            reply = ProtocolFrame(command=0xFF, payload=b"")
        self.transport.send(reply.to_bytes())


@dataclass(frozen=True)
class MockMSTRun:
    """
    用 mock_device 生成的一次“采集结果”（time + fluorescence）。

    - t_s: 时间轴（秒）
    - traces: 每根毛细管的荧光时间序列 traces[i][j] = F_i(t_j)
    - concentrations: 每根毛细管对应浓度（用于 dose-response）
    - scan_center: 每根毛细管中心荧光（用于 capillary scan 图）
    - t_ir_on_s: 红外激光开启时间（默认 0s）
    """

    t_s: List[float]
    traces: List[List[float]]
    concentrations: List[float]
    scan_center: List[float]
    t_ir_on_s: float = 0.0


def simulate_mst_time_fluorescence(
    *,
    n_capillaries: int = 16,
    t_start_s: float = -5.0,
    t_end_s: float = 25.0,
    dt_s: float = 0.1,
    t_ir_on_s: float = 0.0,
    noise_std: float = 0.01,
    # 4PL 参数（用于生成“结合程度”，再映射到热泳幅度）
    bottom: float = 0.2,
    top: float = 1.0,
    ec50: float = 2.0,
    hill: float = 1.2,
) -> MockMSTRun:
    if n_capillaries <= 0:
        raise ValueError("n_capillaries must be > 0")
    if dt_s <= 0:
        raise ValueError("dt_s must be > 0")
    if t_end_s <= t_start_s:
        raise ValueError("t_end_s must be > t_start_s")

    t = np.arange(t_start_s, t_end_s + 1e-12, dt_s, dtype=float)
    concentrations = np.logspace(-2, 1, n_capillaries).astype(float)

    # 模拟 scan center：沿扫描方向多段类高斯峰（探测器移动连续采样），连线作 capillary scan 曲线
    base = 800.0
    drift = np.linspace(-40, 40, n_capillaries)
    i = np.arange(n_capillaries, dtype=float)
    denom = max(n_capillaries - 1, 1)
    peaks = 35.0 * np.sin((i / denom) * np.pi * 4.0) ** 2
    scan_center = (base + drift + peaks + np.random.normal(0.0, 8.0, n_capillaries)).astype(float)

    # 4PL 生成 binding 程度，再映射到 trace 幅度
    x_safe = np.maximum(concentrations, 1e-12)
    ec50_safe = max(float(ec50), 1e-12)
    bind = bottom + (top - bottom) / (1.0 + (x_safe / ec50_safe) ** (-hill))

    traces: List[List[float]] = []
    for i in range(n_capillaries):
        baseline = 1.0 + 0.002 * (i - n_capillaries / 2)
        tau = 0.7 + 0.03 * i
        amp = 0.12 + 0.25 * float(bind[i])
        y = np.empty_like(t)
        for j, tj in enumerate(t):
            if tj < t_ir_on_s:
                yj = baseline
            else:
                yj = baseline - amp * (1.0 - np.exp(-(tj - t_ir_on_s) / tau))
            if noise_std > 0:
                yj += float(np.random.normal(0.0, noise_std))
            y[j] = yj
        traces.append(y.astype(float).tolist())

    return MockMSTRun(
        t_s=t.astype(float).tolist(),
        traces=traces,
        concentrations=concentrations.astype(float).tolist(),
        scan_center=scan_center.astype(float).tolist(),
        t_ir_on_s=float(t_ir_on_s),
    )

