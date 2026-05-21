from codontrace.genesis import (
    DynamicVocabularyConfig,
    DynamicVocabularyState,
    GenesisATPState,
    propose_dynamic_vocabulary,
)
from codontrace.trace import TraceEvent


def _event(step, action="WAIT", codon="000"):
    return TraceEvent(
        step=step,
        agent_id="org",
        codon=codon,
        action=action,
        atp_before=10.0,
        atp_after=9.0,
        position_before=(0, 0),
        position_after=(0, 0),
    )


def _traces():
    return [[_event(0), _event(1, "MOVE_TOWARD", "011")]] * 3


def test_insufficient_learning_atp_blocks_proposals_and_runtime_untouched():
    state = DynamicVocabularyState(base_table_version="genesis_v0")
    atp = GenesisATPState.from_runtime(10.0, learning_atp=0.0, learning_enabled=True)
    result = propose_dynamic_vocabulary(
        _traces(), state, atp, DynamicVocabularyConfig(), tick=0, organism_id="org"
    )
    assert not result.succeeded
    assert result.blocked_reason == "insufficient_learning_atp"
    assert atp.runtime_available == 10.0
    assert result.vocabulary_state.digest() == state.digest()


def test_enough_learning_atp_creates_proposal_without_auto_accept_by_default():
    state = DynamicVocabularyState(base_table_version="genesis_v0")
    atp = GenesisATPState.from_runtime(10.0, learning_atp=3.0, learning_enabled=True)
    result = propose_dynamic_vocabulary(
        _traces(), state, atp, DynamicVocabularyConfig(), tick=0, organism_id="org"
    )
    assert result.succeeded
    assert result.proposals_created >= 1
    assert result.proposals_accepted == 0
    assert result.vocabulary_state.proposals[0].status == "proposed"
    assert atp.runtime_available == 10.0
    assert atp.learning_available == 2.0
    assert result.vocabulary_state.digest() != state.digest()


def test_auto_accept_accepts_threshold_passing_proposal():
    state = DynamicVocabularyState(base_table_version="genesis_v0")
    atp = GenesisATPState.from_runtime(10.0, learning_atp=3.0, learning_enabled=True)
    result = propose_dynamic_vocabulary(
        _traces(),
        state,
        atp,
        DynamicVocabularyConfig(allow_auto_accept=True),
        tick=0,
        organism_id="org",
    )
    assert result.proposals_accepted >= 1
    assert result.vocabulary_state.accepted_proposals
    assert (
        DynamicVocabularyState.from_dict(result.vocabulary_state.to_dict()).digest()
        == result.vocabulary_state.digest()
    )
