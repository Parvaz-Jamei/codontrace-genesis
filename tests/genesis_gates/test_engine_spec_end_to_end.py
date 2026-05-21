from __future__ import annotations

from codontrace.genesis.engine import GenesisEngine, GenesisExperimentSpec


def test_engine_spec_end_to_end_exports_artifacts() -> None:
    engine = GenesisEngine.from_spec(
        GenesisExperimentSpec(tick_count=2, genome_bits=("101110000",))
    )
    result = engine.run_ticks()
    assert result.summary().experiment.final_population == 1
    assert result.manifest.digest()
    assert engine.snapshot().digest()
    assert engine.export_evidence_pack().manifest.run_id == result.run.run_id
    assert engine.export_replay_bundle().manifest.digest() == result.manifest.digest()
