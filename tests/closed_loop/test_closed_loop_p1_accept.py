"""Closed-loop P1 accept: unify+mutate scaffold under step_population (hard-scoped)."""

from __future__ import annotations

import ast
from pathlib import Path
from unittest.mock import patch

import pytest

from codontrace.errors import ConfigurationError
from codontrace.genesis.closed_loop_p1 import ClosedLoopP1Session, replay_bit_identical
from codontrace.genesis.host_parasite_genesis_path import (
    HostParasiteGenesisPath,
    orchestrate_hp_tick,
)
from codontrace.genesis.host_parasite_life_plugin import P1_SCOPE, role_of
from codontrace.genesis.host_parasite_world import HostParasiteProfile, HostParasiteWorld

REPO = Path(__file__).resolve().parents[2]


def _minimal_profile(**overrides: object) -> HostParasiteProfile:
    body: dict[str, object] = {
        "profile_id": "hp_p1_reject",
        "seed": 11,
        "slot_capacity": 2,
        "coupling_amount": 0.5,
        "coupling_loss_fraction": 0.0,
        "match_rule_id": "always",
        "contact_probability": 1.0,
        "inherit_mode": "copy",
        "inherit_probability": 1.0,
        "primary_members": ("a0",),
        "secondary_members": ("b0",),
        "initial_energy": 20.0,
        "max_population_primary": 8,
        "max_population_secondary": 8,
    }
    body.update(overrides)
    return HostParasiteProfile(**body)  # type: ignore[arg-type]


def test_p1_both_roles_are_genesis_organisms_with_atp_state() -> None:
    session = ClosedLoopP1Session.boot(seed=3)
    role_map = session.runner.configs.closed_loop_hp_life.role_map()
    orgs = session.runner.population.organisms
    assert len(orgs) >= 4
    for org in orgs:
        assert role_of(org.id, role_map) in {"primary", "secondary"}
        assert org.atp_state is not None
        assert org.atp_state.runtime.current_atp > 0


def test_p1_secondary_mutates_via_engine_mutate_genome_path() -> None:
    session = ClosedLoopP1Session.boot(seed=5, bit_flip_rate=0.5)
    before = session.secondary_genome_digests()
    session.run_ticks(3)
    after = session.secondary_genome_digests()
    assert before.keys() == after.keys()
    assert before != after, "secondary must change via mutate_genome under live stream"


def test_p1_atp_moves_under_basal_metabolism() -> None:
    session = ClosedLoopP1Session.boot(seed=5, basal_atp_cost=1.0, initial_atp=12.0)
    session.run_ticks(2)
    summary = session.summary()
    assert summary["atp_moved"] is True
    assert summary["mean_runtime_atp"] < 12.0
    assert summary["p1_scope"] == P1_SCOPE
    assert "one_clock" not in summary
    assert "dual_path_used" not in summary


def test_p1_same_seed_replay_bit_identical() -> None:
    """Gate7-shaped same-seed match — not P4 dual-arm elicit/ablate."""

    a, b = replay_bit_identical(seed=19, ticks=3)
    assert a == b


def test_p1_dual_path_hard_raises() -> None:
    world = HostParasiteWorld(_minimal_profile(seed=9))
    path = HostParasiteGenesisPath(world=world)
    with pytest.raises(ConfigurationError, match="dual HostParasiteGenesisPath"):
        path.tick()
    with pytest.raises(ConfigurationError, match="deprecated_dual_path fails closed"):
        path.tick(deprecated_dual_path=True)
    with pytest.raises(ConfigurationError):
        orchestrate_hp_tick(world)


def test_p1_runtime_anti_cheat_world_tick_not_called() -> None:
    """Runtime witness: HostParasiteWorld.tick must not run during P1 accept."""

    session = ClosedLoopP1Session.boot(seed=8)
    with patch.object(HostParasiteWorld, "tick", autospec=True) as spy:
        session.run_ticks(2)
        assert spy.call_count == 0
        assert session.hp_world_tick_calls == 0
    for org in session.runner.population.organisms:
        assert not hasattr(org, "accounts")


def test_p1_role_is_opaque_map_not_id_prefix() -> None:
    session = ClosedLoopP1Session.boot(seed=2)
    role_map = session.runner.configs.closed_loop_hp_life.role_map()
    assert role_of("org_a0") is None
    assert role_of("org_a0", role_map) == "primary"
    assert role_of("org_b0", role_map) == "secondary"


def test_p1_accept_no_world_demography_calls_in_session_ast() -> None:
    src = (REPO / "src/codontrace/genesis/closed_loop_p1.py").read_text(encoding="utf-8")
    tree = ast.parse(src)
    # Imports of HP world/path are banned; docstring mentions of the retired path are fine.
    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            mod = getattr(node, "module", "") or ""
            names = [a.name for a in getattr(node, "names", [])]
            blob = mod + " " + " ".join(names)
            assert "HostParasiteWorld" not in blob
            assert "host_parasite_world" not in blob
            assert "HostParasiteGenesisPath" not in blob
            assert "host_parasite_genesis_path" not in blob
    call_hits: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            if node.func.attr in {"tick", "_birth_role", "_death_role"}:
                call_hits.append(node.func.attr)
    assert not call_hits, f"banned demography calls: {call_hits}"
    for banned in ("_birth_role", "_death_role"):
        assert banned not in src


def test_p1_engine_py_stays_domain_free() -> None:
    engine_src = (REPO / "src/codontrace/engine.py").read_text(encoding="utf-8")
    lowered = engine_src.casefold()
    assert "hostparasiteenv" not in lowered
    assert "steal_fraction" not in engine_src
    assert "closed_loop_hp_life" not in engine_src


def test_p1_hook_sits_after_atp_before_nexus_in_source() -> None:
    """Structural cut: apply_closed_loop_hp_life appears after basal debit, before nexus."""

    src = (REPO / "src/codontrace/genesis/population.py").read_text(encoding="utf-8")
    plugin = src.index("Closed-loop P1: post-ATP settle")
    # basal debit site that precedes the plugin in the organism loop
    basal_loop = src.rfind("basal_runtime_atp_cost", 0, plugin)
    nexus = src.index("if working_nexus_layer is not None and stigmergy_enabled:", plugin)
    assert basal_loop < plugin < nexus
