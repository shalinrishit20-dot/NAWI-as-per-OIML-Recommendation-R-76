"""Isolated OIML R 76 rules package.

This package is independent of Flask, SQLAlchemy, and report generation.
"""

from .oiml_r76 import (
    STANDARD_CODE,
    STANDARD_EDITION,
    RULESET_VERSION,
    AccuracyClass,
    MassUnit,
    MpeResult,
    ClassificationResult,
    verification_intervals,
    initial_verification_mpe_multiplier,
    initial_verification_mpe,
    in_service_mpe,
    calculate_mpe,
    to_grams,
    validate_single_range_classification,
)
from .error_determination import (
    ErrorDeterminationResult,
    requires_rounding_elimination,
    indication_before_rounding,
    error_before_rounding,
    corrected_error,
    calculate_digital_error,
)
from .compliance import (
    ObservationComplianceResult,
    evaluate_digital_observation,
)
from .repeatability import (
    RepeatabilitySeriesResult,
    evaluate_type_approval_repeatability_series,
)
from .eccentricity import (
    EccentricityResult,
    evaluate_quarter_segment_eccentricity,
)
from .test_programme import (
    CoreTestProgrammeResult,
    evaluate_core_test_programme,
)
from .zero_setting import (
    ZeroSettingResult,
    evaluate_zero_setting_accuracy,
)
from .tare_weighing import (
    TareWeighingSeriesResult,
    evaluate_tare_weighing_series,
)

__all__ = [
    "STANDARD_CODE",
    "STANDARD_EDITION",
    "RULESET_VERSION",
    "AccuracyClass",
    "MassUnit",
    "MpeResult",
    "ClassificationResult",
    "verification_intervals",
    "initial_verification_mpe_multiplier",
    "initial_verification_mpe",
    "in_service_mpe",
    "calculate_mpe",
    "to_grams",
    "validate_single_range_classification",
    "ErrorDeterminationResult",
    "requires_rounding_elimination",
    "indication_before_rounding",
    "error_before_rounding",
    "corrected_error",
    "calculate_digital_error",
    "ObservationComplianceResult",
    "evaluate_digital_observation",
    "RepeatabilitySeriesResult",
    "evaluate_type_approval_repeatability_series",
    "EccentricityResult",
    "evaluate_quarter_segment_eccentricity",
    "CoreTestProgrammeResult",
    "evaluate_core_test_programme",
    "ZeroSettingResult",
    "evaluate_zero_setting_accuracy",
]
