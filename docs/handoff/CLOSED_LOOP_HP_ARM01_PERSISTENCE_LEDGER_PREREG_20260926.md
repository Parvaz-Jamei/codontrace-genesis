# Host persistence ledger and passage refill (HP-ARM01-PERSISTENCE-LEDGER)

**Status:** LOCKED before outcomes. No campaign numbers in this file.  
**Date locked:** 2026-09-26 (Asia/Tehran)  
**Slice names:** `HP-ARM01-PERSISTENCE-LEDGER`, `HP-ARM01-PASSAGE-REFILL`, `ASSAY-VALIDITY-GATE`  
**Estimand (conditional):** `slowinski_selfing_invasion_into_obligate_outcross` — scored only after assay validity  
**Substrate:** `population_runner_phase_b_host_parasite_env`  
**Revision:** `hp-arm01-persistence-ledger-20260926`  
**Code hooks:** `src/codontrace/genesis/closed_loop_hp_arm01_persistence.py`  
**Branch context:** `closed-loop/hp-three-arm-frequency-clocks` (PR #65)

This document freezes a **new** confirmatory cell set that repairs the host
persistence / birth–ATP ledger hole exposed by the locked Slowinski invasion
horizon in
`CLOSED_LOOP_HP_ARM01_SLOWINSKI_INVASION_PREREG_20260926.md` (commit
`214df20`). That prior lock and its sealed outcomes (seeds 201–208; honest
FAIL with early deme collapse on all arms including avirulent) are **not**
edited, retuned, or soft-passed. Last-live selfing series from that campaign
are not an alternate PASS.

Nosek et al. (Proc. Natl. Acad. Sci. USA 115:2600–2606, 2018,
doi:10.1073/pnas.1708274114) separate prediction from postdiction. Simmons,
Nelson, and Simonsohn (Psychol. Sci. 22:1359–1366, 2011,
doi:10.1177/0956797611417632) motivate writing seeds and pass rules first.
Kriegeskorte et al. (Nat. Neurosci. 12:535–540, 2009, doi:10.1038/nn.2303)
forbid selecting the analysis on the confirming data.

Sealed P7 seeds 101–108 and `CLOSED_LOOP_P7_ROADMAP_PREREG_20260925.md` remain
untouched.

## 1. Scientific motivation

Under the prior Slowinski lock (birth ATP 40, basal metabolism on, one-shot
world resources, no generation-boundary refill), living host mating census
reached zero by about generation index 14 on **all three** ecology arms,
including antagonist removal (`avirulent`). Terminal generation-48 selfing
frequencies were therefore undefined. That pattern is a **substrate / ledger**
failure for the invasion assay, not a scored Slowinski contrast miss.

Experimental microbial evolution routinely restores resources at transfer
boundaries. Elena and Lenski (Nat. Rev. Genet. 4:457–469, 2003,
doi:10.1038/nrg1088) describe serial-transfer (serial-dilution) regimes in
which a fresh resource bolus accompanies each passage. Chemostat-style
continuous inflow is the thin alternative (Ofria & Wilke, Artif. Life
10:191–229, 2004; Cooper & Ofria limited-resource ecosystems). This lock
adopts a **generation-boundary resource bolus** (Elena–Lenski passage refill)
as the primary persistence mechanism, with soft carrying capacity, on the
existing life-loop ATP / world ledger — without placing host–parasite
vocabulary into `engine.py`.

## 2. Typed outcomes (ClaimCritic)

Every confirmatory seed receives exactly one typed outcome:

| Typed outcome | Meaning |
|---|---|
| `persistence_fail` | Assay invalid: minimum viable census gate failed before the invasion contrast is eligible. Slowinski estimand **unscored**. |
| `invasion_fail` | Assay valid, but the Slowinski invasion contrast does not hold at generation 48. |
| `invasion_pass` | Assay valid, and the Slowinski invasion contrast holds at generation 48. |

The prior locked campaign (seeds 201–208) is classified retroactively as
**assay_invalid / `persistence_fail`**, not as an invasion scientific null.
This new lock must not soft-green that prior prereg, must not treat
`last_live` series as PASS, and must not promote persistence rescue as Red
Queen proof or Slowinski proof.

## 3. ASSAY-VALIDITY-GATE (minimum viable census)

Before any Slowinski invasion contrast is scored for a seed:

1. Run all three ecology arms (`avirulent`, `fixed`, `copassaged`) for the
   locked generation horizon on the life-loop substrate.
2. At the **terminal** generation, each arm must have living host mating
   census ≥ `min_viable_census` (outcross + selfing headcount).
3. If any arm fails that gate, the seed outcome is `persistence_fail`
   (assay_invalid). Invasion frequencies may be recorded as descriptive
   nulls; they do **not** grant `invasion_fail` or `invasion_pass`.
4. Only when the gate passes on all three arms may the locked Slowinski
   invasion contrast be evaluated, yielding `invasion_pass` or
   `invasion_fail`.

`last_live` selfing frequency before extinction is measurement-only and
never substitutes for a terminal living census.

## 4. HP-ARM01-PASSAGE-REFILL (persistence mechanism)

| Parameter | Locked value | Role |
|---|---|---|
| Passage refill mode | `generation_boundary_resource_bolus` | Elena–Lenski serial-transfer style |
| Food patch set | 4×2 cells: \((x,y)\) for \(x\in\{0,1,2,3\}\), \(y\in\{0,1\}\) | Same patch geometry as the bound arm’s initial placement |
| Resource bolus amount | **16.0** per patch, applied each generation **before** `PopulationRunner.step_generation` | Fresh lumen resource at the generation boundary |
| Soft carrying capacity \(K\) | **32** (`ReproductionConfig.max_population`) | Soft census ceiling; not a hard kill switch outside reproduction |
| Birth ATP | **40.0** | Unchanged from the prior Slowinski lock’s birth endowment |
| Basal runtime ATP cost | **0.05** | Unchanged MetabolicConfig on the bound arm |
| Ticks per generation | **2** | Bound arm default |
| Thin chemostat ATP inflow | **off** (0.0) | Deferred; resource bolus is the chosen smallest honest change |
| Two-fold cost of sex | **unpaid** | Documented; Maynard Smith / Hamilton not claimed |
| CPS / SPC ownership | Measurement-only; **never** owns accept path or Red Queen flags | Fail-closed clauses only after per-arm clocks exist |

**CPS refill sync (declared):** the resource bolus is applied at the
**generation boundary**, in lockstep with the same generation index that
drives passage update, HostParasiteEnv contact, and mating census. The
design digest must record
`passage_refill_sync=generation_boundary` together with bolus amount, patch
set, and soft \(K\). SPC/CUSUM/observer predicates do not own the accept
path and do not write `red_queen_proved`.

Birth / basal ATP audit fields (locked report schema):

- `birth_atp`
- `basal_runtime_atp_cost`
- `passage_refill_mode`
- `resource_bolus_amount`
- `soft_carrying_capacity`
- `cumulative_resource_bolus_placed` (per arm)
- `terminal_host_census_by_arm`
- `assay_valid`
- `typed_outcome`

## 5. Ecology arms and Slowinski contrast (unchanged estimand)

Arm map unchanged from the life-loop bind:

| Ecology arm | Tip passage | Meaning |
|---|---|---|
| `avirulent` | `absent` | Antagonist removal |
| `fixed` | `frozen` | Update off, debit on |
| `copassaged` | `coevolve` | Update on, debit on |

When assay-valid, **seed-level Slowinski invasion PASS** if and only if all
hold at generation 48:

1. Terminal selfing frequency under `avirulent` **>** intro frequency (0.2).
2. Terminal selfing frequency under `fixed` **>** intro frequency (0.2).
3. Terminal selfing frequency under `copassaged` **≤** intro frequency **and**
   strictly below both `avirulent` and `fixed` terminals.

Otherwise, if assay-valid, the seed is `invasion_fail`. Shared-modifier
census remains refused as primary substrate. Morran outcrossing maintenance
is secondary.

## 6. Locked design constants (this cell set)

| Parameter | Locked value |
|---|---|
| Generations | **48** |
| Virulence | **32.0** |
| Parasite mutation rate | **0.5** |
| Host bit-flip rate | **0.0** |
| Host N (founders) | **10** |
| Parasite N | **8** |
| Intro selfing frequency | **0.2** |
| Handling time | **0.0** |
| Steal fraction | **0.8** |
| World | 12×12 with generation-boundary bolus on the 4×2 patch set |
| Min viable census | **1** living host with mating mode, per arm, at terminal |
| Pass bar (invasion) | **≥6 of 8** assay-valid seeds with `invasion_pass` |
| Campaign persistence bar | **≥6 of 8** seeds assay-valid (`persistence_fail` count ≤2) |

### Invasion founders (same multiset as prior Slowinski lock)

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

### Confirmatory seeds (held-out; disjoint from 101–108 and 201–208)

In this order: **301, 302, 303, 304, 305, 306, 307, 308**.

## 7. ClaimGate and ceiling

| Item | Locked rule |
|---|---|
| `red_queen_proved` | false; not promoted |
| `biological_red_queen_proved` | false |
| ClaimGate refuse | must still raise on `red_queen_proved` |
| Ceiling while any seed is assay-invalid, or invasion campaign unmet | `runtime_observation` |
| Ceiling climb above `runtime_observation` | **forbidden** until living generation-48 census exists on treatment and control demes **and** the invasion campaign pass bar holds; then at most `candidate_evidence` |
| Persistence rescue as RQ / Slowinski proof | **rejected** |
| Soft-green of prereg `214df20` / seeds 201–208 | **rejected** |
| `last_live` as Slowinski PASS | **rejected** |
| HP / infection vocabulary in `engine.py` | **rejected** |
| Second population registry | **rejected** |
| Two-fold cost of sex | unpaid unless separately implemented and documented |

## 8. What may and may not change after lock

**May:** record typed outcomes, digests, census tables, birth/basal audit
fields, ClaimGate status; attach Pearl/SPC measurement only after per-arm
clocks exist (measurement-only).

**May not:** retune bolus amount, soft \(K\), birth ATP, basal cost, seeds,
pass bars, founders, virulence, or generation count after inspecting
outcomes; edit the sealed Slowinski prereg or P7 prereg; put infection /
host–parasite terms into `engine.py`; invent DOIs; claim `red_queen_proved`;
treat persistence alone as invasion PASS.

## 9. Digests

Design constants are digested by `persistence_ledger_design_digest()` in
`closed_loop_hp_arm01_persistence.py`, including
`passage_refill_sync=generation_boundary`. The UTF-8 bytes of this markdown
file are digested by `persistence_ledger_document_digest()`. Campaign
payloads must record both digests. Digests are of the lock, not of outcomes.

## 10. Citations

- Elena & Lenski, Nat. Rev. Genet. 4:457–469, 2003, doi:10.1038/nrg1088
- Morran et al., Science 333:216–218, 2011, doi:10.1126/science.1206360
- Slowinski et al., Evolution 70:2632–2639, 2016, doi:10.1111/evo.13048
- Ofria & Wilke, Artif. Life 10:191–229, 2004
- Hamilton, Axelrod & Tanese, Proc. Natl. Acad. Sci. USA 87:3566–3573, 1990, doi:10.1073/pnas.87.9.3566
- Pearl, Biometrika 82:669–688, 1995, doi:10.1093/biomet/82.4.669
- Nosek et al., Proc. Natl. Acad. Sci. USA 115:2600–2606, 2018, doi:10.1073/pnas.1708274114
- Simmons, Nelson & Simonsohn, Psychol. Sci. 22:1359–1366, 2011, doi:10.1177/0956797611417632
- Kriegeskorte et al., Nat. Neurosci. 12:535–540, 2009, doi:10.1038/nn.2303
