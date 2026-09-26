# Slowinski invasion confirmatory results (HP-ARM01), 2026-09-26

This file records outcomes for the lock in
`CLOSED_LOOP_HP_ARM01_SLOWINSKI_INVASION_PREREG_20260926.md`. The preregistration
file was not edited after the run. Parameters were not retuned.

Prereg commit (before outcomes): `214df201438338e0a803201d284d4d1a8f091fb2`.
Sealed P7 seeds 101–108 and
`CLOSED_LOOP_P7_ROADMAP_PREREG_20260925.md` were not touched.

## Locked inputs (unchanged)

48 generations, virulence 32, parasite mutation 0.5, host N 10, parasite N 8,
intro selfing frequency 0.2, birth ATP 40, handling time 0, seeds 201–208,
pass bar 6 of 8, substrate `population_runner_phase_b_host_parasite_env`,
two-fold cost of sex unpaid.

## Campaign outcome

| Item | Value |
|---|---|
| Overall Slowinski invasion | **FAIL** |
| Seeds passed | 0 / 8 |
| Claim ceiling | `runtime_observation` |
| `red_queen_proved` | false |
| `biological_red_queen_proved` | false |
| Two-fold cost of sex | unpaid |

Every seed failed the seed-level contrast because terminal selfing frequencies
at generation 48 were undefined: living host mating census reached zero by
about generation index 14 on all three arms, including `avirulent`. Last-live
selfing frequencies just before extinction were typically 0.0. That pattern is
descriptive only; it is not an alternate PASS.

Design digest:
`hp_arm01_slowinski_design:b47f73e2598ae711fe78d8913111866fd3bdc5d3d778fd9b43459112c25955a8`

Document digest:
`844f8b3ebfe1cd986fcadb574e1a807cd5d9de5ade3cc89d2aea62ad7e8cfc69`

Campaign digest:
`cb8f127b74707b80c183e44425e15fe51fcfd1c15d978f66f71263f6cc63af06`

## Seed table

| Seed | Passed | Terminal avi / fixed / copassaged |
|---|---|---|
| 201 | no | None / None / None |
| 202 | no | None / None / None |
| 203 | no | None / None / None |
| 204 | no | None / None / None |
| 205 | no | None / None / None |
| 206 | no | None / None / None |
| 207 | no | None / None / None |
| 208 | no | None / None / None |

## Reading

The confirmatory bar was unmet. Honest FAIL is the result. Early deme collapse
under the locked birth ATP and basal metabolism, including without antagonists,
is a substrate limit for this lock. A later amendment would need its own
preregistration before any new seeds; this campaign does not authorize one.
`engine.py` stays domain-free. ClaimGate still refuses `red_queen_proved`.

Evidence package (outside the git tree for the storm handoff):
`/workspace/codontrace-genesis-storm/evidence_confirm_slowinski_20260926/`.
