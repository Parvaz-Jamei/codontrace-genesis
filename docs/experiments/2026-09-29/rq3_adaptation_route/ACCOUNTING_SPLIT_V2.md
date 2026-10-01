# RQ-3 antagonist accounting, split_v2

The tables already in this directory were produced by the previous population
object. That object copied a parent's energy onto each offspring and did not
debit the parent, and its frozen reseat could seat the same `unit_id` twice.
Those files are kept as results of that defective model. They were not
recomputed, deleted, or relabelled as a finished hypothesis test.

`ACCOUNTING_VERSION = split_v2` in
`src/codontrace/genesis/measurements/antagonist_population.py` is a different
contract: the parent remains, its energy is divided across itself and its
offspring, and a frozen reseat is one-to-one. No new RQ-3 campaign was run
for this change. `hypothesis_supported` and `red_queen_proved` stay false.
