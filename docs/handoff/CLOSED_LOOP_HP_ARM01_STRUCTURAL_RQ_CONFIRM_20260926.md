# Structural Red Queen regime confirmatory — Stages A→D (HP-ARM01-STRUCTURAL-RQ-CONFIRM)

**Status:** LOCKED before outcomes. No campaign numbers in this file.
**Date locked:** 2026-09-26 (Asia/Tehran)
**Slice name:** `HP-ARM01-STRUCTURAL-RQ-CONFIRM`
**Estimand (this wave):** `structural_polymorphism_hold_under_large_N_multilocus_mid_turnover`
**Secondary (conditional):** `cycle_candidate` — scored only after `polymorphism_hold`; observation-only
**Unscored this wave:** Slowinski selfing invasion; mating / selfing hold estimands
**Substrate:** `population_runner_phase_b_host_parasite_env`
**Revision:** `hp-arm01-structural-rq-confirm-20260926`
**Code hooks:** `src/codontrace/genesis/closed_loop_hp_arm01_structural_rq_confirm.py`
**Branch context:** `closed-loop/hp-three-arm-frequency-clocks` (PR #65)

This document freezes the **confirmatory** structural-regime campaign that
reuses the Stage A–D knobs already landed under the pilot prereg
`CLOSED_LOOP_HP_ARM01_STRUCTURAL_RQ_REGIME_PREREG_20260926.md`. It confirms
that landed regime; it does **not** redesign Stages A–D. It does **not**
edit, retune, or soft-pass sealed preregs `214df20` (Slowinski invasion,
seeds 201–208), `91ab0c6` (persistence ledger, seeds 301–308), or `7171d19`
(mating ledger, seeds 401–408). Pilot outcomes under seeds 601–603
(`645e68d` / tip `2ab9ec9`) are **prior observation only** and are not
soft-greened into a confirmatory PASS. Pilot seeds 601–603 are never reused
as confirmatory seeds. Selfing-hold / mating locks remain deferred;
Slowinski stays **unscored**. Last-live series and body-census soft-\(K\)
counts are not allelic \(N_e\) and do not authorize `polymorphism_hold`.
`regime_hostile_ne` is a typed fail and never a hold.

Nosek et al. (Proc. Natl. Acad. Sci. USA 115:2600–2606, 2018,
doi:10.1073/pnas.1708274114) separate prediction from postdiction. Simmons,
Nelson, and Simonsohn (Psychol. Sci. 22:1359–1366, 2011,
doi:10.1177/0956797611417632) motivate writing seeds and pass rules first.
Kriegeskorte et al. (Nat. Neurosci. 12:535–540, 2009, doi:10.1038/nn.2303)
forbid selecting the analysis on the confirming data. Ashby (J. Evol. Biol.
33:1795–1805, 2020, doi:10.1111/jeb.13718): sex ≠ Red Queen Dynamics;
`polymorphism_hold` ≠ `cycle_candidate` ≠ `red_queen_proved`.

## 1. Relation to the pilot (confirm, do not redesign)

The pilot locked Stages A–D and ran seeds 601–603 at 250 generations with
windows 50 / 125 / 250, bolus 20.0 on 16 patches, and an OR soft-path in the
hold clause. Confirmatory keeps the same Stage A–D ecology knobs and
tightens only the items listed below:

| Item | Pilot (prior observation) | Confirmatory (this lock) |
|---|---|---|
| Seeds | 601–603 (n=3) | **701–708** (n=8); never reuse 601–603 |
| Horizon | 250 gens | **500** gens |
| Locked windows | 50, 125, 250 | **125, 250, 500** |
| Hold clause | joint \(R_{\min}\) **or** sub-locus soft-path | **conjunctive only** (see §7) |
| Bolus / patches | 20.0 × 16 | **24.0 × 20** (Elena–Lenski scale with \(N\); digest-pin) |
| Campaign bar | pilot count only | PASS iff hold-class ≥ **6/8** |

Forbidden: dropping the demographic floor or the campaign bar to rescue
pilot `regime_hostile_ne` seeds; retuning virulence / steal / \(\kappa\) /
bit-flip after peek; soft-greening sealed FAILS.

Primary citations for the Stage A–D stack remain Gokhale & Traulsen 2013
(BMC Evol. Biol. 13:254, doi:10.1186/1471-2148-13-254), Engelstädter 2015
(Am. Nat. 185:E000, doi:10.1086/680476), Rabajante et al. 2015 (Sci. Rep.
5:10004, doi:10.1038/srep10004), Decaestecker et al. 2007 (Nature
450:870–873, doi:10.1038/nature06291), and Papkou et al. 2021 (Proc. R.
Soc. B 288:20212269, doi:10.1098/rspb.2021.2269). Resource-bolus scaling
follows Elena & Lenski (Nat. Rev. Genet. 4:457–469, 2003,
doi:10.1038/nrg1088) spirit: refill density scales with world / \(N\), not
a post-hoc rescue of typed fails.

HP / infection vocabulary stays in plugin / env / closed_loop modules.
`engine.py` stays domain-free. No second population registry. BAIC pins are no longer byte-frozen (owner policy 2026-09-26); engine stays general — see OWNER_ENGINE_MODULE_UPDATE_POLICY_20260926.md.

## 2. Typed outcomes (mutually exclusive per seed)

Every confirmatory seed receives exactly one label from:

`sweep_fixation` | `polymorphism_hold` | `cycle_candidate` | `horizon_insufficient` | `parasite_extinct` | `selfing_nonviable` | `Slowinski_unscored`

Plus regime-hostile auxiliaries when demography / turnover contracts fail
before allelic scoring is interpretable.

| Typed outcome | Meaning |
|---|---|
| `parasite_extinct` | On any debit-active arm (`fixed` or `copassaged`), parasite stock empties before the terminal locked window, so allelic clocks cannot be scored. |
| `regime_hostile_ne` | Founder richness / host bit-flip / soft-\(K\) contract fails, **or** living host mating census on debit-active arms falls below `min_viable_census` at a locked window so series cannot be read. **Gates use match-class / per-sublocus frequencies + founder richness — never soft-\(K\) body census as \(N_e\) proxy.** Body census alone never grants `polymorphism_hold`. Typed fail; never hold. |
| `regime_hostile_turnover` | Debit-active arms survive demographically, but `turnover_audit` shows bang-bang wipe or freeze (effective keep-fraction outside the locked mid band) so mid-diversity cannot be attributed to Stage C. |
| `sweep_fixation` | At any locked mid or terminal window on a debit-active arm, the conjunctive hold clause fails. Sweep / fixation dominates (Gokhale–Traulsen). |
| `horizon_insufficient` | Conjunctive hold holds at mid windows but collapses only at terminal, **or** locked windows are too short to classify sweep vs hold vs cycle. Not a soft-green of sealed FAILS. |
| `polymorphism_hold` | **Primary success THIS wave (only).** On **each** debit-active score arm (`fixed` and `copassaged`): at **every** locked mid window **and** terminal, the **conjunctive** hold clause (§7) holds. Mid+terminal multi-class series — not one-shot diversity / bump. `avirulent` / `absent` = no-antagonist control only; never RQ null for mid-\(d\). |
| `cycle_candidate` | **Observation-only / secondary.** Recorded only after `polymorphism_hold` criteria hold, plus pre-registered dominant-class turnover across ≥2 locked windows with multi-seed concordance (§7). Never equals `red_queen_proved`. |
| `selfing_nonviable` | Reserved mating/selfing label; **DEFER** — not scored as campaign Result this wave. |
| `Slowinski_unscored` | Slowinski invasion estimand left unscored this wave (DEFER). |

Priority (first match wins):
`parasite_extinct` → `regime_hostile_ne` → `regime_hostile_turnover` →
`sweep_fixation` → `horizon_insufficient` → `polymorphism_hold` →
`cycle_candidate` (observation upgrade only when oscillation rule holds).

Refuse packaging as Slowinski PASS. Refuse `red_queen_proved` (always false
this wave). Refuse soft-green of `214df20` / `91ab0c6` / `7171d19`. Refuse
treating pilot `645e68d` / `2ab9ec9` as confirmatory PASS.

## 3. Ecology arms (retained contrast; Slowinski unscored)

| Ecology arm | Tip passage | Role this wave |
|---|---|---|
| `avirulent` | `absent` | No-antagonist control only; not RQ null for mid-\(d\) |
| `fixed` | `frozen` | Debit on, update off — debit-active score arm |
| `copassaged` | `coevolve` | Debit on, update on — debit-active score arm |

## 4. Stage A — Ne / diversity (confirm landed; unchanged ecology)

| Parameter | Locked value | Role |
|---|---|---|
| Host soft carrying capacity \(K\) | **64** | Large-\(N\) floor in 50–100 band |
| Host founder count \(N_h\) | **64** | Equals soft \(K\) at \(t_0\) |
| Parasite stock \(N_p\) | **64** | Matched large-\(N\) parasite pool |
| Distinct match-state founders at \(t_0\) | **16** | Founder richness ≫2 |
| Host bit-flip rate | **0.02** | Non-zero locked rate |
| World size | **20** | Fits 20-patch digest-pin |
| Founder spatial policy | `food_patch_interleaved` | Avoid off-patch starve artifact |
| Food patch set | **20** patches: \((x,y)\) for \(x\in\{0,1,2,3,4\}\), \(y\in\{0,1,2,3\}\) | Digest-pin with bolus |
| Resource bolus amount | **24.0** per patch at generation boundary | Elena–Lenski scale with \(N\); FORBID dropping floor/bar to rescue pilot `hostile_ne` |
| Substrate | `population_runner_phase_b_host_parasite_env` | Unchanged life-loop bind; no second registry |
| Reproduction mode | **asexual** (`ReproductionMode.ASEXUAL`) | Mating / Slowinski **DEFER** |
| Min viable census (demographic gate only) | **12** living hosts with mating mode, per debit-active arm, at each locked window | Demographic floor ≠ \(N_e\); `regime_hostile_ne` typed fail never hold |

### Match-state founder multiset (16 distinct 6-bit windows)

Same ordered block as the pilot prereg §4: windows `000000` … `000111`
and `111000` … `111111`, repeated to fill \(N_h=64\) (16 unique at \(t_0\)).
Parasite stock cycles the same 16 windows to \(N_p=64\).

## 5. Stage B — Multi-locus genetics (confirm landed)

| Parameter | Locked value |
|---|---|
| Recognition window width | **6** bits |
| Sub-locus partition | **3** independent sub-loci × **2** bits |
| Sub-locus bit ranges | \(L_0=[0,2)\), \(L_1=[2,4)\), \(L_2=[4,6)\) |
| Affinity rule | `feature_overlap` (graded); **refuse AND-exact** composite sold as multi-locus |
| Debit | graded affinity × virulence × steal; one parasite–host pair per seat per generation |

## 6. Stage C — Mid turnover (confirm landed)

| Parameter | Locked value |
|---|---|
| Parasite keep-fraction \(\kappa\) | **0.5** |
| Parasite mutation rate | **0.25** |
| Virulence | **8.0** |
| Steal fraction | **0.15** |
| Birth ATP | **48.0** |
| Basal runtime ATP cost | **0.05** |
| Passage refill mode | `generation_boundary_resource_bolus` |
| Ticks per generation | **2** |
| Handling time | **0.0** |
| \(\kappa\) mid-band tolerance | \(\pm 0.15\) on copassaged mid-window mean keep |

## 7. Stage D — Horizon, conjunctive hold, and campaign bar

| Parameter | Locked value |
|---|---|
| Generations | **500** |
| Locked observation windows (1-indexed) | **125**, **250**, **500** (terminal) |
| Mid windows for hold | **125**, **250** |
| Terminal window | **500** |
| Confirmatory seeds (held-out; disjoint from 101–108, 201–208, 301–308, 401–408, 501–508, **and** pilot 601–603) | **701, 702, 703, 704, 705, 706, 707, 708** |
| \(R_{\min}\) (joint richness) | **3** |
| \(\varepsilon\) (dominance) | **0.15** (single-class frequency \(>1-\varepsilon=0.85\) fails) |
| Hold clause | **conjunctive only** (remove OR soft-path): on each debit-active arm at each mid+terminal window, **all** of (a) joint richness \(\ge R_{\min}\), **and** (b) max joint class frequency \(\le 1-\varepsilon\), **and** (c) ≥2 sub-loci with allelic richness ≥2 |
| Oscillation rule (`cycle_candidate`) | Dominant joint match-class identity changes across ≥2 consecutive locked windows on **both** debit-active arms; and ≥2 confirmatory seeds agree on that change pattern |
| Campaign PASS | hold-class seeds (`polymorphism_hold` or observation upgrade `cycle_candidate`) ≥ **6/8** |
| Mixed | 3–5/8 hold-class → **no** campaign PASS (report Mixed) |
| Honest FAIL | ≤2/8 hold-class |
| Primary success label | `polymorphism_hold` only; `cycle_candidate` remains observation-only / secondary |

Clocks: per-sub-locus frequency series **and** joint match-class series at
the locked windows only. No post-hoc window pick. Digests are observation
only; they never write `red_queen_proved`.

## 8. ClaimGate and ceiling

| Item | Locked rule |
|---|---|
| `red_queen_proved` | **false**; not promoted |
| `biological_red_queen_proved` | **false** |
| ClaimGate refuse | must still raise on `red_queen_proved` |
| Ceiling default | `runtime_observation` |
| Ceiling climb | ≤ `runtime_observation` until confirmatory hold seeds exist; then ≤ `candidate_evidence` |
| Ceiling hard stop | never climb past `candidate_evidence`; never equate hold or living clocks with RQ proved / Slowinski unlock |
| Ceiling for `cycle_candidate` | ≤ `candidate_evidence`; observation-only; never authorizes RQ proved |
| Soft-pass \(N=1\) as campaign RQ | **rejected** |
| Body census as allelic \(N_e\) | **rejected** |
| Drop floor/bar to rescue pilot `hostile_ne` | **rejected** |
| Soft-green of `214df20` / `91ab0c6` / `7171d19` | **rejected** |
| Soft-green of pilot `645e68d` / `2ab9ec9` | **rejected** (prior observation only) |
| Peek-retune of this file after outcomes | **rejected** |
| HP / infection vocabulary in `engine.py` | **rejected** |
| Mating / Slowinski unlock this wave | **rejected** (DEFER) |
| Second population registry / BAIC edits | **rejected** |

## 9. Exports required with outcomes

- Typed outcome counts and per-seed table (mutually exclusive labels)
- Per-sub-locus frequency digests at windows 125, 250, 500
- Joint match-class richness and max-class frequency at those windows
- `turnover_audit` digest (copassaged)
- Arm contrast retained (avirulent / fixed / copassaged census + clocks)
- Whether Slowinski was scored: **no**
- `engine.py` domain-token scan CLEAN
- Claim ceiling ≤ `runtime_observation` unless confirmatory hold earned climb to ≤ `candidate_evidence`
- Campaign PASS / Mixed / honest FAIL against the 6/8 bar
- Evidence dir:
  `/workspace/codontrace-genesis-storm/evidence_structural_rq_confirm_20260926/`
  (+ tar.gz) with RESULT.md, prereg copy, SHAs, campaign_report.json,
  seed_terminals.json, typed_outcome_counts.json, engine_token_scan.txt,
  claimgate_ceiling.txt

## 10. What may and may not change after lock

**May:** record typed outcomes, digests, census tables, turnover audits,
ClaimGate status; attach Pearl/SPC measurement only as non-accept evidence.

**May not:** edit this file's locked parameters after seeing outcomes; retune
seeds, windows, \(R_{\min}\), \(\varepsilon\), \(\kappa\), sub-locus partition,
virulence/steal, bit-flip, bolus, patch count, demographic floor, or campaign
bar after peek; rewrite sealed preregs; narrate `sweep_fixation`,
`horizon_insufficient`, or `regime_hostile_ne` as Slowinski ecology Result;
promote RQ flags; put HP domain tokens in `engine.py`; unlock Slowinski /
mating as PASS this wave; soft-green the pilot.
