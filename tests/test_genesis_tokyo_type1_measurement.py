"""Tokyo Type 1 measurement protocol tests (Channon 2024 steps, pass blocked).

These tests document measurement software capability only. They do not claim
Tokyo Type 1 OEE, open-endedness, intelligence, or Avida replacement.
"""

from __future__ import annotations

from codontrace.errors import ConfigurationError
from codontrace.genesis.claim_gate import ClaimRequest, ScientificClaimGate
from codontrace.genesis.engine import GenesisEngine
from codontrace.genesis.multi_generation import build_multi_generation_evidence_pack
from codontrace.genesis.replay_integrity import build_replay_digest_class_policy
from codontrace.genesis.runtime_profiles import GenesisRuntimeProfile
from codontrace.genesis.tokyo_type1 import (
    CHANNON_2024_MEASUREMENT_STEPS,
    TokyoType1MeasurementProtocol,
    build_tokyo_type1_measurement_protocol,
    evaluate_tokyo_type1_measurement_claim,
    evaluate_tokyo_type1_pass_claim,
)


def test_tokyo_type1_public_api_and_life_loop_digest_pin() -> None:
    import codontrace.genesis as g

    for name in (
        "TokyoType1MeasurementProtocol",
        "build_tokyo_type1_measurement_protocol",
        "evaluate_tokyo_type1_measurement_claim",
        "evaluate_tokyo_type1_pass_claim",
        "CHANNON_2024_MEASUREMENT_STEPS",
    ):
        assert hasattr(g, name)
        assert name in g.__all__
    spec = GenesisRuntimeProfile.life_loop_world(seed=7, tick_count=12, population=6)
    assert spec.digest() == "7d199ae51345872215dbbb0c45cf8f141aacfb4c31d6537eda6de246c0cb7aac"


def test_tokyo_type1_protocol_records_channon_steps_and_blocks_pass() -> None:
    spec = GenesisRuntimeProfile.life_loop_world(seed=7, tick_count=8, population=6)
    result = GenesisEngine.from_spec(spec).run_ticks()
    pack = build_multi_generation_evidence_pack(result, spec=spec)
    protocol = build_tokyo_type1_measurement_protocol(pack)
    assert protocol.claim_ceiling == "tokyo_type1_measurement_only"
    assert protocol.tokyo_type1_passed is False
    assert protocol.to_dict()["tokyo_type1_passed"] is False
    assert protocol.to_dict()["open_endedness_proved"] is False
    assert protocol.persistence_window_t == pack.config.persistence_window_t
    assert protocol.empirical_systematics_shadow_run is False
    assert protocol.shadow_normalization_status == "unavailable"
    assert tuple(step.step_id for step in protocol.steps) == tuple(
        item[0] for item in CHANNON_2024_MEASUREMENT_STEPS
    )
    assert protocol.measurement_status == "measurement_only"
    measured = evaluate_tokyo_type1_measurement_claim(protocol)
    assert measured.allowed is True
    assert measured.final_claim == "tokyo_type1_measurement_only"
    blocked = evaluate_tokyo_type1_pass_claim(protocol)
    assert blocked.allowed is False
    assert "overclaim_alias_forbidden" in blocked.failed_reasons


def test_tokyo_type1_multi_seed_stays_measurement_only_not_passed() -> None:
    spec = GenesisRuntimeProfile.life_loop_world(seed=3, tick_count=6, population=4)
    pack = build_multi_generation_evidence_pack(
        GenesisEngine.from_spec(spec).run_ticks(), spec=spec
    )
    protocol = build_tokyo_type1_measurement_protocol(pack, seed_count=5)
    assert protocol.seed_count == 5
    assert protocol.measurement_status == "multi_seed_measurement_only_still_not_passed"
    assert protocol.claim_ceiling == "tokyo_type1_measurement_only"
    assert protocol.tokyo_type1_passed is False
    decision = evaluate_tokyo_type1_measurement_claim(protocol)
    assert decision.final_claim == "tokyo_type1_measurement_only"
    gate = ScientificClaimGate()
    proved = gate.decide(
        ClaimRequest(
            "tokyo_type1_passed", {"multi_seed_protocol": True, "shadow_run_present": True}
        )
    )
    assert proved.allowed is False


def test_tokyo_type1_constructor_rejects_pass_bits() -> None:
    protocol = build_tokyo_type1_measurement_protocol()
    try:
        TokyoType1MeasurementProtocol(
            steps=protocol.steps,
            seed_count=1,
            persistence_window_t=2,
            activity_observed=False,
            novelty_observed=False,
            shadow_normalization_status="unavailable",
            tokyo_type1_passed=True,
        )
    except ConfigurationError as exc:
        assert "never set tokyo_type1_passed" in str(exc)
    else:
        raise AssertionError("pass bit should be rejected")


def test_tokyo_type1_shadow_hook_does_not_invent_empirical_systematics() -> None:
    from codontrace.genesis.canonical import canonical_digest

    shadow = canonical_digest({"shadow": "caller_supplied"})
    protocol = build_tokyo_type1_measurement_protocol(seed_count=1, shadow_digest=shadow)
    assert protocol.shadow_normalization_status == "hook_recorded_not_empirical_systematics"
    assert protocol.empirical_systematics_shadow_run is False
    try:
        build_tokyo_type1_measurement_protocol(empirical_systematics_shadow_run=True)
    except ConfigurationError as exc:
        assert "empirical" in str(exc).lower()
    else:
        raise AssertionError("invented Empirical systematics run should be rejected")


def test_tokyo_type1_protocol_is_replay_critical() -> None:
    policy = build_replay_digest_class_policy(
        "codontrace.genesis.tokyo_type1.TokyoType1MeasurementProtocol"
    )
    assert policy.replay_critical is True
    assert "digest" in policy.digest_fields
