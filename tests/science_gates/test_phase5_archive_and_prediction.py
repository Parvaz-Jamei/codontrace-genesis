"""Phase 5: immutable time-shift archive, and prediction gain that is not a slope.

A frozen dataclass does not freeze a dict it holds. The Granger-style gain is
the fractional drop in residual error against the target's own lag (Granger
1969), not the absolute slope of the source. Empty controls stay a confounded
candidate and are not a causal claim.
"""

from __future__ import annotations

from types import MappingProxyType

import pytest

from codontrace.errors import ConfigurationError
from codontrace.genesis.causal_validation import granger_lite_probe
from codontrace.life_loop.time_shift_assay import CohortArchive


def _abs_source_slope(source: list[float], target: list[float], lag: int) -> float:
    paired = [(source[index - lag], target[index]) for index in range(lag, len(target))]
    x_mean = sum(x for x, _ in paired) / len(paired)
    y_mean = sum(y for _, y in paired) / len(paired)
    cov = sum((x - x_mean) * (y - y_mean) for x, y in paired)
    var = sum((x - x_mean) ** 2 for x, _ in paired)
    return abs(cov / var)


def test_recorded_snapshot_does_not_follow_later_mutation() -> None:
    archive = CohortArchive()
    raw = {"m": ["a"]}
    snap = archive.record(1, raw)
    stored = snap.digest
    raw["m"] = ["changed"]
    raw["other"] = ["new"]
    assert archive.require(1).features_by_member["m"] == frozenset({"a"})
    assert "other" not in archive.require(1).features_by_member
    with pytest.raises(TypeError):
        snap.features_by_member["m"] = frozenset({"z"})
    exported = snap.to_dict()
    exported["features_by_member"]["m"] = ["z"]
    assert archive.require(1).features_by_member["m"] == frozenset({"a"})
    assert archive.require(1).digest == stored
    assert snap.to_dict()["digest"] == stored


def test_digest_mismatch_is_rejected_when_the_body_is_replaced() -> None:
    archive = CohortArchive()
    snap = archive.record(1, {"m": ["a"]})
    object.__setattr__(snap, "features_by_member", MappingProxyType({"m": frozenset({"z"})}))
    with pytest.raises(ConfigurationError, match="digest"):
        archive.require(1)
    with pytest.raises(ConfigurationError, match="digest"):
        snap.to_dict()


def test_replacing_a_tick_without_a_revision_is_refused() -> None:
    archive = CohortArchive()
    original = archive.record(1, {"m": ["a"]})
    before = archive.digest()
    with pytest.raises(ConfigurationError, match="revise"):
        archive.record(1, {"m": ["b"]})
    assert archive.require(1).digest == original.digest
    assert archive.digest() == before
    revised = archive.revise(1, {"m": ["b"]}, reason="corrected transcription")
    assert revised.features_by_member["m"] == frozenset({"b"})
    assert archive.revisions[0].superseded.features_by_member["m"] == frozenset({"a"})
    assert archive.revisions[0].superseded.digest == original.digest
    assert archive.revisions[0].replacement_digest == revised.digest
    assert archive.digest() != before


def test_nonzero_slope_is_not_predictive_gain_and_untested_lags_are_absent() -> None:
    series = [0.0, 1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0]
    probe = granger_lite_probe(series, series, max_lag=1)
    assert _abs_source_slope(series, series, 1) == pytest.approx(1.0)
    assert probe.predictive_gain == 0.0
    assert probe.status == "not_predictive"
    assert probe.tested_lags == (1,)
    assert probe.gain_definition == "fractional_sse_reduction_vs_target_own_lag"
    assert probe.evidence_level != "intervention_supported"

    short = [0.0, 1.0, 2.0, 3.0, 4.0]
    limited = granger_lite_probe(short, short, max_lag=3)
    assert limited.tested_lags == (1,)
    assert 2 not in limited.tested_lags and 3 not in limited.tested_lags

    source = [0.0, 1.0, 0.0, 1.0, 0.0, 1.0, 0.0, 1.0]
    target = [0.0, 0.0, 1.0, 0.0, 1.0, 0.0, 1.0, 0.0]
    helpful = granger_lite_probe(source, target, max_lag=2)
    assert helpful.tested_lags == (1, 2)
    assert helpful.predictive_gain > 0.0
    assert helpful.status == "confounded_candidate"
    assert helpful.evidence_level == "lagged_predictive_support"
    assert helpful.caveat == "predictive_precedence_not_mechanistic_causality"
