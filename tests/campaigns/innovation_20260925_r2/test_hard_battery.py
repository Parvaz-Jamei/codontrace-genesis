"""Wave C — hard unsolved-style battery on FULL CodonTrace stack (R1+R2).

Targets phenomena beyond Round 1, ClaimGate-honest:
1. Persistent entropy + Mapper + Spectral separate reticulate vs disjoint structure.
2. Front-door mediation stays observational_bounds (beyond DiD).
3. TE/Granger-lite + conformal abstention on meter series.
4. ESS + sparse recovery + FARM + World + R1 meters + calib + export wired.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from codontrace.errors import ConfigurationError
from codontrace.genesis.host_parasite_analytics import (
    run_continuum_factorial,
    run_did_intervention_contrast,
    run_front_door_mediation_contrast,
)
from codontrace.genesis.host_parasite_calibration import run_calibration_suite
from codontrace.genesis.host_parasite_export import (
    meter_snapshot_rows,
    world_summary_row,
    write_csv_rows,
    write_json,
)
from codontrace.genesis.host_parasite_world import (
    HostParasiteProfile,
    HostParasiteWorld,
    assert_baic_pins_untouched,
)
from codontrace.life_loop import (
    AblationTemplate,
    FarmPlan,
    PhenotypeMap,
    PhenotypeRecord,
    PopulationRegistry,
    ScheduleLock,
    allele_outcome_association,
    apply_farm,
    betti_proxy,
    conformal_risk_band,
    contrast_phenotype_maps,
    ess_invasion_indicator,
    hook_meter_transfer_entropy,
    mapper_cover_proxy,
    persistent_entropy_proxy,
    skyline_ne_proxy,
    sparse_phenotype_recovery,
    spectral_laplacian_structure,
    topology_continuum_structure,
    write_hook_meter_csv,
)


def _reticulate_map() -> PhenotypeMap:
    return PhenotypeMap(
        map_id="retic",
        records=(
            PhenotypeRecord(member_id="h0", feature_tags=("r1", "r2", "core")),
            PhenotypeRecord(member_id="h1", feature_tags=("r2", "r3", "core")),
            PhenotypeRecord(member_id="h2", feature_tags=("r3", "r1", "core")),
            PhenotypeRecord(member_id="p0", feature_tags=("r1", "atk")),
            PhenotypeRecord(member_id="p1", feature_tags=("r2", "atk", "extra")),
            PhenotypeRecord(member_id="p2", feature_tags=("r3", "atk", "x", "y")),
        ),
    )


def _disjoint_map() -> PhenotypeMap:
    return PhenotypeMap(
        map_id="disj",
        records=(
            PhenotypeRecord(member_id="h0", feature_tags=("a",)),
            PhenotypeRecord(member_id="h1", feature_tags=("b", "c")),
            PhenotypeRecord(member_id="h2", feature_tags=("d", "e", "f")),
            PhenotypeRecord(member_id="p0", feature_tags=("x",)),
            PhenotypeRecord(member_id="p1", feature_tags=("y", "z")),
            PhenotypeRecord(member_id="p2", feature_tags=("u", "v", "w", "t")),
        ),
    )


def test_hard_r2_topology_stack_beyond_betti() -> None:
    """Persistent entropy + Mapper + Spectral separate structure; R1 betti still works."""

    retic = _reticulate_map()
    disj = _disjoint_map()
    pe_r = persistent_entropy_proxy(retic, snapshot_id="pe_r", normalize=False)
    pe_d = persistent_entropy_proxy(disj, snapshot_id="pe_d", normalize=False)
    assert pe_r.n_bars >= 1 and pe_d.n_bars >= 1
    # reticulate shared tags → shorter merge distances on average than disjoint
    assert pe_r.mean_lifetime < pe_d.mean_lifetime

    map_r = mapper_cover_proxy(retic, snapshot_id="mc_r", n_lens_bins=3, overlap_threshold=0.15)
    map_d = mapper_cover_proxy(disj, snapshot_id="mc_d", n_lens_bins=3, overlap_threshold=0.15)
    assert map_r.n_bins >= 2
    # reticulate cover should be more connected (fewer components or more edges)
    assert map_r.n_edges >= map_d.n_edges or map_r.n_components <= map_d.n_components

    sp_r = spectral_laplacian_structure(retic, snapshot_id="sp_r")
    sp_d = spectral_laplacian_structure(disj, snapshot_id="sp_d")
    assert sp_r.fiedler_value > sp_d.fiedler_value

    # R1 betti still distinguishes
    b_r = betti_proxy(retic, snapshot_id="b_r", epsilon=0.2)
    b_d = betti_proxy(disj, snapshot_id="b_d", epsilon=0.2)
    assert b_r.beta1_proxy >= b_d.beta1_proxy
    structure = topology_continuum_structure((b_r, b_d))
    assert structure["arms_race_proved"] is False
    assert pe_r.arms_race_proved is False


def test_hard_r2_front_door_beyond_did() -> None:
    """Front-door mediation contrast + DiD both observational_bounds."""

    fd = run_front_door_mediation_contrast(
        contrast_id="hard_fd",
        seed=7,
        ticks=2,
        treat_schedule_arm="freeze",
        control_schedule_arm="none",
        mediator_channel="match_pass",
        outcome_channel="coupling_total",
        claim_role="exploratory",
        smoke_only=False,
        claim_ceiling="candidate_evidence",
    )
    assert fd.identifiability == "observational_bounds"
    assert fd.intervention_supported is False
    assert fd.front_door_identified is False
    assert "intervention_supported" in fd.refuse_list
    assert any(c.role == "dual_null" for c in fd.cells)

    did = run_did_intervention_contrast(
        contrast_id="hard_did_r2",
        seed=7,
        pre_ticks=1,
        post_ticks=2,
        treat_schedule_arm="freeze",
        primary_channel="coupling_total",
    )
    assert did.identifiability == "observational_bounds"
    # distinct schemas / digests
    assert fd.digest != did.digest


def test_hard_r2_te_conformal_meter_stack() -> None:
    """TE/Granger-lite on synthetic meter path + conformal selective abstention."""

    # driven series: match_pass leads coupling
    match = (0.0, 1.0, 2.0, 3.0, 4.0, 5.0, 6.0)
    coupling = (0.0, 0.2, 1.1, 2.0, 3.2, 4.1, 5.0)
    te = hook_meter_transfer_entropy(
        match,
        coupling,
        result_id="hard_te",
        source_key="match_pass",
        target_key="coupling_total",
    )
    assert te.granger_lite > 0.0
    assert te.causality_proved is False

    # conformal around TE score using fake calibration residuals
    band_ok = conformal_risk_band(
        result_id="hard_cb_ok",
        point_prediction=te.granger_lite,
        calibration_residuals=(0.02, 0.03, 0.01, 0.04, 0.025),
        alpha=0.2,
        max_width=1.0,
    )
    assert band_ok.abstained is False
    assert band_ok.lower <= te.granger_lite <= band_ok.upper

    band_abs = conformal_risk_band(
        result_id="hard_cb_abs",
        point_prediction=te.granger_lite,
        calibration_residuals=(2.0, 2.5, 3.0, 2.2),
        alpha=0.1,
        max_width=0.5,
    )
    assert band_abs.abstained is True
    assert band_abs.coverage_guaranteed_proved is False


def test_hard_r2_ess_sparse_compose() -> None:
    """ESS candidate + sparse recovery on reticulate map; ClaimGate refuses."""

    retic = _reticulate_map()
    ess = ess_invasion_indicator(retic, result_id="hard_ess", resident_id="h0")
    assert ess.ess_proved is False
    # h0 has core+r1+r2 — may or may not be ESS; just check structure
    assert isinstance(ess.ess_candidate, bool)
    assert len(ess.scores) == 5

    outcomes = {
        "h0": 1.0,
        "h1": 1.0,
        "h2": 1.0,
        "p0": 0.0,
        "p1": 0.0,
        "p2": 0.0,
    }
    sparse = sparse_phenotype_recovery(
        retic, outcomes, result_id="hard_sp", soft_threshold=0.05, n_iters=10
    )
    assert sparse.support_size >= 1
    assert sparse.gene_identity_proved is False
    assert sparse.locus_identity_proved is False

    # allele R1 still composes
    allele = allele_outcome_association(
        retic,
        {k: bool(v) for k, v in outcomes.items()},
        result_id="hard_al",
    )
    assert allele.gene_identity_proved is False


def test_hard_r2_full_stack_world_farm_export_calib(tmp_path: Path) -> None:
    """FULL stack: World + R1 + R2 + FarmPlan + calib + export; BAIC pins."""

    assert_baic_pins_untouched()
    profile = HostParasiteProfile(
        profile_id="hard_r2_full",
        seed=42,
        coupling_amount=0.4,
        spatial_mode="well_mixed",
        inherit_probability=0.3,
        inherit_mode="copy",
        match_score_scale=1.0,
        schedule_arm="none",
        ablation_preset="none",
        match_rule_id="feature_overlap",
        phenotype_tags={
            "prim_0": ("r1", "core"),
            "prim_1": ("r2", "core"),
            "sec_0": ("r1", "atk"),
            "sec_1": ("r2", "atk"),
        },
        contact_probability=1.0,
    )
    world = HostParasiteWorld(profile)
    world.run(4)
    snap = world.meter.snapshot()
    assert snap.digest

    pm = _reticulate_map()
    pe = persistent_entropy_proxy(pm, snapshot_id="full_pe")
    sp = spectral_laplacian_structure(pm, snapshot_id="full_sp")
    mc = mapper_cover_proxy(pm, snapshot_id="full_mc", n_lens_bins=3)
    assert pe.digest and sp.digest and mc.digest

    series_match = [
        float(snap.related_counts.get("match_pass", 0) + t) for t in range(4)
    ]
    series_coup = [
        float(snap.related_totals.get("coupling_total", 0.0) + 0.5 * t) for t in range(4)
    ]
    te = hook_meter_transfer_entropy(series_match, series_coup, result_id="full_te")
    band = conformal_risk_band(
        result_id="full_cb",
        point_prediction=te.granger_lite,
        calibration_residuals=(0.05, 0.08, 0.04, 0.07),
        alpha=0.2,
    )
    assert band.coverage_guaranteed_proved is False

    related = dict(snap.related_counts)
    totals = dict(snap.related_totals)
    sky = skyline_ne_proxy(
        [
            {
                "window_id": "early",
                "tick_start": 0,
                "tick_end": 2,
                "birth_count": float(related.get("birth_count", 0)),
                "death_count": float(related.get("death_count", 0)),
                "attach_occupancy": float(totals.get("attach_occupancy", 0.0)) / 2.0,
            },
            {
                "window_id": "late",
                "tick_start": 2,
                "tick_end": 4,
                "birth_count": float(related.get("birth_count", 0)) + 1,
                "death_count": float(related.get("death_count", 0)),
                "attach_occupancy": float(totals.get("attach_occupancy", 0.0)),
            },
        ],
        series_id="full_sky",
    )
    assert sky.epidemic_forecast_certified is False

    plan = FarmPlan(
        plan_id="full_farm",
        fault_ablation_mode="structure_null",
        activation_lock_mode="freeze",
        activation_tick=0,
    )
    template = AblationTemplate(
        arm_id="full_arm",
        mode="structure_null",
        content_keys=("payload",),
        structure_keys=("link",),
    )
    lock = ScheduleLock(schedule_id="full_sch", lock_mode="unlock", population_id="pop_a")
    registry = PopulationRegistry().create_population("pop_a", member_ids=("m1",))
    farm_rec, *_rest = apply_farm(
        plan,
        ablation_template=template,
        bag={"payload": 1, "link": "g"},
        schedule_lock=lock,
        registry=registry,
        live_bags={"m1": {"payload": 1}},
    )
    assert farm_rec.intervention_supported is False

    fd = run_front_door_mediation_contrast(contrast_id="full_fd", seed=42, ticks=1)
    continuum = run_continuum_factorial(
        factorial_id="full_cont_r2",
        seeds=(0,),
        ticks=1,
        coupling_levels=(0.2, 0.6),
        spatial_modes=("well_mixed",),
        inherit_levels=(0.0,),
        match_score_scales=(1.0,),
    )
    assert continuum.cells
    assert fd.identifiability == "observational_bounds"

    write_hook_meter_csv(snap, tmp_path / "hooks.csv")
    write_csv_rows(meter_snapshot_rows(snap), tmp_path / "meters.csv")
    write_json(
        {
            "persistent_entropy": pe.to_dict(),
            "spectral": sp.to_dict(),
            "mapper": mc.to_dict(),
            "te": te.to_dict(),
            "conformal": band.to_dict(),
            "skyline": sky.to_dict(),
            "front_door": fd.to_dict(),
            "world": world_summary_row(world.summary()),
        },
        tmp_path / "r2_stack.json",
    )
    assert (tmp_path / "r2_stack.json").exists()

    calib = run_calibration_suite(report_id="hard_r2_calib")
    assert calib.red_queen_proved is False
    assert calib.raises_claim_ladder is False

    assert_baic_pins_untouched()


def test_hard_r2_claimgate_refuses_still_hard() -> None:
    """Scientific refuses remain hard — no soft-pass."""

    from codontrace.life_loop.persistent_entropy import PersistentEntropySnapshot
    from codontrace.genesis.host_parasite_analytics import FrontDoorMediationContrast

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

    fd = run_front_door_mediation_contrast(contrast_id="refuse_fd", seed=0, ticks=1)
    with pytest.raises(ConfigurationError, match="front_door_identified"):
        FrontDoorMediationContrast(
            contrast_id=fd.contrast_id,
            cells=fd.cells,
            front_door_estimate=fd.front_door_estimate,
            effect_lower=fd.effect_lower,
            effect_upper=fd.effect_upper,
            dual_null_delta=fd.dual_null_delta,
            mediator_channel=fd.mediator_channel,
            outcome_channel=fd.outcome_channel,
            front_door_identified=True,
        )


def test_hard_r2_no_engine_infection_physics() -> None:
    """Static guard: R2 campaign modules must not import engine infection physics."""

    repo = Path(__file__).resolve().parents[3]
    life_loop = repo / "src" / "codontrace" / "life_loop"
    for name in (
        "persistent_entropy.py",
        "mapper_cover.py",
        "spectral_structure.py",
        "transfer_entropy.py",
        "conformal_bands.py",
        "ess_invasion.py",
        "sparse_recovery.py",
    ):
        text = (life_loop / name).read_text()
        assert "codontrace.engine" not in text
        assert "HostParasiteEnv" not in text
        lowered = text.casefold()
        for banned in ("virulence", "infection_physics", "phage_therapy"):
            assert banned not in lowered
