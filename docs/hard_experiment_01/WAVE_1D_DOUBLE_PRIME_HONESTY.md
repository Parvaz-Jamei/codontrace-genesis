# Wave 1d″ — evidence honesty (HE01)

**Scope:** evidence honesty ONLY. No new ClaimGate claim, no Amendment 01/03
rewrite, no full re-campaign, no overwrite of `results_v5.json`.

**Source of truth:** user review captured at
[`handoff/WAVE_1D_PRIME_REVIEW.md`](../../handoff/WAVE_1D_PRIME_REVIEW.md)
(reported SHA `74197d0` was **not** on `origin/main` when checked; substance
from workspace handoff + user paste).

**ClaimGate ceiling:** remains **`runtime_observation`** (level 1). Do **not**
invent `intervention_supported`.

---

## TL;DR (English)

Wave 1d′ is honest and reproducible, but “scientifically closed” was wrong.
The `capsules_shuffled` control is a **cyclic peer-rotation**
(`ordered[(index+1)%n]`) that **preserves the payload marginal**. So shuffled
still delivers profitable `EAT_LUMEN` ~45% of the time, and
`shuffled > capsules_off` is **by construction**, not a failed mechanism.
Honest split of treatment surplus (~30.69 ATP): ~46.65% channel-with-50/50-pool
(~14.31) + ~53.35% gate (~16.49). Additional metric caveats: `capsule_adoptions`
counts **attempts** not accepts; dose(1.5)≡treatment and dose S is an algebraic
sum of two primary contrasts; dose(4.0) is outside support (downturn, not
saturate). Wave 1e (proper content-null + activity-matched arms) is deferred to
Amendment 04.

## TL;DR (فارسی — کوتاه)

موج 1d″ فقط **صداقت شواهد** است، نه ادعای جدید. کنترل
`capsules_shuffled` یک **چرخش دوری** است که توزیع محتوا را حفظ می‌کند؛ پس
`shuffled > capsules_off` از روی ساخت است، نه شکست سازوکار. حدود ۴۷٪ از
مازاد درمان (~۳۰.۶۹ ATP) از کانال با استخر ۵۰/۵۰ و حدود ۵۳٪ از گیت است.
`capsule_adoptions` تلاش است نه پذیرش موفق. سقف ClaimGate همان
`runtime_observation` می‌ماند. Wave 1e (بازوهای null محتوا / هم‌سطح‌شدهٔ
فعالیت) برای Amd 04 به تعویق افتاد.

---

## Core scientific correction

`apply_capsule_shuffle_control` / CONTENT peer rotation assigns each capsule
the event pattern / predicted outcome of
`ordered[(index + 1) % n]`. That is a **cyclic content swap**:

- The **multiset** of `event_pattern` values in the window is unchanged.
- Window size 1 is identity (`content_changed=false`).
- Therefore `capsules_shuffled` still presents profitable `EAT_LUMEN` at the
  calibrated rate (~44.8% in the review) whenever the pool is mixed.
- Decision-rule failure `shuffled_better_than_capsules_off` on v5 is expected
  under this control design; it does **not** by itself prove the treatment
  mechanism failed.

Honest decomposition of total treatment surplus vs `capsules_off`
(~30.69 ATP on v5 means):

| Component | Contrast (approx.) | ATP | Share |
|---|---|---:|---:|
| Channel present with 50/50 pool | `capsules_shuffled − capsules_off` | ~14.31 | ~46.65% |
| Gate | `source_bias_on − source_bias_off` (≈ on − shuffled) | ~16.49 | ~53.35% |

That sentence is stronger than “scrambled still a problem.”

---

## Findings / blockers documented (not “fixed” by a new campaign)

1. **Adoption metric:** `capsule_adoptions` / `adoption_mean` = **attempts**
   (`len(capsule_adoption_records)`, including blocked). New additive field
   `capsule_adoptions_accepted` / `adoption_accepted_mean` counts
   `adoption_success is True`. Historical v5 `~542.53` identical across
   gated arms is attempt-count identity, not accept identity.
2. **Shuffle audit not in artifact:** `CapsuleShuffleRecord.content_changed`
   / `source_changed` now aggregate into arm records
   (`shuffle_*_count`) and arm summaries (`shuffle_*_rate`) on **new** runs.
   Frozen `results_v5.json` is untouched and lacks these fields.
3. **Vacuous shuffled-channel assay:**
   `assay_failed_shuffled_channel_silent` previously keyed only on attempt
   `adoption_mean`. Wave 1d″ tightens **new** runs to require
   `adoption_accepted_mean > near-zero` **or**
   `shuffle_content_changed_rate > 0`. Legacy summaries without those fields
   keep the attempts fallback so frozen v5 JSON tests stay green.
4. **Dose honesty:** new-run `dose_trend.pattern` display label is
   `peak_at_intermediate_dose_then_channel_closure` (plus `pattern_label_note`; `independent: false`). Amd 01 frozen text is
   **not** rewritten. `dose(1.5)` digests equal treatment; `dose(4.0)` is
   outside support (sd=0, equals `capsules_off`). Statistic
   `S = 47.174… = 16.488… + 30.685…` is the algebraic sum of two primary
   contrasts → **zero independent information**, and dose is outside
   `metric_count=3`. Cite **Hothorn 2020**; **Simpson & Margolin 1986**.
5. **Tests:** soft `if assay_failed: assert …` dodge replaced with
   `pytest.xfail` (strict expected-failure path) for the Amd 02 smoke
   positive-control clause; unit tests cover single-capsule identity and
   multiset preservation under peer rotation.

### Stats notes (disclosure only)

- `capsules_off` sd=0 → contrasts vs it behave like one-sample
  (`sd_delta` = sd of the other arm).
- Positive control saturated: Z′ vs off is high, but vs `source_bias_off`
  is not (Assay Guidance Manual warning).
- Permutation p-values sit at the floor `(k+1)/(B+1)` with B=20000 — form
  correct; disclose “floor.”
- Throughput not matched across arms → activity-matched arm needed (Wave 1e).
- Clean unused content contrast: `oracle` vs `source_bias_off` same
  throughput, large Δ.

---

## What v5 / Wave 1d″ may and may not claim

**May:**

- Report v5 as a reproducible research campaign with realized manipulation
  checks (as recorded), decision-rule FAIL on
  `shuffled_better_than_capsules_off`, ClaimGate **`runtime_observation`**.
- State the shuffle-control marginal-preservation caveat and the surplus
  split above as **interpretation / limitation**, not as a new confirmatory
  finding.
- Ship additive instrumentation and docs for future campaigns.

**May not:**

- Raise the ladder / invent `intervention_supported`.
- Claim the negative control “proved content does not matter” or that the
  mechanism “failed” solely from `shuffled > off`.
- Treat dose trend as an independent fourth primary metric.
- Treat `capsule_adoptions ≈ 542` as successful accept evidence.
- Rewrite Amd 01/03 frozen text or overwrite `results_v5.json`.

---

## Wave 1e stub (deferred — Amendment 04)

Not implemented in Wave 1d″. Design pointer only:

| Future arm | Intent |
|---|---|
| `capsules_content_null` | True content null that does **not** preserve the profitable payload marginal (e.g. replace patterns with non-informative / matched-null tokens). |
| `capsules_activity_matched` | Match channel activity / throughput to treatment so contrasts are not confounded by adoption volume. |
| Oracle ladder (optional) | Use `oracle` vs `source_bias_off` (matched throughput) as a clean content contrast. |

Formal prereg changes belong in **Amendment 04**; then re-campaign under that
amendment. E6 Morris / HE02 / HE03 stay on the later track after 1e.

---

## Files / instrumentation summary

- `handoff/WAVE_1D_PRIME_REVIEW.md` — review commit-in.
- This doc — honesty narrative.
- `hard_experiment_01.py` — additive fields, tighter assay when fields exist,
  dose display label + note, limitations strings.
- Tests — xfail path; shuffle unit tests; counts split.
- `docs/HARD_EXPERIMENT_01.md` / `CLAIMS.md` — short honesty paragraphs only.

---

## Follow-on audit closure (Wave 1d′ review blockers)

- Dose: `independent: false`; out of decision rule; `metric_count = len(PRIMARY_CONTRASTS)`.
- B6: smoke edge-level asserts split from positive-control mean move (no permissive `if assay_failed`).
- P1 pilots committed: `pilot_v5.json`, `pilot_v6.json`.
- P3: [`AMD03_CODE_DEVIATIONS.md`](AMD03_CODE_DEVIATIONS.md) (Willroth rows; Amd 03 bytes frozen).
- P5: `_calibration_food_cells` no longer takes a dead `seed` parameter.
- CONTENT_NULL remains confirmatory null; peer-rotation stays sensitivity (known non-derangement when payloads collide / window size 1).
