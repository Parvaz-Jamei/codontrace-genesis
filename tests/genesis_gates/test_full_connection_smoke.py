from __future__ import annotations

from codontrace.genesis.engine import GenesisEngine, GenesisExperimentSpec
from codontrace.genesis.review import LLMReviewRequest


def test_full_connection_smoke() -> None:
    spec = GenesisExperimentSpec(
        genome_bits=("101110000", "110101000"),
        tick_count=3,
        initial_runtime_atp=25.0,
        initial_learning_atp=12.0,
        population_max=4,
    )
    engine = GenesisEngine.from_spec(spec)
    result = engine.run_ticks()
    snapshot = engine.snapshot()
    evidence = engine.export_evidence_pack()
    request = LLMReviewRequest.from_evidence_pack(evidence)
    replay = engine.export_replay_bundle()
    assert snapshot.digest()
    assert evidence.digest()
    assert request.digest()
    assert replay.digest()
    assert result.summary().experiment.causal_updates > 0
    assert result.summary().experiment.qd_filled_bins > 0
