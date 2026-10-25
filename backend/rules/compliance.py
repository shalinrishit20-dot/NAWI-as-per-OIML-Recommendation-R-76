"""Compose digital error (Ec) with applicable MPE for one observation.

PASS when abs(Ec) <= MPE; FAIL when abs(Ec) > MPE. No extra tolerance.

Does not reimplement Table 6, rounding elimination, or changeover formulas.
Does not run Table 3 classification. Does not assign report/instrument IDs.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Optional

from .error_determination import calculate_digital_error
from .oiml_r76 import (
    AccuracyClass,
    VerificationStage,
    calculate_mpe,
)

ComplianceVerdict = Literal["PASS", "FAIL"]


@dataclass(frozen=True)
class ObservationComplianceResult:
    standard_code: str
    standard_edition: str
    ruleset_version: str
    accuracy_class: AccuracyClass
    verification_stage: VerificationStage
    load: float
    indication: float
    verification_scale_interval: float
    actual_scale_interval: float
    error_method: Literal["direct", "changeover_point"]
    rounding_elimination_required: bool
    additional_load: Optional[float]
    indication_before_rounding: float
    error_before_rounding: float
    zero_error: float
    corrected_error: float
    absolute_corrected_error: float
    mpe_multiplier: float
    mpe: float
    margin_to_limit: float
    result: ComplianceVerdict
    error_rule_reference: str
    mpe_rule_reference: str


def evaluate_digital_observation(
    accuracy_class: AccuracyClass,
    load: float,
    indication: float,
    e: float,
    d: float,
    zero_error: float,
    stage: VerificationStage = "initial",
    additional_load: Optional[float] = None,
) -> ObservationComplianceResult:
    """Compare one digital observation's Ec with the applicable MPE."""
    error = calculate_digital_error(
        load=load,
        indication=indication,
        e=e,
        d=d,
        zero_error=zero_error,
        additional_load=additional_load,
    )
    mpe = calculate_mpe(
        accuracy_class=accuracy_class,
        load=load,
        e=e,
        stage=stage,
    )
    abs_ec = abs(error.corrected_error)
    margin = mpe.mpe - abs_ec
    verdict: ComplianceVerdict = "PASS" if abs_ec <= mpe.mpe else "FAIL"
    return ObservationComplianceResult(
        standard_code=error.standard_code,
        standard_edition=error.standard_edition,
        ruleset_version=error.ruleset_version,
        accuracy_class=mpe.accuracy_class,
        verification_stage=mpe.verification_stage,
        load=error.load,
        indication=error.indication,
        verification_scale_interval=error.verification_scale_interval,
        actual_scale_interval=error.actual_scale_interval,
        error_method=error.method,
        rounding_elimination_required=error.rounding_elimination_required,
        additional_load=error.additional_load,
        indication_before_rounding=error.indication_before_rounding,
        error_before_rounding=error.error_before_rounding,
        zero_error=error.zero_error,
        corrected_error=error.corrected_error,
        absolute_corrected_error=abs_ec,
        mpe_multiplier=mpe.multiplier,
        mpe=mpe.mpe,
        margin_to_limit=margin,
        result=verdict,
        error_rule_reference=error.rule_reference,
        mpe_rule_reference=mpe.rule_reference,
    )
