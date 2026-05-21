from codontrace.genesis.causal_graph import CausalGraph
from codontrace.genesis.causal_validation import (
    PredictiveProbeResult,
    build_intervention_result,
    granger_lite_probe,
)
from codontrace.genesis.event_graph import EventGraph, event_graph_from_causal_graph
from codontrace.genesis.statistical_protocol import (
    OEEClaimThresholds,
    StatisticalTestPolicy,
    build_oee_metrics_report,
    choose_paired_test,
    validate_statistical_claim_inputs,
)
from codontrace.genesis.translation_profile import (
    TranslationPolicy,
    TranslationWeight,
    build_semantic_proxy_report,
    build_translation_profile,
    inherit_translation_profile,
    resolve_translation_action,
    translation_profile_from_dict,
    update_translation_profile,
)


def test_event_graph_canonical_and_causal_graph_alias_temporal_association():
    graph = CausalGraph()
    assert graph.to_dict()["claim_level"] == "temporal_association"
    event_graph = event_graph_from_causal_graph(graph)
    assert isinstance(event_graph, EventGraph)
    assert event_graph.claim_level == "temporal_association"


def test_predictive_probe_records_lags_controls_and_no_intervention_claim():
    probe = granger_lite_probe([0, 1, 2, 3], [0, 0, 1, 2], max_lag=1)
    assert probe.selected_lag == 1
    assert probe.tested_lags == (1,)
    assert probe.evidence_level == "lagged_predictive_support"
    pcmci = PredictiveProbeResult(
        "x",
        "y",
        "pcmci",
        0.1,
        0.05,
        1,
        (1,),
        ("z",),
        "ok",
        10,
        "predictive",
        evidence_level="intervention_supported",
    )
    assert pcmci.evidence_level != "intervention_supported"


def test_intervention_result_required_object_and_oee_thresholds():
    result = build_intervention_result("s", [1, 1, 1], [2, 2, 2])
    assert result.evidence_level == "intervention_supported"
    thresholds = OEEClaimThresholds()
    assert thresholds.min_seed_count_research_grade == 30
    report = build_oee_metrics_report(5, 50, {"archive_coverage_slope": 0.1}, shadow_adjusted=False)
    assert report.claim_level == "measurement_only"
    ok = build_oee_metrics_report(
        30,
        1000,
        {name: 1.0 for name in thresholds.required_metrics},
        confidence_intervals={name: (0.0, 1.0) for name in thresholds.required_metrics},
        shadow_adjusted=True,
        persistence_window_observed=thresholds.min_persistence_window_generations,
    )
    assert ok.claim_level == "oee_candidate"


def test_statistical_policy_paired_rules_and_required_claim_inputs():
    policy = StatisticalTestPolicy()
    assert policy.ci_method == "bca_bootstrap"
    assert policy.tier_for_n(7) == "descriptive_only"
    assert choose_paired_test(policy, paired=True) == "paired_permutation"
    assert not validate_statistical_claim_inputs(
        p_value=0.01,
        effect_size=None,
        confidence_interval=(0, 1),
        replay_artifact_digest="r",
        protocol_digest="p",
        claim_gate_decision_digest="c",
    )[0]


def test_translation_profile_digest_policy_update_inheritance_and_proxy_claim():
    profile = build_translation_profile(
        "p",
        "spec",
        [
            TranslationWeight("000", "MOVE_EAST", 2.0, 1, 0),
            TranslationWeight("000", "WAIT", 1.0, 1, 0),
        ],
    )
    assert translation_profile_from_dict(profile.to_dict()).digest == profile.digest
    assert resolve_translation_action("000", "WAIT", profile, TranslationPolicy()) == "MOVE_EAST"
    new_profile, record, remaining = update_translation_profile(
        profile,
        organism_id="o",
        tick=1,
        codon="000",
        new_action="WAIT",
        delta=2.0,
        reason="test",
        atp_learning_available=3.0,
    )
    assert remaining == 2.0
    assert record.atp_learning_cost == 1.0
    child = inherit_translation_profile(new_profile, child_profile_id="child")
    assert child.digest != profile.digest
    proxy = build_semantic_proxy_report(child)
    assert proxy.claim_level == "adaptive_gp_map_proxy"
