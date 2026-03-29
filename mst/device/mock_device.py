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
        if frame.command == 0x01:
            reply = ProtocolFrame(command=0x81, payload=b"\x01")
        elif frame.command == 0x02:
            reply = ProtocolFrame(command=0x82, payload=b"\x00")
        else:
            reply = ProtocolFrame(command=0xFF, payload=b"")
        self.transport.send(reply.to_bytes())


@dataclass(frozen=True)
class MockMSTRun:
    """
    用 mock_device 生成的一次"采集结果"。

    字段
    ────
    t_s           : 时间轴（秒），0 对应 IR 开启时刻
    traces        : traces[i][j] = F_i(t_j)（绝对荧光值）
    concentrations: 每通道浓度（用于 dose-response）
    scan_center   : 每通道峰顶荧光（用于 capillary scan 图）
    t_ir_on_s     : IR 开启时刻（时间轴上的 0，默认 0.0）
    t_ir_off_s    : IR 关闭时刻（默认 20.0 s）
    """

    t_s: List[float]
    traces: List[List[float]]
    concentrations: List[float]
    scan_center: List[float]
    t_ir_on_s: float = 0.0
    t_ir_off_s: float = 20.0


def simulate_mst_time_fluorescence(
    *,
    n_capillaries: int = 16,
    t_start_s: float = -5.0,
    t_end_s: float = 25.0,
    dt_s: float = 0.1,
    t_ir_on_s: float = 0.0,
    t_ir_off_s: float = 20.0,
    noise_std: float = 0.003,        # 相对噪声（占 F0 的比例）
    # 4PL 参数（生成各通道"结合程度"，映射到热泳幅度）
    bottom: float = 0.2,
    top: float = 1.0,
    ec50: float = 2.0,
    hill: float = 1.2,
    # TRIC 物理参数
    t_jump_ratio: float = -0.12   # T-jump幅度（负值=下降）
    t_jump_tau: float = 0.05      # T-jump恢复时间（很快）
    tau_fast: float = 0.4,           # TRIC 快分量时间常数（s）
    alpha_fast: float = 0.35,        # 快分量占比
    decay_range: tuple = (0.84, 0.92),   # 各通道稳态比范围
    tau_slow_range: tuple = (3.0, 7.0),  # 各通道热泳慢分量 τ 范围（s）
    tau_recovery: float = 3.0,       # IR 关闭后回升时间常数（s）
) -> MockMSTRun:
    """
    生成符合 TRIC 物理过程的 MST 荧光时间曲线。

    信号模型（t 为相对 IR 开启的时间，单位 s）
    ───────────────────────────────────────────
    预热段（t < 0）：
        F(t) = F0                         ← 平稳基线

    加热段（0 ≤ t < t_ir_off）：
        F(t) = F0 * { d
                    + (1 - d) * [ α   * exp(-t / τ_fast)    ← TRIC 快速跌落
                                + (1-α) * exp(-t / τ_slow) ] ← 热泳慢变
                    }
        其中 d = 稳态比（每通道略不同），τ_slow 随结合程度变化

    回升段（t ≥ t_ir_off）：
        F(t) = F0 - (F0 - F_off) * exp(-(t - t_ir_off) / τ_rec)
        F_off = t_ir_off 时刻的荧光值

    scan_center：
        取各通道 F0（预热段均值），与 STM32 发送逻辑一致
    """
    if n_capillaries <= 0:
        raise ValueError("n_capillaries must be > 0")
    if dt_s <= 0:
        raise ValueError("dt_s must be > 0")
    if t_end_s <= t_start_s:
        raise ValueError("t_end_s must be > t_start_s")

    rng = np.random.default_rng(seed=42)

    t = np.arange(t_start_s, t_end_s + 1e-12, dt_s, dtype=float)
    concentrations = np.logspace(-2, 1, n_capillaries).astype(float)

    # ── 各通道基线荧光（scan_center 来源） ──
    base_F0 = 100.0
    drift = np.linspace(-5.0, 5.0, n_capillaries)   # 通道间 ±5% 漂移
    F0_arr = base_F0 + drift + rng.normal(0.0, 2.0, n_capillaries)
    F0_arr = np.clip(F0_arr, 80.0, 120.0)
    scan_center = F0_arr.tolist()

    # ── 4PL：结合程度 → 热泳幅度（影响 τ_slow 和稳态比 d） ──
    x_safe   = np.maximum(concentrations, 1e-12)
    ec50_safe = max(float(ec50), 1e-12)
    bind = bottom + (top - bottom) / (1.0 + (x_safe / ec50_safe) ** (-hill))

    traces: List[List[float]] = []

    for i in range(n_capillaries):
        F0 = float(F0_arr[i])
        b  = float(bind[i])

        # 稳态比：结合程度越高 → 衰减越深（d 越小）
        d_lo, d_hi = decay_range
        d = d_hi - b * (d_hi - d_lo)           # bind=0→d_hi, bind=1→d_lo
        d = float(np.clip(d, d_lo, d_hi))

        # 热泳慢分量 τ：结合程度越高 → τ 越长（衰减越慢）
        ts_lo, ts_hi = tau_slow_range
        tau_slow = ts_lo + b * (ts_hi - ts_lo)

        # 计算 IR 关闭时的荧光值（用于回升段初始值）
        T_off = t_ir_off_s - t_ir_on_s
        fast_off = alpha_fast * np.exp(-T_off / tau_fast)
        slow_off = (1.0 - alpha_fast) * np.exp(-T_off / tau_slow)
        F_off = F0 * (d + (1.0 - d) * (fast_off + slow_off))

        y = np.empty_like(t)
        for j, tj in enumerate(t):
            t_rel = tj - t_ir_on_s

            if t_rel < 0.0:
                # 预热段：平稳基线
                Fj = F0

            elif t_rel < T_off:
                # 1. T-jump（瞬间变化 + 快速恢复）
                 t_jump = t_jump_ratio * np.exp(-t_rel / t_jump_tau)
                # 2. Thermophoresis（慢变化）
                fast = alpha_fast * np.exp(-t_rel / tau_fast)
                slow = (1.0 - alpha_fast) * np.exp(-t_rel / tau_slow)
                thermo = (d + (1.0 - d) * (fast + slow)) - 1.0
                # 3. 合成
                Fj = F0 * (1.0 + t_jump + thermo)

            else:
                # 回升段：指数恢复至 F0
                t_off = t_rel - T_off
                Fj = F0 - (F0 - F_off) * np.exp(-t_off / tau_recovery)

            # 相对噪声
            Fj += float(rng.normal(0.0, F0 * noise_std))
            y[j] = max(0.0, Fj)

        traces.append(y.astype(float).tolist())

    return MockMSTRun(
        t_s=t.astype(float).tolist(),
        traces=traces,
        concentrations=concentrations.astype(float).tolist(),
        scan_center=scan_center,
        t_ir_on_s=float(t_ir_on_s),
        t_ir_off_s=float(t_ir_off_s),
    )