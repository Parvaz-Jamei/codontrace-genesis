# CodonTrace Genesis Claim Policy

Version target: `0.3.0a2`  
Release DOI: `10.5281/zenodo.20337435`  
License: `AGPL-3.0-or-later`  
Status: Public alpha research software  
Repository: `https://github.com/Parvaz-Jamei/codontrace-genesis`  
Package: `codontrace==0.3.0a2`

This document defines the strongest claims that CodonTrace Genesis can make today, the claims that require stronger benchmark evidence, and the claims that are explicitly blocked for the current release.

CodonTrace Genesis should be described confidently as a **deterministic, replay/audit-first Python research library for digital evolution and ALife experiments**. Its strongest current contribution is not merely running evolutionary simulations; it is exposing **mechanism-level evidence surfaces** so that claims about mutation, birth, death, reproduction, lineage, memory, capsule-mediated signaling, skill compression, roles, collective tasks, quality-diversity, open-endedness, and causal mechanisms can be tested through replayable records rather than asserted from raw outcomes.

This policy is intentionally:

- **Strong about implemented software capability**
- **Ambitious about the research direction**
- **Strict about final scientific conclusions**
- **Non-hardcoded about success, intelligence, or emergence**

---

## 1. Canonical public claim

The following claim is approved for README, PyPI, JOSS preparation, academic outreach, and technical discussion:

> **CodonTrace Genesis is deterministic research software for building, replaying, auditing, and evaluating digital-evolution and ALife experiments with digest-backed artifacts, explicit evidence surfaces, ablation/counterfactual-style mechanisms, and claim-gated scientific workflows.**

Shorter version:

> **CodonTrace Genesis is a Python research library for replayable, evidence-gated digital-evolution experiments and causal mechanism auditing.**

Stronger but still defensible version:

> **CodonTrace Genesis provides a modern evidence layer for digital-evolution research: deterministic replay records, runtime digests, mechanism audits, controlled ablation surfaces, and claim gates for testing ALife and evolutionary-AI hypotheses.**

Most practical one-line positioning:

> **CodonTrace Genesis helps researchers test digital-evolution and ALife claims with replayable evidence, mechanism-level records, controlled ablations, and explicit claim gates.**

---

## 2. Core positioning

CodonTrace Genesis should be positioned as an **evidence infrastructure library** for experimental digital evolution and ALife research.

It is not currently positioned as:

- a final proof of artificial general intelligence,
- a final proof of collective intelligence,
- a biological evolution simulator,
- a general-purpose genetic algorithm framework,
- a replacement for established platforms such as Avida or MABE.

It is currently positioned as:

- a deterministic and replay-aware experimental substrate,
- a mechanism-auditing layer for digital evolution,
- a claim-gated research workflow system,
- a Python library for building controlled ALife/evolution experiments,
- a platform for investigating capsule-mediated information transfer, memory links, inheritance/compression, roles, collective-behavior hypotheses, quality-diversity, and open-endedness-oriented evidence.

Approved comparative positioning:

> **CodonTrace Genesis complements classical digital-evolution platforms and general evolutionary-computation frameworks by focusing on deterministic replay, mechanism-level audit records, counterfactual-style evidence surfaces, and explicit claim gates for ALife/evolution experiments.**

Avoid:

> CodonTrace is better than Avida, MABE, DEAP, QDax, pyribs, or similar tools.

Use instead:

> CodonTrace targets a different layer: evidence integrity, replayability, and claim discipline around experimental digital evolution.

---

## 3. Stable software claims allowed now

These claims are allowed for the current public alpha release because they describe implemented software scope, packaging, metadata, and instrumentation intent rather than final scientific discoveries.

| Area | Allowed claim | Required wording discipline |
|---|---|---|
| Research software | CodonTrace Genesis is public alpha research software for digital evolution, causal mechanism auditing, replayable ALife experiments, and evidence-gated AI/evolution studies. | Say “research software” or “research library,” not “proven intelligence system.” |
| Packaging | CodonTrace Genesis is published as a Python package and can be installed from PyPI as `codontrace==0.3.0a2`. | Tie install claims to the exact version. |
| Citation | The release has a Zenodo DOI and citation metadata. | Cite the exact DOI/version used. |
| License | The public release uses `AGPL-3.0-or-later`. | Keep commercial/proprietary exceptions separate from the open license. |
| Determinism | The library is designed around deterministic experiment specifications, digests, replay records, and artifact manifests. | Do not claim every user experiment is automatically deterministic unless seeds/configs/artifacts are preserved. |
| Evidence integrity | The project includes evidence-oriented records, blocked reasons, claim manifests, output completeness records, export status records, and digest-backed audit surfaces. | Do not treat generated output as positive evidence without checking status, completeness, and claim gates. |
| Evolution primitives | The library exposes and records mechanisms around genomes, mutation, birth, death, reproduction gates, lineage, selection, survival, and diagnostics. | “Exposes/records mechanisms” is allowed; “proves evolution of intelligence” is not. |
| Capsule signaling | The library supports capsule/packet-style information-transfer policies, adoption records, utility scoring, source-fitness controls, and ablation settings. | “Supports testing capsule-mediated transfer” is allowed; “proves communication intelligence” is not. |
| Memory and learning | The library includes memory-use records, learning/inheritance records, skill-compression records, and delayed-outcome surfaces. | “Can instrument memory/learning paths” is allowed; “proves learning” requires benchmarks. |
| Role/social instrumentation | The library includes role records, role contribution records, partner interaction records, and social interaction records. | “Can study role/social behavior” is allowed; “proves collective intelligence” is blocked unless higher evidence levels pass. |
| QD/OEE instrumentation | The library includes quality-diversity and open-endedness-oriented metrics/records. | “Supports descriptive and candidate OEE analysis” is allowed; “proves open-ended intelligence” is blocked. |
| Claim gating | CodonTrace does not treat placeholder, fake, `not_run:*`, NaN, Infinity, empty digest, failed, incomplete, or skipped artifacts as positive scientific evidence. | This is a strong positive feature and should be emphasized. |

---

## 4. Inspected development-evidence snapshot

This section records the strongest evidence observed in the currently inspected runner output package. It is useful as development evidence and as a guide for the next public benchmark.

It should **not** be used as a publication-grade claim until the run is repeated on the current public release (`0.3.0a2` or newer), archived with its configuration/artifacts, and reported with enough seeds and controls.

Inspected artifact: `collective_heavy_outputs.zip`  
Runner: `codontrace_collective_intelligence_heavy_runner`  
Runner schema: `collective_heavy_runner_v1.2.0_incremental_checkpointing`  
Observed engine/package version: `0.2.0a25`  
Profile: `quick`  
Seed count: `2`  
Ticks/generations: `8`  
Population: `6`  
Workers: `1`  
Runs planned/completed/failed: `40 / 40 / 0`  
Unique result digests: `40`

Important provenance warning:

- The inspected output was generated from an older `0.2.0a25` development/release artifact, not the current public `0.3.0a2` PyPI release.
- The inspected summary includes a release-identity/provenance warning around the tested zip name.
- Therefore this snapshot is valid as **development evidence** and **instrumentation evidence**, but not as a final public benchmark for `0.3.0a2`.

### 4.1 Evidence categories observed

| Evidence family | Observed? | Notes |
|---|---:|---|
| Evolution primitives | yes | Energy/action/fitness/reproduction, birth, mutation, child genome/admission, lineage, and survival-related records were present. |
| Memory primitives | yes | Memory-use and delayed-reward surfaces were observed. |
| Capsule primitives | yes | Capsule adoption, cost, utility, and source-fitness records were observed. |
| QD primitives | yes | QD selection and parent-feedback audit records were observed. |
| Social/partner interaction | yes | Capsule-learning and resource-competition interaction records were observed. |
| Behavior diversity | yes | Behavior descriptors and unique behavior descriptor summaries were produced. |
| Claim readiness gates | yes | Claim-readiness output existed and blocked collective-intelligence readiness. |
| Collective intelligence | no | The runner explicitly marked collective-intelligence claim readiness as false. |

### 4.2 Aggregate output records observed

The inspected quick output produced broad instrumentation coverage:

| Record family | Count |
|---|---:|
| energy accounting records | `1604` |
| death reason records | `1604` |
| death classification records | `1604` |
| action cost records | `1604` |
| action reward records | `1604` |
| fitness breakdown records | `1604` |
| selection fitness records | `1604` |
| reproduction attempt records | `1604` |
| reproduction gate records | `1604` |
| birth event records | `442` |
| child genome records | `74` |
| child admission records | `442` |
| mutation plan records | `74` |
| mutation result records | `74` |
| learning inheritance records | `74` |
| skill compression records | `74` |
| ADF inheritance records | `74` |
| lineage growth records | `316` |
| behavior descriptors | `1604` |
| memory use records | `1138` |
| delayed reward records | `6` |
| capsule adoption records | `62` |
| capsule cost records | `62` |
| capsule utility records | `62` |
| capsule source-fitness records | `62` |
| social interaction records | `77` |
| partner interaction records | `77` |
| role records | `1604` |
| role timeline records | `1604` |
| role contribution records | `1604` |
| QD selection audit records | `220` |
| QD parent-feedback audit records | `192` |
| generalization records | `40` |
| engine digest audit records | `200` |
| strong claim ladder records | `40` |
| output completeness records | `2600` |
| export status records | `2600` |

This supports a strong software claim:

> **CodonTrace Genesis can produce multi-family, digest-backed, tabular and JSON/HTML evidence artifacts spanning evolution, memory, capsule signaling, social/partner interactions, role records, QD audits, behavior diversity, claim-readiness, and output completeness.**

It does **not** by itself support a strong scientific claim of collective intelligence.

### 4.3 Counterfactual-style observations from inspected output

The following observations were present in the inspected quick run. They should be treated as **candidate instrumentation evidence**, not final scientific results.

| Pair | Observed delta pattern | Interpretation |
|---|---|---|
| `high_communication` vs `no_capsules` | `+27` capsule adoption, `+27` capsule utility, `+15` social interaction per inspected seed | Strong instrumentation evidence for capsule-path activation under the quick scenario. Requires larger benchmark for outcome/effect claims. |
| `baseline` vs `no_memory` | `+9` memory-use records and `+1` delayed-reward record per inspected seed | Candidate evidence that the memory pathway is toggled and recorded. Requires outcome-level validation. |
| `birth_friendly` vs `no_reproduction` | `+10` to `+12` birth-event records and `+36` reproduction-gate records across inspected seeds | Strong evidence that birth/reproduction controls are observable in the runner. |
| `collective_mixed` vs `no_capsules` | `0` delta for social interaction, partner interaction, and capsule adoption in inspected seeds | Negative evidence for collective-intelligence readiness under this quick profile. |
| `high_mutation` vs `no_mutation` | mixed birth-event deltas and no mutation-result delta in inspected pair summary | Not sufficient for a mutation-effect claim. Needs protocol refinement. |

Approved interpretation:

> **The inspected quick runner demonstrates that CodonTrace can generate controlled evidence surfaces and counterfactual-style pair summaries. It provides candidate evidence for capsule, memory, and reproduction instrumentation, but it does not establish collective intelligence or publication-grade causal effects.**

---

## 5. Claim ladder

CodonTrace claims should move through evidence levels. Stronger language is allowed only when the required evidence exists.

| Level | Name | What it means | Minimum evidence |
|---:|---|---|---|
| 0 | Software capability | The library exposes the mechanism/API/record type. | Source code, API docs, tests, examples. |
| 1 | Runtime observation | The mechanism occurred or was recorded in at least one valid run. | Successful run, version, config, seed, artifact manifest, non-empty records. |
| 2 | Candidate evidence | A controlled comparison shows a consistent measured difference. | Treatment/control, seed list, paired summary, no failed/placeholder evidence. |
| 3 | Mechanism support | Ablation/intervention/counterfactual-style evidence supports a mechanism-outcome link. | Ablation protocol, negative controls, replay audit, effect direction, artifact completeness. |
| 4 | Replicated effect | The effect is stable across enough seeds/configurations and survives sanity checks. | Multi-seed campaign, effect sizes, uncertainty intervals or statistical tests, robustness checks. |
| 5 | Publication-grade scientific claim | The claim is suitable for a paper/preprint or benchmark-backed scientific result. | Archived artifact, exact version, DOI, complete configs, analysis scripts, documented limitations, statistical and ablation evidence. |

---

## 6. Claims approved by level

### Level 0–1 claims allowed now

These can be used immediately, provided exact version/release context is shown:

- CodonTrace Genesis provides a deterministic experiment substrate for digital evolution and ALife-style research workflows.
- CodonTrace Genesis exposes mechanism-level records for mutation, birth, death, reproduction gates, lineage, memory, capsule signaling, skill compression, roles, social/partner interactions, QD audit surfaces, and open-endedness-oriented metrics.
- CodonTrace Genesis produces digest-backed artifacts, runtime records, output completeness records, and export status records intended for replayable analysis.
- CodonTrace Genesis includes claim-gating discipline that prevents placeholder/fake/failed/invalid artifacts from being counted as positive evidence.
- CodonTrace Genesis can be used to construct controlled treatment/control and ablation-style experiments around information transfer, memory, reproduction, roles, and behavior diversity.
- CodonTrace Genesis is suitable for building controlled ALife/digital-evolution experiments and reviewing scientific evidence schemas.

### Level 2 candidate claims allowed with inspected-output wording

These are allowed only with careful wording such as “observed in an inspected quick run,” “candidate instrumentation evidence,” or “development evidence.”

- In the inspected quick output, capsule-enabled variants produced capsule adoption, utility, source-fitness, and social interaction records, while the no-capsule control produced zero capsule records in the paired comparison.
- In the inspected quick output, memory-enabled variants produced memory-use and delayed-reward records relative to a no-memory control.
- In the inspected quick output, birth-friendly variants produced more birth-event and reproduction-gate records than no-reproduction controls.
- The inspected quick output demonstrates a working multi-family evidence-export path across CSV, JSON, JSONL, HTML, logs, and manifest files.
- The inspected quick output demonstrates that claim-readiness logic can refuse collective-intelligence claims even when social/capsule/memory/QD building blocks are present.

### Level 3–5 claims not yet approved

These require a stronger public benchmark:

- Capsule-mediated transfer improves fitness, survival, reproduction, adaptation, or group performance.
- Memory mechanisms causally improve later behavior or delayed reward.
- Skill compression improves offspring survival, memory reuse, fitness, or reproduction.
- Roles are functionally specialized rather than labels.
- Group behavior outperforms individual baselines.
- Collective intelligence emerges under controlled conditions.
- Open-endedness is demonstrated beyond descriptive novelty accumulation.
- CodonTrace outperforms established tools or baselines.

---

## 7. Explicitly blocked claims for the current release

The following claims must not be made for `0.3.0a2` unless a future paper/benchmark explicitly satisfies the required evidence level.

- CodonTrace has proven artificial general intelligence.
- CodonTrace has proven consciousness or subjective experience.
- CodonTrace has proven collective intelligence.
- CodonTrace has proven open-ended intelligence as a settled scientific result.
- CodonTrace is superior to Avida, MABE, DEAP, QDax, pyribs, or other established tools by benchmark evidence.
- CodonTrace reproduces biological evolution in a biologically faithful sense.
- CodonTrace proves that capsule communication is causal without ablation/outcome evidence.
- CodonTrace proves learning merely because memory records exist.
- CodonTrace proves social intelligence merely because partner or social interaction records exist.
- CodonTrace proves role specialization merely because role records exist.
- CodonTrace proves QD/open-endedness merely because behavior diversity or novelty metrics exist.
- CodonTrace proves intelligence merely because behavior appears complex.

---

## 8. Evidence rules

Positive evidence must satisfy all relevant checks:

1. The exact package version must be recorded.
2. The code source or release artifact must be recorded.
3. The seed list must be recorded.
4. The run configuration must be preserved.
5. Generated artifacts must include a manifest or artifact index.
6. Failed, skipped, incomplete, placeholder, fake, `not_run:*`, NaN, Infinity, and empty-digest outputs must not be treated as positive evidence.
7. Treatment/control comparisons should use paired seeds where possible.
8. Causal claims require ablation, intervention, or counterfactual-style evidence.
9. Collective claims require group-over-individual improvement, communication/control ablation, role complementarity, heldout/unfamiliar partner checks, and robustness across seeds.
10. Publication claims require archived artifacts and enough documentation for independent rerun.
11. Results generated on older development artifacts must be labeled as development evidence unless repeated on the current public release.
12. Descriptive event counts are not equivalent to outcome improvement.

---

## 9. Publication-grade benchmark gates

For a future strong benchmark, the following minimum gates are recommended.

| Claim target | Minimum gates |
|---|---|
| Capsule-mediated transfer effect | `>= 12` seeds, paired `high_communication` vs `no_capsules`, utility/outcome metrics, source-fitness controls, no-signal-memory-link ablation. |
| Memory effect | `>= 12` seeds, `baseline` vs `no_memory`, delayed outcome window, memory-read/write/action trace, negative control. |
| Skill compression effect | `>= 12` seeds, `full_compression` vs `disabled/capacity_only/shuffle/null`, child outcome audit, sibling or matched controls. |
| Reproduction/birth mechanism | `>= 12` seeds, `birth_friendly` vs `no_reproduction`, birth gates, child admission, lineage growth, nonfatal gate diagnostics. |
| Role specialization | Role persistence, role switch cost, role contribution, role ablation, heldout partner evaluation. |
| Collective behavior | Group-over-individual improvement, non-capsule cooperation control, communication ablation, role complementarity, heldout partner tests, multi-seed effect size. |
| Open-endedness | Novelty accumulation plus persistence, complexity growth, adaptive success, lineage persistence, behavior-space expansion, learnability, and controls. |

Recommended next public benchmark baseline:

```bash
python examples/collective_joss_evidence_benchmark.py   --seed-count 12   --ticks 40   --population 16   --workers 1   --variants high_communication,no_capsules,no_packet_utility,no_packet_source_fitness,no_signal_memory_link,baseline,no_memory,no_skill_compression,no_adf_inheritance   --output-dir outputs/joss_collective_evidence_v1
```

Stress/publication candidate:

```bash
python examples/collective_joss_evidence_benchmark.py   --seed-count 20   --ticks 60   --population 24   --workers 2   --output-dir outputs/joss_collective_evidence_v1_stress
```

---

## 10. JOSS-safe wording

For JOSS, the focus should be the software, not a new scientific discovery.

Approved JOSS-style wording:

> **CodonTrace Genesis provides a research-software framework for deterministic digital-evolution experiments with replayable evidence records, mechanism-level audit surfaces, and claim-gated workflows for testing ALife hypotheses.**

Avoid in JOSS paper unless supported by separate publication-grade evidence:

> CodonTrace Genesis proves collective intelligence.

Better wording:

> **CodonTrace Genesis includes example workflows for investigating collective-behavior hypotheses under explicit ablation and claim-gating protocols.**

JOSS-oriented statement:

> **The examples in this repository demonstrate reproducible instrumentation and evidence generation. They are not presented as final proof of intelligence or collective intelligence.**

---

## 11. Approved wording by context

### README / GitHub About

> CodonTrace Genesis is deterministic research software for digital evolution, causal mechanism auditing, replayable ALife experiments, and evidence-gated AI/evolution studies.

### PyPI

> A Python research library for replayable digital-evolution experiments, causal mechanism auditing, and claim-gated ALife workflows.

### Academic outreach

> CodonTrace Genesis provides a replayable evidence layer for digital-evolution experiments, including mechanism records, ablation surfaces, runtime digests, and claim gates for testing ALife hypotheses.

### LinkedIn / public technical post

> I built CodonTrace Genesis to make digital-evolution experiments more auditable: instead of only showing final outcomes, it records mechanisms, digests, ablations, and claim gates so claims can be tested with replayable evidence.

### JOSS paper

> CodonTrace Genesis is research software for constructing and auditing controlled digital-evolution experiments. It focuses on deterministic replay, artifact completeness, mechanism-level records, and claim-gated workflows.

### Future scientific paper

Use only if benchmark gates pass:

> We report controlled evidence for [specific effect] under [specific protocol], with paired seeds, ablations, replay manifests, archived artifacts, and documented limitations.

---

## 12. Citation and research-use statement

If you use CodonTrace Genesis in research, please cite the exact software release DOI and repository.

Use of the software does not automatically imply co-authorship. Co-authorship may be appropriate when there is substantial collaboration in experimental design, analysis, interpretation, validation, or manuscript writing.

Commercial or proprietary use cases that cannot comply with `AGPL-3.0-or-later` may contact the author to discuss a separate license.

Suggested citation target:

- Software DOI: `10.5281/zenodo.20337435`
- Repository: `https://github.com/Parvaz-Jamei/codontrace-genesis`
- Package: `codontrace==0.3.0a2`

---

## 13. Reference context

This claim policy is written with the following research-software context in mind:

- JOSS publishes research software and expects clear research application, open-source licensing, documentation, tests, and software-focused papers rather than papers focused on new results produced by the software.
- Avida is a classic digital-evolution platform for experiments with self-replicating/evolving digital organisms.
- MABE is a modular framework for constructing and comparing digital-evolution experiments.
- DEAP is a general Python evolutionary-computation framework designed around explicit algorithms and transparent data structures.

Reference URLs:

- https://joss.readthedocs.io/en/latest/submitting.html
- https://joss.theoj.org/about
- https://alife.org/encyclopedia/digital-evolution/avida/
- https://alife.org/encyclopedia/software-platforms/mabe/
- https://deap.readthedocs.io/

---

## 14. Maintainer note

This file should be updated whenever a new public benchmark, JOSS paper, arXiv preprint, Zenodo artifact, or independent external use changes the evidence status of the project.

Recommended update triggers:

- a benchmark is rerun on `0.3.0a2` or newer,
- a new Zenodo artifact is created,
- an external user cites or uses the library,
- a JOSS/arXiv/paper artifact is prepared,
- collective, memory, capsule, role, or open-endedness evidence moves to a higher claim level,
- a previously blocked claim becomes supported by replicated evidence.
