from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, Signal, QSize
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QLabel, QPushButton, QFrame, QHBoxLayout, QVBoxLayout, QSizePolicy

from mst.core.experiment_schema import get_experiment_type_config, normalize_experiment_type_id
from .ui_style import PALETTE


class ExperimentItem(QPushButton):
    clicked_experiment = Signal(str)

    def __init__(
        self,
        name: str,
        status: str = "draft",
        experiment_id: str | None = None,
        experiment_type_id: str | None = None,
        experiment_type_name: str | None = None,
        order_index: int = 1,
        parent=None,
    ):
        super().__init__(parent)
        self.experiment_id = str(experiment_id or "").strip()
        self.experiment_name = str(name or "未命名实验").strip() or "未命名实验"
        self.experiment_type_id = normalize_experiment_type_id(experiment_type_id or "pre_test")
        type_cfg = get_experiment_type_config(self.experiment_type_id)
        self.experiment_type_name = str(experiment_type_name or type_cfg.get("name") or "Pre-test")
        self.order_index = max(1, int(order_index or 1))
        self.icon_path = Path(__file__).resolve().parent / "icons" / f"{self.experiment_type_id}.svg"

        self.setCheckable(True)
        self.setFixedHeight(78)
        self.setCursor(Qt.PointingHandCursor)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        status_colors = {
            "draft": PALETTE["text_muted"],
            "running": PALETTE["warning"],
            "done": PALETTE["success"],
            "failed": PALETTE["danger"],
        }
        dot_color = status_colors.get(status, PALETTE["text_muted"])

        root = QVBoxLayout(self)
        root.setContentsMargins(12, 10, 12, 10)
        root.setSpacing(6)

        top_row = QHBoxLayout()
        top_row.setContentsMargins(0, 0, 0, 0)
        top_row.setSpacing(8)

        order_badge = QLabel(f"E{self.order_index:02d}")
        order_badge.setAlignment(Qt.AlignCenter)
        order_badge.setFixedSize(38, 20)
        order_badge.setStyleSheet(
            f"background: {PALETTE['bg_main']};"
            f"border: 1px solid {PALETTE['border']};"
            f"border-radius: 10px;"
            f"color: {PALETTE['accent_dim']};"
            "font-size: 10px;"
            "font-weight: 700;"
            "letter-spacing: 0.8px;"
        )
        order_badge.setAttribute(Qt.WA_TransparentForMouseEvents)

        icon_holder = QLabel()
        icon_holder.setFixedSize(22, 22)
        icon_holder.setAttribute(Qt.WA_TransparentForMouseEvents)
        pix = QPixmap(str(self.icon_path))
        if not pix.isNull():
            icon_holder.setPixmap(pix.scaled(QSize(18, 18), Qt.KeepAspectRatio, Qt.SmoothTransformation))
        else:
            icon_holder.setText(str(type_cfg.get("icon") or "◈"))
            icon_holder.setAlignment(Qt.AlignCenter)
            icon_holder.setStyleSheet(f"color: {PALETTE['accent']}; font-size: 16px; font-weight: 700;")

        type_lbl = QLabel(self.experiment_type_name)
        type_lbl.setStyleSheet(
            f"color: {PALETTE['text_secondary']}; font-size: 12px; font-weight: 700;"
            "letter-spacing: 0.2px;"
        )
        type_lbl.setAttribute(Qt.WA_TransparentForMouseEvents)

        status_dot = QLabel("●")
        status_dot.setStyleSheet(f"color: {dot_color}; font-size: 8px;")
        status_dot.setAttribute(Qt.WA_TransparentForMouseEvents)

        top_row.addWidget(order_badge, 0, Qt.AlignVCenter)
        top_row.addWidget(icon_holder, 0, Qt.AlignVCenter)
        top_row.addWidget(type_lbl, 1, Qt.AlignVCenter)
        top_row.addWidget(status_dot, 0, Qt.AlignVCenter)

        bottom_frame = QFrame()
        bottom_frame.setObjectName("bottomFrame")
        bottom_frame.setAttribute(Qt.WA_TransparentForMouseEvents)
        bottom_frame.setStyleSheet(f"""
            QFrame#bottomFrame {{
                background: rgba(255, 255, 255, 0.82);
                border: 1px solid {PALETTE['border']};
                border-radius: 11px;
            }}
        """)
        bottom_row = QHBoxLayout(bottom_frame)
        bottom_row.setContentsMargins(12, 8, 12, 8)
        bottom_row.setSpacing(8)

        name_lbl = QLabel(self.experiment_name)
        name_lbl.setStyleSheet(
            f"color: {PALETTE['text_primary']}; font-size: 13px; font-weight: 600;"
        )
        name_lbl.setAttribute(Qt.WA_TransparentForMouseEvents)
        bottom_row.addWidget(name_lbl, 1)

        root.addLayout(top_row)
        root.addWidget(bottom_frame)

        self.setStyleSheet(f"""
            QPushButton {{
                background: qlineargradient(
                    x1:0, y1:0, x2:1, y2:1,
                    stop:0 rgba(255, 255, 255, 0.72),
                    stop:1 rgba(234, 228, 240, 0.96)
                );
                border: 1px solid transparent;
                border-radius: 16px;
                text-align: left;
            }}
            QPushButton:hover  {{
                background: qlineargradient(
                    x1:0, y1:0, x2:1, y2:1,
                    stop:0 #FFFFFF,
                    stop:1 {PALETTE['bg_hover']}
                );
                border: 1px solid {PALETTE['border']};
            }}
            QPushButton:checked {{
                background: qlineargradient(
                    x1:0, y1:0, x2:1, y2:1,
                    stop:0 #FBF8FF,
                    stop:1 {PALETTE['bg_active']}
                );
                border: 1px solid {PALETTE['accent']};
            }}
            QPushButton:checked QFrame#bottomFrame {{
                background: rgba(255, 255, 255, 0.95);
                border: 1px solid {PALETTE['accent']};
            }}
        """)
