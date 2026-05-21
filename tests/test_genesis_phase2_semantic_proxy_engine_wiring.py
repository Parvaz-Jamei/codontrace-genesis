from codontrace.genesis import (
    GenesisEngine,
    GenesisExperimentSpec,
    TranslationPolicy,
    TranslationWeight,
    build_translation_profile,
)


def _profile():
    return build_translation_profile(
        "profile-a",
        "spec",
        (TranslationWeight("000", "EMIT_NEXUS", 1.0, 1, 0),),
    )


def test_engine_built_semantic_proxy_report_marks_status_measured():
    result = GenesisEngine.from_spec(
        GenesisExperimentSpec(
            genome_bits=("000",),
            tick_count=1,
            initial_runtime_atp=10,
            translation_profile=_profile(),
            translation_policy=TranslationPolicy(),
            enable_execution_source=True,
        )
    ).run_ticks()
    assert result.manifest.runtime_hashes["semantic_proxy_report_digest"]
    assert result.manifest.protocol_statuses["phase2.semantic_proxy_report_digest.status"] == "measured"
    assert result.manifest.protocol_statuses["translation_protocol_executed"] == "true"
    assert result.manifest.protocol_statuses["semantic_proxy_status"] == "active"


def test_adaptive_gp_map_proxy_uses_engine_semantic_report_evidence():
    result = GenesisEngine.from_spec(
        GenesisExperimentSpec(
            genome_bits=("000",),
            tick_count=1,
            initial_runtime_atp=10,
            translation_profile=_profile(),
            translation_policy=TranslationPolicy(),
            enable_execution_source=True,
            engine_config=__import__("codontrace.genesis", fromlist=["GenesisEngineConfig"]).GenesisEngineConfig(claim_level="adaptive_gp_map_proxy"),
        )
    ).run_ticks()
    assert result.manifest.normalized_requested_claim == "adaptive_gp_map_proxy"
    assert result.manifest.claim_gate_allowed is True


def test_translation_profile_without_replay_capture_does_not_unlock_high_claim():
    result = GenesisEngine.from_spec(GenesisExperimentSpec(tick_count=1, translation_profile=None)).run_ticks()
    assert result.manifest.protocol_statuses["semantic_proxy_status"] == "fixed_translation"
