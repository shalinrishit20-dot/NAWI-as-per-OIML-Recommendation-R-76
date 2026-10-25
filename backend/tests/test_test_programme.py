"""unittest coverage for the implemented-core test-programme aggregator."""

from __future__ import annotations

import os
import sys
import unittest
from dataclasses import FrozenInstanceError

BACKEND_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if BACKEND_ROOT not in sys.path:
    sys.path.insert(0, BACKEND_ROOT)

from rules.compliance import evaluate_digital_observation
from rules.eccentricity import evaluate_quarter_segment_eccentricity
from rules.repeatability import evaluate_type_approval_repeatability_series
from rules.tare_weighing import evaluate_tare_weighing_series
from rules.test_programme import (
    CoreTestProgrammeResult,
    evaluate_core_test_programme,
)
from rules.zero_setting import evaluate_zero_setting_accuracy


def _obs_pass():
    return evaluate_digital_observation("III", 5000.0, 5000.5, 5.0, 0.5, 0.2)


def _obs_fail():
    return evaluate_digital_observation("III", 5000.0, 5010.0, 5.0, 0.5, 0.0)


def _rep_pass(load: float):
    return evaluate_type_approval_repeatability_series(
        "III", 30.0, load, 0.01, "kg", [load] * 10
    )


def _rep_incomplete(load: float):
    return evaluate_type_approval_repeatability_series(
        "III", 30.0, load, 0.01, "kg", [load]
    )


def _rep_fail(load: float):
    return evaluate_type_approval_repeatability_series(
        "III", 30000.0, load, 10.0, "g", [load] * 9 + [load + 10.0001]
    )


def _ecc_pass():
    return evaluate_quarter_segment_eccentricity(
        "III", 30000.0, 10.0, "g",
        {"Q1": 0.0, "Q2": 0.0, "Q3": 0.0, "Q4": 0.0},
    )


def _ecc_fail():
    return evaluate_quarter_segment_eccentricity(
        "III", 30000.0, 10.0, "g",
        {"Q1": 10.0001, "Q2": 0.0, "Q3": 0.0, "Q4": 0.0},
    )


def _ecc_incomplete():
    return evaluate_quarter_segment_eccentricity(
        "III", 30.0, 0.01, "kg", {"Q1": 0.0}
    )


def _zero_pass():
    return evaluate_zero_setting_accuracy(0.0, 1.0, 0.1, "kg")


def _zero_fail():
    return evaluate_zero_setting_accuracy(1.0, 1.0, 0.1, "kg")


def _tare_obs(net, indication, zero_error=0.2):
    return {
        "net_load": net,
        "reference_value": net,
        "indication": indication,
        "zero_error": zero_error,
    }


def _tare_pass():
    return evaluate_tare_weighing_series(
        "III", 30000.0, 100.0, 5.0, 0.5, "g", 0.0,
        [_tare_obs(5000.0, 5000.5)] * 5,
    )


def _tare_fail():
    obs = [_tare_obs(5000.0, 5000.5)] * 4
    obs.append(_tare_obs(5000.0, 5200.0, 0.0))
    return evaluate_tare_weighing_series(
        "III", 30000.0, 100.0, 5.0, 0.5, "g", 0.0, obs,
    )


def _tare_incomplete():
    return evaluate_tare_weighing_series(
        "III", 30000.0, 100.0, 5.0, 0.5, "g", 0.0,
        [_tare_obs(5000.0, 5000.5)] * 3,
    )


def _all_four_except_zero_tare(**extra):
    args = dict(
        observations=[_obs_pass()],
        repeatability_half_max=_rep_pass(15.0),
        repeatability_near_max=_rep_pass(30.0),
        eccentricity=_ecc_pass(),
    )
    args.update(extra)
    return evaluate_core_test_programme(**args)


class EmptyAndPartialTests(unittest.TestCase):
    def test_everything_missing_incomplete(self) -> None:
        r = evaluate_core_test_programme([])
        self.assertEqual(r.zero_setting_status, "INCOMPLETE")
        self.assertEqual(r.observation_status, "INCOMPLETE")
        self.assertEqual(r.repeatability_status, "INCOMPLETE")
        self.assertEqual(r.eccentricity_status, "INCOMPLETE")
        self.assertEqual(r.tare_weighing_status, "INCOMPLETE")
        self.assertEqual(r.overall_status, "INCOMPLETE")
        self.assertEqual(
            r.incomplete_modules,
            ("zero_setting", "observation", "repeatability", "eccentricity", "tare_weighing"),
        )
        self.assertEqual(r.failed_modules, ())
        self.assertFalse(r.full_standard_coverage)
        self.assertEqual(r.observation_count, 0)

    def test_observations_pass_others_missing_incomplete(self) -> None:
        r = evaluate_core_test_programme([_obs_pass()])
        self.assertEqual(r.observation_status, "PASS")
        self.assertEqual(r.overall_status, "INCOMPLETE")
        self.assertIn("repeatability", r.incomplete_modules)
        self.assertIn("zero_setting", r.incomplete_modules)
        self.assertIn("tare_weighing", r.incomplete_modules)


class ObservationModuleTests(unittest.TestCase):
    def test_one_observation_fail_overall_fail(self) -> None:
        r = evaluate_core_test_programme(
            [_obs_pass(), _obs_fail()],
            repeatability_half_max=_rep_pass(15.0),
            repeatability_near_max=_rep_pass(30.0),
            eccentricity=_ecc_pass(),
            zero_setting=_zero_pass(),
            tare_weighing=_tare_pass(),
        )
        self.assertEqual(r.observation_status, "FAIL")
        self.assertEqual(r.overall_status, "FAIL")
        self.assertEqual(r.failed_modules, ("observation",))


class RepeatabilityModuleTests(unittest.TestCase):
    def test_both_series_pass(self) -> None:
        r = evaluate_core_test_programme(
            [_obs_pass()],
            repeatability_half_max=_rep_pass(15.0),
            repeatability_near_max=_rep_pass(30.0),
        )
        self.assertEqual(r.repeatability_status, "PASS")
        self.assertEqual(r.repeatability_half_max_status, "PASS")
        self.assertEqual(r.repeatability_near_max_status, "PASS")

    def test_one_series_missing_incomplete(self) -> None:
        r = evaluate_core_test_programme(
            [_obs_pass()],
            repeatability_half_max=_rep_pass(15.0),
        )
        self.assertEqual(r.repeatability_status, "INCOMPLETE")
        self.assertIsNone(r.repeatability_near_max_status)

    def test_one_series_incomplete(self) -> None:
        r = evaluate_core_test_programme(
            [_obs_pass()],
            repeatability_half_max=_rep_pass(15.0),
            repeatability_near_max=_rep_incomplete(30.0),
        )
        self.assertEqual(r.repeatability_status, "INCOMPLETE")
        self.assertEqual(r.repeatability_near_max_status, "INCOMPLETE")

    def test_one_series_fail(self) -> None:
        r = evaluate_core_test_programme(
            [_obs_pass()],
            repeatability_half_max=_rep_fail(15000.0),
            repeatability_near_max=_rep_pass(30.0),
        )
        self.assertEqual(r.repeatability_status, "FAIL")
        self.assertEqual(r.overall_status, "FAIL")
        self.assertIn("repeatability", r.failed_modules)


class EccentricityModuleTests(unittest.TestCase):
    def test_pass_fail_incomplete(self) -> None:
        p = evaluate_core_test_programme([], eccentricity=_ecc_pass())
        f = evaluate_core_test_programme([], eccentricity=_ecc_fail())
        i = evaluate_core_test_programme([], eccentricity=_ecc_incomplete())
        n = evaluate_core_test_programme([])
        self.assertEqual(p.eccentricity_status, "PASS")
        self.assertEqual(f.eccentricity_status, "FAIL")
        self.assertEqual(i.eccentricity_status, "INCOMPLETE")
        self.assertEqual(n.eccentricity_status, "INCOMPLETE")
        self.assertEqual(f.overall_status, "FAIL")


class FiveModuleTests(unittest.TestCase):
    def test_all_five_pass(self) -> None:
        r = _all_four_except_zero_tare(zero_setting=_zero_pass(), tare_weighing=_tare_pass())
        self.assertEqual(r.zero_setting_status, "PASS")
        self.assertEqual(r.observation_status, "PASS")
        self.assertEqual(r.repeatability_status, "PASS")
        self.assertEqual(r.eccentricity_status, "PASS")
        self.assertEqual(r.tare_weighing_status, "PASS")
        self.assertEqual(r.overall_status, "PASS")
        self.assertFalse(r.full_standard_coverage)
        self.assertEqual(r.failed_modules, ())
        self.assertEqual(r.incomplete_modules, ())

    def test_zero_missing_others_pass_incomplete(self) -> None:
        r = _all_four_except_zero_tare(tare_weighing=_tare_pass())
        self.assertEqual(r.zero_setting_status, "INCOMPLETE")
        self.assertEqual(r.overall_status, "INCOMPLETE")
        self.assertEqual(r.incomplete_modules, ("zero_setting",))

    def test_tare_missing_others_pass_incomplete(self) -> None:
        r = _all_four_except_zero_tare(zero_setting=_zero_pass())
        self.assertEqual(r.tare_weighing_status, "INCOMPLETE")
        self.assertEqual(r.overall_status, "INCOMPLETE")
        self.assertEqual(r.incomplete_modules, ("tare_weighing",))

    def test_zero_fail_outranks_incomplete(self) -> None:
        r = evaluate_core_test_programme(
            [_obs_pass()],
            zero_setting=_zero_fail(),
        )
        self.assertEqual(r.overall_status, "FAIL")
        self.assertIn("zero_setting", r.failed_modules)
        self.assertIn("tare_weighing", r.incomplete_modules)

    def test_tare_fail_outranks_incomplete(self) -> None:
        r = evaluate_core_test_programme(
            [_obs_pass()],
            tare_weighing=_tare_fail(),
        )
        self.assertEqual(r.overall_status, "FAIL")
        self.assertIn("tare_weighing", r.failed_modules)

    def test_tare_incomplete_status(self) -> None:
        r = _all_four_except_zero_tare(zero_setting=_zero_pass(), tare_weighing=_tare_incomplete())
        self.assertEqual(r.tare_weighing_status, "INCOMPLETE")
        self.assertEqual(r.overall_status, "INCOMPLETE")


class OverallTests(unittest.TestCase):
    def test_all_modules_pass_overall_pass_not_full_coverage(self) -> None:
        r = _all_four_except_zero_tare(zero_setting=_zero_pass(), tare_weighing=_tare_pass())
        self.assertEqual(r.overall_status, "PASS")
        self.assertFalse(r.full_standard_coverage)
        self.assertEqual(r.scope_name, "OIML R76 implemented core test scope")
        self.assertIn("tare", r.scope_note.lower())
        self.assertIn("zero-setting", r.scope_note.lower())

    def test_fail_outranks_incomplete(self) -> None:
        r = evaluate_core_test_programme(
            [_obs_fail()],
            eccentricity=_ecc_incomplete(),
        )
        self.assertEqual(r.overall_status, "FAIL")
        self.assertEqual(r.failed_modules, ("observation",))
        self.assertIn("repeatability", r.incomplete_modules)
        self.assertIn("zero_setting", r.incomplete_modules)
        self.assertIn("tare_weighing", r.incomplete_modules)

    def test_references_deduplicated(self) -> None:
        obs = _obs_pass()
        half = _rep_pass(15.0)
        near = _rep_pass(30.0)
        ecc = _ecc_pass()
        zero = _zero_pass()
        tare = _tare_pass()
        r = evaluate_core_test_programme(
            [obs, obs],
            repeatability_half_max=half,
            repeatability_near_max=near,
            eccentricity=ecc,
            zero_setting=zero,
            tare_weighing=tare,
        )
        self.assertEqual(
            r.rule_references,
            (
                zero.rule_reference,
                obs.error_rule_reference,
                obs.mpe_rule_reference,
                half.rule_reference,
                ecc.rule_reference,
                tare.rule_reference,
            ),
        )
        self.assertEqual(len(r.rule_references), len(set(r.rule_references)))

    def test_frozen_and_rejects_dicts(self) -> None:
        r = evaluate_core_test_programme([])
        self.assertIsInstance(r, CoreTestProgrammeResult)
        with self.assertRaises(FrozenInstanceError):
            r.overall_status = "PASS"  # type: ignore[misc]
        with self.assertRaises(ValueError):
            evaluate_core_test_programme([{"result": "PASS"}])  # type: ignore[list-item]


if __name__ == "__main__":
    unittest.main()
