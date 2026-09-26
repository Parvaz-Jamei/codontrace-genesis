# Mating ledger, selfing baseline, and debit–birth gain (HP-ARM01-MATING-LEDGER)

**Status:** LOCKED before outcomes. No campaign numbers in this file.  
**Date locked:** 2026-09-26 (Asia/Tehran)  
**Slice names:** `HP-ARM01-MATING-LEDGER`, `HP-ARM01-SELFING-BASELINE`, `HP-ARM01-CLAIMGATE-SELFING-TAXONOMY`, `HP-ARM01-DEBIT-GAIN-ASSURANCE`  
**Estimand (conditional):** `slowinski_selfing_invasion_into_obligate_outcross` — scored only after assay validity **and** avirulent selfing baseline  
**Substrate:** `population_runner_phase_b_host_parasite_env`  
**Revision:** `hp-arm01-mating-ledger-20260926`  
**Code hooks:** `src/codontrace/genesis/closed_loop_hp_arm01_mating.py`  
**Branch context:** `closed-loop/hp-three-arm-frequency-clocks` (PR #65)

This document freezes a **new** confirmatory cell set that repairs the Phase B
mating-mode / selfing transmission hole and the debit↔birth census hole exposed
by the persistence-ledger campaign in
`CLOSED_LOOP_HP_ARM01_PERSISTENCE_LEDGER_PREREG_20260926.md` (commit `91ab0c6`,
outcomes on tip after that lock). That persistence lock and its typed outcomes
(seeds 301–308) are **not** edited, retuned, or soft-passed. The sealed Slowinski
invasion prereg `214df20` (seeds 201–208) is likewise untouched. Last-live series
are not an alternate PASS.

Nosek et al. (Proc. Natl. Acad. Sci. USA 115:2600–2606, 2018,
doi:10.1073/pnas.1708274114) separate prediction from postdiction. Simmons,
Nelson, and Simonsohn (Psychol. Sci. 22:1359–1366, 2011,
doi:10.1177/0956797611417632) motivate writing seeds and pass rules first.
Kriegeskorte et al. (Nat. Neurosci. 12:535–540, 2009, doi:10.1038/nn.2303)
forbid selecting the analysis on the confirming data.

Sealed P7 seeds 101–108 remain untouched.

## 1. Scientific motivation

Under the persistence-ledger lock, generation-boundary resource bolus restored
living generation-48 host census on the avirulent arm (soft \(K=32\)) and made
the three-arm assay valid on most seeds. Terminal selfing frequency was
nevertheless **0.0 on every living arm**, including antagonist removal
(`avirulent`). Fixed-arm terminal census collapsed to 1. That pattern is **not**
a Slowinski ecology contrast. It is a **mating-mode transmission /
reproductive-assurance hole** plus a **debit↔birth gain hole** under
antagonist arms:

1. Selfing founders were placed off the food-patch set while outcross founders
   occupied lumen cells — a spatial starvation confound that purges selfing
   before ecology can be scored.
2. Phase B must guarantee that a selfing genotype transmits without a mate
   (reproductive assurance; Theologidis et al., BMC Biol. 12:93, 2014,
   doi:10.1186/s12915-014-0093-1).
3. Debit-on arms (fixed / copassaged) need a locked virulence×steal versus
   birth/bolus schedule so living census stays well above a scientifically
   defensible finite-\(N\) floor (Papkou et al., Proc. R. Soc. B 288:20212269,
   2021, doi:10.1098/rspb.2021.2269 — small host census constrains adaptation
   and invalidates allele-frequency clocks).
4. `min_viable_census=1` was sexual-assay theater: allele clocks at \(N=1\) are
   invalid. This lock raises the floor and adds typed `selfing_nonviable` so a
   living avirulent deme with terminal selfing 0 is **not** narrated as an
   ecology `invasion_fail`.

HP / infection vocabulary stays in plugin / env / runner modules.
`engine.py` stays domain-free.

## 2. Typed outcomes (ClaimCritic taxonomy)

Every confirmatory seed receives exactly one typed outcome:

| Typed outcome | Meaning |
|---|---|
| `persistence_fail` | Assay invalid: minimum viable census gate failed on any ecology arm. Slowinski estimand **unscored**. |
| `selfing_nonviable` | Census gate passed on all arms, but avirulent terminal selfing frequency is at or below the locked baseline threshold (selfing transmission / reproductive-assurance baseline failed). Slowinski estimand **unscored**. Not an ecology null. |
| `invasion_fail` | Census gate passed **and** avirulent selfing baseline held, but the Slowinski invasion contrast does not hold at generation 48. |
| `invasion_pass` | Census gate passed, avirulent selfing baseline held, and the Slowinski invasion contrast holds at generation 48. |

Refuse packaging universal selfing purge as Slowinski ecology Result.
Refuse soft-green of `91ab0c6` or `214df20`. Refuse `last_live` as PASS.

## 3. Gates (order locked)

Before any Slowinski invasion contrast is scored for a seed:

1. **ASSAY-VALIDITY-GATE (raised census floor).** At terminal generation, each
   ecology arm must have living host mating census ≥ `min_viable_census`
   (**8**). If any arm fails, outcome is `persistence_fail`.
2. **AVIRULENT-SELFING-BASELINE-GATE.** Terminal selfing frequency under
   `avirulent` must be **>** `avirulent_selfing_baseline_min` (**0.0**, i.e.
   strictly positive — at least one living selfing host in a deme that already
   cleared the census floor). If the census gate passed but this baseline
   fails, outcome is `selfing_nonviable` (not `invasion_fail`).
3. **SLOWINSKI BAR.** Only when both gates pass may the locked Slowinski
   invasion contrast be evaluated → `invasion_pass` or `invasion_fail`.

## 4. HP-ARM01-MATING-LEDGER / SELFING-BASELINE (mechanism)

| Parameter | Locked value | Role |
|---|---|---|
| Selfing copy-self mode | `asexual` via existing Phase B `resolve_copy_self_mode` when outcross codon is `000` | Reproductive assurance: no mate required |
| Outcross copy-self mode | `chamber` when outcross codon is `001` | Unchanged Phase B sexual chamber |
| Founder spatial policy | `food_patch_interleaved` | Place founders on the 4×2 food-patch set with mating types interleaved so selfing is not off-patch starved |
| Food patch set | 4×2: \((x,y)\) for \(x\in\{0,1,2,3\}\), \(y\in\{0,1\}\) | Same geometry as persistence bolus patches |
| Outcross mating-effort ATP | **1.0** | Unchanged |
| Two-fold cost of sex | **unpaid** | Documented; Maynard Smith / Hamilton not claimed |

## 5. HP-ARM01-DEBIT-GAIN-ASSURANCE (mechanism)

Locked debit↔birth gain schedule (plugin / arm defaults — not engine infection):

| Parameter | Locked value | Role |
|---|---|---|
| Virulence | **32.0** | Unchanged from prior ecology locks |
| Steal fraction | **0.25** | Lower antagonist ATP drain so debit-on arms can sustain census ≫ floor |
| Birth ATP | **48.0** | Higher birth endowment under debit |
| Resource bolus amount | **20.0** per patch at generation boundary | Persistence refill retained and slightly raised |
| Soft carrying capacity \(K\) | **32** | Unchanged soft ceiling |
| Basal runtime ATP cost | **0.05** | Unchanged |
| Passage refill mode | `generation_boundary_resource_bolus` | Elena–Lenski style; sync `generation_boundary` |
| Thin chemostat ATP inflow | **off** (0.0) | Deferred |
| Ticks per generation | **2** | Bound arm default |

Design digest must record `debit_gain_schedule` (virulence, steal_fraction,
birth_atp, bolus, soft \(K\)) and `founder_spatial_policy=food_patch_interleaved`.

## 6. Ecology arms and Slowinski contrast (unchanged estimand)

| Ecology arm | Tip passage | Meaning |
|---|---|---|
| `avirulent` | `absent` | Antagonist removal |
| `fixed` | `frozen` | Update off, debit on |
| `copassaged` | `coevolve` | Update on, debit on |

When both gates pass, **seed-level Slowinski invasion PASS** iff all hold at
generation 48:

1. Terminal selfing frequency under `avirulent` **>** intro frequency (0.2).
2. Terminal selfing frequency under `fixed` **>** intro frequency (0.2).
3. Terminal selfing frequency under `copassaged` **≤** intro frequency **and**
   strictly below both `avirulent` and `fixed` terminals.

Otherwise, if both gates pass, the seed is `invasion_fail`. Shared-modifier
census remains refused as primary substrate.

## 7. Locked design constants (this cell set)

| Parameter | Locked value |
|---|---|
| Generations | **48** |
| Host N (founders) | **10** |
| Parasite N | **8** |
| Intro selfing frequency | **0.2** |
| Host bit-flip rate | **0.0** |
| Parasite mutation rate | **0.5** |
| Handling time | **0.0** |
| Min viable census | **8** living hosts with mating mode, per arm, at terminal |
| Avirulent selfing baseline min | **0.0** (strictly greater — positive selfing frequency) |
| Pass bar (invasion) | **≥6 of 8** seeds with `invasion_pass` |
| Campaign assay-valid bar | **≥6 of 8** seeds with census gate passed |
| Campaign selfing-baseline bar | **≥6 of 8** seeds with avirulent selfing baseline held (among census-valid) is **not** required for invasion campaign PASS; invasion PASS bar alone decides ecology claim |

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

### Confirmatory seeds (held-out; disjoint from 101–108, 201–208, 301–308)

In this order: **401, 402, 403, 404, 405, 406, 407, 408**.

## 8. ClaimGate and ceiling

| Item | Locked rule |
|---|---|
| `red_queen_proved` | false; not promoted |
| `biological_red_queen_proved` | false |
| ClaimGate refuse | must still raise on `red_queen_proved` |
| Ceiling default | `runtime_observation` |
| Ceiling climb above `runtime_observation` | **forbidden** until (a) all ecology arms meet raised `min_viable_census`, (b) avirulent terminal selfing is strictly positive, and (c) the invasion campaign pass bar holds; then at most `candidate_evidence` |
| Soft-pass \(N=1\) | **rejected** |
| Universal selfing purge as ecology Result | **rejected** |
| Soft-green of `91ab0c6` / seeds 301–308 | **rejected** |
| Soft-green / rewrite of `214df20` / seeds 201–208 | **rejected** |
| `last_live` as Slowinski PASS | **rejected** |
| Peek-retune of sealed preregs | **rejected** |
| HP / infection vocabulary in `engine.py` | **rejected** |
| SPC / CPS ownership of accept path or RQ flags | **rejected** (measurement-only) |
| Two-fold cost of sex | unpaid unless separately implemented and documented |
| Ashby factorial / two-fold cost | **deferred** |

## 9. What may and may not change after lock

**May:** record typed outcomes, digests, census tables, selfing series,
debit-gain audit fields, ClaimGate status; attach Pearl/SPC measurement only
after per-arm clocks exist (measurement-only).

**May not:** retune steal fraction, birth ATP, bolus, soft \(K\), seeds, pass
bars, founders, virulence, generation count, `min_viable_census`, or baseline
threshold after inspecting outcomes; edit sealed persistence or Slowinski
preregs; put infection / host–parasite terms into `engine.py`; invent DOIs;
claim `red_queen_proved`; treat selfing_nonviable as invasion_fail.

## 10. Digests

Design constants are digested by `mating_ledger_design_digest()` in
`closed_loop_hp_arm01_mating.py`. The UTF-8 bytes of this markdown file are
digested by `mating_ledger_document_digest()`. Campaign payloads must record
both digests. Digests are of the lock, not of outcomes.

## 11. Citations

- Theologidis, Chelo, Goy & Teotónio, BMC Biol. 12:93, 2014, doi:10.1186/s12915-014-0093-1
- Papkou, Schalkowski, Barg, Koepper & Schulenburg, Proc. R. Soc. B 288:20212269, 2021, doi:10.1098/rspb.2021.2269
- Elena & Lenski, Nat. Rev. Genet. 4:457–469, 2003, doi:10.1038/nrg1088
- Morran et al., Science 333:216–218, 2011, doi:10.1126/science.1206360
- Slowinski et al., Evolution 70:2632–2639, 2016, doi:10.1111/evo.13048
- Ofria & Wilke, Artif. Life 10:191–229, 2004
- Hamilton, Axelrod & Tanese, Proc. Natl. Acad. Sci. USA 87:3566–3573, 1990, doi:10.1073/pnas.87.9.3566
- Pearl, Biometrika 82:669–688, 1995, doi:10.1093/biomet/82.4.669
- Nosek et al., Proc. Natl. Acad. Sci. USA 115:2600–2606, 2018, doi:10.1073/pnas.1708274114
- Simmons, Nelson & Simonsohn, Psychol. Sci. 22:1359–1366, 2011, doi:10.1177/0956797611417632
- Kriegeskorte et al., Nat. Neurosci. 12:535–540, 2009, doi:10.1038/nn.2303
