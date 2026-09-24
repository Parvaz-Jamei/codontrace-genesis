# FINAL_REPORT — open_problem_20260925 (time-shift FRQ vs ERQ)

**Date:** 2026-09-25 (Asia/Tehran)  
**Repo tip before campaign:** `c56dada` (engine gates green)
**Campaign tip:** `41ced3e1ba46d033ed9579322bb29026e09756c7`  
**Chosen problem:** oscillatory Red Queen vs arms-race discrimination via in-loop time-shift assay  
**Verified DOIs:** `10.1038/nature06291`, `10.1098/rspb.2014.1382`, `10.1111/jeb.13981`

## Innovation mechanism

`life_loop.time_shift_assay` — CohortArchive during the loop + cross-temporal
match panel + `match_linked_cycle` / `trait_escalation` generative arms.
Not a new meter on frozen outputs. Infection physics remain out of `engine.py`.

## Test outcomes (honest)

| ID | Engineering | hypothesis_supported | Result |
|---|---|---|---|
| SF_TS1 time-shift FRQ/ERQ discrimination | PASS | True | PASS |
| SF_TS2 live HostParasiteWorld genome archive witness | PASS | False | PASS |

- SF_TS1: 8/8 seeds `peak_contemp` on cycle; 8/8 `mono_rise` on escalation;
  content/structure/dual nulls flat 8/8. Ceiling `candidate_evidence`.
- SF_TS2: live demography archives run; **no** FRQ/ERQ claim
  (`hypothesis_supported=False`). Ceiling `runtime_observation`.

## ClaimGate

Refuses retained: `red_queen_proved`, `arms_race_proved`, `causality_proved`,
`intervention_supported`. No ClaimGate softening.

## One-sentence falsification vs still-closed claim

**Falsified:** the claim that this engine cannot host an in-loop time-shift
assay that structurally separates tracking-cycle (`peak_contemp`) from
escalation (`mono_rise`) under content/structure/dual nulls at
`candidate_evidence`. **Still closed:** `red_queen_proved` / wet FRQ–ERQ
identity / causality from demography-alone live worlds.

## Artifacts

- `docs/campaigns/open_problem_20260925/PROBLEM.md`
- `docs/campaigns/open_problem_20260925/FINAL_REPORT.md`
- `src/codontrace/life_loop/time_shift_assay.py`
- `src/codontrace/genesis/campaigns/open_problem_20260925_time_shift.py`
- `tests/campaigns/open_problem_20260925/`
- `outputs/campaigns/open_problem_20260925/results.json`
