"""HARD_EXPERIMENT_03 knob + campaign gates. Pins A–E must stay green."""

from __future__ import annotations

from dataclasses import replace

import pytest

from codontrace.errors import ConfigurationError
from codontrace.genesis.canonical import canonical_digest
from codontrace.genesis.engine import GenesisEngine
from codontrace.genesis.hard_experiment_03 import (
    ARMS,
    CLAIM_CEILING,
    PILOT_SEEDS,
    build_hard_experiment_03_spec,
    evaluate_hard_experiment_03_claim,
    evaluate_hard_experiment_03_pilot_gates,
    hard_experiment_03_causal_dag,
    hard_experiment_03_interventions,
    hard_experiment_03_prereg_digest,
    run_hard_experiment_03,
)
from codontrace.genesis.isolation_assay import IsolationAssayConfig, run_isolation_assay
from codontrace.genesis.metrics.division_of_labor import gorelick_nmi
from codontrace.genesis.population import PopulationConfigs
from codontrace.genesis.runtime_profiles import GenesisRuntimeProfile
from codontrace.genesis.task_switch_cost import (
    SWITCH_COST_ATP_HIGH,
    SWITCH_COST_ATP_MODERATE,
    TaskSwitchCostConfig,
    TaskSwitchCostRecord,
    apply_task_switch_cost,
)

LIFE_LOOP_SPEC_DIGEST = "7d199ae51345872215dbbb0c45cf8f141aacfb4c31d6537eda6de246c0cb7aac"
LIFE_LOOP_SNAPSHOT_DIGEST = "76a5e62cb0123b20a089adde25acd1cfb6dc460bdfab52f33ee460533d76f43a"


def test_phase_a_life_loop_digest_pin_unchanged_by_hard_experiment_03() -> None:
    spec = GenesisRuntimeProfile.life_loop_world(seed=7, tick_count=12, population=6)
    result = GenesisEngine.from_spec(spec).run_ticks()
    replay = GenesisEngine.from_spec(spec).run_ticks()
    assert spec.digest() == LIFE_LOOP_SPEC_DIGEST
    assert result.digest() == replay.digest()
    assert result.snapshot.digest() == LIFE_LOOP_SNAPSHOT_DIGEST


def test_he03_knobs_default_off_omit_from_population_configs_dict() -> None:
    payload = PopulationConfigs().to_dict()
    assert "task_switch_cost" not in payload


def test_he03_knobs_enabled_change_digest() -> None:
    off = PopulationConfigs()
    on = replace(
        PopulationConfigs(),
        task_switch_cost=TaskSwitchCostConfig(
            enabled=True, switch_cost_atp=SWITCH_COST_ATP_MODERATE
        ),
    )
    assert canonical_digest(off.to_dict()) != canonical_digest(on.to_dict())
    assert "task_switch_cost" in on.to_dict()


def test_gorelick_nmi_specialists_have_high_d_sym() -> None:
    samples = [
        ("a", "TASK_A"),
        ("a", "TASK_A"),
        ("b", "TASK_B"),
        ("b", "TASK_B"),
    ]
    result = gorelick_nmi(samples)
    assert result.matrix_degenerate is False
    assert result.d_sym == pytest.approx(1.0)
    assert result.collective_intelligence is False


def test_gorelick_nmi_empty_is_degenerate() -> None:
    result = gorelick_nmi(())
    assert result.matrix_degenerate is True
    assert result.d_sym == 0.0


def test_task_switch_cost_charges_on_switch() -> None:
    class _ATP:
        runtime_available = 10.0

        def debit_runtime(self, cost: float, **kwargs: object) -> int:
            self.runtime_available = round(self.runtime_available - float(cost), 10)
            return 1

    config = TaskSwitchCostConfig(enabled=True, switch_cost_atp=SWITCH_COST_ATP_HIGH)
    atp = _ATP()
    task, record = apply_task_switch_cost(
        tick=1,
        organism_id="o1",
        action="EMIT_NEXUS",
        previous_task="TASK_A",
        config=config,
        atp_state=atp,
    )
    assert task == "TASK_B"
    assert isinstance(record, TaskSwitchCostRecord)
    assert record.charged is True
    assert atp.runtime_available == pytest.approx(9.5)


def test_task_switch_cost_off_is_noop() -> None:
    class _ATP:
        runtime_available = 10.0

        def debit_runtime(self, cost: float, **kwargs: object) -> int:
            raise AssertionError("must not debit when disabled")

    task, record = apply_task_switch_cost(
        tick=1,
        organism_id="o1",
        action="EMIT_NEXUS",
        previous_task="TASK_A",
        config=TaskSwitchCostConfig(enabled=False),
        atp_state=_ATP(),
    )
    assert task is None
    assert record is None


def test_isolation_assay_secondary_drop() -> None:
    result = run_isolation_assay(
        group_scores={"a": 1.0, "b": 0.8},
        solo_scores={"a": 0.2, "b": 0.4},
        config=IsolationAssayConfig(enabled=True),
    )
    assert result.enabled is True
    assert result.mean_isolation_drop == pytest.approx(0.6)
    assert result.collective_intelligence is False
    assert result.claim_ceiling == "runtime_observation"


def test_he03_overlay_does_not_alias_default_life_loop_digest() -> None:
    overlay = build_hard_experiment_03_spec(
        seed=7, arm="cost_high", tick_count=4, population=4
    )
    pinned = GenesisRuntimeProfile.life_loop_world(seed=7, tick_count=12, population=6)
    assert overlay.digest() != pinned.digest()
    assert pinned.digest() == LIFE_LOOP_SPEC_DIGEST


def test_he03_interventions_cover_all_arms() -> None:
    mapped = hard_experiment_03_interventions()
    assert {item.arm for item in mapped} == set(ARMS)


def test_he03_claim_ceiling_is_runtime_observation() -> None:
    assert CLAIM_CEILING == "runtime_observation"
    dag = hard_experiment_03_causal_dag()
    assert dag["claim_ceiling"] == "runtime_observation"
    assert dag["collective_intelligence"] is False


def test_he03_prereg_digest_is_real() -> None:
    digest = hard_experiment_03_prereg_digest()
    assert isinstance(digest, str) and len(digest) == 64


def test_he03_smoke_campaign_runs_and_stays_at_runtime_observation() -> None:
    campaign = run_hard_experiment_03(
        seeds=(11,), scale="smoke", tick_count=2, population=4
    )
    claim = evaluate_hard_experiment_03_claim(campaign)
    assert claim["claim_ceiling"] == "runtime_observation"
    assert claim["collective_intelligence"] is False
    assert claim["intelligence"] is False
    assert claim["agi"] is False
    gates = evaluate_hard_experiment_03_pilot_gates(campaign)
    assert "overall_pass" in gates or "cleared_for_research" in gates
    assert gates.get("cleared_for_research") is False
    assert campaign.claim_ceiling == "runtime_observation"


def test_invalid_task_switch_overlap_raises() -> None:
    with pytest.raises(ConfigurationError):
        TaskSwitchCostConfig(
            enabled=True,
            task_a_actions=("EAT_LUMEN",),
            task_b_actions=("EAT_LUMEN",),
        )


def test_pilot_seeds_are_1000_to_1009() -> None:
    assert PILOT_SEEDS == tuple(range(1000, 1010))


def test_he03_dual_task_overlay_enables_switches_and_refuses_ci() -> None:
    """Dual-action genomes + persisted last_task make switches observable."""

    campaign = run_hard_experiment_03(
        seeds=(1000, 1001), scale="smoke", tick_count=8, population=6
    )
    assert campaign.assay_failed is False
    assert campaign.collective_intelligence_candidate is False
    assert campaign.claim_ceiling == CLAIM_CEILING
    cost_high = [rec.cost_high for rec in campaign.seed_records]
    assert all(item.n_switches > 0 for item in cost_high)
    assert all(item.matrix_degenerate is False for item in cost_high)
    assert len(campaign.paired_contrasts) == 3
    claim = evaluate_hard_experiment_03_claim(campaign)
    assert claim["collective_intelligence"] is False
    assert claim["decision_rule_passed"] is False


def test_he03_last_task_persists_across_ticks() -> None:
    from codontrace.genesis.engine import GenesisEngine
    from codontrace.genesis.hard_experiment_03 import build_hard_experiment_03_spec

    spec = build_hard_experiment_03_spec(
        seed=42, arm="cost_moderate", tick_count=12, population=4
    )
    result = GenesisEngine.from_spec(spec).run_ticks()
    n_switches = 0
    for tick in result.ticks:
        generation = tick.generation_result
        if generation is None:
            continue
        n_switches += len(generation.task_switch_cost_records or ())
    assert n_switches > 0
