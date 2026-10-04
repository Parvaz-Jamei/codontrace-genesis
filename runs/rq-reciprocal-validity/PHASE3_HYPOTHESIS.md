# Phase 3 hypothesis

No swap result and no confirmatory number has been computed.

Hypothesis. In the no-parasite control, class A births exceed class B because `PopulationState` steps organisms in id order and the birth cap fills before later ids act. Food headcount is not the cause.

Prediction. Swapping ids moves the extra births. Reversing the population tuple without renaming ids does not, because the stepper sorts by id. Swapping patch coordinates (position) and assigning the other class to the even patch indexes (food access) do not move id-letter births if the open seats are the cap, not the food. Swapping genomes and keeping ids does not move births counted by id letter, and it does move births counted by the parent window.

Control. The absent passage. The pressured arm is the same hosts with the conditioned parasite roster and coevolve passage. Contact count alone is not a change in the direction of selection. Direction is the sign of births and the sign of deaths.

Consequence. If only the id swap moves id-letter births, the stepper order stays as it is. It is not retuned to make A and B equal. Founder-lineage fitness and current-window fitness are reported separately. A missing series stays missing.

Engine path. `install_equal_hosts`, `PASSAGE_ABSENT`, and `run_generations` on `StructuralRQArm`. Parasite rows are read from `runs/rq-mechanism-v2/phase3-frequency/` and not rewritten.

Limit. One diagnostic seed for the factorial swaps. It is not twelve histories and it is not the confirmatory.
