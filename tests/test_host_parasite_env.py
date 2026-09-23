"""Optional HostParasiteEnv outside engine: overlap, seat, inject, dual-null."""

from __future__ import annotations

import pytest

from codontrace.errors import ConfigurationError
from codontrace.genesis.host_parasite_env import (
    DEFAULT_STEAL_FRACTION,
    HostParasiteEnv,
    dual_null_template,
    run_dual_null_contrast,
)


def test_default_steal_fraction_matches_fortuna_analogy() -> None:
    env = HostParasiteEnv()
    assert env.steal_fraction == DEFAULT_STEAL_FRACTION == 0.8
    assert env.claim_ceiling == "runtime_observation"


def test_task_overlap_eligibility_and_one_seat() -> None:
    env = HostParasiteEnv()
    env.add_host("H0", ("nand", "and", "or"))
    first = env.try_horizontal_inject(
        host_id="H0",
        parasite_id="P0",
        parasite_tasks=("and", "xor"),
        payload=(1, 2, 3),
    )
    assert first.eligible is True
    assert first.injected is True
    assert first.overlap_tasks == ("and",)
    second = env.try_horizontal_inject(
        host_id="H0",
        parasite_id="P1",
        parasite_tasks=("and",),
        payload=(9,),
    )
    assert second.injected is False
    assert second.reason == "seat_occupied"
    assert env.host_retained_cpu("H0") == pytest.approx(0.2)


def test_no_overlap_refuses_inject() -> None:
    env = HostParasiteEnv()
    env.add_host("H0", ("nand",))
    attempt = env.try_horizontal_inject(
        host_id="H0",
        parasite_id="P0",
        parasite_tasks=("xor",),
        payload=(1,),
    )
    assert attempt.eligible is False
    assert attempt.injected is False
    assert attempt.reason == "no_task_overlap"
    assert env.host_retained_cpu("H0") == 1.0


def test_vertical_mode_blocks_horizontal_inject() -> None:
    env = HostParasiteEnv(transmission_mode="vertical")
    env.add_host("H0", ("and",))
    attempt = env.try_horizontal_inject(
        host_id="H0",
        parasite_id="P0",
        parasite_tasks=("and",),
        payload=(1,),
    )
    assert attempt.injected is False
    assert "vertical" in attempt.reason


def test_dual_null_templates_change_outcomes() -> None:
    contrast = run_dual_null_contrast(
        host_tasks=("nand", "and"),
        parasite_tasks=("and", "or"),
        payload=(7, 8, 9),
        steal_fraction=0.8,
    )
    scores = contrast["scores"]
    assert contrast["nulls_change_outcomes"] is True
    # Intact infection steals 80% → retained 0.2
    assert scores["none"] == pytest.approx(0.2)
    # Content-null: seat may fill, but payload-dependent steal is zero → 1.0
    assert scores["content_null"] == pytest.approx(1.0)
    # Structure-null: no eligibility → no infection → 1.0
    assert scores["structure_null"] == pytest.approx(1.0)
    assert scores["dual_null"] == pytest.approx(1.0)
    assert scores["none"] != scores["content_null"]
    assert scores["none"] != scores["structure_null"]


def test_content_null_preserves_seat_structure_null_blocks() -> None:
    content = HostParasiteEnv(null_template=dual_null_template("content_null"))
    content.add_host("H0", ("and",))
    c_attempt = content.try_horizontal_inject(
        host_id="H0",
        parasite_id="P0",
        parasite_tasks=("and",),
        payload=(1, 2),
    )
    assert c_attempt.injected is True
    assert content.hosts["H0"].parasite_payload == ()
    assert content.host_retained_cpu("H0") == 1.0

    structure = HostParasiteEnv(null_template=dual_null_template("structure_null"))
    structure.add_host("H0", ("and",))
    s_attempt = structure.try_horizontal_inject(
        host_id="H0",
        parasite_id="P0",
        parasite_tasks=("and",),
        payload=(1, 2),
    )
    assert s_attempt.injected is False
    assert s_attempt.reason == "structure_null_blocks_overlap"
    assert structure.hosts["H0"].parasite_id is None


def test_env_rejects_invalid_steal_and_claim_ceiling() -> None:
    with pytest.raises(ConfigurationError):
        HostParasiteEnv(steal_fraction=1.5)
    with pytest.raises(ConfigurationError):
        HostParasiteEnv(claim_ceiling="red_queen_proved")
    with pytest.raises(ConfigurationError):
        dual_null_template("clinical_null")


def test_snapshot_marks_outside_engine_and_no_red_queen() -> None:
    env = HostParasiteEnv()
    env.add_host("H0", ("and",))
    snap = env.snapshot()
    assert snap["engine_infection_physics"] == "not_in_engine_core"
    assert snap["raises_claim_ladder"] is False
    assert snap["red_queen_proved"] is False
    assert "digest" in snap


def test_duplicate_host_and_unknown_host_fail_closed() -> None:
    env = HostParasiteEnv()
    env.add_host("H0", ("and",))
    with pytest.raises(ConfigurationError, match="already exists"):
        env.add_host("H0", ("or",))
    with pytest.raises(ConfigurationError, match="unknown host"):
        env.try_horizontal_inject(
            host_id="Hx",
            parasite_id="P0",
            parasite_tasks=("and",),
        )


def test_empty_host_tasks_rejected() -> None:
    env = HostParasiteEnv()
    with pytest.raises(ConfigurationError, match="at least one task"):
        env.add_host("H0", ())


def test_dual_null_contrast_tracks_injection_when_scores_tie() -> None:
    contrast = run_dual_null_contrast(
        host_tasks=("and",),
        parasite_tasks=("and",),
        payload=(1,),
        steal_fraction=0.0,
    )
    assert contrast["nulls_change_scores"] is False
    assert contrast["nulls_change_injection"] is True
    assert contrast["nulls_change_outcomes"] is True
    assert contrast["injected"]["none"] is True
    assert contrast["injected"]["structure_null"] is False


def test_mixed_mode_blends_horizontal_and_vertical() -> None:
    env = HostParasiteEnv(
        transmission_mode="mixed",
        vertical_transmission_probability=1.0,
        steal_fraction=0.8,
    )
    env.add_host("H0", ("and", "or"))
    injected = env.try_horizontal_inject(
        host_id="H0",
        parasite_id="P0",
        parasite_tasks=("and",),
        payload=(1, 2),
    )
    assert injected.injected is True
    child = env.replicate_host(parent_id="H0", child_id="H1", draw=0.0)
    assert child.parasite_id is not None
    snap = env.snapshot()
    assert snap["vertical_component"] == "mixed_mode_enabled"
    assert snap["red_queen_proved"] is False


def test_parasite_id_must_differ_from_host_id() -> None:
    env = HostParasiteEnv()
    env.add_host("H0", ("and",))
    with pytest.raises(ConfigurationError, match="differ"):
        env.try_horizontal_inject(
            host_id="H0",
            parasite_id="H0",
            parasite_tasks=("and",),
            payload=(1,),
        )


def test_dual_null_contrast_requires_overlap() -> None:
    with pytest.raises(ConfigurationError, match="task overlap"):
        run_dual_null_contrast(
            host_tasks=("nand",),
            parasite_tasks=("xor",),
            payload=(1,),
        )
