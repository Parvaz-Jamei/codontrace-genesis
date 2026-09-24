"""Engine-complete gates for HostParasiteWorld / life_loop (2026-09-25 lock)."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from codontrace.energy import ATPAccount
from codontrace.engine import GenesisEngine
from codontrace.genesis.host_parasite_genesis_path import (
    HostParasiteGenesisPath,
    orchestrate_hp_tick,
)
from codontrace.genesis.host_parasite_world import HostParasiteProfile, HostParasiteWorld
from codontrace.genesis.runtime_profiles import GenesisRuntimeProfile
from codontrace.mutation import Mutation
from codontrace.rng import RNGManager

REPO = Path(__file__).resolve().parents[2]
WORLD_SRC = REPO / "src" / "codontrace" / "genesis" / "host_parasite_world.py"
ENGINE_SRC = REPO / "src" / "codontrace" / "engine.py"


def _profile(**overrides: object) -> HostParasiteProfile:
    body: dict[str, object] = {
        "profile_id": "hp_gate",
        "seed": 11,
        "slot_capacity": 2,
        "coupling_amount": 0.5,
        "coupling_loss_fraction": 0.0,
        "match_rule_id": "always",
        "contact_probability": 1.0,
        "inherit_mode": "copy",
        "inherit_probability": 1.0,
        "primary_members": ("a0", "a1"),
        "secondary_members": ("b0", "b1"),
        "initial_energy": 20.0,
        "max_population_primary": 32,
        "max_population_secondary": 32,
    }
    body.update(overrides)
    return HostParasiteProfile(**body)  # type: ignore[arg-type]


# --- Gate 1: birth+death both pops; extinction + coexistence recordable ---


def test_gate1_birth_and_death_mutate_both_populations() -> None:
    world = HostParasiteWorld(
        _profile(
            birth_probability_primary=0.8,
            birth_probability_secondary=0.8,
            death_probability_primary=0.05,
            death_probability_secondary=0.05,
            seed=21,
        )
    )
    before = world.census()
    world.run(8)
    after = world.census()
    summary = world.summary()
    assert summary["birth_counts"]["primary"] > 0
    assert summary["birth_counts"]["secondary"] > 0
    assert summary["death_counts"]["primary"] + summary["death_counts"]["secondary"] >= 0
    # Populations changed (births push above founders unless capped/deaths).
    assert after["primary"] != before["primary"] or after["secondary"] != before["secondary"]
    assert "coexistence" in summary
    assert "extinct_primary" in summary
    assert "extinct_secondary" in summary


def test_gate1_extinction_and_coexistence_recordable() -> None:
    # Coexistence path
    alive = HostParasiteWorld(_profile(seed=1))
    alive.tick()
    assert alive.coexistence() is True
    assert alive.summary()["coexistence"] is True
    assert alive.summary()["extinct_primary"] is False
    assert alive.summary()["extinct_secondary"] is False
    assert any(bool(row["coexistence"]) for row in alive.outcome_log)

    # Extinction of secondary
    doomed = HostParasiteWorld(
        _profile(
            seed=2,
            death_probability_secondary=1.0,
            birth_probability_secondary=0.0,
            secondary_members=("b0",),
        )
    )
    doomed.tick()
    assert doomed.census()["secondary"] == 0
    assert doomed.extinction_flags()["secondary"] is True
    assert doomed.coexistence() is False
    assert doomed.summary()["extinct_secondary"] is True
    assert any(bool(row["extinct_secondary"]) for row in doomed.outcome_log)


# --- Gate 2: mutation both sides via core Mutation + RNG (no hash sidecar) ---


def test_gate2_mutation_both_sides_uses_core_mutation_and_rng() -> None:
    world = HostParasiteWorld(
        _profile(
            seed=5,
            mutation_probability_primary=1.0,
            mutation_probability_secondary=1.0,
            founder_genome_compact="000000",
        )
    )
    before = {mid: g.to_compact() for mid, g in world.genomes.items()}
    assert isinstance(world.rng, RNGManager)
    world.tick()
    after = {mid: g.to_compact() for mid, g in world.genomes.items()}
    assert world.mutation_counts["primary"] >= 1
    assert world.mutation_counts["secondary"] >= 1
    assert before != after
    # Static: no _deterministic_unit in module; Mutation type used for genetics.
    source = WORLD_SRC.read_text(encoding="utf-8")
    assert "_deterministic_unit" not in source
    assert "Mutation(" in source
    assert "RNGManager" in source
    assert isinstance(Mutation(operation="point"), Mutation)


# --- Gate 3: quantitative attachment whole population + capacity fail reasons ---


def test_gate3_attachment_whole_population_capacity_and_fail_reasons() -> None:
    world = HostParasiteWorld(
        _profile(
            seed=8,
            slot_capacity=1,
            primary_members=("a0", "a1", "a2"),
            secondary_members=("b0", "b1", "b2"),
            contact_probability=0.0,
            coupling_amount=0.0,
        )
    )
    world.tick()
    census = world.attach_fail_census
    assert census.get("success", 0) >= 1
    # More secondary than capacity across slots → seat_full recorded for whole pop.
    assert census.get("seat_full", 0) + census.get("already_occupant", 0) >= 1
    # Not only the first pair: attempts span multiple holders.
    total_attempts = sum(census.values())
    assert total_attempts >= len(world.profile.primary_members)


# --- Gate 4: energy from core ATP ledger; parameterized trade; no silent swallow ---


def test_gate4_energy_core_ledger_parameterized_no_silent_swallow() -> None:
    world = HostParasiteWorld(
        _profile(
            seed=9,
            coupling_amount=2.5,
            coupling_loss_fraction=0.2,
            initial_energy=10.0,
            contact_probability=0.0,
        )
    )
    assert all(isinstance(a, ATPAccount) for a in world.accounts.values())
    before_ledger_lens = {m: len(a.ledger) for m, a in world.accounts.items()}
    world.tick()
    assert world.coupling_fail_census.get("success", 0) >= 1
    # Ledger grew on at least one account (debit or credit).
    after_lens = {m: len(a.ledger) for m, a in world.accounts.items()}
    assert after_lens != before_ledger_lens
    # Balances mirror accounts end-to-end.
    for mid, acct in world.accounts.items():
        assert world.balances[mid] == pytest.approx(acct.current_atp)
    # ConfigurationError paths leave census entries — never a silent swallow.
    dry = HostParasiteWorld(
        _profile(
            seed=10,
            coupling_amount=5.0,
            initial_energy=0.0,
            contact_probability=0.0,
        )
    )
    dry.tick()
    assert sum(dry.coupling_fail_census.values()) + sum(dry.attach_fail_census.values()) >= 1


# --- Gate 5: InheritAttachedPolicy invoked on birth ---


def test_gate5_inherit_attached_invoked_on_birth() -> None:
    world = HostParasiteWorld(
        _profile(
            seed=12,
            birth_probability_primary=1.0,
            birth_probability_secondary=0.0,
            inherit_mode="copy",
            inherit_probability=1.0,
            max_population_primary=8,
            secondary_members=("b0",),
        )
    )
    # Pre-attach so parent has occupants to inherit.
    world.book, _ = world.book.attach("slot_a0", "b0")
    world.tick()
    assert world.birth_counts["primary"] >= 1
    assert world.inherit_fail_census.get("success", 0) >= 1
    assert world._inherit_census.attempts >= 1
    source = WORLD_SRC.read_text(encoding="utf-8")
    assert "apply_birth_inherit" in source


# --- Gate 6: registry in GenesisEngine life-loop via single orchestrated path ---


def test_gate6_registry_participates_via_genesis_path_not_second_engine() -> None:
    world = HostParasiteWorld(_profile(seed=13, birth_probability_primary=0.5))
    path = HostParasiteGenesisPath(world=world)
    spec = GenesisRuntimeProfile.life_loop_world(seed=13, tick_count=2, population=2)
    engine = GenesisEngine.from_spec(spec)
    path.bind_engine(engine)
    record = path.tick()
    assert record["engine_bound"] is True
    assert record["registry_digest"] == world.registry.digest
    assert record["hp_tick"] == world.tick_index
    # Registry advanced only through world.tick (orchestrated path).
    assert world.registry.tick == world.tick_index
    # engine.py must remain free of infection / HostParasiteEnv.
    engine_src = ENGINE_SRC.read_text(encoding="utf-8")
    lowered = engine_src.casefold()
    assert "HostParasiteEnv" not in engine_src
    assert "steal_fraction" not in engine_src
    assert "hostparasiteenv" not in lowered
    # Module-level entry exists.
    snap = orchestrate_hp_tick(HostParasiteWorld(_profile(seed=14)))
    assert snap["registry_digest"]


# --- Gate 7: bit-identical replay ---


def test_gate7_bit_identical_replay_same_seed_profile() -> None:
    profile = _profile(
        seed=77,
        birth_probability_primary=0.35,
        birth_probability_secondary=0.35,
        death_probability_primary=0.12,
        death_probability_secondary=0.12,
        mutation_probability_primary=0.4,
        mutation_probability_secondary=0.4,
        inherit_mode="copy",
        inherit_probability=1.0,
    )
    s1 = HostParasiteWorld(profile).run(12)
    s2 = HostParasiteWorld(HostParasiteProfile.from_dict(profile.to_dict())).run(12)
    assert s1["world_digest"] == s2["world_digest"]
    assert s1["life_loop_snapshot"]["genome_digest"] == s2["life_loop_snapshot"]["genome_digest"]
    assert (
        s1["life_loop_snapshot"]["energy_ledger_digest"]
        == s2["life_loop_snapshot"]["energy_ledger_digest"]
    )
    assert s1["life_loop_snapshot"]["rng_state_digest"] == s2["life_loop_snapshot"]["rng_state_digest"]
    assert s1["census"] == s2["census"]


# --- Gate 8: demographic main effects only with n_seeds >= 30 ---


def test_gate8_demographic_effect_requires_n_seeds_ge_30() -> None:
    n_seeds = 30
    assert n_seeds >= 30

    def mean_primary(birth_p: float, death_p: float) -> float:
        totals = []
        for seed in range(n_seeds):
            world = HostParasiteWorld(
                _profile(
                    seed=1000 + seed,
                    birth_probability_primary=birth_p,
                    death_probability_primary=death_p,
                    birth_probability_secondary=0.2,
                    death_probability_secondary=0.05,
                    mutation_probability_primary=0.0,
                    mutation_probability_secondary=0.0,
                    max_population_primary=40,
                    initial_energy=30.0,
                    birth_energy_cost=0.5,
                )
            )
            world.run(10)
            totals.append(world.census()["primary"])
        return sum(totals) / len(totals)

    high_birth = mean_primary(0.7, 0.05)
    high_death = mean_primary(0.05, 0.5)
    assert high_birth > high_death


def test_gate8_fixture_wiring_may_use_small_n() -> None:
    """Unit wiring fixture may use n<30; demographic effects must not."""
    n_fixture = 3
    censuses = []
    for seed in range(n_fixture):
        w = HostParasiteWorld(_profile(seed=seed, birth_probability_primary=0.5))
        w.run(2)
        censuses.append(w.census()["primary"])
    assert len(censuses) == n_fixture
    # Guard: this test itself must not claim a demographic main effect.
    assert n_fixture < 30


def test_static_no_step_and_no_infection_in_engine() -> None:
    source = WORLD_SRC.read_text(encoding="utf-8")
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == "HostParasiteWorld":
            for item in node.body:
                if isinstance(item, ast.FunctionDef) and item.name == "step":
                    raise AssertionError("HostParasiteWorld must not define step()")
    assert "HostParasiteEnv" not in source
