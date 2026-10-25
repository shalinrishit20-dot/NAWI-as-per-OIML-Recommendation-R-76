"""OIML R 76-1:2006 eccentric loading for ordinary receptors ≤4 supports.

Scope (this module only):
  - §3.6.2 / §3.6.2.1
  - Annex A §A.4.7 / §A.4.7.1
  Ordinary instrument, load receptor with not more than four points of
  support. Test load is 1/3 of (Max + corresponding maximum additive tare).
  Four quarter segments are loaded in turn; the centre is not required.
  Each position's already-corrected error must satisfy the applicable MPE.

Out of scope:
  - >4 support points (§3.6.2.2 / A.4.7.2)
  - tanks/hoppers/special receptors (§3.6.2.3 / A.4.7.3)
  - rolling/vehicle loads (§3.6.2.4 / A.4.7.4)
  - automatic zero-setting workflow, sketches, placement geometry
  - recomputing P / E / E0 / Ec (error_determination / observation composer)
  - Table 6 (delegated to calculate_mpe, initial stage)

This module accepts corrected errors Ec per quarter. It does not determine
those errors.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Mapping, Tuple

from .oiml_r76 import (
    RULESET_VERSION,
    STANDARD_CODE,
    STANDARD_EDITION,
    SUPPORTED_MASS_UNITS,
    AccuracyClass,
    MassUnit,
    _require_accuracy_class,
    _require_finite_number,
    calculate_mpe,
)

EccentricityStatus = Literal["INCOMPLETE", "PASS", "FAIL"]
QuarterPosition = Literal["Q1", "Q2", "Q3", "Q4"]

CANONICAL_POSITIONS: Tuple[QuarterPosition, ...] = ("Q1", "Q2", "Q3", "Q4")
_RULE_REF_ECCENTRICITY = (
    "OIML R 76-1:2006 §3.6.2; §3.6.2.1; Annex A §A.4.7; §A.4.7.1"
)


@dataclass(frozen=True)
class EccentricityResult:
    """Immutable quarter-segment eccentricity series result."""

    standard_code: str
    standard_edition: str
    ruleset_version: str
    rule_reference: str
    accuracy_class: AccuracyClass
    max_capacity: float
    maximum_additive_tare_effect: float
    verification_scale_interval: float
    unit: MassUnit
    required_test_load: float
    required_positions: Tuple[QuarterPosition, ...]
    tested_positions: Tuple[QuarterPosition, ...]
    mpe: float
    position_errors: Tuple[Tuple[QuarterPosition, float], ...]
    failed_positions: Tuple[QuarterPosition, ...]
    complete: bool
    all_positions_within_mpe: bool
    status: EccentricityStatus


def evaluate_quarter_segment_eccentricity(
    accuracy_class: AccuracyClass,
    max_capacity: float,
    e: float,
    unit: MassUnit,
    position_errors: Mapping[object, object],
    maximum_additive_tare_effect: float = 0,
) -> EccentricityResult:
    """Evaluate four-quarter eccentricity using already-corrected errors.

    required_test_load = (Max + maximum additive tare) / 3.
    PASS iff all four Q1–Q4 errors satisfy abs(Ec) <= initial MPE at that load.
    """
    cls = _require_accuracy_class(accuracy_class)
    if unit not in SUPPORTED_MASS_UNITS:
        raise ValueError(
            "unit must be one of g, kg, t; "
            f"got {unit!r}"
        )
    max_value = _require_finite_number(max_capacity, "max_capacity")
    e_value = _require_finite_number(e, "e")
    tare = _require_finite_number(
        maximum_additive_tare_effect, "maximum_additive_tare_effect"
    )
    if max_value <= 0:
        raise ValueError("max_capacity must be > 0")
    if e_value <= 0:
        raise ValueError("e must be > 0")
    if tare < 0:
        raise ValueError("maximum_additive_tare_effect must be >= 0")
    if not isinstance(position_errors, Mapping):
        raise ValueError("position_errors must be a mapping of Q1–Q4 to corrected errors")
    if len(position_errors) == 0:
        raise ValueError("position_errors must not be empty")
    if len(position_errors) > 4:
        raise ValueError("at most four quarter positions Q1–Q4 are allowed")

    parsed: dict[QuarterPosition, float] = {}
    for key, raw in position_errors.items():
        if key not in CANONICAL_POSITIONS:
            raise ValueError(
                f"unknown eccentric position {key!r}; allowed: Q1, Q2, Q3, Q4"
            )
        label: QuarterPosition = key  # type: ignore[assignment]
        parsed[label] = _require_finite_number(raw, f"position_errors[{key}]")

    required_load = (max_value + tare) / 3.0
    mpe = calculate_mpe(cls, required_load, e_value, stage="initial")
    tested = tuple(p for p in CANONICAL_POSITIONS if p in parsed)
    ordered_errors = tuple((p, parsed[p]) for p in tested)
    failed = tuple(
        p for p, err in ordered_errors if abs(err) > mpe.mpe
    )
    complete = len(tested) == 4
    all_within = len(failed) == 0
    if not complete:
        status: EccentricityStatus = "INCOMPLETE"
    elif all_within:
        status = "PASS"
    else:
        status = "FAIL"

    typed_unit: MassUnit = unit  # type: ignore[assignment]
    return EccentricityResult(
        standard_code=STANDARD_CODE,
        standard_edition=STANDARD_EDITION,
        ruleset_version=RULESET_VERSION,
        rule_reference=_RULE_REF_ECCENTRICITY,
        accuracy_class=cls,
        max_capacity=max_value,
        maximum_additive_tare_effect=tare,
        verification_scale_interval=e_value,
        unit=typed_unit,
        required_test_load=required_load,
        required_positions=CANONICAL_POSITIONS,
        tested_positions=tested,
        mpe=mpe.mpe,
        position_errors=ordered_errors,
        failed_positions=failed,
        complete=complete,
        all_positions_within_mpe=all_within,
        status=status,
    )
