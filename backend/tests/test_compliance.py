"""unittest coverage for digital-observation Ec vs MPE composition."""

from __future__ import annotations

import os
import sys
import unittest

BACKEND_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if BACKEND_ROOT not in sys.path:
    sys.path.insert(0, BACKEND_ROOT)

from rules.compliance import ObservationComplianceResult, evaluate_digital_observation
from rules.error_determination import calculate_digital_error
from rules.oiml_r76 import calculate_mpe


class DirectPathComplianceTests(unittest.TestCase):
    def test_direct_pass(self) -> None:
        # Class III, m = 1000e → MPE = 1.0 e = 5; d = 0.5 <= 0.2e
        r = evaluate_digital_observation(
            "III", 5000.0, 5000.5, 5.0, 0.5, 0.2
        )
        self.assertEqual(r.error_method, "direct")
        self.assertEqual(r.result, "PASS")
        self.assertEqual(r.corrected_error, 0.3)
        self.assertEqual(r.absolute_corrected_error, 0.3)
        self.assertEqual(r.mpe, 5.0)
        self.assertEqual(r.margin_to_limit, 4.7)
        self.assertGreater(r.margin_to_limit, 0)

    def test_direct_fail(self) -> None:
        r = evaluate_digital_observation(
            "III", 5000.0, 5010.0, 5.0, 0.5, 0.0
        )
        self.assertEqual(r.error_method, "direct")
        self.assertEqual(r.result, "FAIL")
        self.assertEqual(r.corrected_error, 10.0)
        self.assertLess(r.margin_to_limit, 0)


class BoundaryEqualityTests(unittest.TestCase):
    def test_plus_mpe_is_pass(self) -> None:
        r = evaluate_digital_observation(
            "III", 5000.0, 5005.0, 5.0, 0.5, 0.0
        )
        self.assertEqual(r.corrected_error, 5.0)
        self.assertEqual(r.mpe, 5.0)
        self.assertEqual(r.margin_to_limit, 0.0)
        self.assertEqual(r.result, "PASS")

    def test_minus_mpe_is_pass(self) -> None:
        r = evaluate_digital_observation(
            "III", 5000.0, 4995.0, 5.0, 0.5, 0.0
        )
        self.assertEqual(r.corrected_error, -5.0)
        self.assertEqual(r.result, "PASS")
        self.assertEqual(r.margin_to_limit, 0.0)

    def test_just_above_plus_mpe_is_fail(self) -> None:
        r = evaluate_digital_observation(
            "III", 5000.0, 5005.000001, 5.0, 0.5, 0.0
        )
        self.assertEqual(r.result, "FAIL")
        self.assertLess(r.margin_to_limit, 0)

    def test_just_below_minus_mpe_is_fail(self) -> None:
        r = evaluate_digital_observation(
            "III", 5000.0, 4994.999999, 5.0, 0.5, 0.0
        )
        self.assertEqual(r.result, "FAIL")
        self.assertLess(r.margin_to_limit, 0)


class ChangeoverComplianceTests(unittest.TestCase):
    def test_annex_a_values_from_error_engine(self) -> None:
        r = evaluate_digital_observation(
            "III",
            1000.0,
            1000.0,
            5.0,
            5.0,
            0.5,
            additional_load=1.5,
        )
        engine = calculate_digital_error(
            1000.0, 1000.0, 5.0, 5.0, 0.5, additional_load=1.5
        )
        self.assertEqual(r.indication_before_rounding, engine.indication_before_rounding)
        self.assertEqual(r.error_before_rounding, engine.error_before_rounding)
        self.assertEqual(r.corrected_error, engine.corrected_error)
        self.assertEqual(r.indication_before_rounding, 1001.0)
        self.assertEqual(r.error_before_rounding, 1.0)
        self.assertEqual(r.corrected_error, 0.5)
        self.assertEqual(r.error_method, "changeover_point")
        self.assertEqual(r.result, "PASS")


class StageDelegationTests(unittest.TestCase):
    def test_fails_initial_passes_in_service(self) -> None:
        kwargs = dict(
            accuracy_class="III",
            load=5000.0,
            indication=5007.5,
            e=5.0,
            d=0.5,
            zero_error=0.0,
        )
        initial = evaluate_digital_observation(**kwargs, stage="initial")
        service = evaluate_digital_observation(**kwargs, stage="in_service")
        self.assertEqual(initial.corrected_error, 7.5)
        self.assertEqual(initial.mpe, 5.0)
        self.assertEqual(initial.result, "FAIL")
        self.assertEqual(service.mpe, 10.0)
        self.assertEqual(service.mpe, 2.0 * initial.mpe)
        self.assertEqual(service.result, "PASS")
        self.assertEqual(
            service.mpe_rule_reference, "OIML R 76-1:2006 §3.5.1 Table 6; §3.5.2"
        )
        self.assertEqual(
            initial.mpe_rule_reference, "OIML R 76-1:2006 §3.5.1 Table 6"
        )


class NegativeErrorComplianceTests(unittest.TestCase):
    def test_negative_inside_limit(self) -> None:
        r = evaluate_digital_observation(
            "III", 5000.0, 4998.0, 5.0, 0.5, 0.0
        )
        self.assertEqual(r.corrected_error, -2.0)
        self.assertEqual(r.result, "PASS")

    def test_negative_outside_limit(self) -> None:
        r = evaluate_digital_observation(
            "III", 5000.0, 4990.0, 5.0, 0.5, 0.0
        )
        self.assertEqual(r.corrected_error, -10.0)
        self.assertEqual(r.result, "FAIL")


class ResultConsistencyTests(unittest.TestCase):
    def test_matches_underlying_engines(self) -> None:
        r = evaluate_digital_observation(
            "III", 5000.0, 5000.5, 5.0, 0.5, 0.2, stage="initial"
        )
        err = calculate_digital_error(5000.0, 5000.5, 5.0, 0.5, 0.2)
        mpe = calculate_mpe("III", 5000.0, 5.0, stage="initial")
        self.assertEqual(r.corrected_error, err.corrected_error)
        self.assertEqual(r.mpe, mpe.mpe)
        self.assertEqual(r.mpe_multiplier, mpe.multiplier)
        self.assertEqual(r.standard_code, err.standard_code)
        self.assertEqual(r.standard_edition, err.standard_edition)
        self.assertEqual(r.ruleset_version, err.ruleset_version)
        self.assertEqual(r.error_rule_reference, err.rule_reference)
        self.assertEqual(r.mpe_rule_reference, mpe.rule_reference)
        self.assertIsInstance(r, ObservationComplianceResult)
        with self.assertRaises(Exception):
            r.result = "FAIL"  # type: ignore[misc]


class InputPropagationTests(unittest.TestCase):
    def test_invalid_class(self) -> None:
        with self.assertRaises(ValueError):
            evaluate_digital_observation("IV", 100.0, 100.0, 1.0, 0.1, 0.0)

    def test_negative_load(self) -> None:
        with self.assertRaises(ValueError):
            evaluate_digital_observation("III", -1.0, 1.0, 1.0, 0.1, 0.0)

    def test_non_positive_e_d(self) -> None:
        with self.assertRaises(ValueError):
            evaluate_digital_observation("III", 100.0, 100.0, 0.0, 0.1, 0.0)
        with self.assertRaises(ValueError):
            evaluate_digital_observation("III", 100.0, 100.0, 1.0, 0.0, 0.0)

    def test_nan_and_inf(self) -> None:
        with self.assertRaises(ValueError):
            evaluate_digital_observation("III", float("nan"), 1.0, 1.0, 0.1, 0.0)
        with self.assertRaises(ValueError):
            evaluate_digital_observation("III", 1.0, float("inf"), 1.0, 0.1, 0.0)

    def test_additional_load_path_rules(self) -> None:
        with self.assertRaises(ValueError):
            evaluate_digital_observation("III", 1000.0, 1000.0, 5.0, 5.0, 0.0)
        with self.assertRaises(ValueError):
            evaluate_digital_observation(
                "III", 1000.0, 1000.0, 5.0, 0.5, 0.0, additional_load=0.1
            )

    def test_unsupported_table_6_range(self) -> None:
        with self.assertRaises(ValueError):
            evaluate_digital_observation(
                "III", 10_001.0, 10_001.0, 1.0, 0.1, 0.0
            )


if __name__ == "__main__":
    unittest.main()
