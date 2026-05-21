from codontrace.genesis import ADFCompressionScore, ADFPattern, ADFProposal, DynamicVocabularyState


def test_adf_public_objects_roundtrip_and_digest():
    pattern = ADFPattern("p", ("WAIT", "MOVE_TOWARD"), ("000", "011"), 2, 3, 0, 1, ("org",), ("r",))
    score = ADFCompressionScore("p", 6, 3, 3.0, 3, None, 0.5, True, ("thresholds_passed",))
    proposal = ADFProposal("prop", pattern, score, "1000", "ADF_1000", 0.2)
    state = DynamicVocabularyState("genesis_v0", proposals=(proposal,))
    assert ADFPattern.from_dict(pattern.to_dict()).digest() == pattern.digest()
    assert ADFProposal.from_dict(proposal.to_dict()).digest() == proposal.digest()
    assert DynamicVocabularyState.from_dict(state.to_dict()).digest() == state.digest()
