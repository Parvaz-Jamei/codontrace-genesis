"""Phase 11: codon-entropy / Hamming dual-null (HE02 honesty)."""

from __future__ import annotations

import pytest

from codontrace.claimgate import audit_bundle
from codontrace.claimgate.adapters.host_parasite import (
    attach_genome_diversity_campaign,
    bundle_from_host_parasite_cou,
)
from codontrace.claimgate.adapters.host_parasite_prereg import (
    attach_host_parasite_preregistration,
    host_parasite_preregistration,
)
from codontrace.errors import ConfigurationError
from codontrace.genesis.host_parasite_genome_diversity import (
    HYPOTHESIS,
    run_genome_diversity_campaign,
)


def test_diversity_assay_can_fail_universal_entropy_claim() -> None:
    result = run_genome_diversity_campaign(
        seeds=(1, 2),
        steps=3,
        request_claim_ceiling="candidate_evidence",
    )
    assert result.hypothesis == HYPOTHESIS
    assert result.hypothesis_supported is False
    assert "abiotic_stress" in result.failure_reason or "content_null" in result.failure_reason
    assert result.red_queen_proved is False
    by_arm: dict[str, list[float]] = {}
    for item in result.arm_outcomes:
        by_arm.setdefault(item.arm, []).append(item.entropy_delta_vs_baseline)
    assert sum(by_arm["biotic_intact"]) / len(by_arm["biotic_intact"]) > 0
    assert sum(by_arm["abiotic_stress"]) / len(by_arm["abiotic_stress"]) <= 0
    assert sum(by_arm["content_null"]) / len(by_arm["content_null"]) <= 0
    assert sum(by_arm["structure_null"]) / len(by_arm["structure_null"]) <= 0
    payload = result.to_dict()
    assert payload["arms_are_distinct"] is True
    assert len(set(payload["arm_digests"].values())) == 4
    assert payload["he02_honesty"] == "dual_null_genotype_observables"
    sample = result.arm_outcomes[0].to_dict()
    assert "mean_genome_distance" in sample
    assert "unique_genome_count" in sample
    assert "codon_usage_entropy" in sample


def test_diversity_refuses_high_ceiling() -> None:
    with pytest.raises(ConfigurationError, match="candidate_evidence"):
        run_genome_diversity_campaign(
            seeds=(1,),
            request_claim_ceiling="mechanism_support",
        )


def test_diversity_deterministic_digests() -> None:
    a = run_genome_diversity_campaign(seeds=(9, 10), steps=2)
    b = run_genome_diversity_campaign(seeds=(9, 10), steps=2)
    assert a.to_dict()["campaign_digest"] == b.to_dict()["campaign_digest"]


def test_attach_genome_diversity_requires_prereg() -> None:
    campaign = run_genome_diversity_campaign(seeds=(4,), steps=2)
    bundle = bundle_from_host_parasite_cou(
        question_of_interest="Can dual-null falsify parasites_always_raise_codon_entropy?",
        context_of_use="Digital genotype diversity only.",
        model_influence=1,
        decision_consequence=1,
        treatment_scores=(0.2,),
        control_scores=(1.0,),
    )
    with pytest.raises(ConfigurationError, match="preregistration"):
        attach_genome_diversity_campaign(bundle, campaign)
    prereg = host_parasite_preregistration(
        question_of_interest="Can dual-null falsify parasites_always_raise_codon_entropy?",
        context_of_use="Digital genotype diversity only.",
        arms=("biotic_intact", "content_null", "structure_null", "abiotic_stress"),
        success_metrics=("entropy_delta_vs_baseline", "arm_digest_distinctness"),
    )
    ready = attach_host_parasite_preregistration(bundle, prereg)
    before = audit_bundle(ready).achieved_level
    attached = attach_genome_diversity_campaign(ready, campaign)
    assert attached.extra["genome_diversity_campaign"]["hypothesis_supported"] is False
    assert attached.extra["genome_diversity_campaign"]["red_queen_proved"] is False
    assert attached.extra["genome_diversity_campaign"]["preregistration_digest"] == str(
        prereg.to_dict()["digest"]
    )
    assert audit_bundle(attached).achieved_level == before
    with pytest.raises(ConfigurationError, match="already attached"):
        attach_genome_diversity_campaign(attached, campaign)
