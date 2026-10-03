# Scientific integrity patch — 3 October 2026

Base: `ff37a2187374d6322c724ba67a4ebf02ab1f4b9a`.

## Scope and scientific interpretation

This patch repairs evidence classification and accounting. It does not establish a new biological finding, prove the Red Queen hypothesis, or certify the whole engine. Previously locked endpoints and historical verdicts remain unchanged. Scripted positive controls establish implementation behaviour, not spontaneous ecological recovery.

### Independent units and intervention artifacts

Independent units are history/seed blocks for a single specified estimand. Repeated checkpoints and aliases are not new replicates. Different interventions, target factors or settings cannot be pooled by this univariate paired estimator. This conservative contract is not a substitute for a hierarchical model when dependent interventions genuinely need joint analysis.

`build_intervention_result(scenario_id, baseline_values, treatment_values)` remains callable but anonymous arrays are descriptive only: `intervention_observed`, no verified independent-seed count, and no claim eligibility. Unequal paired lengths raise `ConfigurationError`. The paired Student-t interval is undefined for fewer than two observations or zero residual variance. To request audited support, pass `run_pairs=...` with matching identities and metrics. Eligibility is recalculated from the attached report and its run pairs, rather than accepted from its evidence label. The 16-unit floor is an existing project policy, not a universal statistical theorem. A digest protects internal consistency; it does not prove that submitted histories were honestly generated.

### D2 contact binding and time-bound recovery

Use `execute_runtime_transfer(source_account, recipient_account, run_id=..., contact_id=..., source_id=..., recipient_id=..., tick=..., amount=..., loss=...)`. Both ledger entries carry the same canonical binding, covering participants, run, contact, tick and payment/loss. Unrelated movement debits and food credits cannot be relabelled as a contact. Persist both returned `consumed_contact_ids` and `consumed_ledger_entries` across validation calls to prevent replay under a new contact alias. Local validation cannot detect replay if the caller discards those sets.

Capture boundaries with `capture_recovery_boundary(account, run_id=..., recipient_id=..., tick=...)` and pass those mappings to `assess_recovery`. Plain numeric trajectories have no verifiable temporal provenance and return `unbound_boundaries`. Every mapping must reconcile to the recipient's ledger cursor and balance. Only bound contacts inside the actual drop-to-restoration interval can explain restoration; other positive credits invalidate that attribution. Ledger debits, including maintenance, are reconciled against net gain. Mixed runs and late transfers cannot explain an earlier recovery.

The new endpoint is `FI-RESOURCE-RECOVERY-V4-TIME-BOUND`; contact validation is `D2-CONTACT-LEDGER-V2`. The V3 fractional thresholds are retained, but the extra temporal binding changes the evidence contract. Do not silently relabel an old V1/V2/V3 result as V4. Rerun the instrumented experiment when V4 evidence is needed. A positive recovery score still sets `hypothesis_supported=False`. Locked-arm helper outputs are explicitly `control_only=True`.

Legacy engine entries may use different tick clocks. Entry ID remains append order; balances must be continuous. Sampling validates the cursor against ticks instead of globally rejecting every legacy prehistory with a backward tick. This tolerance is not permission to mix unrelated ledgers, identities or histories. The ledger is a trusted experiment input, not an authenticated external data source.

### Closure archive provenance

RQ1 and RQ3 closure seed JSONs are current aggregate summaries. Their existence does not replace missing historical trajectories. Explicit `EVIDENCE_STATUS.json` files and a read-only inventory tool mark these closure directories `INCOMPLETE_PROVENANCE`. Four archive manifests include the new status files and existing summaries. No seed results, raw trajectories, historical verdicts or missing data were invented. To close provenance gaps, generate a new versioned raw pack with initial state, exact configuration, complete trajectory, environment/version identifiers and a tested replay recipe.

Run the inventory with `python tools/audit_closure_evidence.py`. Its verdict is deliberately specific to these six existing closure summaries; future complete packs require a real replay audit before promotion.

## Validation

- Broad scientific gates, measurements, D2, checkpoint/RNG, manifests, antagonist energy accounting and verdict ledger: 327 passed in 35.82 s.
- Discovery campaigns and three additional closed-loop confirmation/mechanism suites: 111 passed in 23.47 s.
- Ruff selected-file checks: passed after correcting imports.
- New adversarial regressions cover false replication, mixed estimands, anonymous artifacts, positive audited artifacts, unrelated ledger entries, untimed boundaries, delayed contacts, balance tampering, mixed histories, ledger replay and unfunded transfer mutation.

These are targeted suites. The full repository suite and a fresh large scientific campaign were not run. Package-level final checks and exact commands are in the accompanying `TEST_REPORT.json`.

## Scientific basis

Hurlbert, S. H. (1984). Pseudoreplication and the design of ecological field experiments. *Ecological Monographs*, 54, 187–211. https://doi.org/10.2307/1942661 . Supports distinguishing experimental units from repeated observations; it does not prove independence merely from IDs.

NIST/SEMATECH e-Handbook, Confidence Limits for the Mean: https://www.itl.nist.gov/div898/handbook/eda/section3/eda352.htm . The Student-t interval uses sample variance, sample size and degrees of freedom; assumptions and sampling design still matter.

The engineering binding/cursor rules are safeguards designed for this engine. They are not a claim of scientific novelty or a published universal recovery definition.
