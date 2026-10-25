"""unittest coverage for quarter-segment eccentricity (§3.6.2 / A.4.7.1)."""

from __future__ import annotations

import math
import os
import sys
import unittest
from dataclasses import FrozenInstanceError

BACKEND_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if BACKEND_ROOT not in sys.path:
    sys.path.insert(0, BACKEND_ROOT)

from rules.eccentricity import (
    EccentricityResult,
    evaluate_quarter_segment_eccentricity,
)
from rules.oiml_r76 import calculate_mpe


def _four(q1: float, q2: float, q3: float, q4: float) -> dict[str, float]:
    return {"Q1": q1, "Q2": q2, "Q3": q3, "Q4": q4}


class RequiredLoadTests(unittest.TestCase):
    def test_thirty_kg_no_tare(self) -> None:
        r = evaluate_quarter_segment_eccentricity(
            "III", 30.0, 0.01, "kg", {"Q1": 0.0}
        )
        self.assertEqual(r.required_test_load, 10.0)

    def test_thirty_kg_with_tare(self) -> None:
        r = evaluate_quarter_segment_eccentricity(
            "III", 30.0, 0.01, "kg", {"Q1": 0.0}, maximum_additive_tare_effect=3.0
        )
        self.assertEqual(r.required_test_load, 11.0)

    def test_equivalent_units(self) -> None:
        kg = evaluate_quarter_segment_eccentricity(
            "III", 30.0, 0.01, "kg", {"Q1": 0.0}, maximum_additive_tare_effect=3.0
        )
        g = evaluate_quarter_segment_eccentricity(
            "III", 30000.0, 10.0, "g", {"Q1": 0.0}, maximum_additive_tare_effect=3000.0
        )
        t = evaluate_quarter_segment_eccentricity(
            "III", 0.03, 0.00001, "t", {"Q1": 0.0}, maximum_additive_tare_effect=0.003
        )
        self.assertEqual(kg.required_test_load, 11.0)
        self.assertEqual(g.required_test_load, 11000.0)
        self.assertAlmostEqual(t.required_test_load, 0.011)


class VerdictTests(unittest.TestCase):
    def test_partial_positions_incomplete(self) -> None:
        for n in (1, 2, 3):
            keys = ["Q1", "Q2", "Q3", "Q4"][:n]
            r = evaluate_quarter_segment_eccentricity(
                "III", 30.0, 0.01, "kg", {k: 0.0 for k in keys}
            )
            self.assertFalse(r.complete)
            self.assertEqual(r.status, "INCOMPLETE")
            self.assertEqual(len(r.tested_positions), n)

    def test_four_inside_mpe_pass(self) -> None:
        # load 10 kg, e=0.01 → m=1000 → MPE=1.0e=0.01
        r = evaluate_quarter_segment_eccentricity(
            "III", 30.0, 0.01, "kg", _four(0.002, -0.004, 0.0, 0.009)
        )
        self.assertTrue(r.complete)
        self.assertEqual(r.status, "PASS")
        self.assertTrue(r.all_positions_within_mpe)
        self.assertEqual(r.failed_positions, ())

    def test_exactly_plus_mpe_pass(self) -> None:
        r = evaluate_quarter_segment_eccentricity(
            "III", 30000.0, 10.0, "g", _four(10.0, 0.0, 0.0, 0.0)
        )
        self.assertEqual(r.required_test_load, 10000.0)
        self.assertEqual(r.mpe, 10.0)
        self.assertEqual(r.status, "PASS")

    def test_exactly_minus_mpe_pass(self) -> None:
        r = evaluate_quarter_segment_eccentricity(
            "III", 30000.0, 10.0, "g", _four(0.0, -10.0, 0.0, 0.0)
        )
        self.assertEqual(r.status, "PASS")
        self.assertEqual(r.failed_positions, ())

    def test_just_above_plus_mpe_fail(self) -> None:
        r = evaluate_quarter_segment_eccentricity(
            "III", 30000.0, 10.0, "g", _four(10.0001, 0.0, 0.0, 0.0)
        )
        self.assertEqual(r.status, "FAIL")
        self.assertEqual(r.failed_positions, ("Q1",))

    def test_just_below_minus_mpe_fail(self) -> None:
        r = evaluate_quarter_segment_eccentricity(
            "III", 30000.0, 10.0, "g", _four(0.0, 0.0, -10.0001, 0.0)
        )
        self.assertEqual(r.status, "FAIL")
        self.assertEqual(r.failed_positions, ("Q3",))


class ValidationTests(unittest.TestCase):
    def test_unknown_position_rejected(self) -> None:
        with self.assertRaises(ValueError):
            evaluate_quarter_segment_eccentricity(
                "III", 30.0, 0.01, "kg", {"Q1": 0.0, "Q5": 0.0}
            )

    def test_empty_rejected(self) -> None:
        with self.assertRaises(ValueError):
            evaluate_quarter_segment_eccentricity("III", 30.0, 0.01, "kg", {})

    def test_malformed_inputs_rejected(self) -> None:
        good = {"Q1": 0.0}
        with self.assertRaises(ValueError):
            evaluate_quarter_segment_eccentricity("IV", 30.0, 0.01, "kg", good)
        with self.assertRaises(ValueError):
            evaluate_quarter_segment_eccentricity("III", 30.0, 0.01, "lb", good)
        with self.assertRaises(ValueError):
            evaluate_quarter_segment_eccentricity("III", 0.0, 0.01, "kg", good)
        with self.assertRaises(ValueError):
            evaluate_quarter_segment_eccentricity("III", 30.0, 0.0, "kg", good)
        with self.assertRaises(ValueError):
            evaluate_quarter_segment_eccentricity("III", True, 0.01, "kg", good)
        with self.assertRaises(ValueError):
            evaluate_quarter_segment_eccentricity("III", float("nan"), 0.01, "kg", good)
        with self.assertRaises(ValueError):
            evaluate_quarter_segment_eccentricity("III", 30.0, float("inf"), "kg", good)
        with self.assertRaises(ValueError):
            evaluate_quarter_segment_eccentricity("III", 30.0, 0.01, "kg", {"Q1": True})
        with self.assertRaises(ValueError):
            evaluate_quarter_segment_eccentricity("III", 30.0, 0.01, "kg", {"Q1": float("nan")})
        with self.assertRaises(ValueError):
            evaluate_quarter_segment_eccentricity("III", 30.0, 0.01, "kg", {"Q1": math.inf})
        with self.assertRaises(ValueError):
            evaluate_quarter_segment_eccentricity(
                "III", 30.0, 0.01, "kg", {"Q1": 0, "Q2": 0, "Q3": 0, "Q4": 0, "Q1b": 0}
            )

    def test_negative_tare_rejected(self) -> None:
        with self.assertRaises(ValueError):
            evaluate_quarter_segment_eccentricity(
                "III", 30.0, 0.01, "kg", {"Q1": 0.0}, maximum_additive_tare_effect=-0.1
            )


class MpeDelegationTests(unittest.TestCase):
    def test_mpe_matches_calculate_mpe(self) -> None:
        r = evaluate_quarter_segment_eccentricity(
            "III", 30.0, 0.01, "kg", _four(0.0, 0.0, 0.0, 0.0)
        )
        expected = calculate_mpe("III", 10.0, 0.01, stage="initial")
        self.assertEqual(r.mpe, expected.mpe)
        self.assertEqual(r.mpe, 0.01)

    def test_two_class_iii_bands(self) -> None:
        # 10 kg / 0.01 = 1000 e → 1.0 e; 4.5 kg / 0.01 = 450 e → 0.5 e
        high = evaluate_quarter_segment_eccentricity(
            "III", 30.0, 0.01, "kg", _four(0.0, 0.0, 0.0, 0.0)
        )
        low = evaluate_quarter_segment_eccentricity(
            "III", 13.5, 0.01, "kg", _four(0.0, 0.0, 0.0, 0.0)
        )
        self.assertEqual(low.required_test_load, 4.5)
        self.assertEqual(low.mpe, calculate_mpe("III", 4.5, 0.01).mpe)
        self.assertEqual(high.mpe, calculate_mpe("III", 10.0, 0.01).mpe)
        self.assertEqual(low.mpe, 0.005)
        self.assertEqual(high.mpe, 0.01)

    def test_frozen(self) -> None:
        r = evaluate_quarter_segment_eccentricity(
            "III", 30.0, 0.01, "kg", {"Q1": 0.0}
        )
        self.assertIsInstance(r, EccentricityResult)
        with self.assertRaises(FrozenInstanceError):
            r.status = "PASS"  # type: ignore[misc]
        self.assertEqual(
            r.rule_reference,
            "OIML R 76-1:2006 §3.6.2; §3.6.2.1; Annex A §A.4.7; §A.4.7.1",
        )
        self.assertEqual(r.ruleset_version, "R76-1-2006-v1")


if __name__ == "__main__":
    unittest.main()
