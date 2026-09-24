"""Phase 6: HostParasiteWorld thin profile + locked-digest adapter."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from codontrace.errors import ConfigurationError
from codontrace.genesis.host_parasite_world import (
    HostParasiteProfile,
    HostParasiteWorld,
    adapt_locked_digests,
    assert_baic_pins_untouched,
)
from codontrace.life_loop import resolve_member_state

REPO = Path(__file__).resolve().parents[1]
WORLD_SRC = REPO / "src" / "codontrace" / "genesis" / "host_parasite_world.py"


def _default_profile(**overrides: object) -> HostParasiteProfile:
    body: dict[str, object] = {
        "profile_id": "hp_smoke",
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


def test_profile_round_trip_and_digest() -> None:
    profile = _default_profile()
    again = HostParasiteProfile.from_dict(profile.to_dict())
    assert again.digest == profile.digest
    assert again.to_dict() == profile.to_dict()


def test_profile_tampered_digest_refuses() -> None:
    profile = _default_profile()
    payload = profile.to_dict()
    payload["digest"] = "0" * 64
    with pytest.raises(ConfigurationError, match="digest mismatch"):
        HostParasiteProfile.from_dict(payload)


def test_role_map_refuses_banned_population_id() -> None:
    with pytest.raises(ConfigurationError, match="banned fragment"):
        _default_profile(
            role_population_ids={"primary": "pop_a", "secondary": "parasite_1"}
        )


def test_world_constructs_two_populations_and_capacity() -> None:
    profile = _default_profile(slot_capacity=3)
    world = HostParasiteWorld(profile)
    assert set(world.registry.list_population_ids()) == {"pop_a", "pop_b"}
    assert world.census() == {"primary": 2, "secondary": 1}
    slot = world.book.get("slot_a0")
    assert slot.capacity == 3


def test_run_100_census_digests_stable() -> None:
    p1 = _default_profile(seed=11)
    p2 = _default_profile(seed=11)
    s1 = HostParasiteWorld(p1).run(100)
    s2 = HostParasiteWorld(p2).run(100)
    assert s1["tick"] == 100
    assert s1["census"] == {"primary": 2, "secondary": 1}
    assert s1["world_digest"] == s2["world_digest"]
    assert s1["profile_digest"] == p1.digest
    assert s1["red_queen_proved"] is False
    assert s1["raises_claim_ladder"] is False


def test_ablation_content_null_changes_bag_digest() -> None:
    none_world = HostParasiteWorld(_default_profile(ablation_preset="none", seed=3))
    null_world = HostParasiteWorld(
        _default_profile(ablation_preset="content_null", seed=3)
    )
    none_world.run(1)
    null_world.run(1)
    assert none_world.state_bags["a0"]["payload"] is not None
    assert null_world.state_bags["a0"]["payload"] is None
    assert none_world.summary()["world_digest"] != null_world.summary()["world_digest"]


def test_schedule_freeze_resolves_frozen_snapshot() -> None:
    profile = _default_profile(schedule_arm="freeze", schedule_target_role="secondary", seed=5)
    world = HostParasiteWorld(profile)
    world.tick()
    assert world._lock_state is not None
    assert world._lock_state.lock_mode == "freeze"
    # Mutate live bag; resolve must return frozen snapshot for secondary member.
    world.state_bags["b0"]["payload"] = "mutated_live"
    resolved, reason = resolve_member_state(world._lock_state, "b0", world.state_bags["b0"])
    assert reason == "success"
    assert resolved["payload"] != "mutated_live"
    # Primary remains unlocked path when not in freeze member set.
    live_a = dict(world.state_bags["a0"])
    live_a["payload"] = "mutated_primary"
    resolved_a, reason_a = resolve_member_state(world._lock_state, "a0", live_a)
    assert reason_a == "success"
    assert resolved_a["payload"] == "mutated_primary"


def test_locked_adapter_validates_pack_and_pins() -> None:
    assert_baic_pins_untouched()
    record = adapt_locked_digests()
    body = record.to_dict()
    assert body["red_queen_proved"] is False
    assert body["raises_claim_ladder"] is False
    assert body["baic_pins_untouched"] is True
    assert body["pack_valid"] is True
    assert "zaman_three_arm" in body["campaign_names"]


def test_locked_adapter_refuses_mutated_pack() -> None:
    import json

    pack = json.loads(
        (REPO / "docs/hard_experiment_hp/locked_campaign_digests.json").read_text(
            encoding="utf-8"
        )
    )
    pack["red_queen_proved"] = True
    with pytest.raises(ConfigurationError):
        adapt_locked_digests(pack=pack)


def test_static_no_private_physics_audit() -> None:
    source = WORLD_SRC.read_text(encoding="utf-8")
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == "step":
            # Disallow def step on any class in this module.
            raise AssertionError("HostParasiteWorld module must not define step()")
        if isinstance(node, ast.ClassDef) and node.name == "HostParasiteWorld":
            for item in node.body:
                if isinstance(item, ast.FunctionDef) and item.name == "step":
                    raise AssertionError("HostParasiteWorld must not define step()")
    assert "HostParasiteEnv" not in source
    assert "steal_fraction" not in source
    assert "Simulation(" not in source
    assert "codontrace.life_loop" in source
    # Positioning: no peer-engine-as-baseline phrasing.
    lowered = source.casefold()
    assert "like avida" not in lowered
    assert "avida plugin" not in lowered
    assert "avida add-on" not in lowered


def test_claimgate_host_parasite_adapter_still_imports() -> None:
    from codontrace.claimgate.adapters import host_parasite as hp

    assert hasattr(hp, "attach_host_parasite_campaign")
    assert hasattr(hp, "bundle_from_host_parasite_campaign")


def test_unknown_ablation_preset_refuses() -> None:
    with pytest.raises(ConfigurationError, match="unknown ablation_preset"):
        _default_profile(ablation_preset="content")
