# Design Note: A25 Final Scientific-Library Hardening

## What was fixed?
- ClaimGate is now whitelist-based, alias-resistant, and returns a full ClaimDecision.
- Run manifests now carry requested claim, normalized claim, final ClaimGate decision, evidence digests, policy version, and protocol/evidence execution status.
- ApprovedRuleSet validates the proposal -> validation -> approval digest chain.
- Structural mutation now separates genome identity digest from provenance/artifact digests.
- Replay-critical science objects reject spoofed digests in strict constructors/import paths.
- QDCandidate validates inline genome_bits against genome_digest and records reference status.
- not_run/disabled protocol placeholders are status metadata, not scientific evidence.
- Active QD labels require parent-selection feedback; passive archives are downgraded to reporting.
- Execution source digest is based on real CodonExecutionRecord payloads when source tracing is enabled.
- ActionRegistry hash includes handler/provenance/ABI or marks external handlers as non-replayable.
- GenesisExperimentSpec validates genome_bits and metadata early.
- TranslationProfile safety gates reject unapproved actions and unsafe weight bounds.
- OEE persistence windows and shadow adjustment are enforced before oee_candidate.
- BenchmarkScenarioSuite now includes known_capsule_transfer_world.

## Why was it scientifically necessary?
Scientific artifacts must not be spoofable, placeholder hashes must not be counted as evidence, and overclaim aliases must not bypass policy. The patch hardens CodonTrace as an importable, replayable Python research library rather than an app or workflow product.

## Existing modules touched
- codontrace.genesis.claim_gate
- codontrace.genesis.artifacts
- codontrace.genesis.engine
- codontrace.genesis.rules
- codontrace.genesis.structural_mutation
- codontrace.genesis.qd_search
- codontrace.genesis.event_graph
- codontrace.genesis.translation_profile
- codontrace.genesis.statistical_protocol
- codontrace.genesis.benchmark_suite
- codontrace.genesis.review
- codontrace.genesis.population

## New modules added and why
No new runtime modules were added. This patch strengthens existing library modules instead of creating parallel systems.

## Claim labels changed
- Unknown claims are rejected by default.
- Forbidden aliases for semantic-closure overclaiming, artificial-life-adjacent proof wording, true causal intelligence, unbounded OEE, and full GENESIS are rejected.
- active_qd_supported requires parent-selection feedback; otherwise qd_reporting_supported is the ceiling.
- oee_candidate requires persistence window, shadow adjustment, threshold support, and non-placeholder evidence.

## Artifacts / manifest fields changed
Manifest now records requested claim, normalized claim, final claim, ClaimGate decision, failed reasons, evidence digests, policy version, protocol statuses, schema completeness, scientific protocol execution status, runtime RNG fields, execution source digest, and stricter runtime hashes.

## Negative / spoofing tests added
- overclaim alias rejection
- unknown claim rejection
- ApprovedRuleSet digest mismatch rejection
- replay-critical fake digest rejection
- QDCandidate genome digest mismatch rejection
- source digest metadata exclusion
- placeholder not_run evidence rejection
- TranslationProfile safety gate failures

## Backward compatibility risk
Legacy claim labels are normalized through aliases when safe. Existing CausalGraph/EventGraph compatibility remains. Experimental claims are more restrictive than before, which is intentional.

## Literature / tooling pattern followed
- ACM artifact-review principles: documented, consistent, complete, exercisable, verification/validation evidence.
- Reproducibility principle: same code/data/config/seed/protocol should reproduce artifacts.
- MAP-Elites/QD distinction: passive archive is not active QD unless archive state affects parent selection.

## What this supports
A stronger scientific-library base with replay-safe artifacts, claim-controlled manifests, digest-chain validation, and negative tests against scientific spoofing.

## What this does not claim
It does not prove artificial life, semantic closure, unbounded open-ended evolution, true causal discovery, causal intelligence, or a full GENESIS engine.
