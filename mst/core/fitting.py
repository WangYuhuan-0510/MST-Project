from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, List, Tuple

import numpy as np
from scipy.optimize import curve_fit


def binding_model(x: np.ndarray, kd: float, r_max: float) -> np.ndarray:
    """
    简单 1:1 结合模型： y = Rmax * x / (Kd + x)
    """

    return r_max * x / (kd + x)


@dataclass
class FitResult:
    kd: float
    r_max: float
    r_squared: float


def fit_binding_curve(x: Iterable[float], y: Iterable[float]) -> FitResult:
    """
    对给定数据进行 1:1 结合模型拟合。
    这是一个简化版本，主要用于单元测试。
    """

    x_arr = np.asarray(list(x), dtype=float)
    y_arr = np.asarray(list(y), dtype=float)

    if x_arr.size == 0 or y_arr.size == 0 or x_arr.size != y_arr.size:
        raise ValueError("invalid data for fitting")

    p0: Tuple[float, float] = (1.0, float(np.max(y_arr) if y_arr.size else 1.0))
    popt, _ = curve_fit(binding_model, x_arr, y_arr, p0=p0, maxfev=10000)
    kd, r_max = map(float, popt)

    y_fit = binding_model(x_arr, kd, r_max)
    ss_res = float(np.sum((y_arr - y_fit) ** 2))
    ss_tot = float(np.sum((y_arr - np.mean(y_arr)) ** 2))
    r_squared = 1 - ss_res / ss_tot if ss_tot != 0 else 0.0

    return FitResult(kd=kd, r_max=r_max, r_squared=r_squared)


def sigmoid_4pl(x: np.ndarray, bottom: float, top: float, ec50: float, hill: float) -> np.ndarray:
    x = np.asarray(x, dtype=float)
    x_safe = np.maximum(x, 1e-12)
    ec50_safe = max(float(ec50), 1e-12)
    return bottom + (top - bottom) / (1.0 + (x_safe / ec50_safe) ** (-hill))


@dataclass
class Fit4PLResult:
    bottom: float
    top: float
    ec50: float
    hill: float
    r_squared: float
    x_fit: List[float]
    y_fit: List[float]


def fit_4pl_curve(x: Iterable[float], y: Iterable[float]) -> Fit4PLResult:
    x_arr = np.asarray(list(x), dtype=float)
    y_arr = np.asarray(list(y), dtype=float)
    if x_arr.size == 0 or y_arr.size == 0 or x_arr.size != y_arr.size:
        raise ValueError("invalid data for fitting")
    if np.any(x_arr <= 0):
        raise ValueError("4PL requires x > 0 (log-scale concentrations)")

    # 初值：bottom/top 用分位数更稳，ec50 用中位数，hill=1
    bottom0 = float(np.percentile(y_arr, 5))
    top0 = float(np.percentile(y_arr, 95))
    ec500 = float(np.median(x_arr))
    hill0 = 1.0
    p0: Tuple[float, float, float, float] = (bottom0, top0, ec500, hill0)

    # 简单边界，避免跑飞
    bounds = (
        (-np.inf, -np.inf, float(np.min(x_arr)), 0.05),
        (np.inf, np.inf, float(np.max(x_arr)), 10.0),
    )
    popt, _ = curve_fit(sigmoid_4pl, x_arr, y_arr, p0=p0, bounds=bounds, maxfev=20000)
    bottom, top, ec50, hill = map(float, popt)

    y_pred = sigmoid_4pl(x_arr, bottom, top, ec50, hill)
    ss_res = float(np.sum((y_arr - y_pred) ** 2))
    ss_tot = float(np.sum((y_arr - np.mean(y_arr)) ** 2))
    r_squared = 1 - ss_res / ss_tot if ss_tot != 0 else 0.0

    x_dense = np.logspace(np.log10(float(np.min(x_arr))), np.log10(float(np.max(x_arr))), 200)
    y_dense = sigmoid_4pl(x_dense, bottom, top, ec50, hill)
    return Fit4PLResult(
        bottom=bottom,
        top=top,
        ec50=ec50,
        hill=hill,
        r_squared=r_squared,
        x_fit=x_dense.astype(float).tolist(),
        y_fit=y_dense.astype(float).tolist(),
    )

