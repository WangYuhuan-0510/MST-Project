from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import List


@dataclass
class Sample:
    name: str
    concentration: float


class StepType(Enum):
    BASELINE = auto()
    INJECTION = auto()
    WASH = auto()


@dataclass
class Step:
    order: int
    type: StepType
    duration_s: float


@dataclass
class Experiment:
    name: str
    samples: List[Sample] = field(default_factory=list)
    steps: List[Step] = field(default_factory=list)

