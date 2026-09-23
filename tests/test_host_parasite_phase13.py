"""Phase 13: declared task–gene map digests (optional earn-in)."""

from __future__ import annotations

import pytest

from codontrace.claimgate import audit_bundle
from codontrace.claimgate.adapters.host_parasite import (
    attach_task_gene_map,
    bundle_from_host_parasite_cou,
)
from codontrace.claimgate.adapters.host_parasite_prereg import (
    attach_host_parasite_preregistration,
    host_parasite_preregistration,
)
from codontrace.errors import ConfigurationError
from codontrace.genesis.host_parasite_task_gene import build_task_gene_map


def test_task_gene_map_digests_refuse_identity() -> None:
    result = build_task_gene_map(seed=7, genome_length=12, window_width=2)
    payload = result.to_dict()
    assert payload["gene_identity_proved"] is False
    assert payload["crispr_identity_proved"] is False
    assert payload["red_queen_proved"] is False
    assert payload["raises_claim_ladder"] is False
    assert len(payload["windows"]) >= 2
    assert payload["map_digest"]
    assert all(w["gene_identity_proved"] is False for w in payload["windows"])
    labels = [w["task_label"] for w in payload["windows"]]
    assert len(labels) == len(set(labels))


def test_task_gene_map_deterministic() -> None:
    a = build_task_gene_map(seed=11)
    b = build_task_gene_map(seed=11)
    assert a.to_dict()["map_digest"] == b.to_dict()["map_digest"]
    assert a.to_dict()["digest"] == b.to_dict()["digest"]


def test_task_gene_map_refuses_high_ceiling() -> None:
    with pytest.raises(ConfigurationError, match="candidate_evidence"):
        build_task_gene_map(seed=1, request_claim_ceiling="mechanism_support")


def test_attach_task_gene_map_requires_prereg() -> None:
    mapping = build_task_gene_map(seed=3)
    bundle = bundle_from_host_parasite_cou(
        question_of_interest="Do declared codon windows map to task labels?",
        context_of_use="Digital declared phenotype link only. Gene identity unproved.",
        model_influence=1,
        decision_consequence=1,
        treatment_scores=(0.2,),
        control_scores=(1.0,),
    )
    with pytest.raises(ConfigurationError, match="preregistration"):
        attach_task_gene_map(bundle, mapping)
    prereg = host_parasite_preregistration(
        question_of_interest="Do declared codon windows map to task labels?",
        context_of_use="Digital declared phenotype link only. Gene identity unproved.",
        arms=("task_gene_map",),
        success_metrics=("map_digest",),
    )
    ready = attach_host_parasite_preregistration(bundle, prereg)
    before = audit_bundle(ready).achieved_level
    attached = attach_task_gene_map(ready, mapping)
    assert attached.extra["task_gene_map"]["gene_identity_proved"] is False
    assert attached.extra["task_gene_map"]["crispr_identity_proved"] is False
    assert audit_bundle(attached).achieved_level == before
    with pytest.raises(ConfigurationError, match="already attached"):
        attach_task_gene_map(attached, mapping)
