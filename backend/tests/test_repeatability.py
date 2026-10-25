"""unittest coverage for type-approval repeatability (§3.6.1 / A.4.10)."""

from __future__ import annotations

import math
import os
import sys
import unittest
from dataclasses import FrozenInstanceError

BACKEND_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if BACKEND_ROOT not in sys.path:
    sys.path.insert(0, BACKEND_ROOT)

from rules.oiml_r76 import calculate_mpe
from rules.repeatability import (
    RepeatabilitySeriesResult,
    evaluate_type_approval_repeatability_series,
)


def _ten(base: float, *deltas: float) -> list[float]:
    vals = [base] * 10
    for i, d in enumerate(deltas):
        vals[i] = base + d
    return vals


class RequiredCountTests(unittest.TestCase):
    def test_30_kg_class_iii_requires_10(self) -> None:
        r = evaluate_type_approval_repeatability_series(
            "III", 30.0, 15.0, 0.01, "kg", [15.0]
        )
        self.assertEqual(r.required_weighings, 10)
        self.assertEqual(r.status, "INCOMPLETE")

    def test_exactly_1000_kg_requires_3(self) -> None:
        r = evaluate_type_approval_repeatability_series(
            "III", 1000.0, 500.0, 0.5, "kg", [500.0, 500.0, 500.0]
        )
        self.assertEqual(r.required_weighings, 3)

    def test_tonne_threshold(self) -> None:
        low = evaluate_type_approval_repeatability_series(
            "III", 0.999, 0.5, 0.0005, "t", [0.5]
        )
        high = evaluate_type_approval_repeatability_series(
            "III", 1.0, 0.5, 0.0005, "t", [0.5, 0.5, 0.5]
        )
        self.assertEqual(low.required_weighings, 10)
        self.assertEqual(high.required_weighings, 3)


class VerdictTests(unittest.TestCase):
    def test_spread_less_than_mpe_pass(self) -> None:
        # Class III, Max 30 kg, load 15 kg, e=0.01 → m=1500 → MPE=1.0e=0.01
        readings = _ten(15.00, 0.0, 0.004)
        r = evaluate_type_approval_repeatability_series(
            "III", 30.0, 15.0, 0.01, "kg", readings
        )
        mpe = calculate_mpe("III", 15.0, 0.01, stage="initial")
        self.assertEqual(r.mpe, mpe.mpe)
        self.assertEqual(r.mpe, 0.01)
        self.assertLess(r.spread, r.mpe)
        self.assertTrue(r.complete)
        self.assertEqual(r.status, "PASS")

    def test_spread_equal_mpe_pass(self) -> None:
        # Integer grams: Class III Max 30000 g, load 15000, e=10 → m=1500 → MPE=10
        readings = [15000.0] * 9 + [15010.0]
        r = evaluate_type_approval_repeatability_series(
            "III", 30000.0, 15000.0, 10.0, "g", readings
        )
        self.assertEqual(r.spread, r.mpe)
        self.assertEqual(r.spread, 10.0)
        self.assertEqual(r.status, "PASS")
        self.assertTrue(r.spread_within_mpe)

    def test_spread_just_greater_than_mpe_fail(self) -> None:
        readings = [15000.0] * 9 + [15010.0001]
        r = evaluate_type_approval_repeatability_series(
            "III", 30000.0, 15000.0, 10.0, "g", readings
        )
        self.assertGreater(r.spread, r.mpe)
        self.assertEqual(r.status, "FAIL")
        self.assertFalse(r.spread_within_mpe)

    def test_nine_readings_incomplete(self) -> None:
        r = evaluate_type_approval_repeatability_series(
            "III", 30.0, 15.0, 0.01, "kg", [15.0] * 9
        )
        self.assertFalse(r.complete)
        self.assertEqual(r.status, "INCOMPLETE")
        self.assertEqual(r.weighing_count, 9)

    def test_extra_readings_allowed(self) -> None:
        r = evaluate_type_approval_repeatability_series(
            "III", 30.0, 15.0, 0.01, "kg", [15.0] * 12
        )
        self.assertTrue(r.complete)
        self.assertEqual(r.weighing_count, 12)
        self.assertEqual(r.status, "PASS")

    def test_single_reading_incomplete(self) -> None:
        r = evaluate_type_approval_repeatability_series(
            "III", 30.0, 15.0, 0.01, "kg", [15.0]
        )
        self.assertEqual(r.weighing_count, 1)
        self.assertEqual(r.spread, 0.0)
        self.assertEqual(r.status, "INCOMPLETE")


class ValidationTests(unittest.TestCase):
    def test_rejects_malformed(self) -> None:
        good = dict(
            accuracy_class="III",
            max_capacity=30.0,
            applied_load=15.0,
            e=0.01,
            unit="kg",
            readings=[15.0],
        )
        with self.assertRaises(ValueError):
            evaluate_type_approval_repeatability_series(**{**good, "accuracy_class": "IV"})
        with self.assertRaises(ValueError):
            evaluate_type_approval_repeatability_series(**{**good, "unit": "lb"})
        with self.assertRaises(ValueError):
            evaluate_type_approval_repeatability_series(**{**good, "max_capacity": 0})
        with self.assertRaises(ValueError):
            evaluate_type_approval_repeatability_series(**{**good, "applied_load": -1})
        with self.assertRaises(ValueError):
            evaluate_type_approval_repeatability_series(**{**good, "e": 0})
        with self.assertRaises(ValueError):
            evaluate_type_approval_repeatability_series(**{**good, "max_capacity": True})
        with self.assertRaises(ValueError):
            evaluate_type_approval_repeatability_series(**{**good, "applied_load": float("nan")})
        with self.assertRaises(ValueError):
            evaluate_type_approval_repeatability_series(**{**good, "e": float("inf")})
        with self.assertRaises(ValueError):
            evaluate_type_approval_repeatability_series(**{**good, "readings": []})
        with self.assertRaises(ValueError):
            evaluate_type_approval_repeatability_series(**{**good, "readings": [True]})
        with self.assertRaises(ValueError):
            evaluate_type_approval_repeatability_series(**{**good, "readings": [float("nan")]})
        with self.assertRaises(ValueError):
            evaluate_type_approval_repeatability_series(**{**good, "readings": [math.inf]})
        with self.assertRaises(ValueError):
            evaluate_type_approval_repeatability_series(**{**good, "readings": "15"})

    def test_applied_load_above_max_rejected(self) -> None:
        with self.assertRaises(ValueError):
            evaluate_type_approval_repeatability_series(
                "III", 30.0, 30.1, 0.01, "kg", [30.0]
            )


class MpeDelegationTests(unittest.TestCase):
    def test_mpe_matches_calculate_mpe_two_class_iii_bands(self) -> None:
        # m = 400 → 0.5 e; m = 1500 → 1.0 e
        low = evaluate_type_approval_repeatability_series(
            "III", 30.0, 4.0, 0.01, "kg", [4.0] * 10
        )
        high = evaluate_type_approval_repeatability_series(
            "III", 30.0, 15.0, 0.01, "kg", [15.0] * 10
        )
        self.assertEqual(low.mpe, calculate_mpe("III", 4.0, 0.01).mpe)
        self.assertEqual(high.mpe, calculate_mpe("III", 15.0, 0.01).mpe)
        self.assertEqual(low.mpe, 0.005)
        self.assertEqual(high.mpe, 0.01)
        self.assertNotEqual(low.mpe, high.mpe)

    def test_frozen(self) -> None:
        r = evaluate_type_approval_repeatability_series(
            "III", 30.0, 15.0, 0.01, "kg", [15.0]
        )
        self.assertIsInstance(r, RepeatabilitySeriesResult)
        with self.assertRaises(FrozenInstanceError):
            r.status = "PASS"  # type: ignore[misc]
        self.assertEqual(r.rule_reference, "OIML R 76-1:2006 §3.6.1; Annex A §A.4.10")
        self.assertEqual(r.ruleset_version, "R76-1-2006-v1")


if __name__ == "__main__":
    unittest.main()
