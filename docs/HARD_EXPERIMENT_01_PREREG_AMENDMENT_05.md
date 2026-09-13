# HARD_EXPERIMENT_01 preregistration — Amendment 05 (Wave 1e, demote activity_matched pilot gate)

Product: **CodonTrace Genesis** (package `codontrace`).
Experiment id: `hard_experiment_01_capsule_source_bias`.
Schema after this amendment: **`hard_experiment_01_v6` (unchanged)**.
Identity: `0.3.0b4.dev0`. Not a new Phase letter. Not a tag or PyPI release.

Hashed **sibling** of the original prereg and Amendments 01–04. Does **not**
rewrite those files (including Amd 04). Campaign payloads record digests for
prereg + amd01 + amd02 + amd03 + amd04 + **`prereg_amendment_05_digest`**
(this file). SCHEMA stays **v6**; trail is the amd05 digest, not a schema bump.

**Freeze time:** after Wave 1e pilot seeds 1000–1009 under Amd 04 / SCHEMA v6
(`WAVE_1E_PILOT_REPORT.md`): assay PASS; content_null PASS (EAT=0,
content_null mean = capsules_off = 28); **activity_match FAIL**
mean_abs_activity_match_gap ≈ 25.4 ≫ ε = 1; `cleared_for_11_40=false`.
Written **before** any analysis seeds 11–40 under Amd 04+05 and **before**
any ClaimGate raise. Does **not** overwrite `results_v5.json`.

**Blocked claims (unchanged):** `intelligence`, `collective_intelligence`,
`proved_collective_intelligence`, `agi`, `tokyo_type1_passed`,
`avida_replacement`. ClaimGate is **not** loosened. Amd 05 alone never
auto-grants `intervention_supported`.

---

## 1. Why (pilot FAIL on auxiliary yoke only)

Amd 04 correctly replaced the broken peer-rotation "content scramble" with
confirmatory **`capsules_content_null`** (fixed WAIT token). The Wave 1e
pilot showed that confirmatory null **works**: profitable EAT rate = 0;
content_null ATP = off ATP. The **only** Amd 04 pilot gate that failed was
the auxiliary **activity_matched** volume yoke
(`mean_abs_activity_match_gap ≤ ε = 1`).

Under the locked **cap-down-only** yoke, matched accepts cannot exceed the
content-null channel's natural accept volume. When treatment
`capsule_adoptions_accepted` is large, the yoke undershoots the budget by
construction → large |gap|. That is **unmatched throughput** (Boot et al.
yoked-control honesty), not evidence that content_null failed as an
informational negative control. Silent retune of ε inside Amd 04 would
launder a gate failure; this sibling amendment demotes the arm instead.

---

## 2. Willroth-style deviations table

| Item | Prior (Amd 04 / v6 pilot) | Amd 05 (this file) | Why | Confirmatory? | Timing |
|---|---|---|---|---|---|
| Pilot gate: activity match | Required: mean \|activity_match_gap\| ≤ ε=1 | **Demoted off pilot gate**; report gap + ε; non-blocking sensitivity | Cap-down-only yoke unmeetable when treatment accept volume ≫ null-channel capacity; unmatched volume is a limitation, not a silent fail of content_null (Boot/yoked) | No — exploratory / auxiliary | After Wave 1e pilot FAIL on activity_match only; before 11–40 |
| ε = 1 (Amd 04 §3.2) | Locked | **Unchanged** (do **not** silent-retune Amd 04) | Honesty / audit trail | Reporting only | — |
| Confirmatory null | `capsules_content_null` | **Unchanged** | Pilot PASS: EAT≈0; mean=off | Yes | — |
| Decision rule (content_null non-superiority vs off; on > content_null) | Amd 04 §4 | **Unchanged** | Estimand / confirmatory null frozen | Yes | — |
| Primary H1 / Amd 03 ecology | on > off; roles permute; every-cell food; draws=pop | **Unchanged** | Estimand frozen | Yes | — |
| `capsules_activity_matched` arm | Auxiliary; pilot-blocking | **Keep arm**; exploratory / auxiliary; report gap | Instrumentation retained | Sensitivity | — |
| Legacy shuffled | Sensitivity | **Unchanged** | Expected ≥ off | Sensitivity | — |
| Schema | `hard_experiment_01_v6` | **Keep v6** (amd05 digest in protocol/campaign) | Avoid schema churn for gate demotion | — | — |
| ClaimGate | `runtime_observation` unless full rule | **Unchanged** | Demoting auxiliary ≠ ladder promotion | Yes | — |
| `results_v5.json` | frozen | **Do not overwrite** | Trail | — | — |

---

## 3. Locked algorithms (unchanged from Amd 04 except pilot gate)

### 3.1 `capsules_content_null` — confirmatory (unchanged)

Fixed WAIT token; channel on; window-1 must still null. Manipulation checks
unchanged: profitable-payload rate ≈ 0; content_changed evidence > 0.

### 3.2 `capsules_activity_matched` — exploratory / auxiliary (gate demoted)

Per analysis seed \(s\): content null as in Amd 04 §3.1; successful accepts
**capped down** to match `source_bias_on` seed \(s\) accepts. Report
`activity_match_gap` and campaign `mean_abs_activity_match_gap`. Amd 04 ε=1
remains the **reporting reference**; it is **not** a pilot pass/fail
criterion under Amd 05. Do not retune ε; do not treat large |gap| as a
content_null failure.

### 3.3 Legacy `capsules_shuffled`

Sensitivity / archival only (unchanged).

---

## 4. Decision rule (confirmatory — unchanged from Amd 04)

**Unchanged primary H1:** `source_bias_on` > `source_bias_off` (paired ATP).

**Auxiliary (confirmatory null):** `source_bias_on` > `capsules_content_null`;
and `capsules_content_null` does **not** beat `capsules_off` (lower 95% BCa of
`content_null − off` ≤ 0).

**Activity arm:** report on vs activity_matched and the volume gap; **not**
part of confirmatory decision rule; **not** a pilot blocker under Amd 05.

**Dose / legacy shuffled / ClaimGate:** as Amd 04. Amd 05 alone never raises
the ceiling above `runtime_observation`.

---

## 5. Pilot / analysis split (Amd 05)

| Use | Seeds | Gate |
|---|---|---|
| Pilot | 1000–1009 only | assay valid (incl. oracle > off); content_null EAT rate ≈ 0 + content_changed evidence; schema v6 + amd04 + **amd05** digests present. **Activity gap reported, not required ≤ ε.** |
| Analysis | 11–40 | After hashed Amd 04 + Amd 05 + pilot PASS under **this** gate set (parent confirms before campaign) |

Wave 1e pilot under Amd 04 failed only the activity gate. Under Amd 05, that
same pilot's content_null / assay evidence **satisfies** the confirmatory
pilot gates. Do **not** re-peek 11–40 until parent confirms the research
campaign under Amd 04+05.

If confirmatory pilot gates (assay / content_null / digests) fail on a fresh
run: stop; do not run 11–40.

---

## 6. Frozen from prior amendments

Estimand, primary on-vs-off, e2 coupling, role permute, every-cell food,
draws=pop, seeds 11–40 / pilot 1000–1009, BCa/Holm/α, blocked claims,
Amd 04 algorithms and ε text, `results_v5.json` bytes, original prereg +
Amd 01–04 bytes, Phase pins, SCHEMA v6 label.

---

## 7. References

1. Boot et al. (2013) https://doi.org/10.1177/1745691613491271 — yoked /
   unmatched-volume controls; volume mismatch is a limitation disclosure,
   not automatic invalidation of the informational null.
2. Goldsby et al. (2012) https://doi.org/10.1073/pnas.1202233109
3. Willroth & Atherton (2024); Nosek et al. (2018); DeHaven (2017)
4. Amd 04 (`HARD_EXPERIMENT_01_PREREG_AMENDMENT_04.md`); Wave 1e pilot report

Smoke remains exploratory_only; ceiling `runtime_observation`.
