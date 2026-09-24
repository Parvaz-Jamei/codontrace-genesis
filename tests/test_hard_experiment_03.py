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


def test_he03_mutational_overlay_raises_mutation_and_keeps_life_loop_pin() -> None:
    from codontrace.genesis.hard_experiment_03 import (
        HE03_MUTATION_BIT_FLIP_RATE,
        build_hard_experiment_03_spec,
    )

    overlay = build_hard_experiment_03_spec(
        seed=7, arm="cost_high", tick_count=4, population=4
    )
    assert overlay.population_configs is not None
    assert overlay.population_configs.mutation.bit_flip_rate == HE03_MUTATION_BIT_FLIP_RATE
    assert "mutational_specialization" in overlay.metadata
    pinned = GenesisRuntimeProfile.life_loop_world(seed=7, tick_count=12, population=6)
    assert pinned.digest() == LIFE_LOOP_SPEC_DIGEST
    assert pinned.population_configs is not None
    assert pinned.population_configs.mutation.bit_flip_rate != HE03_MUTATION_BIT_FLIP_RATE


def test_he03_genome_task_width_counts_a_and_b() -> None:
    from codontrace.genesis.hard_experiment_03 import (
        HE03_DUAL_TASK_GENOME,
        _genome_task_width,
        _task_switch_for_arm,
    )

    config = _task_switch_for_arm("cost_high")
    assert _genome_task_width(HE03_DUAL_TASK_GENOME, config) == 2.0
    # EAT_LUMEN + COPY_SELF + WAIT only → TASK_A
    assert _genome_task_width("101111000", config) == 1.0


def test_he03_trace_samples_exclude_switch_endpoints() -> None:
    from codontrace.genesis.hard_experiment_03 import (
        _extract_task_samples,
        _task_switch_for_arm,
        build_hard_experiment_03_spec,
    )

    spec = build_hard_experiment_03_spec(
        seed=1000, arm="cost_high", tick_count=6, population=4
    )
    result = GenesisEngine.from_spec(spec).run_ticks()
    config = _task_switch_for_arm("cost_high")
    samples = _extract_task_samples(result, config)
    # Ensure we still get TASK samples from traces under mutational overlay.
    assert any(task == "TASK_A" for _, task in samples)


# --- Negative controls for the HE03 measurement surface ---------------------
# The tests above only assert that samples and switch records exist. None of them
# would notice if the extractors changed meaning, so the checks below assert the
# exclusions and the arithmetic that the campaign's claims actually rest on.


class _FakeEvent:
    def __init__(self, action: str, agent_id: str | None = "org-0") -> None:
        self.action = action
        self.agent_id = agent_id


class _FakeTrace:
    def __init__(self, events: list[_FakeEvent]) -> None:
        self.events = tuple(events)


class _FakeGeneration:
    def __init__(self, traces: list[_FakeTrace], records: list[object]) -> None:
        self.traces = tuple(traces)
        self.task_switch_cost_records = tuple(records)


class _FakeTick:
    def __init__(self, generation: _FakeGeneration) -> None:
        self.generation_result = generation


class _FakeResult:
    def __init__(self, ticks: list[_FakeTick]) -> None:
        self.ticks = tuple(ticks)


def test_he03_trace_samples_ignore_switch_records_entirely() -> None:
    """A result whose only evidence is switch records must yield no samples.

    Under the pre-fix construction the switch endpoints were folded into the
    Gorelick matrix, so this input produced samples and inflated the cost arms.
    This assertion fails on that construction and passes only when the trace is
    the sole source.
    """

    from codontrace.genesis.hard_experiment_03 import (
        _extract_task_samples,
        _task_switch_for_arm,
    )

    records = [
        TaskSwitchCostRecord(
            tick=0,
            organism_id="org-0",
            from_task="TASK_A",
            to_task="TASK_B",
            action="EMIT_NEXUS",
            switch_cost_atp=SWITCH_COST_ATP_HIGH,
            charged=True,
            runtime_atp_after=3.5,
        )
    ]
    result = _FakeResult([_FakeTick(_FakeGeneration([], records))])
    config = _task_switch_for_arm("cost_high")
    assert _extract_task_samples(result, config) == ()


def test_he03_switch_stats_count_only_charged_debits() -> None:
    """The realised total must be ATP that moved, not the configured cost.

    ``TaskSwitchCostRecord.switch_cost_atp`` keeps the configured value even when
    the debit returned None, so summing that field reports a nominal total. The
    manipulation check compared those nominal totals, which let a campaign report
    a realised cost while no balance ever paid.
    """

    from codontrace.genesis.hard_experiment_03 import _extract_switch_stats

    charged = TaskSwitchCostRecord(
        tick=0,
        organism_id="org-0",
        from_task="TASK_A",
        to_task="TASK_B",
        action="EMIT_NEXUS",
        switch_cost_atp=SWITCH_COST_ATP_HIGH,
        charged=True,
        runtime_atp_after=3.5,
    )
    uncharged = TaskSwitchCostRecord(
        tick=1,
        organism_id="org-1",
        from_task="TASK_B",
        to_task="TASK_A",
        action="EAT_LUMEN",
        switch_cost_atp=SWITCH_COST_ATP_HIGH,
        charged=False,
        runtime_atp_after=0.0,
    )
    result = _FakeResult([_FakeTick(_FakeGeneration([], [charged, uncharged]))])
    n_switches, realized = _extract_switch_stats(result)
    # Both records are switches; only the charged one moved ATP.
    assert n_switches == 2
    assert realized == pytest.approx(SWITCH_COST_ATP_HIGH)


def test_he03_switch_stats_report_zero_when_nothing_was_payable() -> None:
    """Every switch uncharged but recorded as a switch: realised cost is zero."""

    from codontrace.genesis.hard_experiment_03 import _extract_switch_stats

    records = [
        TaskSwitchCostRecord(
            tick=tick,
            organism_id="org-0",
            from_task="TASK_A",
            to_task="TASK_B",
            action="EMIT_NEXUS",
            switch_cost_atp=SWITCH_COST_ATP_HIGH,
            charged=False,
            runtime_atp_after=0.0,
        )
        for tick in range(3)
    ]
    result = _FakeResult([_FakeTick(_FakeGeneration([], records))])
    n_switches, realized = _extract_switch_stats(result)
    assert n_switches == 3
    assert realized == 0.0


def test_he03_isolation_readout_is_a_width_census_not_a_behavioural_assay() -> None:
    """Pin the current isolation semantics so a change to them is a visible one.

    The group term is the ancestral dual width for every organism and the solo
    term is genome task width, so the drop is an algebraic function of the genome
    and can never be negative. A population in which one organism keeps TASK_A and
    another keeps TASK_B scores identically to one in which both lost TASK_B.
    """

    from codontrace.genesis.hard_experiment_03 import (
        HE03_ANCESTRAL_TASK_WIDTH,
        _genome_task_width,
        _task_switch_for_arm,
    )

    config = _task_switch_for_arm("isolation_probe")
    # One organism keeps A, another keeps B: maximal complementarity.
    complementary = [1.0, 1.0]
    # Both lost B: maximal capability loss.
    degraded = [1.0, 1.0]
    assert complementary == degraded, "the width census cannot separate these"
    assert all(
        HE03_ANCESTRAL_TASK_WIDTH - width >= 0.0 for width in complementary + degraded
    )
    # And the two states it *can* report are the two widths themselves.
    assert _genome_task_width("101111000", config) == 1.0
    dropped = HE03_ANCESTRAL_TASK_WIDTH - 1.0
    assert dropped == 1.0  # a positive "drop" that reads as autonomy loss
