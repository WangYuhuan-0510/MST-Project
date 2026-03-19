from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, List, Sequence, Tuple

import numpy as np


@dataclass
class ProcessedSignal:
    x: List[float]
    y: List[float]


def moving_average(data: Iterable[float], window: int = 5) -> ProcessedSignal:
    """
    简单移动平均滤波，用于单元测试和占位。
    """

    arr = np.asarray(list(data), dtype=float)
    if window <= 1 or len(arr) == 0:
        return ProcessedSignal(x=list(range(len(arr))), y=arr.tolist())
    kernel = np.ones(window) / window
    filtered = np.convolve(arr, kernel, mode="valid")
    x = list(range(len(filtered)))
    return ProcessedSignal(x=x, y=filtered.tolist())


def nearest_index(x: Sequence[float], x0: float) -> int:
    """
    返回序列中最接近 x0 的索引。
    """

    if not x:
        raise ValueError("x is empty")
    arr = np.asarray(list(x), dtype=float)
    return int(np.argmin(np.abs(arr - float(x0))))


def extract_feature_at_time(
    t_s: Sequence[float],
    traces: Sequence[Sequence[float]],
    *,
    t_feature_s: float,
) -> List[float]:
    """
    从每根毛细管的 trace 中提取某个时间点的特征值（默认就是 F(t_feature)）。
    """

    j = nearest_index(t_s, float(t_feature_s))
    out: List[float] = []
    for tr in traces:
        if j >= len(tr):
            out.append(float("nan"))
        else:
            out.append(float(tr[j]))
    return out


def extract_delta_over_f(
    t_s: Sequence[float],
    traces: Sequence[Sequence[float]],
    *,
    t0_s: float,
    t1_s: float,
) -> List[float]:
    """
    常见 MST 特征：ΔF/F = (F(t1) - F(t0)) / F(t0)
    """

    j0 = nearest_index(t_s, float(t0_s))
    j1 = nearest_index(t_s, float(t1_s))
    out: List[float] = []
    for tr in traces:
        if j0 >= len(tr) or j1 >= len(tr):
            out.append(float("nan"))
            continue
        f0 = float(tr[j0])
        f1 = float(tr[j1])
        if f0 == 0:
            out.append(float("nan"))
        else:
            out.append((f1 - f0) / f0)
    return out

