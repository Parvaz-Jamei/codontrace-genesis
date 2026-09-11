# CodonTrace Genesis

### Replayable digital evolution, causal mechanism auditing, and evidence-gated ALife research software.

[![PyPI](https://img.shields.io/pypi/v/codontrace?label=PyPI)](https://pypi.org/project/codontrace/)
[![Python](https://img.shields.io/badge/Python-3.11%E2%80%933.14-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![CI](https://github.com/Parvaz-Jamei/codontrace-genesis/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/Parvaz-Jamei/codontrace-genesis/actions/workflows/ci.yml)
[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.20337435.svg)](https://doi.org/10.5281/zenodo.20337435)
[![License: AGPL v3+](https://img.shields.io/badge/License-AGPL%20v3%2B-blue.svg)](LICENSE)

**CodonTrace Genesis** is a Python research library for building, replaying, auditing, and evaluating digital-evolution experiments with deterministic evidence trails, mechanism-level records, controlled ablations, and explicit claim gates.

It is built for researchers and developers who want to test ALife and evolutionary-AI hypotheses with **replayable evidence** rather than final-outcome screenshots or unverifiable claims.

---

## At a glance

| Field | Current status |
|---|---|
| Package | `codontrace` |
| Public beta | `0.3.0b2` |
| Python | `3.11–3.14` verified; latest stable checked for this beta line: `3.14.5` |
| DOI | `10.5281/zenodo.20337435` |
| License | `AGPL-3.0-or-later` |
| Main focus | Digital evolution, causal audit, replayable ALife experiments, benchmark protocols, claim-gated evidence |
| Claim boundary | Research software and evidence infrastructure; not a final proof of AGI, consciousness, collective intelligence, or benchmark superiority |

---

## Why CodonTrace Genesis?

Digital-evolution and artificial-life experiments often produce fascinating behavior, but the hard part is not only running the simulation.

The hard part is answering questions like:

- Can the result be replayed?
- Which mechanism changed the outcome?
- Did memory influence later action?
- Did a signal become useful, or was it just present?
- Did inherited compression improve child outcomes?
- Did a role actually matter when ablated?
- Did a group outperform individual/control baselines?
- Which claims are supported, and which claims must stay blocked?

**CodonTrace Genesis** focuses on that evidence layer.

It provides a deterministic, library-first substrate for experiments involving mutation, birth, death, reproduction, lineage, memory, capsule-mediated signaling, role instrumentation, quality-diversity, open-endedness-oriented metrics, and controlled claim review.

---

## What it is

CodonTrace Genesis is:

- a Python research library for controlled digital-evolution and ALife experiments,
- a replay/audit-first evidence layer,
- a mechanism instrumentation toolkit,
- a benchmarkable research-software package,
- a claim-gated workflow for scientific discipline.

## What it is not

CodonTrace Genesis is **not** currently presented as:

- proof of artificial general intelligence,
- proof of consciousness,
- proof of collective intelligence,
- proof of open-ended intelligence as a settled result,
- a biological evolution simulator,
- a replacement for Avida, MABE, DEAP, QDax, pyribs, or similar tools.

The project is ambitious, but claims must pass evidence gates.

---

## Research transparency

CodonTrace keeps the most important scientific boundaries in separate reviewable documents:

| Document | Purpose |
|---|---|
| [`CLAIMS.md`](CLAIMS.md) | Allowed, candidate, and blocked claims for the current public-beta release |
| [`docs/PHASE_D_LITERATURE.md`](docs/PHASE_D_LITERATURE.md) | Phase D multi-generation evidence literature checklist (MODES / Bedau / OEE hallmarks) |
| [`docs/PHASE_E_LITERATURE.md`](docs/PHASE_E_LITERATURE.md) | Phase E capsule / memory / role / deme / plasticity literature checklist |
| [`docs/SCIENTIFIC_AUTHORITIES_2026.md`](docs/SCIENTIFIC_AUTHORITIES_2026.md) | 2026 eval-bugfix → literature mapping (MODES, Channon Tokyo Type 1 *measurement only*, Avida 2.14.0, plasticity protocol). Not intelligence/OEE proof |
| [`docs/STUDIO_PHASE1_EXECUTION_SPEC.html`](docs/STUDIO_PHASE1_EXECUTION_SPEC.html) + [`docs/STUDIO_PHASE1_EXECUTION_SPEC.md`](docs/STUDIO_PHASE1_EXECUTION_SPEC.md) | Phase 1 Studio handoff while keeping this repo a core library; HTML for designed handoff, Markdown for GitHub review |
| [`docs/STUDIO_BOUNDARY.md`](docs/STUDIO_BOUNDARY.md) | Boundary policy preventing UI/server drift into core |
| [`docs/PERFORMANCE_PHASE1.md`](docs/PERFORMANCE_PHASE1.md) | Safe live-performance plan without changing scientific semantics |
| [`REPRODUCIBILITY.md`](REPRODUCIBILITY.md) | Installation, validation tiers, benchmark execution, artifact preservation, and version discipline |
| [`BENCHMARKS.md`](BENCHMARKS.md) | Benchmark protocols, runner commands, smoke result interpretation, artifact policy, and claim boundaries |

These documents are part of the research-software design, not just documentation polish.

---

## Key capabilities

| Area | Capability |
|---|---|
| Digital evolution | Genome, mutation, birth, death, reproduction gates, lineage, selection, survival diagnostics |
| Replayability | Deterministic experiment specs, runtime digests, replay records, artifact manifests |
| Evidence integrity | Claim manifests, blocked reasons, output completeness, export status, negative evidence handling |
| Causal mechanisms | Ablation policies, treatment/control variants, delayed outcome windows, counterfactual-style summaries |
| Capsule signaling | Capsule transfer, adoption, utility scoring, source-fitness controls, cost records |
| Memory and learning | Memory-use records, delayed reward surfaces, signal-memory-action paths |
| Skill compression | Skill-compression policies, inheritance records, child outcome audit surfaces |
| Roles and social behavior | Role persistence, role contribution, partner interaction, social instrumentation |
| Quality diversity | QD selection audit, parent feedback audit, diversity-oriented evidence records |
| Open-endedness | Novelty, complexity, adaptive success, lineage persistence, behavior-space expansion, learnability |
| Reviewability | Tests, examples, benchmark runner, citation metadata, release evidence, DOI, AGPL license |

---

## Installation

> Compatibility note: this beta line is verified for Python `3.11`, `3.12`, `3.13`, and `3.14` on OS-independent core code. Python `3.14.5` is the latest stable Python release checked for this handoff; Python `3.15+` must be added only after CI verification.


### GitHub Actions compatibility

The release CI uses a real cross-OS smoke matrix for `ubuntu-latest`, `windows-latest`, and `macos-latest` across Python `3.11`, `3.12`, `3.13`, and `3.14`. The workflows intentionally use current official action majors checked for this beta handoff: `actions/checkout@v6`, `actions/setup-python@v6`, `actions/upload-artifact@v7`, and `actions/download-artifact@v8`.

### From PyPI

```bash
pip install codontrace==0.3.0b2
```

### Optional research extras

```bash
pip install "codontrace[research]==0.3.0b2"
pip install "codontrace[causal]==0.3.0b2"
pip install "codontrace[qd]==0.3.0b2"
```

### From source

```bash
git clone https://github.com/Parvaz-Jamei/codontrace-genesis.git
cd codontrace-genesis
python -m pip install -e ".[dev,research,causal,qd]"
```

Verify the installed version:

```bash
python -c "import codontrace; print(codontrace.__version__)"
```

Expected:

```text
0.3.0b2
```

---

## Quick start

Use the beginner API first. It keeps setup small and returns the agent, world, trace, and optional explanation without manually creating low-level runtime objects.

```python
from codontrace import WhiteBoxAgent, World2D

world = World2D.from_ascii("""
....
.A*.
....
""")

agent = WhiteBoxAgent.from_world(world, genome="101111000", initial_atp=5.0)
result = agent.run_trial(world, steps=3, explain=True)

print(result.agent.position)
print(result.explanation.summary if result.explanation else "no explanation")
```

---

## Core API

For Genesis-level research runs, use the explicit experiment spec and engine APIs.

```python
from codontrace.genesis import GenesisEngine, GenesisExperimentSpec

spec = GenesisExperimentSpec(seed=42, tick_count=32, population_max=8)
result = GenesisEngine.from_spec(spec).run_ticks()

print(result.digest()[:24])
print(len(result.engine_frames))
```

### Phase A life-loop / ecology preset

Short eat → survive → reproduce experiments should use the explicit
`GenesisRuntimeProfile.life_loop_world()` preset instead of relying on empty
research defaults (`ResourceConfig.density=0`, `ReproductionConfig` SAME_CELL).

The preset is a Darwinian life-loop *substrate* grounded in digital-evolution
practice (Avida limited-resource ecology; energy-budget ALife such as JaxLife /
EEDx-style maintenance costs). It is not an Avida replacement and does not
claim benchmark superiority.

It places a **small, depletable** food pool (two patches, `max_resources=3`)
with **partial** respawn (`respawn_rate=0.4`), so eat reduces local/global
availability and two foragers can compete. Organisms pay an opt-in **basal
ATP drain** every tick and die with an explicit `starvation` reason when
runtime ATP stays at or below the configured floor. Adjacent empty-cell
placement is the preset default (SAME_CELL remains the research default;
`REPLACE_OCCUPIED` is an explicit overwrite option only). COPY_SELF is gated
on AliveGate plus runtime ATP so eat-capable lineages can out-reproduce
WAIT/starved controls. Inheritance stays asexual parent→mutate→child
unless an explicit `reproduction_mode` / `life_loop_world(reproduction_mode=...)`
selects Phase B two-parent positional crossover. Seasonal / fluctuating
environments are opt-in via `dynamic_environment_world()` or
`life_loop_world(environment=...)`. Multi-generation instinct/behavior
*measurement* is opt-in via `build_multi_generation_evidence_pack` and does
not change these presets. Phase E capsule/memory/role/deme substrate effects
are opt-in via `phase_e_substrate_world()` and do not change A–D defaults.

Phase B adds an optional sexual recombination substrate grounded in
Avida `divide-sex` / birth-chamber mechanics (Misevic, Ofria, Lenski 2006;
`avida.cfg` `RECOMBINATION_GROUP`): incipient genomes wait in a pairing
queue, exchange one continuous corresponding positional region, then
ordinary mutation runs. Config knobs mirror Avida (`recombination_prob`,
`same_length_only`, `two_fold_cost_sex`, `max_birth_wait_ticks`, chamber
capacity). Research presets and the default life-loop run stay asexual so
existing replay digests remain stable. This is not an Avida replacement.
Diploid meiosis (Aevol Eukaryote) is deferred.

Phase C adds an optional dynamic environment substrate grounded in Avida
`environment.cfg` `RESOURCE` lines (Ofria & Wilke 2004; Cooper/Ofria
chemostat ecosystems) and Avida-ED unlimited / limited / chemostat /
periodic modes: per-resource `initial` / `inflow` / `outflow` pools,
deterministic periodic or seeded regime switches (high-food vs low-food,
or two niche maps), global and/or local patches with optional diffusion
and decay hooks, digest-backed env events, and replay verification of
environment trajectory digests. Default life-loop and sexual presets stay
static. This is not a claim that phenotypic plasticity evolved, and not an
Avida replacement.

Phase D adds a post-hoc multi-generation evidence API grounded in the MODES
toolbox (Dolson et al. 2019; persistence-filtered change/novelty/complexity/
ecological potential), Bedau evolutionary activity statistics, and ALife OEE
encyclopedia / ISAL 2024 MODES-assessment reporting practice. Callers get a
first-class `MultiGenerationEvidencePack` (JSON + digest) rather than only an
external analyze-mode dump. Metric deltas are **runtime observations**.
ClaimGate keeps `instinct_improved` below publication grade without multi-seed
protocol objects and blocks open-ended intelligence.

Phase E adds an opt-in substrate for **real** organism-local or lineage
capsule/memory effects (subsequent action choice, ATP, or task eligibility),
Avida-inspired role / propagule-eligibility gates, deme containers with a
Goldsby-style messaging buffer (`send_message` / `retrieve_message` /
`broadcast_message` / `block_propagation`), a phenotypic-plasticity
experimental-design object over Phase C `sense-react` cues, OntoAvida-style
phenotype/transcriptome evidence export, and an `AvidaParityProtocolSpec`
head-to-head recipe. Defaults stay off. This is not proved learning, evolved
plasticity, collective intelligence, or an Avida replacement.

This is a **software capability / runtime observation** surface. It does not
prove life, intelligence, cooperation, instinct evolution, or OEE.

```python
from codontrace.genesis import GenesisEngine, GenesisRuntimeProfile

spec = GenesisRuntimeProfile.life_loop_world(seed=7, tick_count=12, population=6)
result = GenesisEngine.from_spec(spec).run_ticks()
print(result.digest()[:24])

spec = GenesisRuntimeProfile.dynamic_environment_world(
    seed=7, tick_count=12, population=6
)
result = GenesisEngine.from_spec(spec).run_ticks()
print(result.digest()[:24])

from codontrace.genesis import build_multi_generation_evidence_pack

pack = build_multi_generation_evidence_pack(result, spec=spec)
print(pack.claim_ceiling, pack.digest[:24])

from codontrace.genesis import GenesisRuntimeProfile as Profile

phase_e = Profile.phase_e_substrate_world(seed=7, tick_count=8, population=4)
print(phase_e.metadata["runtime_profile"])
```

Print-only smokes: `examples/genesis_life_loop.py`,
`examples/genesis_sexual_recombination.py`,
`examples/genesis_dynamic_environment.py`,
`examples/genesis_multi_generation_evidence.py`,
`examples/genesis_phase_e_substrate.py`.

---

## Benchmark smoke

CodonTrace Genesis includes a lightweight benchmark runner for software review, reproducibility checks, and artifact-generation validation.

### Smoke test

```bash
python -m pytest tests/examples/test_collective_joss_evidence_benchmark_smoke.py -q
```

### Smoke benchmark

```bash
PYTHONPATH=src python examples/collective_joss_evidence_benchmark.py   --out outputs/joss_evidence_smoke   --profile smoke   --seed-count 1   --ticks 3   --population 4   --workers 1   --max-runs 6   --per-run-timeout 90
```

Expected core artifacts:

```text
run_config.json
summary.json
run_records.csv
feature_matrix.csv
counterfactual_pairs.csv
claim_readiness.json
artifact_manifest.json
environment.txt
report.html
```

The smoke benchmark is a functionality and artifact-generation check. It is not a proof of collective intelligence.

For benchmark levels and interpretation rules, see [`BENCHMARKS.md`](BENCHMARKS.md).

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
        ├── artifact digests
        ├── replay policies
        ├── evidence manifests
        ├── causal mechanism reports
        └── claim-gated summaries
```

A feature is considered scientifically useful only when it is wired through configuration, runtime behavior, records, digests, manifests, examples, tests, and claim boundaries.

---

## Core research mechanisms

### Digital evolution substrate

CodonTrace records mutation, birth, death, reproduction gates, child admission, lineage growth, population dynamics, energy accounting, fitness breakdowns, and replay evidence.

### Capsule-mediated signaling

Capsules are the canonical information-transfer primitive. They support controlled testing of transfer, adoption, utility, cost, source-fitness, and memory-link hypotheses.

### Signal → memory → action audit

The library is designed to distinguish “a signal existed” from “a signal influenced memory, later action, and an outcome.”

### Skill compression and inheritance

CodonTrace exposes skill-compression, inheritance, ADF, and child-outcome audit surfaces for testing whether compressed learned behavior changes offspring outcomes.

### Role and social behavior

Role records, partner interactions, role contribution, role persistence, and heldout-partner protocols support careful study of social and collective-behavior hypotheses.

### Quality diversity and open-endedness

QD and open-endedness-oriented records support descriptive and candidate evidence around diversity, novelty, complexity growth, adaptive success, lineage persistence, and learnability.

---

## Claim policy

CodonTrace Genesis uses explicit claim levels.

| Claim level | Meaning |
|---|---|
| Software capability | The mechanism/API/record exists and is testable |
| Runtime observation | The mechanism was observed in a valid run |
| Candidate evidence | Treatment/control comparison exists |
| Mechanism support | Ablation/intervention/counterfactual-style evidence supports a mechanism |
| Replicated effect | Effect is stable across enough seeds/configurations |
| Publication-grade claim | Archived artifacts, statistics, controls, and limitations are available |

Blocked for the current release unless future evidence gates pass:

- proven AGI,
- proven consciousness,
- proven collective intelligence,
- proven open-ended intelligence,
- benchmark superiority over established tools,
- causal claims without ablation or intervention evidence.

Full policy: [`CLAIMS.md`](CLAIMS.md).

---

## Repository layout

```text
codontrace-genesis/
├── src/codontrace/                # Library source
├── tests/                         # Unit, integration, science-gate, release, and example tests
├── examples/                      # Runnable examples and benchmark runners
├── docs/                          # Technical notes and extended documentation
├── .github/workflows/             # CI and publishing workflows
├── README.md                      # Public project overview
├── CLAIMS.md                      # Scientific claim policy
├── REPRODUCIBILITY.md             # Reproducibility and validation guide
├── BENCHMARKS.md                  # Benchmark protocols and interpretation rules
├── RELEASE_EVIDENCE.md            # Release evidence and claim boundaries
├── CITATION.cff                   # Citation metadata
├── CHANGELOG.md                   # Release history
├── pyproject.toml                 # Packaging metadata
├── LICENSE                        # AGPL-3.0-or-later license
└── NOTICE                         # Attribution and licensing notice
```

---

## Testing

```bash
python -m compileall -q src tests examples tools
python -m pytest tests/genesis_gates -q
python -m pytest tests/science_gates -q
python -m pytest tests/examples/test_collective_joss_evidence_benchmark_smoke.py -q
python -m pytest tests -q
```

For validation tiers and heavier manual runs, see [`REPRODUCIBILITY.md`](REPRODUCIBILITY.md).

---

## Documentation map

| Document | Purpose |
|---|---|
| [`README.md`](README.md) | Public project overview |
| [`CLAIMS.md`](CLAIMS.md) | Scientific claim policy and evidence levels |
| [`REPRODUCIBILITY.md`](REPRODUCIBILITY.md) | Installation, validation tiers, artifact preservation, and version discipline |
| [`BENCHMARKS.md`](BENCHMARKS.md) | Benchmark protocols, runner commands, smoke result interpretation, and claim boundaries |
| [`RELEASE_EVIDENCE.md`](RELEASE_EVIDENCE.md) | Release evidence and claim boundaries |
| [`CHANGELOG.md`](CHANGELOG.md) | Release history |
| [`docs/`](docs/) | Technical notes and extended documentation |
| [`examples/`](examples/) | Runnable experiment examples and benchmark runners |
| [`tests/`](tests/) | Regression, science-gate, integration, release, and example smoke tests |

---

## Publication roadmap

CodonTrace Genesis is being prepared through staged research-software maturity:

1. public GitHub beta,
2. PyPI package,
3. Zenodo DOI archival,
4. claim/reproducibility/benchmark documentation,
5. benchmark smoke artifacts,
6. technical whitepaper,
7. JOSS-style research software paper preparation,
8. heavier multi-seed empirical campaigns,
9. separate scientific papers for empirical claims if evidence gates pass.

JOSS is treated as a software-publication path. Strong scientific claims belong in separate empirical papers when evidence is sufficient.

---

## Citation

If you use CodonTrace Genesis in research, prototypes, technical evaluation, benchmark work, reports, or derivative research artifacts, please cite the versioned software release.

```bibtex
@software{codontrace_genesis_2026,
  title = {CodonTrace Genesis},
  author = {Jamei, Parvaz},
  version = {0.3.0b2},
  doi = {10.5281/zenodo.20337435},
  url = {https://github.com/Parvaz-Jamei/codontrace-genesis}
}
```

A [`CITATION.cff`](CITATION.cff) file is included for citation-aware tools.

Use of the software does not automatically imply co-authorship. Co-authorship may be appropriate when there is substantial collaboration in experimental design, analysis, interpretation, validation, or manuscript writing.

---

## License

CodonTrace Genesis is licensed under the **GNU Affero General Public License v3.0 or later** (`AGPL-3.0-or-later`).

This license is selected to keep modified, redistributed, and network-deployed versions open, attributable, and scientifically inspectable.

Commercial or proprietary use cases that cannot comply with `AGPL-3.0-or-later` may contact the author for a separate commercial license.

See [`LICENSE`](LICENSE) and [`NOTICE`](NOTICE).

---

## Author

**Parvaz Jamei**
Embedded / Industrial IoT / Edge AI / Digital Evolution Research Software

GitHub: [@Parvaz-Jamei](https://github.com/Parvaz-Jamei)

---

**CodonTrace Genesis**
Replayable evidence for digital evolution, causal mechanisms, and ALife research.
