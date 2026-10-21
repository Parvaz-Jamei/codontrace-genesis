"""Identified effects vs. the engine's interventional reruns (ground truth)."""

from __future__ import annotations

import pytest

from codontrace.causal_inference import NotIdentifiable, identify
from codontrace.causal_inference.contingency import decompose, engine_contingency_table
from codontrace.causal_inference.engine_study import (
    EngineBitStudy,
    diagram_from_evidence_graph,
    set_founder_bits,
)
from codontrace.errors import ConfigurationError


@pytest.fixture(scope="module")
def report():
    return EngineBitStudy().validate(n_units=160, seed=0, n_bootstrap=150)


def test_do_bit_only_edits_primary_founders():
    bits = ("101111000", "101111000", "000000000")
    assert set_founder_bits(bits, {1: 1, 2: 0}) == ("110111000", "110111000", "000000000")


def test_identified_effect_matches_fresh_seed_truth(report):
    assert report.adjustment == ("bit:2", "env:population")
    assert report.truth_seeds == (1000, 1001, 1002)
    lo, hi = report.bootstrap_ci
    tlo, thi = report.truth_ci
    assert tlo <= report.true_ate <= thi
    # The truth comes from independent runs, so compare the two intervals.
    assert lo <= thi and tlo <= hi
    assert abs(report.identified_ate - report.true_ate) < 0.1 * abs(report.true_ate) + 0.5


def test_truth_runs_use_only_fresh_seeds_and_never_observational_runs():
    calls = []

    def runner(seed, pop, bits, ticks):
        calls.append(seed)
        return seed % 3 + bits[1] * (1 + bits[2])

    study = EngineBitStudy(seeds=(0, 1, 2), truth_seeds=(7, 8, 9), runner=runner)
    units = study.observational_sample(40, seed=0)
    assert {u.seed for u in units} <= {0, 1, 2} and set(calls) <= {0, 1, 2}
    calls.clear()
    truth = study.ground_truth()
    assert set(calls) == {7, 8, 9} and len(calls) == 3 * 2 * 2 * 2
    assert truth.means[1] - truth.means[0] == pytest.approx(1.5)
    assert truth.ate_ci == pytest.approx((1.5, 1.5))


def test_truth_seeds_must_be_fresh():
    with pytest.raises(ConfigurationError, match="disjoint"):
        EngineBitStudy(seeds=(0, 1, 2), truth_seeds=(2, 3))
    with pytest.raises(ConfigurationError, match="two distinct"):
        EngineBitStudy(truth_seeds=(5, 5))


def test_naive_contrast_is_confounded_and_excluded(report):
    lo, hi = report.bootstrap_ci
    assert not lo <= report.naive_ate <= hi
    assert abs(report.naive_ate - report.true_ate) > 2 * abs(report.identified_ate - report.true_ate)


def test_hidden_environment_makes_effect_not_identifiable():
    study = EngineBitStudy()
    assert study.hidden_environment_is_not_identifiable()
    with pytest.raises(NotIdentifiable):
        identify(study.diagram(env_observed=False), {study.outcome_var}, {study.focal_var})


def test_engine_replay_separates_contingency_from_selection():
    study = EngineBitStudy(seeds=(0, 1, 2, 3))
    d = decompose(engine_contingency_table(study, env=0), n_permutations=199)
    # Focal bit has no effect on the bit:2=0 background and a positive one on
    # bit:2=1: a potentiated, history-dependent effect (Blount et al. 2008).
    assert d.treatment_effect_by_history["bit:2=0"] == 0.0
    assert d.treatment_effect_by_history["bit:2=1"] > 0.0
    assert d.verdict == "historically_contingent"
    assert d.contingency_share > 0.5


def test_decompose_detects_pure_selection_and_pure_chance():
    sel = {h: {0: [1.0, 1.1, 0.9], 1: [3.0, 3.1, 2.9]} for h in ("a", "b", "c")}
    d = decompose(sel, n_permutations=199)
    assert d.verdict == "selection" and d.share("treatment") > 0.9
    noise = {"a": {0: [1.0, 2.0, 0.0], 1: [2.0, 0.0, 1.0]}, "b": {0: [0.0, 1.0, 2.0], 1: [1.0, 2.0, 0.0]}}
    d = decompose(noise, n_permutations=199)
    assert d.verdict == "not_detected" and d.share("chance") > 0.9


def test_decomposition_is_exact():
    t = {"a": {0: [1.0, 2.0], 1: [4.0, 7.0]}, "b": {0: [3.0, 3.5], 1: [1.0, 0.0]}}
    d = decompose(t, n_permutations=9)
    flat = [y for h in t.values() for c in h.values() for y in c]
    mean = sum(flat) / len(flat)
    assert d.ss_total == pytest.approx(sum((y - mean) ** 2 for y in flat))


def test_evidence_graph_bridge():
    from codontrace.genesis.causal_graph import CausalGraph, CausalNode

    g = CausalGraph()
    for nid, kind in (("action:eat", "action"), ("resource:lumen", "resource"), ("action:move", "action")):
        g.add_node(CausalNode(nid, kind, nid))
    g.add_or_update_edge("action:eat", "resource:lumen", "leads_to_resource_gain", tick=1, evidence_ref="r1")
    g.add_or_update_edge("action:move", "action:eat", "precedes", tick=1, evidence_ref="r2")
    d = diagram_from_evidence_graph(g, confounded=[("action:move", "resource:lumen")])
    assert d.directed == frozenset({("event:action:eat", "event:resource:lumen")})
    assert ("event:action:move", "event:resource:lumen") in d.bidirected


def test_empty_focal_arm_names_the_value():
    study = EngineBitStudy(assignment={(0, 0): 0.0, (0, 1): 0.0, (1, 0): 0.0, (1, 1): 0.0},
                           runner=lambda seed, pop, bits, ticks: 0)
    with pytest.raises(ConfigurationError, match="no unit received focal value 1;"):
        study.validate(n_units=4, seed=0, n_bootstrap=2)
