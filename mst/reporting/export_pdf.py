from __future__ import annotations

from pathlib import Path
from typing import Iterable, Tuple

from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas


def export_simple_report(path: Path, title: str, kv: Iterable[Tuple[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    c = canvas.Canvas(str(path), pagesize=A4)
    width, height = A4

    y = height - 72
    c.setFont("Helvetica-Bold", 16)
    c.drawString(72, y, title)
    y -= 36

    c.setFont("Helvetica", 11)
    for k, v in kv:
        c.drawString(72, y, f"{k}: {v}")
        y -= 18
        if y < 72:
            c.showPage()
            y = height - 72
            c.setFont("Helvetica", 11)

    c.save()

