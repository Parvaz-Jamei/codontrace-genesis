# Phase 2 Scientific Evidence Ladder

Phase 2 supports stronger claim labels by increasing evidence quality rather than lowering the claim bar.

## Ladder pattern

1. `metadata_only`: schema exists but no runtime effect.
2. `instrumented_runtime`: runtime records exist and are digestable.
3. `control_supported`: negative/control evidence exists.
4. `ablation_supported`: removing a feature changes the measured outcome.
5. `multi_seed_supported`: paired seeds, effect size, CI, non-finite guard.
6. `heldout_supported`: heldout world/partner or environment shift with leakage checks.
7. `intervention_supported`: explicit treatment/baseline intervention or ablation.
8. `claim_ready_research_alpha`: all required surfaces are replayable and manifest-backed.

## Phase 2 labels

| Claim label | Required idea |
|---|---|
| `variable_genome_runtime_supported` | Runtime mutation plus genome/record/replay digests |
| `adf_macro_usefulness_supported` | Executable macro, source-map, null/permutation controls, cost-aware utility |
| `contribution_attribution_supported` | Ledger from runtime records plus micro-ablation status |
| `innovation_protection_supported` | Bounded evidence-triggered protection plus controls |
| `event_graph_evidence_supported` | Runtime event graph digest and replay |
| `intervention_supported_causal_evidence` | Treatment/baseline intervention result, effect size, paired seeds |
| `discovery_witness_candidate` | D0, shadow, persistence, witness artifact |
| `discovery_ablation_supported_candidate` | Discovery witness plus ablation/QD novelty evidence |
| `social_partner_generalization_supported` | Familiar/unfamiliar/heldout partner protocol and leakage check |
| `oee_candidate_evidence_supported` | Novelty, learnability, persistence, ablation, multi-seed statistics |

Metadata-only artifacts do not unlock these labels.
