"""Zero-setting accuracy (§4.5.2 / A.4.2.3) rule tests."""

from __future__ import annotations

import math
import os
import sys
import unittest

BACKEND_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if BACKEND_ROOT not in sys.path:
    sys.path.insert(0, BACKEND_ROOT)

from rules.error_determination import indication_before_rounding
from rules.oiml_r76 import RULESET_VERSION, STANDARD_CODE, STANDARD_EDITION
from rules.zero_setting import ZeroSettingResult, evaluate_zero_setting_accuracy


class ZeroSettingPassFailTests(unittest.TestCase):
    def test_zero_deviation_is_pass(self) -> None:
        r = evaluate_zero_setting_accuracy(0.0, 1.0, 0.1, "kg")
        self.assertEqual(r.status, "PASS")
        self.assertEqual(r.zero_error, 0.0)
        self.assertEqual(r.error_method, "direct")

    def test_plus_quarter_e_is_pass(self) -> None:
        r = evaluate_zero_setting_accuracy(0.25, 1.0, 0.1, "kg")
        self.assertEqual(r.status, "PASS")
        self.assertEqual(r.zero_error, 0.25)
        self.assertEqual(r.permitted_limit, 0.25)

    def test_minus_quarter_e_is_pass(self) -> None:
        r = evaluate_zero_setting_accuracy(-0.25, 1.0, 0.1, "kg")
        self.assertEqual(r.status, "PASS")
        self.assertEqual(r.zero_error, -0.25)

    def test_just_above_plus_quarter_e_is_fail(self) -> None:
        r = evaluate_zero_setting_accuracy(0.2500001, 1.0, 0.1, "kg")
        self.assertEqual(r.status, "FAIL")

    def test_just_below_minus_quarter_e_is_fail(self) -> None:
        r = evaluate_zero_setting_accuracy(-0.2500001, 1.0, 0.1, "kg")
        self.assertEqual(r.status, "FAIL")

    def test_margin_to_limit(self) -> None:
        r = evaluate_zero_setting_accuracy(0.10, 1.0, 0.1, "kg")
        self.assertAlmostEqual(r.margin_to_limit, 0.15)
        fail = evaluate_zero_setting_accuracy(0.40, 1.0, 0.1, "kg")
        self.assertAlmostEqual(fail.margin_to_limit, -0.15)

    def test_absolute_zero_error(self) -> None:
        r = evaluate_zero_setting_accuracy(-0.20, 1.0, 0.1, "g")
        self.assertEqual(r.absolute_zero_error, 0.20)


class ZeroSettingMethodTests(unittest.TestCase):
    def test_changeover_reuses_indication_before_rounding(self) -> None:
        i, e, dL = 0.0, 2.0, 0.75
        expected_p = indication_before_rounding(i, e, dL)
        r = evaluate_zero_setting_accuracy(i, e, e, "kg", additional_load=dL)
        self.assertEqual(r.error_method, "changeover_point")
        self.assertTrue(r.rounding_elimination_required)
        self.assertEqual(r.indication_before_rounding, expected_p)
        self.assertEqual(r.zero_error, expected_p)
        self.assertEqual(r.additional_load, dL)
        self.assertIn("A.4.4.3", r.rule_reference)

    def test_changeover_boundary_plus_quarter_e(self) -> None:
        # P = I + 0.5e - ΔL = 0 + 0.5 - 0.25 = 0.25e when e=1
        r = evaluate_zero_setting_accuracy(0.0, 1.0, 1.0, "kg", additional_load=0.25)
        self.assertEqual(r.zero_error, 0.25)
        self.assertEqual(r.status, "PASS")

    def test_direct_fine_indication_path(self) -> None:
        r = evaluate_zero_setting_accuracy(0.0, 5.0, 1.0, "kg")
        self.assertFalse(r.rounding_elimination_required)
        self.assertEqual(r.error_method, "direct")
        self.assertIsNone(r.additional_load)
        self.assertEqual(r.zero_error, 0.0)

    def test_missing_delta_l_rejected(self) -> None:
        with self.assertRaises(ValueError):
            evaluate_zero_setting_accuracy(0.0, 1.0, 1.0, "kg")

    def test_additional_load_forbidden_on_direct_path(self) -> None:
        with self.assertRaises(ValueError):
            evaluate_zero_setting_accuracy(0.0, 5.0, 1.0, "kg", additional_load=0.1)


class ZeroSettingValidationTests(unittest.TestCase):
    def test_e_not_positive(self) -> None:
        for bad in (0.0, -1.0):
            with self.assertRaises(ValueError):
                evaluate_zero_setting_accuracy(0.0, bad, 0.1, "kg")

    def test_d_not_positive(self) -> None:
        for bad in (0.0, -0.2):
            with self.assertRaises(ValueError):
                evaluate_zero_setting_accuracy(0.0, 1.0, bad, "kg")

    def test_nan_inf_rejected(self) -> None:
        for bad in (float("nan"), float("inf"), float("-inf")):
            with self.assertRaises(ValueError):
                evaluate_zero_setting_accuracy(bad, 1.0, 0.1, "kg")
            with self.assertRaises(ValueError):
                evaluate_zero_setting_accuracy(0.0, bad, 0.1, "kg")
            with self.assertRaises(ValueError):
                evaluate_zero_setting_accuracy(0.0, 1.0, bad, "kg")

    def test_unsupported_unit(self) -> None:
        with self.assertRaises(ValueError):
            evaluate_zero_setting_accuracy(0.0, 1.0, 0.1, "lb")

    def test_automatic_mode_rejected(self) -> None:
        with self.assertRaises(ValueError):
            evaluate_zero_setting_accuracy(
                0.0, 1.0, 0.1, "kg", setting_mode="automatic"
            )

    def test_bool_rejected(self) -> None:
        with self.assertRaises(ValueError):
            evaluate_zero_setting_accuracy(True, 1.0, 0.1, "kg")


class ZeroSettingProvenanceTests(unittest.TestCase):
    def test_frozen_result(self) -> None:
        r = evaluate_zero_setting_accuracy(0.0, 1.0, 0.1, "kg")
        self.assertIsInstance(r, ZeroSettingResult)
        with self.assertRaises(Exception):
            r.status = "FAIL"  # type: ignore[misc]

    def test_ruleset_and_standard(self) -> None:
        r = evaluate_zero_setting_accuracy(0.0, 1.0, 0.1, "kg")
        self.assertEqual(r.ruleset_version, RULESET_VERSION)
        self.assertEqual(r.standard_code, STANDARD_CODE)
        self.assertEqual(r.standard_edition, STANDARD_EDITION)
        self.assertIn("§4.5.2", r.rule_reference)
        self.assertIn("A.4.2.3", r.rule_reference)


if __name__ == "__main__":
    unittest.main()
