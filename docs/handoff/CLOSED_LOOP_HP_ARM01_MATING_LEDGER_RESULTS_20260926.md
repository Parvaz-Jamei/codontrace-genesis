# Mating ledger confirmatory results (HP-ARM01-MATING-LEDGER), 2026-09-26

This file records outcomes for the lock in
`CLOSED_LOOP_HP_ARM01_MATING_LEDGER_PREREG_20260926.md`. The preregistration
file was not edited after the run. Parameters were not retuned.

Prereg commit (before code and outcomes): `7171d1950122934cf36da61463b1b0107dad4d2c`.
Mechanism commit (before confirmatory outcomes): `1a22a57ef04c93379bf53ab0dd5de0685b1743d9`.
Sealed Slowinski prereg `214df20` / persistence prereg `91ab0c6` / P7 seeds
101–108 were not touched. Prior seeds 201–208 and 301–308 were not soft-greened.

## Locked inputs (unchanged after inspection)

48 generations, virulence 32, parasite mutation 0.5, host N 10, parasite N 8,
intro selfing 0.2, birth ATP 48, basal 0.05, soft K 32, steal fraction 0.25,
resource bolus 20.0 on the 4×2 patch set each generation boundary
(`passage_refill_sync=generation_boundary`), founder spatial policy
`food_patch_interleaved`, thin chemostat ATP inflow off, handling time 0,
seeds 401–408, min viable census 8, avirulent selfing baseline strictly
positive, assay-valid bar 6/8, invasion pass bar 6/8, two-fold cost unpaid,
substrate `population_runner_phase_b_host_parasite_env`.

## Campaign outcome

| Item | Value |
|---|---|
| Typed outcomes | persistence_fail=0, selfing_nonviable=8, invasion_fail=0, invasion_pass=0 |
| Assay-valid seeds (census ≥8 all arms) | 8 / 8 (bar 6) — PASS |
| Avirulent selfing baseline held | 0 / 8 |
| Slowinski invasion campaign | unscored (0 / 8); FAIL as ecology claim |
| Claim ceiling | `runtime_observation` |
| `red_queen_proved` | false |
| `biological_red_queen_proved` | false |
| Two-fold cost of sex | unpaid |
| Debit-arm terminal census | fixed and copassaged ≥30 on all seeds (≫ raised floor) |

Design digest: `hp_arm01_mating_design:f4475f69032423aa99e86cae9d4e88bc6d1cc2026aadd52f8a89b3eaa32d80dd`

Document digest: `b056da3d8ccd4e4066ad820c5dfe6b73529d680c1b693b696ae4871c9745f9e0`

Campaign digest: `72f59eff61ee02905efd075ba08b908c42368bb4079a96eecefc3ad53910f0a5`

## Seed table

| Seed | Typed outcome | Terminal census avi / fixed / copassaged | Terminal selfing avi / fixed / copassaged |
|---|---|---|---|
| 401 | `selfing_nonviable` | 32 / 31 / 31 | 0.0 / 0.0 / 0.0 |
| 402 | `selfing_nonviable` | 32 / 31 / 31 | 0.0 / 0.0 / 0.0 |
| 403 | `selfing_nonviable` | 32 / 32 / 30 | 0.0 / 0.125 / 0.0 |
| 404 | `selfing_nonviable` | 32 / 32 / 32 | 0.0 / 0.0 / 0.0 |
| 405 | `selfing_nonviable` | 32 / 32 / 31 | 0.0 / 0.0 / 0.0 |
| 406 | `selfing_nonviable` | 32 / 31 / 31 | 0.0 / 0.0 / 0.0 |
| 407 | `selfing_nonviable` | 32 / 32 / 32 | 0.0 / 0.0 / 0.0 |
| 408 | `selfing_nonviable` | 32 / 31 / 30 | 0.0 / 0.0 / 0.0 |

## Reading

Debit↔birth gain plus passage refill restored living generation-48 host census
well above the raised floor of 8 on all three arms for every seed (including
debit-on fixed and copassaged). That closes the prior N=1 sexual-assay theater
for this cell set. Terminal selfing frequency on the avirulent arm was 0.0 on
all eight seeds, so every seed is typed `selfing_nonviable` — the avirulent
reproductive-assurance baseline failed before the Slowinski bar. These are
**not** packaged as ecology `invasion_fail`. Ceiling stays
`runtime_observation`. ClaimGate still refuses `red_queen_proved`. `engine.py`
stays domain-free.

Evidence package:
`/workspace/codontrace-genesis-storm/evidence_mating_ledger_20260926/`.
