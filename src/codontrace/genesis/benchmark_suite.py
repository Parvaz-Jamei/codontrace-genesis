"""Stable benchmark scenario suite for GENESIS scientific runs."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from dataclasses import dataclass, replace

from codontrace._types import JsonValue
from codontrace.codon import CodonTable
from codontrace.genesis.engine import GenesisEngine, GenesisEngineConfig, GenesisExperimentSpec, GenesisRunResult
from codontrace.genesis.population import MutationConfig, PopulationConfigs, ReproductionConfig, RuntimeResourcePolicy
from codontrace.genesis.selection import EvolutionConfig
from codontrace.genesis.substrate import world2d_to_element_grid
from codontrace.world import World2D, WorldObject


@dataclass(frozen=True, slots=True)
class BaselineConfig:
    seed: int = 1
    tick_count: int = 5

    def to_dict(self) -> dict[str, JsonValue]:
        return {"seed": self.seed, "tick_count": self.tick_count}


@dataclass(frozen=True, slots=True)
class AblationConfig:
    disabled_components: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, JsonValue]:
        return {"disabled_components": list(self.disabled_components)}


@dataclass(frozen=True, slots=True)
class ScenarioBehaviorSpec:
    scenario_id: str
    scenario_status: str = "metadata_only_not_evidence_bearing"
    world_builder: str = "default_world2d"
    world_config: dict[str, JsonValue] | None = None
    resource_policy: str = "none"
    hazard_policy: str = "none"
    obstacle_policy: str = "none"
    novelty_requirement: bool = False
    qd_mode: str = "archive_only"
    enabled_components: tuple[str, ...] = ()
    disabled_components: tuple[str, ...] = ()
    reward_policy: str = "default"
    requires_population_min: int = 1
    claim_ceiling: str = "foundation_engine"
    evidence_bearing: bool = False

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "scenario_id": self.scenario_id,
            "scenario_status": self.scenario_status,
            "world_builder": self.world_builder,
            "world_config": dict(sorted((self.world_config or {}).items())),
            "resource_policy": self.resource_policy,
            "hazard_policy": self.hazard_policy,
            "obstacle_policy": self.obstacle_policy,
            "novelty_requirement": self.novelty_requirement,
            "qd_mode": self.qd_mode,
            "enabled_components": list(self.enabled_components),
            "disabled_components": list(self.disabled_components),
            "reward_policy": self.reward_policy,
            "requires_population_min": self.requires_population_min,
            "claim_ceiling": self.claim_ceiling,
            "evidence_bearing": self.evidence_bearing,
        }

    def digest(self) -> str:
        return _digest(self.to_dict())


@dataclass(frozen=True, slots=True)
class BenchmarkScenario:
    scenario_id: str
    description: str
    baseline_config: BaselineConfig
    ablation_config: AblationConfig

    def behavior_spec(self, *, ablation: bool = False) -> ScenarioBehaviorSpec:
        return _scenario_behavior_spec(self.scenario_id, self.ablation_config if ablation else None)

    def build_spec(self, base_spec: GenesisExperimentSpec | None = None, *, ablation: bool = False) -> GenesisExperimentSpec:
        spec = base_spec or GenesisExperimentSpec()
        by_id = {item.scenario_id: item for item in benchmark_v2_specs()}
        scenario_spec = by_id.get(self.scenario_id)
        behavior = self.behavior_spec(ablation=ablation)
        engine_config = _apply_behavior_engine_toggles(spec.engine_config, behavior)
        metadata = {
            **spec.metadata,
            "benchmark_scenario": self.scenario_id,
            "benchmark_scenario_digest": None if scenario_spec is None else scenario_spec.digest(),
            "claim_ceiling": "foundation_engine" if scenario_spec is None else scenario_spec.claim_ceiling,
            "scenario_runtime_status": behavior.scenario_status,
            "scenario_evidence_bearing": behavior.evidence_bearing,
            "scenario_behavior_spec_digest": behavior.digest(),
            "world_builder_digest": _digest({"world_builder": behavior.world_builder, "world_config": behavior.world_config or {}}),
            "runtime_toggles_digest": _digest({
                "enabled_components": list(behavior.enabled_components),
                "disabled_components": list(behavior.disabled_components),
                "qd_mode": behavior.qd_mode,
            }),
            "ablation_effective": bool(ablation and behavior.disabled_components),
            "ablation_blocked_reason": None if (not ablation or behavior.disabled_components) else "component_toggle_not_implemented",
            "claim_allowed": behavior.evidence_bearing and behavior.scenario_status == "measured",
        }
        if ablation:
            metadata["ablation"] = ",".join(self.ablation_config.disabled_components)
        base = replace(
            spec,
            seed=self.baseline_config.seed,
            tick_count=self.baseline_config.tick_count,
            engine_config=engine_config,
            metadata=metadata,
        )
        return _apply_behavior_runtime_spec(base, behavior, ablation=ablation)

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "scenario_id": self.scenario_id,
            "description": self.description,
            "baseline_config": self.baseline_config.to_dict(),
            "ablation_config": self.ablation_config.to_dict(),
        }

    def digest(self) -> str:
        return _digest(self.to_dict())


@dataclass(frozen=True, slots=True)
class BenchmarkRunResult:
    scenario_id: str
    baseline_result: GenesisRunResult
    ablation_result: GenesisRunResult

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "scenario_id": self.scenario_id,
            "baseline_manifest_digest": self.baseline_result.manifest.digest(),
            "baseline_replay_digest": self.baseline_result.replay_bundle.digest(),
            "baseline_evidence_digest": self.baseline_result.evidence_pack.digest(),
            "ablation_manifest_digest": self.ablation_result.manifest.digest(),
            "ablation_replay_digest": self.ablation_result.replay_bundle.digest(),
            "ablation_evidence_digest": self.ablation_result.evidence_pack.digest(),
        }

    def digest(self) -> str:
        return _digest(self.to_dict())


@dataclass(frozen=True, slots=True)
class BenchmarkComparisonReport:
    suite_id: str
    run_digests: tuple[str, ...]
    scenario_count: int

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "suite_id": self.suite_id,
            "run_digests": list(self.run_digests),
            "scenario_count": self.scenario_count,
        }

    def digest(self) -> str:
        return _digest(self.to_dict())


@dataclass(frozen=True, slots=True)
class BenchmarkScenarioSuite:
    suite_id: str
    scenarios: tuple[BenchmarkScenario, ...]

    @classmethod
    def standard(cls) -> BenchmarkScenarioSuite:
        return cls("genesis_standard_science_suite_v2", benchmark_v2_scenarios())

    def scenario_specs(self) -> tuple[BenchmarkScenarioSpec, ...]:
        by_id = {spec.scenario_id: spec for spec in benchmark_v2_specs()}
        return tuple(
            by_id[item.scenario_id] for item in self.scenarios if item.scenario_id in by_id
        )

    def run(
        self, base_spec: GenesisExperimentSpec | None = None
    ) -> tuple[tuple[BenchmarkRunResult, ...], BenchmarkComparisonReport]:
        results: list[BenchmarkRunResult] = []
        for scenario in self.scenarios:
            baseline_spec = scenario.build_spec(base_spec)
            baseline = GenesisEngine.from_spec(baseline_spec).run_ticks()
            ablation_spec = scenario.build_spec(base_spec, ablation=True)
            ablation = GenesisEngine.from_spec(ablation_spec).run_ticks()
            results.append(BenchmarkRunResult(scenario.scenario_id, baseline, ablation))
        report = BenchmarkComparisonReport(
            self.suite_id, tuple(result.digest() for result in results), len(results)
        )
        return tuple(results), report

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "suite_id": self.suite_id,
            "scenarios": [scenario.to_dict() for scenario in self.scenarios],
        }

    def digest(self) -> str:
        return _digest(self.to_dict())


def _digest(payload: Mapping[str, JsonValue]) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


@dataclass(frozen=True, slots=True)
class BenchmarkScenarioSpec:
    """Benchmark v2 metadata required before strong statistical claims."""

    scenario_id: str
    purpose: str
    expected_signal: str
    baseline_config_digest: str
    treatment_config_digest: str | None
    required_metrics: tuple[str, ...]
    min_seed_policy: str
    claim_ceiling: str

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "scenario_id": self.scenario_id,
            "purpose": self.purpose,
            "expected_signal": self.expected_signal,
            "baseline_config_digest": self.baseline_config_digest,
            "treatment_config_digest": self.treatment_config_digest,
            "required_metrics": list(self.required_metrics),
            "min_seed_policy": self.min_seed_policy,
            "claim_ceiling": self.claim_ceiling,
        }

    def digest(self) -> str:
        return _digest(self.to_dict())

    def build_experiment_spec(self, *, seed: int = 1, tick_count: int = 3) -> GenesisExperimentSpec:
        behavior = _scenario_behavior_spec(self.scenario_id, None)
        return GenesisExperimentSpec(
            seed=seed,
            tick_count=tick_count,
            engine_config=_apply_behavior_engine_toggles(GenesisEngineConfig(), behavior),
            metadata={
                "benchmark_scenario": self.scenario_id,
                "benchmark_scenario_digest": self.digest(),
                "claim_ceiling": self.claim_ceiling,
                "scenario_runtime_status": behavior.scenario_status,
                "scenario_evidence_bearing": behavior.evidence_bearing,
                "scenario_behavior_spec_digest": behavior.digest(),
                "claim_allowed": behavior.evidence_bearing and behavior.scenario_status == "measured",
            },
        )


def _scenario_behavior_spec(
    scenario_id: str, ablation_config: AblationConfig | None
) -> ScenarioBehaviorSpec:
    disabled = tuple(ablation_config.disabled_components) if ablation_config is not None else ()
    component_toggle = "component_toggle" in disabled
    if scenario_id == "empty_world_sanity":
        return ScenarioBehaviorSpec(
            scenario_id=scenario_id,
            scenario_status="metadata_only_not_evidence_bearing",
            world_builder="empty_world_smoke",
            enabled_components=("deterministic_replay",),
            disabled_components=disabled,
            evidence_bearing=False,
            reward_policy="smoke_only",
            claim_ceiling="foundation_engine",
        )
    if scenario_id in {"static_resource_world", "known_resource_gate_world", "environmental_shift_translation_world"}:
        return ScenarioBehaviorSpec(
            scenario_id=scenario_id,
            scenario_status="measured",
            world_builder="resource_fixture_world2d",
            world_config={"resources": [[0, 0, 2.0], [1, 0, 2.0]], "respawn": True},
            resource_policy="static_lumen_with_optional_respawn",
            enabled_components=("resource_runtime",),
            disabled_components=disabled,
            reward_policy="resource_gain",
            requires_population_min=1,
            claim_ceiling="experimental_engine",
            evidence_bearing=True,
        )
    if scenario_id in {"resource_competition_world", "birth_pressure_world"}:
        return ScenarioBehaviorSpec(
            scenario_id=scenario_id,
            scenario_status="measured",
            world_builder="resource_competition_birth_pressure_world2d",
            world_config={"resources": [[0, 0, 2.0], [1, 0, 2.0]], "capacity": 4},
            resource_policy="limited_lumen_competition",
            enabled_components=("resource_runtime", "reproduction", "mutation"),
            disabled_components=disabled,
            reward_policy="birth_resource_pressure",
            requires_population_min=4,
            claim_ceiling="digital_evolution_claim",
            evidence_bearing=True,
        )
    if scenario_id in {"deceptive_resource_world", "novelty_required_maze_world"}:
        return ScenarioBehaviorSpec(
            scenario_id=scenario_id,
            scenario_status="measured",
            world_builder="maze_qd_fixture_world2d",
            world_config={"walls": [[2, 0], [2, 1], [2, 2]], "resources": [[4, 0, 4.0]]},
            resource_policy="sparse_lumen",
            obstacle_policy="maze_walls",
            novelty_requirement=True,
            qd_mode="disabled" if component_toggle else "selection_pressure",
            enabled_components=() if component_toggle else ("qd_selection_pressure", "resource_runtime"),
            disabled_components=disabled or (),
            evidence_bearing=not component_toggle,
            reward_policy="novelty_selection_pressure_required",
            requires_population_min=4,
            claim_ceiling="active_qd_supported",
        )
    if scenario_id in {"capsule_transfer_world", "known_capsule_transfer_world", "multi_agent_stigmergy_world"}:
        return ScenarioBehaviorSpec(
            scenario_id=scenario_id,
            scenario_status="measured",
            world_builder="multi_agent_capsule_fixture_world2d",
            world_config={"resources": [[0, 0, 2.0], [1, 0, 2.0]], "population": 2},
            resource_policy="shared_lumen",
            enabled_components=() if component_toggle else ("capsules", "multi_agent"),
            disabled_components=disabled or (),
            evidence_bearing=not component_toggle,
            reward_policy="capsule_transfer_records_required",
            requires_population_min=2,
            claim_ceiling="experimental_engine",
        )
    if scenario_id == "toolchain_unlock_world":
        return ScenarioBehaviorSpec(
            scenario_id=scenario_id,
            scenario_status="measured",
            world_builder="toolchain_fixture_world2d",
            world_config={"objects": ["wood", "stone", "key"], "door": True},
            resource_policy="tool_objects",
            enabled_components=("toolchain",),
            disabled_components=disabled,
            reward_policy="tool_chain_score",
            claim_ceiling="experimental_engine",
            evidence_bearing=True,
        )
    if scenario_id in {"known_action_delayed_effect_world", "adf_usefulness_world"}:
        return ScenarioBehaviorSpec(
            scenario_id=scenario_id,
            scenario_status="metadata_only_not_evidence_bearing" if component_toggle else "measured",
            world_builder="delayed_or_adf_fixture_world2d",
            world_config={"resources": [[0, 0, 2.0]]},
            enabled_components=() if component_toggle else ("memory", "adf"),
            disabled_components=disabled,
            evidence_bearing=not component_toggle,
            reward_policy="delayed_effect_or_adf_runtime_required",
            claim_ceiling="experimental_engine",
        )
    return ScenarioBehaviorSpec(
        scenario_id=scenario_id,
        disabled_components=disabled,
        evidence_bearing=False,
    )


def _apply_behavior_runtime_spec(
    spec: GenesisExperimentSpec, behavior: ScenarioBehaviorSpec, *, ablation: bool = False
) -> GenesisExperimentSpec:
    """Attach a small real World2D/profile fixture when a benchmark is evidence-bearing."""

    if not behavior.evidence_bearing:
        metadata = {
            **spec.metadata,
            "behavior_digest_equal_baseline_treatment": True if ablation else False,
            "claim_allowed": False,
        }
        return replace(spec, metadata=metadata)
    world = _build_behavior_world(behavior)
    component_toggle = ablation and "component_toggle" in behavior.disabled_components
    if component_toggle and "resource_runtime" in behavior.enabled_components:
        world.resources.clear()
    population_min = max(1, behavior.requires_population_min)
    genome_bits = spec.genome_bits
    codon_table = spec.codon_table
    if "toolchain" in behavior.enabled_components:
        codon_table = CodonTable.genesis_toolchain_v0()
        genome_bits = ("011001110001100111001101",)  # collect/craft-ish smoke sequence
    elif population_min > len(genome_bits):
        genome_bits = tuple(genome_bits[i % len(genome_bits)] for i in range(population_min))
    pop_cfg = spec.population_configs or PopulationConfigs(
        reproduction=spec.reproduction_config or ReproductionConfig(max_population=max(spec.population_max, population_min)),
        mutation=spec.mutation_config or MutationConfig(bit_flip_rate=0.0),
        evolution=EvolutionConfig(max_population=max(spec.population_max, population_min), qd_mode=behavior.qd_mode),
        qd_mode=behavior.qd_mode,
    )
    if behavior.resource_policy not in {"none", "tool_objects"}:
        pop_cfg = replace(
            pop_cfg,
            runtime_resource_policy=RuntimeResourcePolicy(
                respawn_enabled=not component_toggle,
                respawn_rate=1.0 if not component_toggle else 0.0,
                max_resources=max(1, len(world.resources) + 2),
                amount=2.0,
                status="runtime_effective_default_off" if not component_toggle else "disabled_by_config",
            ),
        )
    metadata = {
        **spec.metadata,
        "scenario_status": "runtime_effective",
        "behavior_digest_equal_baseline_treatment": False if ablation else False,
        "ablation_effective": bool(ablation and behavior.disabled_components),
        "claim_allowed": not (component_toggle and not behavior.enabled_components),
    }
    return replace(
        spec,
        genome_bits=genome_bits,
        population_max=max(spec.population_max, population_min),
        world_width=world.width,
        world_height=world.height,
        element_grid=world2d_to_element_grid(world),
        substrate_bridge_mode="element_grid_source",
        population_configs=pop_cfg,
        codon_table=codon_table,
        metadata=metadata,
    )


def _build_behavior_world(behavior: ScenarioBehaviorSpec) -> World2D:
    width = 5 if "maze" in behavior.world_builder or "qd" in behavior.world_builder else 4
    height = 4
    world = World2D(width, height)
    for item in (behavior.world_config or {}).get("walls", []):
        if isinstance(item, list) and len(item) >= 2:
            world.set_cell((int(item[0]), int(item[1])), World2D.WALL)
    for item in (behavior.world_config or {}).get("resources", []):
        if isinstance(item, list) and len(item) >= 3:
            world.place_resource((int(item[0]), int(item[1])), float(item[2]))
    if "toolchain" in behavior.enabled_components:
        world.add_object((0, 0), WorldObject("wood", metadata={"item": "wood"}))
        world.add_object((0, 0), WorldObject("stone", metadata={"item": "stone"}))
        world.add_object((0, 0), WorldObject("key", metadata={"item": "key"}))
    if not world.resources and behavior.resource_policy not in {"none", "tool_objects"}:
        world.place_resource((0, 0), 2.0)
    return world

def _apply_behavior_engine_toggles(
    engine_config: GenesisEngineConfig, behavior: ScenarioBehaviorSpec
) -> GenesisEngineConfig:
    disable = set(behavior.disabled_components)
    cfg = engine_config
    if "component_toggle" in disable:
        # Generic v2 ablation: disable the component that the scenario actually names,
        # otherwise report non-evidence metadata in the behavior spec.
        if "capsules" in behavior.enabled_components:
            disable.add("capsules")
        if "qd_selection_pressure" in behavior.enabled_components:
            disable.add("qd")
    if "capsules" in disable:
        cfg = replace(cfg, enable_capsules=False)
    if "qd" in disable or behavior.qd_mode == "disabled":
        cfg = replace(cfg, enable_qd=False, qd_mode="disabled")
    elif behavior.qd_mode == "selection_pressure":
        cfg = replace(cfg, enable_qd=True, qd_mode="selection_pressure")
    if "memory" in disable:
        cfg = replace(cfg, enable_memory=False)
    if "causal_graph" in disable:
        cfg = replace(cfg, enable_causal_graph=False)
    return cfg


_V2_SCENARIOS: tuple[tuple[str, str, str, tuple[str, ...], str], ...] = (
    (
        "empty_world_sanity",
        "Sanity check for deterministic empty-world survival.",
        "stable_replay",
        ("survival_ticks",),
        "foundation_engine",
    ),
    (
        "static_resource_world",
        "Static resource acquisition baseline.",
        "resource_gain",
        ("resource_gain", "fitness"),
        "experimental_engine",
    ),
    (
        "deceptive_resource_world",
        "Objective deception scaffold for novelty-sensitive search.",
        "novelty_vs_fitness",
        ("novelty_score", "fitness"),
        "QD_search_supported",
    ),
    (
        "novelty_required_maze_world",
        "Maze-like novelty pressure benchmark spec.",
        "persistent_novelty",
        ("archive_coverage", "behavior_entropy"),
        "QD_search_supported",
    ),
    (
        "variable_genome_bloat_trap",
        "Reserved benchmark for variable genome bloat penalties.",
        "bloat_penalty",
        ("genome_length", "fitness"),
        "continuous_fitness_supported",
    ),
    (
        "adf_usefulness_world",
        "Reserved benchmark for ADF usefulness controls.",
        "adf_utility",
        ("ADF_usage", "fitness"),
        "ADF_pattern_candidate",
    ),
    (
        "known_resource_gate_world",
        "Known resource gate for causal validation.",
        "resource_gate",
        ("causal_prediction_accuracy",),
        "causal_association_supported",
    ),
    (
        "known_action_delayed_effect_world",
        "Known delayed action-effect benchmark spec.",
        "delayed_effect",
        ("prediction_gain",),
        "causal_association_supported",
    ),
    (
        "capsule_transfer_world",
        "Capsule transfer ON/OFF benchmark spec.",
        "capsule_effect",
        ("capsule_adoption_success_rate",),
        "capsule_transfer_effect_supported",
    ),
    (
        "known_capsule_transfer_world",
        "Ground-truth causal capsule transfer benchmark with paired baseline/treatment metadata.",
        "known_capsule_effect",
        ("capsule_adoption_success_rate", "effect_size", "confidence_interval"),
        "intervention_supported",
    ),
    (
        "environmental_shift_translation_world",
        "Translation robustness under environmental shift.",
        "translation_shift",
        ("survival_ticks", "resource_gain"),
        "experimental_engine",
    ),
    (
        "multi_agent_stigmergy_world",
        "Multi-agent stigmergy benchmark spec.",
        "stigmergy_signal",
        ("capsules_emitted", "capsules_read"),
        "capsule_transfer_supported",
    ),
)


def benchmark_v2_specs() -> tuple[BenchmarkScenarioSpec, ...]:
    specs: list[BenchmarkScenarioSpec] = []
    for index, (scenario_id, purpose, signal, metrics, ceiling) in enumerate(_V2_SCENARIOS):
        baseline = BaselineConfig(seed=index + 1, tick_count=3)
        ablation = AblationConfig(("component_toggle",))
        specs.append(
            BenchmarkScenarioSpec(
                scenario_id=scenario_id,
                purpose=purpose,
                expected_signal=signal,
                baseline_config_digest=_digest(baseline.to_dict()),
                treatment_config_digest=_digest(ablation.to_dict()),
                required_metrics=metrics,
                min_seed_policy="descriptive_phase1",
                claim_ceiling=ceiling,
            )
        )
    return tuple(specs)


def benchmark_v2_scenarios() -> tuple[BenchmarkScenario, ...]:
    scenarios: list[BenchmarkScenario] = []
    for index, spec in enumerate(benchmark_v2_specs()):
        scenarios.append(
            BenchmarkScenario(
                scenario_id=spec.scenario_id,
                description=spec.purpose,
                baseline_config=BaselineConfig(seed=index + 1, tick_count=3),
                ablation_config=AblationConfig(("component_toggle",)),
            )
        )
    return tuple(scenarios)

# Phase 3 benchmark catalog contracts.
from codontrace.genesis.canonical import canonical_digest as _phase3_digest

@dataclass(frozen=True, slots=True)
class BenchmarkControlSpec:
    positive_control: str
    negative_control: str
    ablation_control: str = "feature_ablation"
    schema_version: str = "benchmark_control_spec_v1"
    def to_dict(self) -> dict[str, JsonValue]:
        return {"schema_version": self.schema_version, "positive_control": self.positive_control, "negative_control": self.negative_control, "ablation_control": self.ablation_control}
    def digest(self) -> str:
        return _phase3_digest(self.to_dict())

@dataclass(frozen=True, slots=True)
class BenchmarkDifficultyLadder:
    scenario_family: str
    levels: tuple[str, ...]
    schema_version: str = "benchmark_difficulty_ladder_v1"
    def __post_init__(self) -> None:
        if not self.scenario_family or not self.levels:
            raise ValueError("BenchmarkDifficultyLadder requires family and levels")
    def to_dict(self) -> dict[str, JsonValue]:
        return {"schema_version": self.schema_version, "scenario_family": self.scenario_family, "levels": list(self.levels)}
    def digest(self) -> str:
        return _phase3_digest(self.to_dict())

@dataclass(frozen=True, slots=True)
class BenchmarkScenarioContract:
    scenario_family: str
    purpose: str
    controls: BenchmarkControlSpec
    difficulty_ladder: BenchmarkDifficultyLadder
    public_api_only: bool = True
    schema_version: str = "benchmark_scenario_contract_v1"
    def to_dict(self) -> dict[str, JsonValue]:
        return {"schema_version": self.schema_version, "scenario_family": self.scenario_family, "purpose": self.purpose, "controls": self.controls.to_dict(), "difficulty_ladder": self.difficulty_ladder.to_dict(), "public_api_only": self.public_api_only}
    def digest(self) -> str:
        return _phase3_digest(self.to_dict())

_PHASE3_SCENARIO_FAMILIES = (
    "evolution_birth_mutation_lineage", "qd_selection_pressure", "memory_delayed_reward", "adf_macro_reuse", "toolchain_sparse_reward", "causal_intervention", "social_partner_heldout", "collective_coordination", "swarm_resilience_scaling", "oee_discovery_curriculum",
)

@dataclass(frozen=True, slots=True)
class BenchmarkScenarioCatalog:
    contracts: tuple[BenchmarkScenarioContract, ...]
    schema_version: str = "benchmark_scenario_catalog_v1"
    @classmethod
    def phase3_default(cls) -> "BenchmarkScenarioCatalog":
        contracts=[]
        for fam in _PHASE3_SCENARIO_FAMILIES:
            controls=BenchmarkControlSpec(f"{fam}_positive", f"{fam}_negative")
            ladder=BenchmarkDifficultyLadder(fam, ("small", "medium", "large"))
            contracts.append(BenchmarkScenarioContract(fam, f"Phase 3 {fam} benchmark", controls, ladder))
        return cls(tuple(contracts))
    def to_dict(self) -> dict[str, JsonValue]:
        return {"schema_version": self.schema_version, "contracts": [c.to_dict() for c in self.contracts]}
    def digest(self) -> str:
        return _phase3_digest(self.to_dict())
