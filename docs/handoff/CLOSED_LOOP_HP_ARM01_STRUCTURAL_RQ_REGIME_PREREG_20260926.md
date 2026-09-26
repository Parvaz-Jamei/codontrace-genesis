# Structural Red Queen regime pilot — Stages A→D (HP-ARM01-STRUCTURAL-RQ-REGIME)

**Status:** LOCKED before outcomes. No campaign numbers in this file.
**Date locked:** 2026-09-26 (Asia/Tehran)
**Slice name:** `HP-ARM01-STRUCTURAL-RQ-REGIME`
**Estimand (this wave):** `structural_polymorphism_hold_under_large_N_multilocus_mid_turnover`
**Secondary (conditional):** `cycle_candidate` — scored only after `polymorphism_hold`
**Unscored this wave:** Slowinski selfing invasion; mating / selfing hold estimands
**Substrate:** `population_runner_phase_b_host_parasite_env`
**Revision:** `hp-arm01-structural-rq-regime-20260926`
**Code hooks:** `src/codontrace/genesis/closed_loop_hp_arm01_structural_rq.py`
**Branch context:** `closed-loop/hp-three-arm-frequency-clocks` (PR #65)

This document freezes a **new** structural-regime pilot that addresses the
ordered mechanism failure stack behind sealed honest FAILS. It does **not**
edit, retune, or soft-pass sealed preregs `214df20` (Slowinski invasion,
seeds 201–208), `91ab0c6` (persistence ledger, seeds 301–308), or `7171d19`
(mating ledger, seeds 401–408). Selfing-hold / mating locks remain deferred;
Slowinski stays **unscored**. Last-live series and body-census soft-\(K\)
counts are not allelic \(N_e\) and do not authorize `polymorphism_hold`.

Nosek et al. (Proc. Natl. Acad. Sci. USA 115:2600–2606, 2018,
doi:10.1073/pnas.1708274114) separate prediction from postdiction. Simmons,
Nelson, and Simonsohn (Psychol. Sci. 22:1359–1366, 2011,
doi:10.1177/0956797611417632) motivate writing seeds and pass rules first.
Kriegeskorte et al. (Nat. Neurosci. 12:535–540, 2009, doi:10.1038/nn.2303)
forbid selecting the analysis on the confirming data. Ashby (J. Evol. Biol.
33:1795–1805, 2020, doi:10.1111/jeb.13718): sex ≠ Red Queen Dynamics;
`polymorphism_hold` ≠ `cycle_candidate` ≠ `red_queen_proved`.

## 1. Scientific motivation (ordered Stages A→D)

Sealed campaigns under tiny allelic \(N_e\) (host \(N\approx10\), soft \(K=32\),
two match founders, host bit-flip \(=0\)), a single composite matching-allele
locus (6-bit AND-collapse), bang-bang parasite replacement, and a 48-generation
horizon are structurally hostile to sustained polymorphism and cycling
(owner literature redirect; Wave 4 consensus). Primary citations:

1. **Gokhale & Traulsen 2013**, BMC Evol. Biol. 13:254,
   doi:10.1186/1471-2148-13-254 — in finite / small populations, sustained Red
   Queen oscillation is structurally unlikely; successive selective sweeps
   dominate. Body census ≠ allelic \(N_e\): lock match-class richness and
   frequencies per sub-locus, not soft-\(K\) living count alone.
2. **Engelstädter 2015**, Am. Nat. 185:E000,
   doi:10.1086/680476 — single interaction locus yields only narrow
   matching-allele cycling regimes; two or more independent loci expand
   cycling regimes. Prefer feature-overlap / graded allele channels; forbid
   AND-collapse of the 6-bit window to one exact-match bit.
3. **Rabajante et al. 2015**, Sci. Rep. 5:10004,
   doi:10.1038/srep10004 — intermediate parasite mortality / turnover supports
   cycles; extremes (full wipe each generation, or too-weak pressure) suppress
   mid-diversity. Lock keep-fraction \(\kappa\in(0,1)\) with mid mut and mid
   virulence / steal band.
4. **Decaestecker et al. 2007**, Nature 450:870–873,
   doi:10.1038/nature06291 — empirical Red Queen readouts often need long
   horizons; distinguish “no cycle” from “insufficient time.”
5. **Papkou et al. 2021**, Proc. R. Soc. B 288:20212269,
   doi:10.1098/rspb.2021.2269 — empirical coevolution / polymorphism context
   for multi-generation host–parasite frequency clocks (observation digests).

Ordered stack locked in **one** NEW prereg for a first structural Critic pilot:

| Stage | Lock |
|---|---|
| **A — Ne / diversity** | Host soft \(K\) / \(N_h\) and \(N_p\) in 50–100; ≥8–16 distinct match-state founders at \(t_0\); host bit-flip \(>0\); same `PopulationRunner` + `GenesisEngine` + `HostParasiteEnv` |
| **B — Multi-locus genetics** | Split 6-bit window into 2–3 independently scored sub-loci; graded affinity → debit fraction; forbid AND-collapse |
| **C — Mid turnover** | Parasite keep-fraction \(\kappa\in(0,1)\); mid parasite mut; mid virulence/steal; digest `turnover_audit` + mut/churn |
| **D — Horizon (pilot)** | 200–500 gens on few seeds (not 8×500 confirmatory); new seed block; match-class / sub-locus clocks = observation digests only |

HP / infection vocabulary stays in plugin / env / closed_loop modules.
`engine.py` stays domain-free.

## 2. Typed outcomes (mutually exclusive per seed)

Storm four-role ladder (locked). Every pilot seed receives exactly one label
from:

`sweep_fixation` | `polymorphism_hold` | `cycle_candidate` | `horizon_insufficient` | `parasite_extinct` | `selfing_nonviable` | `Slowinski_unscored`

Plus regime-hostile auxiliaries when demography / turnover contracts fail before
allelic scoring is interpretable.

| Typed outcome | Meaning |
|---|---|
| `parasite_extinct` | On any debit-active arm (`fixed` or `copassaged`), parasite stock empties before the terminal locked window, so allelic clocks cannot be scored. |
| `regime_hostile_ne` | Founder richness / host bit-flip / soft-\(K\) contract fails, **or** living host mating census on debit-active arms falls below `min_viable_census` at a locked window so series cannot be read. **Gates use match-class / per-sublocus frequencies + founder richness — never soft-\(K\) body census as \(N_e\) proxy.** Body census alone never grants `polymorphism_hold`. |
| `regime_hostile_turnover` | Debit-active arms survive demographically, but `turnover_audit` shows bang-bang wipe or freeze (effective keep-fraction outside the locked mid band, or mut/churn audit miss co-prereg'd with \(\kappa\)) so mid-diversity cannot be attributed to Stage C. |
| `sweep_fixation` | At any locked mid or terminal window on a debit-active arm, match-class (or per-sub-locus) richness \(< R_{\min}\) **or** a single class frequency \(> 1-\varepsilon\). Sweep / fixation dominates (Gokhale–Traulsen). |
| `horizon_insufficient` | Polymorphism criteria hold at mid windows but collapse only at terminal, **or** locked windows are too short to classify sweep vs hold vs cycle; Critic may not promote. Not a soft-green of sealed FAILS. |
| `polymorphism_hold` | **Primary success THIS wave (only).** On each debit-active score arm (`fixed` and `copassaged`): at **every** locked mid window **and** terminal, (a) match-class richness \(\ge R_{\min}\), **and** (b) no single class frequency \(> 1-\varepsilon\). Mid+terminal multi-class series — not one-shot diversity / bump. `avirulent` / `absent` = no-antagonist control only; never RQ null for mid-\(d\). |
| `cycle_candidate` | **Observation-only / secondary.** Recorded only after `polymorphism_hold` criteria hold, plus pre-registered dominant-class turnover across ≥2 locked windows with multi-seed concordance (§7). SPC/CUSUM / oscillation detectors are observation-only **after** hold — never accept path / RQ grant. Never equals `red_queen_proved`. |
| `selfing_nonviable` | Reserved mating/selfing label; **DEFER** — not scored as campaign Result this wave (mating deferred). |
| `Slowinski_unscored` | Slowinski invasion estimand left unscored this wave (DEFER). Emit when a seed would otherwise only be narrated as Slowinski ecology; do not unlock Slowinski. |

Priority (first match wins):
`parasite_extinct` → `regime_hostile_ne` → `regime_hostile_turnover` →
`sweep_fixation` → `horizon_insufficient` → `polymorphism_hold` →
`cycle_candidate` (observation upgrade only when oscillation rule holds).
If mating/Slowinski paths are accidentally invoked, label `selfing_nonviable`
or `Slowinski_unscored` rather than inventing an invasion PASS/FAIL.

Refuse packaging as Slowinski PASS. Refuse `red_queen_proved` (always false
this wave). Refuse soft-green of `214df20` / `91ab0c6` / `7171d19`.

## 3. Ecology arms (retained contrast; Slowinski unscored)

| Ecology arm | Tip passage | Role this wave |
|---|---|---|
| `avirulent` | `absent` | No-antagonist control only; not RQ null for mid-\(d\) |
| `fixed` | `frozen` | Debit on, update off — debit-active score arm |
| `copassaged` | `coevolve` | Debit on, update on — debit-active score arm |

Arm contrast is retained for reporting. Slowinski three-arm selfing invasion
contrast is **not** evaluated. Mating / selfing frequencies may appear in
digests as observation only.

## 4. Stage A — Ne / diversity (locked)

| Parameter | Locked value | Role |
|---|---|---|
| Host soft carrying capacity \(K\) | **64** | Large-\(N\) floor in 50–100 band (Gokhale) |
| Host founder count \(N_h\) | **64** | Equals soft \(K\) at \(t_0\) (saturated start) |
| Parasite stock \(N_p\) | **64** | Matched large-\(N\) parasite pool |
| Distinct match-state founders at \(t_0\) | **16** | Founder richness ≫2 (not just `000111`/`111000`) |
| Host bit-flip rate | **0.02** | Non-zero locked rate (was 0.0 on sealed paths) |
| Stage A co-requirement | **ALL** of \(N\in[50,100]\), founder richness ≫2, host bit-flip >0 on the **same** `PopulationRunner` / `GenesisEngine` / `HostParasiteEnv` | No second population registry |
| World size | **16** | Scaled with \(N\) so large-\(N\) does not starve (Elena & Lenski) |
| Founder spatial policy | `food_patch_interleaved` | Avoid off-patch starve artifact |
| Food patch set | 4×4: \((x,y)\) for \(x,y\in\{0,1,2,3\}\) | Expanded with world / \(N\) |
| Resource bolus (see Stage C) | **20.0** × 16 patches | Scaled with patch count / \(N\) |
| Substrate | `population_runner_phase_b_host_parasite_env` | Unchanged life-loop bind; no second registry |
| Reproduction mode | **asexual** (`ReproductionMode.ASEXUAL`) | Mating / Slowinski **DEFER**; allelic clocks do not require sexual chamber |
| Min viable census (demographic gate only) | **16** living hosts with mating mode, per debit-active arm, at each locked window | **Never** soft-\(K\) body census as \(N_e\) proxy; allelic gates use match-class / per-sublocus freqs + founder richness |

### Match-state founder multiset (16 distinct 6-bit windows)

Ordered host founders, all `outcross` mating (Slowinski / selfing deferred).
Recognition windows (distinct):

1. `000000`  2. `000001`  3. `000010`  4. `000011`
5. `000100`  6. `000101`  7. `000110`  8. `000111`
9. `111000` 10. `111001` 11. `111010` 12. `111011`
13. `111100` 14. `111101` 15. `111110` 16. `111111`

Then repeat this 16-window block three more times (indexes 17–64) to fill
\(N_h=64\), preserving order and distinctness at \(t_0\) (16 unique states).
Parasite stock at \(t_0\): uniform draw without replacement cycling over the
same 16 windows until \(N_p=64\) (4 copies of each founder window).

## 5. Stage B — Multi-locus genetics (locked)

| Parameter | Locked value | Role |
|---|---|---|
| Recognition window width | **6** bits (unchanged layout) | Plugin match locus |
| Sub-locus partition | **3** independent sub-loci × **2** bits | Engelstädter multi-locus |
| Sub-locus bit ranges (0-indexed within window) | \(L_0=[0,2)\), \(L_1=[2,4)\), \(L_2=[4,6)\) | Fixed; no post-hoc repartition |
| Affinity rule | `feature_overlap` | Graded allele channels (Engelstädter) |
| Affinity score | mean over **independent bit-disjoint** sub-loci of (sub-locus Hamming agreement / 2) | \(\in[0,1]\); sub-scores never collapsed before averaging |
| Debit | graded \(f(\text{independent bit-disjoint sub-scores})\) → virulence × steal × affinity; **one parasite–host pair per seat per generation** (no multi-hit pile-on) | Graded debit; partial match pays partial debit; load must not erase mid-d |
| AND-exact composite sold as multi-locus | **forbidden** (Engelstädter theater) | Exact full-window AND required for any debit is rejected |
| Match-class identity for clocks | Per-sub-locus 2-bit allele string (and joint tuple digest) | Observation digests |

`HostParasiteEnv` may still gate inject eligibility; **debit magnitude** on
this path must follow graded affinity (plugin / closed_loop structural module),
not a binary exact-window AND.

## 6. Stage C — Mid turnover (locked)

| Parameter | Locked value | Role |
|---|---|---|
| Parasite keep-fraction \(\kappa\) | **0.5** | Mid-\(\kappa\) = partial keep-fraction \(\in(0,1)\); not wipe/freeze |
| Parasite mutation rate | **0.25** | Mid mut band; **co-preregistered with** \(\kappa\) (not retuned separately after peek) |
| Virulence | **8.0** | Mid load band (sealed exploratory 8; harsh 32 reserved); must not erase mid-d |
| Steal fraction | **0.15** | Mid steal band; co-locked with virulence so graded contact does not erase mid-d (Rabajante) |
| Birth ATP | **48.0** | Reproductive assurance under soft \(K\) |
| Basal runtime ATP cost | **0.05** | Unchanged spirit |
| Resource bolus amount | **20.0** per patch at generation boundary | Elena–Lenski refill |
| Passage refill mode | `generation_boundary_resource_bolus` | Unchanged |
| Ticks per generation | **2** | Bound arm default |
| Handling time | **0.0** | Off this pilot |
| Turnover audit | required export | Record effective replaced fraction, mut events, churn |

On `fixed` (frozen): parasite windows stay at ancestral multiset; \(\kappa\)
does not apply (update off). On `copassaged`: each generation keep
\(\lfloor\kappa N_p\rfloor\) randomly selected current windows; replace the
rest from graded-match parent draws + mut. On `avirulent`: parasite stock
empty (control).

`turnover_audit` must record per generation on `copassaged`: kept count,
replaced count, mutation event count, unique window churn. Effective keep
outside \([\kappa-0.15,\kappa+0.15]\) over the mid windows →
`regime_hostile_turnover` if demography otherwise OK.

## 7. Stage D — Horizon and Critic windows (pilot)

| Parameter | Locked value |
|---|---|
| Generations | **250** |
| Locked observation windows (1-indexed generation index) | **50**, **125**, **250** (terminal) |
| Mid windows for hold | **50**, **125** |
| Terminal window | **250** |
| Pilot seeds (held-out; disjoint from 101–108, 201–208, 301–308, 401–408, 501–508) | **601, 602, 603** |
| \(R_{\min}\) (richness) | **3** distinct match-classes (joint sub-locus tuple) **or** ≥2 distinct alleles on **at least 2** of 3 sub-loci |
| \(\varepsilon\) (dominance) | **0.15** so single-class frequency \(>1-\varepsilon=0.85\) fails hold |
| Oscillation rule (`cycle_candidate`) | Dominant joint match-class identity changes across ≥2 consecutive locked windows on **both** debit-active arms; and ≥2 of 3 pilot seeds agree on that change pattern (multi-seed concordance) |
| Confirmatory bar | **not this wave** (no 8×500); pilot only |
| Pass reporting (primary) | count seeds with `polymorphism_hold` only; `cycle_candidate` is secondary observation; no soft-green |

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
| Ceiling climb | ≤ `runtime_observation` until pre-reg `polymorphism_hold` across locked windows/seeds; then ≤ `candidate_evidence` for `cycle_candidate` **only** |
| Ceiling hard stop | never climb past `candidate_evidence`; never equate hold or living clocks with RQ proved / Slowinski unlock |
| Ceiling for `cycle_candidate` | ≤ `candidate_evidence`; observation-only; never authorizes RQ proved |
| Soft-pass \(N=1\) as campaign RQ | **rejected** |
| Body census as allelic \(N_e\) | **rejected** |
| `avirulent` as RQ null for mid-\(d\) | **rejected** |
| `polymorphism_hold` = `cycle_candidate` | **rejected** |
| `cycle_candidate` = `red_queen_proved` | **rejected** (Ashby) |
| Soft-green of `214df20` / `91ab0c6` / `7171d19` | **rejected** |
| Peek-retune of this file after outcomes | **rejected** |
| HP / infection vocabulary in `engine.py` | **rejected** |
| Mating / Slowinski unlock this wave | **rejected** (DEFER) |
| Invented DOIs / second population registry / BAIC edits | **rejected** |

## 9. Exports required with outcomes

- Typed outcome counts and per-seed table (mutually exclusive labels)
- Per-sub-locus frequency digests at windows 50, 125, 250
- Joint match-class richness and max-class frequency at those windows
- `turnover_audit` digest (copassaged)
- Arm contrast retained (avirulent / fixed / copassaged census + clocks)
- Whether Slowinski was scored: **no**
- `engine.py` domain-token scan CLEAN
- Claim ceiling ≤ `runtime_observation` unless polymorphism_hold earned climb to ≤ `candidate_evidence`
- Evidence dir:
  `/workspace/codontrace-genesis-storm/evidence_structural_rq_20260926/`
  (+ tar.gz) with RESULT.md, prereg copy, SHAs, campaign_report.json,
  seed_terminals.json, typed_outcome_counts.json, engine_token_scan.txt,
  claimgate_ceiling.txt, match_class digests if available

## 10. What may and may not change after lock

**May:** record typed outcomes, digests, census tables, turnover audits,
ClaimGate status; attach Pearl/SPC measurement only as non-accept evidence.

**May not:** edit this file's locked parameters after seeing outcomes; retune
seeds, windows, \(R_{\min}\), \(\varepsilon\), \(\kappa\), sub-locus partition,
virulence/steal, or bit-flip after peek; rewrite sealed preregs; narrate
`sweep_fixation` or `horizon_insufficient` as Slowinski ecology Result;
promote RQ flags; put HP domain tokens in `engine.py`; unlock Slowinski /
mating as PASS this wave.
