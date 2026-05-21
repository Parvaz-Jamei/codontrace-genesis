<div align="center">

# CodonTrace Genesis 🧬

**A deterministic research engine for digital evolution, causal mechanism auditing, replayable evidence, and white-box agent experiments.**

[![PyPI version](https://img.shields.io/pypi/v/codontrace.svg)](https://pypi.org/project/codontrace/)
[![Python](https://img.shields.io/pypi/pyversions/codontrace.svg)](https://pypi.org/project/codontrace/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Status: Research Alpha](https://img.shields.io/badge/status-research--alpha-orange.svg)](#scientific-claim-policy)
[![Deterministic Replay](https://img.shields.io/badge/replay-digest--backed-blue.svg)](#why-codontrace-genesis)
[![Library-as-Tool](https://img.shields.io/badge/design-library--as--tool-purple.svg)](#scientific-claim-policy)

</div>

---

## What is CodonTrace Genesis?

**CodonTrace Genesis** is a Python research library for building and auditing deterministic digital-evolution experiments. It focuses on transparent mechanisms: semantic genomes, white-box agent execution, capsule-mediated information transfer, skill-compression inheritance, role and collective-behavior instrumentation, causal ablations, replay digests, evidence manifests, and claim-gated scientific artifacts.

It is designed for researchers, engineers, and advanced experimenters who want a **library-first engine**, not a black-box simulator and not a runner that hard-codes success.

> **Release status:** `0.3.0a1` is a research-alpha software release. It provides engine primitives, public APIs, tests, examples, and evidence surfaces. It is not a claim of AGI, consciousness, autonomous open-ended discovery, artificial life equivalence, or causal certainty.

---

## Why CodonTrace Genesis?

| Need | How CodonTrace Genesis approaches it |
|---|---|
| Deterministic experiments | Seeded execution, stable digests, replay bundles, and manifest-level runtime hashes. |
| Mechanism-level AI research | Explicit primitives for genomes, actions, memory, capsules, roles, reproduction, selection, QD, OEE, and causal interventions. |
| Stronger social/collective evidence | Role mechanics, heldout partner evaluation, collective task graphs, role ablations, contribution ledgers, and ClaimGate-compatible records. |
| Safer scientific claims | Evidence manifests, negative controls, ablations, blocked reasons, and explicit claim downgrades. |
| Extensible research software | Library APIs first; runners and examples are consumers of the engine, not hidden sources of success. |

---

## Core capabilities

### Evolution and runtime

- Semantic genome translation and codon-to-action execution.
- ATP-constrained white-box agent runtime.
- Reproduction, mutation, lineage, birth/death diagnostics, and runtime maturity records.
- Configurable `GenesisExperimentSpec` and `GenesisEngine` execution.

### Causal mechanisms and replayable evidence

- `CapsuleAblationPolicy` for capsule/packet-style transfer controls.
- `CapsuleOutcomeWindow` for delayed capsule outcome tracking.
- `SignalMemoryCausalLinkRecord` for `signal/capsule → memory → action → outcome` audits.
- `SkillCompressionAblationPolicy` and `ChildOutcomeAuditRecord` for inheritance and compression controls.
- `CounterfactualReplayProtocol` for digest-backed intervention design.

### Social, role, and collective behavior

- `RoleMechanicsPolicy` for role persistence and soft role-bias mechanics.
- `TerritoryMechanicsConfig` and territory-defense records.
- `CollectiveTaskGraph`, role dependency edges, and joint-task progress records.
- `RoleAblationProtocol` and `HeldoutPartnerEvaluationProtocol`.
- `MultiAgentContributionLedger` and source-reputation memory surfaces.

### Scientific instrumentation

- Quality Diversity and Pareto/QD evidence surfaces.
- Discovery, D0/shadow-baseline, ablation, and generalization schemas.
- Extended open-endedness metrics through `OEEExtendedMetrics`.
- Evidence lineage, release evidence packs, statistical protocol checks, and ClaimGate integration.

---

## Installation

From PyPI after publication:

```bash
python -m pip install codontrace==0.3.0a1
```

For a local source checkout:

```bash
python -m pip install -e ".[dev]"
python -m pytest
```

Optional research extras:

```bash
python -m pip install "codontrace[research]"
```

---

## Quick start

### Compact beginner API

```python
from codontrace import WhiteBoxAgent, World2D

world = World2D(width=4, height=4)
agent = WhiteBoxAgent.from_world(world, genome="000")
result = agent.run_trial(world, steps=3, explain=True)

print(result.explanation)
```

### Genesis runtime API

```python
from codontrace.genesis import GenesisEngine, GenesisExperimentSpec

spec = GenesisExperimentSpec(seed=7, tick_count=3)
result = GenesisEngine.from_spec(spec).run_ticks()

print(result.replay_bundle.digest())
print(result.manifest.digest())
print(result.manifest.runtime_hashes)
```

### Causal mechanism configuration

```python
from codontrace.genesis import (
    CapsuleAblationPolicy,
    CapsuleOutcomeWindow,
    GenesisExperimentSpec,
    SkillCompressionAblationPolicy,
)

spec = GenesisExperimentSpec(
    seed=11,
    tick_count=5,
    capsule_ablation_policy=CapsuleAblationPolicy(
        enable_capsule_transfer=True,
        enable_capsule_utility_scoring=True,
        enable_source_fitness_weighting=True,
        enable_signal_memory_link=True,
        enable_capsule_behavior_update=True,
    ),
    capsule_outcome_window=CapsuleOutcomeWindow(window_ticks=5),
    skill_compression_ablation_policy=SkillCompressionAblationPolicy(
        mode="full_compression"
    ),
)
```

`PacketAblationPolicy` and `PacketOutcomeWindow` are compatibility aliases for the canonical `Capsule*` APIs. They do **not** create a second packet runtime.

---

## Architecture at a glance

```text
GenesisExperimentSpec
        ↓
GenesisEngine / population / runtime modules
        ↓
Agent events, capsules, memory, roles, reproduction, QD, OEE, interventions
        ↓
GenesisRunResult
        ↓
ReplayBundle · EvidenceManifest · Runtime hashes · ClaimGate records
        ↓
Auditable scientific artifacts and controlled claim surfaces
```

The engine is intentionally structured so that new mechanisms must pass through runtime configuration, execution, records, digests, manifests, replay policy, and claim gating. This keeps CodonTrace Genesis extensible without turning experiments into hidden hard-coded success paths.

---

## Scientific claim policy

CodonTrace Genesis is a **Library-as-Tool**. It provides primitives, policies, records, digests, controls, and audit surfaces. It does not automatically turn configured mechanisms into positive scientific claims.

A claim becomes stronger only when the relevant records are:

1. produced by an explicit experiment or configured protocol,
2. deterministic and digest-backed,
3. visible in the manifest or evidence bundle,
4. linked to controls, ablations, heldout evaluation, or negative controls when required,
5. compatible with replay policy, and
6. accepted by ClaimGate for the specific claim level.

This means a successful smoke run is useful engineering evidence, but it is not treated as a strong scientific claim by itself.

---

## Documentation map

| Topic | Document |
|---|---|
| Runtime contract | `docs/GENESIS_RUNTIME_CONTRACT.md` |
| Claim policy | `docs/CLAIM_GATE_POLICY.md` |
| Replay and artifacts | `docs/REPLAY_AND_ARTIFACTS.md` |
| Causal validation | `docs/CAUSAL_VALIDATION_PROTOCOL.md` |
| Capsule transfer validation | `docs/CAPSULE_TRANSFER_VALIDATION.md` |
| Quality Diversity | `docs/QD_SEARCH_LOOP.md` |
| Open-endedness protocol | `docs/OEE_LONG_HORIZON_PROTOCOL.md` |
| Scientific limits | `docs/SCIENTIFIC_LIMITS.md` |
| Publishing notes | `docs/publishing.md` |

---

## Project status

`0.3.0a1` is intended for:

- research-alpha evaluation,
- reproducible local experiments,
- review by collaborators,
- citation-ready archival releases,
- controlled benchmark design,
- and development of stronger experimental campaigns.

It is not intended to be marketed as a finished autonomous intelligence system.

---

## Citation

See [`CITATION.cff`](CITATION.cff). If you archive a GitHub release through Zenodo, cite the resulting DOI together with the versioned release tag.

---

## License

MIT License. See [`LICENSE`](LICENSE).

---

<div align="center">

**CodonTrace Genesis** — deterministic digital evolution with replayable evidence and claim-gated mechanisms.

</div>
