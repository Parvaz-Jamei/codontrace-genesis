# Slowinski selfing-invasion confirmatory preregistration (HP-ARM01)

**Status:** LOCKED before outcomes. No campaign numbers in this file.  
**Date locked:** 2026-09-26 (Asia/Tehran)  
**Estimand:** `slowinski_selfing_invasion_into_obligate_outcross`  
**Substrate:** `population_runner_phase_b_host_parasite_env`  
**Revision:** `hp-arm01-slowinski-confirm-20260926`  
**Code hooks:** `src/codontrace/genesis/closed_loop_hp_arm01_confirm.py`  
**Branch context:** `closed-loop/hp-three-arm-frequency-clocks` (stacked on Pearl-pair SPC)

This document freezes the confirmatory invasion horizon for the Morran–Slowinski
three-arm ecology path already bound to the CodonTrace life-loop. It was written
before the confirmatory seeds below were run. Nosek et al. (Proc. Natl. Acad.
Sci. USA 115:2600–2606, 2018, doi:10.1073/pnas.1708274114) separate prediction
from postdiction. Parameters must not be retuned after outcomes are seen.
Simmons, Nelson, and Simonsohn (Psychol. Sci. 22:1359–1366, 2011,
doi:10.1177/0956797611417632) are why the seed list and pass bar are written
first. Kriegeskorte et al. (Nat. Neurosci. 12:535–540, 2009,
doi:10.1038/nn.2303) forbid selecting the analysis on the same data used to
confirm it.

Sealed confirmatory seeds 101–108 and the P7 roadmap preregistration
(`CLOSED_LOOP_P7_ROADMAP_PREREG_20260925.md`) are untouched. This file is a
new estimand on the life-loop three-arm path, not a reopen of that campaign.

## 1. Scientific question

In a resident obligate-outcross deme with a low-frequency selfing introduction,
does selfing **invade** under avirulent (antagonist removal) and fixed
(non-coevolving) antagonist regimes, and **stay rare** under copassaged
coevolution?

Primary outcomes are the per-arm **selfing-rate** and **selfing-allele
(recognition-window) frequency** trajectories under the three ecology arms.
The accept contrast is terminal selfing frequency relative to introduction
frequency, not a shared-modifier terminal inequality and not a Red Queen proof.

Morran et al. (Science 333:216–218, 2011, doi:10.1126/science.1206360) used
control / evolution / coevolution treatments on *C. elegans*–*S. marcescens*
and reported obligate-selfing extinction within about twenty generations under
coevolution, with mixed-mating outcrossing rising over about eight generations.
Slowinski et al. (Evolution 70:2632–2639, 2016, doi:10.1111/evo.13048) examined
mixed-mating host populations under coevolving antagonists across multi-generation
experimental-evolution horizons on the order of dozens of generations. Those
horizons motivate the locked generation count below. Short scaffolding
(for example four generations) is refused as confirmatory theater.

Morran outcrossing-maintenance is **secondary** and cannot substitute for a
failed invasion contrast. Shared-modifier census is refused as primary
substrate (Pearl debit knockouts remain measurement-only).

## 2. Ecology arms (locked map)

| Ecology arm | Tip passage | Meaning |
|---|---|---|
| `avirulent` | `absent` | Antagonist removal; not Pearl zero-debit / `costless` |
| `fixed` | `frozen` | Update off, debit on |
| `copassaged` | `coevolve` | Update on, debit on |

`costless` is not an ecology arm on this path.

## 3. Locked design constants

| Parameter | Locked value | Rationale |
|---|---|---|
| Generations | **48** | Dozens-of-generations confirmatory horizon; matches Morran extinction window order (~20) and Slowinski multi-generation experimental evolution; matches the life-loop module threshold that marks shorter runs as deferred scaffold |
| Virulence | **32.0** | Primary debit scale already used for closed-loop ecological signal on this codebase; not searched after outcomes |
| Parasite mutation rate | **0.5** | Default on the already-bound life-loop arm; not retuned to another campaign’s rate after peeking |
| Host bit-flip rate | **0.0** | Host genomic change via sexual crossover of the outcross locus; bit-flip off on this path |
| Host N (founders) | **10** | Invasion founders below |
| Parasite N | **8** | Stock size on the bound arm |
| Intro selfing frequency | **0.2** | 2 selfing / 10 founders |
| Birth ATP | **40.0** | Bound life-loop arm default under basal metabolism |
| Handling time | **0.0** | Primary endpoint; Holling on/off ablation is measurement-only |
| Two-fold cost of sex | **unpaid** (`SexualRecombinationConfig.two_fold_cost_sex=False`) | Mating-effort ATP is paid and documented separately; Maynard Smith / Hamilton two-fold is not claimed (Hamilton, Axelrod & Tanese, Proc. Natl. Acad. Sci. USA 87:3566–3573, 1990, doi:10.1073/pnas.87.9.3566) |
| Ticks per generation | **2** | Bound arm default |
| World | 12×12 with fixed resource patch | Bound arm default |
| Steal fraction | **0.8** | Bound arm default |

### Invasion founders (resident obligate outcross + rare selfing)

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

Intro frequency = 2/10 = 0.2. This multiset is fixed; it is not redesigned after outcomes.

### Confirmatory seeds (held-out; disjoint from sealed 101–108)

In this order: **201, 202, 203, 204, 205, 206, 207, 208**.

Seeds 101–108 remain sealed under the P7 preregistration and are not reused
here. Seeds used only for CI scaffolding on this path are not confirmatory
units.

## 4. Primary outcomes and accept path

For each seed, run all three arms on `PopulationRunner.step_generation` with
Phase B `SEXUAL_CROSSOVER` and per-arm `HostParasiteEnv` contact.

Record per arm, each generation:

- selfing-rate (selfing headcount / (outcross + selfing))
- allele-frequency tables over recognition windows
- genotype, mating-mode, and match-class digest-backed clocks

**Seed-level Slowinski invasion PASS** when all hold at generation 48:

1. Terminal selfing frequency under `avirulent` **>** intro frequency (0.2).
2. Terminal selfing frequency under `fixed` **>** intro frequency (0.2).
3. Terminal selfing frequency under `copassaged` **≤** intro frequency **and**
   strictly below both `avirulent` and `fixed` terminals.

Otherwise the seed is an honest FAIL.

**Campaign PASS** when at least **6 of 8** seeds pass the seed-level contrast.
A 5/8 split is campaign FAIL. Honest FAIL is preferred over soft-pass. No
parameter may be changed after any confirmatory seed is inspected.

Legacy three-frequency terminal inequality is recorded as measurement only and
is **not** Slowinski PASS. Shared-modifier substrate cannot grant PASS.

## 5. ClaimGate and flags

| Item | Locked rule |
|---|---|
| `red_queen_proved` | remains false; not promoted by this campaign |
| `biological_red_queen_proved` | remains false |
| ClaimGate `assert_claim_allowed("red_queen_proved")` | must still raise |
| Reported ceiling | `runtime_observation` unless every gate predicate below holds, then at most `candidate_evidence` |
| Max allowed ceiling | never above what `max_allowed_claim_ceiling` returns |

Gate predicates for any ceiling above observation (all required):

1. Life-loop substrate bound (`population_runner_phase_b_host_parasite_env`)
2. Per-arm frequency clocks complete (not concatenated across arms)
3. Treatment and control arms present
4. Slowinski invasion contrast holds at the campaign pass bar (≥6/8)

Non-empty clock fields alone do not grant `candidate_evidence`. Campaign FAIL
forces ceiling `runtime_observation`.

## 6. What may and may not change after lock

**May:** record outcomes, digests, FAIL/PASS tables, and ClaimGate status;
attach Pearl/SPC measurement only after per-arm clocks exist (measurement-only,
no Red Queen grant).

**May not:** retune generations, virulence, mutation, N, intro frequency,
founders, seeds, or pass bar after seeing outcomes; reopen sealed 101–108 or
edit the P7 prereg; put infection / host–parasite vocabulary into `engine.py`;
add a second population registry; invent DOIs; claim `red_queen_proved`;
treat shared-modifier inequality as Slowinski PASS; soft-green a miss by
shortening the bar or lengthening only the seeds that looked promising.

## 7. Compute note

If the box cannot complete 48 generations × 8 seeds × 3 arms, run the longest
locked horizon that completes **without changing other locked constants**,
document the compute limit, and treat unmet bars as FAIL. Do not fall back to
four-generation theater while calling the run confirmatory.

## 8. Digests

Design constants are digested by
`slowinski_confirm_design_digest()` in
`closed_loop_hp_arm01_confirm.py`. The UTF-8 bytes of this markdown file are
digested by `slowinski_confirm_document_digest()`. Campaign payloads must
record both digests. Digests are of the lock, not of outcomes.

## 9. Citations used (already in the closed-loop literature ledger)

- Morran et al., Science 333:216–218, 2011, doi:10.1126/science.1206360
- Slowinski et al., Evolution 70:2632–2639, 2016, doi:10.1111/evo.13048
- Hamilton, Axelrod & Tanese, Proc. Natl. Acad. Sci. USA 87:3566–3573, 1990, doi:10.1073/pnas.87.9.3566
- Pearl, Biometrika 82:669–688, 1995, doi:10.1093/biomet/82.4.669
- Nosek et al., Proc. Natl. Acad. Sci. USA 115:2600–2606, 2018, doi:10.1073/pnas.1708274114
- Simmons, Nelson & Simonsohn, Psychol. Sci. 22:1359–1366, 2011, doi:10.1177/0956797611417632
- Kriegeskorte et al., Nat. Neurosci. 12:535–540, 2009, doi:10.1038/nn.2303
