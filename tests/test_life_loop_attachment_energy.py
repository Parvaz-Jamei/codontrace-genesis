"""Accept tests for Phase 3 AttachmentSlot + EnergyCoupling."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from codontrace.contracts import BANNED_DOMAIN_TOKENS, world_digest
from codontrace.contracts.life_loop_events import AttachmentEvent, EnergyCouplingEvent
from codontrace.errors import ConfigurationError
from codontrace.genesis.canonical import canonical_digest
from codontrace.life_loop import (
    AttachmentBook,
    AttachmentSlot,
    EnergyCoupling,
    EnergyTransferLedgerEntry,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
LIFE_LOOP_DIR = REPO_ROOT / "src" / "codontrace" / "life_loop"


def _cfg_digest() -> str:
    return canonical_digest({"phase": 3, "fixture": "attachment_energy"}, prefix="cfg")


def test_attach_up_to_capacity_and_refuse_overflow() -> None:
    slot = AttachmentSlot(slot_id="seat_a", owner_id="owner_a", capacity=2)
    slot, ev1 = slot.attach("occ_1")
    assert isinstance(ev1, AttachmentEvent)
    assert slot.occupant_ids == ("occ_1",)
    slot, ev2 = slot.attach("occ_2")
    assert set(slot.occupant_ids) == {"occ_1", "occ_2"}
    assert slot.is_full is True
    with pytest.raises(ConfigurationError, match="seat_full"):
        slot.attach("occ_3")


def test_detach_and_absent_refuse() -> None:
    slot = AttachmentSlot(
        slot_id="seat_a", owner_id="owner_a", capacity=2, occupant_ids=("occ_1",)
    )
    slot, ev = slot.detach("occ_1")
    assert isinstance(ev, AttachmentEvent)
    assert slot.occupant_ids == ()
    with pytest.raises(ConfigurationError, match="not_occupant"):
        slot.detach("occ_1")


def test_self_attach_and_duplicate_refused() -> None:
    slot = AttachmentSlot(slot_id="seat_a", owner_id="owner_a", capacity=2)
    with pytest.raises(ConfigurationError, match="self_attach"):
        slot.attach("owner_a")
    slot, _ = slot.attach("occ_1")
    with pytest.raises(ConfigurationError, match="already_occupant"):
        slot.attach("occ_1")


def test_slot_round_trip_and_digest_mismatch() -> None:
    slot = AttachmentSlot(
        slot_id="seat_a",
        owner_id="owner_a",
        capacity=2,
        occupant_ids=("occ_2", "occ_1"),
        label="link_x",
        tick=4,
    )
    payload = slot.to_dict()
    restored = AttachmentSlot.from_dict(payload)
    assert restored.digest == slot.digest
    assert restored.to_dict() == payload
    bad = dict(payload)
    bad["digest"] = "0" * 64
    with pytest.raises(ConfigurationError, match="digest mismatch"):
        AttachmentSlot.from_dict(bad)


def test_occupant_order_does_not_change_digest() -> None:
    a = AttachmentSlot(
        slot_id="seat_a", owner_id="owner_a", capacity=3, occupant_ids=("b", "a")
    )
    b = AttachmentSlot(
        slot_id="seat_a", owner_id="owner_a", capacity=3, occupant_ids=("a", "b")
    )
    assert a.digest == b.digest
    assert a.occupant_ids == ("a", "b")


def test_energy_coupling_conservation_and_loss_residual() -> None:
    conserved = EnergyCoupling(
        coupling_id="cpl_1", source_id="src", target_id="tgt", amount=10.0
    )
    balances, event, (src_e, tgt_e), is_cons = conserved.apply(
        {"src": 50.0, "tgt": 5.0}, tick=1
    )
    assert isinstance(event, EnergyCouplingEvent)
    assert is_cons is True
    assert balances["src"] == pytest.approx(40.0)
    assert balances["tgt"] == pytest.approx(15.0)
    assert src_e.loss == pytest.approx(0.0)
    assert src_e.accepted + src_e.loss == pytest.approx(src_e.requested)

    lossy = EnergyCoupling(
        coupling_id="cpl_2",
        source_id="src",
        target_id="tgt",
        amount=10.0,
        loss_fraction=0.2,
    )
    balances2, event2, (s2, t2), is_cons2 = lossy.apply(
        {"src": 50.0, "tgt": 5.0}, tick=2
    )
    assert is_cons2 is False
    assert balances2["src"] == pytest.approx(40.0)
    assert balances2["tgt"] == pytest.approx(13.0)
    assert event2.delta_energy == pytest.approx(8.0)
    assert s2.requested == pytest.approx(10.0)
    assert s2.accepted == pytest.approx(8.0)
    assert s2.loss == pytest.approx(2.0)
    assert s2.accepted + s2.loss == pytest.approx(s2.requested)


def test_content_empty_zero_transfer() -> None:
    coupling = EnergyCoupling(
        coupling_id="cpl_1", source_id="src", target_id="tgt", amount=7.0
    )
    balances, event, (src_e, _), conserved = coupling.apply(
        {"src": 20.0, "tgt": 1.0}, tick=3, content_empty=True
    )
    assert balances == {"src": 20.0, "tgt": 1.0}
    assert event.delta_energy == pytest.approx(0.0)
    assert src_e.requested == pytest.approx(0.0)
    assert conserved is True


def test_require_attached_refuses_without_link() -> None:
    coupling = EnergyCoupling(
        coupling_id="cpl_1", source_id="src", target_id="tgt", amount=1.0
    )
    with pytest.raises(ConfigurationError, match="not_attached"):
        coupling.apply(
            {"src": 10.0, "tgt": 1.0},
            tick=1,
            require_attached=True,
            attached=False,
        )
    balances, _, _, _ = coupling.apply(
        {"src": 10.0, "tgt": 1.0},
        tick=1,
        require_attached=True,
        attached=True,
    )
    assert balances["src"] == pytest.approx(9.0)


def test_attachment_book_link_gates_coupling() -> None:
    book = AttachmentBook().add_slot(
        AttachmentSlot(slot_id="seat_a", owner_id="owner_a", capacity=1)
    )
    book, _ = book.attach("seat_a", "occ_1")
    assert book.any_link("owner_a", "occ_1") is True
    coupling = EnergyCoupling(
        coupling_id="cpl_1", source_id="owner_a", target_id="occ_1", amount=2.0
    )
    balances, _, entries, _ = coupling.apply(
        {"owner_a": 10.0, "occ_1": 0.0},
        tick=2,
        require_attached=True,
        attached=book.any_link("owner_a", "occ_1"),
    )
    assert balances["owner_a"] == pytest.approx(8.0)
    assert isinstance(entries[0], EnergyTransferLedgerEntry)


def test_world_digest_extras_pin_slot_and_coupling() -> None:
    cfg = _cfg_digest()
    slot = AttachmentSlot(slot_id="seat_a", owner_id="owner_a", capacity=1)
    coupling = EnergyCoupling(
        coupling_id="cpl_1", source_id="owner_a", target_id="occ_1", amount=1.0
    )
    d1 = world_digest(
        11,
        cfg,
        extras={
            "attachment_slot_digest": slot.digest,
            "energy_coupling_digest": coupling.digest,
        },
    )
    d2 = world_digest(
        11,
        cfg,
        extras={
            "attachment_slot_digest": slot.digest,
            "energy_coupling_digest": coupling.digest,
        },
    )
    assert d1 == d2
    slot2, _ = slot.attach("occ_1")
    d3 = world_digest(
        11,
        cfg,
        extras={
            "attachment_slot_digest": slot2.digest,
            "energy_coupling_digest": coupling.digest,
        },
    )
    assert d3 != d1


def test_ledger_composes_with_energy_accounting_field_names() -> None:
    coupling = EnergyCoupling(
        coupling_id="cpl_1", source_id="src", target_id="tgt", amount=3.0
    )
    _, _, (src_e, _), _ = coupling.apply({"src": 9.0, "tgt": 0.0}, tick=5)
    fields = src_e.as_energy_accounting_fields()
    for key in (
        "organism_id",
        "tick",
        "action",
        "runtime_atp_before",
        "runtime_atp_after",
        "action_cost",
        "blocked",
        "blocked_reason",
        "energy_delta",
    ):
        assert key in fields
    assert fields["organism_id"] == "src"
    assert fields["energy_delta"] == pytest.approx(-3.0)


def test_runtime_banned_fragments_refused() -> None:
    sample = next(iter(BANNED_DOMAIN_TOKENS))
    with pytest.raises(ConfigurationError, match="banned fragment"):
        AttachmentSlot(slot_id=f"seat_{sample}", owner_id="owner_a")
    with pytest.raises(ConfigurationError, match="banned fragment"):
        AttachmentSlot(slot_id="seat_a", owner_id="owner_a", label=f"tag_{sample}")
    with pytest.raises(ConfigurationError, match="banned fragment"):
        EnergyCoupling(
            coupling_id=f"cpl_{sample}",
            source_id="src",
            target_id="tgt",
            amount=1.0,
        )


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


def test_phase3_tests_do_not_import_discipline_modules() -> None:
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
    assert not hasattr(AttachmentSlot, "step")
    assert not hasattr(AttachmentBook, "step")
    assert not hasattr(EnergyCoupling, "step")
    assert not hasattr(AttachmentSlot, "run")
    assert not hasattr(EnergyCoupling, "run")


def test_type_names_free_of_domain_nouns() -> None:
    names = (
        "AttachmentSlot",
        "AttachmentBook",
        "EnergyCoupling",
        "EnergyTransferLedgerEntry",
        "AttachFailReason",
        "CouplingFailReason",
    )
    banned = {t.casefold() for t in BANNED_DOMAIN_TOKENS}
    for name in names:
        lowered = name.casefold()
        for token in banned:
            assert token not in lowered, f"{name} embeds {token}"


def test_insufficient_energy_refused_by_default() -> None:
    coupling = EnergyCoupling(
        coupling_id="cpl_1", source_id="src", target_id="tgt", amount=10.0
    )
    with pytest.raises(ConfigurationError, match="insufficient_energy"):
        coupling.apply({"src": 3.0, "tgt": 0.0}, tick=1)
    balances, _, (src_e, _), _ = coupling.apply(
        {"src": 3.0, "tgt": 0.0}, tick=1, allow_partial=True
    )
    assert balances["src"] == pytest.approx(0.0)
    assert src_e.requested == pytest.approx(3.0)


def test_nan_amount_refused() -> None:
    with pytest.raises(ConfigurationError):
        EnergyCoupling(
            coupling_id="cpl_1", source_id="src", target_id="tgt", amount=float("nan")
        )


def test_capacity_must_be_at_least_one() -> None:
    with pytest.raises(ConfigurationError):
        AttachmentSlot(slot_id="seat_a", owner_id="owner_a", capacity=0)
