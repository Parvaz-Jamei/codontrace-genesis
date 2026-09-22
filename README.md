# CodonTrace Genesis

### Replayable digital evolution, causal mechanism auditing, and evidence-gated ALife research software.

[![PyPI](https://img.shields.io/pypi/v/codontrace?label=PyPI)](https://pypi.org/project/codontrace/)
[![Python](https://img.shields.io/badge/Python-3.11%E2%80%933.14-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![CI](https://github.com/Parvaz-Jamei/codontrace-genesis/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/Parvaz-Jamei/codontrace-genesis/actions/workflows/ci.yml)
[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.20337435.svg)](https://doi.org/10.5281/zenodo.20337435)
[![License: AGPL v3+](https://img.shields.io/badge/License-AGPL%20v3%2B-blue.svg)](LICENSE)

CodonTrace Genesis is a Python library for running small digital-evolution
experiments that you can replay later. You start a tiny world, let simple
agents eat, survive, and reproduce, and the library writes down what happened
as checkable records. Use it when you want to test an evolutionary idea with
evidence instead of a screenshot. It is research software. It does **not**
claim that the agents are intelligent.

The installable package is `codontrace`. Product naming for contributors
lives in [`CONTRIBUTING.md`](CONTRIBUTING.md) and [`STYLE.md`](STYLE.md).

---

## What it is

- a Python research library for controlled digital-evolution and ALife experiments
- a replay / audit-first evidence layer (specs, runtime digests, manifests)
- a mechanism instrumentation toolkit (ablations, treatment/control, delayed outcomes)
- a claim-gated workflow: software capability and runtime observations are allowed; strong scientific conclusions are not auto-promoted

## What it is not

CodonTrace Genesis is **not** currently presented as:

- proof of artificial general intelligence, consciousness, or collective intelligence
- proof of open-ended intelligence, or a Tokyo Type 1 *pass* (Channon 2024)
- a biological evolution simulator or wet-lab chemistry engine
- a replacement for Avida, MABE, DEAP, QDax, pyribs, or similar tools
- a physical-robot research platform (ESP32 Moj-ه is an engineering stub / `SimEsp32Bridge` only)
- an Avida/MABE literature-compatible campaign runner (ClaimGate adapters are skeletons until audited published `.dat`/CSV exist)

The project is ambitious. Claims must pass evidence gates. See [`CLAIMS.md`](CLAIMS.md) and [`docs/WHY_NOT_INTELLIGENCE_YET.md`](docs/WHY_NOT_INTELLIGENCE_YET.md).

---

## Status

| Field | Current status |
|---|---|
| Package | `codontrace` |
| Public PyPI tip | `0.3.0b4` — Phases H–L + HE01 SCHEMA v7 + discovery ClaimGate pipeline. Confirm on [PyPI](https://pypi.org/project/codontrace/). |
| GitHub `main` | Development identity `0.3.0b4.dev1` (ahead of the published cut). |
| Python | `3.11–3.14` |
| DOI | `10.5281/zenodo.20337435` |
| License | `AGPL-3.0-or-later` |
| Official GitHub release | [`v0.3.0b4`](https://github.com/Parvaz-Jamei/codontrace-genesis/releases/tag/v0.3.0b4) (set older handoff tags to pre-release so Latest stays here) |
| HE01 | SCHEMA v7 locked; ceiling at most `intervention_supported` when the full rule holds |
| HE02 | Research null after analysis v1b; ceiling stays `runtime_observation` |
| HE03 | Code + prereg present; research `results_v1` is absent on purpose |
| Claim ceiling | Research software and evidence infrastructure. Not a proof of AGI, consciousness, collective intelligence, Tokyo Type 1 passed, or Avida replacement. |

### Phases A–L

Phases A–G remain the earlier `0.3.0b3` substrate. Phases H–L + HE01 SCHEMA v7 + discovery ClaimGate pipeline ship in public `0.3.0b4`.

| Phase | What landed | Claim ceiling |
|---|---|---|
| **A** | Darwinian life-loop ecology preset (`life_loop_world`: eat → survive → asexual reproduce) | `runtime_observation` |
| **B** | Avida-parity sexual recombination (opt-in; defaults stay asexual) | `runtime_observation` |
| **C** | Dynamic / fluctuating environment (chemostat, regimes, patches) | `runtime_observation` |
| **D** | Multi-generation evidence pack; Tokyo Type 1 *measurement* only | `oee_measurement_only` / `tokyo_type1_measurement_only` |
| **E** | Capsule / memory / role / deme substrate (opt-in) | `runtime_observation` |
| **F** | Multi-seed deme payoff campaigns; division-of-labor *metrics* | `runtime_observation` |
| **G** | Named-materials / chemistry-effect overlay (opt-in) | `runtime_observation` |
| **H** | Literature RAG; communication-ablation and group-vs-individual harnesses | `runtime_observation` |
| **I** | Heldout partners; evolved DoL; MLS outcome; export-of-fitness scaffold | `runtime_observation`; flags earned at research scale only; smoke never earns |
| **J** | Independent digest replay; Price-equation scaffold | `collective_intelligence_candidate` only with **full honest flags including replay** |
| **K** | Coordination-instruction analog; Goldsby-scale CPU-delay harness; Price transmission; conflict-suppression hooks | `runtime_observation`; smoke never earns |
| **L** | Closer Avida `ORGANISM_MESSAGING` / `DEME_GROUP` analogs; Goldsby-aligned specialist measurement | `runtime_observation`; analog, **not** an Avida C++ port |

Allowed when the evidence objects actually exist: `runtime_observation`, `oee_measurement_only`, `tokyo_type1_measurement_only`, and `collective_intelligence_candidate` (full honest flags only, including replay).

**Still blocked:** bare `collective_intelligence`, `intelligence`, AGI, `tokyo_type1_passed`, Avida replacement, and related aliases. Smoke never auto-sets ClaimGate flags. Digests are never faked.

North star: eventually produce honest collective-work / intelligence-*pathway* outputs. That is not the same as unlocking those claims.

---

## Installation

The published wheel is `codontrace==0.3.0b4` (Phases H–L + HE01 SCHEMA v7 + discovery ClaimGate pipeline). `main` is `0.3.0b4.dev1` and is not a PyPI recut. Older `0.3.0b3` remains the A–G substrate tip.

Python `3.11–3.14`. CI smokes `ubuntu-latest`, `windows-latest`, and `macos-latest` on that range.

### From PyPI (`0.3.0b4`)

```bash
pip install codontrace==0.3.0b4
```

Optional research extras:

```bash
pip install "codontrace[research]==0.3.0b4"
pip install "codontrace[causal]==0.3.0b4"
pip install "codontrace[qd]==0.3.0b4"
```

### From source (`main`, may be ahead of PyPI)

```bash
git clone https://github.com/Parvaz-Jamei/codontrace-genesis.git
cd codontrace-genesis
python -m pip install -e ".[dev,research,causal,qd]"
```

```bash
python -c "import codontrace; print(codontrace.__version__)"
```

A PyPI install of the current tip prints `0.3.0b4`. An editable install from `main` prints `0.3.0b4.dev1`. Do not treat the version tuple as a phase fence.

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

Short eat → survive → reproduce experiments should use
`GenesisRuntimeProfile.life_loop_world()` instead of empty research defaults
(`ResourceConfig.density=0`, `ReproductionConfig` SAME_CELL). The preset is a
Darwinian life-loop *substrate*. It is not an Avida replacement.

```python
from codontrace.genesis import GenesisEngine, GenesisRuntimeProfile

spec = GenesisRuntimeProfile.life_loop_world(seed=7, tick_count=12, population=6)
result = GenesisEngine.from_spec(spec).run_ticks()
print(result.digest()[:24])
```

Opt-in presets and measurement packs (sexual recombination, fluctuating
environments, multi-generation / Tokyo Type 1 *measurement*, Phase E substrate,
materials, RAG, and H–L CI harnesses) are library APIs with the ceilings in
the status table. Defaults stay off so A–E digest pins remain stable.

Print-only smokes live under [`examples/`](examples/).

---

## Benchmark smoke

The smoke runner is a functionality and artifact-generation check. It is **not**
a proof of collective intelligence.

```bash
python -m pytest tests/examples/test_collective_joss_evidence_benchmark_smoke.py -q
```

```bash
PYTHONPATH=src python examples/collective_joss_evidence_benchmark.py   --out outputs/joss_evidence_smoke   --profile smoke   --seed-count 1   --ticks 3   --population 4   --workers 1   --max-runs 6   --per-run-timeout 90
```

Expected core artifacts: `run_config.json`, `summary.json`, `run_records.csv`,
`feature_matrix.csv`, `counterfactual_pairs.csv`, `claim_readiness.json`,
`artifact_manifest.json`, `environment.txt`, `report.html`.

Levels and interpretation: [`BENCHMARKS.md`](BENCHMARKS.md).

---

## Claim policy

| Claim level | Meaning |
|---|---|
| Software capability | The mechanism / API / record exists and is testable |
| Runtime observation | The mechanism was observed in a valid run |
| Candidate evidence | Treatment / control comparison exists |
| Mechanism support | Ablation / intervention / counterfactual-style evidence supports a mechanism |
| Replicated effect | Effect is stable across enough seeds / configurations |
| Publication-grade claim | Archived artifacts, statistics, controls, and limitations are available |

`ScientificClaimGate` can allow `collective_intelligence_candidate` only when
the full honest flag set is present, including replay. It does **not** allow
bare `collective_intelligence`, `intelligence`, AGI, `tokyo_type1_passed`, or
Avida replacement.

Full policy: [`CLAIMS.md`](CLAIMS.md).

---

## Next steps

Library-complete beta is not “done.” The next work is **not** more empty Phase
letters.

1. **Do not recut PyPI `0.3.0b4`.** The next public wheel is `0.3.0b5` only after CI is green on a release identity.
2. **Keep `main` on `0.3.0b4.dev1`** until that cut. Mark stale GitHub handoff releases as pre-release so Latest stays on [`v0.3.0b4`](https://github.com/Parvaz-Jamei/codontrace-genesis/releases/tag/v0.3.0b4).
3. **HE03 research campaign** — run only against the locked prereg; do not fabricate `results_v1`.
4. **Lint/type inventory** — `lint-type` remains non-blocking until the ruff/mypy backlog is reduced in its own PR.
5. **Candidate claims** — `collective_intelligence_candidate` only if the full honest flags, including replay, are actually earned.
6. **OEE later** — Tokyo Type 1 *pass* and open-ended intelligence remain blocked.

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

A feature is scientifically useful only when it is wired through configuration,
runtime behavior, records, digests, manifests, examples, tests, and claim
boundaries.

---

## Documentation

| Document | Purpose |
|---|---|
| [`CLAIMS.md`](CLAIMS.md) | Allowed, candidate, and blocked claims |
| [`docs/protocol/CLAIM_LADDER_PROTOCOL_v0.1.md`](docs/protocol/CLAIM_LADDER_PROTOCOL_v0.1.md) | Claim-ladder protocol v0.1 (design + grade ALife claims; Wave 3) |
| [`docs/WHY_NOT_INTELLIGENCE_YET.md`](docs/WHY_NOT_INTELLIGENCE_YET.md) | Literature-vs-reality barrier map; not close to AGI |
| [`docs/PHASE_H_CI_AI_PATH.md`](docs/PHASE_H_CI_AI_PATH.md) | Phase H: RAG + ablation / effect-size harnesses |
| [`docs/PHASE_I_CI_EVIDENCE.md`](docs/PHASE_I_CI_EVIDENCE.md) | Phase I: heldout / evolved DoL / MLS / export-of-fitness |
| [`docs/PHASE_J_REPLAY_CI.md`](docs/PHASE_J_REPLAY_CI.md) | Phase J: honest digest replay + Price scaffold |
| [`docs/PHASE_K_CI_DEPTH.md`](docs/PHASE_K_CI_DEPTH.md) | Phase K: coordination, Goldsby-scale harness, Price transmission |
| [`docs/PHASE_INDEX.md`](docs/PHASE_INDEX.md) | Pointer index for Phases H–L and honesty docs |
| [`docs/PHASE_L_AVIDA_FIDELITY.md`](docs/PHASE_L_AVIDA_FIDELITY.md) | Phase L: ORGANISM_MESSAGING / DEME_GROUP analogs |
| [`docs/HARD_EXPERIMENT_01.md`](docs/HARD_EXPERIMENT_01.md) | Hard experiment 01: capsule source-bias measurement paper (not a Phase M) |
| [`docs/CLAIMGATE_STANDALONE.md`](docs/CLAIMGATE_STANDALONE.md) | Wave 2 simulator-agnostic ClaimGate auditor (public 0–5; not a Tokyo/OEE pass) |
| [`docs/ARCHITECTURE_PORTS.md`](docs/ARCHITECTURE_PORTS.md) | Engine vs adapter vs DomainProfile; not a second engine per domain |
| [`docs/ENGINE_REPLAY_CONTRACT.md`](docs/ENGINE_REPLAY_CONTRACT.md) | Replay hashes and run-identity types extracted from `engine.py` |
| [`CONTRIBUTING.md`](CONTRIBUTING.md) / [`STYLE.md`](STYLE.md) | Product naming: **CodonTrace Genesis**; package `codontrace` |
| [`docs/SCIENTIFIC_AUTHORITIES_2026.md`](docs/SCIENTIFIC_AUTHORITIES_2026.md) | Feature × authority matrix (landed / partial / deferred) |
| [`docs/rag/README.md`](docs/rag/README.md) | Literature RAG corpus (measurement design, not intelligence evidence) |
| [`REPRODUCIBILITY.md`](REPRODUCIBILITY.md) | Install, validation tiers, artifact preservation |
| [`BENCHMARKS.md`](BENCHMARKS.md) | Benchmark protocols and claim boundaries |
| [`RELEASE_EVIDENCE.md`](RELEASE_EVIDENCE.md) | Release evidence pack (see file for which public wheel it covers) |

Phase literature checklists: [`PHASE_D_LITERATURE.md`](docs/PHASE_D_LITERATURE.md),
[`PHASE_E_LITERATURE.md`](docs/PHASE_E_LITERATURE.md),
[`PHASE_G_MATERIALS_LITERATURE.md`](docs/PHASE_G_MATERIALS_LITERATURE.md).
Studio / performance notes stay out of core:
[`STUDIO_BOUNDARY.md`](docs/STUDIO_BOUNDARY.md).

---

## Testing

```bash
python -m compileall -q src tests examples tools
python -m pytest tests/genesis_gates -q
python -m pytest tests/science_gates -q
python -m pytest tests/examples/test_collective_joss_evidence_benchmark_smoke.py -q
python -m pytest tests -q
```

Validation tiers: [`REPRODUCIBILITY.md`](REPRODUCIBILITY.md).

---

## Citation

If you use CodonTrace Genesis in research, prototypes, technical evaluation,
benchmark work, reports, or derivative research artifacts, please cite the
versioned software release.

```bibtex
@software{codontrace_genesis_2026,
  title = {CodonTrace Genesis},
  author = {Jamei, Parvaz},
  version = {0.3.0b4},
  doi = {10.5281/zenodo.20337435},
  url = {https://github.com/Parvaz-Jamei/codontrace-genesis}
}
```

A [`CITATION.cff`](CITATION.cff) file is included for citation-aware tools.

Use of the software does not automatically imply co-authorship. Co-authorship
may be appropriate when there is substantial collaboration in experimental
design, analysis, interpretation, validation, or manuscript writing.

---

## License

CodonTrace Genesis is licensed under the **GNU Affero General Public License
v3.0 or later** (`AGPL-3.0-or-later`).

This license is selected to keep modified, redistributed, and network-deployed
versions open, attributable, and scientifically inspectable.

Commercial or proprietary use cases that cannot comply with `AGPL-3.0-or-later`
may contact the author for a separate commercial license.

See [`LICENSE`](LICENSE) and [`NOTICE`](NOTICE).

---

## Author

**Parvaz Jamei**
Embedded / Industrial IoT / Edge AI / Digital Evolution Research Software

GitHub: [@Parvaz-Jamei](https://github.com/Parvaz-Jamei)

---

**CodonTrace Genesis**
Replayable evidence for digital evolution, causal mechanisms, and ALife research.
