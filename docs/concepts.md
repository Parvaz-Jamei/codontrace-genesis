# Concepts

## Core Kernel

`codontrace` uses executable semantic genomes, ATP-constrained white-box agents, audit-ready trace events, and deterministic replay.

## Extensible actions

In `v0.3.0a1`, actions are resolved by string action name. The default `Action` enum remains for backward compatibility, but custom codons may use strings such as `"REST"`.

`ActionRegistry` maps action names to handlers. Handlers accept `ActionContext` and return `ActionResult`.

Handlers must not bypass:

- `ATPAccount`
- `ATPLedgerEntry`
- `TraceEvent`
- deterministic replay

## ATP policy


## Trace and timeline

`Trace` is an append-only in-memory timeline with two compatible event families:

- `TraceEvent`: agent decision/action events.
- `WorldEvent`: world/environment mutation events.

`Trace.to_jsonl()` remains agent-event-only for backward compatibility. Use `Trace.to_bundle()`, `Trace.to_bundle_json()`, `Trace.bundle_digest()`, and `Trace.to_engine_events()` when a complete timeline is needed for audit, notebooks, or future replay viewers. A streaming `TraceStream` pattern is still deferred.

## World2D custom cells

Custom cell markers are metadata only. They are not walls, resources, or ATP. Custom action handlers may read them with `get_custom_cell()`.

## Non-claims

This project does not claim general-intelligence, biological simulation, causal-certainty claim, open-ended population evolution, or production automation claim.


## WorldEvent scope

Use event-aware wrappers such as `World2D.place_resource_event(...)` or `RunRecorder.place_resource(...)` when external world changes need to be replayed or visualized. Direct mutations such as `world.place_resource(...)` remain valid, but they are intentionally not logged unless the caller uses the event-aware APIs. Full UI/game-engine integration is out of scope; this release provides only the typed JSON contract.

## Multi-agent rendering scope

`World2D.agent_position` and `World2D.render_ascii()` are single-agent convenience features. In multi-agent simulations, agent positions are represented by the `WhiteBoxAgent` objects and by `SimulationResult.agent_states`. `render_ascii()` is not a full multi-agent renderer in `v0.3.0a1`; notebooks and applications can build their own `agents_by_position` overlay for visualization.

## Ledger refs

`TraceEvent.ledger_entry_ids` are local to one `ATPAccount`, so two different agents may both have ledger entry id `0`. For shared multi-agent traces, use the additive `TraceEvent.ledger_entry_refs` property and JSON field, such as `agent-a:0`, for globally unambiguous audit/export.

## Scenario diversity and reproducibility


This layer is not open-ended population evolution and not a claim of open-ended discovery. It is an experiment setup layer for reproducibility, scenario diversity, audit, and script/test workflows.

Hazards and beacons are object-layer markers represented with `WorldObject`; they do not add physics, damage, rewards, or automatic behavior in this release.

## Diversity metrics scope

`codontrace.metrics.diversity` exposes pure metrics for genome diversity, behavior signatures, profile/ATP distributions, action entropy, resource/wall/object densities, traversability, clustering, scenario summaries, one-scenario metadata, and two-scenario reproducibility reports. Genome metrics accept `SemanticGenome` objects directly and also accept agents as a convenience. These functions must not mutate worlds, agents, traces, or scenario configs.

Scenario-level runs via `Scenario.run()` or `ScenarioFactory.run()` propagate `Scenario.config_hash` into `TraceEvent.config_hash`. `trace_enabled=False` returns an empty trace from scenario-level runners. `replay_enabled=False` is recorded as scenario metadata and disables automatic replay-validation metadata for this release; it does not change the low-level `Simulation.run()` contract. Default movement follows `World2D` boundary semantics, including `boundary="wrap"`. Scenario-level runs pass `WorldConfig.allow_agent_on_wall` into runtime validation, while low-level `Simulation.run()` keeps wall starts rejected unless `SimulationConfig(allow_agent_on_wall=True)` is chosen explicitly. `World2D.walls` are real walls only; agent occupancy is stored outside the wall set. Collision blocking is a runtime occupancy rule, not wall physics, and `SENSE_DANGER` / `nearby_wall` report real nearby walls only. Scheduler semantics are stable: `sequential` uses sorted ids every tick, `round_robin` rotates the start index deterministically, and `random_order` is the only seeded shuffled scheduler.

### Scenario config metadata vs runtime behavior


`ObstacleConfig.block_movement` and `block_sight` are also preserved metadata in `v0.3.0a1`. They do not change default movement or sensing behavior yet: default movement still treats `World2D.walls` as blocking cells, and this alpha does not implement line-of-sight physics or raycasting.


## Population lifecycle foundation

`v0.3.0a1` adds a controlled population lifecycle layer after the GENESIS Foundation path (`NexusGenome -> Ribosome -> CompiledBrain -> ATP_runtime -> Trace -> AliveGate`). It provides controlled reproduction, deterministic mutation, lineage tracking, fitness scoring, and generation stepping as library objects.

The layer is focused, correctness-first, and extensible. It includes dependency-free D0 baseline objects, DiscoveryCandidate/DiscoveryWitness records, Quality-Diversity archive/selection-pressure primitives, Phase-B evidence records, Integration validation artifacts, and deterministic smoke report outputs. These are library-level research primitives, not automatic proof of open-ended evolution, unrestricted ADF growth, Pearl-grade causal discovery, or production AI.


## Dual ATP and bounded memory

Dual ATP separates action execution energy from memory/learning accounting. `ATP_runtime` pays token/action execution. `ATP_learning` pays bounded memory writes, consolidation-style attempts, and explicit local CausalGraph scaffold updates. Vitae is the conceptual source for learning ATP, but this release does not implement Pearl-grade causality, causal-certainty claim, unrestricted automatic ADF vocabulary growth, full Causal Capsule exchange proof, full MAP-Elites search, or open-ended discovery claims. D0, Discovery Witness, QD, ablation, heldout/generalization, statistical protocol, release-pack, and evidence-lineage objects are digest-backed library audit primitives with conservative claim-gating. The local CausalGraph stores event-based evidence edges from traces and memory; it is not DoWhy, causal-learn, Granger causality, or statistical causal discovery.



## ADF / Dynamic Vocabulary foundation

`v0.3.0a1` adds deterministic ADF candidate detection as a measurement and proposal layer. It searches trace action/codon sequences for repeated patterns, scores compression gain and reuse, and creates ATP_learning-gated `ADFProposal` objects. This is an explicit, auditable dynamic vocabulary foundation: proposals do not silently mutate the base GENESIS codon table, do not execute dynamic Python code, and do not prove endogenous language emergence or discovery.

Capsule/Nexus objects are present only as typed hooks for the next phase. They do not transfer graph knowledge between organisms yet.

## Local CausalGraph scaffold

`v0.3.0a1` adds a focused dependency-free local causal evidence graph. It builds deterministic nodes and evidence-count edges from `TraceEvent` and `EpisodicMemory` signals, and updates are gated by `ATP_learning`. This is an auditable scaffold for later research phases. It is not causal-certainty claim, not Pearl-grade causality, not DoWhy/causal-learn, not Granger causality, not a Causal Capsule, and not a discovery detector.


## Causal Capsule + Nexus Stigmergy Foundation

CodonTrace provides an in-memory Causal Capsule + Nexus Stigmergy foundation for controlled GENESIS-style experiments. It implements CausalCapsule lifecycle objects, CapsuleStore, NexusStigmergyLayer, ATP-gated capsule emission/read/adoption, environment-mediated capsule transfer, capsule transfer audit metrics, and typed D0/Discovery hooks for future phases.

This is not proof of knowledge transfer, not proof of causal learning, not a D0-calibrated discovery claim, not a Discovery Witness archive, not Quality-Diversity/MAP-Elites, and not open-ended discovery. Stigmergy is represented as in-memory environment-mediated signals: target organisms read from a Nexus layer/store rather than receiving direct source-to-target messages.

ADF/Dynamic Vocabulary support remains explicit and auditable: proposals use codon-width-consistent state, full-window occurrence evidence, primitive-cost-based macro cost policies, ATP_learning-gated proposal accounting, and additive extended codon-table proposals. Base GENESIS codon tables remain stable.


## Configurable GENESIS research primitives

The extensibility foundation separates built-in GENESIS v0 defaults from the experimental objects researchers may need to vary. Defaults remain stable for reproducibility, while `Registry`, `Config`, `Spec`, and `Protocol` objects allow controlled variation of elements, substrate rules, genome alphabets, codon widths, codon tables, schedulers, topologies, fitness signals, and action-status semantics.

This is an experiment-design mechanism, not an open-ended discovery claim. Changing a registry or protocol defines a testable experimental condition; evidence still requires baselines, ablations, multi-seed runs, and conservative interpretation.


## D0 / Discovery Witness / QD Hooks

CodonTrace now provides dependency-free library objects for D0 baseline calibration, distance-to-D0 measurement, conservative DiscoveryCandidate records, DiscoveryWitness evidence scaffolds, Quality-Diversity archive hardening, and ablation/statistical protocol records. These APIs are Python-object based, serializable, digestible, and designed for audit. They do not force positive claims or hide controls. Current Integration smoke/examples can write deterministic evidence bundles and validation summaries, while strong discovery/OEE claims still require configured baselines, controls, multi-seed evidence, and ClaimGate approval. Witness status is evidence infrastructure only and requires baseline, replay/trace, ablation coverage, and configurable multi-seed metadata before reaching evidence-supported scaffold status.


## v0.3.0a1 Release Candidate Hardening + Scientific Evidence Pack

CodonTrace v0.3.0a1 focuses on API hardening, validation objects, compatibility snapshots, example-smoke contracts, research-validation bundle records, and claim-audit scaffolds. These are dependency-free Python object APIs only. They do not add an app, UI, dashboard, CLI, report writer, notebook generator, experiment runner, file writer, p-value engine, or external dependency. The validation pack helps researchers audit reproducibility and claim safety, but it does not prove general-intelligence, artificial life, open-ended discovery, causal-certainty claim, knowledge transfer, or benchmark-rank claim.
