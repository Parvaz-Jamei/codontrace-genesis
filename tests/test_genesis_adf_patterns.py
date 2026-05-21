from codontrace.genesis import DynamicVocabularyConfig, detect_adf_patterns
from codontrace.trace import TraceEvent


def _event(step, action, codon, agent="org", status="executed"):
    return TraceEvent(
        step=step,
        agent_id=agent,
        codon=codon,
        action=action,
        atp_before=10.0,
        atp_after=9.0,
        position_before=(0, 0),
        position_after=(0, 0),
        status=status,
    )


def test_repeated_action_codon_sequence_detected_with_support():
    traces = [
        [_event(0, "WAIT", "000"), _event(1, "MOVE_TOWARD", "011"), _event(2, "WAIT", "000")],
        [_event(0, "WAIT", "000", agent="b"), _event(1, "MOVE_TOWARD", "011", agent="b")],
    ]
    config = DynamicVocabularyConfig(
        min_support_count=2, min_pattern_length=2, max_pattern_length=2
    )
    patterns = detect_adf_patterns(traces, config)
    assert patterns
    assert patterns[0].tokens == ("WAIT", "MOVE_TOWARD")
    assert patterns[0].support_count == 2
    assert patterns[0].organism_ids == ("b", "org")


def test_blocked_only_patterns_ignored_by_default():
    traces = [
        [
            _event(0, "WAIT", "000", status="blocked"),
            _event(1, "WAIT", "000", status="blocked"),
        ]
    ] * 3
    config = DynamicVocabularyConfig(
        min_support_count=2, min_pattern_length=2, max_pattern_length=2
    )
    assert detect_adf_patterns(traces, config) == ()


def test_pattern_order_and_digest_are_deterministic():
    traces = [[_event(0, "A", "000"), _event(1, "B", "001"), _event(2, "A", "000")]] * 3
    config = DynamicVocabularyConfig(
        min_support_count=2, min_pattern_length=2, max_pattern_length=3
    )
    first = detect_adf_patterns(traces, config)
    second = detect_adf_patterns(traces, config)
    assert [p.pattern_id for p in first] == [p.pattern_id for p in second]
    assert [p.digest() for p in first] == [p.digest() for p in second]
