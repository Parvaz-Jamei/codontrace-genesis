from __future__ import annotations

from codontrace.genesis.artifacts import JsonArtifactExporter, ReplayBundle
from codontrace.genesis.engine import GenesisEngine, GenesisExperimentSpec


def test_manifest_and_replay_bundle_are_serializable_and_deterministic() -> None:
    engine = GenesisEngine.from_spec(GenesisExperimentSpec(tick_count=1, seed=42))
    result = engine.run_ticks()
    payload = result.replay_bundle.to_dict()
    restored = ReplayBundle.from_dict(payload)
    assert restored.digest() == result.replay_bundle.digest()
    assert result.manifest.config_hash
    exported = JsonArtifactExporter(indent=None).export(result.evidence_pack)
    assert result.manifest.run_id in exported
