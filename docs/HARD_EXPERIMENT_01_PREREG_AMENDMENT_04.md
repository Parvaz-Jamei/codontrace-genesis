# HARD_EXPERIMENT_01 preregistration — Amendment 04 (Wave 1e, proper negative controls)

Product: **CodonTrace Genesis** (package `codontrace`).
Experiment id: `hard_experiment_01_capsule_source_bias`.
Schema after this amendment: `hard_experiment_01_v6`.
Identity: `0.3.0b4.dev0`. Not a new Phase letter. Not a tag or PyPI release.

Hashed **sibling** of the original prereg and Amendments 01–03. Does **not**
rewrite those files. Campaign payloads record digests for prereg + amd01 +
amd02 + amd03 + **`prereg_amendment_04_digest`** (this file).

**Freeze time:** after Wave 1d″ honesty documentation (`WAVE_1D_DOUBLE_PRIME_HONESTY.md`
/ PRIME review) and before any v6 pilot (1000–1009) or analysis seeds 11–40
under the new nulls. Science brief: `WAVE_1E_SCIENCE_BRIEF.md`.

**Blocked claims (unchanged):** `intelligence`, `collective_intelligence`,
`proved_collective_intelligence`, `agi`, `tokyo_type1_passed`,
`avida_replacement`. ClaimGate is **not** loosened. Wave 1e does **not**
auto-grant `intervention_supported`.

---

## 1. Why (broken auxiliary operationalization)

Amd 01 auxiliary H1 treated `capsules_shuffled` as a content scramble that
“severs informational content of e2,” with non-superiority vs `capsules_off`.
Wave 1d″ showed the implementation is **cyclic peer-rotation** of capsules in
the same window (`ordered[(i+1)%n]`), which **preserves the payload marginal**.
Receivers still see ~45% profitable `EAT_LUMEN` when the pool is mixed; thus
`shuffled > capsules_off` is **by construction**, not a failed gate mechanism.

Honest surplus split (v5 research): ~46.65% channel-with-50/50-pool + ~53.35%
gate — stronger than “scramble still a problem.”

Amd 04 replaces the **operational** negative control; frozen Amd 01 bytes stay
as historical text; confirmatory null for new campaigns is redefined below.

---

## 2. Willroth-style deviations table

| Item | Prior (Amd 01 / v5) | Amd 04 (v6) | Why | Confirmatory? | Timing |
|---|---|---|---|---|---|
| Content negative control | `capsules_shuffled` (CONTENT peer-rotation) | **`capsules_content_null`** (fixed null token) | Peer-rotation preserves marginal (Goldsby isolation intent unmet) | Yes — new confirmatory null | Before any v6 pilot |
| Legacy shuffled | Confirmatory non-superiority vs off | **Sensitivity / archival only** | Expected ≥ off by construction | Sensitivity | — |
| Activity control | none | **`capsules_activity_matched`** (yoked accept count) | Throughput unmatched across arms (Boot/yoked) | Auxiliary | Before v6 pilot |
| Dose pattern label | `step_up_then_saturate` | Analysis label **`step_up_then_downturn`** (1d″); Amd 01 frozen wording untouched | dose(4) outside support / = off; Simpson & Margolin; Hothorn | Disclosure | — |
| Dose S independence | used in decision | Still reported; **not** a 4th primary (`metric_count=3`); dose(1.5)≡treatment | Algebraic sum of two primary contrasts | Honesty | — |
| Adoption metrics | `capsule_adoptions` attempts | Keep attempts; use **`capsule_adoptions_accepted`** for yoking / assay | Attempts identical across arms | Instrumentation | 1d″ already |
| Primary H1 / Amd 03 ecology | on > off; roles permute; every-cell food; draws=pop | **Unchanged** | Estimand frozen | Yes | — |
| Schema | `hard_experiment_01_v5` | `hard_experiment_01_v6` | Trail | — | — |
| ClaimGate | `runtime_observation` unless full rule | **Unchanged** | Fixing null ≠ ladder promotion | Yes | — |

---

## 3. Locked algorithms (choose locked — do not retune after pilot peek)

### 3.1 `capsules_content_null` — fixed null token (preferred)

For every capsule in the read window, replace `event_pattern` /
`predicted_outcome` (payload used for adoption effect) with **`WAIT`**
(non-profitable under HE01 calibration). Channel on; emit/read/adopt
machinery live; source ids / timing may remain. Window size 1 must still
null (identity forbidden).

**Forbidden:** peer-rotation, permutation of the same multiset, SOURCE-only
shuffle, RANDOM_METADATA as content_null.

**Manipulation checks:** profitable-payload rate (`EAT_LUMEN`) on content_null
≈ 0; `content_null_replaced_rate` (or content_changed aggregate) > 0;
accepted adoptions may be > 0.

### 3.2 `capsules_activity_matched` — yoked accept count

Per analysis seed \(s\): content is null as in §3.1; successful accepts are
**capped down** to match `source_bias_on` seed \(s\)
`capsule_adoptions_accepted`. Report `activity_match_gap` =
accepted_matched − accepted_treatment. Pilot: mean absolute gap ≤ **ε = 1**
accept (pre-registered).

Activity match without content null is **not** a valid e2 negative control.

### 3.3 Legacy `capsules_shuffled`

Keep arm for sensitivity. Do **not** use for Amd 04 confirmatory
non-superiority. Expect shuffled ≥ off.

### 3.4 Oracle ladder (secondary)

Keep Amd 01 assay: `oracle > capsules_off`. Report descriptive
`oracle` vs `source_bias_off` (throughput-matched content-quality contrast).
Does not replace content_null.

---

## 4. Decision rule (Amd 04 confirmatory)

**Unchanged primary H1:** `source_bias_on` > `source_bias_off` (paired ATP).

**Auxiliary (updated):** `source_bias_on` > `capsules_content_null`; and
`capsules_content_null` does **not** beat `capsules_off` (lower 95% BCa of
`content_null − off` ≤ 0).

**Activity auxiliary:** report on vs activity_matched; volume match within ε.

**Dose:** report pattern with downturn honesty; S not independent primary.

**Legacy shuffled non-superiority:** sensitivity only; failure expected.

**`intervention_supported`:** all research-scale Amd 01 clauses under this
null operationalization, replay matched, assay valid — else
`runtime_observation`. Amd 04 alone never raises the ceiling.

---

## 5. Pilot / analysis split

| Use | Seeds | Gate |
|---|---|---|
| Pilot | 1000–1009 only | content_null EAT rate ≈ 0; mean \|activity_match_gap\| ≤ 1; assay valid; oracle > off; sd>0 on capsule-active arms |
| Analysis | 11–40 | After hashed Amd 04 + pilot PASS |

If pilot fails: stop; do not run 11–40.

---

## 6. Frozen from Amd 01 / 03

Estimand, primary on-vs-off, e2 coupling, role permute, every-cell food,
draws=pop, seeds 11–40 / pilot 1000–1009, BCa/Holm/α, blocked claims,
`results_v5.json` bytes, original prereg + Amd 01–03 bytes, Phase pins.

---

## 7. References

1. Goldsby et al. (2012) https://doi.org/10.1073/pnas.1202233109  
2. Boot et al. (2013) https://doi.org/10.1177/1745691613491271  
3. Zhang et al. (1999) / Assay Guidance Manual Z′  
4. Simpson & Margolin (1986); Hothorn (2020) downturn  
5. Willroth & Atherton (2024); Nosek et al. (2018); DeHaven (2017)  
6. Wave 1d″ honesty + PRIME review (workspace / handoff)

Smoke remains exploratory_only; ceiling `runtime_observation`.
