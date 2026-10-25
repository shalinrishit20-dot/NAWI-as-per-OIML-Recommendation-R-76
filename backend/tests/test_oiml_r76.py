"""unittest coverage for OIML R 76-1:2006 Table 6 / §3.5.1 / §3.5.2 MPE rules."""

from __future__ import annotations

import math
import os
import sys
import unittest

BACKEND_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if BACKEND_ROOT not in sys.path:
    sys.path.insert(0, BACKEND_ROOT)

from rules.oiml_r76 import (
    RULESET_VERSION,
    STANDARD_CODE,
    STANDARD_EDITION,
    ClassificationResult,
    MpeResult,
    calculate_mpe,
    in_service_mpe,
    initial_verification_mpe,
    initial_verification_mpe_multiplier,
    to_grams,
    validate_single_range_classification,
    verification_intervals,
)


class VerificationIntervalsTests(unittest.TestCase):
    def test_m_equals_load_over_e(self) -> None:
        self.assertEqual(verification_intervals(10.0, 0.01), 1000.0)

    def test_zero_load_allowed(self) -> None:
        self.assertEqual(verification_intervals(0.0, 1.0), 0.0)

    def test_negative_load_rejected(self) -> None:
        with self.assertRaises(ValueError):
            verification_intervals(-1.0, 1.0)

    def test_zero_e_rejected(self) -> None:
        with self.assertRaises(ValueError):
            verification_intervals(1.0, 0.0)

    def test_negative_e_rejected(self) -> None:
        with self.assertRaises(ValueError):
            verification_intervals(1.0, -0.5)

    def test_nan_load_rejected(self) -> None:
        with self.assertRaises(ValueError):
            verification_intervals(float("nan"), 1.0)

    def test_nan_e_rejected(self) -> None:
        with self.assertRaises(ValueError):
            verification_intervals(1.0, float("nan"))

    def test_pos_inf_rejected(self) -> None:
        with self.assertRaises(ValueError):
            verification_intervals(float("inf"), 1.0)
        with self.assertRaises(ValueError):
            verification_intervals(1.0, float("inf"))

    def test_neg_inf_rejected(self) -> None:
        with self.assertRaises(ValueError):
            verification_intervals(float("-inf"), 1.0)
        with self.assertRaises(ValueError):
            verification_intervals(1.0, float("-inf"))


class InvalidAccuracyClassTests(unittest.TestCase):
    def test_arbitrary_class_rejected(self) -> None:
        with self.assertRaises(ValueError):
            initial_verification_mpe_multiplier("IV", 1.0, 1.0)
        with self.assertRaises(ValueError):
            initial_verification_mpe("iii", 1.0, 1.0)
        with self.assertRaises(ValueError):
            calculate_mpe("1", 1.0, 1.0)


class ClassITable6Tests(unittest.TestCase):
    """e = 1 so load == m."""

    def test_lower_band_and_boundaries(self) -> None:
        self.assertEqual(initial_verification_mpe_multiplier("I", 0.0, 1.0), 0.5)
        self.assertEqual(initial_verification_mpe_multiplier("I", 50_000.0, 1.0), 0.5)
        self.assertEqual(
            initial_verification_mpe_multiplier("I", 50_000.0001, 1.0), 1.0
        )

    def test_mid_band_and_boundaries(self) -> None:
        self.assertEqual(initial_verification_mpe_multiplier("I", 200_000.0, 1.0), 1.0)
        self.assertEqual(
            initial_verification_mpe_multiplier("I", 200_000.0001, 1.0), 1.5
        )

    def test_no_upper_bound_for_1_5_e_band(self) -> None:
        self.assertEqual(initial_verification_mpe_multiplier("I", 1_000_000.0, 1.0), 1.5)
        self.assertEqual(initial_verification_mpe("I", 1_000_000.0, 1.0), 1.5)


class ClassIITable6Tests(unittest.TestCase):
    def test_boundaries(self) -> None:
        self.assertEqual(initial_verification_mpe_multiplier("II", 0.0, 1.0), 0.5)
        self.assertEqual(initial_verification_mpe_multiplier("II", 5_000.0, 1.0), 0.5)
        self.assertEqual(
            initial_verification_mpe_multiplier("II", 5_000.0001, 1.0), 1.0
        )
        self.assertEqual(initial_verification_mpe_multiplier("II", 20_000.0, 1.0), 1.0)
        self.assertEqual(
            initial_verification_mpe_multiplier("II", 20_000.0001, 1.0), 1.5
        )
        self.assertEqual(initial_verification_mpe_multiplier("II", 100_000.0, 1.0), 1.5)

    def test_above_100000e_unsupported(self) -> None:
        with self.assertRaises(ValueError) as ctx:
            initial_verification_mpe_multiplier("II", 100_000.0001, 1.0)
        self.assertIn("Table 6", str(ctx.exception))


class ClassIIITable6Tests(unittest.TestCase):
    def test_boundaries(self) -> None:
        self.assertEqual(initial_verification_mpe_multiplier("III", 0.0, 1.0), 0.5)
        self.assertEqual(initial_verification_mpe_multiplier("III", 500.0, 1.0), 0.5)
        self.assertEqual(
            initial_verification_mpe_multiplier("III", 500.0001, 1.0), 1.0
        )
        self.assertEqual(initial_verification_mpe_multiplier("III", 2_000.0, 1.0), 1.0)
        self.assertEqual(
            initial_verification_mpe_multiplier("III", 2_000.0001, 1.0), 1.5
        )
        self.assertEqual(initial_verification_mpe_multiplier("III", 10_000.0, 1.0), 1.5)

    def test_above_10000e_unsupported(self) -> None:
        with self.assertRaises(ValueError):
            initial_verification_mpe_multiplier("III", 10_000.0001, 1.0)

    def test_worked_example_10kg_e_0_01(self) -> None:
        # m = 10 / 0.01 = 1000 e -> Class III multiplier 1.0 -> MPE = 0.01 kg
        self.assertEqual(initial_verification_mpe("III", 10.0, 0.01), 0.01)


class ClassIIIITable6Tests(unittest.TestCase):
    def test_boundaries(self) -> None:
        self.assertEqual(initial_verification_mpe_multiplier("IIII", 0.0, 1.0), 0.5)
        self.assertEqual(initial_verification_mpe_multiplier("IIII", 50.0, 1.0), 0.5)
        self.assertEqual(
            initial_verification_mpe_multiplier("IIII", 50.0001, 1.0), 1.0
        )
        self.assertEqual(initial_verification_mpe_multiplier("IIII", 200.0, 1.0), 1.0)
        self.assertEqual(
            initial_verification_mpe_multiplier("IIII", 200.0001, 1.0), 1.5
        )
        self.assertEqual(initial_verification_mpe_multiplier("IIII", 1000.0, 1.0), 1.5)

    def test_above_1000e_unsupported(self) -> None:
        with self.assertRaises(ValueError):
            initial_verification_mpe_multiplier("IIII", 1000.0001, 1.0)


class AbsoluteMpeAndInServiceTests(unittest.TestCase):
    def test_initial_mpe_is_multiplier_times_e(self) -> None:
        self.assertEqual(initial_verification_mpe("III", 500.0, 2.0), 1.0)  # 0.5 * 2
        self.assertEqual(initial_verification_mpe("III", 2000.0, 2.0), 2.0)  # 1.0 * 2
        self.assertEqual(initial_verification_mpe("III", 4000.2, 2.0), 3.0)  # m=2000.1 -> 1.5 * 2

    def test_in_service_is_exactly_double(self) -> None:
        for cls, load, e in (
            ("I", 50_000.0, 1.0),
            ("II", 20_000.0, 0.5),
            ("III", 10.0, 0.01),
            ("IIII", 50.0, 0.1),
        ):
            initial = initial_verification_mpe(cls, load, e)
            self.assertEqual(in_service_mpe(cls, load, e), 2.0 * initial)


class CalculateMpeResultTests(unittest.TestCase):
    def test_initial_metadata_and_rule_reference(self) -> None:
        result = calculate_mpe("III", 10.0, 0.01, stage="initial")
        self.assertIsInstance(result, MpeResult)
        self.assertEqual(result.standard_code, STANDARD_CODE)
        self.assertEqual(result.standard_edition, STANDARD_EDITION)
        self.assertEqual(result.ruleset_version, RULESET_VERSION)
        self.assertEqual(result.rule_reference, "OIML R 76-1:2006 §3.5.1 Table 6")
        self.assertEqual(result.accuracy_class, "III")
        self.assertEqual(result.load, 10.0)
        self.assertEqual(result.verification_scale_interval, 0.01)
        self.assertEqual(result.load_in_verification_intervals, 1000.0)
        self.assertEqual(result.multiplier, 1.0)
        self.assertEqual(result.mpe, 0.01)
        self.assertEqual(result.verification_stage, "initial")

    def test_in_service_metadata_and_doubling(self) -> None:
        result = calculate_mpe("III", 10.0, 0.01, stage="in_service")
        self.assertEqual(
            result.rule_reference, "OIML R 76-1:2006 §3.5.1 Table 6; §3.5.2"
        )
        self.assertEqual(result.verification_stage, "in_service")
        self.assertEqual(result.multiplier, 2.0)
        self.assertEqual(result.mpe, 0.02)

    def test_class_iii_load_1000_e_1_effective_multipliers(self) -> None:
        initial = calculate_mpe("III", 1000.0, 1.0, stage="initial")
        self.assertEqual(initial.multiplier, 1.0)
        self.assertEqual(initial.mpe, 1.0)
        in_service = calculate_mpe("III", 1000.0, 1.0, stage="in_service")
        self.assertEqual(in_service.multiplier, 2.0)
        self.assertEqual(in_service.mpe, 2.0)
        self.assertEqual(
            initial_verification_mpe_multiplier("III", 1000.0, 1.0), 1.0
        )

    def test_result_is_frozen(self) -> None:
        result = calculate_mpe("I", 1.0, 1.0)
        with self.assertRaises(Exception):
            result.mpe = 99.0  # type: ignore[misc]

    def test_invalid_stage(self) -> None:
        with self.assertRaises(ValueError):
            calculate_mpe("I", 1.0, 1.0, stage="periodic")  # type: ignore[arg-type]

    def test_nan_rejected_at_calculate(self) -> None:
        with self.assertRaises(ValueError):
            calculate_mpe("I", math.nan, 1.0)

    def test_ruleset_is_versioned_not_latest(self) -> None:
        self.assertNotEqual(RULESET_VERSION.lower(), "latest")
        self.assertEqual(STANDARD_CODE, "OIML R 76-1")
        self.assertEqual(STANDARD_EDITION, "2006")
        self.assertEqual(RULESET_VERSION, "R76-1-2006-v1")


def _classify(cls, max_c, min_c, e, unit="g", d=None):
    actual = e if d is None else d
    return validate_single_range_classification(cls, max_c, min_c, e, actual, unit)


class ToGramsTests(unittest.TestCase):
    def test_supported_conversions(self) -> None:
        self.assertEqual(to_grams(1.0, "g"), 1.0)
        self.assertEqual(to_grams(1.0, "kg"), 1000.0)
        self.assertEqual(to_grams(1.0, "t"), 1_000_000.0)

    def test_unsupported_unit(self) -> None:
        with self.assertRaises(ValueError):
            to_grams(1.0, "lb")


class ClassificationMalformedInputTests(unittest.TestCase):
    def test_unsupported_class(self) -> None:
        with self.assertRaises(ValueError):
            _classify("IV", 1000.0, 20.0, 1.0)

    def test_unsupported_unit(self) -> None:
        with self.assertRaises(ValueError):
            _classify("III", 1000.0, 20.0, 1.0, "mg")

    def test_max_zero_and_negative(self) -> None:
        with self.assertRaises(ValueError):
            _classify("III", 0.0, 0.0, 1.0)
        with self.assertRaises(ValueError):
            _classify("III", -10.0, 1.0, 1.0)

    def test_min_negative(self) -> None:
        with self.assertRaises(ValueError):
            _classify("III", 1000.0, -1.0, 1.0)

    def test_min_not_less_than_max(self) -> None:
        with self.assertRaises(ValueError):
            _classify("III", 100.0, 100.0, 1.0)
        with self.assertRaises(ValueError):
            _classify("III", 100.0, 101.0, 1.0)

    def test_e_zero_and_negative(self) -> None:
        with self.assertRaises(ValueError):
            _classify("III", 1000.0, 20.0, 0.0)
        with self.assertRaises(ValueError):
            _classify("III", 1000.0, 20.0, -1.0)

    def test_nan_and_infinity(self) -> None:
        with self.assertRaises(ValueError):
            _classify("III", float("nan"), 20.0, 1.0)
        with self.assertRaises(ValueError):
            _classify("III", 1000.0, float("inf"), 1.0)
        with self.assertRaises(ValueError):
            _classify("III", 1000.0, 20.0, float("-inf"))

    def test_malformed_d(self) -> None:
        with self.assertRaises(ValueError):
            _classify("III", 1000.0, 20.0, 1.0, d=0.0)
        with self.assertRaises(ValueError):
            _classify("III", 1000.0, 20.0, 1.0, d=-1.0)
        with self.assertRaises(ValueError):
            _classify("III", 1000.0, 20.0, 1.0, d=float("nan"))
        with self.assertRaises(ValueError):
            _classify("III", 1000.0, 20.0, 1.0, d=float("inf"))
        with self.assertRaises(ValueError):
            _classify("III", 1000.0, 20.0, 1.0, d=float("-inf"))


class ClassITable3Tests(unittest.TestCase):
    def test_exact_valid_boundary(self) -> None:
        r = _classify("I", 50.0, 0.1, 0.001)
        self.assertTrue(r.valid)
        self.assertEqual(r.errors, ())
        self.assertEqual(r.number_of_verification_intervals, 50_000.0)
        self.assertEqual(r.minimum_n, 50_000.0)
        self.assertIsNone(r.maximum_n)
        self.assertEqual(r.minimum_capacity_in_d, 100.0)
        self.assertEqual(r.minimum_capacity_multiplier, 100.0)
        self.assertEqual(r.rule_reference, "OIML R 76-1:2006 §3.2 Table 3; §3.4.3")

    def test_n_below_50000_invalid(self) -> None:
        r = _classify("I", 49.999, 0.1, 0.001)
        self.assertFalse(r.valid)
        self.assertTrue(any("50000" in e and "n =" in e for e in r.errors))

    def test_e_below_0_001_g_invalid(self) -> None:
        r = _classify("I", 50.0, 0.08, 0.0008)
        self.assertFalse(r.valid)
        self.assertTrue(any("0.001 g" in e for e in r.errors))

    def test_min_below_100d_invalid(self) -> None:
        r = _classify("I", 50.0, 0.099, 0.001)
        self.assertFalse(r.valid)
        self.assertTrue(any("100 d" in e for e in r.errors))

    def test_very_large_n_valid(self) -> None:
        r = _classify("I", 1_000_000.0, 0.1, 0.001)
        self.assertTrue(r.valid)
        self.assertEqual(r.number_of_verification_intervals, 1_000_000_000.0)


class ClassIITable3Tests(unittest.TestCase):
    def test_band_a_e_and_n_boundaries(self) -> None:
        self.assertTrue(_classify("II", 0.1, 0.02, 0.001).valid)
        self.assertTrue(_classify("II", 100.0, 1.0, 0.001).valid)
        self.assertTrue(_classify("II", 5.0, 1.0, 0.05).valid)
        self.assertTrue(_classify("II", 5000.0, 1.0, 0.05).valid)

    def test_band_a_n_and_min_failures(self) -> None:
        r = _classify("II", 0.099, 0.02, 0.001)
        self.assertFalse(r.valid)
        r = _classify("II", 100.001, 1.0, 0.001)
        self.assertFalse(r.valid)
        r = _classify("II", 1.0, 0.019, 0.001)
        self.assertFalse(r.valid)
        self.assertTrue(any("20 d" in e for e in r.errors))

    def test_band_b_boundaries(self) -> None:
        self.assertTrue(_classify("II", 500.0, 5.0, 0.1).valid)
        self.assertTrue(_classify("II", 10_000.0, 5.0, 0.1).valid)

    def test_band_b_failures(self) -> None:
        r = _classify("II", 499.9, 5.0, 0.1)
        self.assertFalse(r.valid)
        r = _classify("II", 1000.0, 4.9, 0.1)
        self.assertFalse(r.valid)
        self.assertTrue(any("50 d" in e for e in r.errors))

    def test_gap_e_075_g(self) -> None:
        r = _classify("II", 7.5, 1.5, 0.075)
        self.assertFalse(r.valid)
        self.assertTrue(any("0.075 g" in e and "Table 3" in e for e in r.errors))


class ClassIIITable3Tests(unittest.TestCase):
    def test_band_a_boundaries(self) -> None:
        self.assertTrue(_classify("III", 10.0, 2.0, 0.1).valid)
        self.assertTrue(_classify("III", 1000.0, 2.0, 0.1).valid)
        self.assertTrue(_classify("III", 200.0, 40.0, 2.0).valid)
        self.assertTrue(_classify("III", 20_000.0, 40.0, 2.0).valid)

    def test_band_b_boundaries(self) -> None:
        self.assertTrue(_classify("III", 2500.0, 100.0, 5.0).valid)
        self.assertTrue(_classify("III", 50_000.0, 100.0, 5.0).valid)

    def test_gap_e_3_g(self) -> None:
        r = _classify("III", 300.0, 60.0, 3.0)
        self.assertFalse(r.valid)
        self.assertTrue(any("3 g" in e and "Table 3" in e for e in r.errors))

    def test_n_50_is_compliance_failure_not_exception(self) -> None:
        r = _classify("III", 5.0, 2.0, 0.1)
        self.assertFalse(r.valid)
        self.assertTrue(any("100" in e and "n = 50" in e for e in r.errors))


class ClassIIIITable3Tests(unittest.TestCase):
    def test_boundaries(self) -> None:
        self.assertTrue(_classify("IIII", 500.0, 50.0, 5.0).valid)
        self.assertTrue(_classify("IIII", 5000.0, 50.0, 5.0).valid)

    def test_failures(self) -> None:
        r = _classify("IIII", 400.0, 40.0, 4.0)
        self.assertFalse(r.valid)
        self.assertTrue(any("5 g" in e for e in r.errors))
        r = _classify("IIII", 495.0, 50.0, 5.0)
        self.assertFalse(r.valid)
        r = _classify("IIII", 5005.0, 50.0, 5.0)
        self.assertFalse(r.valid)
        r = _classify("IIII", 1000.0, 49.0, 5.0)
        self.assertFalse(r.valid)
        self.assertTrue(any("10 d" in e for e in r.errors))


class ClassificationUnitEquivalenceTests(unittest.TestCase):
    def test_class_iii_kg_equals_g(self) -> None:
        as_kg = validate_single_range_classification(
            "III", 100.0, 0.2, 0.01, 0.01, "kg"
        )
        as_g = validate_single_range_classification(
            "III", 100_000.0, 200.0, 10.0, 10.0, "g"
        )
        self.assertTrue(as_kg.valid)
        self.assertTrue(as_g.valid)
        self.assertEqual(as_kg.verification_scale_interval_g, as_g.verification_scale_interval_g)
        self.assertEqual(as_kg.number_of_verification_intervals, as_g.number_of_verification_intervals)
        self.assertEqual(as_kg.max_capacity_g, as_g.max_capacity_g)

    def test_tonne_conversion(self) -> None:
        r = validate_single_range_classification(
            "IIII", 5.0, 0.05, 0.005, 0.005, "t"
        )
        self.assertEqual(r.verification_scale_interval_g, 5000.0)
        self.assertEqual(r.number_of_verification_intervals, 1000.0)
        self.assertTrue(r.valid)

    def test_result_is_frozen_and_errors_tuple(self) -> None:
        r = _classify("III", 5.0, 2.0, 0.1)
        self.assertIsInstance(r, ClassificationResult)
        self.assertIsInstance(r.errors, tuple)
        with self.assertRaises(Exception):
            r.valid = True  # type: ignore[misc]


class Section343MinUsesDTests(unittest.TestCase):
    """Min is compared with multiplier × d (§3.4.3), while n uses Max/e."""

    def test_min_equals_20d_valid(self) -> None:
        r = validate_single_range_classification(
            "III", 30.0, 0.10, 0.01, 0.005, "kg"
        )
        self.assertTrue(r.valid)
        self.assertEqual(r.number_of_verification_intervals, 3000.0)
        self.assertEqual(r.verification_scale_interval_g, 10.0)
        self.assertEqual(r.actual_scale_interval_g, 5.0)
        self.assertEqual(r.minimum_capacity_in_d, 20.0)
        self.assertEqual(r.minimum_capacity_required, 0.10)

    def test_min_below_20d_invalid(self) -> None:
        r = validate_single_range_classification(
            "III", 30.0, 0.099, 0.01, 0.005, "kg"
        )
        self.assertFalse(r.valid)
        self.assertTrue(any("20 d" in e for e in r.errors))

    def test_min_fails_20e_but_passes_20d(self) -> None:
        r = validate_single_range_classification(
            "III", 30.0, 0.15, 0.01, 0.005, "kg"
        )
        self.assertTrue(r.valid)
        self.assertLess(r.min_capacity, 20.0 * r.verification_scale_interval)
        self.assertGreaterEqual(r.min_capacity, 20.0 * r.actual_scale_interval)


if __name__ == "__main__":
    unittest.main()
