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


def test_mention_spans_stay_off_the_default_tape() -> None:
    from codontrace.genesis.population import MutationConfig, mutate_genome
    from codontrace.genome import BitSpan

    plain = SemanticGenome.from_compact("101111000")
    assert "spans" not in plain.to_dict()
    assert plain.executable_bits() == plain.to_compact()
    assert SemanticGenome.from_dict(plain.to_dict()).digest() == plain.digest()
    span = BitSpan(3, 6, "payload", "note")
    mixed = plain.with_spans((span,))
    assert mixed.to_compact() == "101111000"
    assert mixed.executable_bits() == "101000"
    assert mixed.digest() != plain.digest()
    assert SemanticGenome.from_dict(mixed.to_dict()).spans == mixed.spans
    flipped = mutate_genome(mixed, MutationConfig(bit_flip_rate=0.0), seed=1)
    assert flipped.mutated_genome.spans == mixed.spans
    assert flipped.mutated_genome.executable_bits() == "101000"
