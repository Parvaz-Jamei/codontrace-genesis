# Universal motor matrix, 2026-09-25

Contract tests only. Not a cell, not an intelligent organism, not a Red Queen result.
Existing suites were left in place. This file records the new matrix and the two
assertions that were wrong.

## Run

`pytest tests/universal -q` — 35 passed.

| File | Passed | What it locks |
|---|---|---|
| `tests/universal/test_mention_span_matrix.py` | 11 | Opt-in spans: digest unchanged when empty, overlap and alignment refused, insertion and deletion shift or drop a span, a straddling splice is dropped |
| `tests/universal/test_population_parameter_matrix.py` | 8 | Asexual seed identity, zero flip keeps the child tape, unpaid parent cost blocks birth, population cap, offspring ATP is a share not new energy, basal cost stays non-negative |
| `tests/universal/test_replay_parameter_matrix.py` | 10 | Same start plus same seed matches `step_population`. Later seeds on one runner keep carried state. Indel rates apply one codon each. Default closed-loop config stays out of `to_dict`. `engine.py` has no plugin words |
| `tests/universal/test_motor_quality_matrix.py` | 6 | Default genome keys, a payload span is not translated, trim drops a cut span, ATP debit above the balance returns `None` |

## Rejected as engine bugs

1. Seeds 12 and 13 on one runner did not match fresh runners given only those seeds. The first seed matched. Later steps carry the previous population. Rebuilt from the same start state, the successive runner matches. No motor change.
2. `insertion_rate=1` and `deletion_rate=1` together, seed 17, produced `insert:9:001` and `delete:6:010`. Length change was 0, which is one codon in and one codon out. Each rate alone moves length by one codon. No motor change.

## Not claimed

No new phenotype, no evolved locus, no medical or cognitive result.
