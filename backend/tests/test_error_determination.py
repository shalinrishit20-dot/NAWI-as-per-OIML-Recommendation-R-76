"""unittest coverage for §3.5.3.2 / Annex A §A.4.4.3 error determination."""

from __future__ import annotations

import math
import os
import sys
import unittest

BACKEND_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if BACKEND_ROOT not in sys.path:
    sys.path.insert(0, BACKEND_ROOT)

from rules.error_determination import (
    ErrorDeterminationResult,
    calculate_digital_error,
    corrected_error,
    error_before_rounding,
    indication_before_rounding,
    requires_rounding_elimination,
)
from rules.oiml_r76 import RULESET_VERSION, STANDARD_CODE, STANDARD_EDITION


class RoundingEliminationDecisionTests(unittest.TestCase):
    def test_boundary_equal_is_false(self) -> None:
        self.assertFalse(requires_rounding_elimination(5.0, 1.0))

    def test_just_above_threshold_is_true(self) -> None:
        self.assertTrue(requires_rounding_elimination(5.0, 1.000001))

    def test_below_threshold_is_false(self) -> None:
        self.assertFalse(requires_rounding_elimination(5.0, 0.5))

    def test_d_equals_e_is_true(self) -> None:
        self.assertTrue(requires_rounding_elimination(5.0, 5.0))

    def test_malformed_e_and_d(self) -> None:
        for bad in (0.0, -1.0, float("nan"), float("inf"), float("-inf")):
            with self.assertRaises(ValueError):
                requires_rounding_elimination(bad, 1.0)
            with self.assertRaises(ValueError):
                requires_rounding_elimination(1.0, bad)
        with self.assertRaises(ValueError):
            requires_rounding_elimination(True, 1.0)  # type: ignore[arg-type]


class AnnexAWorkedExampleTests(unittest.TestCase):
    """OIML R 76-1:2006 Annex A §A.4.4.3 official numerical example."""

    def test_intermediate_and_high_level(self) -> None:
        p = indication_before_rounding(1000.0, 5.0, 1.5)
        self.assertEqual(p, 1001.0)
        e = error_before_rounding(1000.0, 1000.0, 5.0, 1.5)
        self.assertEqual(e, 1.0)
        self.assertEqual(corrected_error(1.0, 0.5), 0.5)

        result = calculate_digital_error(
            load=1000.0,
            indication=1000.0,
            e=5.0,
            d=5.0,
            zero_error=0.5,
            additional_load=1.5,
        )
        self.assertEqual(result.indication_before_rounding, 1001.0)
        self.assertEqual(result.error_before_rounding, 1.0)
        self.assertEqual(result.corrected_error, 0.5)
        self.assertTrue(result.rounding_elimination_required)
        self.assertEqual(result.method, "changeover_point")
        self.assertEqual(result.additional_load, 1.5)
        self.assertEqual(result.rule_reference, "OIML R 76-1:2006 §3.5.3.2; Annex A §A.4.4.3")
        self.assertEqual(result.standard_code, STANDARD_CODE)
        self.assertEqual(result.standard_edition, STANDARD_EDITION)
        self.assertEqual(result.ruleset_version, RULESET_VERSION)


class DirectPathTests(unittest.TestCase):
    def test_fine_indication_used_directly(self) -> None:
        result = calculate_digital_error(
            load=1000.0,
            indication=1000.5,
            e=5.0,
            d=0.5,
            zero_error=0.2,
        )
        self.assertFalse(result.rounding_elimination_required)
        self.assertEqual(result.method, "direct")
        self.assertIsNone(result.additional_load)
        self.assertEqual(result.indication_before_rounding, 1000.5)
        self.assertEqual(result.error_before_rounding, 0.5)
        self.assertEqual(result.corrected_error, 0.3)


class PathSelectionValidationTests(unittest.TestCase):
    def test_changeover_requires_additional_load(self) -> None:
        with self.assertRaises(ValueError):
            calculate_digital_error(1000.0, 1000.0, 5.0, 5.0, 0.5)

    def test_direct_rejects_additional_load(self) -> None:
        with self.assertRaises(ValueError):
            calculate_digital_error(
                1000.0, 1000.5, 5.0, 0.5, 0.2, additional_load=0.1
            )


class NegativeErrorTests(unittest.TestCase):
    def test_negative_e_and_ec_allowed(self) -> None:
        result = calculate_digital_error(
            load=1000.0,
            indication=990.0,
            e=5.0,
            d=5.0,
            zero_error=-0.5,
            additional_load=1.5,
        )
        # P = 990 + 2.5 - 1.5 = 991; E = -9; Ec = -8.5
        self.assertEqual(result.indication_before_rounding, 991.0)
        self.assertEqual(result.error_before_rounding, -9.0)
        self.assertEqual(result.corrected_error, -8.5)


class MalformedInputTests(unittest.TestCase):
    def test_nan_and_infinity(self) -> None:
        for bad in (float("nan"), float("inf"), float("-inf")):
            with self.assertRaises(ValueError):
                calculate_digital_error(bad, 1.0, 1.0, 0.1, 0.0)
            with self.assertRaises(ValueError):
                calculate_digital_error(1.0, bad, 1.0, 0.1, 0.0)
            with self.assertRaises(ValueError):
                calculate_digital_error(1.0, 1.0, bad, 0.1, 0.0)
            with self.assertRaises(ValueError):
                calculate_digital_error(1.0, 1.0, 1.0, bad, 0.0)
            with self.assertRaises(ValueError):
                calculate_digital_error(1.0, 1.0, 1.0, 0.1, bad)
            with self.assertRaises(ValueError):
                indication_before_rounding(1.0, 1.0, bad)

    def test_non_positive_e_d_load_and_delta(self) -> None:
        with self.assertRaises(ValueError):
            calculate_digital_error(1.0, 1.0, 0.0, 0.1, 0.0)
        with self.assertRaises(ValueError):
            calculate_digital_error(1.0, 1.0, -1.0, 0.1, 0.0)
        with self.assertRaises(ValueError):
            calculate_digital_error(1.0, 1.0, 1.0, 0.0, 0.0)
        with self.assertRaises(ValueError):
            calculate_digital_error(1.0, 1.0, 1.0, -0.1, 0.0)
        with self.assertRaises(ValueError):
            calculate_digital_error(-1.0, 1.0, 1.0, 0.1, 0.0)
        with self.assertRaises(ValueError):
            indication_before_rounding(1000.0, 5.0, -0.1)
        with self.assertRaises(ValueError):
            calculate_digital_error(True, 1.0, 1.0, 0.1, 0.0)  # type: ignore[arg-type]


class ResultShapeTests(unittest.TestCase):
    def test_frozen_and_no_pass_fail(self) -> None:
        result = calculate_digital_error(1000.0, 1000.5, 5.0, 0.5, 0.2)
        self.assertIsInstance(result, ErrorDeterminationResult)
        self.assertFalse(hasattr(result, "pass_fail") or hasattr(result, "compliant"))
        with self.assertRaises(Exception):
            result.corrected_error = 0.0  # type: ignore[misc]


if __name__ == "__main__":
    unittest.main()
