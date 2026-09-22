# CodonTrace Genesis

### Replayable digital evolution, causal mechanism auditing, and evidence-gated ALife research software.

[![PyPI](https://img.shields.io/pypi/v/codontrace?label=PyPI)](https://pypi.org/project/codontrace/)
[![Python](https://img.shields.io/badge/Python-3.11%E2%80%933.14-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![CI](https://github.com/Parvaz-Jamei/codontrace-genesis/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/Parvaz-Jamei/codontrace-genesis/actions/workflows/ci.yml)
[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.20337435.svg)](https://doi.org/10.5281/zenodo.20337435)
[![License: AGPL v3+](https://img.shields.io/badge/License-AGPL%20v3%2B-blue.svg)](https://github.com/Parvaz-Jamei/codontrace-genesis/blob/main/LICENSE)

CodonTrace Genesis is a Python library for running small digital-evolution
experiments that you can replay later. You start a tiny world, let simple
agents eat, survive, and reproduce, and the library writes down what happened
as checkable records. Use it when you want to test an evolutionary idea with
evidence instead of a screenshot. It is research software. It does **not**
claim that the agents are intelligent.

That life-loop is still the product. Domain modules sit beside the engine;
they do not replace it. The biomedical module is the first extra port: a
ClaimGate `DomainProfile` that audits a declared evidence table. Hardware
today is one arm, `SimEsp32Bridge`. Further domain modules and hardware arms
attach the same way, without a second engine.

The installable package is `codontrace`. Product naming for contributors
lives in [`CONTRIBUTING.md`](https://github.com/Parvaz-Jamei/codontrace-genesis/blob/main/CONTRIBUTING.md) and [`STYLE.md`](https://github.com/Parvaz-Jamei/codontrace-genesis/blob/main/STYLE.md).

---

## What it is

- a Python research library for controlled digital-evolution and ALife experiments
- a replay / audit-first evidence layer (specs, runtime digests, manifests)
- a mechanism instrumentation toolkit (ablations, treatment/control, delayed outcomes)
- a claim-gated workflow: software capability and runtime observations are allowed; strong scientific conclusions are not auto-promoted
- one biomedical port and one hardware arm on that same auditor; more domain modules and hardware arms attach later without forking the engine

## What it is not

CodonTrace Genesis is **not** currently presented as:

- proof of artificial general intelligence, consciousness, or collective intelligence
- proof of open-ended intelligence, or a Tokyo Type 1 *pass* (Channon 2024)
- a biological evolution simulator or wet-lab chemistry engine
- a replacement for Avida, MABE, DEAP, QDax, pyribs, or similar tools
- a physical-robot research platform (ESP32 Moj-ه is an engineering stub / `SimEsp32Bridge` only)
- a medical device, SaMD, IVD, FDA/CE clearance, or ASME V&V 40 certification (biomedical is a ClaimGate `DomainProfile` port)
- an Avida/MABE literature-compatible campaign runner (ClaimGate adapters are skeletons until audited published `.dat`/CSV exist)

The project is ambitious. Claims must pass evidence gates. See [`CLAIMS.md`](https://github.com/Parvaz-Jamei/codontrace-genesis/blob/main/CLAIMS.md) and [`docs/WHY_NOT_INTELLIGENCE_YET.md`](https://github.com/Parvaz-Jamei/codontrace-genesis/blob/main/docs/WHY_NOT_INTELLIGENCE_YET.md).

---

## Status

| Field | Current status |
|---|---|
| Package | `codontrace` |
| Public PyPI tip | `0.3.0b6` — tag [`v0.3.0b6`](https://github.com/Parvaz-Jamei/codontrace-genesis/releases/tag/v0.3.0b6). Older `0.3.0b4` and `0.3.0b5` are immutable. |
| GitHub `main` | Runtime `__version__` is `[project].version` in `pyproject.toml` (currently `0.3.0b7`). That identity is not tagged and is not on PyPI. |
| Python | `3.11–3.14` |
| DOI | `10.5281/zenodo.20337435` |
| License | `AGPL-3.0-or-later` |
| Official GitHub release | [`v0.3.0b6`](https://github.com/Parvaz-Jamei/codontrace-genesis/releases/tag/v0.3.0b6). There is no `v0.3.0b7` tag. |
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

The published wheel is `codontrace==0.3.0b6`. `0.3.0b7` is the identity in
`pyproject.toml` on `main` and is not a PyPI release. Older public cuts
`0.3.0b4` and `0.3.0b5` remain immutable and must not be recut. Phases A–G
remain the `0.3.0b3` substrate; H–L + HE01 SCHEMA v7 shipped in `0.3.0b4`.

Python `3.11–3.14`. CI smokes `ubuntu-latest`, `windows-latest`, and `macos-latest` on that range.

### From PyPI (`0.3.0b6`)

```bash
pip install codontrace==0.3.0b6
```

Optional research extras:

```bash
pip install "codontrace[research]==0.3.0b6"
pip install "codontrace[causal]==0.3.0b6"
pip install "codontrace[qd]==0.3.0b6"
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

A PyPI install of the published tip prints `0.3.0b6`. An editable install from
`main` prints `[project].version` from `pyproject.toml` (currently `0.3.0b7`). Do not treat the version
tuple as a phase fence.

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

Print-only smokes live under [`examples/`](https://github.com/Parvaz-Jamei/codontrace-genesis/blob/main/examples/).

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

Levels and interpretation: [`BENCHMARKS.md`](https://github.com/Parvaz-Jamei/codontrace-genesis/blob/main/BENCHMARKS.md).

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

Full policy: [`CLAIMS.md`](https://github.com/Parvaz-Jamei/codontrace-genesis/blob/main/CLAIMS.md).

---

## Next steps

Library-complete beta is not “done.” The next work is **not** more empty Phase
letters.

1. **Do not recut published wheels** `0.3.0b4`, `0.3.0b5`, or `0.3.0b6`. A later public identity needs its own version, a green CI on that exact commit, and an explicit tag. `0.3.0b7` is not that tag yet.
2. **Do not tag or publish from a red or queued CI.** Runtime identity stays the pyproject version until then. The GitHub release that exists is [`v0.3.0b6`](https://github.com/Parvaz-Jamei/codontrace-genesis/releases/tag/v0.3.0b6).
3. **HE03 research campaign** — run only against the locked prereg; do not fabricate `results_v1`.
4. **Lint/type inventory** — `lint-type` remains non-blocking until the ruff/mypy backlog is reduced in its own PR.
5. **Candidate claims** — `collective_intelligence_candidate` only if the full honest flags, including replay, are actually earned.
6. **OEE later** — Tokyo Type 1 *pass* and open-ended intelligence remain blocked.

---

## Architecture

The product is still the engine: a world, agents that eat, survive, and reproduce, then a digest you can replay. The engine does not know medicine or hardware.

```text
GenesisEngine  →  ticks, digest, replay
       └→ native adapter  →  claimgate_bundle_v1  →  audit_bundle()  →  ladder 0–5

Domain modules (same auditor, no second engine)
       biomedical   DomainProfile  — declared evidence table
       hardware     SimEsp32Bridge — one arm today; more arms later
       (later)      another DomainProfile or ingest adapter
```

A new module is a `DomainProfile` or an adapter. It is not a copy of `engine.py`.

| Port | Ingest | Engine |
|---|---|---|
| Native campaign | live spec, or HE01 / HE02 / HE03 JSON | yes, when a spec runs; JSON adapters only read the artifact |
| Avida `.dat`, MABE2 CSV | foreign run tables | no |
| Biomedical module | declared question of interest, context of use, risk, and a PIRT worksheet | no |
| Hardware arm | `SimEsp32Bridge` today; further arms on the same bridge port | optional |

`ALIFE` is the default profile for the life-loop. `BIOMEDICAL` and `HARDWARE` are the two extra profiles that ship now. Biomedical stores ASME V&V 40, FDA 2023, IEC 62304, and IMDRF wording as labels. The same port ranks a phenomena table (PIRT, from nuclear safety) and caps a coupled model at its weakest submodel (building-block VVUQ). A study file closes a phenomenon only when that arm was executed; a typed rank does not. Declared model risk has a separate bar (level 2/3/4 for risk 1/2/3, and an open high-importance phenomenon blocks from risk 2 up). The bar does not move the ladder. See `docs/claimgate/risk_bar.json`. It is not a device. Strings such as `asme_vv40_passed`, `fda_cleared`, and `samd_certified` raise `ConfigurationError`.

```python
from codontrace.claimgate import audit_bundle
from codontrace.claimgate.adapters.codontrace import bundle_from_hard_experiment_01

report = audit_bundle(bundle_from_hard_experiment_01())
print(report.achieved_level, report.public_name, report.missing_for_next)
```

```python
from codontrace.claimgate import audit_bundle
from codontrace.claimgate.adapters.biomedical import bundle_from_device_model_cou

bundle = bundle_from_device_model_cou(
    question_of_interest="Would this score table support the claim?",
    context_of_use="Declared table only; no implant.",
    model_influence=2,
    decision_consequence=3,
    treatment_scores=(0.12, 0.11, 0.13),
    control_scores=(0.20, 0.19, 0.21),
    device_software_kind="simd_declared",
    iec_62304_class="B",
    imdrf_n12_category="II",
    fda_2023_evidence=(1, 3, 8),
    physics_based=True,
)
print(audit_bundle(bundle).achieved_level, bundle.extra["domain"], bundle.extra["model_risk"])
```

The second call stays on the biomedical port. It does not start `GenesisEngine`. Map: [`docs/ARCHITECTURE_PORTS.md`](https://github.com/Parvaz-Jamei/codontrace-genesis/blob/main/docs/ARCHITECTURE_PORTS.md). Biomedical scope: [`docs/BIOMEDICAL_ENGINEERING.md`](https://github.com/Parvaz-Jamei/codontrace-genesis/blob/main/docs/BIOMEDICAL_ENGINEERING.md).

---

## Documentation

| Document | Purpose |
|---|---|
| [`CLAIMS.md`](https://github.com/Parvaz-Jamei/codontrace-genesis/blob/main/CLAIMS.md) | Allowed, candidate, and blocked claims |
| [`docs/protocol/CLAIM_LADDER_PROTOCOL_v0.1.md`](https://github.com/Parvaz-Jamei/codontrace-genesis/blob/main/docs/protocol/CLAIM_LADDER_PROTOCOL_v0.1.md) | Claim-ladder protocol v0.1 (design + grade ALife claims; Wave 3) |
| [`docs/WHY_NOT_INTELLIGENCE_YET.md`](https://github.com/Parvaz-Jamei/codontrace-genesis/blob/main/docs/WHY_NOT_INTELLIGENCE_YET.md) | Literature-vs-reality barrier map; not close to AGI |
| [`docs/PHASE_H_CI_AI_PATH.md`](https://github.com/Parvaz-Jamei/codontrace-genesis/blob/main/docs/PHASE_H_CI_AI_PATH.md) | Phase H: RAG + ablation / effect-size harnesses |
| [`docs/PHASE_I_CI_EVIDENCE.md`](https://github.com/Parvaz-Jamei/codontrace-genesis/blob/main/docs/PHASE_I_CI_EVIDENCE.md) | Phase I: heldout / evolved DoL / MLS / export-of-fitness |
| [`docs/PHASE_J_REPLAY_CI.md`](https://github.com/Parvaz-Jamei/codontrace-genesis/blob/main/docs/PHASE_J_REPLAY_CI.md) | Phase J: honest digest replay + Price scaffold |
| [`docs/PHASE_K_CI_DEPTH.md`](https://github.com/Parvaz-Jamei/codontrace-genesis/blob/main/docs/PHASE_K_CI_DEPTH.md) | Phase K: coordination, Goldsby-scale harness, Price transmission |
| [`docs/PHASE_INDEX.md`](https://github.com/Parvaz-Jamei/codontrace-genesis/blob/main/docs/PHASE_INDEX.md) | Pointer index for Phases H–L and honesty docs |
| [`docs/PHASE_L_AVIDA_FIDELITY.md`](https://github.com/Parvaz-Jamei/codontrace-genesis/blob/main/docs/PHASE_L_AVIDA_FIDELITY.md) | Phase L: ORGANISM_MESSAGING / DEME_GROUP analogs |
| [`docs/HARD_EXPERIMENT_01.md`](https://github.com/Parvaz-Jamei/codontrace-genesis/blob/main/docs/HARD_EXPERIMENT_01.md) | Hard experiment 01: capsule source-bias measurement paper (not a Phase M) |
| [`docs/CLAIMGATE_STANDALONE.md`](https://github.com/Parvaz-Jamei/codontrace-genesis/blob/main/docs/CLAIMGATE_STANDALONE.md) | Wave 2 simulator-agnostic ClaimGate auditor (public 0–5; not a Tokyo/OEE pass) |
| [`docs/ARCHITECTURE_PORTS.md`](https://github.com/Parvaz-Jamei/codontrace-genesis/blob/main/docs/ARCHITECTURE_PORTS.md) | Engine vs adapter vs DomainProfile; not a second engine per domain |
| [`docs/BIOMEDICAL_ENGINEERING.md`](https://github.com/Parvaz-Jamei/codontrace-genesis/blob/main/docs/BIOMEDICAL_ENGINEERING.md) | Biomedical analog (QOI/COU labels); not SaMD / FDA / ASME certification |
| [`paper/baic/paper.md`](https://github.com/Parvaz-Jamei/codontrace-genesis/blob/main/paper/baic/paper.md) | BAIC 2026 Persian manuscript (evidence audit; not a device paper) |
| [`docs/ENGINE_REPLAY_CONTRACT.md`](https://github.com/Parvaz-Jamei/codontrace-genesis/blob/main/docs/ENGINE_REPLAY_CONTRACT.md) | Replay hashes and run-identity types extracted from `engine.py` |
| [`CONTRIBUTING.md`](https://github.com/Parvaz-Jamei/codontrace-genesis/blob/main/CONTRIBUTING.md) / [`STYLE.md`](https://github.com/Parvaz-Jamei/codontrace-genesis/blob/main/STYLE.md) | Product naming: **CodonTrace Genesis**; package `codontrace` |
| [`docs/SCIENTIFIC_AUTHORITIES_2026.md`](https://github.com/Parvaz-Jamei/codontrace-genesis/blob/main/docs/SCIENTIFIC_AUTHORITIES_2026.md) | Feature × authority matrix (landed / partial / deferred) |
| [`docs/rag/README.md`](https://github.com/Parvaz-Jamei/codontrace-genesis/blob/main/docs/rag/README.md) | Literature RAG corpus (measurement design, not intelligence evidence) |
| [`REPRODUCIBILITY.md`](https://github.com/Parvaz-Jamei/codontrace-genesis/blob/main/REPRODUCIBILITY.md) | Install, validation tiers, artifact preservation |
| [`BENCHMARKS.md`](https://github.com/Parvaz-Jamei/codontrace-genesis/blob/main/BENCHMARKS.md) | Benchmark protocols and claim boundaries |
| [`RELEASE_EVIDENCE.md`](https://github.com/Parvaz-Jamei/codontrace-genesis/blob/main/RELEASE_EVIDENCE.md) | Release evidence pack (see file for which public wheel it covers) |

Phase literature checklists: [`PHASE_D_LITERATURE.md`](https://github.com/Parvaz-Jamei/codontrace-genesis/blob/main/docs/PHASE_D_LITERATURE.md),
[`PHASE_E_LITERATURE.md`](https://github.com/Parvaz-Jamei/codontrace-genesis/blob/main/docs/PHASE_E_LITERATURE.md),
[`PHASE_G_MATERIALS_LITERATURE.md`](https://github.com/Parvaz-Jamei/codontrace-genesis/blob/main/docs/PHASE_G_MATERIALS_LITERATURE.md).
Studio / performance notes stay out of core:
[`STUDIO_BOUNDARY.md`](https://github.com/Parvaz-Jamei/codontrace-genesis/blob/main/docs/STUDIO_BOUNDARY.md).

---

## Testing

```bash
python -m compileall -q src tests examples tools
python -m pytest tests/genesis_gates -q
python -m pytest tests/science_gates -q
python -m pytest tests/examples/test_collective_joss_evidence_benchmark_smoke.py -q
python -m pytest tests -q
```

Validation tiers: [`REPRODUCIBILITY.md`](https://github.com/Parvaz-Jamei/codontrace-genesis/blob/main/REPRODUCIBILITY.md).

---

## Citation

If you use CodonTrace Genesis in research, prototypes, technical evaluation,
benchmark work, reports, or derivative research artifacts, please cite the
versioned software release.

```bibtex
@software{codontrace_genesis_2026,
  title = {CodonTrace Genesis},
  author = {Jamei, Parvaz},
  version = {0.3.0b7},
  doi = {10.5281/zenodo.20337435},
  url = {https://github.com/Parvaz-Jamei/codontrace-genesis},
  note = {0.3.0b7 is the pyproject identity on main at commit c8db778 and is not the PyPI tip. PyPI tip is 0.3.0b6. The DOI is the software archive, not a campaign archive.}
}
```

A [`CITATION.cff`](https://github.com/Parvaz-Jamei/codontrace-genesis/blob/main/CITATION.cff) file is included for citation-aware tools.

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

See [`LICENSE`](https://github.com/Parvaz-Jamei/codontrace-genesis/blob/main/LICENSE) and [`NOTICE`](https://github.com/Parvaz-Jamei/codontrace-genesis/blob/main/NOTICE).

---

## Author

**Parvaz Jamei**
Embedded / Industrial IoT / Edge AI / Digital Evolution Research Software

GitHub: [@Parvaz-Jamei](https://github.com/Parvaz-Jamei)

---

**CodonTrace Genesis**
Replayable evidence for digital evolution, causal mechanisms, and ALife research.
