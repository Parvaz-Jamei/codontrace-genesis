from __future__ import annotations

from codontrace.genesis.engine import GenesisEngine, GenesisExperimentSpec


def test_qd_archive_updates_during_engine_run() -> None:
    engine = GenesisEngine.from_spec(
        GenesisExperimentSpec(tick_count=1, genome_bits=("101110000",))
    )
    assert engine.qd_archive is not None
    before = engine.qd_archive.digest()
    result = engine.run_ticks()
    assert result.ticks[0].qd_update is not None
    assert engine.qd_archive is not None
    assert engine.qd_archive.digest() != before
    assert result.summary().experiment.qd_filled_bins >= 1
