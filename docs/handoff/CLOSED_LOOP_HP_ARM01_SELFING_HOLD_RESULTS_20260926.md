# Selfing-hold confirmatory results (HP-ARM01-SELFING-HOLD), 2026-09-26

This file records outcomes for the lock in
`CLOSED_LOOP_HP_ARM01_SELFING_HOLD_PREREG_20260926.md`. The preregistration
file was not edited after the run. Parameters were not retuned.

Prereg commit (before code and outcomes): `f2302ec9c9a913b72aeb75b9c0b8a8c2bcf9fb49`.
Mechanism commit (before confirmatory outcomes): `b3fa5b4b52801d791dc1ccafdd237d6b4c595337`.
Sealed Slowinski prereg `214df20` / persistence prereg `91ab0c6` / mating
ledger prereg `7171d19` / P7 seeds 101–108 were not touched. Prior seeds
201–208, 301–308, and 401–408 were not soft-greened.

## Locked inputs (unchanged after inspection)

48 generations, mid windows 16 and 32, ε=0.05, virulence 32, parasite
mutation 0.5, host N 10, parasite N 8, intro selfing 0.2, birth ATP 48,
selfing birth endowment 48, basal 0.05, soft K 32, steal fraction 0.25,
resource bolus 20.0 on the 4×2 patch set each generation boundary,
founder spatial policy `food_patch_interleaved`, mating-locus lock on,
mate-search radius 1, outcross mates-per-generation cap 1, chamber wait
2 ticks with timeout `fail`, two-fold cost paid, seeds 501–508,
min viable census 8, assay-valid bar 6/8, invasion pass bar 6/8,
substrate `population_runner_phase_b_host_parasite_env`.

## Campaign outcome

| Item | Value |
|---|---|
| Typed outcomes | persistence_fail=0, selfing_nonviable=0, invasion_fail=8, invasion_pass=0 |
| Assay-valid seeds (census ≥8 all arms) | 8 / 8 (bar 6) — PASS |
| Avirulent mid+terminal selfing hold | 8 / 8 |
| Slowinski invasion campaign | scored; invasion_pass=0 / 8 (bar 6) — FAIL |
| Claim ceiling | `runtime_observation` |
| `red_queen_proved` | false |
| `biological_red_queen_proved` | false |
| Two-fold cost of sex | paid (documented; sex≠RQD) |

Design digest: `hp_arm01_selfing_hold_design:762e778bac175b31992fe85572b3ce7057e4727393f23d0622b295ba7a6fd298`

Document digest: `e99a72f47496c8634656453fe31796f60f4498b38ae4db6b3168046e6cc9b575`

Campaign digest: `73e6a52825f92a595c0676f63f81add87f0bbddb080c657e7f42d9a274aa94e6`

Baseline series digest (campaign): `a3ca4af6ea17c5edac2c57d1a4e9cd1fbd0d8761c75883aa9183a8228263c427`

## Seed table

| Seed | Typed outcome | Terminal census avi / fixed / copassaged | Terminal selfing avi / fixed / copassaged | Mid16 / Mid32 / Terminal avi selfing |
|---|---|---|---|---|
| 501 | `invasion_fail` | 32 / 32 / 32 | 0.15625 / 0.59375 / 0.40625 | 0.375 / 0.21875 / 0.15625 |
| 502 | `invasion_fail` | 32 / 32 / 32 | 0.15625 / 0.53125 / 0.40625 | 0.375 / 0.21875 / 0.15625 |
| 503 | `invasion_fail` | 32 / 31 / 32 | 0.15625 / 0.12903225806451613 / 0.5 | 0.375 / 0.21875 / 0.15625 |
| 504 | `invasion_fail` | 32 / 32 / 32 | 0.15625 / 0.46875 / 0.4375 | 0.375 / 0.21875 / 0.15625 |
| 505 | `invasion_fail` | 32 / 32 / 32 | 0.15625 / 0.53125 / 0.46875 | 0.375 / 0.21875 / 0.15625 |
| 506 | `invasion_fail` | 32 / 32 / 32 | 0.15625 / 0.53125 / 0.625 | 0.375 / 0.21875 / 0.15625 |
| 507 | `invasion_fail` | 32 / 30 / 32 | 0.15625 / 0.4666666666666667 / 0.25 | 0.375 / 0.21875 / 0.15625 |
| 508 | `invasion_fail` | 32 / 32 / 32 | 0.15625 / 0.59375 / 0.5 | 0.375 / 0.21875 / 0.15625 |

## Reading

Mode-true selfing birth endowment, mating-locus lock, local density
mate-limitation, and paid two-fold cost restored avirulent mid-horizon and
terminal selfing above ε=0.05 on all eight seeds (hold 8/8). Assay validity
passed on all arms. Slowinski three-arm contrast was therefore **scored**
and failed on every seed: terminal avirulent selfing (~0.156) did not exceed
intro frequency 0.2, so typed outcomes are `invasion_fail` 8/8 — an honest
ecology null after a viable selfing baseline, not `selfing_nonviable` and not
a soft-green. Ceiling stays `runtime_observation`. ClaimGate still refuses
`red_queen_proved`. `engine.py` stays domain-free. SPC does not own accept or
baseline.

Evidence package:
`/workspace/codontrace-genesis-storm/evidence_selfing_hold_20260926/`.
