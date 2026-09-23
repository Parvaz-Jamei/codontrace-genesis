"""Phase 8: interaction continuum + VT × spatial factorial."""

from __future__ import annotations

import pytest

from codontrace.claimgate import HOST_PARASITE, audit_bundle
from codontrace.claimgate.adapters.host_parasite import (
    BLOCKED_HOST_PARASITE_CLAIMS,
    attach_interaction_continuum,
    attach_vt_spatial_factorial,
    bundle_from_host_parasite_cou,
    declare_interaction_continuum,
)
from codontrace.claimgate.adapters.host_parasite_prereg import (
    attach_host_parasite_preregistration,
    host_parasite_preregistration,
)
from codontrace.errors import ConfigurationError
from codontrace.genesis.host_parasite_continuum import run_vt_spatial_factorial
from codontrace.genesis.host_parasite_env import HostParasiteEnv


def test_interaction_value_modulates_steal_and_benefit() -> None:
    def score(iv: float) -> float:
        env = HostParasiteEnv(steal_fraction=0.8, interaction_value=iv)
        env.add_host("H0", ("and",))
        env.try_horizontal_inject(
            host_id="H0",
            parasite_id="P0",
            parasite_tasks=("and",),
            payload=(1,),
        )
        return env.host_retained_cpu("H0")

    assert score(-1.0) == pytest.approx(0.2)
    assert score(0.0) == pytest.approx(1.0)
    assert score(1.0) == pytest.approx(1.8)
    # Default preserves Phase 2 antagonism semantics.
    env = HostParasiteEnv(steal_fraction=0.8)
    assert env.interaction_value == -1.0


def test_mutualism_not_labeled_success() -> None:
    record = declare_interaction_continuum(interaction_value=0.7)
    assert record["pole"] == "mutualism"
    assert record["mutualism_equals_success"] is False
    assert record["raises_claim_ladder"] is False
    assert record["blocked_claims_unchanged"] is True
    assert set(BLOCKED_HOST_PARASITE_CLAIMS) == set(HOST_PARASITE.blocked_claims)


def test_vt_spatial_factorial_digests_contrast() -> None:
    result = run_vt_spatial_factorial(
        seeds=(1, 2),
        vt_levels=(0.0, 1.0),
        spatial_modes=("well_mixed", "local_neighborhood"),
        interaction_value=-1.0,
        request_claim_ceiling="candidate_evidence",
    )
    payload = result.to_dict()
    assert len(result.cells) == 4
    assert payload["mutualism_equals_success"] is False
    assert payload["red_queen_proved"] is False
    assert len(set(payload["cell_digests"].values())) >= 2
    assert "factorial_digest" in payload


def test_mutualism_cell_scores_higher_than_antagonism_not_success() -> None:
    ant = run_vt_spatial_factorial(
        seeds=(4,),
        vt_levels=(1.0,),
        spatial_modes=("well_mixed",),
        interaction_value=-1.0,
    )
    mut = run_vt_spatial_factorial(
        seeds=(4,),
        vt_levels=(1.0,),
        spatial_modes=("well_mixed",),
        interaction_value=1.0,
    )
    assert mut.cells[0].mean_score > ant.cells[0].mean_score
    assert mut.mutualism_equals_success is False
    assert mut.to_dict()["mutualism_equals_success"] is False


def test_attach_continuum_and_factorial_prereg_gate() -> None:
    factorial = run_vt_spatial_factorial(seeds=(9,), vt_levels=(0.0, 1.0))
    bundle = bundle_from_host_parasite_cou(
        question_of_interest="Does VT×spatial change digital outcomes?",
        context_of_use="Digital continuum only. Mutualism ≠ success.",
        model_influence=1,
        decision_consequence=1,
        treatment_scores=(0.2,),
        control_scores=(1.0,),
    )
    with_continuum = attach_interaction_continuum(bundle, interaction_value=0.25)
    assert with_continuum.extra["interaction_continuum"]["pole"] == "mutualism"
    assert set(HOST_PARASITE.blocked_claims) == set(BLOCKED_HOST_PARASITE_CLAIMS)
    with pytest.raises(ConfigurationError, match="preregistration"):
        attach_vt_spatial_factorial(with_continuum, factorial)
    prereg = host_parasite_preregistration(
        question_of_interest="Does VT×spatial change digital outcomes?",
        context_of_use="Digital continuum only. Mutualism ≠ success.",
        arms=("vt0_well_mixed", "vt1_local_neighborhood"),
        success_metrics=("cell_digest_contrast",),
    )
    ready = attach_host_parasite_preregistration(with_continuum, prereg)
    before = audit_bundle(ready).achieved_level
    attached = attach_vt_spatial_factorial(ready, factorial)
    assert "vt_spatial_factorial" in attached.extra
    assert attached.extra["vt_spatial_factorial"]["mutualism_equals_success"] is False
    assert audit_bundle(attached).achieved_level == before


def test_interaction_value_out_of_range_refused() -> None:
    with pytest.raises(ConfigurationError, match="\\[-1, \\+1\\]"):
        HostParasiteEnv(interaction_value=1.5)
    with pytest.raises(ConfigurationError, match="candidate_evidence"):
        run_vt_spatial_factorial(
            seeds=(1,),
            request_claim_ceiling="mechanism_support",
        )


def test_snapshot_declares_continuum() -> None:
    env = HostParasiteEnv(interaction_value=0.5, steal_fraction=0.4)
    env.add_host("H0", ("xor",))
    snap = env.snapshot()
    assert snap["interaction_value"] == 0.5
    assert snap["interaction_continuum"] == "antagonism_to_mutualism"
    assert snap["mutualism_equals_success"] is False

def test_spatial_mode_changes_injection_counts() -> None:
    local = run_vt_spatial_factorial(
        seeds=(11,),
        vt_levels=(0.0,),
        spatial_modes=("local_neighborhood",),
        interaction_value=-1.0,
    )
    mixed = run_vt_spatial_factorial(
        seeds=(11,),
        vt_levels=(0.0,),
        spatial_modes=("well_mixed",),
        interaction_value=-1.0,
    )
    # Well-mixed reaches H_far; local neighborhood does not.
    assert mixed.cells[0].injected_or_transmitted > local.cells[0].injected_or_transmitted
    assert mixed.cells[0].mean_score != local.cells[0].mean_score

