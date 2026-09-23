"""Phase 5: spatial inject, vertical/mixed transmission, ARD/FSD diagnostics."""

from __future__ import annotations

import pytest

from codontrace.claimgate import audit_bundle
from codontrace.claimgate.adapters.host_parasite import (
    attach_coevolution_diagnostics,
    bundle_from_host_parasite_cou,
)
from codontrace.errors import ConfigurationError
from codontrace.genesis.host_parasite_diagnostics import diagnose_coevolution_ranges
from codontrace.genesis.host_parasite_env import HostParasiteEnv


def test_local_neighborhood_blocks_distant_inject() -> None:
    env = HostParasiteEnv(
        spatial_mode="local_neighborhood",
        grid_rows=3,
        grid_cols=3,
        steal_fraction=0.8,
    )
    env.add_host("A", ("and",), row=0, col=0)
    env.add_host("B", ("and",), row=0, col=1)
    env.add_host("C", ("and",), row=2, col=2)
    near = env.try_local_inject(
        source_host_id="A",
        target_host_id="B",
        parasite_id="P1",
        parasite_tasks=("and",),
        payload=(1,),
    )
    far = env.try_local_inject(
        source_host_id="A",
        target_host_id="C",
        parasite_id="P2",
        parasite_tasks=("and",),
        payload=(1,),
    )
    assert near.injected is True
    assert far.injected is False
    assert far.reason == "outside_local_neighborhood"
    assert env.neighbors("A") == ("B",)


def test_well_mixed_local_inject_allows_any_target() -> None:
    env = HostParasiteEnv(spatial_mode="well_mixed", steal_fraction=0.8)
    env.add_host("A", ("and",), row=0, col=0)
    env.add_host("Z", ("and",), row=9, col=9)
    attempt = env.try_local_inject(
        source_host_id="A",
        target_host_id="Z",
        parasite_id="P",
        parasite_tasks=("and",),
        payload=(3,),
    )
    assert attempt.injected is True


def test_vertical_transmission_on_replicate() -> None:
    env = HostParasiteEnv(
        transmission_mode="vertical",
        vertical_transmission_probability=1.0,
        steal_fraction=0.5,
    )
    env.add_host("H0", ("and", "or"))
    env.seed_parasite_seat(
        host_id="H0",
        parasite_id="P0",
        parasite_tasks=("and",),
        payload=(7, 8),
    )
    child = env.replicate_host(parent_id="H0", child_id="H1", draw=0.0)
    assert child.parasite_id is not None
    assert child.parasite_payload == (7, 8)
    miss = env.replicate_host(parent_id="H0", child_id="H2", draw=0.99)
    # probability 1.0 → still transmits even on high draw? draw < 1.0 is True for 0.99
    assert miss.parasite_id is not None
    env_low = HostParasiteEnv(
        transmission_mode="vertical",
        vertical_transmission_probability=0.0,
        steal_fraction=0.5,
    )
    env_low.add_host("P", ("and",))
    env_low.seed_parasite_seat(
        host_id="P", parasite_id="X", parasite_tasks=("and",), payload=(1,)
    )
    no = env_low.replicate_host(parent_id="P", child_id="C", draw=0.0)
    assert no.parasite_id is None
    assert env.snapshot()["vertical_component"] == "vertical_mode_enabled"


def test_mixed_mode_blends_horizontal_and_vertical_not_stub() -> None:
    env = HostParasiteEnv(
        transmission_mode="mixed",
        vertical_transmission_probability=1.0,
        steal_fraction=0.8,
    )
    env.add_host("H0", ("nand", "and"))
    horiz = env.try_horizontal_inject(
        host_id="H0",
        parasite_id="P0",
        parasite_tasks=("and",),
        payload=(1, 2, 3),
    )
    assert horiz.injected is True
    child = env.replicate_host(parent_id="H0", child_id="H1", draw=0.0)
    assert child.parasite_id is not None
    snap = env.snapshot()
    assert snap["vertical_component"] == "mixed_mode_enabled"
    assert "not_implemented" not in str(snap["vertical_component"])
    assert snap["red_queen_proved"] is False


def test_resource_productivity_modulates_steal() -> None:
    low = HostParasiteEnv(steal_fraction=0.8, resource_productivity=1.0)
    high = HostParasiteEnv(steal_fraction=0.8, resource_productivity=2.0)
    for env in (low, high):
        env.add_host("H0", ("and",))
        env.try_horizontal_inject(
            host_id="H0",
            parasite_id="P0",
            parasite_tasks=("and",),
            payload=(1,),
        )
    assert low.host_retained_cpu("H0") == pytest.approx(0.2)
    assert high.host_retained_cpu("H0") == pytest.approx(0.6)
    assert high.host_retained_cpu("H0") > low.host_retained_cpu("H0")


def test_ard_like_diagnostics_never_prove_red_queen() -> None:
    result = diagnose_coevolution_ranges(
        [
            {"time_index": 0, "infectivity_range": 0.1, "resistance_range": 0.1},
            {"time_index": 1, "infectivity_range": 0.3, "resistance_range": 0.25},
            {"time_index": 2, "infectivity_range": 0.6, "resistance_range": 0.5},
        ]
    )
    assert result.label == "ard_like"
    assert result.red_queen_proved is False
    assert result.to_dict()["raises_claim_ladder"] is False
    assert "digest" in result.to_dict()


def test_fsd_like_and_mixed_diagnostics() -> None:
    fsd = diagnose_coevolution_ranges(
        [
            {"time_index": 0, "infectivity_range": 0.5, "resistance_range": 0.4},
            {"time_index": 1, "infectivity_range": 0.1, "resistance_range": 0.7},
            {"time_index": 2, "infectivity_range": 0.55, "resistance_range": 0.35},
        ],
        escalation_threshold=0.5,
        fluctuation_threshold=0.05,
    )
    assert fsd.label == "fsd_like"
    assert fsd.red_queen_proved is False
    mixed = diagnose_coevolution_ranges(
        [
            {"time_index": 0, "infectivity_range": 0.1, "resistance_range": 0.1},
            {"time_index": 1, "infectivity_range": 0.8, "resistance_range": 0.2},
            {"time_index": 2, "infectivity_range": 0.9, "resistance_range": 0.85},
        ],
        escalation_threshold=0.05,
        fluctuation_threshold=0.05,
    )
    assert mixed.label == "mixed_like"
    assert mixed.red_queen_proved is False


def test_attach_diagnostics_refuses_overwrite_and_wrong_domain() -> None:
    from codontrace.claimgate.adapters.biomedical import bundle_from_biomedical_cou

    diagnostics = diagnose_coevolution_ranges(
        [
            {"time_index": 0, "infectivity_range": 0.1, "resistance_range": 0.1},
            {"time_index": 1, "infectivity_range": 0.4, "resistance_range": 0.4},
        ]
    )
    bio = bundle_from_biomedical_cou(
        question_of_interest="q",
        context_of_use="c",
        model_influence=1,
        decision_consequence=1,
        treatment_scores=(0.1,),
        control_scores=(0.0,),
    )
    with pytest.raises(ConfigurationError, match="host_parasite"):
        attach_coevolution_diagnostics(bio, diagnostics)
    bundle = bundle_from_host_parasite_cou(
        question_of_interest="Do escalating digital ranges justify an ARD-like label?",
        context_of_use="Digital diagnostics only. No Red Queen proof.",
        model_influence=2,
        decision_consequence=2,
        treatment_scores=(0.4, 0.5),
        control_scores=(0.1, 0.2),
    )
    before = audit_bundle(bundle).achieved_level
    once = attach_coevolution_diagnostics(bundle, diagnostics)
    assert once.extra["coevolution_diagnostics"]["red_queen_proved"] is False
    assert audit_bundle(once).achieved_level == before
    with pytest.raises(ConfigurationError, match="already attached"):
        attach_coevolution_diagnostics(once, diagnostics)


def test_local_neighborhood_requires_coordinates() -> None:
    env = HostParasiteEnv(spatial_mode="local_neighborhood", grid_rows=2, grid_cols=2)
    with pytest.raises(ConfigurationError, match="row and col"):
        env.add_host("H0", ("and",))


def test_seed_seat_blocked_by_structure_null() -> None:
    from codontrace.genesis.host_parasite_env import dual_null_template

    env = HostParasiteEnv(
        transmission_mode="vertical",
        null_template=dual_null_template("structure_null"),
    )
    env.add_host("H0", ("and",))
    with pytest.raises(ConfigurationError, match="structure_null"):
        env.seed_parasite_seat(
            host_id="H0",
            parasite_id="P0",
            parasite_tasks=("and",),
            payload=(1,),
        )
