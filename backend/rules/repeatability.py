"""OIML R 76-1:2006 type-approval repeatability for ONE series of readings.

Scope (this module only):
  - §3.6.1: the difference between results of several weighings of the same
    load shall not be greater than the absolute value of the applicable MPE.
  - Annex A §A.4.10 type approval: required count is 10 weighings when
    Max < 1000 kg, otherwise at least 3. This function evaluates a single
    series at a given applied load.

Out of scope:
  - Verification-specific 0.8 Max procedure.
  - Numeric tolerances for “about 50 % of Max” or “close to 100 % of Max”.
  - Individual weighing error vs MPE (use evaluate_digital_observation).
  - Combining two series (0.5 Max and Max) into a test programme.
  - Table 6 MPE bands (delegated to calculate_mpe, initial stage only).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Sequence, Tuple

from .oiml_r76 import (
    RULESET_VERSION,
    STANDARD_CODE,
    STANDARD_EDITION,
    AccuracyClass,
    MassUnit,
    _require_accuracy_class,
    _require_finite_number,
    calculate_mpe,
    to_grams,
)

RepeatabilityStatus = Literal["INCOMPLETE", "PASS", "FAIL"]

_RULE_REF_REPEATABILITY = "OIML R 76-1:2006 §3.6.1; Annex A §A.4.10"
_TYPE_APPROVAL_MAX_KG_THRESHOLD_G = 1_000_000.0  # 1000 kg


@dataclass(frozen=True)
class RepeatabilitySeriesResult:
    """Immutable type-approval repeatability series result."""

    standard_code: str
    standard_edition: str
    ruleset_version: str
    rule_reference: str
    accuracy_class: AccuracyClass
    max_capacity: float
    applied_load: float
    verification_scale_interval: float
    unit: MassUnit
    weighing_count: int
    required_weighings: int
    minimum_result: float
    maximum_result: float
    spread: float
    mpe: float
    complete: bool
    spread_within_mpe: bool
    status: RepeatabilityStatus
    readings: Tuple[float, ...]


def type_approval_required_weighings(max_capacity: float, unit: MassUnit) -> int:
    """Annex A §A.4.10: 10 if Max < 1000 kg, else 3."""
    max_g = to_grams(max_capacity, unit)
    return 10 if max_g < _TYPE_APPROVAL_MAX_KG_THRESHOLD_G else 3


def evaluate_type_approval_repeatability_series(
    accuracy_class: AccuracyClass,
    max_capacity: float,
    applied_load: float,
    e: float,
    unit: MassUnit,
    readings: Sequence[object],
) -> RepeatabilitySeriesResult:
    """Evaluate one type-approval repeatability series against initial MPE.

    Spread = max(readings) − min(readings). PASS iff the series is complete
    and spread <= calculate_mpe(..., stage='initial').mpe. No extra tolerance.
    """
    cls = _require_accuracy_class(accuracy_class)
    max_value = _require_finite_number(max_capacity, "max_capacity")
    load_value = _require_finite_number(applied_load, "applied_load")
    e_value = _require_finite_number(e, "e")
    if max_value <= 0:
        raise ValueError("max_capacity must be > 0")
    if load_value < 0:
        raise ValueError("applied_load must be >= 0")
    if load_value > max_value:
        raise ValueError("applied_load must be <= max_capacity")
    if e_value <= 0:
        raise ValueError("e must be > 0")
    if not isinstance(readings, Sequence) or isinstance(readings, (str, bytes)):
        raise ValueError("readings must be a non-empty sequence of finite numbers")
    if len(readings) == 0:
        raise ValueError("readings must not be empty")

    parsed: list[float] = []
    for i, item in enumerate(readings):
        parsed.append(_require_finite_number(item, f"readings[{i}]"))

    required = type_approval_required_weighings(max_value, unit)
    mpe = calculate_mpe(cls, load_value, e_value, stage="initial")
    minimum = min(parsed)
    maximum = max(parsed)
    spread = maximum - minimum
    complete = len(parsed) >= required
    within = spread <= mpe.mpe
    if not complete:
        status: RepeatabilityStatus = "INCOMPLETE"
    elif within:
        status = "PASS"
    else:
        status = "FAIL"

    return RepeatabilitySeriesResult(
        standard_code=STANDARD_CODE,
        standard_edition=STANDARD_EDITION,
        ruleset_version=RULESET_VERSION,
        rule_reference=_RULE_REF_REPEATABILITY,
        accuracy_class=cls,
        max_capacity=max_value,
        applied_load=load_value,
        verification_scale_interval=e_value,
        unit=unit,  # type: ignore[arg-type]
        weighing_count=len(parsed),
        required_weighings=required,
        minimum_result=minimum,
        maximum_result=maximum,
        spread=spread,
        mpe=mpe.mpe,
        complete=complete,
        spread_within_mpe=within,
        status=status,
        readings=tuple(parsed),
    )
