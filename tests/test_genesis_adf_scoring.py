from codontrace.genesis import ADFPattern, DynamicVocabularyConfig, score_adf_pattern


def _pattern(support=3, length=3):
    return ADFPattern(
        pattern_id="p",
        tokens=tuple(f"A{i}" for i in range(length)),
        codons=tuple("000" for _ in range(length)),
        length=length,
        support_count=support,
        first_seen_tick=0,
        last_seen_tick=2,
        organism_ids=("org",),
        trace_refs=("r",),
    )


def test_compression_gain_formula_and_accept():
    config = DynamicVocabularyConfig(
        min_support_count=3, min_reuse_count=2, min_compression_gain=1.0
    )
    score = score_adf_pattern(_pattern(support=4, length=3), config=config, atp_pressure=2.0)
    assert score.compression_gain == 8.0
    assert score.atp_pressure_score == 1.0
    assert score.accepted


def test_low_support_and_low_gain_reject_with_reasons():
    config = DynamicVocabularyConfig(
        min_support_count=3, min_reuse_count=3, min_compression_gain=10.0
    )
    score = score_adf_pattern(_pattern(support=1, length=2), config=config)
    assert not score.accepted
    assert "support_below_threshold" in score.reasons
    assert "compression_gain_below_threshold" in score.reasons


def test_negative_fitness_delta_rejects_when_required():
    config = DynamicVocabularyConfig(require_fitness_non_decrease=True)
    score = score_adf_pattern(_pattern(), config=config, fitness_before=10.0, fitness_after=9.0)
    assert not score.accepted
    assert "negative_fitness_delta" in score.reasons
