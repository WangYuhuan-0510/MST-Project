from __future__ import annotations

from pathlib import Path
from typing import Iterable, Tuple

import h5py
import numpy as np


def save_raw_hdf5(path: Path, x: Iterable[float], y: Iterable[float]) -> None:
    x_arr = np.asarray(list(x), dtype=float)
    y_arr = np.asarray(list(y), dtype=float)
    if x_arr.size != y_arr.size:
        raise ValueError("x/y size mismatch")

    with h5py.File(path, "w") as f:
        f.create_dataset("x", data=x_arr)
        f.create_dataset("y", data=y_arr)


def load_raw_hdf5(path: Path) -> Tuple[np.ndarray, np.ndarray]:
    with h5py.File(path, "r") as f:
        x = np.asarray(f["x"])
        y = np.asarray(f["y"])
    return x, y

