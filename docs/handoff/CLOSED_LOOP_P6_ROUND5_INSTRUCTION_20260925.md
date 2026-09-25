# P6 retraction instruction

Five rounds, 2026-09-25. This note overrides the claim in
`CLOSED_LOOP_P6_STATUS_20260925.md` that `red_queen_proved` is true because
the storm rule held. The storm note still says the flag stays false. No code
in this commit. The patch below is the instruction, not an implementation.

## What failed

The factorial sets `red_queen_proved` true at virulence 32. That contradicts
the storm note.

Holling type II at virulence 32 costs 16 when H=1, above birth ATP 10. Every
match is lethal. The curve is not identified. It is not a force of infection.

The coevolve gap is already present at virulence 20, off the declared grid.
Locking `debit_threshold == 32` is the next label on that grid, not the onset.
Kriegeskorte et al. 2009, Nature Neuroscience 12:535–540,
doi:10.1038/nn.2303: a cutoff selected on the same run and then asserted there
is circular.

Outcross × coevolve, generations 1–3, alternates `{000000,111111}` with
`{000111,111000}` and takes no `p6_match_cost`. That is the square of a
first-codon exchange. `frequency_cycles` keys on name-sets and ignores counts.
Checked on this tree: coevolve at 32 pays 2, 0, 0, 0 match debits by
generation. Frozen at 16 pays 2, 1, 0, 1: a debit on every generation whose
name-set still contains ancestral `000111`, including generation 0, not only
on generations 1 and 3. The name-set still alternates there.

`absent` skips the window update as well as the debit, so it is not
`do(debit=0)` (Pearl 1995, doi:10.1093/biomet/82.4.669). That split is not
this patch.

Mating is an arm label. Pure outcross versus pure selfing is not selection on
a modifier. A cycle or an extinction is not by itself the maintenance of sex
(Ashby 2020, doi:10.1111/jeb.13718).

The module docstring cites Agrawal 2006 parental exposure. The contact rule
does not read the parent. Do not add parental contact in this patch.

`step_generation` does not set the flag. Moving the orbit onto
`GenerationResult` would launder it.

## Instruction A, the only patch

1. `MatchingAlleleFactorial.red_queen_proved` stays false. Do not copy the predicate into the flag.
2. `biological_red_queen_proved` stays false. `assert_claim_allowed("red_queen_proved")` still raises. Ceiling stays `runtime_observation`. Do not edit `engine.py`.
3. Delete test locks that `red_queen_proved` is True, that `pattern_holds` is True, and that `debit_threshold == 32.0`.
4. Add one observation test and no new field: outcross × coevolve at virulence 32, generations 1–3, zero `p6_match_cost`, name-set still alternates. That alternation must not satisfy the cycle clause used by the flag. Name 32 only as this witness.
5. Do not add a stored-antagonist field, a second debit reason, a type-III curve, a next-generation matrix, or a `GenerationResult` field. Do not set the flag true in this patch.

## Instruction B, not in that patch

Later, and only later: the frequency change of a rare outcross codon inside one population that also contains selfing, and only where virulence/2 is strictly below birth ATP. Parental-similarity contact versus an encounter that ignores the parent. Freeze must be update-off with the debit still on. Zero debit must be debit-off with the update still on. Pure-arm extinction is not that record. `biological_red_queen_proved` stays false even then. If both mating bit-strings cannot already be copied by the existing birth rule, do not build a new mating engine; stop and report that.

## Killed

Memory debit as a kill-switch. Holling as a synonym for force of infection. The pattern or the flag on `GenerationResult`. 32 as an onset. Setting the flag true together with the retraction.
