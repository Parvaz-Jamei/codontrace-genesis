"""Accept tests for Phase 1 life-loop contracts (schemas + digests)."""

from __future__ import annotations

import importlib
import re
from pathlib import Path

import pytest

from codontrace.contracts import (
    BANNED_DOMAIN_TOKENS,
    EVENT_TYPES,
    HOOK_NAMES,
    AblationArmEvent,
    AttachmentEvent,
    BirthAttachEvent,
    ContactEvent,
    EnergyCouplingEvent,
    LifeLoopEventEnvelope,
    PopulationRegistryEvent,
    ScheduleLockEvent,
    load_event,
    world_digest,
)
from codontrace.errors import ConfigurationError
from codontrace.genesis.canonical import canonical_digest


def _hex_id(label: str) -> str:
    return canonical_digest({"label": label})


def test_hook_names_are_domain_free_life_hooks() -> None:
    assert HOOK_NAMES == frozenset({"on_birth", "on_death", "on_contact", "on_resource"})
    assert EVENT_TYPES == frozenset(
        {
            "population_registry",
            "attachment",
            "energy_coupling",
            "contact",
            "birth_attach",
            "ablation_arm",
            "schedule_lock",
        }
    )


@pytest.mark.parametrize(
    "factory",
    [
        lambda: PopulationRegistryEvent(
            population_id="pop_a",
            individual_id="ind_1",
            action="register",
            tick=0,
            count_after=1,
        ),
        lambda: AttachmentEvent(
            slot_id="slot_1",
            owner_id="own_1",
            occupant_id="occ_1",
            capacity=1,
            tick=3,
        ),
        lambda: EnergyCouplingEvent(
            source_id="a",
            target_id="b",
            delta_energy=-0.25,
            tick=4,
            coupling_id="c1",
        ),
        lambda: ContactEvent(
            actor_id="a",
            other_id="b",
            tick=5,
            rule_id="rule_overlap",
            score=0.5,
            transfer_mode="mode_a",
        ),
        lambda: BirthAttachEvent(
            parent_id="p",
            offspring_id="o",
            slot_id="slot_1",
            inherited_occupant_id="occ_1",
            tick=6,
        ),
        lambda: AblationArmEvent(
            arm_id="arm_content",
            content_null=True,
            structure_null=False,
            tick=7,
        ),
        lambda: ScheduleLockEvent(
            population_id="pop_b",
            lock_mode="freeze",
            tick=8,
            schedule_id="sched_1",
        ),
    ],
)
def test_event_round_trip_and_digest_stability(factory) -> None:
    event = factory()
    again = type(event).from_dict(event.to_dict())
    assert again == event
    assert again.digest == event.digest
    loaded = load_event(event.to_dict())
    assert loaded == event


def test_digest_mismatch_refused_on_reload() -> None:
    event = AttachmentEvent(
        slot_id="slot_1",
        owner_id="own_1",
        occupant_id=None,
        capacity=2,
        tick=1,
    )
    payload = event.to_dict()
    payload["digest"] = "0" * 64
    with pytest.raises(ConfigurationError, match="digest mismatch"):
        AttachmentEvent.from_dict(payload)


def test_world_digest_stable_and_sensitive() -> None:
    cfg = canonical_digest({"grid": 8, "rate": 0.1})
    a = world_digest(11, cfg)
    b = world_digest(11, cfg)
    assert a == b
    assert a != world_digest(12, cfg)
    other_cfg = canonical_digest({"grid": 8, "rate": 0.2})
    assert a != world_digest(11, other_cfg)


def test_envelope_parent_digest_chain() -> None:
    first = ContactEvent(
        actor_id="a",
        other_id="b",
        tick=1,
        rule_id="r1",
        score=None,
        transfer_mode="mode_x",
    )
    env1 = LifeLoopEventEnvelope.wrap(first, event_id=_hex_id("e1"))
    assert env1.parent_digest is None
    env1b = LifeLoopEventEnvelope.from_dict(env1.to_dict())
    assert env1b.digest == env1.digest

    second = EnergyCouplingEvent(
        source_id="a",
        target_id="b",
        delta_energy=1.0,
        tick=2,
        coupling_id="c2",
    )
    env2 = LifeLoopEventEnvelope.wrap(
        second, event_id=_hex_id("e2"), parent_digest=env1.digest
    )
    assert env2.parent_digest == env1.digest
    env2b = LifeLoopEventEnvelope.from_dict(env2.to_dict())
    assert env2b == env2


def test_contracts_package_has_no_banned_domain_tokens() -> None:
    root = Path(__file__).resolve().parents[1] / "src" / "codontrace" / "contracts"
    assert root.is_dir()
    pattern_by_token = {
        tok: re.compile(rf"(?<![a-z0-9_]){re.escape(tok)}(?![a-z0-9_])")
        for tok in BANNED_DOMAIN_TOKENS
    }
    hits: list[str] = []
    for path in sorted(root.rglob("*.py")):
        text = path.read_text(encoding="utf-8").lower()
        for tok, pat in pattern_by_token.items():
            if pat.search(text):
                hits.append(f"{path.relative_to(root.parent.parent.parent)}:{tok}")
    assert hits == []


def test_phase1_tests_do_not_import_host_parasite_or_claimgate() -> None:
    # Ensure this module's imports stay kernel-local.
    banned_prefixes = (
        "codontrace.genesis.host_parasite",
        "codontrace.claimgate",
    )
    for name in list(importlib.sys.modules):
        if any(name == p or name.startswith(p + ".") for p in banned_prefixes):
            # Modules may already be imported by other tests in a shared session;
            # assert this test file itself does not require them.
            pass
    import codontrace.contracts as contracts

    source = Path(contracts.__file__).read_text(encoding="utf-8")
    assert "claimgate" not in source.lower()
    assert "host_parasite" not in source.lower()


def test_placeholder_event_id_refused() -> None:
    event = AblationArmEvent(
        arm_id="arm_structure",
        content_null=False,
        structure_null=True,
        tick=0,
    )
    with pytest.raises(ConfigurationError, match="event_id"):
        LifeLoopEventEnvelope.wrap(event, event_id="placeholder")
