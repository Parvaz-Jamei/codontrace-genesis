"""Closed-loop P1 accept: one clock, both roles as GenesisOrganism, dual path hard-raise."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from codontrace.errors import ConfigurationError
from codontrace.genesis.closed_loop_p1 import ClosedLoopP1Session, replay_bit_identical
from codontrace.genesis.host_parasite_genesis_path import (
    HostParasiteGenesisPath,
    orchestrate_hp_tick,
)
from codontrace.genesis.host_parasite_life_plugin import role_of
from codontrace.genesis.host_parasite_world import HostParasiteProfile, HostParasiteWorld

REPO = Path(__file__).resolve().parents[2]


def _profile(**overrides: object) -> HostParasiteProfile:
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
    orgs = session.runner.population.organisms
    assert len(orgs) >= 4
    for org in orgs:
        assert role_of(org.id) in {"primary", "secondary"}
        assert org.atp_state is not None
        assert org.atp_state.runtime.current_atp > 0


def test_p1_secondary_genome_mutates_under_one_engine_tick_index() -> None:
    session = ClosedLoopP1Session.boot(seed=5)
    before = session.secondary_genome_digests()
    session.run_ticks(2)
    after = session.secondary_genome_digests()
    assert before.keys() == after.keys()
    assert before != after, "secondary must mutate under closed_loop_hp_life hook"


def test_p1_bit_identical_replay() -> None:
    a, b = replay_bit_identical(seed=19, ticks=3)
    assert a == b


def test_p1_dual_path_hard_raises() -> None:
    world = HostParasiteWorld(_profile(seed=9))
    path = HostParasiteGenesisPath(world=world)
    with pytest.raises(ConfigurationError, match="dual HostParasiteGenesisPath"):
        path.tick()
    with pytest.raises(ConfigurationError, match="deprecated_dual_path fails closed"):
        path.tick(deprecated_dual_path=True)
    with pytest.raises(ConfigurationError):
        orchestrate_hp_tick(world)


def test_p1_accept_call_graph_has_no_world_demography_helpers() -> None:
    """Anti-cheat: closed_loop_p1 must not invoke HP world demography authority."""

    src = (REPO / "src/codontrace/genesis/closed_loop_p1.py").read_text(encoding="utf-8")
    tree = ast.parse(src)
    assert "HostParasiteWorld" not in src
    for banned in ("_birth_role", "_death_role", "HostParasiteGenesisPath"):
        assert banned not in src, f"banned demography symbol present: {banned}"
    # Attribute calls named tick / _birth_role / _death_role on any receiver
    # (docstrings mentioning "world.tick" are fine; executable calls are not).
    call_hits: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            if node.func.attr in {"tick", "_birth_role", "_death_role"}:
                call_hits.append(node.func.attr)
    assert not call_hits, f"banned demography calls in closed_loop_p1: {call_hits}"


def test_p1_engine_py_stays_domain_free() -> None:
    engine_src = (REPO / "src/codontrace/engine.py").read_text(encoding="utf-8")
    lowered = engine_src.casefold()
    assert "hostparasiteenv" not in lowered
    assert "steal_fraction" not in engine_src
    assert "closed_loop_hp_life" not in engine_src
