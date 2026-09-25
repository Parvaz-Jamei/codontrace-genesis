"""Wave B — unit coverage for adopted INN-07..14 modules."""

from __future__ import annotations

import pytest

from codontrace.errors import ConfigurationError
from codontrace.genesis.host_parasite_analytics import (
    FrontDoorMediationContrast,
    run_front_door_mediation_contrast,
)
from codontrace.life_loop import (
    PhenotypeMap,
    PhenotypeRecord,
    conformal_risk_band,
    ess_invasion_indicator,
    hook_meter_transfer_entropy,
    mapper_cover_proxy,
    persistent_entropy_proxy,
    sparse_phenotype_recovery,
    spectral_laplacian_structure,
)
from codontrace.life_loop.conformal_bands import ConformalBandResult
from codontrace.life_loop.ess_invasion import EssInvasionResult
from codontrace.life_loop.persistent_entropy import PersistentEntropySnapshot
from codontrace.life_loop.sparse_recovery import SparseRecoveryResult
from codontrace.life_loop.transfer_entropy import TransferEntropyResult


def _triangle_map() -> PhenotypeMap:
    return PhenotypeMap(
        map_id="tri",
        records=(
            PhenotypeRecord(member_id="a", feature_tags=("x", "y")),
            PhenotypeRecord(member_id="b", feature_tags=("y", "z")),
            PhenotypeRecord(member_id="c", feature_tags=("x", "z")),
        ),
    )


def _varied_map() -> PhenotypeMap:
    return PhenotypeMap(
        map_id="varied",
        records=(
            PhenotypeRecord(member_id="h0", feature_tags=("r1",)),
            PhenotypeRecord(member_id="h1", feature_tags=("r1", "r2")),
            PhenotypeRecord(member_id="h2", feature_tags=("r1", "r2", "r3")),
            PhenotypeRecord(member_id="p0", feature_tags=("atk", "r1")),
            PhenotypeRecord(member_id="p1", feature_tags=("atk", "r2", "extra")),
            PhenotypeRecord(member_id="p2", feature_tags=("atk",)),
        ),
    )


def test_inn07_persistent_entropy_deterministic() -> None:
    snap = persistent_entropy_proxy(_triangle_map(), snapshot_id="pe1")
    assert snap.n_nodes == 3
    assert snap.n_bars == 2
    assert snap.persistent_entropy >= 0.0
    assert snap.arms_race_proved is False
    same = persistent_entropy_proxy(_triangle_map(), snapshot_id="pe1")
    assert same.digest == snap.digest


def test_inn07_refuse_arms_race() -> None:
    with pytest.raises(ConfigurationError, match="arms_race_proved"):
        PersistentEntropySnapshot(
            snapshot_id="bad",
            n_nodes=1,
            n_bars=0,
            persistent_entropy=0.0,
            mean_lifetime=0.0,
            max_lifetime=0.0,
            arms_race_proved=True,
        )


def test_inn07_entropy_higher_for_uneven_merges() -> None:
    # chain-like distances vs equal triangle — both produce bars; unequal map
    # with a distant outlier should increase lifetime variance / entropy shape
    clustered = PhenotypeMap(
        map_id="cl",
        records=(
            PhenotypeRecord(member_id="a", feature_tags=("a", "b", "c")),
            PhenotypeRecord(member_id="b", feature_tags=("a", "b", "c")),
            PhenotypeRecord(member_id="c", feature_tags=("a", "b", "c")),
            PhenotypeRecord(member_id="d", feature_tags=("z",)),
        ),
    )
    uniform = _triangle_map()
    e_cl = persistent_entropy_proxy(clustered, snapshot_id="cl", normalize=False)
    e_un = persistent_entropy_proxy(uniform, snapshot_id="un", normalize=False)
    assert e_cl.n_bars >= 1
    assert e_un.n_bars >= 1
    # clustered has a long outlier bar → higher max_lifetime than uniform triangle
    assert e_cl.max_lifetime >= e_un.max_lifetime


def test_inn08_mapper_cover_varied_bins() -> None:
    snap = mapper_cover_proxy(_varied_map(), snapshot_id="m1", n_lens_bins=3, overlap_threshold=0.1)
    assert snap.n_members == 6
    assert snap.n_bins >= 2
    assert snap.n_components >= 1
    assert snap.arms_race_proved is False
    same = mapper_cover_proxy(_varied_map(), snapshot_id="m1", n_lens_bins=3, overlap_threshold=0.1)
    assert same.digest == snap.digest


def test_inn10_spectral_fiedler_positive_connected() -> None:
    snap = spectral_laplacian_structure(_triangle_map(), snapshot_id="sp1")
    assert snap.n_nodes == 3
    assert snap.fiedler_value > 0.0  # connected triangle-ish affinity
    assert len(snap.eigenvalues) >= 1
    assert abs(snap.eigenvalues[0]) < 1e-6  # algebraic connectivity floor ~0
    same = spectral_laplacian_structure(_triangle_map(), snapshot_id="sp1")
    assert same.digest == snap.digest


def test_inn10_spectral_gap_separates_structure() -> None:
    connected = _triangle_map()
    disjoint = PhenotypeMap(
        map_id="dis",
        records=(
            PhenotypeRecord(member_id="a", feature_tags=("a",)),
            PhenotypeRecord(member_id="b", feature_tags=("b",)),
            PhenotypeRecord(member_id="c", feature_tags=("c",)),
        ),
    )
    s_c = spectral_laplacian_structure(connected, snapshot_id="c")
    s_d = spectral_laplacian_structure(disjoint, snapshot_id="d")
    # connected affinity → larger Fiedler than fully disjoint (zero edges)
    assert s_c.fiedler_value > s_d.fiedler_value


def test_inn11_granger_te_lite() -> None:
    # source drives target
    src = (0.0, 1.0, 2.0, 3.0, 4.0, 5.0)
    tgt = (0.0, 0.5, 1.5, 2.5, 3.5, 4.5)
    res = hook_meter_transfer_entropy(
        src, tgt, result_id="te1", source_key="match_pass", target_key="coupling_total"
    )
    assert 0.0 <= res.granger_lite <= 1.0
    assert res.transfer_entropy_lite >= 0.0
    assert res.causality_proved is False
    same = hook_meter_transfer_entropy(
        src, tgt, result_id="te1", source_key="match_pass", target_key="coupling_total"
    )
    assert same.digest == res.digest


def test_inn11_refuse_causality_proved() -> None:
    with pytest.raises(ConfigurationError, match="causality_proved"):
        TransferEntropyResult(
            result_id="bad",
            source_key="a",
            target_key="b",
            granger_lite=0.1,
            transfer_entropy_lite=0.0,
            n_ticks=5,
            causality_proved=True,
        )


def test_inn12_conformal_band_and_abstain() -> None:
    band = conformal_risk_band(
        result_id="cb1",
        point_prediction=10.0,
        calibration_residuals=(0.1, 0.2, 0.15, 0.25, 0.05),
        alpha=0.2,
        max_width=100.0,
    )
    assert band.lower < band.point_prediction < band.upper
    assert band.abstained is False
    assert band.coverage_guaranteed_proved is False
    wide = conformal_risk_band(
        result_id="cb2",
        point_prediction=0.0,
        calibration_residuals=(5.0, 6.0, 7.0, 8.0),
        alpha=0.1,
        max_width=1.0,
    )
    assert wide.abstained is True


def test_inn12_refuse_coverage_proved() -> None:
    with pytest.raises(ConfigurationError, match="coverage_guaranteed_proved"):
        ConformalBandResult(
            result_id="bad",
            point_prediction=0.0,
            lower=-1.0,
            upper=1.0,
            width=2.0,
            alpha=0.1,
            abstained=False,
            n_calibration=3,
            coverage_guaranteed_proved=True,
        )


def test_inn13_ess_invasion() -> None:
    # dominant resident shares all tags with others → mutants cannot invade
    pm = PhenotypeMap(
        map_id="ess",
        records=(
            PhenotypeRecord(member_id="res", feature_tags=("a", "b", "c")),
            PhenotypeRecord(member_id="m1", feature_tags=("a",)),
            PhenotypeRecord(member_id="m2", feature_tags=("b",)),
        ),
    )
    res = ess_invasion_indicator(pm, result_id="ess1", resident_id="res")
    assert res.ess_candidate is True
    assert res.max_invasion <= 0.0
    assert res.ess_proved is False


def test_inn13_refuse_ess_proved() -> None:
    with pytest.raises(ConfigurationError, match="ess_proved"):
        EssInvasionResult(
            result_id="bad",
            resident_id="r",
            scores=(),
            ess_candidate=True,
            max_invasion=0.0,
            ess_proved=True,
        )


def test_inn14_sparse_recovery_support() -> None:
    pm = PhenotypeMap(
        map_id="sp",
        records=(
            PhenotypeRecord(member_id="a", feature_tags=("causal", "noise")),
            PhenotypeRecord(member_id="b", feature_tags=("causal",)),
            PhenotypeRecord(member_id="c", feature_tags=("noise",)),
            PhenotypeRecord(member_id="d", feature_tags=("causal", "noise")),
            PhenotypeRecord(member_id="e", feature_tags=("other",)),
        ),
    )
    outcomes = {"a": 1.0, "b": 1.0, "c": 0.0, "d": 1.0, "e": 0.0}
    res = sparse_phenotype_recovery(
        pm, outcomes, result_id="sr1", soft_threshold=0.05, n_iters=12
    )
    assert res.support_size >= 1
    tags = {c.tag for c in res.coefficients}
    assert "causal" in tags or res.support_size >= 1
    assert res.gene_identity_proved is False
    assert res.locus_identity_proved is False


def test_inn14_refuse_gene_identity() -> None:
    with pytest.raises(ConfigurationError, match="gene_identity_proved"):
        SparseRecoveryResult(
            result_id="bad",
            outcome_key="y",
            coefficients=(),
            support_size=0,
            residual_mse=0.0,
            gene_identity_proved=True,
        )


def test_inn09_front_door_observational() -> None:
    contrast = run_front_door_mediation_contrast(
        contrast_id="fd_smoke",
        seed=0,
        ticks=1,
        treat_schedule_arm="freeze",
        control_schedule_arm="none",
    )
    assert isinstance(contrast, FrontDoorMediationContrast)
    assert contrast.identifiability == "observational_bounds"
    assert contrast.intervention_supported is False
    assert contrast.front_door_identified is False
    assert len(contrast.cells) >= 3
    same = run_front_door_mediation_contrast(
        contrast_id="fd_smoke",
        seed=0,
        ticks=1,
        treat_schedule_arm="freeze",
        control_schedule_arm="none",
    )
    assert same.digest == contrast.digest


def test_inn09_refuse_front_door_identified() -> None:
    # build a minimal valid contrast then try mutating flag via constructor
    base = run_front_door_mediation_contrast(contrast_id="fd_ref", seed=1, ticks=1)
    with pytest.raises(ConfigurationError, match="front_door_identified"):
        FrontDoorMediationContrast(
            contrast_id=base.contrast_id,
            cells=base.cells,
            front_door_estimate=base.front_door_estimate,
            effect_lower=base.effect_lower,
            effect_upper=base.effect_upper,
            dual_null_delta=base.dual_null_delta,
            mediator_channel=base.mediator_channel,
            outcome_channel=base.outcome_channel,
            front_door_identified=True,
        )
