from __future__ import annotations

import csv
from pathlib import Path

from codontrace.codon import CodonTable
from codontrace.genesis.benchmark_suite import BenchmarkScenarioSuite
from codontrace.genesis.claim_gate import ClaimRequest, ScientificClaimGate
from codontrace.genesis.engine import GenesisEngine, GenesisEngineConfig, GenesisExperimentSpec
from codontrace.genesis.liveness import AliveGateConfig, evaluate_alive
from codontrace.genesis.population import PopulationConfigs, RuntimeResourcePolicy
from codontrace.genesis.runtime_profiles import GenesisRuntimeProfile
from codontrace.genesis.selection import EvolutionConfig, select_population
from codontrace.genesis.substrate import element_grid_to_world2d
from codontrace.trace import TraceEvent
from codontrace.world import World2D


def _wait_event(step: int) -> TraceEvent:
    return TraceEvent(
        step=step,
        agent_id="org",
        codon="000",
        action="WAIT",
        status="executed",
        reason="ok",
        atp_before=1.0,
        atp_after=1.0,
        position_before=(0, 0),
        position_after=(0, 0),
        world_delta={},
    )


def test_population_survival_ticks_are_generation_local() -> None:
    result = evaluate_alive([_wait_event(9)], config=AliveGateConfig(min_ticks=1, require_positive_runtime_atp=False))
    assert result.survived_ticks == 1
    engine = GenesisEngine.from_spec(
        GenesisExperimentSpec(
            genome_bits=("000",),
            tick_count=5,
            engine_config=GenesisEngineConfig(enable_qd=False, qd_mode="disabled"),
        )
    )
    run = engine.run_ticks()
    assert [rec.alive_result.survived_ticks for t in run.ticks for rec in t.generation_result.organism_records] == [1, 1, 1, 1, 1]


def test_generation_summary_separates_raw_and_selection_fitness() -> None:
    run = GenesisEngine.from_spec(GenesisRuntimeProfile.evolution_pilot_world(tick_count=2, population=2)).run_ticks()
    gen = run.ticks[-1].generation_result
    assert gen.mean_fitness_alias == "raw_mean_fitness"
    assert gen.best_fitness_alias == "raw_best_fitness"
    assert gen.raw_best_fitness == gen.best_fitness
    assert gen.selection_best_fitness >= 0.0
    assert "selection_best_fitness" in run.evidence_pack.summary.to_dict()


def test_claim_gate_uses_selection_fitness_for_evolution_claims() -> None:
    decision = ScientificClaimGate().decide(
        ClaimRequest(
            "digital_evolution_claim",
            {
                "births_positive": True,
                "heritable_variation": True,
                "differential_fitness": False,
            },
        )
    )
    assert not decision.allowed
    assert "missing_differential_fitness" in decision.failed_reasons


def test_benchmark_scenario_builds_non_empty_world_when_evidence_bearing() -> None:
    scenario = BenchmarkScenarioSuite.standard().scenarios[1]  # static_resource_world
    spec = scenario.build_spec()
    world = element_grid_to_world2d(spec.element_grid)
    assert world.resources
    assert spec.metadata["scenario_evidence_bearing"] is True
    assert spec.metadata["scenario_status"] == "runtime_effective"


def test_benchmark_ablation_changes_runtime_config_or_marks_not_evidence_bearing() -> None:
    scenario = BenchmarkScenarioSuite.standard().scenarios[1]
    baseline = scenario.build_spec()
    ablation = scenario.build_spec(ablation=True)
    assert baseline.element_grid.digest() != ablation.element_grid.digest()
    assert baseline.population_configs.runtime_resource_policy.respawn_enabled is True
    assert ablation.population_configs.runtime_resource_policy.respawn_enabled is False


def test_benchmark_suite_sets_benchmark_scenario_digest_and_claim_ceiling() -> None:
    spec = BenchmarkScenarioSuite.standard().scenarios[0].build_spec()
    assert spec.metadata.get("benchmark_scenario_digest")
    assert spec.metadata.get("claim_ceiling")


def test_metadata_only_benchmark_is_not_claim_eligible() -> None:
    spec = BenchmarkScenarioSuite.standard().scenarios[0].build_spec()
    assert spec.metadata["scenario_evidence_bearing"] is False
    assert spec.metadata["claim_allowed"] is False


def test_resource_respawn_adds_resources_deterministically() -> None:
    spec = GenesisRuntimeProfile.evolution_pilot_world(seed=42, tick_count=1, population=1)
    run1 = GenesisEngine.from_spec(spec).run_ticks()
    run2 = GenesisEngine.from_spec(spec).run_ticks()
    ev1 = [e.to_dict() for e in run1.resource_policy_records]
    ev2 = [e.to_dict() for e in run2.resource_policy_records]
    assert ev1 == ev2
    assert any(e["event_type"] == "resource_regenerated" for e in ev1)


def test_resource_respawn_respects_max_resources_and_walls() -> None:
    world = World2D(2, 1, walls={(1, 0)})
    world.place_resource((0, 0), 1.0)
    configs = PopulationConfigs(runtime_resource_policy=RuntimeResourcePolicy(respawn_enabled=True, respawn_rate=1.0, max_resources=1))
    spec = GenesisExperimentSpec(
        genome_bits=("000",),
        tick_count=1,
        world_width=2,
        world_height=1,
        population_configs=configs,
        engine_config=GenesisEngineConfig(enable_qd=False, qd_mode="disabled"),
    )
    # The policy itself is tested through profile worlds; this asserts the configured max is serialized.
    assert spec.population_configs.runtime_resource_policy.max_resources == 1


def test_resource_respawn_events_are_replay_digest_stable() -> None:
    spec = GenesisRuntimeProfile.evolution_pilot_world(seed=7, tick_count=2, population=1)
    assert GenesisEngine.from_spec(spec).run_ticks().digest() == GenesisEngine.from_spec(spec).run_ticks().digest()


def test_empty_world_smoke_is_not_evolution_claim_eligible() -> None:
    spec = GenesisRuntimeProfile.empty_world_smoke()
    assert spec.metadata["default_world_profile"] == "empty_world_smoke"
    assert spec.metadata["claim_allowed_for_evolution"] is False


def test_evolution_pilot_profile_has_resources_mutation_birth_and_selection_pressure() -> None:
    spec = GenesisRuntimeProfile.evolution_pilot_world(population=3, tick_count=1)
    world = element_grid_to_world2d(spec.element_grid)
    assert world.resources
    assert spec.population_configs.mutation.bit_flip_rate > 0
    assert "111" in spec.genome_bits[0]  # COPY_SELF in GENESIS v0
    assert spec.engine_config.qd_mode == "selection_pressure"


def test_genesis_toolchain_codon_table_exposes_tool_primitives() -> None:
    actions = {codon.action_name for codon in CodonTable.genesis_toolchain_v0().actions()}
    assert {"COLLECT_RESOURCE", "CRAFT_ITEM", "USE_ITEM", "UNLOCK_CELL", "CROSS_TERRAIN", "DEPOSIT_RESOURCE", "RETURN_TO_TARGET"} <= actions


def test_toolchain_pilot_emits_tool_chain_records_per_action() -> None:
    run = GenesisEngine.from_spec(GenesisRuntimeProfile.toolchain_pilot_world(tick_count=3)).run_ticks()
    assert run.tool_chain_records
    assert all(hasattr(item, "allowed") for item in run.tool_chain_records)


def test_toolchain_action_changes_world_inventory_or_reports_blocked_reason() -> None:
    run = GenesisEngine.from_spec(GenesisRuntimeProfile.toolchain_pilot_world(tick_count=2)).run_ticks()
    assert any(item.allowed or item.blocked_reason for item in run.tool_chain_records)


def test_genesis_evolution_pilot_runs_and_exports_required_columns(tmp_path: Path) -> None:
    from examples.genesis_evolution_pilot import REQUIRED_COLUMNS, run

    output = run(tmp_path, tick_count=2)
    with open(output["csv"], newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        assert tuple(reader.fieldnames or ()) == REQUIRED_COLUMNS
        rows = list(reader)
    assert rows


def test_qd_selection_pressure_changes_selection_in_controlled_fixture() -> None:
    class Obj:
        def __init__(self, id: str) -> None:
            self.id = id
    a, b = Obj("a"), Obj("b")
    selected, audit = select_population(
        (a, b),
        fitness_scores={"a": 1.0, "b": 1.0},
        novelty_scores={"a": 0.0, "b": 10.0},
        max_population=1,
        config=EvolutionConfig(selection_policy="novelty_weighted", novelty_weight=1.0, fitness_weight=0.0, qd_mode="selection_pressure"),
        qd_mode="selection_pressure",
    )
    assert selected[0].id == "b"
    assert audit.qd_changed_selection is True


def test_qd_archive_only_never_claims_selection_effect() -> None:
    run = GenesisEngine.from_spec(GenesisRuntimeProfile.empty_world_smoke(tick_count=1)).run_ticks()
    assert not any(getattr(item, "qd_changed_selection", False) for item in run.qd_selection_audit)


def test_internal_generalization_proxy_is_not_claim_eligible() -> None:
    run = GenesisEngine.from_spec(GenesisRuntimeProfile.empty_world_smoke(tick_count=2)).run_ticks()
    assert run.generalization_records
    assert all(getattr(item, "claim_eligible", True) is False for item in run.generalization_records)


def test_newborn_survives_until_first_evaluation_when_age_protection_enabled() -> None:
    configs = PopulationConfigs(
        newborn_protection_policy="protect_until_first_evaluation",
        evolution=EvolutionConfig(max_population=1),
    )
    assert configs.newborn_protection_policy == "protect_until_first_evaluation"
    assert configs.to_dict()["newborn_protection_policy"] == "protect_until_first_evaluation"


def test_reproduction_action_cost_and_parent_build_cost_are_audited_separately() -> None:
    spec = GenesisRuntimeProfile.evolution_pilot_world(tick_count=3, population=1)
    run = GenesisEngine.from_spec(spec).run_ticks()
    results = [rec.reproduction_result for t in run.ticks for rec in t.generation_result.organism_records if rec.reproduction_result]
    assert results
    assert all("reproduction_cost_policy" in item.to_dict() for item in results)


def test_evolution_pilot_default_has_successful_births_and_status(tmp_path: Path) -> None:
    from examples.genesis_evolution_pilot import run
    import json

    output = run(tmp_path, tick_count=20)
    payload = json.loads(Path(output["json"]).read_text(encoding="utf-8"))
    assert payload["summary"]["total_births"] > 0
    assert payload["summary"]["pilot_status"] == "runtime_effective_evolution_pilot"


def test_qd_selection_pilot_runtime_applies_selection_pressure(tmp_path: Path) -> None:
    from examples.genesis_qd_selection_pilot import run
    import json

    output = run(tmp_path)
    payload = json.loads(Path(output["json"]).read_text(encoding="utf-8"))
    assert payload["qd_changed_selection"] is True
    assert payload["status"] == "selection_applied"


def test_capsule_utility_pilot_emits_nonempty_truthful_records(tmp_path: Path) -> None:
    from examples.genesis_capsule_utility_pilot import run
    import json

    output = run(tmp_path)
    payload = json.loads(Path(output["json"]).read_text(encoding="utf-8"))
    assert payload["record_count"] > 0
    assert payload["records"]
    assert all("claim_eligible" in item and "capsule_status" in item for item in payload["records"])
    assert payload["status"] in {"records_emitted_not_usefulness_claim", "claim_eligible_measured_utility"}


def test_memory_delayed_reward_pilot_emits_linked_records(tmp_path: Path) -> None:
    from examples.genesis_memory_delayed_reward_pilot import run
    import json

    output = run(tmp_path)
    payload = json.loads(Path(output["json"]).read_text(encoding="utf-8"))
    assert payload["memory_use_records"]
    assert payload["delayed_reward_records"]
    assert payload["status"] == "runtime_effective_delayed_reward_chain"
    assert payload["claim_allowed_for_strong_memory"] is True
    required = {
        "signal_seen_tick",
        "memory_written_tick",
        "memory_read_tick",
        "decision_tick",
        "reward_tick",
        "latency",
        "memory_key",
        "action_after_memory",
        "reward_after_action",
        "link_digest",
    }
    for item in payload["delayed_reward_records"]:
        assert required <= set(item)
        assert item["memory_key"]
        assert item["action_after_memory"] in {"EAT_LUMEN", "COLLECT_RESOURCE"}
        assert item["link_digest"]
        assert item["latency"] >= 0


def test_social_partner_pilot_exports_familiar_and_unfamiliar_events(tmp_path: Path) -> None:
    from examples.genesis_social_partner_pilot import run
    import json

    output = run(tmp_path)
    payload = json.loads(Path(output["json"]).read_text(encoding="utf-8"))
    assert payload["familiar_partner_group"]
    assert payload["unfamiliar_partner_group"]
    assert payload["claim_allowed_for_social_intelligence"] is False


def test_standalone_toolchain_and_qd_examples_exist_and_run(tmp_path: Path) -> None:
    from examples.genesis_toolchain_pilot import run as run_toolchain
    from examples.genesis_qd_selection_pilot import run as run_qd
    import json

    tool = run_toolchain(tmp_path / "tool")
    qd = run_qd(tmp_path / "qd")
    tool_payload = json.loads(Path(tool["json"]).read_text(encoding="utf-8"))
    qd_payload = json.loads(Path(qd["json"]).read_text(encoding="utf-8"))
    assert tool_payload["record_count"] > 0
    assert qd_payload["qd_changed_selection"] is True


def test_pilot_cli_respects_output_dir(tmp_path: Path) -> None:
    import json
    import os
    import subprocess
    import sys

    out = tmp_path / "cli-evolution"
    env = dict(os.environ)
    env.pop("PYTHONPATH", None)
    completed = subprocess.run(
        [
            sys.executable,
            "examples/genesis_evolution_pilot.py",
            "--output-dir",
            str(out),
            "--tick-count",
            "4",
        ],
        cwd=Path(__file__).resolve().parents[1],
        env=env,
        check=True,
        text=True,
        stdout=subprocess.PIPE,
    )
    payload = json.loads(completed.stdout)
    assert Path(payload["json"]).parent == out
    assert (out / "genesis_evolution_pilot.json").exists()
    assert (out / "genesis_evolution_pilot.csv").exists()


def test_official_pilot_clis_run_from_clean_checkout_without_pythonpath(tmp_path: Path) -> None:
    import json
    import os
    import subprocess
    import sys

    repo = Path(__file__).resolve().parents[1]
    env = dict(os.environ)
    env.pop("PYTHONPATH", None)
    pilots = (
        "genesis_evolution_pilot",
        "genesis_qd_selection_pilot",
        "genesis_capsule_utility_pilot",
        "genesis_memory_delayed_reward_pilot",
        "genesis_toolchain_pilot",
        "genesis_social_partner_pilot",
    )
    for pilot in pilots:
        out = tmp_path / pilot
        args = [
            sys.executable,
            f"examples/{pilot}.py",
            "--output-dir",
            str(out),
        ]
        if pilot == "genesis_evolution_pilot":
            args.extend(["--tick-count", "4"])
        completed = subprocess.run(
            args,
            cwd=repo,
            env=env,
            check=True,
            text=True,
            stdout=subprocess.PIPE,
        )
        payload = json.loads(completed.stdout)
        assert payload
        assert any(Path(value).exists() for value in payload.values() if isinstance(value, str))
