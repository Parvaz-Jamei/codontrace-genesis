from dataclasses import replace

from codontrace.actions import default_action_registry
from codontrace.genesis.artifacts import validate_scientific_manifest
from codontrace.genesis.claim_gate import ClaimRequest, ScientificClaimGate
from codontrace.genesis.elements import ElementRegistry
from codontrace.genesis.engine import GenesisEngine, GenesisExperimentSpec
from codontrace.genesis.replay import verify_replay_bundle
from codontrace.genesis.rules import (
    ApprovalStatus,
    ApprovedRuleSet,
    HumanApprovalRecord,
    RuleProposal,
    RuleProposalSource,
    RuleSetDiff,
    RuleValidator,
    apply_approved_rule_set_with_report,
    build_rule_safety_report,
    validate_rule_compatibility,
)


def _approved_rule() -> ApprovedRuleSet:
    proposal = RuleProposal(
        proposal_id="p1",
        source=RuleProposalSource.TEST,
        diff=RuleSetDiff(
            add=(
                {
                    "target": "metadata",
                    "key": "science_gate",
                    "value": True,
                    "namespace": "genesis",
                },
            )
        ),
    )
    validation = RuleValidator().validate(proposal)
    approval = HumanApprovalRecord(
        proposal.digest(), "tester", ApprovalStatus.APPROVED, "ok", validation.digest()
    )
    return ApprovedRuleSet(proposal, validation, approval)


def test_scientific_manifest_requires_hashes_and_replay_detects_tamper() -> None:
    result = GenesisEngine.from_spec(
        GenesisExperimentSpec(tick_count=1, approved_rule_set=_approved_rule())
    ).run_ticks()
    validation = validate_scientific_manifest(result.manifest)
    assert validation.passed or "runtime_hashes.element_grid_hash" in validation.missing_hashes
    assert verify_replay_bundle(result.replay_bundle, result).passed
    tampered = replace(result.replay_bundle, generation_digests=("bad",))
    assert not verify_replay_bundle(tampered, result).passed


def test_manifest_hash_changes_when_runtime_specs_change() -> None:
    base = (
        GenesisEngine.from_spec(GenesisExperimentSpec(tick_count=1)).run_ticks().manifest.digest()
    )
    changed = (
        GenesisEngine.from_spec(
            GenesisExperimentSpec(tick_count=1, metadata={"substrate": "changed"})
        )
        .run_ticks()
        .manifest.digest()
    )
    assert base != changed


def test_llm_rule_cannot_bypass_validator_and_compatibility_checks() -> None:
    proposal = RuleProposal(
        proposal_id="bad",
        source=RuleProposalSource.LLM,
        diff=RuleSetDiff(
            add=(
                {
                    "code": "eval('x')",
                    "action": "NOT_REGISTERED",
                    "output_element": "Bad",
                    "namespace": "genesis",
                },
            )
        ),
    )
    validation = RuleValidator().validate(proposal)
    safety = build_rule_safety_report(validation)
    compatibility = validate_rule_compatibility(
        proposal,
        element_registry=ElementRegistry.genesis_v0(),
        action_registry=default_action_registry(),
    )
    assert not validation.passed
    assert not safety.no_code_execution
    assert not compatibility.passed
    assert "action_registry_incompatible" in compatibility.issues


def test_approved_rule_changes_config_hash() -> None:
    spec = GenesisExperimentSpec(tick_count=1)
    updated, report = apply_approved_rule_set_with_report(spec, _approved_rule())
    assert report.applied
    assert updated.digest() != spec.digest()
    assert updated.metadata["science_gate"] is True


def test_claim_gate_rejects_overclaim_by_default_and_allows_foundation() -> None:
    gate = ScientificClaimGate()
    assert gate.decide(ClaimRequest("foundation_engine", {})).allowed
    full = gate.decide(ClaimRequest("full_GENESIS_engine", {"all_protocols_complete": True}))
    assert not full.allowed
    causal = gate.decide(
        ClaimRequest("causal_intervention_supported", {"intervention_protocol": True})
    )
    assert not causal.allowed
    oee = gate.decide(ClaimRequest("open_ended_evolution_candidate", {"multi_seed": True}))
    assert not oee.allowed
