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


def _scenario() -> tuple[WhiteBoxAgent, World2D]:
    world = World2D.from_ascii(
        """
        ....
        .A*.
        ....
        """
    )
    agent = WhiteBoxAgent(
        id="agent-1",
        genome=SemanticGenome.from_codons(["101", "111", "000", "101", "000"]),
        codon_table=CodonTable.default_minimal(),
        atp_account=ATPAccount(5.0),
        position=(1, 1),
    )
    return agent, world


def test_replay_from_snapshot_matches_original_continuation_with_ledger_ids() -> None:
    agent, world = _scenario()
    agent.run(world, steps=2)
    snapshot = ReplaySnapshot.capture(agent, world)

    original = CausalReplay.run_deterministic(agent, world, steps=3)
    replayed = CausalReplay.replay_from_snapshot(snapshot, steps=3)

    assert replayed.trace_digest == original.trace_digest
    assert replayed.world_digest == original.world_digest
    assert replayed.agent_digest == original.agent_digest


def test_replay_from_snapshot_continues_ledger_entry_ids() -> None:
    agent, world = _scenario()
    agent.run(world, steps=2)
    snapshot = ReplaySnapshot.capture(agent, world)
    starting_ledger_length = len(agent.atp_account.ledger)

    replay_world = snapshot.world.clone()
    from codontrace.agent import WhiteBoxAgent

    replay_agent = WhiteBoxAgent(
        id=snapshot.agent_id,
        genome=snapshot.genome,
        codon_table=snapshot.codon_table,
        atp_account=ATPAccount.from_dict(snapshot.atp_state),
        position=snapshot.position,
        action_registry=snapshot.action_registry,
    )
    replay_agent.restore_runtime_state(cursor=snapshot.cursor, step_index=snapshot.step_index)
    event = replay_agent.step(replay_world, trace=__import__("codontrace").Trace())

    assert event.ledger_entry_ids[0] == starting_ledger_length
