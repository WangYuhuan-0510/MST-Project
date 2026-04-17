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
        is_dirty: bool = False,
        parent=None,
    ):
        super().__init__(parent)
        self.experiment_id = str(experiment_id or "").strip()
        self.experiment_name = str(name or "未命名实验").strip() or "未命名实验"
        self.experiment_type_id = normalize_experiment_type_id(experiment_type_id or "pre_test")
        type_cfg = get_experiment_type_config(self.experiment_type_id)
        default_type_name = str(type_cfg.get("name") or "Pre-test")
        self.experiment_type_name = str(experiment_type_name or default_type_name or "Pre-test")
        if self.experiment_type_name.casefold() == "binding test":
            self.experiment_type_name = "binding check"
        self.order_index = max(1, int(order_index or 1))
        self.is_dirty = bool(is_dirty)
        self.icon_path = Path(__file__).resolve().parent / "icons" / f"{self.experiment_type_id}.svg"

        status_colors = {
            "draft": PALETTE["text_muted"],
            "running": PALETTE["warning"],
            "done": PALETTE["success"],
            "failed": PALETTE["danger"],
        }
        dot_color = status_colors.get(status, PALETTE["text_muted"])

        self.setCheckable(True)
        self.setFixedHeight(80)
        self.setCursor(Qt.PointingHandCursor)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        outer_frame = QFrame()
        self.outer_frame = outer_frame
        outer_frame.setObjectName("outerFrame")
        outer_layout = QHBoxLayout(outer_frame)
        outer_layout.setContentsMargins(0, 0, 0, 0)
        outer_layout.setSpacing(0)

        number_frame = QFrame()
        self.number_frame = number_frame
        number_frame.setObjectName("numberFrame")
        number_frame.setFixedWidth(30)
        number_layout = QVBoxLayout(number_frame)
        number_layout.setContentsMargins(0, 0, 6, 0)
        number_layout.setSpacing(0)
        number_layout.addStretch(1)

        order_lbl = QLabel(str(self.order_index))
        self.order_lbl = order_lbl
        order_lbl.setObjectName("orderLabel")
        order_lbl.setAlignment(Qt.AlignCenter)
        order_lbl.setAttribute(Qt.WA_TransparentForMouseEvents)
        order_lbl.setStyleSheet(
            f"color: {PALETTE['text_primary']};"
            "background: transparent;"
            "font-size: 22px;"
            "font-weight: 500;"
        )
        number_layout.addWidget(order_lbl, 0, Qt.AlignCenter)
        number_layout.addStretch(1)

        content_wrap = QFrame()
        self.content_wrap = content_wrap
        content_wrap.setObjectName("contentWrap")
        content_layout = QVBoxLayout(content_wrap)
        content_layout.setContentsMargins(0, 1, 1, 1)
        content_layout.setSpacing(0)

        top_frame = QFrame()
        self.top_frame = top_frame
        top_frame.setObjectName("topFrame")
        top_row = QHBoxLayout(top_frame)
        top_row.setContentsMargins(8, 6, 6, 6)
        top_row.setSpacing(6)

        icon_holder = QLabel()
        icon_holder.setFixedSize(22, 14)
        icon_holder.setAttribute(Qt.WA_TransparentForMouseEvents)
        icon_holder.setStyleSheet("background: transparent;")
        pix = QPixmap(str(self.icon_path))
        if not pix.isNull():
            icon_holder.setPixmap(pix.scaled(QSize(22, 14), Qt.KeepAspectRatio, Qt.SmoothTransformation))
        else:
            icon_holder.setText(str(type_cfg.get("icon") or "◈"))
            icon_holder.setAlignment(Qt.AlignCenter)
            icon_holder.setStyleSheet(
                f"background: transparent; color: {PALETTE['accent']}; font-size: 16px; font-weight: 700;"
            )

        type_lbl = QLabel(self.experiment_type_name)
        self.type_lbl = type_lbl
        type_lbl.setObjectName("typeLabel")
        type_lbl.setAttribute(Qt.WA_TransparentForMouseEvents)
        type_lbl.setMinimumWidth(0)
        type_lbl.setWordWrap(False)
        type_lbl.setStyleSheet(
            f"color: {PALETTE['text_secondary']};"
            "background: transparent;"
            "font-size: 14px;"
            "font-weight: 500;"
        )

        dirty_mark = QLabel("*")
        self.dirty_mark = dirty_mark
        dirty_mark.setVisible(self.is_dirty)
        dirty_mark.setAttribute(Qt.WA_TransparentForMouseEvents)
        dirty_mark.setStyleSheet(
            f"color: {PALETTE['accent']};"
            "background: transparent;"
            "font-size: 14px;"
            "font-weight: 800;"
            "padding: 0 1px;"
        )

        status_dot = QLabel("●")
        self.status_dot = status_dot
        status_dot.setFixedWidth(8)
        status_dot.setStyleSheet(f"color: {dot_color}; background: transparent; font-size: 8px;")
        status_dot.setAttribute(Qt.WA_TransparentForMouseEvents)

        self.delete_btn = QPushButton("×")
        self.delete_btn.setObjectName("deleteBtn")
        self.delete_btn.setFixedSize(18, 18)
        self.delete_btn.setCursor(Qt.PointingHandCursor)
        self.delete_btn.setToolTip("删除实验")
        self.delete_btn.clicked.connect(self._emit_delete_requested)

        top_row.addWidget(icon_holder, 0, Qt.AlignVCenter)
        top_row.addWidget(type_lbl, 1, Qt.AlignVCenter)
        top_row.addWidget(dirty_mark, 0, Qt.AlignVCenter)
        top_row.addWidget(self.delete_btn, 0, Qt.AlignVCenter)

        divider = QFrame()
        self.divider = divider
        divider.setObjectName("midDivider")
        divider.setFixedHeight(1)

        bottom_frame = QFrame()
        self.bottom_frame = bottom_frame
        bottom_frame.setObjectName("bottomFrame")
        bottom_row = QHBoxLayout(bottom_frame)
        bottom_row.setContentsMargins(12, 4, 8, 4)
        bottom_row.setSpacing(8)

        self.name_lbl = QLabel(self.experiment_name)
        self.name_lbl.setObjectName("nameLabel")
        self.name_lbl.setStyleSheet(
            f"color: {PALETTE['text_primary']};"
            "background: transparent;"
            "font-size: 13px;"
            "font-style: italic;"
            "font-weight: 500;"
        )
        self.name_lbl.setAlignment(Qt.AlignCenter)
        self.name_lbl.setAttribute(Qt.WA_TransparentForMouseEvents)

        self.rename_btn = QPushButton("✎")
        self.rename_btn.setObjectName("renameBtn")
        self.rename_btn.setFixedSize(18, 18)
        self.rename_btn.setCursor(Qt.PointingHandCursor)
        self.rename_btn.setToolTip("修改实验名称")
        self.rename_btn.clicked.connect(self._emit_rename_requested)

        bottom_row.addStretch(1)
        bottom_row.addWidget(self.name_lbl, 0, Qt.AlignCenter)
        bottom_row.addStretch(1)
        bottom_row.addWidget(self.rename_btn, 0, Qt.AlignRight | Qt.AlignVCenter)

        content_layout.addWidget(top_frame)
        content_layout.addWidget(divider)
        content_layout.addWidget(bottom_frame)

        outer_layout.addWidget(number_frame, 0)
        outer_layout.addWidget(content_wrap, 1)
        root.addWidget(outer_frame)

        self.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                border: none;
                text-align: left;
            }}
            QFrame#outerFrame {{
                background: transparent;
                border: 1px solid {PALETTE['border_active']};
                border-radius: 16px;
            }}
            QFrame#numberFrame {{
                background: transparent;
                border: none;
                border-right: 1px solid {PALETTE['border_active']};
            }}
            QFrame#contentWrap {{
                background: transparent;
                border: none;
            }}
            QLabel {{
                background: transparent;
                border: none;
            }}
            QPushButton#deleteBtn,
            QPushButton#renameBtn {{
                background: transparent;
                border: none;
                border-radius: 10px;
                color: {PALETTE['text_muted']};
                font-size: 12px;
                font-weight: 700;
                text-align: center;
                padding: 0;
            }}
            QPushButton#deleteBtn:hover {{
                background: #FFF0F1;
                color: {PALETTE['danger']};
                border: 1px solid {PALETTE['danger']};
            }}
            QPushButton#deleteBtn:pressed {{
                background: #FFE0E3;
            }}
            QPushButton#renameBtn:hover {{
                background: {PALETTE['bg_hover']};
                color: {PALETTE['accent']};
                border: 1px solid {PALETTE['border']};
            }}
            QPushButton#renameBtn:pressed {{
                background: {PALETTE['bg_active']};
            }}
        """)
        self._apply_selection_style(self.isChecked())

    def _apply_selection_style(self, checked: bool) -> None:
        border_color = PALETTE['accent'] if checked else PALETTE['border_active']
        top_bg = PALETTE['accent'] if checked else '#FFFFFF'
        bottom_bg = PALETTE['accent'] if checked else PALETTE['bg_active']
        type_color = '#FFFFFF' if checked else PALETTE['text_secondary']
        name_color = '#FFFFFF' if checked else PALETTE['text_primary']

        self.outer_frame.setStyleSheet(
            f"background: transparent; border: 1px solid {border_color}; border-radius: 16px;"
        )
        self.number_frame.setStyleSheet(
            f"background: transparent; border: none; border-right: 1px solid {border_color};"
        )
        self.content_wrap.setStyleSheet(
            "background: transparent; border: none;"
        )
        self.top_frame.setStyleSheet(
            f"background: {top_bg}; border: none; border-top-left-radius: 0px; border-top-right-radius: 15px; border-bottom-left-radius: 0px; border-bottom-right-radius: 0px;"
        )
        self.divider.setStyleSheet(f"background: {border_color}; border: none;")
        self.bottom_frame.setStyleSheet(
            f"background: {bottom_bg}; border: none; border-top-left-radius: 0px; border-top-right-radius: 0px; border-bottom-left-radius: 0px; border-bottom-right-radius: 15px;"
        )
        self.type_lbl.setStyleSheet(
            f"color: {type_color}; background: transparent; font-size: 14px; font-weight: 500;"
        )
        self.name_lbl.setStyleSheet(
            f"color: {name_color}; background: transparent; font-size: 13px; font-style: italic; font-weight: 500;"
        )

    def setChecked(self, checked: bool) -> None:
        super().setChecked(checked)
        self._apply_selection_style(bool(checked))

    def _emit_rename_requested(self) -> None:
        if self.experiment_id:
            self.rename_requested.emit(self.experiment_id)

    def update_display(self, *, name: str, status: str, experiment_type_id: str, experiment_type_name: str, order_index: int, is_dirty: bool) -> None:
        self.experiment_name = str(name or "未命名实验").strip() or "未命名实验"
        self.experiment_type_id = normalize_experiment_type_id(experiment_type_id or "pre_test")
        self.experiment_type_name = str(experiment_type_name or get_experiment_type_config(self.experiment_type_id).get("name") or "Pre-test")
        if self.experiment_type_name.casefold() == "binding test":
            self.experiment_type_name = "binding check"
        self.order_index = max(1, int(order_index or 1))
        self.is_dirty = bool(is_dirty)

        status_colors = {
            "draft": PALETTE["text_muted"],
            "running": PALETTE["warning"],
            "done": PALETTE["success"],
            "failed": PALETTE["danger"],
        }

        self.order_lbl.setText(str(self.order_index))
        self.type_lbl.setText(self.experiment_type_name)
        self.name_lbl.setText(self.experiment_name)
        self.dirty_mark.setVisible(self.is_dirty)
        self.status_dot.setStyleSheet(
            f"color: {status_colors.get(status, PALETTE['text_muted'])}; background: transparent; font-size: 8px;"
        )

    def _emit_delete_requested(self) -> None:
        if self.experiment_id:
            self.delete_requested.emit(self.experiment_id)
