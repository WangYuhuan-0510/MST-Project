"""
welcome_view.py
───────────────
软件启动首界面。
  · 新建实验  — 选择文件夹，创建 <name>.moc 文件
  · 打开已有实验  — 选择已有 .moc 文件
  · 最近文件列表  — 点击直接打开
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
    QScrollArea, QSpacerItem,
)

from .ui_style import PALETTE

# ── 最近文件记录存储键 ──────────────────────────────────────────────────────
_ORG  = "SUAN-Lab"
_APP  = "PW-MST"
_KEY  = "recent_files"
_MAX  = 10          # 最多保留条数


# ─────────────────────────────────────────────────────────────────────────────
#  Recent-file helpers
# ─────────────────────────────────────────────────────────────────────────────

def _load_recent() -> list[str]:
    s = QSettings(_ORG, _APP)
    raw = s.value(_KEY, [])
    return [p for p in (raw if isinstance(raw, list) else [raw]) if Path(p).exists()]


def _save_recent(path: str) -> None:
    s   = QSettings(_ORG, _APP)
    lst = _load_recent()
    if path in lst:
        lst.remove(path)
    lst.insert(0, path)
    s.setValue(_KEY, lst[:_MAX])


# ─────────────────────────────────────────────────────────────────────────────
#  Decorative background widget (螺旋线装饰，模仿截图右下角)
# ─────────────────────────────────────────────────────────────────────────────

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

        # 几条大弧线，模仿右下角装饰
        for r in range(120, 420, 60):
            p.drawArc(w - r, h - r, r * 2, r * 2, 90 * 16, 90 * 16)


# ─────────────────────────────────────────────────────────────────────────────
#  Session button  (大型带图标操作按钮)
# ─────────────────────────────────────────────────────────────────────────────

class _SessionBtn(QPushButton):
    """带左侧图标文字的大操作按钮，新建有边框高亮，打开无边框。"""

    def __init__(self, icon_char: str, text: str,
                 primary: bool = False, parent=None):
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


# ─────────────────────────────────────────────────────────────────────────────
#  Recent file row
# ─────────────────────────────────────────────────────────────────────────────

class _RecentRow(QPushButton):
    def __init__(self, path: str, parent=None):
        super().__init__(parent)
        self.path = path
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.setFixedHeight(44)
        self.setCursor(Qt.PointingHandCursor)
        self.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                border: none;
                border-radius: 6px;
                text-align: left;
            }}
            QPushButton:hover {{
                background: {PALETTE['bg_hover']};
            }}
            QPushButton:pressed {{
                background: {PALETTE['bg_active']};
            }}
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
            f"color: {PALETTE['text_primary']}; font-size: 13px;"
            " background: transparent;"
        )
        name_lbl.setAttribute(Qt.WA_TransparentForMouseEvents)

        path_lbl = QLabel(str(p.parent))
        path_lbl.setStyleSheet(
            f"color: {PALETTE['text_muted']}; font-size: 11px;"
            " background: transparent;"
        )
        path_lbl.setAttribute(Qt.WA_TransparentForMouseEvents)

        text_col = QVBoxLayout()
        text_col.setSpacing(2)
        text_col.addWidget(name_lbl)
        text_col.addWidget(path_lbl)

        date_lbl = QLabel(f"— {mtime}")
        date_lbl.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        date_lbl.setStyleSheet(
            f"color: {PALETTE['text_muted']}; font-size: 11px;"
            " background: transparent;"
        )
        date_lbl.setAttribute(Qt.WA_TransparentForMouseEvents)

        lo.addLayout(text_col, 1)
        lo.addWidget(date_lbl)


# ─────────────────────────────────────────────────────────────────────────────
#  WelcomeView
# ─────────────────────────────────────────────────────────────────────────────

class WelcomeView(QWidget):
    """
    启动首界面。
    发出 session_opened(path: str) 信号，由 MainWindow 接收并切换到 ProjectView。
    """
    session_opened = Signal(str)   # 携带 .moc 文件路径

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet(f"background: {PALETTE['bg_main']};")

        # 装饰背景（右下角弧线）
        self._decor = _BgDecor(self)
        self._decor.setAttribute(Qt.WA_TransparentForMouseEvents)

        # ── 主布局：垂直居中 ────────────────────────────────────────────────
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addStretch(2)

        center = QWidget()
        center.setStyleSheet("background: transparent;")
        center.setFixedWidth(540)
        center_lo = QVBoxLayout(center)
        center_lo.setContentsMargins(0, 0, 0, 0)
        center_lo.setSpacing(0)

        # ── 按钮区 ──────────────────────────────────────────────────────────
        self.btn_new    = _SessionBtn("📄", "Start New Session",   primary=False)
        self.btn_open   = _SessionBtn("📂", "Browse Previous Sessions", primary=False)
        self.btn_new.clicked.connect(self._on_new)
        self.btn_open.clicked.connect(self._on_open)

        center_lo.addWidget(self.btn_new)
        center_lo.addSpacing(10)
        center_lo.addWidget(self.btn_open)
        center_lo.addSpacing(28)

        # ── 最近文件 ────────────────────────────────────────────────────────
        self._recent_header = QLabel("Recently Opened:")
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

        # 水平居中
        h_wrap = QHBoxLayout()
        h_wrap.addStretch()
        h_wrap.addWidget(center)
        h_wrap.addStretch()

        outer.addLayout(h_wrap)
        outer.addStretch(3)

        self._populate_recent()

    # ── 布局重绘时同步装饰层大小 ─────────────────────────────────────────────

    def resizeEvent(self, e):
        super().resizeEvent(e)
        self._decor.setGeometry(0, 0, self.width(), self.height())

    # ── 填充最近文件 ─────────────────────────────────────────────────────────

    def _populate_recent(self):
        # 清空旧条目
        while self._recent_lo.count():
            item = self._recent_lo.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        recent = _load_recent()
        if not recent:
            no_lbl = QLabel("No recent files")
            no_lbl.setStyleSheet(
                f"color: {PALETTE['text_muted']}; font-size: 12px;"
            )
            self._recent_lo.addWidget(no_lbl)
            self._recent_header.hide()
            return

        self._recent_header.show()
        for path in recent:
            row = _RecentRow(path)
            row.clicked.connect(lambda _, p=path: self._open_path(p))
            self._recent_lo.addWidget(row)

    # ── 槽函数 ───────────────────────────────────────────────────────────────

    def _on_new(self):
        """Select a folder, create a <folder name>.moc file in it."""
        folder = QFileDialog.getExistingDirectory(
            self, "Select a folder to store the experiment", str(Path.home())
        )
        if not folder:
            return
        folder_path = Path(folder)
        # 文件名取文件夹名，避免重名则追加序号
        base = folder_path.name or "experiment"
        moc_path = folder_path / f"{base}.moc"
        counter = 1
        while moc_path.exists():
            moc_path = folder_path / f"{base}_{counter}.moc"
            counter += 1
        # 写入初始 JSON 结构
        moc_path.write_text(
            json.dumps({
                "version": "1.0",
                "created": datetime.now().isoformat(),
                "name": base,
            }, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        self._open_path(str(moc_path))

    def _on_open(self):
        """Select an existing .moc file."""
        path, _ = QFileDialog.getOpenFileName(
            self, "Select an experiment file", str(Path.home()),
            "PW-MST experiment files (*.moc);;All files (*)"
        )
        if path:
            self._open_path(path)

    def _open_path(self, path: str):
        _save_recent(path)
        self._populate_recent()
        self.session_opened.emit(path)