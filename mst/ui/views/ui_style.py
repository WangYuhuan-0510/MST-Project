"""
ui_style.py
───────────
共享调色盘 + 样式辅助函数，供所有 View 文件引用。
"""

from __future__ import annotations
from PySide6.QtWidgets import QLabel, QFrame, QVBoxLayout, QPushButton

# ─────────────────────────────────────────────
#  Color palette  （浅灰 × 清华紫）
# ─────────────────────────────────────────────
PALETTE: dict[str, str] = {
    "bg_sidebar":     "#F0EDF4",   # 浅紫灰，侧边栏底色
    "bg_main":        "#F7F5FA",   # 极浅灰紫，主区域底色
    "bg_card":        "#FFFFFF",   # 纯白卡片
    "bg_hover":       "#EAE4F0",   # 悬停浅紫
    "bg_active":      "#DDD4EA",   # 激活态淡紫
    "accent":         "#82318E",   # 清华紫（主色）
    "accent_dim":     "#5E2068",   # 深清华紫（按钮底色）
    "text_primary":   "#1A0D22",   # 深紫黑，主文字
    "text_secondary": "#5A4668",   # 中紫灰，副文字
    "text_muted":     "#9D89AA",   # 浅紫灰，弱提示
    "border":         "#DDD4EA",   # 边框浅紫
    "border_active":  "#82318E",   # 激活边框紫
    "danger":         "#C0394B",   # 危险红
    "success":        "#2E7D5E",   # 成功绿
    "warning":        "#B06A00",   # 警告橙
}

SIDEBAR_W = 220

# ─────────────────────────────────────────────
#  Reusable stylesheet fragments
# ─────────────────────────────────────────────

def page_base_style() -> str:
    """顶层页面 widget 背景色。"""
    return f"background: {PALETTE['bg_main']};"


def card_style(radius: int = 10) -> str:
    return (
        f"background: {PALETTE['bg_card']};"
        f"border: 1px solid {PALETTE['border']};"
        f"border-radius: {radius}px;"
    )


def primary_btn_style() -> str:
    return f"""
        QPushButton {{
            background: {PALETTE['accent_dim']};
            border: none;
            border-radius: 7px;
            color: #FFFFFF;
            font-size: 13px;
            font-weight: 600;
            padding: 0 18px;
            height: 34px;
        }}
        QPushButton:hover  {{ background: {PALETTE['accent']}; }}
        QPushButton:pressed {{ background: {PALETTE['accent_dim']}; }}
        QPushButton:disabled {{
            background: {PALETTE['bg_active']};
            color: {PALETTE['text_muted']};
        }}
    """


def secondary_btn_style() -> str:
    return f"""
        QPushButton {{
            background: {PALETTE['bg_card']};
            border: 1px solid {PALETTE['border']};
            border-radius: 7px;
            color: {PALETTE['text_secondary']};
            font-size: 13px;
            font-weight: 500;
            padding: 0 18px;
            height: 34px;
        }}
        QPushButton:hover {{
            background: {PALETTE['bg_hover']};
            color: {PALETTE['text_primary']};
            border-color: {PALETTE['accent']};
        }}
        QPushButton:pressed {{ background: {PALETTE['bg_active']}; }}
        QPushButton:disabled {{
            background: {PALETTE['bg_hover']};
            color: {PALETTE['text_muted']};
        }}
    """


def danger_btn_style() -> str:
    return f"""
        QPushButton {{
            background: {PALETTE['bg_card']};
            border: 1px solid {PALETTE['border']};
            border-radius: 7px;
            color: {PALETTE['danger']};
            font-size: 13px;
            font-weight: 600;
            padding: 0 18px;
            height: 34px;
        }}
        QPushButton:hover {{
            background: #FFF0F1;
            border-color: {PALETTE['danger']};
        }}
        QPushButton:pressed {{ background: #FFE0E3; }}
        QPushButton:disabled {{
            background: {PALETTE['bg_hover']};
            color: {PALETTE['text_muted']};
        }}
    """


def spinbox_style() -> str:
    return f"""
        QDoubleSpinBox, QSpinBox {{
            background: {PALETTE['bg_card']};
            border: 1px solid {PALETTE['border']};
            border-radius: 6px;
            color: {PALETTE['text_primary']};
            font-size: 13px;
            padding: 4px 8px;
            min-height: 28px;
        }}
        QDoubleSpinBox:focus, QSpinBox:focus {{
            border: 1px solid {PALETTE['border_active']};
        }}
        QDoubleSpinBox::up-button, QSpinBox::up-button,
        QDoubleSpinBox::down-button, QSpinBox::down-button {{
            width: 18px;
            border: none;
            background: transparent;
        }}
    """


def groupbox_style() -> str:
    return f"""
        QGroupBox {{
            background: {PALETTE['bg_card']};
            border: 1px solid {PALETTE['border']};
            border-radius: 10px;
            margin-top: 14px;
            font-size: 12px;
            font-weight: 600;
            color: {PALETTE['text_secondary']};
        }}
        QGroupBox::title {{
            subcontrol-origin: margin;
            subcontrol-position: top left;
            left: 12px;
            padding: 0 4px;
            color: {PALETTE['text_secondary']};
            letter-spacing: 0.3px;
        }}
    """


def checkbox_style() -> str:
    return f"""
        QCheckBox {{
            color: {PALETTE['text_secondary']};
            font-size: 13px;
            spacing: 6px;
        }}
        QCheckBox::indicator {{
            width: 16px; height: 16px;
            border: 1px solid {PALETTE['border']};
            border-radius: 4px;
            background: {PALETTE['bg_card']};
        }}
        QCheckBox::indicator:checked {{
            background: {PALETTE['accent']};
            border-color: {PALETTE['accent']};
        }}
        QCheckBox::indicator:hover {{
            border-color: {PALETTE['accent']};
        }}
    """


def label_style(size: int = 13, weight: int = 400, color_key: str = "text_secondary") -> str:
    return (
        f"color: {PALETTE[color_key]};"
        f"font-size: {size}px;"
        f"font-weight: {weight};"
    )


def section_label(text: str) -> QLabel:
    lbl = QLabel(text)
    lbl.setStyleSheet(
        f"color: {PALETTE['text_muted']};"
        "font-size: 10px;"
        "font-weight: 700;"
        "letter-spacing: 1.2px;"
    )
    return lbl


def divider() -> QFrame:
    line = QFrame()
    line.setFrameShape(QFrame.HLine)
    line.setFixedHeight(1)
    line.setStyleSheet(
        f"background: {PALETTE['border']}; border: none;"
    )
    return line