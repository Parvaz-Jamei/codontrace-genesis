"""Accept tests for Phase 2 domain-free multi-population registry."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from codontrace.contracts import BANNED_DOMAIN_TOKENS, world_digest
from codontrace.contracts.life_loop_events import PopulationRegistryEvent
from codontrace.errors import ConfigurationError
from codontrace.genesis.canonical import canonical_digest
from codontrace.life_loop import PopulationRecord, PopulationRegistry

REPO_ROOT = Path(__file__).resolve().parents[1]
LIFE_LOOP_DIR = REPO_ROOT / "src" / "codontrace" / "life_loop"


def _real_config_digest() -> str:
    return canonical_digest({"phase": 2, "fixture": "life_loop_populations"}, prefix="cfg")


def test_two_named_populations_coexist_and_census() -> None:
    reg = PopulationRegistry()
    reg = reg.create_population("pop_a", member_ids=("a1", "a2"))
    reg = reg.create_population("pop_b", member_ids=("b1",))
    assert reg.list_population_ids() == ("pop_a", "pop_b")
    assert reg.census("pop_a") == 2
    assert reg.census("pop_b") == 1
    assert reg.coexistence("pop_a", "pop_b") is True
    assert reg.membership_of("a1") == "pop_a"
    assert reg.membership_of("b1") == "pop_b"
    assert reg.membership_of("missing") is None


def test_empty_and_coexistence_predicates() -> None:
    reg = (
        PopulationRegistry()
        .create_population("alpha")
        .create_population("beta", member_ids=("x",))
    )
    assert reg.is_empty("alpha") is True
    assert reg.is_empty("beta") is False
    assert reg.coexistence("alpha", "beta") is False
    reg2, _ = reg.add_member("alpha", "y")
    assert reg2.coexistence("alpha", "beta") is True


def test_missing_population_raises_on_census_predicates() -> None:
    reg = PopulationRegistry().create_population("only")
    with pytest.raises(ConfigurationError, match="unknown population_id"):
        reg.census("ghost")
    with pytest.raises(ConfigurationError, match="unknown population_id"):
        reg.is_empty("ghost")
    with pytest.raises(ConfigurationError, match="unknown population_id"):
        reg.coexistence("only", "ghost")


def test_add_remove_emit_population_registry_events() -> None:
    reg = PopulationRegistry(tick=3).create_population("pop_a")
    reg, ev_add = reg.add_member("pop_a", "ind_1")
    assert isinstance(ev_add, PopulationRegistryEvent)
    assert ev_add.action == "add"
    assert ev_add.count_after == 1
    assert ev_add.tick == 3
    assert ev_add.digest == PopulationRegistryEvent.from_dict(ev_add.to_dict()).digest

    reg, ev_rm = reg.remove_member("pop_a", "ind_1")
    assert ev_rm.action == "remove"
    assert ev_rm.count_after == 0
    assert reg.is_empty("pop_a") is True


def test_registry_round_trip_and_digest_mismatch_refuse() -> None:
    reg = (
        PopulationRegistry(tick=1)
        .create_population("p1", member_ids=("m2", "m1"), schedule_partition="part_x")
        .create_population("p0", member_ids=("z",))
    )
    payload = reg.to_dict()
    restored = PopulationRegistry.from_dict(payload)
    assert restored.digest == reg.digest
    assert restored.to_dict() == payload

    bad = dict(payload)
    bad["digest"] = "0" * 64
    with pytest.raises(ConfigurationError, match="digest mismatch"):
        PopulationRegistry.from_dict(bad)


def test_digest_canonical_order_and_sensitivity() -> None:
    a = PopulationRegistry().create_population("z", member_ids=("b", "a"))
    b = PopulationRegistry().create_population("z", member_ids=("a", "b"))
    assert a.digest == b.digest

    c = a.create_population("y")
    assert c.digest != a.digest

    d = a.advance_tick(5)
    assert d.digest != a.digest
    assert d.tick == 5

    e = PopulationRegistry().create_population(
        "z", member_ids=("a", "b"), schedule_partition="slot_1"
    )
    assert e.digest != a.digest


def test_duplicate_membership_refused() -> None:
    reg = PopulationRegistry().create_population("p1", member_ids=("x",))
    reg = reg.create_population("p2")
    with pytest.raises(ConfigurationError, match="already in population"):
        reg.add_member("p2", "x")
    with pytest.raises(ConfigurationError, match="already in population"):
        PopulationRegistry(
            populations=(
                PopulationRecord(population_id="p1", member_ids=("x",)),
                PopulationRecord(population_id="p2", member_ids=("x",)),
            )
        )


def test_advance_tick_no_decrease_and_no_organism_step_api() -> None:
    reg = PopulationRegistry(tick=2).create_population("p")
    advanced = reg.advance_tick(4)
    assert advanced.tick == 4
    assert advanced.populations == reg.populations
    with pytest.raises(ConfigurationError, match="must not decrease"):
        reg.advance_tick(1)
    assert not hasattr(PopulationRegistry, "step")
    assert not hasattr(PopulationRegistry, "run")


def test_world_digest_extras_include_registry_digest() -> None:
    cfg = _real_config_digest()
    reg = (
        PopulationRegistry(tick=0)
        .create_population("pop_a", member_ids=("a",))
        .create_population("pop_b", member_ids=("b",))
    )
    d1 = world_digest(7, cfg, extras={"population_registry_digest": reg.digest})
    d2 = world_digest(7, cfg, extras={"population_registry_digest": reg.digest})
    assert d1 == d2
    reg2, _ = reg.add_member("pop_a", "a2")
    d3 = world_digest(7, cfg, extras={"population_registry_digest": reg2.digest})
    assert d3 != d1
    d4 = world_digest(8, cfg, extras={"population_registry_digest": reg.digest})
    assert d4 != d1


def test_runtime_banned_fragments_refused_in_ids() -> None:
    # Use a joined fragment so this test file does not embed contiguous banned words
    # beyond what the contracts package already defines as the token set.
    sample = next(iter(BANNED_DOMAIN_TOKENS))
    with pytest.raises(ConfigurationError, match="banned fragment"):
        PopulationRegistry().create_population(f"ok_{sample}_x")
    with pytest.raises(ConfigurationError, match="banned fragment"):
        PopulationRegistry().create_population(
            "clean_pop", schedule_partition=f"tag_{sample}"
        )
    reg = PopulationRegistry().create_population("clean_pop")
    with pytest.raises(ConfigurationError, match="banned fragment"):
        reg.add_member("clean_pop", f"ind_{sample}")


def test_banned_tokens_absent_from_life_loop_sources() -> None:
    offenders: list[str] = []
    for path in sorted(LIFE_LOOP_DIR.rglob("*.py")):
        text = path.read_text(encoding="utf-8").casefold()
        for token in BANNED_DOMAIN_TOKENS:
            if token.casefold() in text:
                offenders.append(f"{path.name}:{token}")
    assert offenders == []


def test_no_host_parasite_or_claimgate_imports_in_life_loop() -> None:
    forbidden_substrings = (
        "host_parasite",
        "claimgate",
        "claim_gate",
    )
    for path in sorted(LIFE_LOOP_DIR.rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    lowered = alias.name.casefold()
                    for frag in forbidden_substrings:
                        assert frag not in lowered, f"{path.name} imports {alias.name}"
            elif isinstance(node, ast.ImportFrom) and node.module:
                lowered = node.module.casefold()
                for frag in forbidden_substrings:
                    assert frag not in lowered, f"{path.name} imports {node.module}"


def test_phase2_tests_do_not_import_discipline_modules() -> None:
    """AST-scan this test module for forbidden import modules (not string mentions)."""

    tree = ast.parse(Path(__file__).read_text(encoding="utf-8"), filename=__file__)
    forbidden_parts = (("host", "_para", "site"), ("claim", "gate"))
    forbidden = tuple("".join(parts) for parts in forbidden_parts)
    for node in ast.walk(tree):
        modules: list[str] = []
        if isinstance(node, ast.Import):
            modules.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            modules.append(node.module)
        for mod in modules:
            lowered = mod.casefold()
            for frag in forbidden:
                assert frag not in lowered, f"test imports {mod}"


def test_two_populations_advance_under_one_seeded_tick_snapshot() -> None:
    """Deterministic co-advance of registry tick without a second engine loop."""

    seed = 42
    cfg = _real_config_digest()
    reg = PopulationRegistry(tick=0)
    reg = reg.create_population("pop_a", member_ids=("a1",))
    reg = reg.create_population("pop_b", member_ids=("b1", "b2"))
    # One seeded tick: bump tick metadata only; both pops remain on same spine.
    reg = reg.advance_tick(1)
    assert reg.tick == 1
    assert reg.coexistence("pop_a", "pop_b") is True
    pin = world_digest(
        seed, cfg, extras={"population_registry_digest": reg.digest, "tick": reg.tick}
    )
    # Rebuild identically → same pin (deterministic).
    again = (
        PopulationRegistry(tick=0)
        .create_population("pop_a", member_ids=("a1",))
        .create_population("pop_b", member_ids=("b1", "b2"))
        .advance_tick(1)
    )
    assert again.digest == reg.digest
    pin2 = world_digest(
        seed,
        cfg,
        extras={"population_registry_digest": again.digest, "tick": again.tick},
    )
    assert pin == pin2
