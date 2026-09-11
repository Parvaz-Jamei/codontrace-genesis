# Task-switching costs promote the evolution of division of labor and shifts in individuality

**CodonTrace Genesis literature digest** (not a substitute for the paper).

- **id:** `goldsby_2012_pnas_task_switching`
- **authors:** Heather J. Goldsby, Anna Dornhaus, Benjamin Kerr, Charles Ofria
- **year:** 2012
- **venue:** Proceedings of the National Academy of Sciences 109:13686-13691
- **identifiers:** doi:10.1073/pnas.1202233109
- **tags:** Goldsby, PNAS 2012, task-switching, division of labor, individuality, Avida, communication, spatial patterning, major transitions, DoL, collective intelligence, evidence pathway
- **claim ceiling:** `runtime_observation`

## Digest

Goldsby, Dornhaus, Kerr, and Ofria used Avida to ask whether the cost of switching tasks promotes division of labor and a shift in individuality. Treatments imposed a CPU-cycle delay when an organism exported a different task type (low / 25-cycle moderate / 50-cycle high). Each treatment was replicated 50 times. Colonies had to collect a resource quota to replicate. Division of labor was measured with Shannon mutual information (Gorelick et al.). Higher switching costs produced more DoL (Kruskal-Wallis). Coordination mechanisms that evolved included communication, spatial patterning, and task partitioning. Under high costs, individuals often lost the ability to perform required tasks in isolation and required the group context — simultaneous loss of lower-level autonomy and gain of higher-level function, a signature of a major transition. Clonal groups (identical genomes) still differentiated behaviorally; DoL was not assembled from pre-specialized genotypes. This is the experimental standard CodonTrace Genesis must meet before claiming evolved DoL: a cost parameter, a group-replication payoff, a DoL statistic, isolation-vs-group competence, and multi-replicate effect sizes. Assigned role tags and round-robin gates are not that experiment. How to get collective intelligence evidence in this tradition: impose a task-switching cost, measure evolved DoL, test isolation vs group competence, and keep ClaimGate blocked until those results exist.

## Key claims

- Task-switching costs are a causal driver of evolved division of labor in digital organisms.
- High switching costs can make individuals depend on group context (loss of lower-level autonomy).
- DoL can evolve among genetically identical group members via flexible behavior plus communication.
- Literature-grade evidence needs ~50 replicates, a DoL statistic, and isolation controls — not a single smoke delta.

## What CodonTrace Genesis has

Phase H TaskSwitchingCostConfig hook; Phase I evolved preference DoL analog; Phase K `run_goldsby_cpu_delay_specialist_campaign` (research default 50 replicates, 0/25/50-cycle analog treatments, isolation vs group dual-task hooks). `is_goldsby_2012_pnas_experiment` stays False.

## What CodonTrace Genesis lacks

Avida C++ CPU-delay specialists and colony quota; isolation failure that is evolved autonomy loss rather than missing work instructions or analog delay; the PNAS 2012 experiment itself.

## Next experiment

How to get collective intelligence evidence: run the Phase K Goldsby harness at research `replicate_count=50`; keep ClaimGate blocked; do not label the analog the PNAS paper.

Retrieving this digest is not `collective_intelligence` or intelligence evidence.
