from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable


PlanData = dict[str, Any]
InstructionBuilder = Callable[[PlanData], "InstructionContent"]


@dataclass(frozen=True)
class InstructionFieldRule:
    key: str
    required: bool = False
    visible: bool = True
    highlight_when_missing: bool = False
    missing_message: str = ""


@dataclass
class InstructionValidationResult:
    can_enter_instructions: bool
    missing_fields: list[str] = field(default_factory=list)
    inline_errors: dict[str, str] = field(default_factory=dict)
    highlighted_fields: list[str] = field(default_factory=list)


@dataclass
class InstructionContent:
    title: str
    summary: list[tuple[str, str]] = field(default_factory=list)
    steps: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class ExperimentInstructionRuleSet:
    experiment_type_id: str
    field_rules: dict[str, InstructionFieldRule]
    instruction_builder: InstructionBuilder


_TYPE_ALIASES = {
    "pre_test": "pre_test",
    "binding_test": "binding_test",
    "binding_check": "binding_test",
    "binding_affinity": "binding_affinity",
    "expert_mode": "expert_mode",
    "Pre-test": "pre_test",
    "Binding Test": "binding_test",
    "Binding Check": "binding_test",
    "Binding Affinity": "binding_affinity",
    "Expert Mode": "expert_mode",
}


def normalize_instruction_experiment_type_id(value: str) -> str:
    return _TYPE_ALIASES.get(str(value or "").strip(), "pre_test")


def _clean_text(value: Any) -> str:
    return str(value or "").strip()


def _is_missing_value(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, str):
        text = value.strip()
        return text == "" or text in {"—", "?", "Unknown", "unknown"}
    return False


def _format_value(value: Any, fallback: str = "—") -> str:
    text = _clean_text(value)
    return text or fallback


def _format_with_unit(value: Any, unit: Any, fallback: str = "—") -> str:
    value_text = _clean_text(value)
    if not value_text:
        return fallback
    unit_text = _clean_text(unit)
    return f"{value_text} {unit_text}".strip()


def _field_rule(
    key: str,
    *,
    required: bool = False,
    visible: bool = True,
    highlight_when_missing: bool = False,
    missing_message: str = "",
) -> InstructionFieldRule:
    return InstructionFieldRule(
        key=key,
        required=required,
        visible=visible,
        highlight_when_missing=highlight_when_missing,
        missing_message=missing_message,
    )


def _required_concentration(key: str) -> InstructionFieldRule:
    return _field_rule(
        key,
        required=True,
        visible=True,
        highlight_when_missing=True,
        missing_message="Please enter a valid concentration",
    )


def _required_selection(key: str) -> InstructionFieldRule:
    return _field_rule(
        key,
        required=True,
        visible=True,
        highlight_when_missing=True,
        missing_message="Please select a value",
    )


def _format_yes_no(value: Any) -> str:
    return "Yes" if bool(value) else "No"


def build_pretest_instructions(plan_data: PlanData) -> InstructionContent:
    target = _format_value(plan_data.get("target"))
    target_stock = _format_with_unit(plan_data.get("target_stock"), plan_data.get("target_stock_unit"))
    assay = _format_value(plan_data.get("target_assay"))
    buffer = _format_value(plan_data.get("buffer"))
    capillary = _format_value(plan_data.get("capillary"))
    excitation = _format_value(plan_data.get("excitation"))
    mst_power = _format_value(plan_data.get("mst_power"))

    return InstructionContent(
        title="Pretest Instructions",
        summary=[
            ("Experiment Type", "Pretest"),
            ("Target", target),
            ("Target stock", target_stock),
            ("Assay concentration", assay),
            ("Buffer", buffer),
            ("Capillary", capillary),
            ("Excitation", excitation),
            ("MST power", mst_power),
        ],
        steps=[
            f"Calculate the minimum required stock solution and buffer volumes using {target_stock} target stock and {buffer} as assay buffer.",
            f"Prepare the intermediate sample from the configured target stock ({target_stock}). Use the assay concentration ({assay}) directly if no predilution is required.",
            f"Prepare the assay sample in {buffer}, keeping ligand excluded for this pretest workflow.",
            f"Dip {capillary} capillaries into the assay sample, place them into the device tray, and start the pretest measurement.",
            "Review fluorescence quality, adsorption risk, and baseline signal stability before moving on to interaction experiments.",
        ],
        notes=[
            "Pretest is used to confirm that the labeled target behaves well before any ligand is introduced.",
            f"Use the configured excitation ({excitation}) and MST power ({mst_power}) as the starting instrument settings.",
        ],
    )


def build_binding_test_instructions(plan_data: PlanData) -> InstructionContent:
    target = _format_value(plan_data.get("target"))
    ligand = _format_value(plan_data.get("ligand"))
    target_stock = _format_with_unit(plan_data.get("target_stock"), plan_data.get("target_stock_unit"))
    ligand_stock = _format_with_unit(plan_data.get("lig_stock"), plan_data.get("lig_stock_unit"))
    buffer = _format_value(plan_data.get("buffer"))
    capillary = _format_value(plan_data.get("capillary"))
    excitation = _format_value(plan_data.get("excitation"))
    mst_power = _format_value(plan_data.get("mst_power"))
    ligand_in_dmso = _format_yes_no(plan_data.get("lig_in_dmso"))

    return InstructionContent(
        title="Binding Check Instructions",
        summary=[
            ("Experiment Type", "Binding Check"),
            ("Target", target),
            ("Ligand", ligand),
            ("Target stock", target_stock),
            ("Ligand stock", ligand_stock),
            ("Buffer", buffer),
            ("Capillary", capillary),
            ("Ligand in DMSO", ligand_in_dmso),
            ("Excitation", excitation),
            ("MST power", mst_power),
        ],
        steps=[
            f"Calculate the minimum required target stock, ligand stock, and buffer volumes using {target_stock}, {ligand_stock}, and {buffer}.",
            f"Prepare the intermediate samples for {target} and {ligand}. Set up a target-only control sample and a target-plus-ligand complex sample.",
            f"If the ligand stock is prepared in DMSO, keep the solvent fraction matched between the control and complex samples.",
            f"Prepare the final assay samples in {buffer}, then load them into {capillary} capillaries.",
            f"Run the Binding Check measurement using excitation {excitation} and MST power {mst_power}, then compare target-only and complex responses.",
        ],
        notes=[
            "Binding Check is a qualitative experiment used to verify whether a measurable interaction signal is present.",
            "If no clear separation is observed, revisit Plan and adjust ligand concentration, buffer, capillary type, or labeling conditions.",
        ],
    )


def build_binding_affinity_instructions(plan_data: PlanData) -> InstructionContent:
    target = _format_value(plan_data.get("target"))
    ligand = _format_value(plan_data.get("ligand"))
    target_stock = _format_with_unit(plan_data.get("target_stock"), plan_data.get("target_stock_unit"))
    ligand_stock = _format_with_unit(plan_data.get("lig_stock"), plan_data.get("lig_stock_unit"))
    high_conc = _format_with_unit(plan_data.get("hi_conc"), plan_data.get("lig_stock_unit"))
    estimated_kd = _format_with_unit(plan_data.get("kd_estimated"), plan_data.get("kd_unit"))
    buffer = _format_value(plan_data.get("buffer"))
    capillary = _format_value(plan_data.get("capillary"))
    excitation = _format_value(plan_data.get("excitation"))
    mst_power = _format_value(plan_data.get("mst_power"))
    ligand_in_dmso = _format_yes_no(plan_data.get("lig_in_dmso"))

    return InstructionContent(
        title="Binding Affinity Instructions",
        summary=[
            ("Experiment Type", "Binding Affinity"),
            ("Target", target),
            ("Ligand", ligand),
            ("Target stock", target_stock),
            ("Ligand stock", ligand_stock),
            ("High concentration", high_conc),
            ("Estimated Kd", estimated_kd),
            ("Buffer", buffer),
            ("Capillary", capillary),
            ("Ligand in DMSO", ligand_in_dmso),
            ("Excitation", excitation),
            ("MST power", mst_power),
        ],
        steps=[
            f"Calculate the minimum required target stock, ligand stock, and buffer volumes using {target_stock}, {ligand_stock}, and a highest ligand concentration of {high_conc}.",
            f"Prepare the intermediate samples for {target} and {ligand}. If needed, predilute the target to a suitable working concentration before mixing.",
            f"Prepare a serial dilution of the ligand starting from {high_conc}, using matched ligand buffer for the full dilution series.",
            f"Add the target sample to each ligand dilution point, mix thoroughly, and keep the final assay conditions consistent across the full series.",
            f"Load all samples into {capillary} capillaries and run the Binding Affinity measurement using excitation {excitation} and MST power {mst_power}.",
            "Fit the resulting binding curve and review whether the concentration range properly spans the transition region.",
        ],
        notes=[
            "Binding Affinity is intended for quantitative analysis of the interaction and should be run only after a convincing binding signal is observed.",
            f"Estimated Kd ({estimated_kd}) is optional, but it is useful for checking whether the selected high concentration is appropriate.",
        ],
    )


def build_expert_mode_instructions(plan_data: PlanData) -> InstructionContent:
    return InstructionContent(
        title="Expert Mode Instructions",
        summary=[
            ("Target", _format_value(plan_data.get("target"))),
            ("Ligand", _format_value(plan_data.get("ligand"))),
        ],
        steps=[
            "Review all custom parameters configured in Plan.",
            "Confirm capillary, buffer, and system settings before running the expert workflow.",
            "Execute the experiment according to the custom protocol.",
        ],
        notes=["Expert Mode leaves most parameter interpretation to the operator."],
    )


_PRETEST_RULES = ExperimentInstructionRuleSet(
    experiment_type_id="pre_test",
    field_rules={
        "target_stock": _required_concentration("target_stock"),
        "capillary": _required_selection("capillary"),
        "ligand": _field_rule("ligand", visible=False),
        "kd_estimated": _field_rule("kd_estimated", visible=False),
        "kd_unit": _field_rule("kd_unit", visible=False),
        "lig_stock": _field_rule("lig_stock", visible=False),
        "lig_stock_unit": _field_rule("lig_stock_unit", visible=False),
        "lig_in_dmso": _field_rule("lig_in_dmso", visible=False),
        "check_buffer_auto_fluorescence": _field_rule("check_buffer_auto_fluorescence", visible=True),
        "hi_conc": _field_rule("hi_conc", visible=False),
    },
    instruction_builder=build_pretest_instructions,
)

_BINDING_TEST_RULES = ExperimentInstructionRuleSet(
    experiment_type_id="binding_test",
    field_rules={
        "target_stock": _required_concentration("target_stock"),
        "lig_stock": _required_concentration("lig_stock"),
        "capillary": _required_selection("capillary"),
        "ligand": _field_rule("ligand", visible=True),
        "kd_estimated": _field_rule("kd_estimated", visible=True),
        "kd_unit": _field_rule("kd_unit", visible=True),
        "lig_stock_unit": _field_rule("lig_stock_unit", visible=True),
        "lig_in_dmso": _field_rule("lig_in_dmso", visible=True),
        "check_buffer_auto_fluorescence": _field_rule("check_buffer_auto_fluorescence", visible=True),
        "hi_conc": _field_rule("hi_conc", visible=True),
    },
    instruction_builder=build_binding_test_instructions,
)

_BINDING_AFFINITY_RULES = ExperimentInstructionRuleSet(
    experiment_type_id="binding_affinity",
    field_rules={
        "target_stock": _required_concentration("target_stock"),
        "lig_stock": _required_concentration("lig_stock"),
        "capillary": _required_selection("capillary"),
        "ligand": _field_rule("ligand", visible=True),
        "kd_estimated": _field_rule("kd_estimated", visible=True),
        "kd_unit": _field_rule("kd_unit", visible=True),
        "lig_stock_unit": _field_rule("lig_stock_unit", visible=True),
        "lig_in_dmso": _field_rule("lig_in_dmso", visible=True),
        "hi_conc": _field_rule("hi_conc", visible=True),
    },
    instruction_builder=build_binding_affinity_instructions,
)

_EXPERT_MODE_RULES = ExperimentInstructionRuleSet(
    experiment_type_id="expert_mode",
    field_rules={
        "target_stock": _required_concentration("target_stock"),
        "lig_stock": _required_concentration("lig_stock"),
        "capillary": _required_selection("capillary"),
        "ligand": _field_rule("ligand", visible=True),
        "kd_estimated": _field_rule("kd_estimated", visible=True),
        "kd_unit": _field_rule("kd_unit", visible=True),
        "lig_stock_unit": _field_rule("lig_stock_unit", visible=True),
        "lig_in_dmso": _field_rule("lig_in_dmso", visible=True),
        "hi_conc": _field_rule("hi_conc", visible=True),
    },
    instruction_builder=build_expert_mode_instructions,
)


INSTRUCTION_RULES: dict[str, ExperimentInstructionRuleSet] = {
    "pre_test": _PRETEST_RULES,
    "binding_test": _BINDING_TEST_RULES,
    "binding_affinity": _BINDING_AFFINITY_RULES,
    "expert_mode": _EXPERT_MODE_RULES,
}


def get_instruction_rules(experiment_type_id: str) -> ExperimentInstructionRuleSet:
    normalized = normalize_instruction_experiment_type_id(experiment_type_id)
    return INSTRUCTION_RULES.get(normalized, _PRETEST_RULES)


def get_visible_instruction_fields(experiment_type_id: str) -> dict[str, bool]:
    rules = get_instruction_rules(experiment_type_id)
    return {key: rule.visible for key, rule in rules.field_rules.items()}


def get_instruction_required_fields(experiment_type_id: str) -> list[str]:
    rules = get_instruction_rules(experiment_type_id)
    return [key for key, rule in rules.field_rules.items() if rule.required]


def initialize_plan_data_for_new_experiment(
    experiment_type_id: str,
    base_data: PlanData | None = None,
) -> PlanData:
    payload = dict(base_data or {})
    for key in get_instruction_required_fields(experiment_type_id):
        payload[key] = ""
    return payload


def validate_instruction_inputs(
    experiment_type_id: str,
    plan_data: PlanData,
) -> InstructionValidationResult:
    rules = get_instruction_rules(experiment_type_id)
    missing_fields: list[str] = []
    inline_errors: dict[str, str] = {}
    highlighted_fields: list[str] = []

    for key, rule in rules.field_rules.items():
        if not rule.required:
            continue
        if not _is_missing_value(plan_data.get(key)):
            continue
        missing_fields.append(key)
        if rule.missing_message:
            inline_errors[key] = rule.missing_message
        if rule.highlight_when_missing:
            highlighted_fields.append(key)

    return InstructionValidationResult(
        can_enter_instructions=not missing_fields,
        missing_fields=missing_fields,
        inline_errors=inline_errors,
        highlighted_fields=highlighted_fields,
    )


def build_instruction_content(
    experiment_type_id: str,
    plan_data: PlanData,
) -> InstructionContent:
    rules = get_instruction_rules(experiment_type_id)
    return rules.instruction_builder(dict(plan_data or {}))
