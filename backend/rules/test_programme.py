"""Aggregate currently implemented OIML R 76 core test-module results.

This is product/workflow logic, not a new OIML clause.

It consumes already-evaluated module results only. It does not recompute
MPE, Ec, spread, zero deviation, or tare series.

overall PASS means only that every implemented core module passed.
It is not a complete OIML R 76 type-evaluation or type-approval verdict.
full_standard_coverage is always False.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Optional, Sequence, Tuple

from .compliance import ObservationComplianceResult
from .eccentricity import EccentricityResult
from .oiml_r76 import RULESET_VERSION, STANDARD_CODE, STANDARD_EDITION
from .repeatability import RepeatabilitySeriesResult
from .tare_weighing import TareWeighingSeriesResult
from .zero_setting import ZeroSettingResult

ModuleStatus = Literal["INCOMPLETE", "PASS", "FAIL"]

SCOPE_NAME = "OIML R76 implemented core test scope"
SCOPE_NOTE = (
    "This result covers implemented zero-setting accuracy, weighing "
    "performance, quarter-segment eccentricity, repeatability, and "
    "subtractive tare weighing only and is not a complete OIML R76 "
    "type-evaluation verdict."
)

_MODULE_ORDER = (
    "zero_setting",
    "observation",
    "repeatability",
    "eccentricity",
    "tare_weighing",
)


@dataclass(frozen=True)
class CoreTestProgrammeResult:
    standard_code: str
    standard_edition: str
    ruleset_version: str
    scope_name: str
    scope_note: str
    full_standard_coverage: bool
    zero_setting_status: ModuleStatus
    observation_status: ModuleStatus
    repeatability_status: ModuleStatus
    eccentricity_status: ModuleStatus
    tare_weighing_status: ModuleStatus
    overall_status: ModuleStatus
    failed_modules: Tuple[str, ...]
    incomplete_modules: Tuple[str, ...]
    observation_count: int
    repeatability_half_max_status: Optional[ModuleStatus]
    repeatability_near_max_status: Optional[ModuleStatus]
    rule_references: Tuple[str, ...]


def _combine(*statuses: ModuleStatus) -> ModuleStatus:
    if any(s == "FAIL" for s in statuses):
        return "FAIL"
    if any(s == "INCOMPLETE" for s in statuses):
        return "INCOMPLETE"
    return "PASS"


def _observation_status(
    observations: Sequence[ObservationComplianceResult],
) -> ModuleStatus:
    if len(observations) == 0:
        return "INCOMPLETE"
    if any(o.result == "FAIL" for o in observations):
        return "FAIL"
    return "PASS"


def _repeatability_status(
    half: Optional[RepeatabilitySeriesResult],
    near: Optional[RepeatabilitySeriesResult],
) -> ModuleStatus:
    series = (half, near)
    if any(s is not None and s.status == "FAIL" for s in series):
        return "FAIL"
    if any(s is None or s.status == "INCOMPLETE" for s in series):
        return "INCOMPLETE"
    return "PASS"


def _optional_status(result: object, attr: str = "status") -> ModuleStatus:
    if result is None:
        return "INCOMPLETE"
    return getattr(result, attr)


def _collect_references(
    observations: Sequence[ObservationComplianceResult],
    half: Optional[RepeatabilitySeriesResult],
    near: Optional[RepeatabilitySeriesResult],
    eccentricity: Optional[EccentricityResult],
    zero_setting: Optional[ZeroSettingResult],
    tare_weighing: Optional[TareWeighingSeriesResult],
) -> Tuple[str, ...]:
    seen: set[str] = set()
    ordered: list[str] = []

    def add(ref: str) -> None:
        if ref not in seen:
            seen.add(ref)
            ordered.append(ref)

    if zero_setting is not None:
        add(zero_setting.rule_reference)
    for obs in observations:
        add(obs.error_rule_reference)
        add(obs.mpe_rule_reference)
    if half is not None:
        add(half.rule_reference)
    if near is not None:
        add(near.rule_reference)
    if eccentricity is not None:
        add(eccentricity.rule_reference)
    if tare_weighing is not None:
        add(tare_weighing.rule_reference)
    return tuple(ordered)


def evaluate_core_test_programme(
    observations: Sequence[ObservationComplianceResult],
    repeatability_half_max: Optional[RepeatabilitySeriesResult] = None,
    repeatability_near_max: Optional[RepeatabilitySeriesResult] = None,
    eccentricity: Optional[EccentricityResult] = None,
    zero_setting: Optional[ZeroSettingResult] = None,
    tare_weighing: Optional[TareWeighingSeriesResult] = None,
) -> CoreTestProgrammeResult:
    """Combine implemented core-module verdicts. Does not calculate standards."""
    if not isinstance(observations, Sequence) or isinstance(observations, (str, bytes)):
        raise ValueError("observations must be a sequence of ObservationComplianceResult")
    for i, item in enumerate(observations):
        if not isinstance(item, ObservationComplianceResult):
            raise ValueError(f"observations[{i}] must be ObservationComplianceResult")
    if repeatability_half_max is not None and not isinstance(
        repeatability_half_max, RepeatabilitySeriesResult
    ):
        raise ValueError("repeatability_half_max must be RepeatabilitySeriesResult or None")
    if repeatability_near_max is not None and not isinstance(
        repeatability_near_max, RepeatabilitySeriesResult
    ):
        raise ValueError("repeatability_near_max must be RepeatabilitySeriesResult or None")
    if eccentricity is not None and not isinstance(eccentricity, EccentricityResult):
        raise ValueError("eccentricity must be EccentricityResult or None")
    if zero_setting is not None and not isinstance(zero_setting, ZeroSettingResult):
        raise ValueError("zero_setting must be ZeroSettingResult or None")
    if tare_weighing is not None and not isinstance(tare_weighing, TareWeighingSeriesResult):
        raise ValueError("tare_weighing must be TareWeighingSeriesResult or None")

    zero_status: ModuleStatus = _optional_status(zero_setting)
    obs_status = _observation_status(observations)
    rep_status = _repeatability_status(repeatability_half_max, repeatability_near_max)
    ecc_status: ModuleStatus = _optional_status(eccentricity)
    tare_status: ModuleStatus = _optional_status(tare_weighing)
    overall = _combine(zero_status, obs_status, rep_status, ecc_status, tare_status)

    by_name = {
        "zero_setting": zero_status,
        "observation": obs_status,
        "repeatability": rep_status,
        "eccentricity": ecc_status,
        "tare_weighing": tare_status,
    }
    failed = tuple(name for name in _MODULE_ORDER if by_name[name] == "FAIL")
    incomplete = tuple(name for name in _MODULE_ORDER if by_name[name] == "INCOMPLETE")

    half_status: Optional[ModuleStatus] = (
        None if repeatability_half_max is None else repeatability_half_max.status
    )
    near_status: Optional[ModuleStatus] = (
        None if repeatability_near_max is None else repeatability_near_max.status
    )

    return CoreTestProgrammeResult(
        standard_code=STANDARD_CODE,
        standard_edition=STANDARD_EDITION,
        ruleset_version=RULESET_VERSION,
        scope_name=SCOPE_NAME,
        scope_note=SCOPE_NOTE,
        full_standard_coverage=False,
        zero_setting_status=zero_status,
        observation_status=obs_status,
        repeatability_status=rep_status,
        eccentricity_status=ecc_status,
        tare_weighing_status=tare_status,
        overall_status=overall,
        failed_modules=failed,
        incomplete_modules=incomplete,
        observation_count=len(observations),
        repeatability_half_max_status=half_status,
        repeatability_near_max_status=near_status,
        rule_references=_collect_references(
            observations,
            repeatability_half_max,
            repeatability_near_max,
            eccentricity,
            zero_setting,
            tare_weighing,
        ),
    )
