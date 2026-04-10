from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, Signal, QSize
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QLabel, QPushButton, QFrame, QHBoxLayout, QVBoxLayout, QSizePolicy,
)

from mst.core.experiment_schema import get_experiment_type_config, normalize_experiment_type_id
from .ui_style import PALETTE


class ExperimentItem(QPushButton):
    clicked_experiment = Signal(str)
    rename_requested = Signal(str)
    delete_requested = Signal(str)

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
        self.experiment_name = str(name or "Experiment 1").strip() or "Experiment 1"
        self.experiment_type_id = normalize_experiment_type_id(experiment_type_id or "pre_test")
        type_cfg = get_experiment_type_config(self.experiment_type_id)
        self.experiment_type_name = str(experiment_type_name or type_cfg.get("name") or "Pre-test")
        self.order_index = max(1, int(order_index or 1))
        self.icon_path = Path(__file__).resolve().parent / "icons" / f"{self.experiment_type_id}.svg"

        self.setCheckable(True)
        self.setFixedHeight(92)
        self.setCursor(Qt.PointingHandCursor)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        top_frame = QFrame()
        top_frame.setObjectName("topFrame")
        top_frame.setFixedHeight(42)
        top_row = QHBoxLayout(top_frame)
        top_row.setContentsMargins(0, 0, 8, 0)
        top_row.setSpacing(8)

        order_badge = QLabel(str(self.order_index))
        order_badge.setAlignment(Qt.AlignCenter)
        order_badge.setFixedSize(40, 40)
        order_badge.setAttribute(Qt.WA_TransparentForMouseEvents)
        order_badge.setStyleSheet(
            f"background: {PALETTE['bg_card']};"
            "border-radius: 0px;"
            f"color: {PALETTE['text_primary']};"
            "font-size: 14px;"
            "font-weight: 500;"
        )

        icon_holder = QLabel()
        icon_holder.setFixedSize(26, 26)
        icon_holder.setAttribute(Qt.WA_TransparentForMouseEvents)
        pix = QPixmap(str(self.icon_path))
        if not pix.isNull():
            icon_holder.setPixmap(pix.scaled(QSize(22, 22), Qt.KeepAspectRatio, Qt.SmoothTransformation))
        else:
            icon_holder.setText(str(type_cfg.get("icon") or "◈"))
            icon_holder.setAlignment(Qt.AlignCenter)
            icon_holder.setStyleSheet(
                f"color: {PALETTE['bg_card']}; font-size: 16px; font-weight: 700;"
            )

        type_lbl = QLabel(self.experiment_type_name)
        type_lbl.setAttribute(Qt.WA_TransparentForMouseEvents)
        type_lbl.setStyleSheet(
            f"color: {PALETTE['bg_card']}; font-size: 12px; font-weight: 400;"
        )

        top_row.addWidget(order_badge)
        top_row.addSpacing(2)
        top_row.addWidget(icon_holder, 0, Qt.AlignVCenter)
        top_row.addWidget(type_lbl, 1, Qt.AlignVCenter)

        self.delete_btn = QPushButton("×")
        self.delete_btn.setFixedSize(22, 22)
        self.delete_btn.setCursor(Qt.PointingHandCursor)
        self.delete_btn.setToolTip("删除实验")
        self.delete_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                border: none;
                color: {PALETTE['bg_card']};
                font-size: 18px;
                font-weight: 700;
                padding: 0;
            }}
            QPushButton:hover {{
                color: {PALETTE['bg_card']};
            }}
        """)
        self.delete_btn.clicked.connect(self._emit_delete_requested)
        top_row.addWidget(self.delete_btn, 0, Qt.AlignVCenter)

        bottom_frame = QFrame()
        bottom_frame.setObjectName("bottomFrame")
        bottom_row = QHBoxLayout(bottom_frame)
        bottom_row.setContentsMargins(0, 10, 8, 10)
        bottom_row.setSpacing(8)

        bottom_row.addSpacing(48)

        self.name_lbl = QLabel(self.experiment_name)
        self.name_lbl.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.name_lbl.setStyleSheet(
            f"color: {PALETTE['text_muted']}; font-size: 11px; font-style: italic; font-weight: 400;"
        )
        bottom_row.addWidget(self.name_lbl, 1, Qt.AlignVCenter)

        self.rename_btn = QPushButton("✎")
        self.rename_btn.setFixedSize(20, 20)
        self.rename_btn.setCursor(Qt.PointingHandCursor)
        self.rename_btn.setToolTip("修改实验名称")
        self.rename_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                border: none;
                color: {PALETTE['text_muted']};
                font-size: 13px;
                font-weight: 700;
                padding: 0;
            }}
            QPushButton:hover {{
                color: {PALETTE['accent']};
            }}
        """)
        self.rename_btn.clicked.connect(self._emit_rename_requested)
        bottom_row.addWidget(self.rename_btn, 0, Qt.AlignVCenter)

        root.addWidget(top_frame)
        root.addWidget(bottom_frame)

        self.setStyleSheet(f"""
            QPushButton {{
                background: {PALETTE['bg_card']};
                border: 1px solid {PALETTE['border']};
                border-radius: 4px;
                text-align: left;
            }}
            QPushButton:hover {{
                border-color: {PALETTE['accent']};
            }}
            QPushButton:checked {{
                background: {PALETTE['bg_active']};
                border-color: {PALETTE['accent']};
            }}
            QPushButton QFrame#topFrame {{
                background: {PALETTE['text_secondary']};
                border-top-left-radius: 3px;
                border-top-right-radius: 3px;
            }}
            QPushButton QFrame#bottomFrame {{
                background: {PALETTE['text_primary']};
                border-bottom-left-radius: 3px;
                border-bottom-right-radius: 3px;
            }}
            QPushButton:checked QFrame#topFrame {{
                background: {PALETTE['accent']};
            }}
            QPushButton:checked QFrame#bottomFrame {{
                background: {PALETTE['accent_dim']};
            }}
            QPushButton:checked QLabel {{
                color: {PALETTE['bg_card']};
            }}
            QPushButton:checked QLabel[role="orderBadge"] {{
                color: {PALETTE['text_primary']};
            }}
        """)
        order_badge.setProperty("role", "orderBadge")
        self.name_lbl.setStyleSheet(
            f"color: {PALETTE['bg_hover']}; font-size: 11px; font-style: italic; font-weight: 400;"
        )

    def _emit_rename_requested(self) -> None:
        if self.experiment_id:
            self.rename_requested.emit(self.experiment_id)

    def _emit_delete_requested(self) -> None:
        if self.experiment_id:
            self.delete_requested.emit(self.experiment_id)

    def mouseReleaseEvent(self, event) -> None:  # noqa: N802
        super().mouseReleaseEvent(event)
        if self.experiment_id:
            self.clicked_experiment.emit(self.experiment_id)
