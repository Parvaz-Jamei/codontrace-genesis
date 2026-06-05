from __future__ import annotations

import codontrace


def test_import_and_version() -> None:
    assert codontrace.__version__ == "0.3.0b1"
    assert codontrace.SemanticGenome is codontrace.Genome
    assert codontrace.WhiteBoxAgent is codontrace.Agent
    assert codontrace.ATPAccount is codontrace.ATPBudget
