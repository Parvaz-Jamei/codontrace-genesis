# Rule Validation and Security

`RuleProposal` is structured data. `RuleValidator` checks conservation, locality, determinism, namespace, reaction-cycle, codon/action compatibility, and obvious fitness-exploit risk. No proposal is executable code. `ApprovedRuleSet` requires a passed validation result and an explicit `HumanApprovalRecord` with `APPROVED` status.


## Applying approved rule sets

Use `apply_approved_rule_set(spec, approved_rule_set)` to prepare a next-run spec after validation and human approval. The function does not execute code and only applies a conservative whitelist of declarative updates such as metadata and selected engine/capsule/causal config fields. Unsupported diff entries are preserved in `spec.metadata` for audit instead of silently mutating runtime state.
