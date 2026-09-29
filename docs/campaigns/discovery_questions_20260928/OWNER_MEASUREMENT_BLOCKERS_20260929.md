# Measurement and causal-coupling blockers (2026-09-29)

Operational note. Claim ceiling remains `phase2_design`. Green tests do not confirm the six scientific questions.

## Phase status judgment

| Ideas | Status vs four-phase brief |
|---|---|
| 1, 3, 5, 6 | Phase-2 boundaries and designs recorded; harness and smoke exist. Result and transferability discovery phases are not done. |
| 2, 4 | Design plus N≥64 runs and honest negative outcomes are recorded, but the blockers below prevent treating those runs as final hypothesis tests. Discovery phases 3–4 are incomplete. |

Do not run larger seed campaigns as a substitute for fixing priorities 1–4.

## Priority fixes

1. **Ledger interventions must affect the engine.** In the engine–ledger coupler, the engine reports state into the ledger, but edge, knowledge, and marker changes in the ledger do not change engine population trajectories. Idea 4 JSONL showed identical engine digests across all five cells for the same seed and time. Require a paired test where changing the intervention, holding other conditions fixed, changes the real population path. If the ledger is measurement-only, remove any claim of evolutionary effect.

2. **Idea 2 survival from real populations.** `survival_to_T` currently mixes positive-energy step counts with observer-arm energy scores. Those arms are not independent host populations with their own reproduction and extinction. Parasite pressure is a function of ecology indices, not a coevolving parasite population. Useful for calibration; not a test of gene vs pattern vs causal reasoning under parasite pressure.

3. **Matched Idea 4 controls.** Scaffold ablation cuts edges `E0`/`E1`; the random control currently cuts only `E5` (rechecked on seed 301). Edge count, degree, contact weight, and ATP lost must match across arms. Nearest-degree fallback must not be reported silently as an exact match.

4. **Idea 4 lineage recovery opportunity.** Current output has `recover=0` on all 960 records and 855 records ending at population zero. The ledger `rare` tag is not a genotype class or arose innovation; recovery markers and failure digests are pre-placed in the scaffold. Build paired branches from a real checkpoint with observable lineage and innovation, and first show that the control arm has a recovery opportunity. A flat-zero curve does not test a reversibility-window law.

5. **Track C smoke is not a scientific result.** Example: Idea 5 shortcut feeds success rates 0.85 and 0.40 into a function; those are not held-out world measurement accuracies. Idea 1 cost and Idea 6 restraint are still ledger operations, not heritable traits with genealogical consequence. Keep the smoke label; before leaving phase 2, compute metrics from agent behavior and survival.

6. **Auditable process trail.** Each phase needs a checkable trail: fresh prior-art search, five distinct pre-build storm rounds, work split and lead decision, two post-build critiques, tests, and two result analyses. Interdisciplinary novelty must cite nearest prior work plus a distinguishing prediction, not only a “hybrid” label.

## Open Red Queen barrier

The synthetic locked-parameter case still yields about −0.148. The barrier holds only while the absolute value is strictly below 0.20, so −0.148 holds and a score of −0.245 does not. Sign is separate: a negative exceedance is not acceptance of the positive direction, and it is not a proof. `genotype_set` staying fixed means presence of digests. Class-size swaps do not change that set. Abundance is a different quantity (`genotype_counts`).

## Work order

Fix 1–4 before more seeds. Then behavioral metrics for Track C. Then process-audit and Red Queen clarification.

## Reading after the 2026-09-29 code critique

Checked against origin/main `d8b431b` and against the local tree that is not that commit. No discovery claim. `hypothesis_supported` and `red_queen_proved` stay false. Phase 3 stays closed. The synthetic score −0.148 was not recomputed and was not raised.

1. **Red Queen barrier.** `rq_barrier_holds` now uses absolute magnitude: true only while `abs(score) < 0.20`. Sign is separate. −0.148 and −0.199 hold. −0.20 and −0.245 do not hold on magnitude. +0.19 holds. +0.20 does not. A negative exceedance does not accept the positive direction, and `red_queen_proved_from_score` stays false. `genotype_set` is presence only. That is the identity quantity. It is not abundance. Abundance is `genotype_counts`. A class-size swap keeps the set and changes the counts.

2. **Idea 2.** On `d8b431b` the engine file still builds `survival_to_T` from positive-energy steps and the 0.7/0.3 blend. That commit says the host-lineage census is not in it. The local engine census is not a host–parasite hypothesis test: births copy the oldest living lineage id, and the parasite value is a capped counter. Those records set `hypothesis_test_eligible=false` and `score_role=host_lineage_census`. The harness file still emits the 0.7/0.3 blend and now names it `observer_arm_score`, also ineligible.

3. **Idea 4 match.** On `d8b431b`, seeds 301–303 are not an exact ATP match. On this revision the same seeds cut `E0`/`E1` and `E6`/`E7` with equal edge count, degree, and ATP yield, so `match_exact` is true. Contact weight is the edge ATP yield, not a fourth independent quantity. The equality is a planted mirror (`E0→E6`, `E1→E7`). It is not a fully matched scientific control and it is not a result. Inexact arms stay out of the combo contrast.

4. **Coupler.** A control token move debits ATP with the fixed token coefficient and no edge change, and still sets `coupler_affects_engine`. The edge ATP term is `n_edge_changes * 0.35`. The food term adds `n_edge_changes * 0.15`, which is also a count penalty. Path digests can differ. `contact_structure_effect_identified` and `knowledge_effect_identified` stay false. The split is an account, not a mechanism claim.

5. **Recovery window.** `window_law_tested` and `recovery_window_built` stay false. Background births do not clear `recovery_window_missing` (real branching checkpoint, innovation arising in the lineage, control recovery opportunity).

6. **Ideas 1, 3, 5, 6.** Track C JSONL is stamped `data_class=scaffold` and `scientific_result=false`. Sixty-four seeds on that meter are not a closed-loop result. No replacement data set was written.

7. **Process check.** Five distinct texts are no longer enough for `process_cycle_complete`. The checker requires a dated search with references, a lead and two roles, an independent critique, the phase order, two retry slots, and ordered dated events. A unit-test trail that meets the shape is not this campaign's audit. The campaign is not marked audited.

