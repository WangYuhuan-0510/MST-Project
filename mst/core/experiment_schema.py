from __future__ import annotations

from copy import deepcopy
from typing import Any, Dict, List

FieldConfig = Dict[str, Any]
SectionConfig = Dict[str, Any]
ExperimentTypeConfig = Dict[str, Any]


def _base_sections() -> List[SectionConfig]:
    return [
        {
            "id": "sample",
            "title": "样品设置",
            "fields": [
                {"key": "target", "label": "分析物", "type": "select", "options": ["NTA", "His-Tag", "Biotin", "Amine", "Thiol"], "default": "NTA"},
                {"key": "use_histag", "label": "使用 His-Tag 标签", "type": "bool", "default": False},
                {"key": "target_stock", "label": "母液浓度", "type": "text", "default": "5"},
                {"key": "target_stock_unit", "label": "母液浓度单位", "type": "select", "options": ["M", "mM", "µM", "nM", "pM"], "default": "µM"},
                {"key": "target_assay", "label": "此次实验浓度", "type": "text", "default": "25nM"},
            ],
        },
        {
            "id": "ligand",
            "title": "配体设置",
            "fields": [
                {"key": "ligand", "label": "配体", "type": "select", "options": ["mCNGC30", "EGFR", "HER2"], "default": "mCNGC30"},
                {"key": "kd_estimated", "label": "预估 Kd", "type": "text", "default": ""},
                {"key": "kd_unit", "label": "Kd 单位", "type": "select", "options": ["M", "mM", "µM", "nM", "pM"], "default": "nM"},
                {"key": "lig_stock", "label": "配体母液浓度", "type": "text", "default": "16"},
                {"key": "lig_stock_unit", "label": "配体母液浓度单位", "type": "select", "options": ["M", "mM", "µM", "nM", "pM"], "default": "µM"},
                {"key": "lig_in_dmso", "label": "配体溶于 DMSO", "type": "bool", "default": False},
                {"key": "check_buffer_auto_fluorescence", "label": "Check for buffer auto-fliorescence", "type": "bool", "default": False},
                {"key": "hi_conc", "label": "此次实验最高浓度", "type": "text", "default": "2"},
            ],
        },
        {
            "id": "environment",
            "title": "环境与耗材",
            "fields": [
                {"key": "buffer", "label": "缓冲液", "type": "select", "options": ["MST Buffer including 0.05% Tween", "PBS including 0.05% Tween", "PBS Buffer including 0.05% Tween"], "default": "PBS including 0.05% Tween"},
                {
                    "key": "capillary",
                    "label": "毛细管",
                    "type": "select",
                    "options": [
                        "Monolith NT.115 Capillary",
                        "Monolith NT.115 Hydrophobic Capillary",
                        "Monolith NT.115 Premium Capillary",
                    ],
                    "default": "Monolith NT.115 Capillary",
                },
                {"key": "temperature", "label": "实验温度(°C)", "type": "text", "default": "25"},
                {"key": "operator", "label": "操作员", "type": "text", "default": ""},
            ],
        },
        {
            "id": "system",
            "title": "系统设置",
            "fields": [
                {"key": "excitation_auto", "label": "激发光自动检测", "type": "bool", "default": True},
                {"key": "excitation_pct", "label": "激发光功率(%)", "type": "int", "min": 1, "max": 100, "step": 5, "default": 10},
                {"key": "mst_power", "label": "MST 功率", "type": "select", "options": ["低", "中", "高"], "default": "中"},
                {"key": "time_scheme", "label": "时间方案", "type": "text", "default": "[]"},
            ],
        },
    ]


EXPERIMENT_TYPE_CONFIGS: Dict[str, ExperimentTypeConfig] = {
    "pre_test": {
        "id": "pre_test",
        "name": "Pre-test",
        "icon": "☀",
        "description": "用于检查荧光与确定实验条件。",
        "sections": _base_sections(),
    },
    "binding_test": {
        "id": "binding_test",
        "name": "Binding Test",
        "icon": "◕",
        "description": "用于进行是否结合的快速判断与条件筛选。",
        "sections": _base_sections(),
    },
    "binding_affinity": {
        "id": "binding_affinity",
        "name": "Binding Affinity",
        "icon": "◈",
        "description": "用于拟合结合曲线并提取 Kd。",
        "sections": _base_sections(),
    },
    "expert_mode": {
        "id": "expert_mode",
        "name": "Expert Mode",
        "icon": "⚙",
        "description": "高级模式，支持自定义实验参数。",
        "sections": _base_sections(),
    },
}


_LEGACY_TYPE_NAME_TO_ID = {
    "Pre-test": "pre_test",
    "Binding Test": "binding_test",
    "Binding Affinity": "binding_affinity",
    "Expert Mode": "expert_mode",
}


def list_experiment_types() -> List[ExperimentTypeConfig]:
    return [deepcopy(EXPERIMENT_TYPE_CONFIGS[k]) for k in EXPERIMENT_TYPE_CONFIGS]


def normalize_experiment_type_id(value: str) -> str:
    if value in EXPERIMENT_TYPE_CONFIGS:
        return value
    return _LEGACY_TYPE_NAME_TO_ID.get(value, "pre_test")


def get_experiment_type_config(value: str) -> ExperimentTypeConfig:
    exp_id = normalize_experiment_type_id(value)
    return deepcopy(EXPERIMENT_TYPE_CONFIGS[exp_id])


def default_setup_data(value: str) -> Dict[str, Any]:
    config = get_experiment_type_config(value)
    out: Dict[str, Any] = {}
    for section in config.get("sections", []):
        for field in section.get("fields", []):
            out[field["key"]] = deepcopy(field.get("default"))
    return out
