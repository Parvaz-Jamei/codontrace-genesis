from __future__ import annotations

from codontrace import (
    ATPAccount,
    CausalReplay,
    CodonTable,
    ReplaySnapshot,
    SemanticGenome,
    WhiteBoxAgent,
    World2D,
)


def make_scenario() -> tuple[WhiteBoxAgent, World2D]:
    world = World2D.from_ascii("""
....
.A*.
....
""")
    agent = WhiteBoxAgent(
        id="agent-1",
        genome=SemanticGenome.from_codons(["101", "111", "000"]),
        codon_table=CodonTable.default_minimal(),
        atp_account=ATPAccount(5.0),
        position=(1, 1),
    )
    return agent, world


def test_replay_hash_gate_same_seeded_scenario_matches() -> None:
    agent_a, world_a = make_scenario()
    agent_b, world_b = make_scenario()
    original = CausalReplay.run_deterministic(agent_a, world_a, steps=3)
    replay = CausalReplay.run_deterministic(agent_b, world_b, steps=3)
    assert original.trace_digest == replay.trace_digest
    assert original.world_digest == replay.world_digest
    assert original.agent_digest == replay.agent_digest


def test_replay_from_snapshot_is_stable_and_does_not_mutate_snapshot() -> None:
    agent, world = make_scenario()
    snapshot = ReplaySnapshot.capture(agent, world)
    original = CausalReplay.replay_from_snapshot(snapshot, steps=3)
    replayed = CausalReplay.replay_from_snapshot(snapshot, steps=3)
    assert original.trace_digest == replayed.trace_digest
    assert original.world_digest == replayed.world_digest
    assert original.agent_digest == replayed.agent_digest
    assert snapshot.world.render_ascii() == world.render_ascii()
    assert snapshot.world_digest() == world.digest()


def test_replay_snapshot_preserves_atp_ledger_digest_for_audit() -> None:
    agent, world = make_scenario()
    agent.run(world, steps=2)
    snapshot = ReplaySnapshot.capture(agent, world)
    assert snapshot.atp_snapshot["ledger_digest"] == agent.atp_account.ledger_digest()
    assert snapshot.ledger_digest() == agent.atp_account.ledger_digest()
