"""Phase 5: AblationTemplate + ScheduleLock life-loop primitives."""

from __future__ import annotations

from pathlib import Path

import pytest

from codontrace.contracts import (
    BANNED_DOMAIN_TOKENS,
    AblationArmEvent,
    ScheduleLockEvent,
    world_digest,
)
from codontrace.errors import ConfigurationError
from codontrace.genesis.canonical import canonical_digest
from codontrace.life_loop import (
    AblationAttemptCensus,
    AblationTemplate,
    PopulationRegistry,
    ScheduleLock,
    ScheduleLockAttemptCensus,
    apply_ablation,
    apply_replay_frame,
    apply_schedule_lock,
    he02_axis_mode,
    mode_axes,
    resolve_member_state,
)
from codontrace.life_loop.ablation_template import HE02_AXIS_MAP
from codontrace.life_loop.schedule_lock import resolve_target_members

LIFE_LOOP_ROOT = Path(__file__).resolve().parents[1] / "src" / "codontrace" / "life_loop"
NEW_MODULES = (
    LIFE_LOOP_ROOT / "ablation_template.py",
    LIFE_LOOP_ROOT / "schedule_lock.py",
)


def _sample_bag() -> dict[str, object]:
    return {
        "payload": "alpha",
        "signal": 7,
        "link_tag": "grid_a",
        "overlap": True,
    }


def test_mode_axes_pairs() -> None:
    assert mode_axes("none") == (False, False)
    assert mode_axes("content_null") == (True, False)
    assert mode_axes("structure_null") == (False, True)
    assert mode_axes("dual_null") == (True, True)


def test_none_leaves_bag_unchanged() -> None:
    template = AblationTemplate(arm_id="arm_none", mode="none")
    bag = _sample_bag()
    record, census = apply_ablation(template, bag, tick=3)
    assert record.reason == "success"
    assert record.bag == bag
    assert record.before_digest == record.after_digest
    assert record.event is not None
    assert record.event.content_null is False
    assert record.event.structure_null is False
    assert census.attempts == 1
    assert census.counts["success"] == 1


def test_content_null_clears_content_preserves_structure() -> None:
    template = AblationTemplate(
        arm_id="arm_c",
        mode="content_null",
        content_keys=("payload", "signal"),
        structure_keys=("link_tag", "overlap"),
    )
    record, _ = apply_ablation(template, _sample_bag(), tick=1)
    assert record.bag["payload"] is None
    assert record.bag["signal"] is None
    assert record.bag["link_tag"] == "grid_a"
    assert record.bag["overlap"] is True
    assert record.before_digest != record.after_digest
    assert record.event is not None
    assert record.event.content_null is True
    assert record.event.structure_null is False


def test_structure_null_clears_structure_preserves_content() -> None:
    template = AblationTemplate(
        arm_id="arm_s",
        mode="structure_null",
        content_keys=("payload", "signal"),
        structure_keys=("link_tag", "overlap"),
    )
    record, _ = apply_ablation(template, _sample_bag(), tick=1)
    assert record.bag["payload"] == "alpha"
    assert record.bag["signal"] == 7
    assert record.bag["link_tag"] is None
    assert record.bag["overlap"] is None
    assert record.before_digest != record.after_digest
    assert record.event is not None
    assert record.event.structure_null is True


def test_dual_null_differs_from_single_null() -> None:
    keys_c = ("payload", "signal")
    keys_s = ("link_tag", "overlap")
    bag = _sample_bag()
    content = AblationTemplate(
        arm_id="c", mode="content_null", content_keys=keys_c, structure_keys=keys_s
    )
    structure = AblationTemplate(
        arm_id="s", mode="structure_null", content_keys=keys_c, structure_keys=keys_s
    )
    dual = AblationTemplate(
        arm_id="d", mode="dual_null", content_keys=keys_c, structure_keys=keys_s
    )
    r_c, _ = apply_ablation(content, bag, tick=0)
    r_s, _ = apply_ablation(structure, bag, tick=0)
    r_d, _ = apply_ablation(dual, bag, tick=0)
    assert r_d.after_digest != r_c.after_digest
    assert r_d.after_digest != r_s.after_digest
    assert r_d.event is not None
    assert r_d.event.content_null and r_d.event.structure_null


def test_template_round_trip_and_digest_mismatch() -> None:
    template = AblationTemplate(
        arm_id="rt",
        mode="dual_null",
        content_keys=("payload",),
        structure_keys=("link_tag",),
    )
    loaded = AblationTemplate.from_dict(template.to_dict())
    assert loaded == template
    bad = template.to_dict()
    bad["digest"] = "0" * 64
    with pytest.raises(ConfigurationError, match="digest mismatch"):
        AblationTemplate.from_dict(bad)


def test_key_overlap_and_keys_required() -> None:
    with pytest.raises(ConfigurationError, match="overlap"):
        AblationTemplate(
            arm_id="bad",
            mode="dual_null",
            content_keys=("x",),
            structure_keys=("x",),
        )
    with pytest.raises(ConfigurationError, match="content_keys"):
        AblationTemplate(arm_id="bad", mode="content_null", content_keys=())
    with pytest.raises(ConfigurationError, match="structure_keys"):
        AblationTemplate(arm_id="bad", mode="structure_null", structure_keys=())


def test_he02_axis_map() -> None:
    assert he02_axis_mode("content_null") == "content_null"
    assert he02_axis_mode("channel_off") == "structure_null"
    assert he02_axis_mode("capsules_shuffled") == "content_null"
    assert AblationTemplate.from_he02_arm(
        "channel_off", content_keys=("p",), structure_keys=("s",)
    ).mode == "structure_null"
    with pytest.raises(ConfigurationError, match="unknown HE02"):
        he02_axis_mode("not_an_arm")
    assert "content_null" in HE02_AXIS_MAP


def test_ablation_census_sum_check() -> None:
    template = AblationTemplate(arm_id="n", mode="none")
    census = AblationAttemptCensus()
    _, census = apply_ablation(template, {}, tick=0, census=census)
    _, census = apply_ablation(template, {}, tick=1, census=census)
    assert census.attempts == sum(census.counts.values())
    assert census.counts["success"] == 2


def test_ablation_banned_arm_id() -> None:
    sample = next(iter(BANNED_DOMAIN_TOKENS))
    with pytest.raises(ConfigurationError, match="banned"):
        AblationTemplate(arm_id=f"arm_{sample}", mode="none")


def test_freeze_vs_unlock_divergence() -> None:
    registry = PopulationRegistry().create_population(
        "pop_a", member_ids=("m1", "m2"), schedule_partition="part_x"
    )
    live = {
        "m1": {"geno": "A", "score": 1},
        "m2": {"geno": "B", "score": 2},
    }
    freeze_lock = ScheduleLock(
        schedule_id="sched_1", lock_mode="freeze", population_id="pop_a"
    )
    state_f, record_f, _ = apply_schedule_lock(freeze_lock, registry, live, tick=0)
    assert record_f.reason == "success"
    assert state_f.lock_mode == "freeze"
    assert isinstance(record_f.event, ScheduleLockEvent)

    # Live bags mutate; freeze resolve keeps snapshot.
    live_mutated = {
        "m1": {"geno": "Z", "score": 99},
        "m2": {"geno": "Y", "score": 88},
    }
    frozen_m1, reason = resolve_member_state(state_f, "m1", live_mutated["m1"])
    assert reason == "success"
    assert frozen_m1 == {"geno": "A", "score": 1}

    unlock = ScheduleLock(
        schedule_id="sched_1", lock_mode="unlock", population_id="pop_a"
    )
    state_u, record_u, _ = apply_schedule_lock(
        unlock, registry, live_mutated, tick=1, prior=state_f
    )
    assert record_u.reason == "success"
    assert state_u.lock_mode == "unlock"
    live_m1, reason_u = resolve_member_state(state_u, "m1", live_mutated["m1"])
    assert reason_u == "success"
    assert live_m1 == {"geno": "Z", "score": 99}
    assert state_f.digest != state_u.digest


def test_schedule_partition_targets_all_tagged() -> None:
    registry = (
        PopulationRegistry()
        .create_population("p1", member_ids=("a",), schedule_partition="slot_1")
        .create_population("p2", member_ids=("b",), schedule_partition="slot_1")
        .create_population("p3", member_ids=("c",), schedule_partition="other")
    )
    members = resolve_target_members(registry, schedule_partition="slot_1")
    assert members == ("a", "b")
    lock = ScheduleLock(
        schedule_id="s", lock_mode="freeze", schedule_partition="slot_1"
    )
    bags = {"a": {"v": 1}, "b": {"v": 2}, "c": {"v": 3}}
    state, record, _ = apply_schedule_lock(lock, registry, bags, tick=0)
    assert record.reason == "success"
    assert state.member_ids == ("a", "b")
    resolved_c, _ = resolve_member_state(state, "c", bags["c"])
    assert resolved_c == {"v": 3}  # not locked


def test_replay_schedule_bit_identical() -> None:
    registry = PopulationRegistry().create_population(
        "pop_b", member_ids=("x", "y")
    )
    frames = (
        {"x": {"t": 0}, "y": {"t": 0}},
        {"x": {"t": 1}, "y": {"t": 1}},
    )
    lock = ScheduleLock(
        schedule_id="rep", lock_mode="replay_schedule", population_id="pop_b"
    )
    state1, rec1, _ = apply_schedule_lock(
        lock, registry, {"x": {}, "y": {}}, tick=0, frames=frames
    )
    state2, rec2, _ = apply_schedule_lock(
        lock, registry, {"x": {}, "y": {}}, tick=0, frames=frames
    )
    assert rec1.reason == rec2.reason == "success"
    assert state1.digest == state2.digest

    s1a, frame1a, r1a = apply_replay_frame(state1, tick=1)
    s2a, frame2a, r2a = apply_replay_frame(state2, tick=1)
    assert r1a == r2a == "success"
    assert frame1a == frame2a == {"x": {"t": 0}, "y": {"t": 0}}
    assert s1a.digest == s2a.digest

    bag_x, reason = resolve_member_state(state1, "x", {"live": True})
    assert reason == "success"
    assert bag_x == {"t": 0}


def test_replay_requires_frames() -> None:
    registry = PopulationRegistry().create_population("pop_b", member_ids=("x",))
    lock = ScheduleLock(
        schedule_id="rep", lock_mode="replay_schedule", population_id="pop_b"
    )
    _, record, census = apply_schedule_lock(lock, registry, {"x": {}}, tick=0, frames=())
    assert record.reason == "frames_required"
    assert census.counts["frames_required"] == 1


def test_schedule_lock_round_trip_and_target_rules() -> None:
    lock = ScheduleLock(schedule_id="s1", lock_mode="freeze", population_id="p")
    assert ScheduleLock.from_dict(lock.to_dict()) == lock
    with pytest.raises(ConfigurationError, match="exactly one|required"):
        ScheduleLock(schedule_id="s", lock_mode="freeze")
    with pytest.raises(ConfigurationError, match="exactly one"):
        ScheduleLock(
            schedule_id="s",
            lock_mode="freeze",
            population_id="p",
            schedule_partition="t",
        )
    bad = lock.to_dict()
    bad["digest"] = "0" * 64
    with pytest.raises(ConfigurationError, match="digest mismatch"):
        ScheduleLock.from_dict(bad)


def test_schedule_lock_census_and_banned() -> None:
    registry = PopulationRegistry().create_population("pop_a", member_ids=("m1",))
    lock = ScheduleLock(schedule_id="ok", lock_mode="unlock", population_id="pop_a")
    census = ScheduleLockAttemptCensus()
    _, _, census = apply_schedule_lock(lock, registry, {"m1": {}}, tick=0, census=census)
    _, _, census = apply_schedule_lock(lock, registry, {"m1": {}}, tick=1, census=census)
    assert census.attempts == sum(census.counts.values())
    sample = next(iter(BANNED_DOMAIN_TOKENS))
    with pytest.raises(ConfigurationError, match="banned"):
        ScheduleLock(schedule_id=f"id_{sample}", lock_mode="unlock", population_id="p")


def test_world_digest_extras_pin_digests() -> None:
    template = AblationTemplate(arm_id="arm", mode="none")
    lock = ScheduleLock(schedule_id="s", lock_mode="unlock", population_id="p")
    cfg = canonical_digest({"phase": 5}, prefix="cfg")
    d1 = world_digest(7, cfg, extras={"ablation": template.digest, "lock": lock.digest})
    d2 = world_digest(7, cfg, extras={"ablation": template.digest, "lock": lock.digest})
    assert d1 == d2
    d3 = world_digest(8, cfg, extras={"ablation": template.digest, "lock": lock.digest})
    assert d1 != d3


def test_events_loadable() -> None:
    arm = AblationArmEvent(arm_id="a", content_null=True, structure_null=False, tick=0)
    lock = ScheduleLockEvent(
        population_id="p", lock_mode="freeze", tick=0, schedule_id="s"
    )
    assert arm.digest
    assert lock.digest


def test_no_domain_tokens_in_new_modules() -> None:
    for path in NEW_MODULES:
        text = path.read_text(encoding="utf-8").casefold()
        for token in BANNED_DOMAIN_TOKENS:
            assert token.casefold() not in text, f"{path.name} contains {token}"


def test_no_step_or_hp_imports_in_new_modules() -> None:
    for path in NEW_MODULES:
        text = path.read_text(encoding="utf-8")
        assert "host_parasite" not in text
        assert "ClaimGate" not in text and "claimgate" not in text.casefold()
        assert ".step(" not in text
        assert "Simulation" not in text
