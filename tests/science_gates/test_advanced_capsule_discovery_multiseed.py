from codontrace.genesis.capsule_validation import (
    CapsuleClaimDecision,
    CapsuleTransferExperiment,
    CapsuleUsefulnessMetric,
)
from codontrace.genesis.discovery_protocol import (
    AblationMatrix,
    D0ExecutableBaseline,
    DiscoveryDecision,
    DiscoveryExperimentProtocol,
    LineagePersistenceCheck,
    PersistenceFilter,
    ShadowRun,
)
from codontrace.genesis.engine import GenesisExperimentSpec
from codontrace.genesis.multiseed import MultiSeedExperimentConfig, MultiSeedExperimentRunner


def test_capsule_transfer_on_off_and_before_after_effect() -> None:
    experiment = CapsuleTransferExperiment("capsule_effect", metric_name="prediction_accuracy")
    ablation = experiment.on_off_ablation(on_metric=0.75, off_metric=0.40)
    report = experiment.evaluate(
        ablation=ablation,
        before_after=CapsuleUsefulnessMetric("prediction_accuracy", before=0.4, after=0.7),
        locality_respected=True,
        adoption_success_rate=0.5,
    )
    assert report.decision is CapsuleClaimDecision.TRANSFER_EFFECT_SUPPORTED
    assert report.ablation is not None and report.ablation.delta > 0


def test_false_capsule_does_not_improve_claim() -> None:
    report = CapsuleTransferExperiment("false_capsule").evaluate(false_capsule_rejected=False)
    assert report.decision is CapsuleClaimDecision.ADOPTION_RECORDED_NO_TRANSFER_EFFECT
    assert "capsule_adoption_without_effect_is_not_transfer_proof" in report.limitations


def test_discovery_protocol_requires_d0_shadow_persistence_ablation() -> None:
    protocol = DiscoveryExperimentProtocol()
    missing = protocol.evaluate(candidate_id="c0")
    assert missing.decision is DiscoveryDecision.METADATA_ONLY
    assert "d0_baseline" in missing.missing_gates
    supported = protocol.evaluate(
        candidate_id="c1",
        d0=D0ExecutableBaseline("d0", "manifest", 1.0),
        shadow=ShadowRun("shadow", "manifest2", True),
        persistence=PersistenceFilter(window=3, observed_ticks=3),
        lineage=LineagePersistenceCheck(min_lineage_depth=2, observed_depth=2),
        ablation=AblationMatrix(({"factor": "capsule", "effect_supported": True},)),
        multiseed_passed=True,
        replay_verified=True,
    )
    assert supported.decision is DiscoveryDecision.SUPPORTED_BY_ABLATION


def test_discovery_claim_never_overclaims_life_or_oee() -> None:
    result = DiscoveryExperimentProtocol().evaluate(
        candidate_id="c2",
        d0=D0ExecutableBaseline("d0", "manifest", 1.0),
    )
    assert "life" not in result.decision.value
    assert "open_ended" not in result.decision.value


def test_multiseed_modes_and_minimum_seed_policy() -> None:
    spec = GenesisExperimentSpec(tick_count=1)
    reproducible = MultiSeedExperimentRunner(
        spec,
        MultiSeedExperimentConfig(seeds=(1, 2), tick_count=1, min_seeds_for_scientific_claim=3),
    ).run()
    assert reproducible.summary.seed_count == 2
    assert "insufficient_seed_count_for_scientific_claim" in reproducible.summary.limitations
    varied = MultiSeedExperimentRunner(
        spec,
        MultiSeedExperimentConfig(
            seeds=(1, 2, 3),
            tick_count=1,
            mode="evolutionary_variation",
            mutation_rate=0.1,
            novelty_pressure=0.2,
            min_seeds_for_scientific_claim=2,
        ),
    ).run()
    assert varied.summary.reproducibility_status == "distribution_report"
