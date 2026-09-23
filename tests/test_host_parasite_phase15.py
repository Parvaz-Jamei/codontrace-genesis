"""Phase 15: genome × VT × spatial × continuum factorial digests."""

from __future__ import annotations

import pytest

from codontrace.claimgate import audit_bundle
from codontrace.claimgate.adapters.host_parasite import (
    attach_genome_vt_spatial_continuum_factorial,
    bundle_from_host_parasite_cou,
)
from codontrace.claimgate.adapters.host_parasite_prereg import (
    attach_host_parasite_preregistration,
    host_parasite_preregistration,
)
from codontrace.errors import ConfigurationError
from codontrace.genesis.host_parasite_genome_factorial import (
    run_genome_vt_spatial_continuum_factorial,
)


def test_genome_factorial_cells_distinct_and_mutualism_not_success() -> None:
    result = run_genome_vt_spatial_continuum_factorial(
        seeds=(1, 2),
        request_claim_ceiling="candidate_evidence",
    )
    assert result.cells_are_distinct is True
    assert result.mutualism_equals_success is False
    assert result.red_queen_proved is False
    assert result.major_transition_proved is False
    payload = result.to_dict()
    assert len(payload["cell_digests"]) == len(result.cells) == 8
    assert len(set(payload["cell_digests"].values())) == 8
    assert payload["cross_wave"] == "wave2_continuum_x_wave3_genomes"
    for cell in result.cells:
        assert cell.host_genome_digest
        assert cell.parasite_genome_digest
        assert cell.to_dict()["mutualism_equals_success"] is False


def test_genome_factorial_deterministic_and_refuses_high_ceiling() -> None:
    a = run_genome_vt_spatial_continuum_factorial(seeds=(3, 4))
    b = run_genome_vt_spatial_continuum_factorial(seeds=(3, 4))
    assert a.to_dict()["factorial_digest"] == b.to_dict()["factorial_digest"]
    with pytest.raises(ConfigurationError, match="candidate_evidence|request_claim_ceiling"):
        run_genome_vt_spatial_continuum_factorial(
            seeds=(1,),
            request_claim_ceiling="mechanism_support",
        )


def test_attach_genome_factorial_requires_prereg() -> None:
    factorial = run_genome_vt_spatial_continuum_factorial(
        seeds=(5,),
        request_claim_ceiling="candidate_evidence",
    )
    bundle = bundle_from_host_parasite_cou(
        question_of_interest="Do genome digests differ across VT×spatial×continuum cells?",
        context_of_use="Digital genome×continuum factorial only.",
        model_influence=1,
        decision_consequence=1,
        treatment_scores=(0.3,),
        control_scores=(1.0,),
    )
    with pytest.raises(ConfigurationError, match="preregistration"):
        attach_genome_vt_spatial_continuum_factorial(bundle, factorial)
    prereg = host_parasite_preregistration(
        question_of_interest="Do genome digests differ across VT×spatial×continuum cells?",
        context_of_use="Digital genome×continuum factorial only.",
        arms=("genome_factorial_grid",),
        success_metrics=("cell_digest", "host_genome_digest"),
    )
    ready = attach_host_parasite_preregistration(bundle, prereg)
    before = audit_bundle(ready).achieved_level
    attached = attach_genome_vt_spatial_continuum_factorial(ready, factorial)
    record = attached.extra["genome_vt_spatial_continuum_factorial"]
    assert record["cells_are_distinct"] is True
    assert record["mutualism_equals_success"] is False
    assert record["major_transition_proved"] is False
    assert audit_bundle(attached).achieved_level == before
    with pytest.raises(ConfigurationError, match="already attached"):
        attach_genome_vt_spatial_continuum_factorial(attached, factorial)
