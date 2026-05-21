from __future__ import annotations

import pytest

from codontrace import CodonTable, Mutation, SemanticGenome, World2D


def test_mutation_operations_are_seeded_valid_and_logged() -> None:
    genome = SemanticGenome.from_codons(["000", "101", "111"])
    table = CodonTable.default_minimal()
    for operation in ("point", "insert", "delete", "swap"):
        mutation = getattr(Mutation, operation)(seed=11)
        child = mutation.apply(genome, parent_id="p", generation=1, codon_table=table)
        assert len(child) >= 1
        assert all(table.validate(codon) for codon in child.to_codons())
        assert mutation.last_log
        assert mutation.last_log[0].syntactic_valid is True
        assert mutation.last_log[0].behavioral_valid is True
        assert mutation.last_log[0].to_dict()["operation"] == operation


def test_behavioral_validity_does_not_swallow_unexpected_errors(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def crash(_ascii_map: str) -> World2D:
        raise AssertionError("unexpected test crash")

    monkeypatch.setattr(World2D, "from_ascii", crash)
    genome = SemanticGenome.from_codons(["000"])
    with pytest.raises(AssertionError, match="unexpected test crash"):
        Mutation._is_behaviorally_valid(genome, CodonTable.default_minimal())
