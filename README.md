<div align="center">

# 🧬 CodonTrace Genesis

### Deterministic research software for digital evolution, causal mechanism auditing, replayable ALife experiments, and evidence-gated AI/evolution studies.

[![PyPI](https://img.shields.io/pypi/v/codontrace.svg?label=PyPI&color=blue)](https://pypi.org/project/codontrace/)
[![Python](https://img.shields.io/badge/Python-3.13%20%7C%203.14-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![CI](https://github.com/Parvaz-Jamei/codontrace-genesis/actions/workflows/ci.yml/badge.svg)](https://github.com/Parvaz-Jamei/codontrace-genesis/actions)
[![License](https://img.shields.io/github/license/Parvaz-Jamei/codontrace-genesis.svg)](LICENSE)
[![Research Software](https://img.shields.io/badge/research%20software-replayable%20%7C%20evidence--gated-purple)](#scientific-claim-policy)
[![Status](https://img.shields.io/badge/status-alpha%20research%20release-orange)](#release-status)

**CodonTrace Genesis** is a Python research library for building, replaying, auditing, and evaluating digital evolution experiments with deterministic evidence trails.

</div>

---

## Overview

Digital evolution, artificial life, and evolutionary AI experiments often face the same problem: interesting behaviors appear during a run, but the evidence can be hard to replay, hard to audit, and hard to separate from runner-specific assumptions.

**CodonTrace Genesis** is designed as a **library-as-tool** for controlled experiments in digital evolution, causal mechanism analysis, capsule-mediated information transfer, skill compression, role emergence, collective behavior, and open-endedness.

The project focuses on:

- deterministic replay and digest-backed artifacts,
- explicit evidence manifests,
- mutation, birth, death, reproduction, lineage, memory, capsule/signaling, role, and open-endedness primitives,
- ablation and counterfactual-style mechanisms,
- strict claim gating for scientific honesty,
- reproducible research software workflows.

CodonTrace Genesis does **not** hard-code intelligence or force a successful outcome. It provides the experimental substrate, mechanisms, records, and audit surfaces needed to test claims with replayable evidence.

---

## Why this project exists

Most experimental engines can produce outputs. Fewer engines make it easy to answer:

- Did the behavior actually emerge from the runtime?
- Can the result be replayed deterministically?
- Was the useful signal really causal, or just correlated?
- Did memory change later action?
- Did skill compression improve offspring outcome?
- Did a role matter when ablated?
- Did a group outperform individuals under heldout conditions?
- Is an open-endedness claim supported by novelty, persistence, learnability, and controls?

CodonTrace Genesis is built around those questions.

---

## Key capabilities

| Area | Capability |
|---|---|
| Digital evolution | Genome, mutation, birth, death, reproduction gates, lineage, selection, survival diagnostics |
| Replayability | Deterministic digests, runtime hashes, replay manifests, artifact indexes |
| Evidence integrity | Claim manifests, negative evidence, blocked reasons, record digests, release evidence surfaces |
| Causal mechanisms | Capsule ablations, signal-memory-action traces, delayed outcome windows, counterfactual replay protocols |
| Learning and memory | Memory records, signal-memory causal links, memory reuse and delayed reward paths |
| Capsule communication | Capsule transfer, source-fitness controls, utility scoring, misleading/expired/low-confidence cases |
| Skill compression | Compression policies, negative controls, child outcome audits, inherited-skill evidence |
| Role and social behavior | Role mechanics, role persistence, role ablation, heldout partner evaluation |
| Collective tasks | Multi-agent task graphs, role dependency edges, joint progress records |
| Open-endedness | Novelty accumulation, complexity growth, adaptive success, lineage persistence, behavior-space expansion |
| Research release | CI, examples, tests, citation metadata, PyPI-ready packaging, GitHub release readiness |

---

## Installation

### From PyPI

```bash
pip install codontrace
```

### From source

```bash
git clone https://github.com/Parvaz-Jamei/codontrace-genesis.git
cd codontrace-genesis
python -m pip install -e .
```

### Development install

```bash
python -m pip install -e .[dev]
python -m pytest tests
```

Current alpha target: **Python 3.13 / 3.14**.

---

## Quick start

```python
from codontrace.genesis import (
    GenesisExperimentSpec,
    GenesisEngineConfig,
    CapsuleAblationPolicy,
    CapsuleOutcomeWindow,
    SkillCompressionAblationPolicy,
    RoleMechanicsPolicy,
    OEEExtendedMetrics,
)

spec = GenesisExperimentSpec(
    seed=42,
    ticks=32,
    population_size=8,
    engine_config=GenesisEngineConfig(),
    capsule_ablation_policy=CapsuleAblationPolicy(
        enable_capsule_transfer=True,
        enable_capsule_utility_scoring=True,
        enable_source_fitness_weighting=True,
        enable_signal_memory_link=True,
        enable_capsule_behavior_update=True,
    ),
    capsule_outcome_window=CapsuleOutcomeWindow(
        window_ticks=5,
        track_survival=True,
        track_fitness_delta=True,
        track_reproduction_delta=True,
        track_memory_reuse=True,
        track_role_change=True,
    ),
    skill_compression_ablation_policy=SkillCompressionAblationPolicy(
        enabled=True,
        mode="full_compression",
        child_outcome_window_ticks=10,
        compare_against_uncompressed_sibling=True,
    ),
    role_mechanics_policy=RoleMechanicsPolicy(
        enable_role_bias=True,
        enable_role_persistence=True,
        enable_role_switch_cost=True,
        enable_role_task_bonus=False,
        role_inheritance_mode="weak_bias",
    ),
    oee_extended_metrics=OEEExtendedMetrics(
        novelty_accumulation=True,
        complexity_growth=True,
        adaptive_success_accumulation=True,
        lineage_persistence=True,
        behavior_space_expansion=True,
        learnability=True,
    ),
)

print(spec.deterministic_digest())
```

---

## Architecture

```text
GenesisExperimentSpec
        │
        ▼
Engine / population / runtime modules
        │
        ▼
GenesisRunResult
        │
        ├── runtime records
        ├── artifact digest map
        ├── replay policy records
        ├── evidence manifests
        ├── causal mechanism reports
        └── claim-gated scientific summaries
```

CodonTrace Genesis keeps runtime mechanisms and evidence surfaces connected. A feature is treated as mature only when it can be represented through configuration, runtime behavior, records, digests, manifests, tests, and claim gates.

---

## Research mechanisms

### Digital evolution substrate

CodonTrace Genesis includes primitives for mutation, birth, death, reproduction gates, lineage tracking, population dynamics, energy/ATP diagnostics, and deterministic replay.

```python
from codontrace.genesis import MutationOperatorAuditRecord, BirthGateRecord, DeathRecord
```

These records are designed to explain not only what happened, but why something did not happen.

---

### Capsule-mediated signaling

Capsules are the canonical information-transfer primitive in CodonTrace Genesis. They can represent local signals, transferable behavioral hints, social messages, or experimental communication packets.

```python
from codontrace.genesis import CapsuleAblationPolicy, CapsuleOutcomeWindow
```

| Control | Purpose |
|---|---|
| `enable_capsule_transfer` | Allows or disables capsule transfer |
| `enable_capsule_utility_scoring` | Separates transfer from measured utility |
| `enable_source_fitness_weighting` | Controls whether receiver sees sender success evidence |
| `enable_signal_memory_link` | Controls capsule-to-memory causality |
| `enable_capsule_behavior_update` | Controls whether received capsules can influence behavior |

Compatibility aliases may use `Packet*` naming, but the canonical engine concept is **Capsule**.

---

### Signal → memory → action auditing

CodonTrace Genesis can represent whether a signal was seen, written to memory, read later, followed by an action change, and associated with reward, fitness, or selection deltas.

```python
from codontrace.genesis import SignalMemoryCausalLinkRecord
```

This helps avoid weak claims such as “messages were exchanged” when the real question is whether information changed later behavior.

---

### Skill compression and child outcome audits

The library includes skill-compression and inheritance-related evidence records, including negative controls and child outcome audits.

```python
from codontrace.genesis import SkillCompressionAblationPolicy, ChildOutcomeAuditRecord
```

| Mode | Meaning |
|---|---|
| `full_compression` | Full skill-compression path |
| `disabled` | Compression disabled |
| `capacity_only` | Capacity transferred without learned content |
| `shuffle_compressed_skill` | Negative control with shuffled compressed skill |
| `null_compression` | Placebo/control record without real effect |

The goal is not merely to show that a child inherited something, but to test whether inherited compression changes survival, memory reuse, fitness, or reproduction outcomes.

---

### Role mechanics and collective task evidence

CodonTrace Genesis supports role-related records and policies for studying whether roles emerge, persist, switch, and contribute to collective tasks.

```python
from codontrace.genesis import (
    RoleMechanicsPolicy,
    CollectiveTaskGraph,
    RoleAblationProtocol,
    HeldoutPartnerEvaluationProtocol,
)
```

| Evidence path | Why it matters |
|---|---|
| Role persistence | Checks whether roles last beyond labels |
| Role switch cost | Prevents role labels from being arbitrary |
| Role ablation | Tests whether removing a role reduces group performance |
| Heldout partner evaluation | Tests familiar vs unfamiliar partner behavior |
| Collective task graph | Tests multi-agent dependency rather than isolated fitness |

---

### Open-endedness metrics

Open-endedness evidence should not rely on novelty alone. CodonTrace Genesis exposes extended metrics for novelty accumulation, complexity growth, adaptive success, lineage persistence, behavior-space expansion, and learnability.

```python
from codontrace.genesis import OEEExtendedMetrics
```

These metrics can support descriptive or candidate evidence depending on seed count, controls, persistence, and replayable artifacts.

---

## Scientific claim policy

CodonTrace Genesis is intentionally strict about claims.

| Claim type | Requirement |
|---|---|
| Descriptive observation | A recorded event or metric exists |
| Candidate evidence | Deterministic records, digests, and minimum protocol evidence exist |
| Causal support | Intervention, ablation, or counterfactual-style evidence is required |
| Collective/swarm evidence | Multi-agent progress, role complementarity, heldout partners, and ablation evidence are required |
| Open-endedness evidence | Novelty, persistence, learnability, transfer, and controls are required |

CodonTrace Genesis does **not** treat placeholder data, empty digests, fake evidence, `not_run:*`, NaN, or Infinity as positive scientific evidence.

---

## Release status

This is an **alpha research software release**.

It is suitable for:

- exploring the CodonTrace Genesis API,
- running deterministic examples,
- reviewing scientific evidence schemas,
- building controlled ALife and digital evolution experiments,
- extending mechanism-level tests.

It is not yet a final scientific benchmark claim or a peer-reviewed result package.

---

## Repository layout

```text
codontrace-genesis/
├── src/codontrace/             # Library source
├── tests/                      # Unit, integration, release, and science-gate tests
├── examples/                   # Example experiments and validation smoke runs
├── docs/                       # Documentation and release notes
├── .github/workflows/          # CI and publishing workflows
├── README.md                   # Project overview
├── pyproject.toml              # Packaging metadata
├── CITATION.cff                # Citation metadata
├── CHANGELOG.md                # Release history
└── LICENSE                     # License
```

---

## Examples

Run a quick validation smoke:

```bash
python examples/genesis_phase3_validation_smoke.py
```

Run a toolchain pilot:

```bash
python examples/genesis_toolchain_pilot.py --out artifacts/pilots/toolchain
```

Run a capsule utility pilot:

```bash
python examples/genesis_capsule_utility_pilot.py --out artifacts/pilots/capsule_utility
```

Run a QD selection pilot:

```bash
python examples/genesis_qd_selection_pilot.py --out artifacts/pilots/qd_selection
```

---

## Testing

```bash
python -m compileall -q src tests examples tools
python -m pytest tests/genesis_gates -q
python -m pytest tests/science_gates -q
python -m pytest tests -q
```

The public alpha CI focuses on Python 3.13 and 3.14.

---

## Documentation map

| Document | Purpose |
|---|---|
| `README.md` | Public project overview |
| `CHANGELOG.md` | Release history |
| `RELEASE_EVIDENCE.md` | Release evidence and claim boundaries |
| `docs/` | Technical notes and extended documentation |
| `examples/` | Runnable experiment examples |
| `tests/` | Regression, science-gate, integration, and release tests |

---

## Publication roadmap

CodonTrace Genesis is prepared for staged public research release:

1. **GitHub public alpha release**
2. **PyPI alpha package**
3. **Zenodo DOI archival**
4. **Technical whitepaper**
5. **Expanded benchmark report**
6. **JOSS-style research software paper preparation**
7. **Heavier multi-seed scientific campaigns**

The whitepaper and benchmark reports are planned as separate research artifacts, not as overclaims inside the README.

---

## Topics and discoverability

Recommended GitHub topics:

```text
artificial-life
digital-evolution
open-endedness
evolutionary-computation
quality-diversity
causal-inference
replayable-research
research-software
python
alife
genesis
codontrace
```

---

## Citation

If you use CodonTrace Genesis in research, prototypes, technical evaluation, or derivative work, please cite the repository release.

A `CITATION.cff` file is included for citation-aware tools.

```bibtex
@software{codontrace_genesis_2026,
  title = {CodonTrace Genesis},
  author = {Jamei, Parvaz},
  version = {0.3.0a1},
  url = {https://github.com/Parvaz-Jamei/codontrace-genesis}
}
```

---

## License

See [`LICENSE`](LICENSE).

---

## Author

**Parvaz Jamei**  
Embedded / Industrial IoT / Edge AI / Digital Evolution Research Software  
GitHub: [@Parvaz-Jamei](https://github.com/Parvaz-Jamei)

---

<div align="center">

**CodonTrace Genesis**  
Deterministic evidence for digital evolution, causal mechanisms, and replayable ALife research.

</div>
