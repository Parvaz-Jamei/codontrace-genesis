# Wave 1e — Science brief (HE01 Amendment 04: proper negative controls)

**Dated:** 2026-09-12  
**Product:** CodonTrace Genesis (`codontrace`), identity `0.3.0b4.dev0`  
**Repo:** `/workspace/codontrace-genesis` branch `wave-1d-seed-variance` @ `a5acb8b`  
**Status:** research brief only. **No production code, no PR, no Cloud Agent, no Drive.**  
**ClaimGate ceiling:** stays **`runtime_observation`**. Wave 1e / Amd 04 does **not** auto-grant `intervention_supported`.

**Upstream honesty:** Wave 1d″ documented that cyclic peer-rotation shuffle **preserves the payload marginal** → `shuffled > capsules_off` is **by construction**; `capsule_adoptions` = attempts; dose S algebraic; dose(4) downturn. Sources: `handoff/WAVE_1D_PRIME_REVIEW.md`, `docs/hard_experiment_01/WAVE_1D_DOUBLE_PRIME_HONESTY.md`. HE01 v5: assay valid; decision FAIL `shuffled_better_than_capsules_off`; ClaimGate `runtime_observation`.

**One-sentence purpose:** replace the broken content-scramble negative control with lit-backed **content-null** and **activity-matched** arms (and optionally an oracle ladder contrast), under a hashed Amendment 04, without raising ClaimGate.

---

## 0. Locked scope

| In scope | Out of scope |
|---|---|
| Literature + locked arm definitions for Amd 04 | Raising ClaimGate / inventing `intervention_supported` |
| Pilot/analysis seed split for 1e | Full research campaign before Amd 04 is written + hashed |
| Coding checklist (doc → code → pilot) | Production code **in this brief task** |
| Denylist + frozen Amd 01/03 clauses | Rewriting Amd 01 / 02 / 03 / original prereg bytes |
| Cite-only extension of arms proposed in 1d′ review | Inventing arms beyond review **without** a citation |

**Do not invent beyond review without citing lit.** Proposed arms already named in Wave 1d′ review / 1d″ honesty stub: `capsules_content_null`, `capsules_activity_matched`, oracle ladder.

---

## 1. Top citations (DOI)

### 1.1 Negative controls for messaging / content (ALife)

1. **Goldsby, H. J., Dornhaus, A., Kerr, B., & Ofria, C. (2012).** Task-switching costs promote the evolution of division of labor and shifts in individuality. *Proceedings of the National Academy of Sciences, 109*(34), 13686–13691.  
   https://doi.org/10.1073/pnas.1202233109  
   *Messaging / location knockout via neutral `nop-X` replacement — **isolation** of communication mechanism, not content-preserving rotation. HE01 prereg already invoked “Goldsby-style isolation”; peer-rotation failed that intent.*

2. **Goldsby, H. J., Knoester, D. B., Ofria, C., & Kerr, B. (2014).** The effect of conflicting pressures on the evolution of division of labor. *PLOS ONE, 9*(8), e102713.  
   https://doi.org/10.1371/journal.pone.0102713  
   *Knockouts of `retrieve-msg`, location, epigenetic instructions separately — true **capability nulls**, not multiset-preserving swaps.*

3. **Ofria, C., & Wilke, C. O. (2004).** Avida: A software platform for research in computational evolutionary biology. *Artificial Life, 10*(2), 191–229.  
   https://doi.org/10.1162/106454604773563612  
   *Platform baseline for digital-organism messaging controls.*

### 1.2 Activity-matched / yoked / placebo messaging

4. **Boot, W. R., Simons, D. J., Stothart, C., & Stutts, C. (2013).** The pervasive problem with placebos in psychology: Why active control groups are not sufficient to rule out placebo effects. *Perspectives on Psychological Science, 8*(4), 445–454.  
   https://doi.org/10.1177/1745691613491271  
   *“Active” channel presence ≠ matched expectancy / matched activity; motivates **activity-matched** arm when throughput differs (v5: ~253.7 vs ~369.5).*

5. **Vazquez, C., Blanco, I., Sanchez, A., & McNally, R. J. (2016).** Attentional bias modification in depression … study protocol for a placebo-controlled trial. *BMC Psychiatry, 16*, 376.  
   https://doi.org/10.1186/s12888-016-1150-9  
   *Explicit **yoked-control**: same stimuli / same exposure time, contingency removed — template for `capsules_activity_matched` (match adoption/throughput volume; destroy content contingency).*

### 1.3 Assay Guidance Manual — Z′ / positive-control saturation

6. **Zhang, J.-H., Chung, T. D. Y., & Oldenburg, K. R. (1999).** A simple statistical parameter for use in evaluation and validation of high-throughput screening assays. *Journal of Biomolecular Screening, 4*(2), 67–73.  
   https://doi.org/10.1177/108705719900400206  
   *Z′ definition. v5: Z′ vs `capsules_off` ≈ 0.985 looks “excellent” because off is a basal plateau (sd=0).*

7. **Assay Guidance Manual — Advanced assay development guidelines for image-based HCS (NCBI Bookshelf NBK126174).**  
   https://www.ncbi.nlm.nih.gov/books/NBK126174/  
   *Warning: do **not** pick an excessively strong positive control merely to inflate Z′; moderate / dose-ladder positives needed. Matches review: Z′ vs off high but vs `source_bias_off` ≈ −0.28.*

8. **Assay Guidance Manual — HTS Assay Validation (NBK83783).**  
   https://www.ncbi.nlm.nih.gov/books/NBK83783/  
   *Acceptance Z′ ≥ 0.4 (or SW ≥ 2); still requires realistic hit-strength controls.*

### 1.4 Dose downturn / non-monotone

9. **Simpson, D. G., & Margolin, B. H. (1986).** Recursive nonparametric testing for dose-response relationships subject to downturns at high doses. *Biometrika, 73*(3), 589–596.  
   https://doi.org/10.1093/biomet/73.3.589  
   *Downturn-protected testing; Jonckheere–Terpstra alone is **not** robust to high-dose downturns. Wave 1d″ correctly relabeled dose(4) as downturn, not “saturate.”*

10. **Hothorn, L. A. (2020).** Claiming trend in toxicological and pharmacological dose-response studies: an overview on statistical methods and related R-software. *arXiv:2007.09631*.  
    https://doi.org/10.48550/arxiv.2007.09631 · https://arxiv.org/abs/2007.09631  
    *Trend ≠ monotone if high dose downturns; recommend Williams/Tukey-type max tests, intersection-union with control-vs-high-dose, or downturn-protected procedures — do **not** call dose(4)=off a “saturate” success.*

### 1.5 Preregistering replacement of a broken negative control

11. **Nosek, B. A., Ebersole, C. R., DeHaven, A. C., & Mellor, D. T. (2018).** The preregistration revolution. *PNAS, 115*(11), 2600–2606.  
    https://doi.org/10.1073/pnas.1708274114  
    *Timestamped separation of prediction vs postdiction; transparent amendment, not silent rewrite.*

12. **Willroth, E. C., & Atherton, O. E. (2024).** Best laid plans: A guide to reporting preregistration deviations. *Advances in Methods and Practices in Psychological Science, 7*(1).  
    https://doi.org/10.1177/25152459231213802  
    *OSF time-stamped update **before** new analysis data access; after results known → deviations table, not retro-edit. Amd 04 must include Willroth-style table: broken shuffle → content_null + activity_matched.*

13. **Lakens, D. (2024).** When and how to deviate from a preregistration. *Collabra: Psychology, 10*(1), 117094.  
    https://doi.org/10.1525/collabra.117094  
    *Broken auxiliary hypothesis (shuffle severs content) is a legitimate deviation class; report severity/validity impact; run originally planned contrast as sensitivity where possible.*

14. **DeHaven, A. (2017).** Preregistration: A plan, not a prison. Center for Open Science.  
    https://www.cos.io/blog/preregistration-plan-not-prison  
    *Operational rule already used for Amd 02/03: sibling hashed amendment.*

### Top 5 (minimum set for Amd 04 header)

| # | Cite | Why locked into Amd 04 |
|---|---|---|
| 1 | Goldsby et al. 2012 https://doi.org/10.1073/pnas.1202233109 | Isolation / knockout messaging control ≠ peer rotation |
| 2 | Boot et al. 2013 https://doi.org/10.1177/1745691613491271 | Active channel ≠ matched activity / expectancy |
| 3 | Zhang et al. 1999 https://doi.org/10.1177/108705719900400206 + AGM NBK126174 | Z′ saturation warning vs basal off |
| 4 | Simpson & Margolin 1986 https://doi.org/10.1093/biomet/73.3.589 (+ Hothorn 2020 arXiv:2007.09631) | dose(4) downturn, not saturate |
| 5 | Willroth & Atherton 2024 https://doi.org/10.1177/25152459231213802 (+ Nosek 2018) | How to amend a broken negative control |

---

## 2. Why the current shuffle is broken (locked 1d″ facts — do not re-litigate)

| Fact | Implication for 1e |
|---|---|
| `_shuffle_capsules_for_control` / `apply_capsule_shuffle_control` uses `ordered[(index+1)%n]` peer rotation | **Multiset of payloads preserved** |
| `EAT_LUMEN` still ~44.8% in shuffled when pool is mixed; profitable by calibration | `shuffled > capsules_off` **by construction** |
| Window size 1 → identity (`content_changed=false`) | No evidence content was scrambled |
| Honest surplus split ~46.65% channel-with-50/50 + ~53.35% gate | Stronger than “scramble still a problem” |
| `capsule_adoptions` = attempts (~542.53 identical) | Use `capsule_adoptions_accepted` (1d″ additive) for activity matching |
| Throughput unmatched across arms | Need activity-matched arm |
| Clean unused contrast: `oracle` vs `source_bias_off` same throughput (~412), Δ≈36.20 | Oracle ladder optional, cite-backed |

Original prereg text claimed shuffle “**severs informational content of e2**.” Peer rotation does **not** meet that estimand. Amd 04 replaces the operationalization; it does **not** rewrite the frozen prereg bytes.

---

## 3. Locked arm definitions for Amendment 04

### 3.1 Three-way contrast (do not collapse)

| Arm | Role | What it holds constant | What it destroys / matches | Status |
|---|---|---|---|---|
| `capsules_shuffled` (legacy) | **Broken** historical negative control | Channel on; peer-rotated CONTENT mode | Payload **marginal preserved** | Keep as **sensitivity / archival** only; **not** confirmatory null for Amd 04 decision rule |
| `capsules_content_null` | **Proper content null** | Channel on; emission/read/adoption machinery present; attempt volume in same ballpark as treatment unless noted | **Destroys informative payload marginal** — receivers see non-informative / matched-null tokens (see §3.2) | **New confirmatory negative control** |
| `capsules_activity_matched` | **Yoked / activity-matched** | Matched successful-accept count or throughput to a designated yoked arm (default: `source_bias_on` per seed) | Content contingency removed or fixed-null; volume matched | **New auxiliary control** (Boot/yoked) |

### 3.2 `capsules_content_null` — operational lock (cite Goldsby knockout spirit)

**Intent:** Goldsby/Ofria isolation = remove communicative **information**, not permute who said what among the same messages.

**Allowed implementations (choose ONE in Amd 04 text before code; do not invent a fourth without a cite):**

1. **Fixed null token (preferred default):** replace every capsule’s `event_pattern` / `predicted_outcome` with a single non-profitable null action token that is **not** in the calibrated profitable set (e.g. map all payloads to `WAIT` or a dedicated `NULL_PAYLOAD` that receivers treat as no-op / non-`EAT_LUMEN`). Channel, source ids, timing, and attempt machinery remain.  
   *Lit analog:* knockout → neutral `nop-X` (Goldsby 2012/2014).

2. **Independent draw from a null catalogue:** redraw payload from a **null multiset** whose `EAT_LUMEN` (or profitable-action) rate is **0** (or explicitly calibrated to chance with TOST vs off). Must **not** reuse the empirical treatment multiset.  
   *Lit analog:* placebo / non-contingent signal (Boot 2013; Vazquez yoked).

**Hard requirements (manipulation checks for content_null):**

- `payload_marginal_EAT_LUMEN` (or profitable-action rate) on content_null **≠** treatment multiset rate; target **0** or pre-registered null rate.  
- Aggregate `shuffle_content_changed_rate` (or new `content_null_replaced_rate`) **> 0** when window size ≥ 1.  
- Window size 1 must still null the single capsule (identity forbidden).  
- `adoption_accepted_mean` may be > 0 (channel live) — that is OK; information is null.

**Forbidden as content_null:** cyclic peer rotation, random permutation of the **same** window multiset, SOURCE-only shuffle, RANDOM_METADATA.

### 3.3 `capsules_activity_matched` — operational lock (cite Boot + yoked)

**Intent:** hold **channel activity** (successful accepts and/or receiver throughput) to the yoked treatment seed so “more messages” cannot explain ATP.

**Allowed implementations (choose ONE in Amd 04):**

1. **Yoked accept count:** for each analysis seed \(s\), run or replay with content-null (or fixed-null) payloads but **cap / pad** successful accepts to match `source_bias_on` seed \(s\) `capsule_adoptions_accepted` (1d″ field). Prefer **cap-down** from a richer null stream over inventing fake accepts.  
2. **Yoked throughput:** match receiver action-count / ATP-throughput band to treatment within a pre-registered tolerance (e.g. ±5%), content nullified.

**Hard requirements:**

- Report `activity_match_gap` per seed; pilot gate: mean \|gap\| below pre-registered ε.  
- Content must still be null (activity match **without** content null is **not** a negative control for e2).  
- Do **not** claim activity_matched alone proves content irrelevance.

### 3.4 Oracle ladder (optional, review-backed — not invented)

| Contrast | Why | Confirmatory in Amd 04? |
|---|---|---|
| `oracle_capsule` vs `source_bias_off` | Same throughput (~412), large Δ≈36.20 — clean **content quality** contrast without gate | **Descriptive / secondary** unless Amd 04 explicitly promotes it; does **not** replace content_null |
| Existing `oracle` vs `capsules_off` | Positive-control assay (Amd 01) | **Keep frozen** as assay validity check |

AGM warning: do not treat saturated oracle-vs-off Z′ as sensitivity to realistic hits; report Z′ also vs `source_bias_off`.

### 3.5 Decision-rule impact (Amd 04 must state explicitly)

Amd 01 auxiliary H1 used `capsules_shuffled` non-superiority vs `capsules_off`. Under Amd 04:

- **Confirmatory null arm** for “content does not explain surplus” becomes **`capsules_content_null`** (non-superiority vs `capsules_off`: lower 95% BCa of `content_null − off` ≤ 0).  
- **Legacy shuffled** retained as sensitivity: expect shuffled ≥ off (construction); failure of that non-superiority is **not** mechanism failure.  
- Primary H1 (`on > off` gate contrast) unchanged.  
- Activity-matched enters as **auxiliary** (on > activity_matched on outcome, and/or content_null ≈ activity_matched on volume).  
- Dose: keep Amd 01 pattern text in frozen files; **analysis label** remains `step_up_then_downturn` (1d″); do not claim dose S as independent 4th primary (`metric_count=3`).

**Explicit:** passing Amd 04 pilot/campaign does **not** auto-grant `intervention_supported`. Every Amd 01 decision-rule clause must still hold on a valid research campaign under the **new** null operationalization, and ClaimGate stay at `runtime_observation` until that full conjunction is met and reviewed.

---

## 4. What stays frozen from Amd 01 / 03

| Frozen | Source |
|---|---|
| Estimand: source-bias gate → receiver mean terminal runtime ATP | Amd 01 |
| Primary contrast `source_bias_on` vs `source_bias_off` | Amd 01 |
| Edge map e1–e4; overlay genomes/payloads/threshold 1.5 template | Amd 01 |
| Role multiset Fisher–Yates (`hard_experiment_01/roles`); every-cell food; `respawn_draws_per_tick = max(1, pop)` | Amd 03 |
| Analysis seeds **11–40**; pilot **1000–1009**; inferential RNG `20260911` | Amd 01/02/03 trail |
| BCa 10 000, Holm, α=0.05, paired-seed design | Amd 01 |
| `capsules_off` sd=0 expected (basal WAIT plateau) | Amd 03 honesty |
| ClaimGate ceiling default `runtime_observation`; blocked claims list | Amd 01/03 |
| Frozen artifacts: `results_v3.json`, Amd 02 failed pilot trail, `results_v5.json` | do not overwrite |
| Original prereg + Amd 01/02/03 **bytes** | sibling Amd 04 only |
| Engine opcodes / Phase pins | overlay-only changes |

**Schema after Amd 04:** `hard_experiment_01_v6` (proposed). Campaign digests must record `prereg_digest` + amd01 + amd02 + amd03 + **`prereg_amendment_04_digest`**.

---

## 5. Pilot seeds / analysis split

| Set | Seeds | Allowed | Forbidden |
|---|---|---|---|
| Pilot / calibration | **1000–1009 only** | Verify content_null destroys profitable marginal; activity_match ε; assay valid; sd > 0 on capsule-active arms; record legacy shuffled behavior | Inferential \(d_z\), Holm, BCa claim unlock, peeking at 11–40 |
| Analysis | **11–40** (n=30) | Confirmatory campaign **after** hashed Amd 04 + passing pilot | Re-tuning null token, ε, or yoking rule after peek |
| Smoke | 11–22 @ exploratory scale | CI / wiring | ClaimGate raise |
| Inferential RNG | `20260911` | BCa / permutation | Re-seed after seeing v6 numbers |

**Pilot gates (minimum):**

1. Assay valid (Amd 01 §3 + 1d″ accepted-adoption / content-changed logic as applicable).  
2. `content_null` profitable-payload rate ≈ 0 (or within pre-reg null band).  
3. `content_null` mean ATP **not** required to equal off a priori — but non-superiority is the confirmatory claim; pilot should show content_null is **not** construction-superior like shuffled.  
4. `activity_matched`: mean \|activity_match_gap\| < ε.  
5. Oracle > capsules_off (positive control).  
6. Do **not** stop for legacy `shuffled > off` — expected.

If pilot fails: **stop**; amend again or fix implementation; do not run 11–40.

---

## 6. Explicit ClaimGate statement

> **Wave 1e / Amendment 04 does not auto-grant `intervention_supported`.**  
> Ceiling remains **`runtime_observation`** unless and until every Amendment 01 decision-rule clause (research scale, tier, replay, assay valid, H1 vs off, H1 vs **new** confirmatory null, null non-superiority vs off, dose pattern as amended for downturn honesty) actually passes on a future hashed `results_v6.json` (name TBD) and is reviewed.  
> Fixing the negative control is **necessary** for a valid FAIL/PASS on the auxiliary clause; it is **not sufficient** for ladder promotion.

Blocked claims unchanged: `intelligence`, `collective_intelligence`, `proved_collective_intelligence`, `agi`, `tokyo_type1_passed`, `avida_replacement`.

---

## 7. Coding checklist (implement order — never reverse)

1. **Write** `docs/HARD_EXPERIMENT_01_PREREG_AMENDMENT_04.md`  
   - Willroth deviations table (broken shuffle → content_null + activity_matched).  
   - Lock ONE content_null algorithm + ONE activity_matched algorithm.  
   - Update confirmatory null arm in decision rule; demote legacy shuffled to sensitivity.  
   - Dose downturn disclosure (Simpson & Margolin; Hothorn); metric_count=3.  
   - Digests / schema v6 / ClaimGate ceiling statement.  
2. **Hash** Amd 04; record digest in campaign payload contract (tests may assert presence).  
3. **Code** overlay/HE01 arms + manipulation checks + artifact fields (additive; do not overwrite `results_v5.json`).  
4. **Unit tests:** content_null destroys marginal; window-1 nulls; peer-rotation still documented as broken sensitivity; activity_match gap; xfail/strict paths as needed.  
5. **Pilot 1000–1009** only under hashed Amd 04.  
6. **Pilot report** in handoff; if PASS → research 11–40.  
7. **Campaign artifact** `results_v6.json` (or agreed name) + honesty notes; ClaimGate stay `runtime_observation` unless full rule passes.  
8. **Only then** consider E6 → HE02 → HE03 track (E6 brief already exists; do not let E6 peek redefine 1e nulls).

**Never:** code → peek pilot → write Amd 04. **Never:** raise ClaimGate in the brief or in the first failing pilot.

---

## 8. Denylist

- Raising ClaimGate / inventing `intervention_supported` from 1e alone  
- Silent rewrite of original prereg or Amd 01/02/03 bytes  
- Treating peer-rotation `capsules_shuffled` as confirmatory content null  
- Permuting the **same** payload multiset and calling it content_null  
- Activity match **without** content nullification  
- Overwriting `results_v3.json` / `results_v5.json`  
- Using dose S as a 4th independent primary metric  
- Calling dose(4) “saturation success”  
- Counting attempts as successful accepts for activity matching  
- Tuning null token / ε / yoke rule on seeds 11–40  
- Cloud Agent, Drive uploads, PyPI, identity bump, new Phase letter, new opcodes  
- Production code **in this literature-brief task**  
- Inventing arms beyond review without a citation  

---

## 9. Competitor / method map (short)

| Tradition | Control type | HE01 mapping |
|---|---|---|
| Goldsby/Ofria Avida | Instruction knockout (`nop-X`) | `capsules_content_null` (payload → null token) |
| Boot / ABM placebo | Active control with matched exposure | `capsules_activity_matched` (yoked accepts) |
| AGM HTS | Realistic + saturated positive controls | Keep oracle; report Z′ vs off **and** vs `source_bias_off` |
| Simpson–Margolin / Hothorn | Downturn-aware dose tests | dose(4) downturn label; no false “saturate” |
| Nosek / Willroth / Lakens | Amend broken auxiliary hypothesis | Amd 04 sibling + deviations table |

---

## 10. Blockers (before coding)

1. **Amd 04 not yet written** — this brief is not the amendment; implementer must author the hashed sibling first.  
2. **Choose-and-freeze** content_null algorithm (fixed null token vs null catalogue) in Amd 04 text.  
3. **Choose-and-freeze** activity_matched yoke target + ε.  
4. **Schema / artifact field names** for null rates and `activity_match_gap` must be named in Amd 04 before pilot.  
5. **Decision-rule surgery:** confirmatory null arm swap must be explicit so Holm family and auxiliary H1 are unambiguous.  
6. **Legacy shuffled** kept for sensitivity → analysis code must not silently drop it or treat FAIL `shuffled>off` as assay failure.  
7. No ClaimGate raise path in 1e tooling PRs.

---

## 11. Report card (for parent agent)

| Item | Value |
|---|---|
| **Deliverable path** | `/workspace/codontrace-handoff/WAVE_1E_SCIENCE_BRIEF.md` |
| **Repo pin** | `wave-1d-seed-variance` @ `a5acb8b` |
| **Top 5 cites** | Goldsby 2012 `10.1073/pnas.1202233109`; Boot 2013 `10.1177/1745691613491271`; Zhang 1999 `10.1177/108705719900400206` (+ AGM NBK126174); Simpson & Margolin 1986 `10.1093/biomet/73.3.589` (+ Hothorn 2020 `10.48550/arxiv.2007.09631`); Willroth & Atherton 2024 `10.1177/25152459231213802` (+ Nosek 2018) |
| **Implement order** | Amd 04 doc → hash → code → unit tests → pilot 1000–1009 → (if PASS) analysis 11–40 → artifact; **never reverse** |
| **ClaimGate** | Remains `runtime_observation`; 1e does **not** auto-grant `intervention_supported` |
| **Blockers** | Amd 04 unwritten; must lock null + yoke algorithms; decision-rule null-arm swap; no overwrite of v5; no ClaimGate raise |
