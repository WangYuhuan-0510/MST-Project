from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from mst.core.instruction_rules import (
    InstructionContent,
    InstructionValidationResult,
    PlanData,
    build_instruction_content,
    validate_instruction_inputs,
)


InstructionPageMode = Literal["missing", "content"]


@dataclass(frozen=True)
class InstructionPageState:
    mode: InstructionPageMode
    validation: InstructionValidationResult
    content: InstructionContent | None = None
    missing_messages: tuple[str, ...] = ()


def _build_missing_messages(validation: InstructionValidationResult) -> tuple[str, ...]:
    return tuple(
        validation.inline_errors.get(key) or key
        for key in validation.missing_fields
    )


def resolve_instruction_page_state(
    experiment_type_id: str,
    plan_data: PlanData,
) -> InstructionPageState:
    payload = dict(plan_data or {})
    validation = validate_instruction_inputs(experiment_type_id, payload)
    if not validation.can_enter_instructions:
        return InstructionPageState(
            mode="missing",
            validation=validation,
            content=None,
            missing_messages=_build_missing_messages(validation),
        )

    return InstructionPageState(
        mode="content",
        validation=validation,
        content=build_instruction_content(experiment_type_id, payload),
        missing_messages=(),
    )
