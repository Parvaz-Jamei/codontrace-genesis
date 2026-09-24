"""Accept tests for Phase 4 ContactTransfer + InheritAttached."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from codontrace.contracts import BANNED_DOMAIN_TOKENS, world_digest
from codontrace.contracts.life_loop_events import BirthAttachEvent, ContactEvent
from codontrace.errors import ConfigurationError
from codontrace.genesis.canonical import canonical_digest
from codontrace.life_loop import (
    AttachmentBook,
    AttachmentSlot,
    ContactAttemptCensus,
    ContactTransferPolicy,
    InheritAttachedPolicy,
    InheritAttemptCensus,
    apply_birth_inherit,
    apply_contact,
    select_contact_candidates,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
LIFE_LOOP_DIR = REPO_ROOT / "src" / "codontrace" / "life_loop"


def _cfg_digest() -> str:
    return canonical_digest({"phase": 4, "fixture": "contact_inherit"}, prefix="cfg")


def test_well_mixed_vs_local_candidates_differ() -> None:
    members = ("actor_a", "other_b", "other_c", "other_d")
    mixed = select_contact_candidates(
        "actor_a", members, candidate_mode="well_mixed"
    )
    assert mixed == ("other_b", "other_c", "other_d")
    local = select_contact_candidates(
        "actor_a",
        members,
        candidate_mode="local",
        neighbors={"actor_a": ("other_b", "other_d", "stranger")},
    )
    assert local == ("other_b", "other_d")
    assert set(local) != set(mixed)
    with pytest.raises(ConfigurationError, match="neighbors_required"):
        select_contact_candidates("actor_a", members, candidate_mode="local")


def test_match_rule_bool_and_graded_score() -> None:
    policy = ContactTransferPolicy(rule_id="rule_1", transfer_mode="none")
    members = ("actor_a", "other_b")
    payloads, book, event, reason, census = apply_contact(
        policy,
        actor_id="actor_a",
        other_id="other_b",
        tick=1,
        member_ids=members,
        match_rule=lambda a, b: False,
    )
    assert reason == "match_failed"
    assert event is None
    assert census.attempts == 1
    assert census.counts["match_failed"] == 1

    payloads, book, event, reason, census = apply_contact(
        policy,
        actor_id="actor_a",
        other_id="other_b",
        tick=2,
        member_ids=members,
        match_rule=lambda a, b: 0.75,
        census=ContactAttemptCensus(),
    )
    assert reason == "success"
    assert isinstance(event, ContactEvent)
    assert event.score == pytest.approx(0.75)
    assert event.transfer_mode == "none"


def test_payload_copy_and_move_all_or_nothing() -> None:
    policy_copy = ContactTransferPolicy(
        rule_id="rule_copy",
        transfer_mode="payload_copy",
        payload_keys=("beta", "alpha"),
    )
    assert policy_copy.payload_keys == ("alpha", "beta")
    payloads = {"actor_a": {"alpha": 1, "beta": 2, "gamma": 3}, "other_b": {}}
    new_p, _, event, reason, _ = apply_contact(
        policy_copy,
        actor_id="actor_a",
        other_id="other_b",
        tick=1,
        member_ids=("actor_a", "other_b"),
        payloads=payloads,
    )
    assert reason == "success"
    assert isinstance(event, ContactEvent)
    assert new_p["other_b"]["alpha"] == 1
    assert new_p["other_b"]["beta"] == 2
    assert new_p["actor_a"]["alpha"] == 1  # copy keeps sender

    policy_move = ContactTransferPolicy(
        rule_id="rule_move",
        transfer_mode="payload_move",
        payload_keys=("alpha", "beta"),
    )
    new_p2, _, _, reason2, _ = apply_contact(
        policy_move,
        actor_id="actor_a",
        other_id="other_b",
        tick=2,
        member_ids=("actor_a", "other_b"),
        payloads=payloads,
    )
    assert reason2 == "success"
    assert "alpha" not in new_p2["actor_a"]
    assert "beta" not in new_p2["actor_a"]
    assert new_p2["actor_a"]["gamma"] == 3
    assert new_p2["other_b"]["alpha"] == 1

    bad = ContactTransferPolicy(
        rule_id="rule_bad",
        transfer_mode="payload_copy",
        payload_keys=("alpha", "missing"),
    )
    _, _, event3, reason3, _ = apply_contact(
        bad,
        actor_id="actor_a",
        other_id="other_b",
        tick=3,
        member_ids=("actor_a", "other_b"),
        payloads=payloads,
    )
    assert reason3 == "payload_incomplete"
    assert event3 is None


def test_seat_attach_via_attachment_book() -> None:
    book = AttachmentBook().add_slot(
        AttachmentSlot(slot_id="seat_tgt", owner_id="other_b", capacity=1)
    )
    policy = ContactTransferPolicy(
        rule_id="rule_seat",
        transfer_mode="seat_attach",
        target_slot_id="seat_tgt",
    )
    _, new_book, event, reason, _ = apply_contact(
        policy,
        actor_id="actor_a",
        other_id="other_b",
        tick=1,
        member_ids=("actor_a", "other_b"),
        book=book,
    )
    assert reason == "success"
    assert isinstance(event, ContactEvent)
    assert new_book is not None
    assert new_book.get("seat_tgt").has_occupant("actor_a")

    _, _, _, reason2, _ = apply_contact(
        policy,
        actor_id="actor_a",
        other_id="other_b",
        tick=2,
        member_ids=("actor_a", "other_b"),
        book=new_book,
    )
    assert reason2 == "already_occupant"


def test_require_attached_gate_on_contact() -> None:
    book = AttachmentBook().add_slot(
        AttachmentSlot(slot_id="seat_a", owner_id="owner_x", capacity=2)
    )
    book, _ = book.attach("seat_a", "actor_a")
    policy = ContactTransferPolicy(
        rule_id="rule_req",
        transfer_mode="none",
        require_attached=True,
    )
    _, _, _, reason, _ = apply_contact(
        policy,
        actor_id="actor_a",
        other_id="other_b",
        tick=1,
        member_ids=("actor_a", "other_b", "owner_x"),
        book=book,
    )
    assert reason == "not_attached"

    book2, _ = book.attach("seat_a", "other_b")
    # actor_a and other_b both occupants of owner_x seat — any_link checks owner↔occupant
    # so actor_a linked to owner_x, not to other_b. Use owner link:
    policy2 = ContactTransferPolicy(
        rule_id="rule_req2",
        transfer_mode="none",
        require_attached=True,
    )
    _, _, event, reason2, _ = apply_contact(
        policy2,
        actor_id="owner_x",
        other_id="actor_a",
        tick=2,
        member_ids=("actor_a", "other_b", "owner_x"),
        book=book2,
    )
    assert reason2 == "success"
    assert event is not None


def test_policy_round_trip_and_digest_mismatch() -> None:
    policy = ContactTransferPolicy(
        rule_id="rule_1",
        transfer_mode="payload_copy",
        payload_keys=("z", "a"),
        label="pkg",
    )
    payload = policy.to_dict()
    restored = ContactTransferPolicy.from_dict(payload)
    assert restored.digest == policy.digest
    assert restored.payload_keys == ("a", "z")
    bad = dict(payload)
    bad["digest"] = "0" * 64
    with pytest.raises(ConfigurationError, match="digest mismatch"):
        ContactTransferPolicy.from_dict(bad)

    inh = InheritAttachedPolicy(
        policy_id="inh_1", mode="share", probability=0.5, parent_slot_id="seat_p"
    )
    ip = inh.to_dict()
    assert InheritAttachedPolicy.from_dict(ip).digest == inh.digest
    bad_i = dict(ip)
    bad_i["digest"] = "0" * 64
    with pytest.raises(ConfigurationError, match="digest mismatch"):
        InheritAttachedPolicy.from_dict(bad_i)


def test_inherit_none_leaves_offspring_empty() -> None:
    book = AttachmentBook().add_slot(
        AttachmentSlot(
            slot_id="seat_p", owner_id="parent_x", capacity=2, occupant_ids=("occ_1",)
        )
    )
    policy = InheritAttachedPolicy(policy_id="inh_none", mode="none")
    new_book, events, reasons, census = apply_birth_inherit(
        policy, book, parent_id="parent_x", offspring_id="child_y", tick=3
    )
    assert reasons == ("mode_none",)
    assert len(events) == 1
    assert isinstance(events[0], BirthAttachEvent)
    assert events[0].inherited_occupant_id is None
    assert new_book.get("seat_p").occupant_ids == ("occ_1",)
    # no offspring slot created
    assert "seat_p__child_y" not in new_book.list_slot_ids()
    assert census.counts["mode_none"] == 1


def test_inherit_copy_parent_unchanged() -> None:
    book = AttachmentBook().add_slot(
        AttachmentSlot(
            slot_id="seat_p",
            owner_id="parent_x",
            capacity=2,
            occupant_ids=("occ_2", "occ_1"),
        )
    )
    policy = InheritAttachedPolicy(
        policy_id="inh_copy",
        mode="copy",
        probability=1.0,
        parent_slot_id="seat_p",
        offspring_slot_id="seat_c",
    )
    new_book, events, reasons, census = apply_birth_inherit(
        policy, book, parent_id="parent_x", offspring_id="child_y", tick=4
    )
    assert set(reasons) == {"success"}
    assert new_book.get("seat_p").occupant_ids == ("occ_1", "occ_2")
    assert set(new_book.get("seat_c").occupant_ids) == {"occ_1", "occ_2"}
    assert new_book.get("seat_c").owner_id == "child_y"
    assert all(e.inherited_occupant_id is not None for e in events)
    assert census.attempts == 2
    assert census.counts["success"] == 2


def test_inherit_share_dual_link() -> None:
    book = AttachmentBook().add_slot(
        AttachmentSlot(
            slot_id="seat_p", owner_id="parent_x", capacity=1, occupant_ids=("occ_1",)
        )
    )
    policy = InheritAttachedPolicy(
        policy_id="inh_share",
        mode="share",
        probability=1.0,
        parent_slot_id="seat_p",
        offspring_slot_id="seat_c",
    )
    new_book, events, reasons, census = apply_birth_inherit(
        policy, book, parent_id="parent_x", offspring_id="child_y", tick=5
    )
    assert "success" in reasons
    assert new_book.get("seat_p").has_occupant("occ_1")
    assert new_book.get("seat_c").has_occupant("occ_1")
    assert events[0].inherited_occupant_id == "occ_1"
    assert "share_parent_missing" not in reasons
    assert "share_offspring_missing" not in reasons
    assert census.counts.get("success", 0) >= 1


def test_inherit_probability_draws() -> None:
    book = AttachmentBook().add_slot(
        AttachmentSlot(
            slot_id="seat_p", owner_id="parent_x", capacity=2, occupant_ids=("occ_1",)
        )
    )
    policy = InheritAttachedPolicy(
        policy_id="inh_p",
        mode="copy",
        probability=0.5,
        parent_slot_id="seat_p",
        offspring_slot_id="seat_c",
    )
    # draw >= probability => skip
    new_book, events, reasons, _ = apply_birth_inherit(
        policy,
        book,
        parent_id="parent_x",
        offspring_id="child_y",
        tick=6,
        draws=(0.9,),
    )
    assert reasons == ("skipped_draw",)
    assert events[0].inherited_occupant_id is None
    assert new_book.get("seat_c").occupant_ids == ()

    # draw < probability => inherit
    new_book2, events2, reasons2, _ = apply_birth_inherit(
        policy,
        book,
        parent_id="parent_x",
        offspring_id="child_z",
        tick=7,
        draws=(0.1,),
    )
    assert reasons2 == ("success",)
    assert events2[0].inherited_occupant_id == "occ_1"
    assert new_book2.get("seat_c").has_occupant("occ_1")
    assert new_book2.get("seat_p").has_occupant("occ_1")  # parent retained


def test_attempt_census_sum_check() -> None:
    with pytest.raises(ConfigurationError, match="sum mismatch"):
        ContactAttemptCensus(attempts=2, counts={"success": 1})
    census = ContactAttemptCensus(attempts=0, counts={})
    census = census.record("success").record("match_failed")
    assert census.attempts == 2
    assert sum(census.counts.values()) == 2

    with pytest.raises(ConfigurationError, match="sum mismatch"):
        InheritAttemptCensus(attempts=1, counts={})


def test_world_digest_extras_pin_policies() -> None:
    cfg = _cfg_digest()
    ct = ContactTransferPolicy(rule_id="rule_1", transfer_mode="none")
    inh = InheritAttachedPolicy(policy_id="inh_1", mode="none")
    d1 = world_digest(
        21,
        cfg,
        extras={
            "contact_policy_digest": ct.digest,
            "inherit_policy_digest": inh.digest,
        },
    )
    d2 = world_digest(
        21,
        cfg,
        extras={
            "contact_policy_digest": ct.digest,
            "inherit_policy_digest": inh.digest,
        },
    )
    assert d1 == d2
    ct2 = ContactTransferPolicy(rule_id="rule_2", transfer_mode="none")
    d3 = world_digest(
        21,
        cfg,
        extras={
            "contact_policy_digest": ct2.digest,
            "inherit_policy_digest": inh.digest,
        },
    )
    assert d3 != d1


def test_runtime_banned_fragments_refused() -> None:
    sample = next(iter(BANNED_DOMAIN_TOKENS))
    with pytest.raises(ConfigurationError, match="banned fragment"):
        ContactTransferPolicy(rule_id=f"rule_{sample}")
    with pytest.raises(ConfigurationError, match="banned fragment"):
        ContactTransferPolicy(rule_id="rule_ok", payload_keys=(f"key_{sample}",))
    with pytest.raises(ConfigurationError, match="banned fragment"):
        InheritAttachedPolicy(policy_id=f"inh_{sample}")


def test_banned_tokens_absent_from_new_life_loop_modules() -> None:
    offenders: list[str] = []
    for path in sorted(LIFE_LOOP_DIR.rglob("*.py")):
        text = path.read_text(encoding="utf-8").casefold()
        for token in BANNED_DOMAIN_TOKENS:
            if token.casefold() in text:
                offenders.append(f"{path.name}:{token}")
    assert offenders == []


def test_no_host_parasite_or_claimgate_imports_in_life_loop() -> None:
    forbidden = ("host_parasite", "claimgate", "claim_gate")
    for path in sorted(LIFE_LOOP_DIR.rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    lowered = alias.name.casefold()
                    for frag in forbidden:
                        assert frag not in lowered, f"{path.name} imports {alias.name}"
            elif isinstance(node, ast.ImportFrom) and node.module:
                lowered = node.module.casefold()
                for frag in forbidden:
                    assert frag not in lowered, f"{path.name} imports {node.module}"


def test_phase4_tests_do_not_import_discipline_modules() -> None:
    path = Path(__file__)
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    forbidden = ("host_parasite", "claimgate", "claim_gate")
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                lowered = alias.name.casefold()
                for frag in forbidden:
                    assert frag not in lowered
        elif isinstance(node, ast.ImportFrom) and node.module:
            lowered = node.module.casefold()
            for frag in forbidden:
                assert frag not in lowered


def test_no_second_tick_loop_api() -> None:
    assert not hasattr(ContactTransferPolicy, "step")
    assert not hasattr(InheritAttachedPolicy, "step")
    assert not hasattr(ContactTransferPolicy, "run")
    assert not hasattr(InheritAttachedPolicy, "run")
    import codontrace.life_loop.contact as contact_mod
    import codontrace.life_loop.inherit_attached as inherit_mod

    assert not hasattr(contact_mod, "step")
    assert not hasattr(inherit_mod, "step")


def test_type_names_free_of_domain_nouns() -> None:
    names = (
        "ContactTransferPolicy",
        "ContactAttemptCensus",
        "InheritAttachedPolicy",
        "InheritAttemptCensus",
        "TransferMode",
        "CandidateMode",
        "InheritMode",
        "MatchRule",
        "apply_contact",
        "apply_birth_inherit",
        "select_contact_candidates",
    )
    banned = {t.casefold() for t in BANNED_DOMAIN_TOKENS}
    for name in names:
        lowered = name.casefold()
        for token in banned:
            assert token not in lowered, f"{name} embeds {token}"


def test_identical_endpoints_and_not_in_candidates() -> None:
    policy = ContactTransferPolicy(rule_id="rule_1", transfer_mode="none")
    _, _, _, reason, _ = apply_contact(
        policy,
        actor_id="actor_a",
        other_id="actor_a",
        tick=1,
        member_ids=("actor_a", "other_b"),
    )
    assert reason == "identical_endpoints"
    _, _, _, reason2, _ = apply_contact(
        policy,
        actor_id="actor_a",
        other_id="other_c",
        tick=1,
        member_ids=("actor_a", "other_b"),
    )
    assert reason2 == "not_in_candidates"


def test_nan_match_score_refused() -> None:
    policy = ContactTransferPolicy(rule_id="rule_1", transfer_mode="none")
    _, _, _, reason, _ = apply_contact(
        policy,
        actor_id="actor_a",
        other_id="other_b",
        tick=1,
        member_ids=("actor_a", "other_b"),
        match_rule=lambda a, b: float("nan"),
    )
    assert reason == "non_finite"
