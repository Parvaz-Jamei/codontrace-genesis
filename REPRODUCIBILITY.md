# Reproducibility Guide

Version target: `0.3.0b1`
Release DOI: `10.5281/zenodo.20337435`
License: `AGPL-3.0-or-later`
Status: Public beta research software
Repository: `https://github.com/Parvaz-Jamei/codontrace-genesis`
Package: `codontrace==0.3.0b1`
Primary benchmark runner: `examples/collective_joss_evidence_benchmark.py`
Primary benchmark smoke test: `tests/examples/test_collective_joss_evidence_benchmark_smoke.py`

This guide explains how to reproduce CodonTrace Genesis runs, validate the public package, preserve artifacts, and interpret outputs without converting exploratory observations into unsupported scientific claims.

CodonTrace Genesis is designed for deterministic, replay/audit-first digital-evolution and ALife research workflows. Reproducibility requires recording the exact software version, seed list, configuration, command line, runtime environment, generated artifacts, and claim-readiness state.

---

## 1. Reproducibility principle

A CodonTrace result is considered reproducible only when another user can identify and preserve:

1. the exact package version,
2. the exact code source or release archive,
3. the Python version,
4. installed extras/dependencies,
5. the seed list,
6. the full run configuration,
7. the command line or runner entry point,
8. generated CSV/JSON/JSONL/HTML artifacts,
9. artifact manifest or digest index,
10. replay/audit records when available,
11. claim-gate or claim-readiness status,
12. known limitations and failed/skipped outputs.

A result should not be used as positive scientific evidence if it depends on missing seeds, missing configuration, placeholder records, failed exports, empty digests, fake evidence, NaN/Infinity values, or `not_run:*` statuses.

---

## 2. Recommended clean environment

### Windows PowerShell

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip setuptools wheel
```

If Python 3.11 is unavailable, use Python 3.12, 3.13, or 3.14.

### Linux / macOS

```bash
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip setuptools wheel
```

---

## 3. Install from PyPI

Use the exact public release version for reproducible public-beta work:

```bash
python -m pip install codontrace==0.3.0b1
```

For research extras:

```bash
python -m pip install "codontrace[research]==0.3.0b1"
```

For causal-analysis extras:

```bash
python -m pip install "codontrace[causal]==0.3.0b1"
```

For quality-diversity extras:

```bash
python -m pip install "codontrace[qd]==0.3.0b1"
```

Verify the installed version:

```bash
python -c "import codontrace; print(codontrace.__version__)"
```

Expected output:

```text
0.3.0b1
```

---

## 4. Install from source

```bash
git clone https://github.com/Parvaz-Jamei/codontrace-genesis.git
cd codontrace-genesis
python -m pip install -e ".[dev]"
```

For a research environment from source:

```bash
python -m pip install -e ".[dev,research,causal,qd]"
```

Verify import path and version:

```bash
python -c "import codontrace; print(codontrace.__version__); print(codontrace.__file__)"
```

---

## 5. Basic integrity checks

Run these checks before using outputs as evidence:

```bash
python -m compileall -q src tests examples tools
python -m pytest tests/genesis_gates -q
python -m pytest tests/science_gates -q
```

Run the full suite before a release or public benchmark update:

```bash
python -m pytest tests -q --durations=25
```

A failed test run does not automatically mean the engine is scientifically wrong. However, outputs from a failing or partially installed environment should not be promoted as positive scientific evidence.

---

## 6. Benchmark runner smoke test

The current repository includes a JOSS-safe evidence benchmark runner and a CI-safe smoke test:

```text
examples/collective_joss_evidence_benchmark.py
tests/examples/test_collective_joss_evidence_benchmark_smoke.py
```

Run the smoke test:

```bash
python -m pytest tests/examples/test_collective_joss_evidence_benchmark_smoke.py -q
```

This smoke test is intentionally small. It checks that:

- the benchmark runner can be imported,
- the smoke plan covers evolution, capsule, memory, QD, and social/partner surfaces,
- the runner executes a tiny controlled run,
- expected artifacts are generated,
- claim-readiness output exists,
- collective-intelligence claim readiness remains false unless strong evidence gates pass.

The smoke test is a software and artifact-generation check. It is not a proof of collective intelligence.

---

## 7. Manual benchmark runner commands

### CI-safe smoke run

Use this when you need a fast local check:

```bash
PYTHONPATH=src python examples/collective_joss_evidence_benchmark.py   --out outputs/joss_evidence_smoke   --profile smoke   --seed-count 1   --ticks 3   --population 4   --workers 1   --max-runs 6
```

Expected key outputs:

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

### Quick evidence run

Use this for a slightly more informative local evidence run:

```bash
PYTHONPATH=src python examples/collective_joss_evidence_benchmark.py   --out outputs/joss_evidence_quick   --profile quick   --seed-count 3   --ticks 10   --population 8   --workers 1
```

### Stronger local validation run

Use this before writing reports or preparing JOSS material:

```bash
PYTHONPATH=src python examples/collective_joss_evidence_benchmark.py   --out outputs/joss_evidence_standard   --profile strong   --seed-count 12   --generations 40   --population 16   --workers 2   --continue-on-error
```

### Publication-candidate campaign

Use this only for serious benchmark preparation and artifact archiving:

```bash
PYTHONPATH=src python examples/collective_joss_evidence_benchmark.py   --out outputs/joss_evidence_publication   --profile marathon   --seed-count 24   --generations 80   --population 24   --workers 2   --per-run-timeout 240   --continue-on-error
```

Publication-candidate campaigns should preserve all generated artifacts and should not be interpreted without paired controls, effect sizes, replay/digest checks, and claim-readiness review.

---

## 8. Validation tiers

CodonTrace Genesis uses multiple validation levels. This keeps the default workflow reviewer-friendly while still providing a heavier path for research evidence.

| Tier | Name | Purpose | Default? |
|---:|---|---|---|
| 0 | Quick CI validation | compile/import/core gate checks | yes |
| 1 | Benchmark smoke validation | run the tiny benchmark smoke test | yes/recommended |
| 2 | Full local validation | run full test suite and benchmark quick profile | manual |
| 3 | Extended research validation | run standard/strong profile with controls | manual |
| 4 | Publication campaign | multi-seed archived benchmark campaign | manual only |

### Tier 0 — quick CI validation

```bash
python -m compileall -q src tests examples tools
python -m pytest tests/genesis_gates -q
python -m pytest tests/science_gates -q
```

### Tier 1 — benchmark smoke validation

```bash
python -m pytest tests/examples/test_collective_joss_evidence_benchmark_smoke.py -q
```

### Tier 2 — full local validation

```bash
python -m pytest tests -q --durations=25
PYTHONPATH=src python examples/collective_joss_evidence_benchmark.py   --out outputs/joss_evidence_quick   --profile quick   --seed-count 3   --ticks 10   --population 8   --workers 1
```

### Tier 3 — extended research validation

```bash
PYTHONPATH=src python examples/collective_joss_evidence_benchmark.py   --out outputs/joss_evidence_standard   --profile strong   --seed-count 12   --generations 40   --population 16   --workers 2   --continue-on-error
```

### Tier 4 — publication campaign

```bash
PYTHONPATH=src python examples/collective_joss_evidence_benchmark.py   --out outputs/joss_evidence_publication   --profile marathon   --seed-count 24   --generations 80   --population 24   --workers 2   --per-run-timeout 240   --continue-on-error
```

Tier 4 is not required for ordinary CI or JOSS software review. It is for paper-grade empirical claims.

---

## 9. Required metadata for every experiment

Every experiment report should include:

```yaml
codontrace_version: "0.3.0b1"
release_doi: "10.5281/zenodo.20337435"
python_version: "<recorded Python version>"
platform: "<OS / environment>"
command: "<exact command line>"
seed_list: [1, 2, 3]
runner_or_example: "<script/module name>"
output_dir: "<path>"
created_at_utc: "<timestamp>"
claim_level: "<software capability | observation | candidate evidence | mechanism support | replicated effect>"
```

For multi-seed experiments, also preserve:

```yaml
seed_count: "<number of seeds>"
ticks_or_generations: "<number>"
population: "<population size>"
variants:
  - baseline
  - no_capsules
  - no_memory
controls:
  - negative controls used
  - ablations used
```

---

## 10. Artifact preservation checklist

A reproducible output bundle should include as many of the following as applicable:

| Artifact | Purpose |
|---|---|
| `run_config.json` | Exact experiment configuration |
| `summary.json` | Overall runner status and aggregate counts |
| `run_records.csv` | Per-run records |
| `feature_matrix.csv` | Feature/evidence matrix |
| `counterfactual_pairs.csv` | Paired treatment/control comparisons |
| `claim_readiness.json` | Claim-gate output |
| `artifact_manifest.json` | Output file index and digests |
| `environment.txt` | Python/package/environment metadata |
| `report.html` | Human-readable report |
| `stdout.log` / `stderr.log` | Execution logs when available |

If an output bundle lacks the configuration, seed list, version, and manifest/digest evidence, it should be treated as exploratory rather than publication-grade.

---

## 11. Claim-gate discipline

CodonTrace Genesis uses a claim-gated workflow. The following must not be treated as positive scientific evidence:

- failed runs,
- skipped runs,
- incomplete exports,
- empty digests,
- placeholder records,
- fake evidence records,
- `not_run:*` statuses,
- NaN values,
- Infinity values,
- output files without provenance,
- outputs generated from a version different from the claimed release,
- descriptive event counts without treatment/control context.

A descriptive record means something was observed. It does not automatically mean the mechanism caused an outcome.

---

## 12. Version discipline

Use `codontrace==0.3.0b1` for public-beta reproducibility work.

Older development outputs may be useful as development evidence, but should not be presented as release evidence for `0.3.0b1` unless they are rerun on the public release.

When comparing outputs across versions, explicitly state:

```text
This output was generated with <version>. It is not presented as evidence for <different version>.
```

Recommended wording for older internal/development outputs:

> This artifact is useful as development/instrumentation evidence. It should be rerun on the current public release before being used as publication-grade evidence.

---

## 13. Minimum benchmark standard

For a small public benchmark, use at least:

```yaml
seed_count: 10-12
ticks_or_generations: 30-60
population: 12-24
paired_controls: true
artifact_manifest: true
claim_readiness_file: true
```

For publication-grade claims, use stronger multi-seed evidence with ablations, negative controls, uncertainty estimates, replay audit, and archived artifacts.

Example claim boundary:

> This benchmark supports candidate evidence for capsule-mediated transfer under the specified configuration. It does not by itself prove collective intelligence.

---

## 14. Reproducibility statement for papers/reports

Use this wording in reports, README sections, JOSS-style papers, or supplementary materials:

> All CodonTrace Genesis runs should record the exact package version, seed list, configuration, command line, environment, and generated artifact manifest. Outputs are interpreted through the project claim policy: failed, skipped, placeholder, fake, incomplete, NaN, Infinity, or `not_run:*` artifacts are not counted as positive scientific evidence.

For the current public beta:

> Public-beta reproducibility should target `codontrace==0.3.0b1` and DOI `10.5281/zenodo.20337435`.

---

## 15. Troubleshooting

### Import fails

Check that the package was installed into the active environment:

```bash
python -m pip show codontrace
python -c "import sys; print(sys.executable)"
python -c "import codontrace; print(codontrace.__file__)"
```

### Tests cannot find the package

For source installs, use editable mode:

```bash
python -m pip install -e ".[dev]"
```

### Build isolation or setuptools issue

Upgrade build tools:

```bash
python -m pip install --upgrade pip setuptools wheel
```

Then reinstall:

```bash
python -m pip install -e ".[dev]"
```

### Long benchmark runs consume too much memory

Use fewer workers first:

```bash
--workers 1
```

Then increase workers only after a successful smoke or quick run.

### Output exists but claim gate is false

This is expected when evidence is insufficient. A blocked claim is not a failed project result; it is evidence that the claim policy is working.

---

## 16. Maintainer update policy

Update this file whenever:

- a new public version is released,
- the DOI changes,
- Python support changes,
- benchmark scripts are added or renamed,
- output artifact names change,
- claim-gate policy changes,
- JOSS/arXiv/paper workflow is prepared,
- a development benchmark becomes a public benchmark.
