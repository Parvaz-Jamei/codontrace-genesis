from __future__ import annotations

import codontrace
from codontrace._version import package_version


def test_import_and_version() -> None:
    assert codontrace.__version__ == package_version()
    assert codontrace.SemanticGenome is codontrace.Genome
    assert codontrace.WhiteBoxAgent is codontrace.Agent
    assert codontrace.ATPAccount is codontrace.ATPBudget
