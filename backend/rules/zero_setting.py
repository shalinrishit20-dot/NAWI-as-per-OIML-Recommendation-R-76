"""OIML R 76-1:2006 zero-setting accuracy (§4.5.2 / Annex A §A.4.2.3).

Supported scope (this module only):
  - digital indication
  - single-range instrument
  - non-automatic or semi-automatic zero-setting accuracy
  - limit: |zero deviation| ≤ 0.25 e after zero setting

Out of scope (must not silently pass):
  - automatic zero-setting
  - zero tracking
  - multiple-range special cases
  - §4.5.1 maximum effect / range of the zero-setting device
  - full §4.5 device compliance

Zero deviation is the indication-before-rounding at L = 0.
Corrected weighing error Ec is not used.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Optional

from .error_determination import (
    indication_before_rounding,
    requires_rounding_elimination,
)
from .oiml_r76 import (
    RULESET_VERSION,
    STANDARD_CODE,
    STANDARD_EDITION,
    SUPPORTED_MASS_UNITS,
    MassUnit,
    _require_finite_number,
)

ZeroSettingStatus = Literal["PASS", "FAIL"]
ZeroSettingMode = Literal["non_automatic", "semi_automatic"]
ErrorMethod = Literal["direct", "changeover_point"]

_SUPPORTED_MODES: tuple[ZeroSettingMode, ...] = ("non_automatic", "semi_automatic")
_RULE_REF_ZERO = (
    "OIML R 76-1:2006 §4.5.2; Annex A §A.4.2.3; Annex A §A.4.4.3"
)
_RULE_REF_ZERO_DIRECT = "OIML R 76-1:2006 §4.5.2; Annex A §A.4.2.3"


@dataclass(frozen=True)
class ZeroSettingResult:
    """Immutable zero-setting accuracy result (zero deviation vs ±0.25 e)."""

    standard_code: str
    standard_edition: str
    ruleset_version: str
    rule_reference: str
    setting_mode: ZeroSettingMode
    indication: float
    additional_load: Optional[float]
    verification_scale_interval: float
    actual_scale_interval: float
    unit: MassUnit
    rounding_elimination_required: bool
    error_method: ErrorMethod
    indication_before_rounding: float
    zero_error: float
    absolute_zero_error: float
    permitted_limit: float
    margin_to_limit: float
    status: ZeroSettingStatus


def evaluate_zero_setting_accuracy(
    indication: object,
    e: object,
    d: object,
    unit: object,
    additional_load: Optional[object] = None,
    setting_mode: object = "non_automatic",
) -> ZeroSettingResult:
    """Evaluate post-zero-setting deviation at L = 0.

    Changeover path (d > 0.2 e): P = I + 0.5e − ΔL; zero_error = P.
    Direct path (d ≤ 0.2 e): P = I; additional_load must not be supplied.
    PASS iff abs(zero_error) <= 0.25 e (equality passes).
    """
    if setting_mode not in _SUPPORTED_MODES:
        raise ValueError(
            "setting_mode must be 'non_automatic' or 'semi_automatic'; "
            "automatic zero-setting and zero-tracking are not implemented"
        )
    if unit not in SUPPORTED_MASS_UNITS:
        raise ValueError(
            "unit must be one of g, kg, t; "
            f"got {unit!r}"
        )
    i_value = _require_finite_number(indication, "indication")
    e_value = _require_finite_number(e, "e")
    d_value = _require_finite_number(d, "d")
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
        delta: Optional[float] = float(
            _require_finite_number(additional_load, "additional_load")
        )
        rule_ref = _RULE_REF_ZERO
    else:
        if additional_load is not None:
            raise ValueError(
                "additional_load must not be supplied when d <= 0.2 e "
                "(direct indication path)"
            )
        p = i_value
        method = "direct"
        delta = None
        rule_ref = _RULE_REF_ZERO_DIRECT

    zero_error = p  # L = 0
    limit = 0.25 * e_value
    abs_err = abs(zero_error)
    margin = limit - abs_err
    status: ZeroSettingStatus = "PASS" if abs_err <= limit else "FAIL"
    mode: ZeroSettingMode = setting_mode  # type: ignore[assignment]
    typed_unit: MassUnit = unit  # type: ignore[assignment]
    return ZeroSettingResult(
        standard_code=STANDARD_CODE,
        standard_edition=STANDARD_EDITION,
        ruleset_version=RULESET_VERSION,
        rule_reference=rule_ref,
        setting_mode=mode,
        indication=i_value,
        additional_load=delta,
        verification_scale_interval=e_value,
        actual_scale_interval=d_value,
        unit=typed_unit,
        rounding_elimination_required=rounding_required,
        error_method=method,
        indication_before_rounding=p,
        zero_error=zero_error,
        absolute_zero_error=abs_err,
        permitted_limit=limit,
        margin_to_limit=margin,
        status=status,
    )
