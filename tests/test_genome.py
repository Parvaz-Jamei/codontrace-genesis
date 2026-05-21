from __future__ import annotations

import pytest

from codontrace import RNGManager, SemanticGenome


def test_genome_validation_and_pretty() -> None:
    genome = SemanticGenome.from_codons(["000", "101"])
    assert genome.to_codons() == ("000", "101")
    assert genome.to_compact() == "000101"
    assert genome.pretty() == "000 | 101"


@pytest.mark.parametrize("codon", ["", "01", "0101", "02A"])
def test_genome_rejects_invalid_codons(codon: str) -> None:
    with pytest.raises(ValueError):
        SemanticGenome.from_codons([codon])


def test_genome_random_is_seeded_by_rng_manager() -> None:
    first = SemanticGenome.random(length=5, rng=RNGManager(seed=7).fork("g"))
    second = SemanticGenome.random(length=5, rng=RNGManager(seed=7).fork("g"))
    assert first == second
