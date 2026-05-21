from __future__ import annotations

from codontrace import CodonTable, ElementKind, SemanticGenome, SimulationConfig, World2D
from codontrace.genesis import ElementGrid


def test_old_defaults_remain_usable() -> None:
    assert SemanticGenome.from_compact("000111").to_codons() == ("000", "111")
    assert CodonTable.genesis_v0().decode("111").action_name == "COPY_SELF"
    assert ElementGrid(1, 1).amount((0, 0), ElementKind.AETHER) == 1.0
    assert World2D(2, 1, boundary="wrap").move_agent((0, 0), (-1, 0))[0] == (1, 0)
    assert SimulationConfig(steps=1, scheduler="round_robin").scheduler == "round_robin"
