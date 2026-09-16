# A Claim Ladder for Computational Evolution / ALife Experiments

**Protocol version:** `CLAIM_LADDER_PROTOCOL_v0.1`  
**Product:** CodonTrace Genesis  
**Public ladder:** [`CLAIMS.md`](../../CLAIMS.md) §5  
**Evidence rules:** [`CLAIMS.md`](../../CLAIMS.md) §8  
**Identity:** development `0.3.0b4.dev0` (PyPI tip `0.3.0b3`)  
**Status:** Wave 3 documentation only — does not loosen ClaimGate, invent
Phase letters, or raise any granted ceiling.

This document is a **protocol**: how to grade claims about digital-evolution
and ALife experiments. It is not a software release note, not a Tokyo Type 1
pass, and not a license to claim intelligence.

Companion surfaces:

| Surface | Role |
|---|---|
| [`CLAIMS.md`](../../CLAIMS.md) §5 / [`CLAIM_LADDER.md`](../CLAIM_LADDER.md) | Canonical public 0–5 names |
| [`CLAIM_LADDER_MAP.md`](../CLAIM_LADDER_MAP.md) | Internal 9-rung → public 0–5 map |
| [`CLAIMGATE_STANDALONE.md`](../CLAIMGATE_STANDALONE.md) | Simulator-agnostic auditor |
| This protocol | How to *design and grade* experiments so the ladder is honest |

---

## 1. Motivation

Computational evolution and ALife papers often report rich event counts,
pretty trajectories, and strong verbs (“emerged,” “learned,” “cooperated”)
from a single configuration. The claim ladder exists so that **language
cannot outrun evidence**.

Three literature anchors shape the protocol:

### 1.1 Pineau et al. 2021 — reproducibility checklists

Pineau-style machine-learning reproducibility checklists ask whether the
claim can be *re-run and audited*: code, seeds, compute, hyperparameters,
evaluation protocol, and negative results. CodonTrace Genesis adapts that
discipline to ALife: every claim grade requires a Yes / No / NA checklist
(§9), not a vibes-based upgrade.

### 1.2 ODD (Grimm et al.) — Overview, Design concepts, Details

Agent-based and digital-organism models need an explicit **ODD** description
before causal language is allowed. What entities exist? Which processes fire
at which schedule? Which state variables are observed? Without ODD-level
transparency, an “ablation” may cut a knob that was never on the causal path.
HARD_EXPERIMENT_01 Wave E6 records overlay ODD at `runtime_observation`
only ([`HARD_EXPERIMENT_01_ODD.md`](../HARD_EXPERIMENT_01_ODD.md)).

### 1.3 ASME V&V 40 — context-of-use, not a universal score

ASME V&V 40 treats model credibility as **context-of-use (COU)** and
**risk-informed**. There is no universal numeric “validation score” that a
simulator either passes or fails. ClaimGate and this ladder are complementary:
V&V 40 asks whether a model is credible *for a stated use and risk*; the
claim ladder asks whether a **claim wording** is licensed *by the evidence
in hand*. A high ladder level is still not a V&V 40 argument without an
explicit COU. See [`design/ASME_VV40_CONTEXT_OF_USE.md`](../design/ASME_VV40_CONTEXT_OF_USE.md).

---

## 2. Levels 0–5 and anti-patterns

Public names and minimum evidence are frozen in [`CLAIMS.md`](../../CLAIMS.md) §5.
Restated for protocol use:

| Level | Name | What it means | Minimum evidence |
|---:|---|---|---|
| 0 | Software capability | The library exposes the mechanism / API / record type. | Source, API docs, tests, examples. |
| 1 | Runtime observation | The mechanism occurred or was recorded in at least one valid run. | Successful run, version, config, seed, artifact manifest, non-empty records. |
| 2 | Candidate evidence | A controlled comparison shows a consistent measured difference. | Treatment/control, seed list, paired summary, no failed/placeholder evidence. |
| 3 | Mechanism support | Ablation / intervention / counterfactual-style evidence supports a mechanism–outcome link. | Ablation protocol, negative controls, replay audit, effect direction, artifact completeness. |
| 4 | Replicated effect | The effect is stable across enough seeds / configurations and survives sanity checks. | Multi-seed campaign, effect sizes, uncertainty intervals or tests, robustness checks. |
| 5 | Publication-grade scientific claim | Suitable for paper / preprint / benchmark-backed result. | Archived artifact, exact version, DOI, complete configs, analysis scripts, documented limitations, statistical + ablation evidence. |

Internal ClaimGate still uses nine named rungs; that is a finer evaluator,
not a second public policy ([`CLAIM_LADDER_MAP.md`](../CLAIM_LADDER_MAP.md)).

### 2.1 Anti-pattern: event count ≠ outcome

Adoption counts, birth events, memory-use records, and social-interaction
rows are **instrumentation**. They are allowed at level 0–1. They do **not**
by themselves support “improved fitness,” “learned,” or “cooperated.”
CLAIMS.md §8 rule 12: descriptive event counts are not equivalent to
outcome improvement.

### 2.2 Anti-pattern: Cov ≠ causality

A Price equation identity (or any covariance between a trait and fitness)
is a **statistical decomposition**, not a causal claim (Okasha & Otsuka
2020). Causal language requires an explicit DAG, an intervention that cuts
or modulates an edge, and an estimand that actually moved. “Covariance
observed” stays at most candidate / runtime wording until interventions
exist.

### 2.3 Anti-pattern: bitwise-identical arms = scientific null

If treatment, ablation, channel-off, and negative-control arms produce
**bitwise-identical** outcomes on the estimand, the manipulation was not
realized. Label: **`assay_invalid`**. That is **not** a scientific null
finding and does **not** grant mechanism support.

### 2.4 Anti-pattern: metrics auto-grant a pass

MODES numbers and Channon 2024 Tokyo Type 1 *measurement steps* do not
auto-grant OEE, `tokyo_type1_passed`, or level 3+. Measurement ≠ claim
grading (§7).

---

## 3. Intervention taxonomy

Every causal campaign should name which DAG edge each arm cuts or modulates.
HARD_EXPERIMENT_01’s capsule DAG is the reference shape:

```text
gate → which capsule is adopted → action → ATP → terminal fitness
```

| Intervention class | Intent | Typical arm |
|---|---|---|
| **Mechanism ablation** | Cut or disable the hypothesized mechanism while leaving the channel present | `source_bias_off` (gate threshold / weighting ablated) |
| **Channel-off** | Remove the entire transfer pathway | `capsules_off` (`enabled=False`) |
| **Shuffled / negative control** | Keep activity / traffic but destroy informational content | `capsules_shuffled` / later `capsules_content_null` |
| **Dose-response** | Modulate mechanism intensity; expect a preregistered pattern | `min_source_fitness ∈ {0, 1.5, 4}` with a named pattern test |
| **Heldout** | Stability under partner / world / seed-block shift; leakage checks | Held-out partners, held-out exploratory seeds (e.g. Morris 2000–2009) |

Rules of use:

1. **Preregister** arms, estimand, and decision rule *before* numbers.
2. Each knob maps to **one DAG edge** (or an explicit bundle of edges).
3. A negative control that accidentally preserves the payload marginal is
   a **design caveat**, not silent mechanism proof (see HE01 Wave 1d″).
4. Positive controls (e.g. `oracle_capsule`) diagnose assay reachability;
   they are not the scientific claim.

---

## 4. Statistical floor

The floor is intentionally boring and hard to game:

| Requirement | Why |
|---|---|
| Paired seeds across arms | Removes seed as a confounder for primary contrasts |
| Effect size (e.g. paired dz) | Magnitude, not only a p-value |
| Uncertainty (e.g. BCa bootstrap CI) | Interval that can include 0 → claim downgrade |
| Exact or permutation test where feasible | Small-n honesty |
| Multiplicity control (e.g. Holm) on the **preregistered** primary family | Stops contrast shopping |
| `claim_downgraded` when CI includes 0 | Software enforces the verbal rule |
| Missing outcomes dropped, never zero-filled | Empty populations are not “fitness 0 success” |
| Assay / manipulation gate *in front of* inference | Extinction, zero adoptions, or unrealized manipulation → stay at level 1 |

A genuine measured null **after a realized manipulation** is valid evidence
and does not grant mechanism support. An unrealized manipulation is
`assay_invalid`, not a null.

Research-scale guidance for CodonTrace Genesis hard experiments (CLAIMS.md
§9 style): on the order of ≥12–30 paired seeds, explicit ticks/population,
and archived digests. Smoke (`n` small, short ticks) is `exploratory_only`
and never unlocks level 3+.

---

## 5. Replay / digest requirement

No claim above level 1 without replayable identity:

1. Exact package / development identity recorded (`0.3.0b4.dev0` on `main`).
2. Spec / config / seed list preserved.
3. Artifact manifest or campaign JSON with digests.
4. Replay check: re-execute (or snapshot-digest match) for declared
   arm × seed pairs; **campaign construction refuses a mismatch**.
5. Failed, skipped, incomplete, placeholder, `not_run:*`, NaN, Infinity,
   and empty-digest outputs are never positive evidence (CLAIMS.md §8).

Digests are never faked. Independent digest replay (Phase J pathway) can
support `replay_verification` flags when actually earned; it does not
auto-grant `collective_intelligence`.

---

## 6. Worked example — HARD_EXPERIMENT_01 path

Facts below follow [`CLAIMS.md`](../../CLAIMS.md) §4.4. The public ceiling
recorded there for the HE01 wave series is **`runtime_observation`
(level 1)**. This protocol does **not** invent `intervention_supported`
when CLAIMS grants `runtime_observation`.

Question (one measurement, not a Phase letter): does source-fitness-weighted
capsule transfer raise the preregistered outcome relative to mechanism
ablation, channel-off, and a negative control?

### 6.1 Wave 1 (`results_v1.json`) — invalid null

- 30 seeds (`11`…`40`), 40 ticks, population 16.
- Extinction rate 1.0; adoptions 0 on every arm; last-tick mean fitness
  identically 0.
- The source-bias gate was **never exercised** (channel did not transfer).
- Ladder verdict: **invalid null / assay failure**, ceiling
  **`runtime_observation`**. Numerically defined CIs of `[0,0]` were
  *not* allowed to become a scientific null on the causal question.

### 6.2 Wave 1b (`results_v2.json`) — `assay_invalid`

- Survival calibration kept the estimand; populations survived;
  treatment adoptions mean 169.0; `assay_failed=false` on the crash gate.
- All four arms produced **bitwise-identical** `terminal_mean_fitness`
  `0.164375` (adoptions `169 / 169 / 0 / 169`).
- Ladder verdict: **`assay_invalid`** (manipulation not realized on the
  fitness estimand). Still **`runtime_observation`**. Wave 2 standalone
  auditor must reproduce public level 1 from the committed v2 artifact.
  Not mechanism support. Not collective intelligence.

### 6.3 Later validity work (1c / 1d′ / 1e / E6) — still CLAIMS-honest

CLAIMS.md §4.4 continues the story without raising the granted ceiling:

| Wave | What the ladder caught | CLAIMS §4.4 ceiling |
|---|---|---|
| **1c (v3)** | Manipulation realized (gate rejects only in treatment; positive control moved ATP; dose pattern matched) but **sd = 0 across seeds** → dz undefined; 30 “seeds” = 30 replays of one configuration | `runtime_observation` |
| **1d′ (v5)** | Assay PASS; decision-rule FAIL on `shuffled_better_than_capsules_off` (peer-rotation preserves payload marginal — design caveat) | `runtime_observation` |
| **1d″** | Evidence-honesty docs only; no claim raise | `runtime_observation` |
| **1e** | Confirmatory content-null / activity-matched redesign on branch; CLAIMS §4.4 records pilot + **ceiling stays `runtime_observation`** | `runtime_observation` |
| **E6** | ODD + exploratory Morris on held-out seeds; not Holm/BCa; not ClaimGate input | `runtime_observation` |

**Approved reading (CLAIMS.md §4.4):** Wave 1 is a runtime observation of
an invalid-null crash. Wave 1b is a runtime observation labeled
`assay_invalid`. ClaimGate did not grant `intervention_supported`.
Later waves improved assay validity and honesty; they do not rewrite the
§4.4 granted ceiling in this protocol.

The ladder’s job on this path was exactly to **stop promotion**: crash ≠
null; identical arms ≠ null; realized manipulation without seed variance ≠
inference; broken negative control ≠ mechanism proof.

---

## 7. Relation to MODES / Channon 2024 — complementary

| Neighbor | What it is | What it is not |
|---|---|
| **MODES** (Dolson et al. 2019) | Measurement toolbox: change, novelty, complexity, ecological potential after a persistence filter | A claim pass |
| **Channon 2024 Tokyo Type 1** | Measurement-step procedure / vocabulary | `tokyo_type1_passed` |
| **This claim ladder** | Grades *claim wording* given evidence | A novelty metric |

CodonTrace Genesis may expose `oee_measurement_only` /
`tokyo_type1_measurement_only` hooks. Recording steps is allowed.
Auto-granting a pass from metrics is forbidden. Measurement and claim
grading are **complementary**: you need both honest meters and honest
verbs. See [`design/MODES_CHANNON_MEASUREMENT_NEIGHBORS.md`](../design/MODES_CHANNON_MEASUREMENT_NEIGHBORS.md).

---

## 8. Limitations

1. **Protocol ≠ earned claim.** Publishing this file does not move any
   experiment to level 3–5.
2. **CLAIMS.md is authoritative.** If narrative docs and §4.4 disagree,
   §4.4 wins for granted ceilings.
3. **Context-of-use still required.** Ladder level 5 without an ASME-style
   COU is not a V&V 40 credibility argument.
4. **Simulator scope.** The standalone auditor’s Avida / MABE2 paths are
   ingest skeletons, not full platform support.
5. **Forbidden aliases unchanged.** Never claim intelligence, collective
   intelligence, or AGI. Also blocked at every level: `tokyo_type1_passed`,
   `avida_replacement`, and related forms.
6. **Hard bans for this wave:** no new-goal / ASAL / OMNI / LLM / ESP32 /
   differentiation-goal content is introduced by this protocol wave.
7. **HE02 and later hard experiments** are out of scope here; this document
   does not touch their code or configs.
8. **Identity unchanged:** `0.3.0b4.dev0`. No tag. No PyPI publish.

---

## 9. Yes / No / NA checklist (Pineau-style)

Use **Yes**, **No**, or **NA**. Any **No** on a row required for the target
level blocks promotion to that level.

### 9.1 Provenance and identity

| # | Item | Y/N/NA |
|---|---|---|
| P1 | Exact package / development identity recorded | |
| P2 | Code source or release artifact recorded | |
| P3 | Seed list recorded and paired across arms | |
| P4 | Full run configuration preserved | |
| P5 | Artifact manifest / campaign JSON with digests present | |
| P6 | Older development artifacts labeled as development evidence | |

### 9.2 Assay and estimand

| # | Item | Y/N/NA |
|---|---|---|
| A1 | Prereg (or dated amendment) committed before numbers | |
| A2 | Primary estimand named and unchanged without amendment | |
| A3 | ODD / mechanism description sufficient to locate DAG edges | |
| A4 | Treatment assay exercised the channel (not extinct / not zero adoptions when required) | |
| A5 | Manipulation check passed (arms not bitwise-identical on estimand) | |
| A6 | Missing outcomes dropped, never zero-filled | |

### 9.3 Interventions and controls

| # | Item | Y/N/NA |
|---|---|---|
| I1 | Mechanism ablation arm present and mapped to a DAG edge | |
| I2 | Channel-off arm present | |
| I3 | Negative / shuffled / content-null control present and interpreted honestly | |
| I4 | Dose-response pattern preregistered (or NA) | |
| I5 | Heldout / robustness block defined (or NA for this claim level) | |

### 9.4 Statistics and replay

| # | Item | Y/N/NA |
|---|---|---|
| S1 | Effect size reported for primary contrasts | |
| S2 | Uncertainty interval or equivalent reported | |
| S3 | Multiplicity control applied to the preregistered family | |
| S4 | Seed variance adequate for inference (sd not structurally zero) | |
| S5 | Replay / digest identity matched for declared arm × seed pairs | |
| S6 | Failed / placeholder / empty-digest artifacts excluded from positive evidence | |

### 9.5 Claim wording

| # | Item | Y/N/NA |
|---|---|---|
| C1 | Claim language matches the highest level actually earned | |
| C2 | Event counts not presented as outcome improvement | |
| C3 | Covariance / Price identity not presented as causality without interventions | |
| C4 | Metrics (MODES / Tokyo measurement) not presented as a pass | |
| C5 | Forbidden aliases absent | |
| C6 | Limitations section present for level ≥3 targets | |

**Promotion rule:** level *k* requires Yes (or justified NA) on every row
marked required for *k* in CLAIMS.md §5 + §8. Doubt → lower level.

---

## References (protocol anchors)

- Pineau, J., et al. (2021). Improving reproducibility in machine learning research (NeurIPS checklist / JoML line of work).
- Grimm, V., et al. (2005/2020). The ODD protocol for describing agent-based and individual-based models.
- ASME V&V 40. Assessing credibility of computational modeling through verification and validation: application to medical devices (context-of-use / risk-informed credibility).
- Dolson, E., et al. (2019). MODES toolbox (measurement after persistence filtering).
- Channon, A. (2024). Tokyo Type 1 open-ended evolution measurement procedure.
- Okasha, S., & Otsuka, J. (2020). Causal foundations for multilevel selection / Price readings.

---

## Document control

| Field | Value |
|---|---|
| Protocol id | `CLAIM_LADDER_PROTOCOL_v0.1` |
| Wave | 3 (docs only) |
| ClaimGate | Not loosened |
| HE02 / `feat/he02-e1-e2-e5` | Untouched |
| Supersedes | Nothing — complements [`CLAIM_LADDER.md`](../CLAIM_LADDER.md) |
