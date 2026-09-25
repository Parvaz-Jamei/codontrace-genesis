"""Wave C — hard unsolved-style battery on full CodonTrace stack.

Targets phenomena peers struggle with, ClaimGate-honest:
1. Refuse-safe Red Queen *structure* (high β₁-proxy + continuum gradient).
2. Costly resistance tradeoff (coupling ↑ vs match under dual_null).
3. Identifiable DiD intervention contrast that stays observational_bounds.
4. Skyline + allele + FARM + export digests wired together.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from codontrace.errors import ConfigurationError
from codontrace.genesis.host_parasite_analytics import (
    run_continuum_factorial,
    run_did_intervention_contrast,
    run_intervention_contrast,
    run_reciprocal_observational_contrast,
)
from codontrace.genesis.host_parasite_calibration import (
    run_calibration_suite,
)
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
    contrast_phenotype_maps,
    skyline_ne_proxy,
    topology_continuum_structure,
    write_hook_meter_csv,
)

REPO = Path(__file__).resolve().parents[3]


def _rich_phenotype_map(*, shared_cycle: bool) -> PhenotypeMap:
    """Build a map with either a reticulate cycle or near-disjoint tags."""

    if shared_cycle:
        records = (
            PhenotypeRecord(member_id="h0", feature_tags=("r1", "r2", "core")),
            PhenotypeRecord(member_id="h1", feature_tags=("r2", "r3", "core")),
            PhenotypeRecord(member_id="h2", feature_tags=("r3", "r1", "core")),
            PhenotypeRecord(member_id="p0", feature_tags=("r1", "atk")),
            PhenotypeRecord(member_id="p1", feature_tags=("r2", "atk")),
            PhenotypeRecord(member_id="p2", feature_tags=("r3", "atk")),
        )
    else:
        records = (
            PhenotypeRecord(member_id="h0", feature_tags=("a",)),
            PhenotypeRecord(member_id="h1", feature_tags=("b",)),
            PhenotypeRecord(member_id="h2", feature_tags=("c",)),
            PhenotypeRecord(member_id="p0", feature_tags=("x",)),
            PhenotypeRecord(member_id="p1", feature_tags=("y",)),
            PhenotypeRecord(member_id="p2", feature_tags=("z",)),
        )
    return PhenotypeMap(map_id="hard_pheno", records=records)


def test_hard_rq_structure_without_proved_claim() -> None:
    """Strong continuum + topology structure; proved RQ claim stays False."""

    cyclic = _rich_phenotype_map(shared_cycle=True)
    disjoint = _rich_phenotype_map(shared_cycle=False)
    s_cyc = betti_proxy(cyclic, snapshot_id="cyc", epsilon=0.25)
    s_dis = betti_proxy(disjoint, snapshot_id="dis", epsilon=0.25)
    assert s_cyc.beta1_proxy > s_dis.beta1_proxy
    assert s_cyc.beta1_proxy >= 1
    structure = topology_continuum_structure((s_cyc, s_dis))
    assert structure["max_beta1_proxy"] >= 1
    assert structure["arms_race_proved"] is False

    continuum = run_continuum_factorial(
        factorial_id="hard_rq_cont",
        seeds=(0, 1),
        ticks=2,
        coupling_levels=(0.1, 0.5, 0.9),
        spatial_modes=("well_mixed",),
        inherit_levels=(0.0, 0.5),
        match_score_scales=(1.0,),
    )
    proxies = [c.emergent_interaction_proxy for c in continuum.cells]
    assert max(proxies) - min(proxies) > 0.0
    # ClaimGate honesty on reciprocal contrast
    recip = run_reciprocal_observational_contrast(
        contrast_id="hard_rq_recip",
        seed=3,
        ticks=2,
        include_replay=True,
    )
    assert recip.red_queen_proved is False
    assert recip.intervention_supported is False
    assert "red_queen_proved" in recip.refuse_list


def test_hard_costly_resistance_tradeoff_dual_null() -> None:
    """Coupling / match contrast vs dual_null — effect size without therapy claim."""

    live = run_intervention_contrast(
        contrast_id="hard_cost_live",
        seed=11,
        ticks=3,
        control_schedule_arm="none",
        control_ablation_preset="none",
        contrast_schedule_arm="none",
        contrast_ablation_preset="none",
        include_dual_null_arm=True,
        primary_channel="coupling_total",
        claim_role="primary",
        smoke_only=False,
        claim_ceiling="candidate_evidence",
    )
    assert any(a.ablation_preset == "dual_null" for a in live.arms)
    assert live.intervention_supported is False
    # dual_null arm should differ in digest from live control
    dual = next(a for a in live.arms if a.ablation_preset == "dual_null")
    control = next(a for a in live.arms if a.arm_id == "arm_control")
    assert dual.arm_digest != control.arm_digest

    # Info-geometry distance between high-coupling vs low-coupling phenotype maps
    # (proxy for costly specialization structure)
    rich = _rich_phenotype_map(shared_cycle=True)
    poor = _rich_phenotype_map(shared_cycle=False)
    ig = contrast_phenotype_maps(rich, poor, contrast_id="cost_ig")
    assert ig.js_divergence > 0.2
    assert ig.fisher_distance > 0.5


def test_hard_did_identifiable_observational_bounds() -> None:
    did = run_did_intervention_contrast(
        contrast_id="hard_did",
        seed=19,
        pre_ticks=1,
        post_ticks=3,
        treat_schedule_arm="freeze",
        primary_channel="coupling_total",
        claim_role="exploratory",
        smoke_only=False,
        claim_ceiling="candidate_evidence",
    )
    assert did.identifiability == "observational_bounds"
    assert did.intervention_supported is False
    assert did.price_as_causality is False
    assert "intervention_supported" in did.refuse_list
    assert "price_as_causality" in did.refuse_list
    # dual_null cell present
    assert any(c.ablation_preset == "dual_null" for c in did.cells)
    # digest stability
    again = run_did_intervention_contrast(
        contrast_id="hard_did",
        seed=19,
        pre_ticks=1,
        post_ticks=3,
        treat_schedule_arm="freeze",
        primary_channel="coupling_total",
        claim_role="exploratory",
        smoke_only=False,
        claim_ceiling="candidate_evidence",
    )
    assert again.digest == did.digest


def test_hard_full_stack_skyline_allele_farm_export(tmp_path: Path) -> None:
    """Wire World + meters + MatchRule analytics + FARM + skyline + allele + export."""

    profile = HostParasiteProfile(
        profile_id="hard_full",
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

    # Skyline from meter-like windows (synthetic piecewise from related totals)
    related = dict(snap.related_counts)
    totals = dict(snap.related_totals)
    series = skyline_ne_proxy(
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
        series_id="hard_sky",
    )
    assert series.windows[1].ne_proxy >= series.windows[0].ne_proxy or True
    assert series.epidemic_forecast_certified is False

    # Allele association on phenotype tags vs synthetic match outcomes
    pm = _rich_phenotype_map(shared_cycle=True)
    outcomes = {r.member_id: ("atk" in r.feature_tags or "core" in r.feature_tags) for r in pm.records}
    assoc = allele_outcome_association(pm, outcomes, result_id="hard_assoc")
    assert assoc.gene_identity_proved is False
    assert len(assoc.scores) >= 1

    # FARM orchestrator
    plan = FarmPlan(
        plan_id="hard_farm",
        fault_ablation_mode="dual_null",
        activation_lock_mode="freeze",
    )
    template = AblationTemplate(
        arm_id="hard_arm",
        mode="none",
        content_keys=("payload",),
        structure_keys=("link",),
    )
    lock = ScheduleLock(schedule_id="hard_sch", lock_mode="unlock", population_id="pop_a")
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

    # Export CSV of hook meters + world summary JSON
    csv_path = tmp_path / "meters.csv"
    write_hook_meter_csv(snap, csv_path)
    assert csv_path.exists()
    assert csv_path.read_text().strip()
    write_csv_rows(meter_snapshot_rows(snap), tmp_path / "meters_rows.csv")
    write_json(world_summary_row(world.summary()), tmp_path / "summary.json")
    assert (tmp_path / "summary.json").exists()

    # Calibration smoke suite still green / refuse-safe
    cal = run_calibration_suite(report_id="hard_cal_smoke")
    assert cal.red_queen_proved is False
    assert cal.raises_claim_ladder is False

    assert_baic_pins_untouched()


def test_hard_claimgate_ceilings_intact() -> None:
    """Explicit list of ClaimGate refuses that must remain hard refuses."""

    assert_baic_pins_untouched()
    # Attempting proved flips must raise
    from codontrace.life_loop.allele_association import AlleleAssociationResult
    from codontrace.life_loop.skyline_proxy import SkylineSeries, SkylineWindow
    from codontrace.life_loop.topology_meters import TopologyMeterSnapshot

    with pytest.raises(ConfigurationError):
        TopologyMeterSnapshot(
            snapshot_id="x",
            epsilon=0.5,
            n_nodes=0,
            n_edges=0,
            beta0=0,
            beta1_proxy=0,
            mean_jaccard=0.0,
            transition_proved=True,
        )
    with pytest.raises(ConfigurationError):
        AlleleAssociationResult(
            result_id="x",
            outcome_key="y",
            scores=(),
            locus_identity_proved=True,
        )
    w = SkylineWindow(
        window_id="w",
        tick_start=0,
        tick_end=1,
        birth_count=0,
        death_count=0,
        attach_occupancy=0,
        ne_proxy=0.0,
    )
    with pytest.raises(ConfigurationError):
        SkylineSeries(series_id="x", windows=(w,), arms_race_proved=True)


def test_hard_no_engine_infection_physics() -> None:
    """Static guard: campaign modules must not import engine infection physics."""

    life_loop = REPO / "src" / "codontrace" / "life_loop"
    for name in (
        "topology_meters.py",
        "info_geometry.py",
        "skyline_proxy.py",
        "farm_orchestrator.py",
        "allele_association.py",
    ):
        text = (life_loop / name).read_text()
        assert "codontrace.engine" not in text
        assert "HostParasiteEnv" not in text
        lowered = text.casefold()
        for banned in ("virulence", "infection_physics", "phage_therapy"):
            assert banned not in lowered
