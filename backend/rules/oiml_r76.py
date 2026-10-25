"""OIML R 76-1:2006 fundamental Maximum Permissible Error (MPE) rules.

Scope (this module only):
  - §3.2 / Table 3 classification of ordinary single-range, non-grading instruments
  - §3.5.1 Maximum permissible errors on initial verification
  - Table 6
  - §3.5.2 Maximum permissible errors in service (twice initial-verification MPE)

Out of scope: multi-interval/multi-range instruments, grading Min=5e exception,
Class I Table 3 footnote / §3.4.4, e digit-sequence and e/d (§3.1.2) rules,
rounding-error elimination (§3.5.3.2), changeover points, corrected indication P
/ error Ec, repeatability, eccentric loading, tare, zero-setting, influence
factors, discrimination, sensitivity, and report generation.

Historical calculations must identify STANDARD_CODE, STANDARD_EDITION, and
RULESET_VERSION rather than an unspecified \"latest\" ruleset.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Literal, Optional, Tuple

STANDARD_CODE = "OIML R 76-1"
STANDARD_EDITION = "2006"
RULESET_VERSION = "R76-1-2006-v1"

AccuracyClass = Literal["I", "II", "III", "IIII"]
VerificationStage = Literal["initial", "in_service"]

SUPPORTED_ACCURACY_CLASSES: Tuple[AccuracyClass, ...] = ("I", "II", "III", "IIII")

# Table 6 bands: (upper inclusive bound in verification intervals m, multiplier).
# The last band for Class I has no Table 6 upper bound (None).
# For II / III / IIII the last listed upper bound is also the supported range
# limit; loads above that are rejected rather than inventing a further band.
_TABLE_6_BANDS = {
    "I": (
        (50_000.0, 0.5),
        (200_000.0, 1.0),
        (None, 1.5),
    ),
    "II": (
        (5_000.0, 0.5),
        (20_000.0, 1.0),
        (100_000.0, 1.5),
    ),
    "III": (
        (500.0, 0.5),
        (2_000.0, 1.0),
        (10_000.0, 1.5),
    ),
    "IIII": (
        (50.0, 0.5),
        (200.0, 1.0),
        (1_000.0, 1.5),
    ),
}

_RULE_REF_INITIAL = "OIML R 76-1:2006 §3.5.1 Table 6"
_RULE_REF_IN_SERVICE = "OIML R 76-1:2006 §3.5.1 Table 6; §3.5.2"
_RULE_REF_TABLE_3 = "OIML R 76-1:2006 §3.2 Table 3; §3.4.3"

MassUnit = Literal["g", "kg", "t"]
SUPPORTED_MASS_UNITS: Tuple[MassUnit, ...] = ("g", "kg", "t")
_GRAMS_PER_UNIT = {"g": 1.0, "kg": 1000.0, "t": 1_000_000.0}


@dataclass(frozen=True)
class MpeResult:
    """Immutable, explainable MPE calculation result."""

    standard_code: str
    standard_edition: str
    ruleset_version: str
    rule_reference: str
    accuracy_class: AccuracyClass
    load: float
    verification_scale_interval: float
    load_in_verification_intervals: float
    multiplier: float
    mpe: float
    verification_stage: VerificationStage


def _require_finite_number(value: object, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{name} must be a finite number")
    number = float(value)
    if not math.isfinite(number):
        raise ValueError(f"{name} must be a finite number")
    return number


def _require_accuracy_class(accuracy_class: object) -> AccuracyClass:
    if accuracy_class not in SUPPORTED_ACCURACY_CLASSES:
        raise ValueError(
            "accuracy_class must be one of I, II, III, IIII "
            f"(OIML R 76-1:2006 Table 6); got {accuracy_class!r}"
        )
    return accuracy_class  # type: ignore[return-value]


def verification_intervals(load: float, e: float) -> float:
    """Return m = load / e as used in Table 6.

    load must be >= 0; e must be > 0; both must be finite. Values are not
    clamped.
    """
    load_value = _require_finite_number(load, "load")
    e_value = _require_finite_number(e, "e")
    if load_value < 0:
        raise ValueError("load must be >= 0")
    if e_value <= 0:
        raise ValueError("e must be > 0")
    return load_value / e_value


def initial_verification_mpe_multiplier(
    accuracy_class: AccuracyClass,
    load: float,
    e: float,
) -> float:
    """Return the Table 6 multiplier 0.5, 1.0, or 1.5 for initial verification.

    Boundaries are inclusive of the listed upper m of each band
    (e.g. Class III, m = 500 -> 0.5 e; m > 500 -> 1.0 e).
    """
    cls = _require_accuracy_class(accuracy_class)
    m = verification_intervals(load, e)
    bands = _TABLE_6_BANDS[cls]
    for upper, multiplier in bands:
        if upper is None or m <= upper:
            return multiplier
    # Reached only when the last band has a finite upper bound and m exceeds it.
    last_upper = bands[-1][0]
    raise ValueError(
        f"load/e = {m} exceeds the supported OIML R 76-1:2006 Table 6 range "
        f"for accuracy class {cls} (maximum {last_upper:g} e)"
    )


def initial_verification_mpe(
    accuracy_class: AccuracyClass,
    load: float,
    e: float,
) -> float:
    """Absolute MPE on initial verification, in the same unit as e.

    MPE = Table 6 multiplier × e  (§3.5.1).
    """
    e_value = _require_finite_number(e, "e")
    multiplier = initial_verification_mpe_multiplier(accuracy_class, load, e_value)
    return multiplier * e_value


def in_service_mpe(
    accuracy_class: AccuracyClass,
    load: float,
    e: float,
) -> float:
    """Absolute MPE in service: twice initial-verification MPE (§3.5.2)."""
    return 2.0 * initial_verification_mpe(accuracy_class, load, e)


def calculate_mpe(
    accuracy_class: AccuracyClass,
    load: float,
    e: float,
    stage: VerificationStage = "initial",
) -> MpeResult:
    """Explainable MPE calculation for initial verification or in-service use."""
    if stage not in ("initial", "in_service"):
        raise ValueError("stage must be 'initial' or 'in_service'")

    cls = _require_accuracy_class(accuracy_class)
    load_value = _require_finite_number(load, "load")
    e_value = _require_finite_number(e, "e")
    m = verification_intervals(load_value, e_value)
    multiplier = initial_verification_mpe_multiplier(cls, load_value, e_value)
    initial_mpe = multiplier * e_value

    if stage == "initial":
        return MpeResult(
            standard_code=STANDARD_CODE,
            standard_edition=STANDARD_EDITION,
            ruleset_version=RULESET_VERSION,
            rule_reference=_RULE_REF_INITIAL,
            accuracy_class=cls,
            load=load_value,
            verification_scale_interval=e_value,
            load_in_verification_intervals=m,
            multiplier=multiplier,
            mpe=initial_mpe,
            verification_stage="initial",
        )

    return MpeResult(
        standard_code=STANDARD_CODE,
        standard_edition=STANDARD_EDITION,
        ruleset_version=RULESET_VERSION,
        rule_reference=_RULE_REF_IN_SERVICE,
        accuracy_class=cls,
        load=load_value,
        verification_scale_interval=e_value,
        load_in_verification_intervals=m,
        multiplier=2.0 * multiplier,
        mpe=2.0 * initial_mpe,
        verification_stage="in_service",
    )


@dataclass(frozen=True)
class ClassificationResult:
    """Immutable Table 3 classification decision for a single-range instrument."""

    standard_code: str
    standard_edition: str
    ruleset_version: str
    rule_reference: str
    accuracy_class: AccuracyClass
    max_capacity: float
    min_capacity: float
    verification_scale_interval: float
    actual_scale_interval: float
    unit: MassUnit
    max_capacity_g: float
    min_capacity_g: float
    verification_scale_interval_g: float
    actual_scale_interval_g: float
    number_of_verification_intervals: float
    minimum_n: Optional[float]
    maximum_n: Optional[float]
    minimum_capacity_multiplier: Optional[float]
    minimum_capacity_required: Optional[float]
    minimum_capacity_in_d: Optional[float]
    valid: bool
    errors: Tuple[str, ...]


def to_grams(value: float, unit: object) -> float:
    """Convert a mass in g, kg, or t to grams. Unsupported units raise ValueError."""
    if unit not in SUPPORTED_MASS_UNITS:
        raise ValueError(
            "unit must be one of g, kg, t (OIML R 76-1:2006 Table 3 thresholds "
            f"are expressed in grams); got {unit!r}"
        )
    amount = _require_finite_number(value, "mass")
    return amount * _GRAMS_PER_UNIT[unit]  # type: ignore[index]


def _format_n(n: float) -> str:
    if n == int(n):
        return str(int(n))
    return f"{n:g}"


def _append_n_and_min_errors(
    errors: list[str],
    *,
    class_label: str,
    n: float,
    min_in_d: float,
    minimum_n: float,
    maximum_n: Optional[float],
    min_d_required: float,
    n_context: str,
    min_context: str,
) -> None:
    if n < minimum_n:
        errors.append(
            f"{class_label} requires at least {_format_n(minimum_n)} verification "
            f"intervals {n_context}; calculated n = {_format_n(n)}."
        )
    if maximum_n is not None and n > maximum_n:
        errors.append(
            f"{class_label} allows at most {_format_n(maximum_n)} verification "
            f"intervals {n_context}; calculated n = {_format_n(n)}."
        )
    if min_in_d < min_d_required:
        errors.append(
            f"Minimum capacity must be at least {_format_n(min_d_required)} d "
            f"{min_context}; calculated Min = {_format_n(min_in_d)} d."
        )


def validate_single_range_classification(
    accuracy_class: AccuracyClass,
    max_capacity: float,
    min_capacity: float,
    e: float,
    d: float,
    unit: MassUnit,
) -> ClassificationResult:
    """Validate ordinary single-range, non-grading instruments against Table 3.

    Malformed inputs raise ValueError. Table 3 non-compliance returns
    valid=False with explainable errors; it does not raise.
    Does not assess whether e and d have a permitted relationship.
    Minimum capacity is compared with multiplier × d per §3.4.3.
    """
    cls = _require_accuracy_class(accuracy_class)
    if unit not in SUPPORTED_MASS_UNITS:
        raise ValueError(
            "unit must be one of g, kg, t (OIML R 76-1:2006 Table 3 thresholds "
            f"are expressed in grams); got {unit!r}"
        )
    max_value = _require_finite_number(max_capacity, "max_capacity")
    min_value = _require_finite_number(min_capacity, "min_capacity")
    e_value = _require_finite_number(e, "e")
    d_value = _require_finite_number(d, "d")
    if max_value <= 0:
        raise ValueError("max_capacity must be > 0")
    if min_value < 0:
        raise ValueError("min_capacity must be >= 0")
    if e_value <= 0:
        raise ValueError("e must be > 0")
    if d_value <= 0:
        raise ValueError("d must be > 0")
    if min_value >= max_value:
        raise ValueError("min_capacity must be < max_capacity")

    typed_unit: MassUnit = unit  # type: ignore[assignment]
    max_g = to_grams(max_value, typed_unit)
    min_g = to_grams(min_value, typed_unit)
    e_g = to_grams(e_value, typed_unit)
    d_g = to_grams(d_value, typed_unit)
    n = max_value / e_value
    # §3.4.3: last column of Table 3 uses actual scale interval d, not e.
    min_in_d = min_value / d_value

    minimum_n: Optional[float] = None
    maximum_n: Optional[float] = None
    min_d_required: Optional[float] = None
    errors: list[str] = []

    if cls == "I":
        minimum_n = 50_000.0
        maximum_n = None
        min_d_required = 100.0
        if e_g < 0.001:
            errors.append(
                "Class I verification interval must be at least 0.001 g; "
                f"calculated e = {e_g:g} g."
            )
        _append_n_and_min_errors(
            errors,
            class_label="Class I",
            n=n,
            min_in_d=min_in_d,
            minimum_n=50_000.0,
            maximum_n=None,
            min_d_required=100.0,
            n_context="(Table 3, no upper limit on n)",
            min_context="for Class I",
        )
    elif cls == "II":
        maximum_n = 100_000.0
        if 0.001 <= e_g <= 0.05:
            minimum_n = 100.0
            min_d_required = 20.0
            _append_n_and_min_errors(
                errors,
                class_label="Class II",
                n=n,
                min_in_d=min_in_d,
                minimum_n=100.0,
                maximum_n=100_000.0,
                min_d_required=20.0,
                n_context="for e between 0.001 g and 0.05 g",
                min_context="for this Class II band",
            )
        elif e_g >= 0.1:
            minimum_n = 5_000.0
            min_d_required = 50.0
            _append_n_and_min_errors(
                errors,
                class_label="Class II",
                n=n,
                min_in_d=min_in_d,
                minimum_n=5_000.0,
                maximum_n=100_000.0,
                min_d_required=50.0,
                n_context="for e >= 0.1 g",
                min_context="for this Class II band",
            )
        else:
            errors.append(
                f"Class II verification interval {e_g:g} g falls outside the "
                "Table 3 permitted e bands."
            )
            if e_g < 0.001:
                errors.append(
                    "Class II verification interval must be at least 0.001 g; "
                    f"calculated e = {e_g:g} g."
                )
    elif cls == "III":
        maximum_n = 10_000.0
        min_d_required = 20.0
        if 0.1 <= e_g <= 2.0:
            minimum_n = 100.0
            _append_n_and_min_errors(
                errors,
                class_label="Class III",
                n=n,
                min_in_d=min_in_d,
                minimum_n=100.0,
                maximum_n=10_000.0,
                min_d_required=20.0,
                n_context="for e between 0.1 g and 2 g",
                min_context="for this Class III band",
            )
        elif e_g >= 5.0:
            minimum_n = 500.0
            _append_n_and_min_errors(
                errors,
                class_label="Class III",
                n=n,
                min_in_d=min_in_d,
                minimum_n=500.0,
                maximum_n=10_000.0,
                min_d_required=20.0,
                n_context="for e >= 5 g",
                min_context="for this Class III band",
            )
        else:
            errors.append(
                f"Class III verification interval {e_g:g} g falls outside the "
                "Table 3 permitted e bands."
            )
    else:
        minimum_n = 100.0
        maximum_n = 1_000.0
        min_d_required = 10.0
        if e_g < 5.0:
            errors.append(
                "Class IIII verification interval must be at least 5 g; "
                f"calculated e = {e_g:g} g."
            )
        _append_n_and_min_errors(
            errors,
            class_label="Class IIII",
            n=n,
            min_in_d=min_in_d,
            minimum_n=100.0,
            maximum_n=1_000.0,
            min_d_required=10.0,
            n_context="(Table 3)",
            min_context="for Class IIII",
        )

    required_min = (
        None if min_d_required is None else min_d_required * d_value
    )
    return ClassificationResult(
        standard_code=STANDARD_CODE,
        standard_edition=STANDARD_EDITION,
        ruleset_version=RULESET_VERSION,
        rule_reference=_RULE_REF_TABLE_3,
        accuracy_class=cls,
        max_capacity=max_value,
        min_capacity=min_value,
        verification_scale_interval=e_value,
        actual_scale_interval=d_value,
        unit=typed_unit,
        max_capacity_g=max_g,
        min_capacity_g=min_g,
        verification_scale_interval_g=e_g,
        actual_scale_interval_g=d_g,
        number_of_verification_intervals=n,
        minimum_n=minimum_n,
        maximum_n=maximum_n,
        minimum_capacity_multiplier=min_d_required,
        minimum_capacity_required=required_min,
        minimum_capacity_in_d=min_d_required,
        valid=len(errors) == 0,
        errors=tuple(errors),
    )
