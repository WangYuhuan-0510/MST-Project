from __future__ import annotations

import csv
from pathlib import Path
from typing import Iterable, Tuple


def export_xy_csv(path: Path, rows: Iterable[Tuple[float, float]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["x", "y"])
        for x, y in rows:
            w.writerow([x, y])

