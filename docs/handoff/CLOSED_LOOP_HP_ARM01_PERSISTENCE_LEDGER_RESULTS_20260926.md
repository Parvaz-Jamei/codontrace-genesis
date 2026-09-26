# Persistence ledger confirmatory results (HP-ARM01-PASSAGE-REFILL), 2026-09-26

This file records outcomes for the lock in
`CLOSED_LOOP_HP_ARM01_PERSISTENCE_LEDGER_PREREG_20260926.md`. The preregistration
file was not edited after the run. Parameters were not retuned.

Prereg commit (before code and outcomes): `91ab0c60016dc664364ebd69a94e2711df093daf`.
Mechanism commit (before confirmatory outcomes): `d50a2eb8661175233aa4a0956f2a59014a673897`.
Sealed Slowinski prereg `214df20` / outcomes `ecdc3fe` and P7 seeds 101–108 were
not touched. Prior seeds 201–208 remain assay_invalid / persistence_fail under
that lock; they were not soft-greened.

## Locked inputs (unchanged after inspection)

48 generations, virulence 32, parasite mutation 0.5, host N 10, parasite N 8,
intro selfing 0.2, birth ATP 40, basal 0.05, soft K 32, resource bolus 16.0 on
the 4×2 patch set each generation boundary (`passage_refill_sync=generation_boundary`),
thin chemostat ATP inflow off, handling time 0, seeds 301–308, min viable census 1,
assay-valid bar 6/8, invasion pass bar 6/8, two-fold cost unpaid, substrate
`population_runner_phase_b_host_parasite_env`.

## Campaign outcome

| Item | Value |
|---|---|
| Typed outcomes | persistence_fail=2, invasion_fail=6, invasion_pass=0 |
| Assay-valid seeds | 6 / 8 (bar 6) — PASS |
| Slowinski invasion campaign | FAIL (0 / 8) |
| Claim ceiling | `runtime_observation` |
| `red_queen_proved` | false |
| `biological_red_queen_proved` | false |
| Two-fold cost of sex | unpaid |
| Demes reach living gen-48 | yes on avirulent for all 8 seeds; assay-valid on 6/8 (copassaged extinct on 304–305) |

Design digest: `hp_arm01_persistence_design:ce8d7b7d2d9d62515040497a1a785a65ee0df873d9982e5155056c76bfa4cc22`

Document digest: `f3ce8523bf6350b53548dd4db47cd0b97041cd4f536b9d23e437aac141057d8c`

Campaign digest: `9a28aefa978e0b4603ccf07a076af6e2b9b5eea29d90b43d619ae0d8bf56e2f0`

## Seed table

| Seed | Typed outcome | Terminal census avi / fixed / copassaged | Terminal selfing avi / fixed / copassaged |
|---|---|---|---|
| 301 | `invasion_fail` | 32 / 1 / 22 | 0.0 / 0.0 / 0.0 |
| 302 | `invasion_fail` | 32 / 1 / 22 | 0.0 / 0.0 / 0.0 |
| 303 | `invasion_fail` | 32 / 1 / 1 | 0.0 / 0.0 / 0.0 |
| 304 | `persistence_fail` | 32 / 1 / 0 | 0.0 / 0.0 / None |
| 305 | `persistence_fail` | 32 / 1 / 0 | 0.0 / 0.0 / None |
| 306 | `invasion_fail` | 32 / 1 / 21 | 0.0 / 0.0 / 0.0 |
| 307 | `invasion_fail` | 32 / 1 / 27 | 0.0 / 0.0 / 0.0 |
| 308 | `invasion_fail` | 32 / 1 / 21 | 0.0 / 0.0 / 0.0 |

## Reading

Passage refill restored living generation-48 host census on the avirulent arm
for every seed and on all three arms for six of eight seeds. Where the assay
validity gate failed (seeds 304–305), the typed outcome is `persistence_fail`
and Slowinski remains unscored. Where the gate passed, terminal selfing
frequencies were 0.0 on all arms, so the invasion contrast is an honest
`invasion_fail` — not a soft-pass via last_live. Ceiling stays
`runtime_observation`. ClaimGate still refuses `red_queen_proved`. `engine.py`
stays domain-free.

Evidence package:
`/workspace/codontrace-genesis-storm/evidence_persistence_ledger_20260926/`.
