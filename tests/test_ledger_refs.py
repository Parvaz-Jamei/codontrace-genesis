from __future__ import annotations

from codontrace import ATPAccount, CodonTable, SemanticGenome, Trace, WhiteBoxAgent, World2D


def _agent(agent_id: str, position: tuple[int, int]) -> WhiteBoxAgent:
    return WhiteBoxAgent(
        id=agent_id,
        genome=SemanticGenome.from_codons(["000"]),
        codon_table=CodonTable.default_minimal(),
        atp_account=ATPAccount(5.0),
        position=position,
    )


def test_ledger_entry_refs_disambiguate_multi_agent_local_ids() -> None:
    world = World2D(4, 4)
    trace = Trace()
    first = _agent("agent-a", (0, 0))
    second = _agent("agent-b", (1, 1))

    first_event = first.step(world, trace)
    second_event = second.step(world, trace)

    assert first_event.ledger_entry_ids == (0,)
    assert second_event.ledger_entry_ids == (0,)
    assert first_event.ledger_entry_refs == ("agent-a:0",)
    assert second_event.ledger_entry_refs == ("agent-b:0",)


def test_trace_json_exports_ledger_entry_refs() -> None:
    world = World2D(3, 3)
    trace = Trace()
    event = _agent("agent-a", (0, 0)).step(world, trace)

    payload = event.to_dict()
    assert payload["ledger_entry_ids"] == [0]
    assert payload["ledger_entry_refs"] == ["agent-a:0"]
    assert "ledger_entry_refs" in trace.to_jsonl_string()


def test_trace_import_derives_ledger_refs_for_older_payloads() -> None:
    older_payload = [
        {
            "step": 0,
            "agent_id": "legacy-agent",
            "codon": "000",
            "action": "WAIT",
            "atp_before": 5.0,
            "atp_after": 4.9,
            "position_before": [0, 0],
            "position_after": [0, 0],
            "world_delta": {"action_cost": 0.1},
            "status": "executed",
            "reason": "waited",
            "ledger_entry_ids": [0],
        }
    ]

    restored = Trace.from_list(older_payload)
    assert restored.last().ledger_entry_refs == ("legacy-agent:0",)
