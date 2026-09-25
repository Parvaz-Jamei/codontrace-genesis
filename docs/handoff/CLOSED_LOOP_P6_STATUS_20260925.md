# Closed-loop P6 status — 2026-09-25

Numbers from this tree: [CLOSED_LOOP_MEASUREMENTS_20260925.md](CLOSED_LOOP_MEASUREMENTS_20260925.md).

Scope: matching-allele contact on the existing ATP clock. The design lock is
[CLOSED_LOOP_P6_STORM_20260925.md](CLOSED_LOOP_P6_STORM_20260925.md).

## The unsolved measurement

Repeating Morran is not the open problem. Otto and Nuismer (Science 2004,
doi:10.1126/science.1094072) showed interactions usually select against sex.
Ashby (J. Evol. Biol. 2020, doi:10.1111/jeb.13718) showed a parasite can keep
sex without Red Queen cycling. The engine-shaped question is the storm's:
on the ledger that already charges a mating fee, for which Holling debit does
outcrossing persist and selfing disappear only while specificity is passaged
and type sets cycle?

## What was wired

`host_parasite_type2_rq.py` still owns the Euler stepper. P6 does not call it.
A match debits `virulence * H / (1 + H)` (Holling type II) from
`GenesisOrganism.atp_state` with reason `p6_match_cost`. Outcross children also
pay `outcross_runtime_cost` through the existing fee function. Selfing pays
none. `assert_single_atp_owner` runs every generation. `engine.py` is untouched.

Outcross children come from `apply_positional_segment_exchange` on bits
`[18:21)`. `coevolve` sets the antagonist window to the modal living host
window. `frozen` keeps the ancestral window. `absent` does not debit.

## The measured answer

The name-set at virulence 32 still alternates
`({000000,111111}, {000111,111000})` under outcross × coevolve. Match debits
on that arm are `2, 0, 0, 0`. `frequency_cycles` sees the names.
`debit_backed_cycle` does not, because generations 1–3 pay nothing. That is
the witness, not an onset. `debit_threshold` is unset. `pattern_holds` is
false. `red_queen_proved` is false. `biological_red_queen_proved` is false.
`assert_claim_allowed("red_queen_proved")` still raises. Ceiling is
`runtime_observation`.

## Accept

`tests/closed_loop/test_closed_loop_p6_accept.py`
