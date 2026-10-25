"""Subtractive tare-weighing series rule tests."""

from __future__ import annotations

import math
import os
import sys
import unittest

BACKEND_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if BACKEND_ROOT not in sys.path:
    sys.path.insert(0, BACKEND_ROOT)

from rules.compliance import evaluate_digital_observation
from rules.oiml_r76 import RULESET_VERSION, STANDARD_CODE, STANDARD_EDITION
from rules.tare_weighing import (
    TareWeighingSeriesResult,
    evaluate_tare_weighing_series,
)


def _obs(net, indication, zero_error=0.0, additional_load=None, reference=None):
    body = {
        "net_load": net,
        "reference_value": net if reference is None else reference,
        "indication": indication,
        "zero_error": zero_error,
    }
    if additional_load is not None:
        body["additional_load"] = additional_load
    return body


class TareWeighingSeriesTests(unittest.TestCase):
    def _eval(self, tare, observations, **kw):
        args = dict(
            accuracy_class="III",
            maximum_capacity=30000.0,
            minimum_capacity=100.0,
            e=5.0,
            d=0.5,
            unit="g",
            tare_value=tare,
            observations=observations,
        )
        args.update(kw)
        return evaluate_tare_weighing_series(**args)

    def test_five_passing_is_pass(self) -> None:
        obs = [_obs(5000.0, 5000.5, 0.2) for _ in range(5)]
        r = self._eval(0.0, obs)
        self.assertEqual(r.status, "PASS")
        self.assertTrue(r.complete)
        self.assertEqual(r.observation_count, 5)
        self.assertEqual(r.required_observations, 5)
        self.assertEqual(r.failed_observation_indices, ())

    def test_one_failing_is_fail(self) -> None:
        obs = [_obs(5000.0, 5000.5, 0.2) for _ in range(4)]
        obs.append(_obs(5000.0, 5200.0, 0.0))
        r = self._eval(0.0, obs)
        self.assertEqual(r.status, "FAIL")
        self.assertEqual(r.failed_observation_indices, (4,))

    def test_fewer_than_five_incomplete(self) -> None:
        obs = [_obs(5000.0, 5000.5, 0.2) for _ in range(4)]
        r = self._eval(0.0, obs)
        self.assertEqual(r.status, "INCOMPLETE")
        self.assertFalse(r.complete)

    def test_exactly_five_is_complete(self) -> None:
        r = self._eval(0.0, [_obs(5000.0, 5000.5, 0.2)] * 5)
        self.assertTrue(r.complete)
        self.assertEqual(r.observation_count, 5)

    def test_tare_zero_supported(self) -> None:
        r = self._eval(0.0, [_obs(5000.0, 5000.5, 0.2)] * 5)
        self.assertEqual(r.tare_value, 0.0)
        self.assertEqual(r.status, "PASS")

    def test_positive_tare_supported(self) -> None:
        r = self._eval(1000.0, [_obs(5000.0, 5000.5, 0.2)] * 5)
        self.assertEqual(r.tare_value, 1000.0)
        self.assertEqual(r.observations[0].gross_load, 6000.0)
        self.assertEqual(r.status, "PASS")

    def test_gross_exactly_max(self) -> None:
        r = self._eval(10000.0, [_obs(20000.0, 20000.0, 0.0)] * 5)
        self.assertEqual(r.observations[0].gross_load, 30000.0)
        self.assertEqual(r.status, "PASS")

    def test_gross_above_max_rejected(self) -> None:
        with self.assertRaises(ValueError):
            self._eval(10000.0, [_obs(20000.1, 20000.1, 0.0)])

    def test_negative_tare_rejected(self) -> None:
        with self.assertRaises(ValueError):
            self._eval(-1.0, [_obs(100.0, 100.0, 0.0)])

    def test_tare_above_max_rejected(self) -> None:
        with self.assertRaises(ValueError):
            self._eval(30000.1, [_obs(0.0, 0.0, 0.0)])

    def test_negative_net_rejected(self) -> None:
        with self.assertRaises(ValueError):
            self._eval(0.0, [_obs(-1.0, 0.0, 0.0)])

    def test_direct_path(self) -> None:
        r = self._eval(0.0, [_obs(5000.0, 5000.5, 0.2)] * 5)
        self.assertEqual(r.observations[0].compliance.error_method, "direct")

    def test_changeover_path(self) -> None:
        obs = [
            _obs(1000.0, 1000.0, 0.5, additional_load=1.5) for _ in range(5)
        ]
        r = self._eval(0.0, obs, e=5.0, d=5.0)
        self.assertEqual(r.observations[0].compliance.error_method, "changeover_point")
        self.assertEqual(r.status, "PASS")

    def test_ec_mpe_match_compliance_engine(self) -> None:
        item = _obs(5000.0, 5000.5, 0.2)
        expected = evaluate_digital_observation(
            "III", 5000.0, 5000.5, 5.0, 0.5, 0.2
        )
        r = self._eval(0.0, [item] * 5)
        got = r.observations[0].compliance
        self.assertEqual(got.corrected_error, expected.corrected_error)
        self.assertEqual(got.mpe, expected.mpe)
        self.assertEqual(got.result, expected.result)
        self.assertEqual(got.absolute_corrected_error, expected.absolute_corrected_error)

    def test_failed_indices(self) -> None:
        obs = [
            _obs(5000.0, 5000.5, 0.2),
            _obs(5000.0, 5200.0, 0.0),
            _obs(5000.0, 5000.5, 0.2),
            _obs(5000.0, 5300.0, 0.0),
            _obs(5000.0, 5000.5, 0.2),
        ]
        r = self._eval(0.0, obs)
        self.assertEqual(r.failed_observation_indices, (1, 3))

    def test_frozen_result(self) -> None:
        r = self._eval(0.0, [_obs(5000.0, 5000.5, 0.2)] * 5)
        self.assertIsInstance(r, TareWeighingSeriesResult)
        with self.assertRaises(Exception):
            r.status = "FAIL"  # type: ignore[misc]

    def test_provenance(self) -> None:
        r = self._eval(0.0, [_obs(5000.0, 5000.5, 0.2)] * 5)
        self.assertEqual(r.ruleset_version, RULESET_VERSION)
        self.assertEqual(r.standard_code, STANDARD_CODE)
        self.assertEqual(r.standard_edition, STANDARD_EDITION)
        self.assertIn("§3.5.3.3", r.rule_reference)
        self.assertIn("A.4.6.1", r.rule_reference)
        self.assertNotIn("§4.6.3", r.rule_reference)
        self.assertNotIn("A.4.6.2", r.rule_reference)

    def test_nan_inf_rejected(self) -> None:
        for bad in (float("nan"), float("inf"), float("-inf")):
            with self.assertRaises(ValueError):
                self._eval(bad, [_obs(5000.0, 5000.5, 0.2)])
            with self.assertRaises(ValueError):
                self._eval(0.0, [_obs(bad, 5000.0, 0.0)])

    def test_unsupported_unit_and_class(self) -> None:
        with self.assertRaises(ValueError):
            self._eval(0.0, [_obs(5000.0, 5000.5, 0.2)], unit="lb")
        with self.assertRaises(ValueError):
            self._eval(0.0, [_obs(5000.0, 5000.5, 0.2)], accuracy_class="IV")


if __name__ == "__main__":
    unittest.main()
