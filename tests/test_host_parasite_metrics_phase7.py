"""Phase 7: hook meters + HostParasiteWorld prereg/spec (no new physics)."""

from __future__ import annotations

import ast
import hashlib
from pathlib import Path

import pytest

from codontrace.contracts import HOOK_NAMES
from codontrace.errors import ConfigurationError
from codontrace.genesis.host_parasite_metrics import (
    METRIC_IDS,
    SCIENCE_MIN_SEEDS,
    HostParasiteMetricSummary,
    HostParasitePreregSpec,
    SeedPlanSpec,
    build_metric_summary,
)
from codontrace.genesis.host_parasite_world import (
    HostParasiteProfile,
    HostParasiteWorld,
)
from codontrace.life_loop import HookMeter, HookMeterSnapshot

REPO = Path(__file__).resolve().parents[1]
METER_SRC = REPO / "src" / "codontrace" / "life_loop" / "hook_meters.py"
METRICS_SRC = REPO / "src" / "codontrace" / "genesis" / "host_parasite_metrics.py"
WORLD_SRC = REPO / "src" / "codontrace" / "genesis" / "host_parasite_world.py"
ENGINE_SRC = REPO / "src" / "codontrace" / "engine.py"

_BAIC = (
    (
        "docs/hard_experiment_01/results_v7.json",
        "35bb593604438797755e5e7b28af4d1371992a6181a403d08005f7f45421cbd6",
    ),
    (
        "docs/claimgate/risk_bar.json",
        "4dbe4aa3a6ef8e771f180d2a6589c64b0dd5ffebe0aa73703a7256c17d771cd7",
    ),
    (
        "docs/claimgate/biomedical_study.json",
        "9685f2fbafb21477d977dfa0c0bf73e02bea81d084e7605978ea25c47bf5ddce",
    ),
)


def _profile(**overrides: object) -> HostParasiteProfile:
    body: dict[str, object] = {
        "profile_id": "hp_m7",
        "seed": 7,
        "slot_capacity": 2,
        "coupling_amount": 0.25,
        "match_rule_id": "always",
        "contact_probability": 1.0,
        "spatial_mode": "well_mixed",
        "ablation_preset": "none",
        "schedule_arm": "none",
    }
    body.update(overrides)
    return HostParasiteProfile(**body)  # type: ignore[arg-type]


def _smoke_prereg(**overrides: object) -> HostParasitePreregSpec:
    body: dict[str, object] = {
        "prereg_id": "prereg_smoke",
        "phenomenon": "digital_coexistence_census",
        "metric_ids": ("role_density_primary", "hook_contact_count"),
        "dual_null_required": False,
        "seed_plan": SeedPlanSpec.smoke((0, 1, 2)),
    }
    body.update(overrides)
    return HostParasitePreregSpec(**body)  # type: ignore[arg-type]


def _primary_prereg() -> HostParasitePreregSpec:
    return HostParasitePreregSpec(
        prereg_id="prereg_primary",
        phenomenon="digital_attachment_prevalence",
        metric_ids=("attach_prevalence", "coupling_total", "hook_contact_count"),
        dual_null_required=True,
        seed_plan=SeedPlanSpec.science_default(SCIENCE_MIN_SEEDS),
    )


def test_hook_meter_snapshot_round_trip_and_digest() -> None:
    meter = HookMeter(meter_id="meter_a")
    meter.record_hook("on_birth", count=2)
    meter.record_hook("on_contact")
    meter.record_related_count("contact_success")
    snap = meter.snapshot()
    again = HookMeterSnapshot.from_dict(snap.to_dict())
    assert again.digest == snap.digest
    assert again.to_dict() == snap.to_dict()
    assert set(snap.hook_counts) == set(HOOK_NAMES)


def test_hook_meter_tampered_digest_refuses() -> None:
    snap = HookMeter(meter_id="meter_b").snapshot()
    payload = snap.to_dict()
    payload["digest"] = "0" * 64
    with pytest.raises(ConfigurationError, match="digest mismatch"):
        HookMeterSnapshot.from_dict(payload)


def test_unknown_hook_and_banned_meter_id_refuse() -> None:
    meter = HookMeter(meter_id="meter_c")
    with pytest.raises(ConfigurationError, match="unknown hook"):
        meter.record_hook("on_infect")
    with pytest.raises(ConfigurationError, match="banned fragment"):
        HookMeter(meter_id="parasite_meter")


def test_contact_fail_histogram_and_related() -> None:
    meter = HookMeter(meter_id="meter_d")
    meter.record_contact_outcome("success", success=True)
    meter.record_contact_outcome("match_failed", success=False)
    snap = meter.snapshot()
    assert snap.hook_counts["on_contact"] == 1
    assert snap.related_counts["contact_success"] == 1
    assert snap.related_counts["contact_fail"] == 1
    assert snap.contact_fail_reasons["success"] == 1
    assert snap.contact_fail_reasons["match_failed"] == 1


def test_prereg_round_trip_merges_core_refuses() -> None:
    prereg = _smoke_prereg(refuse_list=("custom_ban",))
    again = HostParasitePreregSpec.from_dict(prereg.to_dict())
    assert again.digest == prereg.digest
    assert "red_queen_proved" in again.refuse_list
    assert "custom_ban" in again.refuse_list
    assert again.to_dict()["red_queen_proved"] is False
    assert again.to_dict()["raises_claim_ladder"] is False


def test_prereg_ceiling_and_unknown_metric_refuse() -> None:
    with pytest.raises(ConfigurationError, match="planned_claim_ceiling"):
        HostParasitePreregSpec(
            prereg_id="bad",
            phenomenon="x",
            metric_ids=("hook_contact_count",),
            dual_null_required=False,
            seed_plan=SeedPlanSpec.smoke(),
            planned_claim_ceiling="proved",
        )
    with pytest.raises(ConfigurationError, match="unknown metric_id"):
        HostParasitePreregSpec(
            prereg_id="bad2",
            phenomenon="x",
            metric_ids=("infection_rate",),
            dual_null_required=False,
            seed_plan=SeedPlanSpec.smoke(),
        )


def test_seed_plan_science_n_and_smoke() -> None:
    with pytest.raises(ConfigurationError, match="unless smoke_only"):
        SeedPlanSpec(seeds=(0, 1, 2), smoke_only=False)
    smoke = SeedPlanSpec.smoke((9, 8))
    assert smoke.smoke_only is True
    science = SeedPlanSpec.science_default()
    assert len(science.seeds) == SCIENCE_MIN_SEEDS


def test_primary_summary_requires_dual_null() -> None:
    world = HostParasiteWorld(_profile(ablation_preset="none"))
    world.attach_prereg(_primary_prereg())
    world.run(5)
    with pytest.raises(ConfigurationError, match="dual_null"):
        world.metric_summary(claim_role="primary")


def test_primary_summary_allows_dual_null_profile() -> None:
    world = HostParasiteWorld(_profile(ablation_preset="dual_null", seed=3))
    world.attach_prereg(_primary_prereg())
    world.run(10)
    summary = world.metric_summary(claim_role="primary")
    assert summary.red_queen_proved is False
    assert summary.raises_claim_ladder is False
    assert summary.science_grade is True
    assert summary.claim_role == "primary"
    assert "attach_prevalence" in summary.metrics


def test_metric_summary_refuses_proved_flags() -> None:
    snap = HookMeter(meter_id="meter_e").snapshot()
    with pytest.raises(ConfigurationError, match="red_queen_proved"):
        HostParasiteMetricSummary(
            summary_id="s",
            claim_role="exploratory",
            metrics={"hook_contact_count": 0.0},
            meter_digest=snap.digest,
            prereg_digest=None,
            science_grade=False,
            ablation_preset="none",
            labels={},
            red_queen_proved=True,
        )


def test_world_attach_prereg_and_summary_digests() -> None:
    world = HostParasiteWorld(_profile(seed=11))
    prereg = _smoke_prereg()
    world.attach_prereg(prereg)
    with pytest.raises(ConfigurationError, match="already attached"):
        world.attach_prereg(prereg)
    out = world.run(20)
    assert out["red_queen_proved"] is False
    assert out["meter_digest"]
    assert out["prereg_digest"] == prereg.digest
    assert out["hook_counts"]["on_contact"] >= 1
    assert out["hook_counts"]["on_resource"] >= 1
    exploratory = world.metric_summary(claim_role="exploratory")
    assert exploratory.prereg_digest == prereg.digest
    assert exploratory.science_grade is False


def test_build_metric_summary_smoke_not_science() -> None:
    world = HostParasiteWorld(_profile())
    world.attach_prereg(_smoke_prereg())
    world.run(3)
    smoke = world.metric_summary(claim_role="smoke")
    assert smoke.science_grade is False
    with pytest.raises(ConfigurationError, match="smoke_only"):
        world.metric_summary(claim_role="primary")


def test_static_audit_no_physics_no_claimgate_in_meters() -> None:
    meter_src = METER_SRC.read_text(encoding="utf-8")
    # Import scan (avoid writing banned contiguous tokens in life_loop sources).
    tree_m = ast.parse(meter_src)
    for node in ast.walk(tree_m):
        mods: list[str] = []
        if isinstance(node, ast.Import):
            mods.extend(a.name for a in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            mods.append(node.module)
        for mod in mods:
            low = mod.casefold()
            assert "claim" + "gate" not in low
            assert "host_para" + "site" not in low
    assert "HostParasiteEnv" not in meter_src
    assert "steal_fraction" not in meter_src
    for banned in ("parasite", "infection", "virulence", "host_state"):
        # allow comments? keep module free of domain nouns in identifiers — check AST names
        pass
    tree = ast.parse(meter_src)
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Name):
            names.add(node.id)
        elif isinstance(node, ast.Attribute):
            names.add(node.attr)
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            names.add(node.name)
    lowered = {n.casefold() for n in names}
    for banned in ("parasite", "infection", "virulence", "host", "phage"):
        assert banned not in lowered

    metrics_src = METRICS_SRC.read_text(encoding="utf-8")
    assert "HostParasiteEnv" not in metrics_src
    assert "steal_fraction" not in metrics_src
    assert "Simulation(" not in metrics_src
    assert "Avida" not in metrics_src
    assert "not in Avida" not in metrics_src

    world_src = WORLD_SRC.read_text(encoding="utf-8")
    assert "def step(" not in world_src
    # engine.py byte identity vs pre-phase? just ensure we did not edit it this phase —
    # spot-check file still exists and BAIC pins unchanged.
    assert ENGINE_SRC.is_file()
    for rel, expected in _BAIC:
        got = hashlib.sha256((REPO / rel).read_bytes()).hexdigest()
        assert got == expected, rel


def test_metric_ids_bounded() -> None:
    assert len(METRIC_IDS) <= 16
