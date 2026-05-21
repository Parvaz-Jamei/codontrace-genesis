from __future__ import annotations

from codontrace import Action, CodonTable, default_action_registry
from codontrace.genesis import GenesisCodonTable


def test_genesis_v0_table_has_expected_actions_and_costs() -> None:
    table = CodonTable.genesis_v0()
    expected = {
        "000": (Action.WAIT, 0.1),
        "001": (Action.SENSE_FOOD, 0.4),
        "010": (Action.SENSE_DANGER, 0.4),
        "011": (Action.MOVE_TOWARD, 1.2),
        "100": (Action.MOVE_AWAY, 1.5),
        "101": (Action.EAT_LUMEN, 0.8),
        "110": (Action.EMIT_NEXUS, 0.5),
        "111": (Action.COPY_SELF, 8.0),
    }
    for bits, (action, cost) in expected.items():
        codon = table.decode(bits)
        assert codon.action == action
        assert codon.cost == cost
    assert GenesisCodonTable.default_v0().decode("111").action == Action.COPY_SELF


def test_default_minimal_table_is_preserved() -> None:
    assert CodonTable.default_minimal().decode("111").action == Action.COLLECT_RESOURCE


def test_default_registry_includes_genesis_actions() -> None:
    names = set(default_action_registry().names())
    assert {
        "SENSE_FOOD",
        "MOVE_TOWARD",
        "MOVE_AWAY",
        "EAT_LUMEN",
        "EMIT_NEXUS",
        "COPY_SELF",
    } <= names
