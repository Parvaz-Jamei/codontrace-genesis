# Benchmark Protocols

Version target: `0.3.0a2`  
Release DOI: `10.5281/zenodo.20337435`  
License: `AGPL-3.0-or-later`  
Status: Public alpha research software  
Primary runner: `examples/collective_joss_evidence_benchmark.py`  
Primary smoke test: `tests/examples/test_collective_joss_evidence_benchmark_smoke.py`  
Reference artifact inspected: `joss_evidence_smoke_20260522_182358.zip`

This document defines the benchmark protocol for CodonTrace Genesis as deterministic, replay/audit-first research software for digital evolution, ALife experiments, causal mechanism auditing, and claim-gated evidence generation.

The goal is not to turn a small smoke run into a scientific discovery claim. The goal is to make the software reviewable, rerunnable, measurable, and clear about which evidence level has been reached.

---

## 1. Purpose

CodonTrace Genesis benchmarks are designed to verify that the library can:

1. execute controlled digital-evolution scenarios,
2. generate reproducible evidence artifacts,
3. expose mechanism-level records across multiple evidence families,
4. compare treatment/control variants through counterfactual-style summaries,
5. preserve version/configuration/environment metadata,
6. produce human-readable and machine-readable reports,
7. refuse unsupported strong claims through claim-readiness gates.

The benchmark protocol supports:

- JOSS-style software review,
- reproducibility checks,
- regression detection,
- mechanism-level evidence inspection,
- later empirical campaigns for scientific papers,
- clear separation between software capability, candidate evidence, and publication-grade claims.

---

## 2. JOSS-oriented scope

For JOSS, the benchmark is a **software functionality and reproducibility demonstration**.

It should show that CodonTrace Genesis has:

- runnable examples,
- objective tests,
- generated artifacts,
- documented controls,
- claim-gated output,
- a clear research-software purpose.

It should not claim that the software has already proven:

- collective intelligence,
- AGI,
- consciousness,
- benchmark superiority,
- open-ended intelligence,
- causal superiority of capsule or memory mechanisms.

JOSS-safe benchmark wording:

> The benchmark demonstrates reproducible instrumentation and evidence generation across digital-evolution, capsule, memory, QD, social/partner, role, and behavior-diversity surfaces. It is not presented as proof of collective intelligence.

---

## 3. Current benchmark assets

### Runner

```text
examples/collective_joss_evidence_benchmark.py
```

The runner is the user-facing benchmark entry point. It produces CSV/JSON/HTML artifacts and is designed to stay compatible with the public-alpha `0.3.0a2` branch.

### Smoke test

```text
tests/examples/test_collective_joss_evidence_benchmark_smoke.py
```

The smoke test is the CI/reviewer-friendly check. It verifies that:

- the runner can be imported,
- the runner plan covers the main mechanism families,
- a tiny benchmark can execute,
- expected artifacts are produced,
- `claim_readiness.json` exists,
- collective-intelligence readiness remains `false` without stronger evidence.

### Reference artifact

```text
joss_evidence_smoke_20260522_182358.zip
```

This artifact was generated from a Colab smoke run. It is useful as a reference output for this document and for later release-asset/Zenodo archival if desired.

---

## 4. Required benchmark artifacts

A valid benchmark output directory should include:

```text
run_config.json
summary.json
run_records.csv
feature_matrix.csv
counterfactual_pairs.csv
behavior_diversity.csv
mortality_breakdown.csv
social_breakdown.csv
qd_breakdown.csv
claim_readiness.json
artifact_manifest.json
environment.txt
report.html
evidence_outputs.zip
```

Minimum required for a smoke-level result:

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

If any of the minimum files are missing, the benchmark should be treated as incomplete.

---

## 5. Reference smoke result

The inspected smoke artifact reports:

| Field | Value |
|---|---:|
| Runner | `collective_joss_evidence_benchmark` |
| Runner schema | `collective_joss_evidence_benchmark_v1.1.0_public_alpha_a2` |
| CodonTrace version | `0.3.0a2` |
| Target public version | `0.3.0a2` |
| Expected version | `0.3.0a2` |
| Release DOI | `10.5281/zenodo.20337435` |
| Profile | `smoke` |
| Seed start | `1` |
| Seed count | `1` |
| Ticks / generations | `3` |
| Population | `4` |
| Workers | `1` |
| Max runs | `6` |
| Runs planned | `6` |
| Runs completed | `6` |
| Runs failed | `0` |
| Unique result digests | `6` |
| Duration | `24.708 s` |
| Status | `passed` |
| stderr | empty |

Interpretation:

> The smoke run is valid as a software/artifact-generation benchmark. It is too small for scientific effect claims, but it proves the runner can execute and generate the expected evidence bundle.

---

## 6. Reference smoke claim readiness

The inspected `claim_readiness.json` reports:

| Claim-readiness field | Value |
|---|---:|
| Evolution primitives observed | `true` |
| Memory primitives observed | `true` |
| Capsule primitives observed | `true` |
| QD primitives observed | `true` |
| Social interaction observed | `true` |
| Behavior diversity observed | `true` |
| Collective intelligence claim ready | `false` |

This is the correct smoke-level outcome.

A smoke benchmark should show that evidence surfaces exist, but it should not approve collective intelligence. If a tiny smoke run marks collective intelligence as ready, that should be treated as a claim-gate defect unless the gates are explicitly redesigned and justified.

---

## 7. Reference smoke aggregate counts

The inspected smoke artifact produced the following aggregate counts:

| Record family | Count |
|---|---:|
| `energy_accounting_records` | `64` |
| `death_reason_records` | `64` |
| `death_classification_records` | `64` |
| `action_cost_records` | `64` |
| `action_reward_records` | `64` |
| `action_precondition_records` | `0` |
| `fitness_breakdown_records` | `64` |
| `selection_fitness_records` | `64` |
| `reproduction_attempt_records` | `64` |
| `reproduction_gate_records` | `64` |
| `birth_intent_records` | `0` |
| `birth_request_records` | `0` |
| `birth_event_records` | `8` |
| `child_genome_records` | `4` |
| `child_admission_records` | `8` |
| `mutation_plan_records` | `4` |
| `mutation_result_records` | `4` |
| `structural_mutation_records` | `0` |
| `learning_inheritance_records` | `4` |
| `skill_compression_records` | `4` |
| `adf_inheritance_records` | `4` |
| `lineage_growth_records` | `30` |
| `behavior_descriptors` | `64` |
| `qd_archive_summary_records` | `0` |
| `qd_selection_audit` | `18` |
| `qd_parent_feedback_audit` | `18` |
| `qd_selection_feedback_records` | `0` |
| `capsule_adoption_records` | `16` |
| `capsule_cost_records` | `16` |
| `capsule_utility_records` | `16` |
| `capsule_shuffle_records` | `0` |
| `capsule_source_fitness_records` | `16` |
| `memory_use_records` | `55` |
| `delayed_reward_records` | `1` |
| `signal_memory_link_records` | `0` |
| `social_interaction_records` | `13` |
| `partner_interaction_records` | `13` |
| `role_records` | `64` |
| `role_timeline_records` | `64` |
| `role_contribution_records` | `64` |
| `collective_coordination_records` | `0` |
| `collective_ablation_records` | `0` |
| `tool_chain_records` | `64` |
| `inventory_records` | `64` |
| `action_wiring_records` | `0` |
| `generalization_records` | `6` |
| `engine_frames` | `30` |
| `engine_digest_audit` | `30` |
| `strong_claim_ladder_records` | `6` |
| `output_completeness_records` | `390` |
| `export_status_records` | `390` |
| `ai_birth_intervention_records` | `0` |
| `evidence_status_records` | `0` |

Additional smoke summaries:

| Field | Value |
|---|---:|
| `gene_unique_total_across_runs` | `8` |
| `unique_behavior_descriptors_total` | `50` |
| `counterfactual_pair_count` | `3` |
| `genesis_exports` | `924` |
| `death_reasons.not_applicable` | `50` |
| `death_reasons.alive_gate_failure_nonfatal` | `14` |
| `social_types.capsule_learning` | `9` |
| `social_types.resource_competition` | `4` |
| `qd_reasons.capacity_not_exceeded` | `18` |
| `material_presence_total.Lu` | `16` |
| `material_presence_total.Ae` | `112` |

Interpretation:

> These counts demonstrate broad instrumentation coverage in a tiny run. Counts are descriptive observations, not proof of causality or intelligence.

---

## 8. Reference smoke counterfactual pairs

The inspected smoke output includes three paired comparisons:

| Family | Treatment | Control | Observed delta |
|---|---|---|---|
| Evolution | `birth_friendly` | `no_reproduction` | `birth_event_records: 0`, `reproduction_gate_records: +4` |
| Capsule | `high_communication` | `no_capsules` | `capsule_adoption_records: +16`, `capsule_utility_records: +16`, `social_interaction_records: +9` |
| Memory | `baseline` | `no_memory` | `memory_use_records: +7`, `delayed_reward_records: +1` |

Interpretation:

- The capsule pair shows smoke-level activation of capsule adoption and utility surfaces.
- The memory pair shows smoke-level activation of memory-use and delayed-reward surfaces.
- The evolution pair shows reproduction-gate differences but does not show a birth-event delta in this tiny smoke configuration.
- These are correct as mechanism checks but are not publication-grade effect estimates.

---

## 9. Known provenance note

The inspected smoke `summary.json` includes:

```text
release_artifact_name: codontrace-0.3.0a1-release-bundle.zip
```

while the run configuration and actual CodonTrace version report:

```text
codontrace_version: 0.3.0a2
target_public_version: 0.3.0a2
expected_version: 0.3.0a2
```

Interpretation:

- This is not a smoke-run failure.
- The benchmark executed with `0.3.0a2`.
- The stale `release_artifact_name` should be cleaned before the next formal release so provenance text does not confuse reviewers.
- Until cleaned, benchmark reports should treat this as a minor provenance-label issue, not as evidence that the run used `0.3.0a1`.

Recommended fix before the next release:

> Update any static release-artifact label or default metadata that still mentions `0.3.0a1`.

---

## 10. Benchmark levels

CodonTrace uses tiered benchmark levels so that CI, reviewers, Colab users, and paper authors do not run the same workload.

| Level | Name | Purpose | Intended runtime | Claim level |
|---:|---|---|---|---|
| 0 | Smoke pytest | import + tiny runner + artifacts | seconds/minutes | software capability |
| 1 | Smoke benchmark | minimal artifact bundle | seconds/minutes | runtime observation |
| 2 | Safe benchmark | small multi-seed run | target under 10–15 minutes | candidate instrumentation evidence |
| 3 | Standard benchmark | more informative controlled run | tens of minutes or more | candidate evidence |
| 4 | Strong benchmark | larger multi-seed controlled run | long manual run | mechanism support candidate |
| 5 | Publication campaign | archived paper-grade campaign | long-running | possible scientific claim if gates pass |

The smoke result currently supports Levels 0–1 only.

---

## 11. Commands

### 11.1 Smoke pytest

```bash
python -m pytest tests/examples/test_collective_joss_evidence_benchmark_smoke.py -q
```

### 11.2 Smoke benchmark

```bash
PYTHONPATH=src python examples/collective_joss_evidence_benchmark.py   --out outputs/joss_evidence_smoke   --profile smoke   --seed-count 1   --ticks 3   --population 4   --workers 1   --max-runs 6   --per-run-timeout 90
```

### 11.3 Safe benchmark

Recommended Colab-friendly version:

```bash
PYTHONPATH=src python examples/collective_joss_evidence_benchmark.py   --out outputs/joss_evidence_safe   --profile quick   --seed-count 2   --ticks 8   --population 6   --workers 1   --max-runs 20   --continue-on-error   --per-run-timeout 90
```

Expected role:

- stronger than smoke,
- still lightweight,
- suitable for Colab,
- not publication-grade.

### 11.4 Standard benchmark

```bash
PYTHONPATH=src python examples/collective_joss_evidence_benchmark.py   --out outputs/joss_evidence_standard   --profile quick   --seed-count 6   --ticks 20   --population 10   --workers 1   --max-runs 80   --continue-on-error   --per-run-timeout 120
```

Expected role:

- manual validation,
- may be slow on free Colab,
- good for stronger artifact coverage,
- not mandatory for CI.

### 11.5 Strong benchmark

```bash
PYTHONPATH=src python examples/collective_joss_evidence_benchmark.py   --out outputs/joss_evidence_strong   --profile strong   --seed-count 12   --generations 40   --population 16   --workers 2   --continue-on-error   --per-run-timeout 180
```

Expected role:

- manual research validation,
- candidate mechanism-support evidence if controls pass,
- should preserve all artifacts.

### 11.6 Publication-candidate campaign

```bash
PYTHONPATH=src python examples/collective_joss_evidence_benchmark.py   --out outputs/joss_evidence_publication   --profile marathon   --seed-count 24   --generations 80   --population 24   --workers 2   --continue-on-error   --per-run-timeout 240
```

Expected role:

- paper-grade empirical campaign only,
- should be archived externally,
- must include statistical analysis and strong controls,
- should not be confused with JOSS software-review smoke.

---

## 12. Benchmark questions and claim boundaries

### 12.1 Evolution, birth, reproduction, and mutation

Question:

> Can the runner expose mutation, birth, reproduction-gate, child-genome, child-admission, lineage-growth, death, selection, and fitness records under controlled reproduction settings?

Primary variants:

```text
birth_friendly
no_reproduction
high_mutation
no_mutation
gene_diversity
capacity_pressure
mortality_pressure
```

Primary metrics:

```text
birth_event_records
reproduction_gate_records
child_genome_records
child_admission_records
mutation_plan_records
mutation_result_records
lineage_growth_records
death_reason_records
fitness_breakdown_records
selection_fitness_records
```

Allowed current claim:

> The benchmark runner can generate evolution, reproduction, mutation, birth, child, lineage, death, selection, and fitness evidence records.

Blocked claim:

> The benchmark proves open-ended evolution or intelligent reproduction.

Upgrade path:

- more seeds,
- longer runs,
- lineage persistence,
- inherited change tracking,
- adaptive fitness comparisons,
- controls separating gate availability from actual reproduction success.

---

### 12.2 Capsule-mediated transfer

Question:

> Can capsule-enabled variants produce measurable adoption, utility, source-fitness, cost, and social-interaction records compared with no-capsule controls?

Primary variants:

```text
high_communication
no_capsules
collective_mixed
stress_all
```

Primary metrics:

```text
capsule_adoption_records
capsule_cost_records
capsule_utility_records
capsule_source_fitness_records
social_interaction_records
partner_interaction_records
```

Allowed current claim:

> The benchmark runner can observe and export capsule-mediated signaling records and no-capsule controls.

Blocked claim:

> Capsule transfer causally improves adaptation, group performance, intelligence, or collective intelligence.

Upgrade path:

- multi-seed paired controls,
- source-fitness ablation,
- signal-memory-link ablation,
- capsule utility outcome windows,
- misleading/expired/low-confidence controls,
- effect sizes and uncertainty intervals.

---

### 12.3 Memory and delayed reward

Question:

> Can memory-enabled variants produce measurable memory-use and delayed-reward records compared with no-memory controls?

Primary variants:

```text
baseline
no_memory
collective_mixed
stress_all
```

Primary metrics:

```text
memory_use_records
delayed_reward_records
signal_memory_link_records
```

Allowed current claim:

> The benchmark runner can observe and export memory-use and delayed-reward surfaces.

Blocked claim:

> Memory mechanisms causally improve later behavior, survival, reproduction, or intelligence.

Upgrade path:

- multi-seed paired controls,
- delayed outcome windows,
- memory read/write/action traces,
- negative controls,
- signal-memory-action causal checks,
- effect sizes.

---

### 12.4 Skill compression and inheritance

Question:

> Can the engine expose learning-inheritance, skill-compression, ADF-inheritance, child-genome, and child-outcome records?

Primary variants:

```text
lamarckian
collective_mixed
stress_all
```

Primary metrics:

```text
learning_inheritance_records
skill_compression_records
adf_inheritance_records
child_genome_records
child_admission_records
birth_event_records
lineage_growth_records
```

Allowed current claim:

> CodonTrace can expose and export inheritance/compression-related evidence surfaces.

Blocked claim:

> Skill compression improves child survival or intelligence.

Upgrade path:

- full compression vs disabled,
- capacity-only control,
- shuffle-compressed-skill control,
- null-compression control,
- sibling or matched-child comparison,
- child outcome windows,
- multi-seed effect estimates.

---

### 12.5 Quality diversity and behavior diversity

Question:

> Can the runner expose QD audit records and behavior-diversity descriptors?

Primary variants:

```text
qd_pressure
no_qd
collective_mixed
stress_all
```

Primary metrics:

```text
qd_selection_audit
qd_parent_feedback_audit
qd_selection_feedback_records
behavior_descriptors
unique_behavior_descriptors_total
```

Allowed current claim:

> The benchmark runner can export QD audit records and behavior-diversity summaries.

Blocked claim:

> The benchmark proves open-endedness or QD superiority.

Upgrade path:

- novelty accumulation,
- archive coverage,
- complexity growth,
- adaptive success,
- lineage persistence,
- non-QD controls,
- random/fixed policy controls.

---

### 12.6 Social, partner, and role instrumentation

Question:

> Can the runner expose social/partner interaction and role records suitable for later collective-behavior analysis?

Primary variants:

```text
collective_mixed
no_capsules
scarce_resources
resource_regen
stress_all
```

Primary metrics:

```text
social_interaction_records
partner_interaction_records
role_records
role_timeline_records
role_contribution_records
generalization_records
```

Allowed current claim:

> The benchmark runner can observe and export social, partner, role, and generalization evidence surfaces.

Blocked claim:

> Role specialization or collective intelligence is proven.

Upgrade path:

- role persistence,
- role switch cost,
- role contribution deltas,
- role ablation,
- heldout/unfamiliar partner evaluation,
- group-over-individual improvement,
- communication ablation.

---

### 12.7 Collective-behavior and collective-intelligence hypotheses

Question:

> Does a group-level condition show stable improvement over individual/control baselines with role complementarity, communication ablation, and heldout-partner generalization?

Current status:

```text
blocked for smoke
```

Required gates:

- group-over-individual improvement,
- non-capsule cooperation control,
- role complementarity,
- role ablation,
- communication/no-capsule ablation,
- memory/no-memory ablation,
- heldout/unfamiliar partner generalization,
- multi-seed effect sizes,
- replay/audit artifact preservation,
- external statistical analysis.

Allowed current claim:

> CodonTrace includes instrumentation and benchmark scaffolding for investigating collective-behavior hypotheses.

Blocked current claim:

> CodonTrace proves collective intelligence.

---

## 13. Artifact storage policy

Large benchmark outputs should not be committed directly to `main` by default.

Recommended storage:

| Artifact type | Recommended location |
|---|---|
| Tiny smoke zip | local archive, GitHub Release asset, or Zenodo artifact |
| Safe benchmark zip | GitHub Release asset or Zenodo |
| Standard/strong output | GitHub Release asset or Zenodo |
| Publication campaign | Zenodo/paper supplement |
| Small CSV summary | optionally commit if stable and useful |
| Heavy logs/raw outputs | do not commit to main by default |

For the current stage, it is sufficient to keep:

- `CLAIMS.md`,
- `REPRODUCIBILITY.md`,
- `BENCHMARKS.md`,
- the runner,
- the smoke test,
- and the smoke zip outside the repository or as a future release asset.

The smoke zip does not need to be uploaded into the repository immediately.

---

## 14. Interpretation rules

### What the current smoke benchmark supports

The current smoke benchmark supports:

- runner execution on `0.3.0a2`,
- generation of structured artifacts,
- artifact-manifest creation,
- environment recording,
- claim-readiness recording,
- multi-family evidence-surface activation,
- descriptive counterfactual-style pair output,
- correct blocking of collective-intelligence readiness.

### What the current smoke benchmark does not support

The current smoke benchmark does not support:

- collective intelligence,
- AGI,
- consciousness,
- open-ended intelligence,
- causal superiority of capsule transfer,
- causal superiority of memory,
- role specialization,
- benchmark superiority over Avida, MABE, DEAP, QDax, pyribs, or similar tools.

### Why this matters

A benchmark can be valuable even when it blocks strong claims. For CodonTrace, a blocked claim is not automatically a failure. It can indicate that the evidence gate is doing its job.

---

## 15. Performance and runtime expectations

Colab and older CPUs may run multi-seed benchmarks slowly.

Expected practical guidance:

| Run | Recommendation |
|---|---|
| Smoke | should be used first |
| Safe | should be small enough for Colab |
| Standard | may take tens of minutes |
| Strong | should be manual/overnight |
| Publication | should be planned as a long campaign |

If a “safe” run takes too long, reduce:

```text
--seed-count
--ticks / --generations
--population
--max-runs
```

Recommended Colab safe fallback:

```bash
PYTHONPATH=src python examples/collective_joss_evidence_benchmark.py   --out outputs/joss_evidence_safe   --profile quick   --seed-count 2   --ticks 8   --population 6   --workers 1   --max-runs 20   --continue-on-error   --per-run-timeout 90
```

---

## 16. Reviewer checklist

A reviewer or maintainer should be able to check:

- [ ] package installs,
- [ ] version is reported,
- [ ] smoke test passes,
- [ ] smoke benchmark creates output directory,
- [ ] `run_config.json` exists,
- [ ] `summary.json` exists,
- [ ] `run_records.csv` exists,
- [ ] `counterfactual_pairs.csv` exists,
- [ ] `claim_readiness.json` exists,
- [ ] `artifact_manifest.json` exists,
- [ ] `environment.txt` exists,
- [ ] `report.html` exists,
- [ ] `runs_failed == 0` for smoke,
- [ ] `collective_intelligence_claim_ready == false` for smoke,
- [ ] no failed/skipped/fake/placeholder artifacts are counted as positive evidence,
- [ ] benchmark level is clearly labeled.

---

## 17. Maintainer update policy

Update this file whenever:

- the runner schema changes,
- artifact names change,
- a benchmark result is archived as a release asset or Zenodo artifact,
- `0.3.0a3` or another public release is prepared,
- smoke/safe/standard profiles change,
- claim-readiness gates change,
- new metrics are added,
- stale provenance labels are fixed,
- a JOSS paper or arXiv preprint is prepared,
- external users reproduce or cite benchmark outputs.

Recommended next documentation update after this file:

```text
README.md
```

Add links to:

```text
CLAIMS.md
REPRODUCIBILITY.md
BENCHMARKS.md
```
