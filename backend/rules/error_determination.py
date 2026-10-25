"""Digital-indication error determination (OIML R 76-1:2006).

Scope:
  - §3.5.3.2 Elimination of rounding error
  - Annex A §A.4.4.3 Evaluation of errors (changeover-point method)

This module computes P, E, and Ec only. It does not compare errors with MPE,
does not assign PASS/FAIL, and does not implement the A.4.2.3 zero-setting
procedure. E0 must be supplied by the caller.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Literal, Optional

from .oiml_r76 import RULESET_VERSION, STANDARD_CODE, STANDARD_EDITION

_RULE_REFERENCE = "OIML R 76-1:2006 §3.5.3.2; Annex A §A.4.4.3"

ErrorMethod = Literal["direct", "changeover_point"]


def _require_finite_number(value: object, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{name} must be a finite number")
    number = float(value)
    if not math.isfinite(number):
        raise ValueError(f"{name} must be a finite number")
    return number


def requires_rounding_elimination(e: float, d: float) -> bool:
    """True only when d > 0.2 e (§3.5.3.2). Equality is False."""
    e_value = _require_finite_number(e, "e")
    d_value = _require_finite_number(d, "d")
    if e_value <= 0:
        raise ValueError("e must be > 0")
    if d_value <= 0:
        raise ValueError("d must be > 0")
    return d_value > 0.2 * e_value


def indication_before_rounding(
    indication: float,
    e: float,
    additional_load: float,
) -> float:
    """P = I + 0.5 e − ΔL (Annex A §A.4.4.3)."""
    i_value = _require_finite_number(indication, "indication")
    e_value = _require_finite_number(e, "e")
    delta_l = _require_finite_number(additional_load, "additional_load")
    if e_value <= 0:
        raise ValueError("e must be > 0")
    if delta_l < 0:
        raise ValueError("additional_load must be >= 0")
    return i_value + 0.5 * e_value - delta_l


def error_before_rounding(
    load: float,
    indication: float,
    e: float,
    additional_load: float,
) -> float:
    """E = P − L with P from indication_before_rounding."""
    load_value = _require_finite_number(load, "load")
    if load_value < 0:
        raise ValueError("load must be >= 0")
    p = indication_before_rounding(indication, e, additional_load)
    return p - load_value


def corrected_error(error: float, zero_error: float) -> float:
    """Ec = E − E0. Both arguments are required; E0 is not defaulted."""
    e_value = _require_finite_number(error, "error")
    e0_value = _require_finite_number(zero_error, "zero_error")
    return e_value - e0_value


@dataclass(frozen=True)
class ErrorDeterminationResult:
    """Explainable digital-error result. No MPE or pass/fail fields."""

    standard_code: str
    standard_edition: str
    ruleset_version: str
    rule_reference: str
    load: float
    indication: float
    verification_scale_interval: float
    actual_scale_interval: float
    rounding_elimination_required: bool
    method: ErrorMethod
    additional_load: Optional[float]
    indication_before_rounding: float
    error_before_rounding: float
    zero_error: float
    corrected_error: float


def calculate_digital_error(
    load: float,
    indication: float,
    e: float,
    d: float,
    zero_error: float,
    additional_load: Optional[float] = None,
) -> ErrorDeterminationResult:
    """Determine P, E, and Ec for a digital indication.

    Path A (d > 0.2 e): changeover-point; additional_load is required.
    Path B (d <= 0.2 e): direct; additional_load must not be supplied.
    """
    load_value = _require_finite_number(load, "load")
    i_value = _require_finite_number(indication, "indication")
    e_value = _require_finite_number(e, "e")
    d_value = _require_finite_number(d, "d")
    e0_value = _require_finite_number(zero_error, "zero_error")
    if load_value < 0:
        raise ValueError("load must be >= 0")
    if e_value <= 0:
        raise ValueError("e must be > 0")
    if d_value <= 0:
        raise ValueError("d must be > 0")

    rounding_required = requires_rounding_elimination(e_value, d_value)

    if rounding_required:
        if additional_load is None:
            raise ValueError(
                "additional_load is required when d > 0.2 e "
                "(OIML R 76-1:2006 §3.5.3.2 changeover-point method)"
            )
        p = indication_before_rounding(i_value, e_value, additional_load)
        method: ErrorMethod = "changeover_point"
        delta: Optional[float] = float(additional_load)
    else:
        if additional_load is not None:
            raise ValueError(
                "additional_load must not be supplied when d <= 0.2 e "
                "(direct indication path)"
            )
        p = i_value
        method = "direct"
        delta = None

    error = p - load_value
    ec = corrected_error(error, e0_value)
    return ErrorDeterminationResult(
        standard_code=STANDARD_CODE,
        standard_edition=STANDARD_EDITION,
        ruleset_version=RULESET_VERSION,
        rule_reference=_RULE_REFERENCE,
        load=load_value,
        indication=i_value,
        verification_scale_interval=e_value,
        actual_scale_interval=d_value,
        rounding_elimination_required=rounding_required,
        method=method,
        additional_load=delta,
        indication_before_rounding=p,
        error_before_rounding=error,
        zero_error=e0_value,
        corrected_error=ec,
    )
