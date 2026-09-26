# Selfing transmission contract, density mate-limitation, and avirulent hold gates (HP-ARM01-SELFING-HOLD)

**Status:** LOCKED before outcomes. No campaign numbers in this file.  
**Date locked:** 2026-09-26 (Asia/Tehran)  
**Slice names:** `HP-ARM01-SELFING-TRANSMISSION-CONTRACT`, `HP-ARM01-MATE-LIMITATION-PROCESS`, `HP-ARM01-AVI-HOLD-GATE`, `HP-ARM01-BASELINE-HOLD-GATE`  
**Estimand (conditional):** `slowinski_selfing_invasion_into_obligate_outcross` — scored only after assay validity **and** avirulent mid+terminal selfing hold  
**Substrate:** `population_runner_phase_b_host_parasite_env`  
**Revision:** `hp-arm01-selfing-hold-20260926`  
**Code hooks:** `src/codontrace/genesis/closed_loop_hp_arm01_selfing_hold.py`  
**Branch context:** `closed-loop/hp-three-arm-frequency-clocks` (PR #65)

This document freezes a **new** confirmatory cell set that repairs the
mating-transmission / reproductive-assurance contract hole exposed by the
mating-ledger campaign in
`CLOSED_LOOP_HP_ARM01_MATING_LEDGER_PREREG_20260926.md` (commit `7171d19`,
typed `selfing_nonviable` 8/8 under living demes). That mating-ledger lock,
the persistence ledger (`91ab0c6`, seeds 301–308), and the sealed Slowinski
invasion prereg (`214df20`, seeds 201–208) are **not** edited, retuned, or
soft-passed. Last-live series and early selfing bumps are not an alternate
PASS. SPC / Pearl measurement never owns accept or Red Queen flags.

Nosek et al. (Proc. Natl. Acad. Sci. USA 115:2600–2606, 2018,
doi:10.1073/pnas.1708274114) separate prediction from postdiction. Simmons,
Nelson, and Simonsohn (Psychol. Sci. 22:1359–1366, 2011,
doi:10.1177/0956797611417632) motivate writing seeds and pass rules first.
Kriegeskorte et al. (Nat. Neurosci. 12:535–540, 2009, doi:10.1038/nn.2303)
forbid selecting the analysis on the confirming data.

Sealed P7 seeds 101–108 remain untouched. Prior seeds 401–408 are not reused.

## 1. Scientific motivation

Under the mating-ledger lock, generation-boundary resource bolus and debit↔birth
gain restored living generation-48 host census ≫ raised floor on all three arms
(assay-valid 8/8). Terminal avirulent selfing frequency was nevertheless **0.0**
on every seed (`selfing_nonviable` 8/8). Series inspection shows early
transmission then purge by ~generation 10 under soft \(K\), globally available
outcross mates, unpaid two-fold cost of sex, and selfing offspring ATP
endowments that fail the next reproduction gate. That pattern is **not** a
Slowinski ecology contrast. It is a **mating-mode transmission /
reproductive-assurance / density mate-limitation contract hole**:

1. **Mode-true birth.** When the mating locus declares selfing, birth must be
   truly selfing (asexual copy-self; no forced sexual chamber override).
   Reproductive assurance must hold through the locked horizon (Theologidis
   et al., BMC Biol. 12:93, 2014, doi:10.1186/s12915-014-0093-1).
2. **Mating-locus lock.** Selfing / outcross genotype at the mating locus
   transmits faithfully to offspring under the declared mode (plugin / Phase B
   chamber — not infection physics in `engine.py`).
3. **Density mate-limitation.** Under saturated soft \(K\), outcross mate-search
   is limited (local neighborhood + per-generation mate cap) so selfing is not
   automatically purged by unlimited outcross opportunities. Density-regulated
   selfing / outcrossing competition: Cheptou and Dieckmann (Proc. R. Soc. B
   269:1177–1186, 2002, doi:10.1098/rspb.2002.1997). Mate-density / Allee
   context for outcross pollen limitation: Cheptou (Evolution 58:493–498, 2004,
   doi:10.1111/j.0014-3820.2004.tb01796.x).
4. **Documented two-fold cost of sex (optional honesty).** Enable
   `SexualRecombinationConfig.two_fold_cost_sex` under this NEW prereg so sexual
   chamber pairs place one product (Avida `TWO_FOLD_COST_SEX`). Sex ≠ Red Queen
   Dynamics (Ashby, J. Evol. Biol. 33:1795–1805, 2020, doi:10.1111/jeb.13718).
   Do not claim `red_queen_proved`.
5. **Mid-horizon + terminal hold (ClaimCritic).** Avirulent selfing must stay
   ≥ ε at locked mid window(s) **and** terminal. Bump-then-purge remains typed
   `selfing_nonviable`. Export `baseline_series_digest`.
6. **Avirulent hold before Slowinski bar (EcoEvo).** Only if mid+terminal hold
   passes may the Slowinski three-arm contrast be scored → `invasion_fail` /
   `invasion_pass`. Else `selfing_nonviable` or `persistence_fail`.

HP / infection vocabulary stays in plugin / env / runner modules.
`engine.py` stays domain-free.

## 2. Typed outcomes (ClaimCritic taxonomy)

Every confirmatory seed receives exactly one typed outcome:

| Typed outcome | Meaning |
|---|---|
| `persistence_fail` | Assay invalid: minimum viable census gate failed on any ecology arm. Slowinski estimand **unscored**. |
| `selfing_nonviable` | Census gate passed, but avirulent mid+terminal selfing hold failed (transmission / reproductive-assurance / mate-limitation baseline failed). Slowinski estimand **unscored**. Not an ecology null. Early bump alone does not pass. |
| `invasion_fail` | Census gate passed **and** avirulent mid+terminal hold held, but the Slowinski invasion contrast does not hold at generation 48. |
| `invasion_pass` | Census gate passed, avirulent mid+terminal hold held, and the Slowinski invasion contrast holds at generation 48. |

Refuse packaging universal selfing purge as Slowinski ecology Result.
Refuse soft-green of `7171d19`, `91ab0c6`, or `214df20`.
Refuse `last_live` or early-bump-as-baseline as PASS.
Refuse SPC as accept / RQ owner.

## 3. Gates (order locked)

Before any Slowinski invasion contrast is scored for a seed:

1. **ASSAY-VALIDITY-GATE (raised census floor).** At terminal generation, each
   ecology arm must have living host mating census ≥ `min_viable_census`
   (**8**). If any arm fails, outcome is `persistence_fail`.
2. **AVIRULENT-SELFING-HOLD-GATE (mid + terminal).** On the `avirulent` arm,
   selfing frequency must be ≥ `avirulent_selfing_hold_epsilon` (**0.05**) at
   every locked mid window **and** at terminal generation 48. Locked mid
   windows: generations **16** and **32** (1-indexed generation index after
   that many `run_generations` steps; series index `g-1`). If the census gate
   passed but this hold fails (including bump-then-purge), outcome is
   `selfing_nonviable` (not `invasion_fail`).
3. **SLOWINSKI BAR.** Only when both gates pass may the locked Slowinski
   invasion contrast be evaluated → `invasion_pass` or `invasion_fail`.

## 4. HP-ARM01-SELFING-TRANSMISSION-CONTRACT (mechanism)

| Parameter | Locked value | Role |
|---|---|---|
| Selfing copy-self mode | `asexual` via Phase B `resolve_copy_self_mode` when outcross codon is `000` | Mode-true birth; no mate required |
| Outcross copy-self mode | `chamber` when outcross codon is `001` | Unchanged Phase B sexual chamber |
| Forced `SEXUAL_CROSSOVER` override of selfing inheritance | **forbidden** | Population config may enable sexual chamber for outcrossers; selfing genotype must still take the asexual path |
| Mating-locus lock | **on** | After birth (asexual or chamber), restore the declaring parent's mating codon onto the child genome at the outcross locus |
| Selfing birth ATP endowment | **48.0** (equal to locked `birth_atp`) | Reproductive assurance: selfing offspring clear `min_runtime_atp` and retain enough ATP for subsequent COPY_SELF under basal cost |
| Outcross mating-effort ATP | **1.0** | Unchanged |
| Founder spatial policy | `food_patch_interleaved` | Retained from mating ledger (selfing not off-patch starved) |
| Food patch set | 4×2: \((x,y)\) for \(x\in\{0,1,2,3\}\), \(y\in\{0,1\}\) | Unchanged |

## 5. HP-ARM01-MATE-LIMITATION-PROCESS (mechanism)

| Parameter | Locked value | Role |
|---|---|---|
| Mate-search radius (Manhattan) | **1** | Local outcross mate neighborhood under soft \(K\) |
| Outcross successful mates per organism per generation | **1** | Caps unlimited mate abundance at saturation |
| Density mate-limitation mode | `local_radius_plus_per_capita_cap` | Cheptou–Dieckmann density context; not well-mixed global mate pool |
| Two-fold cost of sex | **paid** (`two_fold_cost_sex=True`) | Chamber places one recombinant product; documented; Ashby 2020 sex≠RQD |

## 6. HP-ARM01-DEBIT-GAIN-ASSURANCE (retained schedule)

Locked debit↔birth gain schedule (plugin / arm defaults — not engine infection),
unchanged in spirit from the mating ledger so demography stays honest:

| Parameter | Locked value | Role |
|---|---|---|
| Virulence | **32.0** | Unchanged |
| Steal fraction | **0.25** | Unchanged |
| Birth ATP | **48.0** | Unchanged |
| Resource bolus amount | **20.0** per patch at generation boundary | Unchanged |
| Soft carrying capacity \(K\) | **32** | Unchanged |
| Basal runtime ATP cost | **0.05** | Unchanged |
| Passage refill mode | `generation_boundary_resource_bolus` | Unchanged |
| Thin chemostat ATP inflow | **off** (0.0) | Deferred |
| Ticks per generation | **2** | Bound arm default |

Design digest must record `transmission_contract`, `mate_limitation`,
`debit_gain_schedule`, mid windows, ε, and `founder_spatial_policy`.

## 7. Ecology arms and Slowinski contrast (unchanged estimand)

| Ecology arm | Tip passage | Meaning |
|---|---|---|
| `avirulent` | `absent` | Antagonist removal |
| `fixed` | `frozen` | Update off, debit on |
| `copassaged` | `coevolve` | Update on, debit on |

When assay validity and avirulent mid+terminal hold both pass, **seed-level
Slowinski invasion PASS** iff all hold at generation 48:

1. Terminal selfing frequency under `avirulent` **>** intro frequency (0.2).
2. Terminal selfing frequency under `fixed` **>** intro frequency (0.2).
3. Terminal selfing frequency under `copassaged` **≤** intro frequency **and**
   strictly below both `avirulent` and `fixed` terminals.

Otherwise, if both gates pass, the seed is `invasion_fail`. Shared-modifier
census remains refused as primary substrate.

## 8. Locked design constants (this cell set)

| Parameter | Locked value |
|---|---|
| Generations | **48** |
| Mid hold windows (generations) | **16**, **32** |
| Avirulent selfing hold epsilon ε | **0.05** |
| Host N (founders) | **10** |
| Parasite N | **8** |
| Intro selfing frequency | **0.2** |
| Host bit-flip rate | **0.0** |
| Parasite mutation rate | **0.5** |
| Handling time | **0.0** |
| Min viable census | **8** living hosts with mating mode, per arm, at terminal |
| Pass bar (invasion) | **≥6 of 8** seeds with `invasion_pass` |
| Campaign assay-valid bar | **≥6 of 8** seeds with census gate passed |
| Campaign hold bar (reporting) | count of seeds with mid+terminal hold; invasion PASS bar alone decides ecology claim |

### Invasion founders (same multiset as prior locks)

Ordered founders (mating, recognition window):

1. outcross `000111`
2. outcross `000111`
3. outcross `000111`
4. outcross `111000`
5. outcross `111000`
6. outcross `111000`
7. outcross `000111`
8. outcross `111000`
9. selfing `000111`
10. selfing `111000`

Placed under `food_patch_interleaved` on the 4×2 patch set (index \(i\) → patch
\(i \bmod 8\)), preserving founder order.

### Confirmatory seeds (held-out; disjoint from 101–108, 201–208, 301–308, 401–408)

In this order: **501, 502, 503, 504, 505, 506, 507, 508**.

## 9. ClaimGate and ceiling

| Item | Locked rule |
|---|---|
| `red_queen_proved` | false; not promoted |
| `biological_red_queen_proved` | false |
| ClaimGate refuse | must still raise on `red_queen_proved` |
| Ceiling default | `runtime_observation` |
| Ceiling climb above `runtime_observation` | **forbidden** until (a) all ecology arms meet raised `min_viable_census`, (b) avirulent mid+terminal selfing hold passes, and (c) the invasion campaign pass bar holds; then at most `candidate_evidence` |
| Soft-pass \(N=1\) | **rejected** |
| Early-bump-as-baseline | **rejected** |
| Universal selfing purge as ecology Result | **rejected** |
| Soft-green of `7171d19` / seeds 401–408 | **rejected** |
| Soft-green of `91ab0c6` / seeds 301–308 | **rejected** |
| Soft-green / rewrite of `214df20` / seeds 201–208 | **rejected** |
| `last_live` as Slowinski PASS | **rejected** |
| Peek-retune of sealed preregs | **rejected** |
| HP / infection vocabulary in `engine.py` | **rejected** |
| SPC / CPS ownership of accept path or RQ flags | **rejected** (measurement-only; SPC never owns baseline/accept) |
| Two-fold cost of sex | **paid** under this lock; documented; does not authorize RQ |

## 10. Exports required with outcomes

- Typed outcome counts and per-seed table
- `baseline_series_digest` over avirulent selfing frequency series
- Mid-window and terminal selfing frequencies for avirulent
- Whether Slowinski was scored; invasion pass/fail counts
- `engine.py` domain-token scan CLEAN
- Claim ceiling ≤ `runtime_observation` unless hold+invasion bars earned

## 11. What may and may not change after lock

**May:** record typed outcomes, digests, census tables, selfing series,
transmission / mate-limitation audit fields, ClaimGate status; attach Pearl/SPC
measurement only as non-accept evidence.

**May not:** edit this file's locked parameters after seeing outcomes; retune
seeds, ε, mid windows, mate radius, two-fold flag, or debit schedule after peek;
rewrite sealed preregs; narrate `selfing_nonviable` as Slowinski ecology null;
promote RQ flags; put HP domain tokens in `engine.py`.
