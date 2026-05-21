# Public API Highlights

## Professional multi-agent run

```python
from codontrace import AgentFactory, AgentProfile, InitializationConfig, Simulation, SimulationConfig, World2D

world = World2D.from_ascii("""
........
..#.....
....*...
........
""")

agents = AgentFactory.create_many(
    world=world,
    config=InitializationConfig(
        count=20,
        seed=42,
        genome_strategy="profiled_random",
        placement_strategy="poisson_disk",
        profiles=(
            AgentProfile(name="explorer", count=10, preferred_codons=("101", "011")),
            AgentProfile(name="collector", count=10, preferred_codons=("111", "001")),
        ),
    ),
)

result = Simulation.run(
    world=world,
    agents=agents,
    config=SimulationConfig(steps=50, scheduler="random_order", seed=42),
)

print(result.trace_digest)
```

## Beginner quick run

```python
from codontrace import AgentProfile, Experiment

result = Experiment.quick(
    world_ascii="""
........
..#.....
....*...
........
""",
    agent_count=20,
    seed=42,
    steps=50,
    profiles=(
        AgentProfile(name="explorer", count=10, preferred_codons=("101", "011")),
        AgentProfile(name="collector", count=10, preferred_codons=("111", "001")),
    ),
)

print(result.summary())
```

## Reproducible specs

```python
from codontrace import (
    AgentFactory,
    AgentProfile,
    AgentSpec,
    InitializationConfig,
    Simulation,
    SimulationConfig,
    SimulationResult,
    Trace,
    World2D,
)

world = World2D(8, 8)
config = InitializationConfig(
    count=4,
    seed=11,
    profiles=(AgentProfile(name="explorer", count=4, genome_length=3),),
)
specs = AgentFactory.create_specs(world=world, config=config)
payload = [spec.to_dict() for spec in specs]
restored = tuple(AgentSpec.from_dict(item) for item in payload)
```

## Object-based serialization

```python
agents = AgentFactory.create_many(world=world, config=config)
result = Simulation.run(
    world=world,
    agents=agents,
    config=SimulationConfig(steps=3, scheduler="round_robin"),
)

jsonl_text = result.trace.to_jsonl_string()
restored_trace = Trace.from_jsonl_string(jsonl_text)

world_payload = world.to_dict()
restored_world = World2D.from_dict(world_payload)

result_payload = result.to_dict()
restored_result = SimulationResult.from_dict(result_payload)
```

The core API does not perform path-based save/load operations. User applications own file I/O, notebooks, dashboards, reports, and visualizations.

Scheduler semantics are explicit: `sequential` means sorted agent id order every tick, `round_robin` means a deterministic rotating start index per tick, and `random_order` is the only seeded shuffled scheduler. Multi-agent collision blocking is occupancy-based. `World2D.walls` remain real walls only; occupied agent cells are not injected into walls, so `SENSE_DANGER` / `nearby_wall` only report real nearby walls.


## Multi-agent world rendering note

`World2D.agent_position` and `World2D.render_ascii()` are single-agent convenience features. In multi-agent simulations, read final agent positions from `SimulationResult.agent_states` or from the `WhiteBoxAgent` objects. `World2D` does not maintain a full `agent_positions` registry in `v0.3.0a1`.

## Trace ledger references

`TraceEvent.ledger_entry_ids` are local to each agent ATP account. Use `TraceEvent.ledger_entry_refs` for trace-level audit/export in shared multi-agent traces. The JSON/JSONL export includes `ledger_entry_refs`, but older trace payloads without that field still import correctly because refs are derived from `agent_id` and `ledger_entry_ids`.

## WorldEvent timeline API

```python
from codontrace import CausalReplay, RunRecorder, Trace, World2D

world = World2D(20, 10)
recorder = RunRecorder()
recorder.place_resource(world, (10, 5), 8.0, step=0, reason="initial food")

bundle = recorder.trace.to_bundle()
restored = Trace.from_bundle(bundle)
replayed_world = CausalReplay.apply_world_events(World2D(20, 10), restored.world_events)

assert replayed_world.resource_amount((10, 5)) == 8.0
```

Public timeline helpers include:

- `WorldEvent`
- `TimelineFrame`
- `RunRecorder`
- `Trace.to_bundle()` / `Trace.from_bundle()`
- `Trace.bundle_digest()`
- `Trace.to_engine_events()` / `Trace.to_engine_json()`
- `World2D.place_resource_event()` and related event-aware wrappers
- `World2D.apply_world_event()`
- `CausalReplay.apply_world_events()`
- `CausalReplay.replay_timeline()`
- `SimulationResult.to_viewer_bundle()` / `SimulationResult.to_viewer_json()`

`Trace.to_jsonl()` remains agent-event-only to avoid breaking existing trace consumers.

## Scenario diversity API

`v0.3.0a1` keeps the deterministic scenario layer stable and tightens runtime/contract semantics around collision occupancy, scheduler order, validation, public exports, and trace correctness. It is additive: existing `World2D`, `AgentFactory`, `InitializationConfig`, `TraceEvent`, and `Trace.to_jsonl()` behavior remain unchanged.

```python
from codontrace import (
    ScenarioAgentProfile,
    ScenarioConfig,
    ScenarioFactory,
    WorldConfig,
)

config = ScenarioConfig(
    name="demo",
    seed=42,
    world=WorldConfig(
        width=12,
        height=8,
        seed=42,
        boundary="open",
        wall_density=0.08,
        wall_pattern="rooms",
        resource_density=0.12,
        resource_distribution="clusters",
        resource_amount_range=(1.0, 3.0),
        hazard_density=0.04,
        hazard_distribution="uniform",
        beacon_density=0.03,
        beacon_distribution="uniform",
    ),
    agents=(
        ScenarioAgentProfile(
            name="collector",
            count=4,
            genome_length_range=(3, 5),
            atp_range=(4.0, 6.0),
            codon_bias={"111": 3.0},
            placement_zone="near_resources",
        ),
    ),
)

scenario = ScenarioFactory.from_config(config)
result = scenario.run()
print(scenario.config_hash)
print(result.trace.events[0].config_hash)
```

Public scenario helpers include:

- `WorldConfig`
- `ResourceConfig`
- `ObstacleConfig`
- `ScenarioAgentProfile`
- `ScenarioConfig`
- `WorldFactory`
- `ScenarioFactory`
- `Scenario`
- `ScenarioResult`

Hazards and beacons are represented as `WorldObject(kind="hazard")` and `WorldObject(kind="beacon")`. They are object-layer markers, not physics, reward, damage, or behavior systems.


## Diversity metrics

`codontrace.metrics.diversity` provides pure functions that inspect worlds, agents, traces, and scenarios without mutating inputs.

```python
from codontrace.metrics.diversity import (
    behavior_signature_distribution,
    diversity_report,
    reproducibility_report,
    scenario_reproducibility_metadata,
)

same_again = ScenarioFactory.from_config(ScenarioConfig.from_json(config.to_json()))
print(reproducibility_report(scenario, same_again))
print(scenario_reproducibility_metadata(scenario))
print(diversity_report(scenario, result.trace))
print(behavior_signature_distribution([result.trace]))
```

Available functions include `unique_genome_count`, `mean_genome_distance`, `codon_usage_entropy`, `genome_length_distribution`, `behavior_signature_distribution`, `lineage_depth_distribution`, `profile_distribution`, `atp_distribution`, `action_entropy`, `wall_density_actual`, `resource_density_actual`, `object_type_distribution`, `traversable_ratio`, `resource_clustering_score`, `hazard_clustering_score`, `scenario_summary`, `scenario_reproducibility_metadata`, `reproducibility_report`, and `diversity_report`.

## Experiment.quick ASCII marker contract


## Zero-cost ATP debit contract

`ATPAccount.can_pay(0.0)` returns `True`, but `ATPAccount.debit(0.0, ...)` is a no-op and returns `None`. Zero-cost actions still emit trace events with `action_cost` and `net_atp_delta` set to `0.0`, but they do not create attempt-cost ledger entries. Credits or extra debits requested through `EnergyEffect` are still ledger-recorded when their amounts are positive.


## GENESIS Foundation API

The GENESIS Foundation namespace is available under `codontrace.genesis` and is also re-exported from the top-level package for convenience.

Main objects:

- `ElementKind`, `ElementOrigin`, `ElementSpec`, `ELEMENT_SPECS`
- `ElementGrid`, `ElementCell`, `ElementRuleConfig`, `ElementStepResult`
- `world2d_to_element_grid()` and `element_grid_to_world2d()`
- `CodonTable.genesis_v0()` and `GenesisCodonTable.default_v0()`
- `Ribosome`, `CompiledToken`, `CompiledBrain`, `TranslationResult`
- `GenesisATPState`, `DualATPBudget`
- `AliveGateConfig`, `AliveGateResult`, `evaluate_alive()`
- `GenesisOrganism`, `GenesisRunResult`

Compatibility note: `WhiteBoxAgent`, `CodonTable.default_minimal()`, existing examples, and the current replay APIs remain available. The GENESIS path is an additive foundation path, not a replacement for the beginner API.

Claim-control note: `CausalReplay` is not `CausalGraph`; `AliveGate` is an operational metric, not life-like outcome validation. `COPY_SELF` remains blocked in single-organism `GenesisOrganism` runs. Controlled reproduction is implemented only inside the explicit population lifecycle path, where `ReproductionConfig`, `AliveGate` evidence, ATP checks, mutation metadata, and lineage records are required.


## GENESIS Population API

`codontrace.genesis.population` adds the focused deterministic population lifecycle needed before later GENESIS phases. The public objects are also re-exported from `codontrace`:

- `ReproductionConfig`, `MutationConfig`, `FitnessConfig`, and `PopulationConfigs`
- `MutationResult`, `ReproductionDecision`, `ReproductionResult`, `FitnessResult`, `LineageRecord`, `PopulationState`, and `GenerationResult`
- `mutate_genome()`, `evaluate_fitness()`, `can_reproduce()`, `reproduce()`, and `step_population()`
- `PopulationRunner` in `codontrace.genesis.population_runner`

`COPY_SELF` remains blocked in single-organism `GenesisOrganism` runs. It may create offspring only inside the population lifecycle path where ATP debit, configuration checks, lineage metadata, and mutation metadata are all recorded. No CLI, UI, dashboard, notebook generator, report writer, database, cloud API, visualization dependency, or file-writing path is added.

Fitness is a controlled scoring function for experiments. It is not a claim of life, intelligence, open-ended discovery, or benchmark-rank claim.


## GENESIS Dual ATP and EpisodicMemory foundation

`v0.3.0a1` adds operational `ATP_learning` alongside `ATP_runtime`. Runtime ATP pays action execution. Learning ATP pays bounded memory writes, consolidation attempts, and learning-update decisions. `EpisodicMemory` is an in-memory bounded audit/research object, not a neural memory, LLM memory, database, report store, or file writer. `LearningUpdateDecision` is a deterministic scaffold and does not implement causal discovery. `BehaviorDescriptor` is a measurement object only; it is not MAP-Elites, D0, Quality-Diversity, or Discovery.



## ADF / Dynamic Vocabulary foundation

`v0.3.0a1` adds `ADFPattern`, `ADFCompressionScore`, `ADFProposal`, `DynamicVocabularyConfig`, `DynamicVocabularyState`, `ADFDetectionResult`, `ADFMacro`, and `ADFExpansionResult`. Use `detect_adf_patterns()` to find repeated action/codon windows from traces, `score_adf_pattern()` to apply explicit support/compression/reuse/ATP-pressure criteria, and `propose_dynamic_vocabulary()` to create ATP_learning-gated proposal objects.

The API does not mutate global codon tables. `extend_codon_table_with_adfs()` returns an additive table only from accepted proposals, and `macro_from_proposal()` / `expand_adf_macro()` provide safe macro metadata without `eval`, `exec`, plugin loading, or file access. Capsule objects now include an in-memory Causal Capsule + Nexus Stigmergy foundation. Capsule adoption is a controlled experiment mechanism, not proof of transferred intelligence or causal learning.

## Local CausalGraph scaffold

`v0.3.0a1` adds `CausalGraph`, `CausalNode`, `CausalEdge`, `CausalGraphConfig`, and `CausalGraphUpdateResult`. Use `update_causal_graph_from_trace()` or `update_causal_graph_from_memory()` to build a focused local evidence graph from `TraceEvent` or `EpisodicMemory` signals. Updates are deterministic, serializable, digestible, and gated by `ATP_learning`; `ATP_runtime` never pays graph-update costs.

This CausalGraph API is deliberately dependency-free. It does not implement DoWhy, causal-learn, Granger causality, Pearl-grade causal discovery, Causal Capsule proof, ADF proof, D0 calibration itself, QD search itself, MAP-Elites search loops, or Discovery Witness proof. Separate GENESIS modules provide D0, Discovery Witness, and QD evidence scaffolds; edge weights here remain evidence counts from controlled runs, not causal-certainty claim.


## Causal Capsule + Nexus Stigmergy Foundation

CodonTrace provides an in-memory Causal Capsule + Nexus Stigmergy foundation for controlled GENESIS-style experiments. It implements CausalCapsule lifecycle objects, CapsuleStore, NexusStigmergyLayer, ATP-gated capsule emission/read/adoption, environment-mediated capsule transfer, capsule transfer audit metrics, and typed D0/Discovery hooks for future phases.

This is not proof of knowledge transfer, not proof of causal learning, not a D0-calibrated discovery claim, not a Discovery Witness archive, not Quality-Diversity/MAP-Elites, and not open-ended discovery. Stigmergy is represented as in-memory environment-mediated signals: target organisms read from a Nexus layer/store rather than receiving direct source-to-target messages.

ADF/Dynamic Vocabulary support remains explicit and auditable: proposals use codon-width-consistent state, full-window occurrence evidence, primitive-cost-based macro cost policies, ATP_learning-gated proposal accounting, and additive extended codon-table proposals. Base GENESIS codon tables remain stable.


## GENESIS extensibility foundation

`v0.3.0a1` exposes object-based extension points for research-critical variation without changing core source code:

- `ElementRegistry` / `ElementDefinition` for open element vocabularies;
- `SubstrateRuleConfig` / `SubstratePhysicsConfig` for deterministic substrate rules and quantitative properties;
- `GenomeSpec` / `CodonTableSpec` for non-binary alphabets and codon widths;
- `SchedulerProtocol` and built-in scheduler presets;
- `TopologyProtocol` and built-in topology presets;
- `FitnessSignalRegistry` for custom measurable fitness signals;
- `ActionStatusRegistry` for status categories beyond `executed`, `blocked`, and `failed`.

These APIs accept Python objects only. They do not add file loaders, CLI runners, dashboards, or new runtime dependencies.


## D0 / Discovery Witness / QD Hooks

CodonTrace now provides dependency-free library objects for D0 baseline calibration, distance-to-D0 measurement, conservative DiscoveryCandidate records, DiscoveryWitness evidence scaffolds, Quality-Diversity archive hardening, and ablation/statistical protocol records. These APIs are Python-object based, serializable, digestible, and designed for audit. They do not force positive claims or hide controls. Current Integration smoke/examples can write deterministic evidence bundles and validation summaries, while strong discovery/OEE claims still require configured baselines, controls, multi-seed evidence, and ClaimGate approval. Witness status is evidence infrastructure only and requires baseline, replay/trace, ablation coverage, and configurable multi-seed metadata before reaching evidence-supported scaffold status.


## v0.3.0a1 Release Candidate Hardening + Scientific Evidence Pack

CodonTrace v0.3.0a1 focuses on API hardening, validation objects, compatibility snapshots, example-smoke contracts, research-validation bundle records, and claim-audit scaffolds. These are dependency-free Python object APIs only. They do not add an app, UI, dashboard, CLI, report writer, notebook generator, experiment runner, file writer, p-value engine, or external dependency. The validation pack helps researchers audit reproducibility and claim safety, but it does not prove general-intelligence, artificial life, open-ended discovery, causal-certainty claim, knowledge transfer, or benchmark-rank claim.

## v0.3.0a1 evidence-hardening APIs

New object-only APIs include `ScientificEvidenceProfile`, `validate_scientific_evidence_pack`, `EvidenceLineageGraph`, `ReproducibilitySummary`, `EvidenceQualityScore`, `MatureAlphaReadinessResult`, `APIStabilityMap`, `CompatibilityPolicy`, `DocumentationAuditResult`, and `SecurityEvidenceRecord`. These APIs return deterministic Python objects and digests; they do not write files or execute external tools.
