"""Phase 10 campaign: digest-stable calibration suite on HostParasiteWorld."""

from __future__ import annotations

import pytest

from codontrace.errors import ConfigurationError
from codontrace.genesis.host_parasite_calibration import (
    CalibrationReport,
    CalibrationTarget,
    default_smoke_targets,
    run_calibration_suite,
)
from codontrace.genesis.host_parasite_export import calibration_report_rows


@pytest.mark.campaign
def test_calibration_suite_digest_stable_and_directional() -> None:
    report = run_calibration_suite(report_id="calib_smoke_a")
    again = run_calibration_suite(report_id="calib_smoke_a")
    assert report.digest == again.digest
    assert len(report.outcomes) >= 4
    by_id = {o.target_id: o for o in report.outcomes}
    assert by_id["cal_freeze_unlock"].outcome == "pass"
    assert by_id["cal_dual_null"].outcome == "pass"
    assert by_id["cal_continuum_coupling"].outcome == "pass"
    assert by_id["cal_meter_finite"].outcome == "pass"
    assert report.red_queen_proved is False
    assert report.calibration_miss_opens_refuses is False
    assert report.science_grade is False
    assert report.to_dict()["epistasis_hgt_lag_status"] == "deferred"
    rows = calibration_report_rows(report.to_dict())
    assert len(rows) == len(report.outcomes)


@pytest.mark.campaign
def test_calibration_seed_change_changes_digest() -> None:
    a = run_calibration_suite(
        report_id="calib_seed",
        targets=(
            CalibrationTarget(
                target_id="cal_meter_a",
                phenomenon="meter_channel_finiteness",
                expectation="meter_channels_finite",
                literature_note="seed sensitivity",
                seed=0,
                ticks=1,
            ),
        ),
    )
    b = run_calibration_suite(
        report_id="calib_seed",
        targets=(
            CalibrationTarget(
                target_id="cal_meter_a",
                phenomenon="meter_channel_finiteness",
                expectation="meter_channels_finite",
                literature_note="seed sensitivity",
                seed=1,
                ticks=1,
            ),
        ),
    )
    assert a.digest != b.digest


@pytest.mark.campaign
def test_calibration_refuses_honesty_true_and_banned_id() -> None:
    outcomes = run_calibration_suite(report_id="calib_ok").outcomes
    with pytest.raises(ConfigurationError, match="refuses"):
        CalibrationReport(
            report_id="calib_bad",
            outcomes=outcomes,
            calibration_miss_opens_refuses=True,
        )
    with pytest.raises(ConfigurationError, match="banned fragment"):
        CalibrationTarget(
            target_id="infect_cal",
            phenomenon="x",
            expectation="meter_channels_finite",
            literature_note="",
        )


@pytest.mark.campaign
def test_default_targets_catalog_nonempty() -> None:
    assert len(default_smoke_targets()) >= 4
