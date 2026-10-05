"""Regression: claims stay unsupported when a required gate is missing."""

from __future__ import annotations

import json
from copy import deepcopy
from dataclasses import replace
from pathlib import Path

import pytest

from codontrace.claimgate import audit_bundle
from codontrace.claimgate.adapters.biomedical import audit_biomedical_study
from codontrace.claimgate.adapters.codontrace import bundle_from_hard_experiment_01
from codontrace.claimgate.adapters.host_parasite import (
    attach_genome_diversity_campaign,
    bundle_from_host_parasite_cou,
)
from codontrace.claimgate.adapters.host_parasite_prereg import (
    attach_host_parasite_preregistration,
    host_parasite_preregistration,
)
from codontrace.claimgate.schema import ClaimgateComparison
from codontrace.errors import ConfigurationError
from codontrace.genesis.host_parasite_genome_diversity import (
    HYPOTHESIS,
    SCHEMA,
    GenomeDiversityCampaignResult,
)

FIXTURE = Path(__file__).resolve().parent / "fixtures" / "claimgate" / "level2_difference.json"


def _diversity_bundle():
    bundle = bundle_from_host_parasite_cou(
        question_of_interest="Can dual-null falsify parasites_always_raise_codon_entropy?",
        context_of_use="Digital genotype diversity only.",
        model_influence=1,
        decision_consequence=1,
        treatment_scores=(0.2,),
        control_scores=(1.0,),
    )
    prereg = host_parasite_preregistration(
        question_of_interest="Can dual-null falsify parasites_always_raise_codon_entropy?",
        context_of_use="Digital genotype diversity only.",
        arms=("biotic_intact", "content_null", "structure_null", "abiotic_stress"),
        success_metrics=("entropy_delta_vs_baseline",),
    )
    return attach_host_parasite_preregistration(bundle, prereg)


def _supported_campaign(*, failure_reason: str) -> GenomeDiversityCampaignResult:
    return GenomeDiversityCampaignResult(
        schema=SCHEMA,
        seeds=(1,),
        arms=("biotic_intact",),
        steps=1,
        host_count=2,
        arm_outcomes=(),
        hypothesis=HYPOTHESIS,
        hypothesis_supported=True,
        failure_reason=failure_reason,
        claim_ceiling="candidate_evidence",
        red_queen_proved=False,
        arms_are_distinct=False,
    )


def test_empty_diversity_evidence_cannot_be_marked_supported() -> None:
    ready = _diversity_bundle()
    with pytest.raises(ConfigurationError, match="falsification success"):
        attach_genome_diversity_campaign(ready, _supported_campaign(failure_reason=""))
    with pytest.raises(ConfigurationError, match="falsification success"):
        attach_genome_diversity_campaign(
            ready, _supported_campaign(failure_reason="not a falsification")
        )


def test_degenerate_interval_does_not_unlock_publication_grade() -> None:
    payload = json.loads(FIXTURE.read_text(encoding="utf-8"))
    payload["comparisons"] = [
        {
            "a": "on",
            "b": "off",
            "effect_size": 0.9,
            "ci_low": None,
            "ci_high": None,
            "p": 0.01,
            "test": "paired",
            "correction": "",
        },
        {
            "a": "on",
            "b": "off",
            "effect_size": 0.9,
            "ci_low": 1.0,
            "ci_high": 1.0,
            "p": 1.0,
            "test": "paired",
            "correction": "",
        },
    ]
    payload["arms"].append({"name": "off_gate", "role": "mechanism_ablation", "n": 16})
    payload["arms"].append({"name": "shuffled", "role": "negative_control", "n": 16})
    payload["replay"] = {"verified": True, "digests": ["d" * 64]}
    payload["seeds"] = list(range(16))
    payload["doi"] = "10.5281/zenodo.99999999"
    report = audit_bundle(payload)
    assert report.achieved_level < 4
    assert "confidence_interval" in report.missing_for_next

    inverted = deepcopy(payload)
    inverted["comparisons"][1]["ci_low"] = 2.0
    inverted["comparisons"][1]["ci_high"] = 0.1
    inverted_report = audit_bundle(inverted)
    assert inverted_report.achieved_level < 4
    assert "confidence_interval" in inverted_report.missing_for_next


def test_zero_width_or_inverted_interval_does_not_close_a_phenomenon() -> None:
    he01 = bundle_from_hard_experiment_01(Path("docs/hard_experiment_01/results_v7.json"))
    first = he01.comparisons[0]
    zero = ClaimgateComparison(
        first.a,
        first.b,
        first.effect_size,
        first.ci_low,
        first.ci_low,
        first.p,
        first.test,
        first.correction,
    )
    study = audit_biomedical_study(
        {
            "phenomena": (
                {
                    "name": "source_fitness_bias",
                    "importance": "high",
                    "arm": "source_bias_on",
                    "max_interval_width": 6.0,
                },
            )
        },
        experiment=replace(he01, comparisons=(zero,) + he01.comparisons[1:]),
    )
    assert "source_fitness_bias" not in study.executed
    assert "source_fitness_bias" in study.not_closed

    inverted = ClaimgateComparison(
        first.a,
        first.b,
        first.effect_size,
        first.ci_high,
        first.ci_low,
        first.p,
        first.test,
        first.correction,
    )
    inverted_study = audit_biomedical_study(
        {
            "phenomena": (
                {
                    "name": "source_fitness_bias",
                    "importance": "high",
                    "arm": "source_bias_on",
                },
            )
        },
        experiment=replace(he01, comparisons=(inverted,) + he01.comparisons[1:]),
    )
    assert "source_fitness_bias" not in inverted_study.executed
    assert "source_fitness_bias" in inverted_study.not_closed


def test_intelligence_and_red_queen_do_not_stay_supported() -> None:
    payload = json.loads(FIXTURE.read_text(encoding="utf-8"))
    baseline = audit_bundle(payload).achieved_level
    assert baseline >= 2
    for key in ("intelligence", "red_queen_proved", "agi"):
        marked = deepcopy(payload)
        marked[key] = True
        report = audit_bundle(marked)
        assert report.achieved_level < baseline
        assert any(key in item for item in report.warnings)
