"""Wave B — unit coverage for adopted INN-01..06 modules."""

from __future__ import annotations

import pytest

from codontrace.errors import ConfigurationError
from codontrace.genesis.host_parasite_analytics import (
    DidInterventionContrast,
    run_did_intervention_contrast,
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
    fisher_simplex_distance,
    js_divergence,
    phenotype_tag_frequencies,
    skyline_ne_proxy,
    topology_continuum_structure,
)


def _triangle_map() -> PhenotypeMap:
    return PhenotypeMap(
        map_id="tri",
        records=(
            PhenotypeRecord(member_id="a", feature_tags=("x", "y")),
            PhenotypeRecord(member_id="b", feature_tags=("y", "z")),
            PhenotypeRecord(member_id="c", feature_tags=("x", "z")),
        ),
    )


def test_inn01_betti_proxy_cycle() -> None:
    snap = betti_proxy(_triangle_map(), snapshot_id="t1", epsilon=0.3)
    assert snap.n_nodes == 3
    assert snap.n_edges == 3
    assert snap.beta0 == 1
    assert snap.beta1_proxy == 1  # triangle cycle
    assert snap.arms_race_proved is False
    same = betti_proxy(_triangle_map(), snapshot_id="t1", epsilon=0.3)
    assert same.digest == snap.digest


def test_inn01_refuse_arms_race_proved() -> None:
    from codontrace.life_loop.topology_meters import TopologyMeterSnapshot

    with pytest.raises(ConfigurationError, match="arms_race_proved"):
        TopologyMeterSnapshot(
            snapshot_id="bad",
            epsilon=0.5,
            n_nodes=1,
            n_edges=0,
            beta0=1,
            beta1_proxy=0,
            mean_jaccard=0.0,
            arms_race_proved=True,
        )


def test_inn01_continuum_structure_summary() -> None:
    s_lo = betti_proxy(_triangle_map(), snapshot_id="lo", epsilon=0.9)
    s_hi = betti_proxy(_triangle_map(), snapshot_id="hi", epsilon=0.1)
    summary = topology_continuum_structure((s_lo, s_hi))
    assert summary["max_beta1_proxy"] >= 0
    assert summary["arms_race_proved"] is False


def test_inn02_info_geometry_distances() -> None:
    fa = phenotype_tag_frequencies(_triangle_map())
    pm2 = PhenotypeMap(
        map_id="alt",
        records=(
            PhenotypeRecord(member_id="a", feature_tags=("p",)),
            PhenotypeRecord(member_id="b", feature_tags=("q",)),
            PhenotypeRecord(member_id="c", feature_tags=("r",)),
        ),
    )
    fb = phenotype_tag_frequencies(pm2)
    js = js_divergence(fa, fb)
    fisher = fisher_simplex_distance(fa, fb)
    assert js > 0.0
    assert fisher > 0.0
    contrast = contrast_phenotype_maps(_triangle_map(), pm2, contrast_id="ig1")
    assert contrast.js_divergence == pytest.approx(js)
    assert contrast.digest.startswith("info_geom:")


def test_inn02_identical_maps_zero_distance() -> None:
    contrast = contrast_phenotype_maps(
        _triangle_map(), _triangle_map(), contrast_id="same"
    )
    assert contrast.js_divergence == pytest.approx(0.0)
    assert contrast.fisher_distance == pytest.approx(0.0)


def test_inn03_did_contrast_digest_stable() -> None:
    a = run_did_intervention_contrast(
        contrast_id="did_smoke",
        seed=7,
        pre_ticks=1,
        post_ticks=2,
        treat_schedule_arm="freeze",
    )
    b = run_did_intervention_contrast(
        contrast_id="did_smoke",
        seed=7,
        pre_ticks=1,
        post_ticks=2,
        treat_schedule_arm="freeze",
    )
    assert isinstance(a, DidInterventionContrast)
    assert a.digest == b.digest
    assert len(a.cells) == 5
    assert a.identifiability == "observational_bounds"
    assert a.intervention_supported is False
    assert a.red_queen_proved is False
    assert a.price_as_causality is False
    assert "intervention_supported" in a.refuse_list


def test_inn03_did_refuses_causal_proved() -> None:
    with pytest.raises(ConfigurationError, match="intervention_supported"):
        DidInterventionContrast(
            contrast_id="bad",
            cells=run_did_intervention_contrast(contrast_id="tmp").cells,
            did_estimate=0.0,
            effect_lower=-1.0,
            effect_upper=1.0,
            dual_null_delta=0.0,
            intervention_supported=True,
        )


def test_inn04_skyline_ne_proxy() -> None:
    series = skyline_ne_proxy(
        [
            {
                "window_id": "w0",
                "tick_start": 0,
                "tick_end": 5,
                "birth_count": 4,
                "death_count": 1,
                "attach_occupancy": 2,
            },
            {
                "window_id": "w1",
                "tick_start": 5,
                "tick_end": 10,
                "birth_count": 10,
                "death_count": 2,
                "attach_occupancy": 1,
            },
        ],
        series_id="sky_test",
    )
    assert series.windows[0].ne_proxy == pytest.approx(5.0)
    assert series.windows[1].ne_proxy == pytest.approx(9.0)
    assert series.epidemic_forecast_certified is False


def test_inn04_refuse_epidemic_forecast() -> None:
    from codontrace.life_loop.skyline_proxy import SkylineSeries, SkylineWindow

    w = SkylineWindow(
        window_id="w",
        tick_start=0,
        tick_end=1,
        birth_count=1,
        death_count=0,
        attach_occupancy=0,
        ne_proxy=1.0,
    )
    with pytest.raises(ConfigurationError, match="epidemic_forecast"):
        SkylineSeries(
            series_id="bad",
            windows=(w,),
            epidemic_forecast_certified=True,
        )


def test_inn05_farm_apply() -> None:
    plan = FarmPlan(
        plan_id="farm1",
        fault_ablation_mode="content_null",
        activation_lock_mode="freeze",
        activation_tick=0,
    )
    template = AblationTemplate(
        arm_id="arm_c",
        mode="none",
        content_keys=("payload",),
        structure_keys=("link",),
    )
    lock = ScheduleLock(schedule_id="sch1", lock_mode="unlock", population_id="pop_a")
    registry = PopulationRegistry().create_population("pop_a", member_ids=("m1", "m2"))
    bag = {"payload": "alpha", "link": "grid"}
    live = {"m1": {"payload": "alpha"}, "m2": {"payload": "beta"}}
    record, abl, sched, state, bag_out = apply_farm(
        plan,
        ablation_template=template,
        bag=bag,
        schedule_lock=lock,
        registry=registry,
        live_bags=live,
    )
    assert bag_out["payload"] is None
    assert bag_out["link"] == "grid"
    assert record.intervention_supported is False
    assert state.lock_mode == "freeze"
    assert abl.digest
    assert sched.digest


def test_inn05_farm_refuses_intervention_supported() -> None:
    with pytest.raises(ConfigurationError, match="intervention_supported"):
        FarmPlan(
            plan_id="bad",
            fault_ablation_mode="none",
            activation_lock_mode="unlock",
            intervention_supported=True,
        )


def test_inn06_allele_association() -> None:
    pm = _triangle_map()
    result = allele_outcome_association(
        pm,
        {"a": True, "b": False, "c": True},
        result_id="assoc1",
        outcome_key="match_pass",
    )
    assert result.gene_identity_proved is False
    assert result.locus_identity_proved is False
    tags = {s.tag: s.risk_diff for s in result.scores}
    assert "x" in tags
    assert tags["x"] > 0.0  # a and c carry x and outcome True


def test_inn06_refuse_gene_identity() -> None:
    from codontrace.life_loop.allele_association import AlleleAssociationResult

    with pytest.raises(ConfigurationError, match="gene_identity"):
        AlleleAssociationResult(
            result_id="bad",
            outcome_key="match_pass",
            scores=(),
            gene_identity_proved=True,
        )
