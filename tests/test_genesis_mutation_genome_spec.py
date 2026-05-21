from __future__ import annotations

from codontrace import GenomeSpec, Mutation, SemanticGenome
from codontrace.genesis import MutationConfig, mutate_genome


def test_core_mutation_respects_dna_spec() -> None:
    genome = SemanticGenome.from_codons(("ACG", "TTA"), spec=GenomeSpec.dna3())
    mutated = Mutation.point(seed=1).apply(genome)
    assert mutated.spec == genome.spec
    assert set(mutated.to_compact()) <= set("ACGT")


def test_genesis_mutation_respects_ternary_spec() -> None:
    genome = SemanticGenome.from_codons(("00", "12", "22"), spec=GenomeSpec.ternary2())
    result = mutate_genome(genome, MutationConfig(bit_flip_rate=1.0), seed=2)
    assert result.mutated_genome.spec == genome.spec
    assert set(result.mutated_genome.to_compact()) <= set("012")
