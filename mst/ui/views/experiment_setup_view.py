"""
experiment_setup_view.py  （Plan 页面）
────────────────────────────────────────
实验计划页面 — 参照 MO.Control 风格，分五个区块：
  分析物 / 配体 / 缓冲液 / 毛细管 / 系统设置
"""
from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QSpinBox, QPushButton, QLabel,
    QFrame, QScrollArea, QLineEdit, QComboBox, QCheckBox,
)
from PySide6.QtCore import Qt

from .ui_style import (
    PALETTE,
    primary_btn_style,
    secondary_btn_style,
    label_style,
    divider,
)


ICON_DIR = Path(__file__).resolve().parent / "icons"
COMBO_ARROW_ICON = str((ICON_DIR / "combo_down_black.svg").resolve()).replace("\\", "/")
SPIN_UP_ARROW_ICON = str((ICON_DIR / "combo_up_black.svg").resolve()).replace("\\", "/")


# ─────────────────────────────────────────────────────────────────────────────
#  Local style helpers
# ─────────────────────────────────────────────────────────────────────────────

def _input_style() -> str:
    return f"""
        QLineEdit {{
            background: {PALETTE['bg_card']};
            border: 1px solid {PALETTE['border']};
            border-radius: 6px;
            color: {PALETTE['text_primary']};
            font-size: 13px;
            padding: 4px 10px;
            min-height: 28px;
        }}
        QLineEdit:focus {{
            border: 1px solid {PALETTE['border_active']};
        }}
    """


def _input_readonly_style() -> str:
    return f"""
        QLineEdit {{
            background: {PALETTE['bg_hover']};
            border: 1px solid {PALETTE['border']};
            border-radius: 6px;
            color: {PALETTE['text_secondary']};
            font-size: 13px;
            padding: 4px 10px;
            min-height: 28px;
        }}
    """


def _combo_style() -> str:
    return f"""
        QComboBox {{
            background: {PALETTE['bg_card']};
            border: 1px solid {PALETTE['border']};
            border-radius: 6px;
            color: {PALETTE['text_primary']};
            font-size: 13px;
            padding: 4px 30px 4px 10px;
            min-height: 28px;
        }}
        QComboBox:focus {{
            border: 1px solid {PALETTE['border_active']};
        }}
        QComboBox::drop-down {{
            subcontrol-origin: padding;
            subcontrol-position: top right;
            width: 24px;
            border: none;
            background: transparent;
        }}
        QComboBox::down-arrow {{
            image: url({COMBO_ARROW_ICON});
            width: 12px;
            height: 12px;
            margin-right: 8px;
        }}
        QComboBox QAbstractItemView {{
            background: {PALETTE['bg_card']};
            border: 1px solid {PALETTE['border']};
            color: {PALETTE['text_primary']};
            selection-background-color: {PALETTE['bg_active']};
        }}
    """


def _spinbox_style() -> str:
    return f"""
        QSpinBox {{
            background: {PALETTE['bg_card']};
            border: 1px solid {PALETTE['border']};
            border-radius: 6px;
            color: {PALETTE['text_primary']};
            font-size: 13px;
            padding: 4px 30px 4px 8px;
            min-height: 28px;
        }}
        QSpinBox:focus {{
            border: 1px solid {PALETTE['border_active']};
        }}
        QSpinBox::up-button, QSpinBox::down-button {{
            subcontrol-origin: border;
            width: 18px;
            border: none;
            background: transparent;
        }}
        QSpinBox::up-button {{
            subcontrol-position: top right;
            height: 14px;
        }}
        QSpinBox::down-button {{
            subcontrol-position: bottom right;
            height: 14px;
        }}
        QSpinBox::up-arrow {{
            image: url({SPIN_UP_ARROW_ICON});
            width: 10px;
            height: 10px;
            margin-top: 2px;
            margin-right: 6px;
        }}
        QSpinBox::down-arrow {{
            image: url({COMBO_ARROW_ICON});
            width: 10px;
            height: 10px;
            margin-bottom: 2px;
            margin-right: 6px;
        }}
    """


def _check_style() -> str:
    return f"""
        QCheckBox {{
            color: {PALETTE['text_secondary']};
            font-size: 13px;
            spacing: 8px;
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


def _help_btn() -> QPushButton:
    btn = QPushButton("?")
    btn.setFixedSize(24, 24)
    btn.setCursor(Qt.PointingHandCursor)
    btn.setStyleSheet(f"""
        QPushButton {{
            background: {PALETTE['bg_hover']};
            border: 1px solid {PALETTE['border']};
            border-radius: 5px;
            color: {PALETTE['text_muted']};
            font-size: 11px;
            font-weight: 700;
        }}
        QPushButton:hover {{
            background: {PALETTE['bg_active']};
            color: {PALETTE['accent']};
            border-color: {PALETTE['accent']};
        }}
    """)
    return btn


def _edit_btn() -> QPushButton:
    btn = QPushButton("✎")
    btn.setFixedSize(30, 28)
    btn.setCursor(Qt.PointingHandCursor)
    btn.setStyleSheet(secondary_btn_style())
    return btn


def _section_card() -> QFrame:
    f = QFrame()
    f.setStyleSheet("background: transparent; border: none;")
    return f


def _section_header(icon: str, text: str) -> QHBoxLayout:
    row = QHBoxLayout()
    row.setSpacing(8)
    icon_lbl = QLabel(icon)
    icon_lbl.setStyleSheet(f"color: {PALETTE['accent']}; font-size: 18px;")
    icon_lbl.setFixedWidth(26)
    title_lbl = QLabel(text)
    title_lbl.setStyleSheet(
        f"color: {PALETTE['text_primary']}; font-size: 15px; font-weight: 700;"
    )
    row.addWidget(icon_lbl)
    row.addWidget(title_lbl)
    row.addStretch()
    return row


def _field_lbl(text: str, min_w: int = 0) -> QLabel:
    lbl = QLabel(text)
    lbl.setStyleSheet(
        f"color: {PALETTE['text_secondary']}; font-size: 13px;"
    )
    lbl.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
    if min_w:
        lbl.setMinimumWidth(min_w)
    return lbl


def _value_lbl(text: str) -> QLabel:
    lbl = QLabel(text)
    lbl.setStyleSheet(
        f"color: {PALETTE['text_primary']}; font-size: 13px; font-weight: 600;"
    )
    return lbl


def _unit_combo(items: list[str]) -> QComboBox:
    c = QComboBox()
    c.addItems(items)
    c.setFixedWidth(72)
    c.setStyleSheet(_combo_style())
    return c


LABEL_W = 260   # 左侧字段标签固定宽度，用于两栏对齐


# ─────────────────────────────────────────────────────────────────────────────
#  Main view
# ─────────────────────────────────────────────────────────────────────────────

class ExperimentSetupView(QScrollArea):
    """
    实验计划页面（Plan）。
    五区块：分析物 / 配体 / 缓冲液 / 毛细管 / 系统设置。
    """

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setFrameShape(QFrame.NoFrame)
        self.setWidgetResizable(True)
        self.setStyleSheet(f"background: {PALETTE['bg_main']};")

        inner = QWidget()
        inner.setStyleSheet(f"background: {PALETTE['bg_main']};")
        self.setWidget(inner)

        root = QVBoxLayout(inner)
        root.setContentsMargins(28, 24, 28, 28)
        root.setSpacing(16)

        # ── 顶部标题栏 ───────────────────────────────────────────────────────
        title_row = QHBoxLayout()
        page_title = QLabel("实验设置")
        page_title.setStyleSheet(
            f"color: {PALETTE['text_primary']}; font-size: 22px; font-weight: 700;"
            " letter-spacing: -0.3px;"
        )
        alter_btn = QPushButton("修改数据")
        alter_btn.setFixedHeight(32)
        alter_btn.setStyleSheet(secondary_btn_style())
        title_row.addWidget(page_title)
        title_row.addStretch()
        title_row.addWidget(alter_btn)
        title_row.addSpacing(6)
        title_row.addWidget(_help_btn())
        root.addLayout(title_row)
        root.addWidget(divider())
        root.addSpacing(2)

        # ── 两栏布局 ─────────────────────────────────────────────────────────
        two_col = QHBoxLayout()
        two_col.setSpacing(20)
        two_col.setAlignment(Qt.AlignTop)

        # ════════════ 左栏 ════════════
        left_col = QVBoxLayout()
        left_col.setSpacing(14)
        left_col.setAlignment(Qt.AlignTop)

        # ── 分析物 ────────────────────────────────────────────────────────
        target_card = _section_card()
        tc = QVBoxLayout(target_card)
        tc.setContentsMargins(20, 16, 20, 18)
        tc.setSpacing(11)
        tc.addLayout(_section_header("◕", "分析物"))
        tc.addWidget(divider())

        r0 = QHBoxLayout(); r0.setSpacing(6)
        self.cmb_target = QComboBox()
        self.cmb_target.addItems(["NTA", "His-Tag", "Biotin", "Amine", "Thiol"])
        self.cmb_target.setStyleSheet(_combo_style())
        r0.addWidget(self.cmb_target, 1)
        r0.addWidget(_help_btn())
        tc.addLayout(r0)

        r1 = QHBoxLayout(); r1.setSpacing(6)
        self.chk_histag = QCheckBox("使用 His-Tag 标签")
        self.chk_histag.setStyleSheet(_check_style())
        r1.addWidget(self.chk_histag)
        r1.addStretch()
        r1.addWidget(_help_btn())
        tc.addLayout(r1)

        r2 = QHBoxLayout(); r2.setSpacing(6)
        r2.addWidget(_field_lbl("母液浓度", LABEL_W))
        self.edit_target_stock = QLineEdit("5")
        self.edit_target_stock.setFixedWidth(80)
        self.edit_target_stock.setStyleSheet(_input_style())
        self.cmb_target_unit = _unit_combo(["µM", "nM", "mM"])
        r2.addWidget(self.edit_target_stock)
        r2.addWidget(self.cmb_target_unit)
        r2.addWidget(_help_btn())
        r2.addStretch()
        tc.addLayout(r2)

        r3 = QHBoxLayout(); r3.setSpacing(6)
        r3.addWidget(_field_lbl("此次实验浓度", LABEL_W))
        self.edit_target_assay = QLineEdit("25nM")
        self.edit_target_assay.setFixedWidth(80)
        self.edit_target_assay.setStyleSheet(_input_style())
        r3.addWidget(self.edit_target_assay)
        r3.addWidget(_help_btn())
        r3.addStretch()
        tc.addLayout(r3)

        left_col.addWidget(target_card)

        # ── 缓冲液 ────────────────────────────────────────────────────────
        buf_card = _section_card()
        bc = QVBoxLayout(buf_card)
        bc.setContentsMargins(20, 16, 20, 18)
        bc.setSpacing(11)
        bc.addLayout(_section_header("⬛", "缓冲液"))
        bc.addWidget(divider())

        rb = QHBoxLayout(); rb.setSpacing(6)
        self.edit_buffer = QLineEdit("PBS including 0.05% Tween")
        self.edit_buffer.setStyleSheet(_input_style())
        rb.addWidget(self.edit_buffer, 1)
        rb.addWidget(_edit_btn())
        rb.addWidget(_help_btn())
        bc.addLayout(rb)

        left_col.addWidget(buf_card)

        # ── 毛细管 ────────────────────────────────────────────────────────
        cap_card = _section_card()
        cc = QVBoxLayout(cap_card)
        cc.setContentsMargins(20, 16, 20, 18)
        cc.setSpacing(11)
        cc.addLayout(_section_header("▮", "毛细管"))
        cc.addWidget(divider())

        rc = QHBoxLayout(); rc.setSpacing(6)
        self.cmb_capillary = QComboBox()
        self.cmb_capillary.addItems([
            "Monolith NT.115 毛细管",
            "Monolith NT.115 Premium 毛细管",
            "Monolith NT.自动化毛细管芯片",
        ])
        self.cmb_capillary.setStyleSheet(_combo_style())
        rc.addWidget(self.cmb_capillary, 1)
        rc.addWidget(_help_btn())
        cc.addLayout(rc)

        left_col.addWidget(cap_card)
        left_col.addStretch()

        # ════════════ 右栏 ════════════
        right_col = QVBoxLayout()
        right_col.setSpacing(14)
        right_col.setAlignment(Qt.AlignTop)

        # ── 配体 ──────────────────────────────────────────────────────────
        lig_card = _section_card()
        lc = QVBoxLayout(lig_card)
        lc.setContentsMargins(20, 16, 20, 18)
        lc.setSpacing(11)
        lc.addLayout(_section_header("◆", "配体"))
        lc.addWidget(divider())

        rl0 = QHBoxLayout(); rl0.setSpacing(6)
        self.cmb_ligand = QComboBox()
        self.cmb_ligand.addItems(["mCNGC30", "EGFR", "HER2", "自定义"])
        self.cmb_ligand.setStyleSheet(_combo_style())
        rl0.addWidget(self.cmb_ligand, 1)
        rl0.addWidget(_help_btn())
        lc.addLayout(rl0)

        rl1 = QHBoxLayout(); rl1.setSpacing(6)
        rl1.addWidget(_field_lbl("预估 Kd", LABEL_W))
        self.edit_kd = QLineEdit()
        self.edit_kd.setPlaceholderText("可选")
        self.edit_kd.setFixedWidth(80)
        self.edit_kd.setStyleSheet(_input_style())
        self.cmb_kd_unit = _unit_combo(["µM", "nM", "mM"])
        rl1.addWidget(self.edit_kd)
        rl1.addWidget(self.cmb_kd_unit)
        rl1.addWidget(_help_btn())
        rl1.addStretch()
        lc.addLayout(rl1)

        rl2 = QHBoxLayout(); rl2.setSpacing(6)
        rl2.addWidget(_field_lbl("母液浓度", LABEL_W))
        self.edit_lig_stock = QLineEdit("16")
        self.edit_lig_stock.setFixedWidth(80)
        self.edit_lig_stock.setStyleSheet(_input_style())
        self.cmb_lig_unit = _unit_combo(["µM", "nM", "mM"])
        rl2.addWidget(self.edit_lig_stock)
        rl2.addWidget(self.cmb_lig_unit)
        rl2.addWidget(_help_btn())
        rl2.addStretch()
        lc.addLayout(rl2)

        rl3 = QHBoxLayout(); rl3.setSpacing(6)
        self.chk_dmso = QCheckBox("配体溶于有机溶剂（如 DMSO）")
        self.chk_dmso.setStyleSheet(_check_style())
        rl3.addWidget(self.chk_dmso)
        rl3.addStretch()
        rl3.addWidget(_help_btn())
        lc.addLayout(rl3)

        rl4 = QHBoxLayout(); rl4.setSpacing(6)
        rl4.addWidget(_field_lbl("配体缓冲液比例", LABEL_W))
        self.lbl_lig_buf = _value_lbl("12.5%")
        rl4.addWidget(self.lbl_lig_buf)
        rl4.addStretch()
        rl4.addWidget(_help_btn())
        lc.addLayout(rl4)

        rl5 = QHBoxLayout(); rl5.setSpacing(6)
        rl5.addWidget(_field_lbl("此次实验最高浓度", LABEL_W))
        self.edit_hi_conc = QLineEdit("2")
        self.edit_hi_conc.setFixedWidth(80)
        self.edit_hi_conc.setStyleSheet(_input_style())
        hi_unit = QLabel("µM")
        hi_unit.setStyleSheet(f"color: {PALETTE['text_muted']}; font-size: 12px;")
        rl5.addWidget(self.edit_hi_conc)
        rl5.addWidget(hi_unit)
        rl5.addWidget(_edit_btn())
        rl5.addWidget(_help_btn())
        rl5.addStretch()
        lc.addLayout(rl5)

        right_col.addWidget(lig_card)

        # ── 系统设置（右栏，配体下方）─────────────────────────────────────
        sys_card = _section_card()
        sc = QVBoxLayout(sys_card)
        sc.setContentsMargins(20, 16, 20, 18)
        sc.setSpacing(12)
        sc.addLayout(_section_header("✦", "系统设置"))
        sc.addWidget(divider())

        sys_row = QHBoxLayout()
        sys_row.setSpacing(40)
        sys_row.setAlignment(Qt.AlignLeft)

        # 激发光功率
        ex_blk = QVBoxLayout(); ex_blk.setSpacing(6)
        ex_hdr = QHBoxLayout(); ex_hdr.setSpacing(6)
        ex_icon = QLabel("☀")
        ex_icon.setStyleSheet(f"color: {PALETTE['accent']}; font-size: 16px;")
        ex_title = QLabel("激发光功率")
        ex_title.setStyleSheet(label_style(13, 600, "text_secondary"))
        ex_hdr.addWidget(ex_icon)
        ex_hdr.addWidget(ex_title)
        ex_hdr.addStretch()
        ex_blk.addLayout(ex_hdr)

        ex_ctrl = QHBoxLayout(); ex_ctrl.setSpacing(6)
        self.chk_auto = QCheckBox("自动检测")
        self.chk_auto.setStyleSheet(_check_style())
        self.chk_auto.setChecked(True)
        self.spin_excitation = QSpinBox()
        self.spin_excitation.setRange(10, 100)
        self.spin_excitation.setSingleStep(5)
        self.spin_excitation.setValue(20)
        self.spin_excitation.setSuffix(" %")
        self.spin_excitation.setFixedWidth(84)
        self.spin_excitation.setStyleSheet(_spinbox_style())
        self.spin_excitation.setEnabled(True)
        ex_ctrl.addWidget(self.chk_auto)
        ex_ctrl.addWidget(self.spin_excitation)
        ex_ctrl.addWidget(_help_btn())
        ex_ctrl.addStretch()
        ex_blk.addLayout(ex_ctrl)

        # MST 功率
        mst_blk = QVBoxLayout(); mst_blk.setSpacing(6)
        mst_hdr = QHBoxLayout(); mst_hdr.setSpacing(6)
        mst_icon = QLabel("✳")
        mst_icon.setStyleSheet(f"color: {PALETTE['accent']}; font-size: 16px;")
        mst_title = QLabel("MST 功率")
        mst_title.setStyleSheet(label_style(13, 600, "text_secondary"))
        mst_hdr.addWidget(mst_icon)
        mst_hdr.addWidget(mst_title)
        mst_hdr.addStretch()
        mst_blk.addLayout(mst_hdr)

        mst_ctrl = QHBoxLayout(); mst_ctrl.setSpacing(6)
        self.cmb_mst = QComboBox()
        self.cmb_mst.addItems(["低", "中", "高"])
        self.cmb_mst.setCurrentIndex(1)
        self.cmb_mst.setFixedWidth(100)
        self.cmb_mst.setStyleSheet(_combo_style())
        mst_ctrl.addWidget(self.cmb_mst)
        mst_ctrl.addWidget(_edit_btn())
        mst_ctrl.addWidget(_help_btn())
        mst_ctrl.addStretch()
        mst_blk.addLayout(mst_ctrl)

        sys_row.addLayout(ex_blk)
        sys_row.addLayout(mst_blk)
        sc.addLayout(sys_row)

        right_col.addWidget(sys_card)

        # ── 应用按钮（右栏，系统设置下方）───────────────────────────────────
        apply_row = QHBoxLayout()
        self.btn_apply = QPushButton("应用")
        self.btn_apply.setFixedHeight(38)
        self.btn_apply.setStyleSheet(primary_btn_style())
        self.btn_apply.clicked.connect(self.apply_current_experiment_plan)
        self.status_lbl = QLabel("")
        self.status_lbl.setStyleSheet(
            f"color: {PALETTE['success']}; font-size: 12px; font-weight: 500;"
        )
        apply_row.addWidget(self.btn_apply)
        apply_row.addSpacing(12)
        apply_row.addWidget(self.status_lbl)
        apply_row.addStretch()
        right_col.addLayout(apply_row)
        right_col.addStretch()

        two_col.addLayout(left_col, 1)
        two_col.addLayout(right_col, 1)
        root.addLayout(two_col)
        root.addStretch()

        self._load_from_state()

    # ── Private helpers ──────────────────────────────────────────────────────

    def _mw(self):
        return self.window()

    def _set_status(self, text: str, color_key: str = "success") -> None:
        self.status_lbl.setText(text)
        self.status_lbl.setStyleSheet(
            f"color: {PALETTE[color_key]}; font-size: 12px; font-weight: 500;"
        )

    def _load_from_state(self) -> None:
        mw = self._mw()
        if not hasattr(mw, "state"):
            return
        sim = getattr(mw.state, "sim", None)
        if sim is None:
            return
        try:
            self.edit_kd.setText(str(sim.kd_true))
            self.edit_target_stock.setText(str(sim.r_max_true))
        except Exception:
            pass

    # ── Public slots ─────────────────────────────────────────────────────────

    def apply_to_state(self) -> None:
        mw = self._mw()
        if not hasattr(mw, "state"):
            self._set_status("未找到主窗口状态（state）", "danger")
            return
        sim = getattr(mw.state, "sim", None)
        if sim is None:
            self._set_status("state.sim 不存在", "danger")
            return
        try:
            kd_text = self.edit_kd.text().strip()
            if kd_text:
                sim.kd_true = float(kd_text)
            stock_text = self.edit_target_stock.text().strip()
            if stock_text:
                sim.r_max_true = float(stock_text)
        except ValueError as e:
            self._set_status(f"数值格式错误：{e}", "danger")
            return
        self._set_status("✓  已应用：运行页将按此参数生成模拟数据。", "success")

    def get_params(self) -> dict:
        """返回当前界面所有参数的字典快照（供其他模块读取）。"""
        return {
            "target":            self.cmb_target.currentText(),
            "use_histag":        self.chk_histag.isChecked(),
            "target_stock":      self.edit_target_stock.text(),
            "target_stock_unit": self.cmb_target_unit.currentText(),
            "target_assay":      self.edit_target_assay.text(),
            "buffer":            self.edit_buffer.text(),
            "capillary":         self.cmb_capillary.currentText(),
            "ligand":            self.cmb_ligand.currentText(),
            "kd_estimated":      self.edit_kd.text(),
            "kd_unit":           self.cmb_kd_unit.currentText(),
            "lig_stock":         self.edit_lig_stock.text(),
            "lig_stock_unit":    self.cmb_lig_unit.currentText(),
            "lig_in_dmso":       self.chk_dmso.isChecked(),
            "hi_conc":           self.edit_hi_conc.text(),
            "excitation_auto":   self.chk_auto.isChecked(),
            "excitation_pct":    self.spin_excitation.value(),
            "mst_power":         self.cmb_mst.currentText(),   # 低 / 中 / 高
        }

    def set_data(self, data: dict) -> None:
        if not isinstance(data, dict):
            return

        def _set_combo(combo: QComboBox, value: object) -> None:
            text = str(value or "")
            idx = combo.findText(text)
            if idx >= 0:
                combo.setCurrentIndex(idx)

        _set_combo(self.cmb_target, data.get("target"))
        self.chk_histag.setChecked(bool(data.get("use_histag", False)))
        self.edit_target_stock.setText(str(data.get("target_stock", "") or ""))
        _set_combo(self.cmb_target_unit, data.get("target_stock_unit"))
        self.edit_target_assay.setText(str(data.get("target_assay", "") or ""))
        self.edit_buffer.setText(str(data.get("buffer", "") or ""))
        _set_combo(self.cmb_capillary, data.get("capillary"))
        _set_combo(self.cmb_ligand, data.get("ligand"))
        self.edit_kd.setText(str(data.get("kd_estimated", "") or ""))
        _set_combo(self.cmb_kd_unit, data.get("kd_unit"))
        self.edit_lig_stock.setText(str(data.get("lig_stock", "") or ""))
        _set_combo(self.cmb_lig_unit, data.get("lig_stock_unit"))
        self.chk_dmso.setChecked(bool(data.get("lig_in_dmso", False)))
        self.edit_hi_conc.setText(str(data.get("hi_conc", "") or ""))
        self.chk_auto.setChecked(bool(data.get("excitation_auto", True)))
        try:
            self.spin_excitation.setValue(int(data.get("excitation_pct", self.spin_excitation.value()) or self.spin_excitation.value()))
        except Exception:
            pass
        _set_combo(self.cmb_mst, data.get("mst_power"))

    def set_experiment_type(self, experiment_type_id: str) -> None:
        mw = self._mw()
        if hasattr(mw, "current_experiment_type_id"):
            mw.current_experiment_type_id = str(experiment_type_id or "pre_test")

    def apply_current_experiment_plan(self) -> bool:
        mw = self._mw()
        if not hasattr(mw, "save_current_experiment_plan"):
            self._set_status("?????????????", "danger")
            return False
        ok = bool(mw.save_current_experiment_plan())
        if ok:
            self._set_status("?  ???? Plan ?????????????", "success")
        else:
            self._set_status("???? Plan ????", "danger")
        return ok
