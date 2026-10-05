"""Runner ordinal blocks survive a v1b rescore that repairs paired contrasts."""

from codontrace.genesis.hard_experiment_02 import (
    CLAIM_CEILING,
    EXPERIMENT_ID,
    PRIMARY_OUTCOME,
    PRODUCT_NAME,
    SCHEMA_VERSION,
    HardExperiment02ArmRecord,
    HardExperiment02ArmSummary,
    HardExperiment02Campaign,
    HardExperiment02SeedRecord,
)
from codontrace.genesis.he02_contrasts import rescore_he02_campaign


def _arm(name: str, seed: int, atp: float) -> HardExperiment02ArmRecord:
    return HardExperiment02ArmRecord(
        arm=name,  # type: ignore[arg-type]
        seed=seed,
        terminal_mean_fitness=1.0,
        receiver_mean_terminal_runtime_atp=atp,
        capsule_adoptions_accepted=0,
        capsule_emissions=0,
        payload_patch_mi=0.0,
    )


def _campaign(failures: tuple[str, ...]) -> HardExperiment02Campaign:
    records = []
    for seed, treatment in enumerate(range(1, 9), start=1):
        records.append(
            HardExperiment02SeedRecord(
                seed=seed,
                treatment=_arm("treatment", seed, float(treatment)),
                content_null=_arm("content_null", seed, 0.0),
                activity_matched=_arm("activity_matched", seed, 0.0),
                channel_off=_arm("channel_off", seed, 0.0),
                capsules_shuffled=_arm("capsules_shuffled", seed, 0.0),
                oracle_moderate=_arm("oracle_moderate", seed, 0.0),
            )
        )
    return HardExperiment02Campaign(
        experiment_id=EXPERIMENT_ID,
        schema_version=SCHEMA_VERSION,
        product_name=PRODUCT_NAME,
        claim_ceiling=CLAIM_CEILING,
        seeds=tuple(range(1, 9)),
        scale="smoke",
        tick_count=1,
        population=1,
        primary_outcome=PRIMARY_OUTCOME,
        prereg_digest="prereg",
        protocol_digest="protocol",
        interventions=(),
        seed_records=tuple(records),
        arm_summaries=(
            HardExperiment02ArmSummary("content_null", 8, 5.0, 0.0, 0.0),
            HardExperiment02ArmSummary("channel_off", 8, 1.0, 0.0, 0.0),
        ),
        paired_contrasts=(),
        assay_failed=False,
        assay_failures=(),
        decision_rule_passed=False,
        decision_rule_failures=failures,
        e2_ordinal_ok=False,
        limitations=(),
    )


def test_rescore_keeps_the_ordinal_block_when_paired_contrasts_pass() -> None:
    scored = rescore_he02_campaign(
        _campaign(("no_holm_surviving_primary_contrast", "content_null_beats_channel_off"))
    )
    assert scored.claim_ceiling == CLAIM_CEILING
    assert scored.decision_rule_passed is False
    assert "content_null_beats_channel_off" in scored.decision_rule_failures
    assert "no_holm_surviving_primary_contrast" not in scored.decision_rule_failures
    assert all(item.dz is not None and item.dz > 0 for item in scored.paired_contrasts)


def test_rescore_drops_a_stale_contrast_failure_when_nothing_else_blocks() -> None:
    scored = rescore_he02_campaign(_campaign(("no_holm_surviving_primary_contrast",)))
    assert scored.decision_rule_passed is True
    assert scored.decision_rule_failures == ()
    assert scored.claim_ceiling == CLAIM_CEILING
