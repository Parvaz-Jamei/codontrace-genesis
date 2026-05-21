import pytest

from codontrace.errors import ConfigurationError
from codontrace.genesis import (
    ADFProposalCostMode,
    CapsuleEmissionConfig,
    CapsuleEmissionResult,
    DynamicVocabularyConfig,
    DynamicVocabularyState,
    GenesisATPState,
    GenesisCodonTable,
    NexusSignal,
    propose_dynamic_vocabulary,
)
from codontrace.genesis.adf import ADFCostPolicy, detect_adf_patterns, extend_codon_table_with_adfs
from codontrace.genesis.capsule import CausalCapsule
from codontrace.trace import TraceEvent


def _event(step, action="WAIT", codon="000", status="executed"):
    return TraceEvent(
        step=step,
        agent_id="org",
        codon=codon,
        action=action,
        atp_before=10.0,
        atp_after=9.0,
        position_before=(0, 0),
        position_after=(0, 0),
        status=status,
    )


def test_extended_codon_width_5_creates_5_bit_proposals():
    config = DynamicVocabularyConfig(extended_codon_width=5)
    state = DynamicVocabularyState.for_config("genesis_v0", config)
    atp = GenesisATPState.from_runtime(10.0, learning_atp=5.0, learning_enabled=True)
    result = propose_dynamic_vocabulary(
        [[_event(0), _event(1, "MOVE_TOWARD", "011")]] * 3,
        state,
        atp,
        config,
        tick=0,
        organism_id="org",
    )
    assert result.succeeded
    assert len(result.vocabulary_state.proposals[0].proposed_bits) == 5
    assert result.vocabulary_state.codon_width == 5


def test_width_mismatch_fails_clearly():
    state = DynamicVocabularyState(base_table_version="genesis_v0")
    config = DynamicVocabularyConfig(extended_codon_width=5)
    atp = GenesisATPState.from_runtime(10.0, learning_atp=5.0, learning_enabled=True)
    with pytest.raises(ConfigurationError):
        propose_dynamic_vocabulary(
            [[_event(0), _event(1, "MOVE_TOWARD", "011")]] * 3,
            state,
            atp,
            config,
            tick=0,
            organism_id="org",
        )


def test_adf_cost_uses_primitive_costs_not_action_name_length():
    config = DynamicVocabularyConfig(cost_policy=ADFCostPolicy.SUM_PRIMITIVE_COSTS)
    state = DynamicVocabularyState.for_config("genesis_v0", config)
    atp = GenesisATPState.from_runtime(10.0, learning_atp=5.0, learning_enabled=True)
    result = propose_dynamic_vocabulary(
        [[_event(0), _event(1, "MOVE_TOWARD", "011")]] * 3,
        state,
        atp,
        config,
        tick=0,
        organism_id="org",
    )
    assert result.vocabulary_state.proposals[0].proposed_cost == pytest.approx(1.3)


def test_discounted_cost_policy_is_deterministic():
    config = DynamicVocabularyConfig(
        cost_policy=ADFCostPolicy.DISCOUNTED_SUM,
        cost_discount=0.5,
    )
    state = DynamicVocabularyState.for_config("genesis_v0", config)
    atp = GenesisATPState.from_runtime(10.0, learning_atp=5.0, learning_enabled=True)
    result = propose_dynamic_vocabulary(
        [[_event(0), _event(1, "MOVE_TOWARD", "011")]] * 3,
        state,
        atp,
        config,
        tick=0,
        organism_id="org",
    )
    assert result.vocabulary_state.proposals[0].proposed_cost == pytest.approx(0.65)


def test_occurrence_refs_digest_full_windows():
    traces = [
        [_event(0, "WAIT", "000"), _event(1, "MOVE_TOWARD", "011")],
        [_event(0, "WAIT", "000"), _event(1, "EAT_LUMEN", "101")],
    ] * 3
    patterns = detect_adf_patterns(
        traces,
        DynamicVocabularyConfig(min_support_count=2, min_pattern_length=2, max_pattern_length=2),
    )
    refs = {pattern.tokens: pattern.occurrence_refs[0] for pattern in patterns}
    assert refs[("WAIT", "MOVE_TOWARD")] != refs[("WAIT", "EAT_LUMEN")]


def test_proposals_rejected_and_roundtrip():
    config = DynamicVocabularyConfig(min_compression_gain=999.0)
    state = DynamicVocabularyState.for_config("genesis_v0", config)
    atp = GenesisATPState.from_runtime(10.0, learning_atp=5.0, learning_enabled=True)
    result = propose_dynamic_vocabulary(
        [[_event(0), _event(1, "MOVE_TOWARD", "011")]] * 3,
        state,
        atp,
        config,
        tick=0,
        organism_id="org",
    )
    assert result.proposals_rejected >= 1
    assert result.rejected_proposal_ids
    assert type(result).from_dict(result.to_dict()).proposals_rejected == result.proposals_rejected


def test_per_proposal_learning_cost_consumes_per_proposal():
    traces = [[_event(0), _event(1, "MOVE_TOWARD", "011"), _event(2, "EAT_LUMEN", "101")]] * 3
    config = DynamicVocabularyConfig(
        min_pattern_length=2,
        max_pattern_length=2,
        proposal_cost_learning_atp=1.0,
        proposal_cost_mode=ADFProposalCostMode.PER_PROPOSAL,
    )
    state = DynamicVocabularyState.for_config("genesis_v0", config)
    atp = GenesisATPState.from_runtime(10.0, learning_atp=5.0, learning_enabled=True)
    result = propose_dynamic_vocabulary(traces, state, atp, config, tick=0, organism_id="org")
    assert result.consumed_learning_atp == result.proposals_created
    assert atp.runtime_available == 10.0


def test_mixed_blocked_executed_window_ignored_by_default_and_included_when_enabled():
    traces = [[_event(0), _event(1, "MOVE_TOWARD", "011", status="blocked")]] * 3
    default_patterns = detect_adf_patterns(
        traces,
        DynamicVocabularyConfig(min_support_count=2, min_pattern_length=2, max_pattern_length=2),
    )
    assert default_patterns == ()
    included = detect_adf_patterns(
        traces,
        DynamicVocabularyConfig(
            min_support_count=2,
            min_pattern_length=2,
            max_pattern_length=2,
            include_blocked_events=True,
        ),
    )
    assert included
    assert included[0].metadata["includes_blocked_or_failed"] is True


def test_nexus_signal_from_capsule_digest_stable_and_capsule_config_result_digest():
    capsule = CausalCapsule("cap", "org", 1.0, "graph", ("WAIT",), "executed", 0.8, 1, 32)
    signal = NexusSignal.from_capsule(capsule, position=(1, 2))
    assert NexusSignal.from_dict(signal.to_dict()).digest() == signal.digest()
    assert (
        CapsuleEmissionConfig().digest()
        == CapsuleEmissionConfig.from_dict(CapsuleEmissionConfig().to_dict()).digest()
    )
    result = CapsuleEmissionResult(False, False, "x", None, 0.0, 0.0, None, None)
    assert CapsuleEmissionResult.from_dict(result.to_dict()).digest() == result.digest()


def test_extended_table_accepts_5_bit_proposal():
    config = DynamicVocabularyConfig(extended_codon_width=5, allow_auto_accept=True)
    state = DynamicVocabularyState.for_config("genesis_v0", config)
    atp = GenesisATPState.from_runtime(10.0, learning_atp=5.0, learning_enabled=True)
    result = propose_dynamic_vocabulary(
        [[_event(0), _event(1, "MOVE_TOWARD", "011")]] * 3,
        state,
        atp,
        config,
        tick=0,
        organism_id="org",
    )
    table = extend_codon_table_with_adfs(
        GenesisCodonTable.default_v0(), result.vocabulary_state.accepted_proposals, codon_width=5
    )
    assert table.validate(result.vocabulary_state.accepted_proposals[0].proposed_bits)
