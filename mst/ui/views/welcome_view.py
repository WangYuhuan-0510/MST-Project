"""
welcome_view.py
───────────────
软件启动首界面。
"""
from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import Qt, Signal, QSettings
from PySide6.QtGui import QPainter, QColor, QPen
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QFrame, QFileDialog, QSizePolicy,
)

from .ui_style import PALETTE

_ORG = "SUAN-Lab"
_APP = "PW-MST"
_KEY = "recent_files"
_MAX = 10


def _load_recent() -> list[str]:
    s = QSettings(_ORG, _APP)
    raw = s.value(_KEY, [])
    return [p for p in (raw if isinstance(raw, list) else [raw]) if Path(p).exists()]


def _save_recent(path: str) -> None:
    s = QSettings(_ORG, _APP)
    lst = _load_recent()
    if path in lst:
        lst.remove(path)
    lst.insert(0, path)
    s.setValue(_KEY, lst[:_MAX])


class _BgDecor(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WA_TransparentForMouseEvents)

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()
        pen = QPen(QColor(PALETTE["border"]))
        pen.setWidth(2)
        p.setPen(pen)
        p.setBrush(Qt.NoBrush)
        for r in range(120, 420, 60):
            p.drawArc(w - r, h - r, r * 2, r * 2, 90 * 16, 90 * 16)


class _SessionBtn(QPushButton):
    def __init__(self, icon_char: str, text: str, primary: bool = False, parent=None):
        super().__init__(parent)
        self.setFixedHeight(74)
        self.setMinimumWidth(340)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.setCursor(Qt.PointingHandCursor)

        lo = QHBoxLayout(self)
        lo.setContentsMargins(20, 0, 20, 0)
        lo.setSpacing(18)

        icon = QLabel(icon_char)
        icon.setFixedWidth(36)
        icon.setAlignment(Qt.AlignCenter)
        icon.setStyleSheet(
            f"color: {PALETTE['text_secondary']}; font-size: 28px;"
            " background: transparent; border: none;"
        )
        icon.setAttribute(Qt.WA_TransparentForMouseEvents)

        lbl = QLabel(text)
        lbl.setStyleSheet(
            f"color: {PALETTE['text_primary']}; font-size: 17px; font-weight: 600;"
            " background: transparent; border: none;"
        )
        lbl.setAttribute(Qt.WA_TransparentForMouseEvents)

        lo.addWidget(icon)
        lo.addWidget(lbl)
        lo.addStretch()

        border = f"2px solid {PALETTE['accent']}" if primary else "none"
        self.setStyleSheet(f"""
            QPushButton {{
                background: {PALETTE['bg_card']};
                border: {border};
                border-radius: 8px;
            }}
            QPushButton:hover {{
                background: {PALETTE['bg_hover']};
                border: 2px solid {PALETTE['accent']};
            }}
            QPushButton:pressed {{
                background: {PALETTE['bg_active']};
            }}
        """)


class _RecentRow(QPushButton):
    def __init__(self, path: str, parent=None):
        super().__init__(parent)
        self.path = path
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.setFixedHeight(44)
        self.setCursor(Qt.PointingHandCursor)
        self.setStyleSheet(f"""
            QPushButton {{
                background: transparent; border: none;
                border-radius: 6px; text-align: left;
            }}
            QPushButton:hover {{ background: {PALETTE['bg_hover']}; }}
            QPushButton:pressed {{ background: {PALETTE['bg_active']}; }}
        """)

        lo = QHBoxLayout(self)
        lo.setContentsMargins(8, 0, 12, 0)
        lo.setSpacing(12)

        p = Path(path)
        mtime = ""
        try:
            ts = os.path.getmtime(path)
            mtime = datetime.fromtimestamp(ts).strftime("%Y/%m/%d  %H:%M:%S")
        except OSError:
            pass

        name_lbl = QLabel(f"<b>{p.stem}</b>")
        name_lbl.setStyleSheet(
            f"color: {PALETTE['text_primary']}; font-size: 13px; background: transparent;"
        )
        name_lbl.setAttribute(Qt.WA_TransparentForMouseEvents)

        path_lbl = QLabel(str(p.parent))
        path_lbl.setStyleSheet(
            f"color: {PALETTE['text_muted']}; font-size: 11px; background: transparent;"
        )
        path_lbl.setAttribute(Qt.WA_TransparentForMouseEvents)

        text_col = QVBoxLayout()
        text_col.setSpacing(2)
        text_col.addWidget(name_lbl)
        text_col.addWidget(path_lbl)

        date_lbl = QLabel(f"— {mtime}")
        date_lbl.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        date_lbl.setStyleSheet(
            f"color: {PALETTE['text_muted']}; font-size: 11px; background: transparent;"
        )
        date_lbl.setAttribute(Qt.WA_TransparentForMouseEvents)

        lo.addLayout(text_col, 1)
        lo.addWidget(date_lbl)


class WelcomeView(QWidget):
    session_opened = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet(f"background: {PALETTE['bg_main']};")

        self._decor = _BgDecor(self)
        self._decor.setAttribute(Qt.WA_TransparentForMouseEvents)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addStretch(2)

        center = QWidget()
        center.setStyleSheet("background: transparent;")
        center.setFixedWidth(540)
        center_lo = QVBoxLayout(center)
        center_lo.setContentsMargins(0, 0, 0, 0)
        center_lo.setSpacing(0)

        self.btn_new  = _SessionBtn("📄", "新建实验",   primary=True)
        self.btn_open = _SessionBtn("📂", "打开已有实验", primary=False)
        self.btn_new.clicked.connect(self._on_new)
        self.btn_open.clicked.connect(self._on_open)

        center_lo.addWidget(self.btn_new)
        center_lo.addSpacing(10)
        center_lo.addWidget(self.btn_open)
        center_lo.addSpacing(28)

        self._recent_header = QLabel("最近打开：")
        self._recent_header.setStyleSheet(
            f"color: {PALETTE['text_muted']}; font-size: 12px; font-weight: 600;"
            " letter-spacing: 0.5px;"
        )

        self._recent_area = QWidget()
        self._recent_area.setStyleSheet("background: transparent;")
        self._recent_lo = QVBoxLayout(self._recent_area)
        self._recent_lo.setContentsMargins(0, 0, 0, 0)
        self._recent_lo.setSpacing(2)

        center_lo.addWidget(self._recent_header)
        center_lo.addSpacing(8)
        center_lo.addWidget(self._recent_area)

        h_wrap = QHBoxLayout()
        h_wrap.addStretch()
        h_wrap.addWidget(center)
        h_wrap.addStretch()

        outer.addLayout(h_wrap)
        outer.addStretch(3)

        self._populate_recent()

    def resizeEvent(self, e):
        super().resizeEvent(e)
        self._decor.setGeometry(0, 0, self.width(), self.height())

    def _populate_recent(self):
        while self._recent_lo.count():
            item = self._recent_lo.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        recent = _load_recent()
        if not recent:
            no_lbl = QLabel("暂无最近文件")
            no_lbl.setStyleSheet(f"color: {PALETTE['text_muted']}; font-size: 12px;")
            self._recent_lo.addWidget(no_lbl)
            self._recent_header.hide()
            return

        self._recent_header.show()
        for path in recent:
            row = _RecentRow(path)
            row.clicked.connect(lambda _, p=path: self._navigate(p))
            self._recent_lo.addWidget(row)

    def _on_new(self):
        self.setEnabled(False)

        # 关键：DontUseNativeDialog 强制使用 Qt 自实现的对话框，
        # 完全绕开 Windows 原生窗口消息（WM_ACTIVATE / WM_SETFOCUS），
        # 对话框关闭后不会向主窗口注入额外系统事件，setCurrentIndex 立即生效。
        dlg = QFileDialog(self, "新建实验文件",
                          str(Path.home() / "新建实验.moc"),
                          "MST 实验文件 (*.moc);;所有文件 (*)")
        dlg.setAcceptMode(QFileDialog.AcceptSave)
        dlg.setOption(QFileDialog.DontUseNativeDialog, True)
        dlg.setDefaultSuffix("moc")

        if dlg.exec() != QFileDialog.Accepted:
            self.setEnabled(True)
            return

        files = dlg.selectedFiles()
        if not files:
            self.setEnabled(True)
            return

        path = files[0]
        self.setEnabled(True)

        moc_path = Path(path)
        if moc_path.suffix.lower() != ".moc":
            moc_path = moc_path.with_suffix(".moc")

        moc_path.write_text(
            json.dumps({
                "version": "1.0",
                "created": datetime.now().isoformat(),
                "name": moc_path.stem,
            }, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        _save_recent(str(moc_path))
        self._populate_recent()
        # Qt 非原生对话框关闭后无残留系统消息，直接 emit 即可
        self.session_opened.emit(str(moc_path))

    def _on_open(self):
        self.setEnabled(False)

        dlg = QFileDialog(self, "打开实验文件",
                          str(Path.home()),
                          "MST 实验文件 (*.moc);;所有文件 (*)")
        dlg.setAcceptMode(QFileDialog.AcceptOpen)
        dlg.setOption(QFileDialog.DontUseNativeDialog, True)

        if dlg.exec() != QFileDialog.Accepted:
            self.setEnabled(True)
            return

        files = dlg.selectedFiles()
        self.setEnabled(True)
        if files:
            path = files[0]
            _save_recent(path)
            self._populate_recent()
            self.session_opened.emit(path)

    def _navigate(self, path: str):
        """点击最近文件直接跳转（无对话框，不需要延迟）。"""
        _save_recent(path)
        self._populate_recent()
        self.session_opened.emit(path)