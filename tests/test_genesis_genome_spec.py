from __future__ import annotations

import pytest

from codontrace import GenomeSpec, SemanticGenome
from codontrace.errors import ConfigurationError


def test_genome_spec_factories_and_digest() -> None:
    dna = GenomeSpec.dna3()
    genome = SemanticGenome.from_codons(("ACG", "TTA"), spec=dna)
    assert genome.to_compact() == "ACGTTA"
    assert SemanticGenome.from_dict(genome.to_dict()).digest() == genome.digest()
    assert SemanticGenome.from_compact("000111").spec == GenomeSpec.binary3()
    assert (
        SemanticGenome.from_compact("000111").digest()
        != SemanticGenome.from_compact("000111", spec=GenomeSpec.binary3()).digest()
        or SemanticGenome.from_compact("000111").digest()
    )
    with pytest.raises(ConfigurationError):
        SemanticGenome.from_codons(("000",), spec=dna)


def test_binary4_and_ternary2_work() -> None:
    assert SemanticGenome.from_codons(("0000",), spec=GenomeSpec.binary4()).to_compact() == "0000"
    assert (
        SemanticGenome.from_codons(("12", "22"), spec=GenomeSpec.ternary2()).to_compact() == "1222"
    )
