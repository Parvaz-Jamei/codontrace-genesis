from __future__ import annotations

import codontrace


def test_import_and_version() -> None:
    assert codontrace.__version__ in {"0.3.0b4", "0.3.0b4.dev0", "0.3.0b4.dev1"}
    assert codontrace.SemanticGenome is codontrace.Genome
    assert codontrace.WhiteBoxAgent is codontrace.Agent
    assert codontrace.ATPAccount is codontrace.ATPBudget
