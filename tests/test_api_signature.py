from __future__ import annotations

import inspect

from codontrace import ATPAccount, Mutation, SemanticGenome, WhiteBoxAgent


def test_internal_runtime_fields_are_not_public_constructor_inputs() -> None:
    assert "_cursor" not in str(inspect.signature(WhiteBoxAgent))
    assert "_step_index" not in str(inspect.signature(WhiteBoxAgent))
    assert "_trace" not in str(inspect.signature(WhiteBoxAgent))
    assert "current_atp" not in str(inspect.signature(ATPAccount))
    assert "last_log" not in str(inspect.signature(Mutation))


def test_semantic_genome_does_not_expose_private_constructor_storage() -> None:
    assert "_codons" not in str(inspect.signature(SemanticGenome))
