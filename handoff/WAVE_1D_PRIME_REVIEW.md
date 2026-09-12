# WAVE_1D_PRIME_REVIEW.md (captured from user chat 2026-09-12)

Source note: user reported push to main as `74197d0` with path `handoff/WAVE_1D_PRIME_REVIEW.md`.
That commit was **not** visible on `origin/main` (still `49b9f2c`) from this agent at capture time.
Substance below is the user's paste / review summary.

## Overall
"Wave 1d′ scientifically closed" is **incorrect**. Work is honest and reproducible, but not 10/10.

## Primary finding — negative control mis-specified (not mechanism failure)
`_shuffle_capsules_for_control` is a **cyclic rotation** of capsules in the same window; rotation **preserves the content marginal**. So `capsules_shuffled` still delivers ~44.78% `EAT_LUMEN`, and `EAT_LUMEN` is profitable by calibration — therefore `shuffled > capsules_off` is **by construction** and never fails the non-superiority gate.

Honest decomposition of total ~30.69 ATP surplus:
- 46.65% (~14.31) from "channel present with 50/50 pool"
- 53.35% (~16.49) from the gate
That sentence is stronger than "scrambled still a problem."

## Five further blockers
1. `capsule_adoptions` counts *attempts* not successful accepts (blocked records included) → ~542.53 identical on all four arms; `assay_failed_shuffled_channel_silent` is vacuous (passes even with zero successful accepts).
2. Window size 1 makes rotation identity; `CapsuleShuffleRecord.content_changed` never aggregated in artifact → no evidence "content was scrambled."
3. Dose test is algebraic sum of two primary contrasts: 47.1741667 = 16.48875 + 30.6854167; `dose(1.5)` same digest as `source_bias_on` on 30/30 seeds → zero independent information; not in `metric_count=3`.
4. `dose(4.0)` outside support (sd=0, equals capsules_off) → `step_up_then_saturate` mislabeled; downturn not trend (Hothorn 2020; Simpson & Margolin 1986).
5. Two hard asserts removed from manipulation-check tests; correct path is `xfail(strict=True)` not `if`.

## Stats notes
- `capsules_off` sd=0 makes contrasts vs it one-sample (`sd_delta` = sd of other arm).
- Positive control saturated: Z′ vs off ≈ 0.985 but vs `source_bias_off` ≈ −0.28 (Assay Guidance Manual warning).
- All p at permutation floor (k+1)/(B+1) with B=20000 — form correct, must disclose "floor."
- Throughput not matched across arms (253.7 vs 369.5) → need activity-matched arm.
- Cleanest unused content contrast: `oracle` vs `source_bias_off` same throughput (412.13), Δ=36.20.

## Recommended coding fixes + Wave 1e design
(See full review for 10 method recommendations; arms `capsules_content_null`, `capsules_activity_matched`, oracle ladder.)

## Revised queue
1. Merge / home
2. Wave **1d″** — evidence honesty only (no new claim)
3. Amendment 04 + Wave **1e** (proper null / activity-matched controls)
4. Then E6 → HE02 → HE03 (E6 already partially landed on branch)
