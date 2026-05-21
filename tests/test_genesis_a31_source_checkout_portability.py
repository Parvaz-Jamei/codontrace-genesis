from types import SimpleNamespace

from codontrace.genesis import CausalGraph, GenesisATPState
from codontrace.genesis.capsule import (
    CapsuleAdoptionBlockedReason,
    CapsuleTransferConfig,
    CausalCapsule,
    SourceFitnessStatus,
    adopt_causal_capsule,
)


def test_capsule_transfer_config_round_trips_provisional_source_fitness_policy() -> None:
    cfg = CapsuleTransferConfig(
        enabled=True,
        min_source_fitness=2.0,
        accept_provisional_source_fitness=False,
    )
    restored = CapsuleTransferConfig.from_dict(cfg.to_dict())
    assert restored.accept_provisional_source_fitness is False
    assert restored.digest() == cfg.digest()


def test_provisional_source_fitness_can_be_rejected_by_strict_policy() -> None:
    capsule = CausalCapsule(
        capsule_id="cap-provisional",
        source_organism_id="source",
        source_fitness=3.0,
        source_fitness_status=SourceFitnessStatus.PROVISIONAL,
        source_graph_digest="graph",
        event_pattern=("predicts",),
        predicted_outcome="outcome:x",
        confidence=1.0,
        emitted_tick=0,
        ttl=8,
    )
    atp = GenesisATPState.from_runtime(5.0, learning_atp=5.0, learning_enabled=True)
    result = adopt_causal_capsule(
        SimpleNamespace(id="target"),
        capsule,
        CausalGraph(),
        None,
        atp,
        CapsuleTransferConfig(
            enabled=True,
            min_confidence=0.0,
            adoption_min_confidence=0.0,
            min_source_fitness=2.0,
            accept_provisional_source_fitness=False,
        ),
        tick=1,
    )
    assert result.succeeded is False
    assert (
        result.blocked_reason
        == CapsuleAdoptionBlockedReason.SOURCE_FITNESS_PROVISIONAL_NOT_ACCEPTED.value
    )


def test_provisional_source_fitness_is_accepted_by_default_when_above_threshold() -> None:
    capsule = CausalCapsule(
        capsule_id="cap-provisional-ok",
        source_organism_id="source",
        source_fitness=3.0,
        source_fitness_status=SourceFitnessStatus.PROVISIONAL,
        source_graph_digest="graph",
        event_pattern=("predicts",),
        predicted_outcome="outcome:x",
        confidence=1.0,
        emitted_tick=0,
        ttl=8,
    )
    atp = GenesisATPState.from_runtime(5.0, learning_atp=5.0, learning_enabled=True)
    result = adopt_causal_capsule(
        SimpleNamespace(id="target"),
        capsule,
        CausalGraph(),
        None,
        atp,
        CapsuleTransferConfig(
            enabled=True,
            min_confidence=0.0,
            adoption_min_confidence=0.0,
            min_source_fitness=2.0,
        ),
        tick=1,
    )
    assert result.succeeded is True
