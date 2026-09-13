# WAVE_1D_PRIME_REVIEW.md

> **SHA incomplete until part03 arrives.** This file embeds the partial
> Wave 1d′ scientific review (`01_WAVE_1D_PRIME_REVIEW_PARTIAL.md` from the
> handoff pack). Hex part03 of the full review was missing at capture time;
> do not treat any single commit SHA below as the complete review artifact
> until part03 is merged into this file.
>
> Reviewed branch tip at implementation close: `wave-1d-seed-variance`
> (see git log). ClaimGate ceiling remains **`runtime_observation`**.

---

## Embedded partial review (missing hex part03)

# Wave 1d′ review — `wave-1d-seed-variance` @ `654a75e`

> برای ایجنت پیاده‌ساز. متن انگلیسی است تا نقل‌قول‌ها و شناسه‌ها دقیق بمانند.
> خلاصهٔ فارسی: ادعای «Wave 1d′ از نظر علمی بسته است» را نمی‌توان پذیرفت.
> کنترل منفی *مشخصاً بد تعریف شده* (نه اینکه مکانیزم شکست خورده باشه)،
> تست dose هیچ اطلاع مستقلی ندارد، شمارندهٔ `capsule_adoptions` چیزی را
> که اسمش می‌گوید نمی‌شمارد، و دو assert سختِ تست حذف شده‌اند.

Reviewed artifacts: `docs/hard_experiment_01/results_v5.json` (5538 lines),
`docs/HARD_EXPERIMENT_01_PREREG_AMENDMENT_02.md`,
`docs/HARD_EXPERIMENT_01_PREREG_AMENDMENT_03.md`,
`src/codontrace/genesis/hard_experiment_01.py` (+136/−31),
`src/codontrace/genesis/capsule.py` (shuffle + adoption paths),
`src/codontrace/genesis/organism.py` (action-bias substitution),
`tests/test_hard_experiment_01.py` (+168).

Verdict: the run is **honestly reported and reproducible**, and several things are
genuinely well done (see §6). It is **not** at 10/10, and the headline conclusion
in the status note is wrong in an important way: `shuffled_better_than_capsules_off`
is not evidence that the mechanism failed — it is evidence that the negative
control is mis-specified. Fixing the control is a design change, not a spin change,
and it must go through a new hashed amendment.

Nothing below asks you to loosen ClaimGate. The ceiling stays `runtime_observation`
until the redesigned controls run.

---

## 1. Blockers

### B1 — `capsule_adoptions` counts attempts, not adoptions; the "channel is alive" gate is vacuous

`_capsule_counts` returns `len(result.capsule_adoption_records)`:

```python
adoptions = len(tuple(getattr(result, "capsule_adoption_records", ()) or ()))
```

But `_adoption_blocked(...)` in `genesis/capsule.py` appends a record for **every**
blocked attempt, including `SOURCE_FITNESS_BELOW_THRESHOLD` — which is exactly what
`rejected_by_source_fitness` counts off the *same list*. So `capsule_adoptions` is
the number of adoption *attempts*.

Consequences, all visible in the artifact:

* `adoption_mean = 542.5333` is **bit-identical across `source_bias_on`,
  `source_bias_off`, `capsules_shuffled`, `oracle_capsule`** and rises 494→585 in
  steps of 13 per seed. That is a read/attempt schedule, not an adoption signal.
* The assay gate

  ```python
  adoptions_shuffled = _num("capsules_shuffled", "adoption_mean")
  if adoptions_shuffled is None or adoptions_shuffled <= ASSAY_ADOPTIONS_NEAR_ZERO:
      failures.append("assay_failed_shuffled_channel_silent")
  ```

  would pass even if **zero** capsules were ever successfully adopted in that arm.
  `ASSAY_ADOPTIONS_NEAR_ZERO = 1e-12` against a count of attempts is not a
  manipulation check.
* `assay_failed_capsules_off_channel_active` is fine only because with the channel
  off there are no attempts either.
* Nowhere in `results_v5.json` is the number of **successful** adoptions reported.
  So edge `e1`'s effect on *which capsule is adopted* — the middle node of the
  preregistered DAG — is unobservable in the published artifact.

Fix (do this first; it is cheap and it changes what the other findings mean):

```python
def _capsule_counts(result: object) -> CapsuleCounts:
    records = tuple(getattr(result, "capsule_adoption_records", ()) or ())
    blocked = tuple(r for r in records if getattr(r, "blocked_reason", None))
    return CapsuleCounts(
        sources=...,
        utilities=...,
        transfers=...,
        adoption_attempts=len(records),
        adoptions_succeeded=len(records) - len(blocked),
        blocked_by_reason=Counter(str(r.blocked_reason) for r in blocked),
    )
```

Then: rename the JSON field (`capsule_adoption_attempts`), add
`capsule_adoptions_succeeded` and `capsule_adoption_blocked_by_reason`, point the
shuffled-channel gate at `adoptions_succeeded`, and add an invariant test
`attempts == succeeded + sum(blocked_by_reason.values())`.

### B2 — the CONTENT scramble is a cyclic rotation and can be a no-op; nothing proves it ever fired

`_shuffle_capsules_for_control` sorts by digest and pairs each capsule with its
successor:

```python
ordered = tuple(sorted(capsules, key=lambda capsule: capsule.digest()))
for index, capsule in enumerate(ordered):
    control_peer = ordered[(index + 1) % len(ordered)]
```

Two structural problems:

1. **Window of size 1 ⇒ identity.** `ordered[(0 + 1) % 1] == ordered[0]`, so the
   capsule is scrambled against itself and `content_changed` is `False`. In that
   tick `capsules_shuffled` is behaviourally identical to `source_bias_on`.
2. **Duplicate content ⇒ no-op.** Two good emitters in the same window rotate
   into each other with identical `event_pattern` / `predicted_outcome`.

`CapsuleShuffleRecord` already records `source_changed`, `content_changed`,
`claim_eligible` — and **none of it is aggregated into the artifact**. Grepping the
whole 5538-line results file for `shuffl`/`eligib`/`content` returns only arm names
and contrast names. So the claim "content was scrambled" is currently unverified
evidence.

Fix: aggregate per seed `shuffle_records_total`, `shuffle_content_changed`,
`shuffle_claim_eligible`, `shuffle_window_size_histogram`; add assay failures
`assay_failed_shuffle_never_changed_content` and
`assay_failed_shuffle_content_change_rate_below_threshold` (require ≥ 0.99).
Separately, make the rotation a real derangement: draw a random derangement from
`RNGManager(namespace="capsule/shuffle")` and, when the window has < 2 *distinct*
payloads, pull the replacement payload from a preregistered null pool instead of a
peer. Keep it deterministic; a derangement is as deterministic as a rotation.

### B3 — the negative control is mis-specified, so `shuffled_better_than_capsules_off` is a design artifact

A rotation is a permutation, so it **preserves the payload marginal exactly**. The
receiver pool is 8 receivers against 8 emitters split good/poor, so ~50 % of
payloads in the pool are `EAT_LUMEN`. The artifact confirms it:

| arm | `bias_payload_totals` | useful (`EAT_LUMEN`) % | `bias_applied_mean` | `rejected_by_source_fitness_mean` |
|---|---|---|---|---|
| `source_bias_on` | `{EAT_LUMEN: 7611}` | **100.00** | 253.70 | 290.77 |
| `source_bias_off` | `{EAT_LUMEN: 5208, SENSE_DANGER: 7156}` | 42.12 | 412.13 | 0.00 |
| `capsules_shuffled` | `{EAT_LUMEN: 4964, SENSE_DANGER: 6121}` | 44.78 | 369.50 | 266.87 |
| `oracle_capsule` | `{EAT_LUMEN: 12364}` | 100.00 | 412.13 | 0.00 |

`capsules_shuffled` still delivers ~45 % useful payloads, and `EAT_LUMEN` is
net-positive by construction (the calibration comment at
`hard_experiment_01.py:125` says so). Therefore `E[shuffled] > E[capsules_off]`
is **true by construction**, for any seed count, at any α. The decision rule

```python
elif shuffled_vs_off.ci_low > 0.0:
    failures.append("shuffled_better_than_capsules_off")
```

is a rule that the design can never satisfy. The measured Δ = 14.3142,
CI [11.4855, 17.6946], dz 1.6424 is the value of *having a channel with a
50/50 payload pool*, which is a real quantity — just not "no information".

Quantitatively, of the total `source_bias_on − capsules_off` gain of 30.6854 ATP,
**46.65 % (14.3142) is reproduced by content-scrambled capsules** and 53.35 %
(16.4888) is attributable to the gate. That decomposition is the honest headline,
and it is a much stronger result than "the scrambled arm is still a problem".

This is the same distinction the playback-experiment literature makes: a control
must preserve the *physical* properties of the stimulus while destroying the
*information*. Reversing or reordering a signal is not automatically an
information-free control (Kroodsma 1989; Kroodsma 1990; McGregor 1992; and for a
clean modern example of controls built to hold acoustics fixed while breaking
"information coherence", Comms Biol 2025, s42003-025-08170-0).

Fix — replace the arm and the rule:

* New arm `capsules_content_null`: every payload is replaced by a **cost-matched
  useless action**, so throughput and ATP cost are held fixed and only usefulness
  is removed. `SENSE_DANGER` (0.4) is *not* cost-matched to `EAT_LUMEN` (0.8);
  either add a preregistered `NULL_ACT` codon with cost 0.8 and no resource
  benefit, or state the cost gap in the amendment and report it as a limitation.
* Keep `capsules_shuffled` but rename its role from "negative control" to
  **"source–payload association ablation"** (it breaks the pairing between source
  quality and payload usefulness while holding the marginal fixed). That is
  scientifically the most interesting arm you have; it just is not a null.
* Replace `shuffled_better_than_capsules_off` with
  `content_null_better_than_capsules_off` as the falsifier, and promote
  `source_bias_on − capsules_shuffled` (Δ 16.3713, dz 1.3226, CI [12.3604,
  21.1038]) to a primary information-transfer contrast, which it effectively
  already is.

### B4 — the dose test carries zero independent information and is an uncounted fourth test

Verified numerically against the artifact:

* `dose(1.5)` is **spec-digest-identical** to `source_bias_on` on 30/30 seeds.
* `dose(0.0)` equals `source_bias_off` in value on 30/30 seeds.
* `dose(4.0)` equals `capsules_off` in value on 30/30 seeds.
* `_dose_pattern_statistic` is `sum(peak − other)`, so
  `S = (on − off) + (on − capsules_off) = 16.48875 + 30.6854167 = 47.1741667`,
  which is exactly the reported `pattern_statistic` 47.1741666667.

So the dose trend is an **algebraic function of the two primary contrasts**. Its
`permutation_p = 9.999e-05` is not new evidence, and yet
`MultipleComparisonAudit(metric_count=3)` does not count it, nor
`shuffled_vs_capsules_off`, nor the legacy secondary. The real family is ≥ 5.

Fix: either drop the dose block, or keep it as *descriptive* with
`independent: false`, exclude it from the decision rule, and add a guard test:

```python
assert abs(trend.pattern_statistic - (c_off.mean_delta + c_none.mean_delta)) < 1e-9
```

and set `metric_count` from the actual list of inferential comparisons rather than
a literal. If you want a genuinely independent dose test, sample dose levels that
are **not** existing arms, on a separate seed block.

### B5 — the top dose is outside the support of `source_fitness`, and `"step_up_then_saturate"` mislabels a downturn

`dose(4.0)` gives mean 28.0000 with **sd exactly 0** and one unique value across
all 30 seeds — identical to `capsules_off`. That is total gate closure, i.e. the
channel is off, not "saturated". The observed pattern is 42.20 → 58.69 → 28.00:
an **umbrella / downturn**, not monotone.

`_analyze_dose_trend` computes an umbrella statistic (peak at
`DOSE_PEAK_INDEX = 1`) and then reports `pattern: "step_up_then_saturate"` and
`trend_supported: true`. The statistic is right for an umbrella; the label and the
word "trend" are not. In the dose–response literature a downturn at the top dose
is explicitly *not* a monotone trend, and the accepted remedies are an
intersection–union combination of a trend test with a control-vs-high-dose test,
or a maxT over candidate maximum doses ignoring the higher ones (Hothorn 2020,
arXiv:2007.09631, §on downturns; Simpson & Margolin 1986 Biometrika 73:589;
Williams 1971 Biometrics 27:103).

Fix: rename to `pattern: "peak_at_intermediate_dose_then_channel_closure"`, drop
`trend_supported` or gate it on a monotone alternative only, and pick the dose grid
**inside the empirical support**. Concretely: report the realized distribution of
`CausalCapsule.source_fitness` (min/median/max per arm) in the artifact and choose
levels as quantiles of it. Right now nothing in the artifact tells a reader why
4.0 closes the gate completely.

### B6 — two hard assertions were deleted from the manipulation-check test

In `tests/test_hard_experiment_01.py::test_wave_1c_manipulation_check_passes_at_smoke_scale`:

```diff
-    assert campaign.assay_failed is False, campaign.assay_failures
-    assert by_arm["oracle_capsule"].mean > by_arm["capsules_off"].mean
+    if campaign.assay_failed:
+        assert campaign.assay_failures == ("assay_failed_positive_control_did_not_move_outcome",)
```

A conditional that only checks the failure *tuple* when a failure occurs is a test
that cannot fail for the reason it was written. If smoke scale genuinely cannot
move the positive control, encode that as an expectation, not as permissiveness:

```python
@pytest.mark.xfail(
    reason="Amd 03 §2: at smoke scale (12 ticks) the oracle arm cannot outrun "
           "basal drain; research scale is the assay of record.",
    strict=True,
)
def test_smoke_scale_positive_control_moves_outcome() -> None:
    ...
    assert by_arm["oracle_capsule"].mean > by_arm["capsules_off"].mean
```

`strict=True` meaVE_1D_PILOT_DIAGNOSIS.md` / `WAVE_1D_PILOT_REPORT.md` — which are
  **workspace files, not committed**. There is no `pilot_v5.json` in the repo. As
  it stands, the audit trail asserts a gate that a third party cannot verify.
  Commit `docs/hard_experiment_01/pilot_v5.json` and add a test that every path
  referenced in an amendment's reference list exists in the tree.
* **P2 — the pilot gate was relaxed after seeing the failure.** Amd 02 §3 required
  sd > 0 in all four `ANALYSIS_ARMS`; Amd 03 §2 relaxes it to on/off/shuffled with
  `capsules_off` sd = 0 expected. The reasoning is correct and §1 documents it
  transparently — this is good practice, not misconduct. But it is a post-hoc gate
  change and belongs in the Willroth & Atherton deviation table as one, with the
  timestamp/digest of the pilot that motivated it.
* **P3 — two code deviations are absent from the deviation table.** In
  `_apply_survival_calibration`:

  ```python
  # v3 was: population_size = int(spec.population_max or len(spec.genome_bits))
  population_size = len(spec.genome_bits)
  ...
  # v3 was: max_resources=len(food_cells)
  max_resources=lattice_cells,
  ```

  Both change the realized environment. Quantify each (does `population_max`
  differ from `len(genome_bits)` in this overlay? by how much does
  `max_resources` change?) and add rows to the Amd 03 table.
* **P4 — docs drift.** `docs/HARD_EXPERIMENT_01.md` and `CLAIMS.md` §4.4 still
  describe v3. The doc test still only asserts `"Results (research v3)"`. Add a
  `Results (research v5)` section and extend the doc test to require a section per
  committed results schema version, derived from the files on disk.
* **P5 — dead parameter.** `_calibration_food_cells(..., seed: int = 0)` with
  `del seed` and a docstring saying it is ignored. It is a private function; there
  is no API to stabilize. Delete the parameter and its two call sites.

---

## 4. Coding-method guidance

These are the patterns behind the findings above, in the order I would adopt them.

1. **Never name a counter after the thing you wish it counted.** B1 is a naming
   bug that silently invalidated a manipulation check. Rule: if a count is derived
   from a record list that includes failures, the name must say so
   (`*_attempts`), and the success count must be a separate field. Add the
   invariant as a test, not a comment.
2. **Assay gates must read the telemetry of the manipulated quantity, never a
   proxy.** "Did the scramble scramble?" must be answered by
   `CapsuleShuffleRecord.content_changed`, not inferred from adoption counts. If a
   record type exists and is not aggregated into the artifact, that is a bug.
3. **Derived statistics must declare their dependence.** Anything that is an
   algebraic function of other reported numbers gets `independent: false` plus an
   assertion tying it to its parents (B4). This is the cheapest possible guard
   against accidentally double-counting evidence.
4. **Alias, don't re-run, when two configurations are the same spec.** `dose(1.5)`
   and `source_bias_on` are spec-digest-identical on 30/30 seeds. Make that an
   explicit alias with a `assert spec_a.digest() == spec_b.digest()` test, so a
   future edit that accidentally decouples them fails loudly instead of quietly
   producing a fourth test.
5. **Guard degenerate statistics at the boundary.** Effect-size and CI helpers
   should return a typed `undefined_zero_variance` / `undefined_constant_baseline`
   sentinel rather than a finite number when `sd == 0`. Right now a reader sees
   `dz 1.6424` for a contrast whose `sd_delta` is literally the treatment arm's own
   sd (M1).
6. **A test may never be weakened to make a run green.** Use
   `pytest.mark.xfail(strict=True, reason=<amendment §>)`, or parametrize by scale
   and assert the strong property at the scale where it must hold (B6). A strict
   xfail is self-cleaning; a permissive `if` is permanent.
7. **Generate the deviation table from the code.** You already have
   `hard_experiment_01_calibration_knobs()` returning a dict per wave. Diff
   consecutive schema versions programmatically and emit the deviation rows; then
   P3 cannot happen. Hand-maintained tables drift from the code they describe.
8. **Property tests for every randomization helper.**
   `test_wave_1d_seed_permuted_roles_preserve_multiset` is exactly right — do the
   same for the shuffle: for any window with ≥ 2 distinct payloads, every capsule's
   content must change (derangement property), and for a window of size 1 the
   implementation must take the null-pool branch rather than self-pairing.
9. **Amendment references are build artifacts.** Add a test that walks every
   `docs/HARD_EXPERIMENT_01_PREREG_AMENDMENT_*.md` reference list and asserts each
   repo-relative path exists and, where a digest is claimed, matches. P1 becomes
   impossible.
10. **Keep the seed as a first-class, recorded parameter of the experiment
    description, not a loop variable.** You already do this well; it is the
    direction SED-ML L1V5 moved for the same reason (global
    `AlgorithmParameter` KISAO:0000488), and it is what makes your
    `paired_seed_digest` auditable. Worth stating in `REPRODUCIBILITY.md` as an
    explicit design principle so it survives refactors.

---

## 5. Suggested Wave 1e design (one amendment, one campaign)

Arms:

| arm | purpose | throughput | payload usefulness |
|---|---|---|---|
| `capsules_off` | channel absent | 0 | — |
| `source_bias_on` | treatment | gated | 100 % |
| `source_bias_off` | gate ablation | ungated | pool marginal (~42 %) |
| `capsules_content_null` | **true null**: cost-matched useless payloads | matched to `source_bias_on` | 0 % |
| `capsules_activity_matched` | escape-from-WAIT control (yoked to `source_bias_on`) | matched exactly | independent of capsule |
| `capsules_shuffled` | source↔payload association ablation (keep, re-label) | ungated-ish | pool marginal |
| `oracle_moderate` (f ∈ {0.25, 0.5, 1.0}) | assay sensitivity ladder | ungated | f |

Primary contrasts (preregister exactly three, Holm over three):

1. `source_bias_on − capsules_content_null` → information transfer.
2. `source_bias_on − capsules_activity_matched` → specificity beyond "acting".
3. `source_bias_on − source_bias_off` → the gate (edge `e1`).

Secondary (declared, not gated): `oracle_capsule − source_bias_off` at matched
throughput; `capsules_shuffled − capsules_content_null` as the value of the payload
marginal; the oracle sensitivity ladder; Z′ per control pair.

Falsifier: `capsules_content_null` must not beat `capsules_off`.

Dose: levels drawn as quantiles of the realized `source_fitness` distribution,
reported in the artifact, none of which coincides with an existing arm, on a
separate seed block. Analyze as an umbrella/protected-trend alternative with an
explicit control-vs-top-dose component (Hothorn 2020), or drop it.

Even if all three primaries pass, the honest ceiling is still
`mechanism_support` at best for a hand-built calibration overlay with fixed
genomes and no evolution. Nothing here licenses `collective_intelligence` or any
other forbidden alias.

---

## 6. What is already good (keep it)

* Reproducibility discipline is genuinely strong: `replay_matched: true`, per-seed
  `spec_digest` and `result_digest`, hashed prereg + three hashed amendments,
  `claim_gate_decision_digest`, pilot seeds (1000–1009) held disjoint from analysis
  seeds (11–40). This is better than most published ALife work.
* `assay_failed` / `assay_failures` as a first-class gate that runs *before* the
  p-values, in the spirit of do-operator manipulation checks. The existing gate set
  (`assay_failed_treatment_bias_never_applied`,
  `assay_failed_source_gate_never_rejected`,
  `assay_failed_treatment_adopted_poor_payload`,
  `assay_failed_gate_off_never_adopted_poor_payload`,
  `assay_failed_capsules_off_channel_active`,
  `assay_failed_positive_control_did_not_move_outcome`,
  `assay_failed_arms_bitwise_identical`) is thoughtful. Extend
  `assay_failed_arms_bitwise_identical` to all arm pairs, not just on-vs-off.
* Amd 03 §1 documents the Amd 02 pilot failure and the structural reason for
  `capsules_off` sd = 0 instead of burying it. That is exactly right.
* `(k + 1)/(B + 1)` p-values, BCa bootstrap, Holm, `claim_downgraded` on CIs
  containing 0, and a decision rule that **reported its own failure** rather than
  relaxing to fit. The ceiling stayed at `runtime_observation`.
* `_capsule_counts`'s docstring refusing to `max()` across surfaces, and
  `_result_identity_digest`'s explicit note about why the snapshot digest is used.
  Reasoning-in-place about evidence integrity is the right habit.
* `test_wave_1d_seed_permuted_roles_preserve_multiset` — a real invariant test on a
  randomization helper.

---

## 7. References used

* Phipson, B. & Smyth, G. K. (2010). Permutation p-values should never be zero.
  *Stat Appl Genet Mol Biol* 9(1):39.
* Ruxton, G. D. & Neuhäuser, M. (2013). Improving the reporting of P-values
  generated by randomization methods. *Methods Ecol Evol* 4:114.
  doi:10.1111/2041-210X.12102
* Hothorn, L. A. (2020). Claiming trend in toxicological and pharmacological
  dose-response studies. arXiv:2007.09631.
* Simpson, D. G. & Margolin, B. H. (1986). Recursive nonparametric testing for
  dose–response relationships subject to downturns at high doses.
  *Biometrika* 73:589.
* Williams, D. A. (1971). A test for differences between treatment means when
  several dose levels are compared with a zero dose control. *Biometrics* 27:103.
* NCBI *Assay Guidance Manual* — Advanced Assay Development Guidelines for
  Image-Based High Content Screening (positive-control selection; Z′ caveats).
  NBK126174.
* Zhang, J.-H., Chung, T. D. Y. & Oldenburg, K. R. (1999). A simple statistical
  parameter for use in evaluation of HTS assays. *J Biomol Screen* 4:67.
  IUPAC Gold Book 14204 (Z′ factor).
* Church, R. M. (1964). Systematic effect of random error in the yoked control
  design. *Psychol Bull* 61:122. (And the reprint discussion, "The Yoked Control
  Design", doi:10.4324/9781315808154-23.)
* "Control Freaks: Towards Optimal Selection of Control Conditions for fMRI
  Neurofeedback Studies", PMC6338498 (sham/yoked control trade-offs).
* Kroodsma, D. E. (1989). Suggested experimental designs for song playbacks.
  *Anim Behav* 37:600. Kroodsma (1990), Design of song playback experiments,
  *Auk*. McGregor (1992) on pseudoreplication.
* *Commun Biol* (2025) s42003-025-08170-0 — controls that hold physical stimulus
  properties fixed while violating information coherence.
* Goldsby, H. J., Knoester, D. B., Ofria, C. & Kerr, B. (2014). *PLoS Biol*
  12(3):e1001858 (coordination instructions); Goldsby et al. (2012) *PNAS*
  109:13686 (knockout controls in digital evolution).
* Morris, M. D. (1991). *Technometrics* 33:161; Campolongo, Cariboni & Saltelli
  (2007) *Environ Model Softw* 22:1509 (μ*); Thiele, Kurth & Grimm (2014) *JASSS*
  17(3):11 — for E6.
* Grimm, V. et al. (2020). The ODD protocol for describing agent-based models:
  a second update. *JASSS* 23(2):7 (+ "Describing simulation experiments"
  supplement); Railsback & Grimm, TRACE.
* Lakens, D. (2013). Calculating and reporting effect sizes. *Front Psychol* 4:863
  (dz vs d_av).
* Gelman, A. & Loken, E. (2013). The garden of forking paths.
* Willroth, E. C. & Atherton, O. E. (2024). Best practices for reporting
  deviations from preregistration.
* Waltemath, D. et al. (2011). SED-ML; and SED-ML L1V5 (2024),
  doi:10.1515/jib-2024-0008 — seed as a first-class experiment parameter.
* Lalejini, A. et al. — ALife Data Standards.

---

## 8. Ordered queue (revised)

The existing queue is fine; this only inserts work before E6.

1. **Merge/home** — unchanged. Land Wave 1c first (`#26` is incomplete: its
   `capsule.py` is truncated at 8713 of 72172 bytes; use `git am` from the Drive
   hex patch), close `#25` with one line, fix the `#26` WIP title.
2. **1d″ hotfix, no new claim** — B1 (adoption attempts vs successes), B2
   (shuffle telemetry + derangement), B6 (restore assertions as strict xfail),
   B4/B5 (demote the dose block, fix the label), M6 (`metric_count` derived),
   P1/P3/P4/P5 (pilot artifact, deviation rows, docs, dead param). All of this is
   audit-integrity work on the existing evidence — the ceiling stays
   `runtime_observation` and no arm changes.
3. **Amendment 04 + Wave 1e** — the redesigned control set in §5. This is where
   the scrambled-arm problem actually gets resolved.
4. **E6** — Morris screening + ODD, as planned (μ* for ranking, σ for
   interactions, r ≈ 10–20 trajectories, `r(k+1)` runs; ODD per Grimm 2020 and the
   JASSS "Describing simulation experiments" supplement). Sensitivity and
   documentation only, no new claim — agreed.
5. **HE02** (E1+E2+E5), **HE03** (E3), **E4/E7** conditional, then the Wave 3
   claim ladder — unchanged.


---

## Prior capture note (workspace)

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
