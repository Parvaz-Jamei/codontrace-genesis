# Structural RQ regime pilot results (HP-ARM01-STRUCTURAL-RQ-REGIME), 2026-09-26

This file records outcomes for the lock in
`CLOSED_LOOP_HP_ARM01_STRUCTURAL_RQ_REGIME_PREREG_20260926.md`. The
preregistration file was not edited after the run. Parameters were not
retuned after seeing outcomes.

Prereg lock (final pre-mechanism): `645e68d91c133888f226f402f75977ded7f5248d`.
Mechanism commit (before confirmatory outcomes): `dd3891cc62649858f7c02db5b49a6e17bbf2dd17`.
Sealed Slowinski prereg `214df20` / persistence prereg `91ab0c6` / mating
ledger prereg `7171d19` / P7 seeds 101–108 / selfing-hold seeds 501–508 were
not touched. Mating and Slowinski remain deferred and unscored.

## Locked inputs (unchanged after inspection)

250 generations; locked windows 50, 125, 250; \(R_{\min}=3\); \(\varepsilon=0.15\);
host \(N=K=64\); parasite \(N=64\); 16 distinct match-state founders; host
bit-flip 0.02; 3×2-bit graded feature-overlap debit (AND-collapse forbidden);
\(\kappa=0.5\); parasite mutation 0.25; virulence 8.0; steal 0.15; birth ATP 48;
bolus 20.0 on 4×4 patches; asexual substrate (mating deferred); seeds 601–603;
min viable census 12 (demographic floor only, not \(N_e\) proxy); substrate
`population_runner_phase_b_host_parasite_env`.

## Campaign outcome

| Item | Value |
|---|---|
| Typed outcomes | polymorphism_hold=1, regime_hostile_ne=2, sweep_fixation=0, cycle_candidate=0, horizon_insufficient=0, parasite_extinct=0, selfing_nonviable=0, Slowinski_unscored=0, regime_hostile_turnover=0 |
| Primary success (`polymorphism_hold`) | 1 / 3 |
| `cycle_candidate` (observation-only) | 0 / 3 |
| Slowinski scored | **no** (deferred) |
| Claim ceiling | `candidate_evidence` |
| `red_queen_proved` | false |
| `biological_red_queen_proved` | false |

Design digest: `hp_arm01_structural_rq_design:15d253a27dff77170ce11ac1c0a6cbb359e92f0d1fd8f1af7219f6fb0a49faf3`

Document digest: `6dfab2b520f197fd65e7b8077acf21bf4f53fe453392e4abbc79604e0733fc20`

Campaign digest: `6105e5f38e5f38ccc5f5e423636fe1f08c68aa1884c3762d289d629d2f7ce1b6`

## Seed table

| Seed | Typed outcome | Terminal census avi / fixed / copassaged | Notes |
|---|---|---|---|
| 601 | `polymorphism_hold` | 55 / 14 / 28 | ceiling `candidate_evidence` |
| 602 | `regime_hostile_ne` | 40 / 20 / 11 | ceiling `runtime_observation` |
| 603 | `regime_hostile_ne` | 53 / 5 / 29 | ceiling `runtime_observation` |

## Reading

Stage A–D structural stack (large \(N\), multi-locus graded debit, mid-\(\kappa\)
turnover, 250-gen horizon) was run under the NEW prereg. Primary success this
wave is `polymorphism_hold` only. Seed 601 met mid+terminal multi-class hold on
debit-active arms (match-class richness and dominance gates). Seeds 602 and 603
are typed `regime_hostile_ne` because living census on a debit-active arm fell
below the demographic floor at a locked window — body census is not \(N_e\), but
series readability failed. No seed earned `cycle_candidate`. Slowinski was not
scored. Ceiling may sit at `candidate_evidence` after a hold seed; it does not
authorize `red_queen_proved`. Sealed FAILS were not soft-greened.

Evidence package:
`/workspace/codontrace-genesis-storm/evidence_structural_rq_20260926/`.
