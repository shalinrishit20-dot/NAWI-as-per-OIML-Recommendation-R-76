"""OIML R 76-1:2006 tare weighing — subtractive tare series (implemented subset).

Supported:
  - digital indication, single-range
  - one fixed tare value per series
  - subtractive tare
  - initial verification MPE via evaluate_digital_observation
  - at least 5 net-load observations for completeness

Out of scope (must not silently PASS):
  - multiple tare values in one call
  - additive / preset / automatic tare devices
  - multiple-range instruments
  - full tare-device compliance
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Mapping, Optional, Sequence, Tuple

from .compliance import ObservationComplianceResult, evaluate_digital_observation
from .oiml_r76 import (
    RULESET_VERSION,
    STANDARD_CODE,
    STANDARD_EDITION,
    SUPPORTED_MASS_UNITS,
    AccuracyClass,
    MassUnit,
    _require_accuracy_class,
    _require_finite_number,
)

TareWeighingStatus = Literal["INCOMPLETE", "PASS", "FAIL"]
_REQUIRED_OBSERVATIONS = 5
_RULE_REF_TARE = "OIML R 76-1:2006 §3.5.3.3; Annex A §A.4.6.1 (implemented subset)"


@dataclass(frozen=True)
class TareWeighingObservationResult:
    """One net-load observation under a fixed tare, with compliance snapshot."""

    net_load: float
    gross_load: float
    compliance: ObservationComplianceResult


@dataclass(frozen=True)
class TareWeighingSeriesResult:
    """Immutable subtractive-tare series result."""

    standard_code: str
    standard_edition: str
    ruleset_version: str
    rule_reference: str
    accuracy_class: AccuracyClass
    maximum_capacity: float
    minimum_capacity: float
    verification_scale_interval: float
    actual_scale_interval: float
    unit: MassUnit
    tare_value: float
    required_observations: int
    observation_count: int
    observations: Tuple[TareWeighingObservationResult, ...]
    failed_observation_indices: Tuple[int, ...]
    complete: bool
    status: TareWeighingStatus


def _observation_mapping(item: object, index: int) -> Mapping[str, object]:
    if not isinstance(item, Mapping):
        raise ValueError(f"observations[{index}] must be a mapping")
    return item


def _net_load_from(item: Mapping[str, object], index: int) -> float:
    if "net_load" in item and item["net_load"] not in (None, ""):
        return _require_finite_number(item["net_load"], f"observations[{index}].net_load")
    if "applied_load" in item and item["applied_load"] not in (None, ""):
        return _require_finite_number(
            item["applied_load"], f"observations[{index}].applied_load"
        )
    raise ValueError(f"observations[{index}] must include net_load or applied_load")


def evaluate_tare_weighing_series(
    accuracy_class: object,
    maximum_capacity: object,
    minimum_capacity: object,
    e: object,
    d: object,
    unit: object,
    tare_value: object,
    observations: object,
) -> TareWeighingSeriesResult:
    """Evaluate a subtractive-tare series of net-load digital observations.

    Gross load = tare_value + net_load must be <= Max.
    PASS iff at least 5 observations and every Ec is within initial MPE.
    """
    cls = _require_accuracy_class(accuracy_class)
    if unit not in SUPPORTED_MASS_UNITS:
        raise ValueError(f"unit must be one of g, kg, t; got {unit!r}")
    max_value = _require_finite_number(maximum_capacity, "maximum_capacity")
    min_value = _require_finite_number(minimum_capacity, "minimum_capacity")
    e_value = _require_finite_number(e, "e")
    d_value = _require_finite_number(d, "d")
    tare = _require_finite_number(tare_value, "tare_value")
    if max_value <= 0:
        raise ValueError("maximum_capacity must be > 0")
    if min_value < 0:
        raise ValueError("minimum_capacity must be >= 0")
    if e_value <= 0:
        raise ValueError("e must be > 0")
    if d_value <= 0:
        raise ValueError("d must be > 0")
    if tare < 0:
        raise ValueError("tare_value must be >= 0")
    if tare > max_value:
        raise ValueError("tare_value must be <= maximum_capacity")
    if not isinstance(observations, Sequence) or isinstance(observations, (str, bytes)):
        raise ValueError("observations must be a sequence of mappings")

    parsed: list[TareWeighingObservationResult] = []
    failed: list[int] = []
    for i, raw in enumerate(observations):
        item = _observation_mapping(raw, i)
        net = _net_load_from(item, i)
        if net < 0:
            raise ValueError(f"observations[{i}] net load must be >= 0")
        gross = tare + net
        if gross > max_value:
            raise ValueError(
                f"observations[{i}] gross load (tare + net) must be <= maximum_capacity"
            )
        if "reference_value" in item and item["reference_value"] not in (None, ""):
            load = _require_finite_number(
                item["reference_value"], f"observations[{i}].reference_value"
            )
        else:
            load = net
        indication = _require_finite_number(
            item["indication"], f"observations[{i}].indication"
        )
        zero_error = _require_finite_number(
            item["zero_error"], f"observations[{i}].zero_error"
        )
        extra = item.get("additional_load")
        if extra in (None, ""):
            additional_load = None
        else:
            additional_load = _require_finite_number(
                extra, f"observations[{i}].additional_load"
            )
        compliance = evaluate_digital_observation(
            accuracy_class=cls,
            load=load,
            indication=indication,
            e=e_value,
            d=d_value,
            zero_error=zero_error,
            stage="initial",
            additional_load=additional_load,
        )
        parsed.append(
            TareWeighingObservationResult(
                net_load=net,
                gross_load=gross,
                compliance=compliance,
            )
        )
        if compliance.result == "FAIL":
            failed.append(i)

    count = len(parsed)
    complete = count >= _REQUIRED_OBSERVATIONS
    if failed:
        status: TareWeighingStatus = "FAIL"
    elif not complete:
        status = "INCOMPLETE"
    else:
        status = "PASS"

    typed_unit: MassUnit = unit  # type: ignore[assignment]
    return TareWeighingSeriesResult(
        standard_code=STANDARD_CODE,
        standard_edition=STANDARD_EDITION,
        ruleset_version=RULESET_VERSION,
        rule_reference=_RULE_REF_TARE,
        accuracy_class=cls,
        maximum_capacity=max_value,
        minimum_capacity=min_value,
        verification_scale_interval=e_value,
        actual_scale_interval=d_value,
        unit=typed_unit,
        tare_value=tare,
        required_observations=_REQUIRED_OBSERVATIONS,
        observation_count=count,
        observations=tuple(parsed),
        failed_observation_indices=tuple(failed),
        complete=complete,
        status=status,
    )
