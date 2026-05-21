from __future__ import annotations

import pytest

from codontrace.genesis import MutationConfig, mutate_genome
from codontrace.genome import SemanticGenome
from codontrace.rng import RNGManager


def test_mutation_fixed_seed_is_deterministic() -> None:
    genome = SemanticGenome.from_compact("000001010011")
    config = MutationConfig(bit_flip_rate=0.5, insertion_rate=0.2, deletion_rate=0.2)

    left = mutate_genome(genome, config, seed=11)
    right = mutate_genome(genome, config, seed=11)

    assert left.mutated_genome.to_compact() == right.mutated_genome.to_compact()
    assert left.digest() == right.digest()


def test_mutation_different_seed_can_change_output() -> None:
    genome = SemanticGenome.from_compact("000001010011100101")
    config = MutationConfig(bit_flip_rate=0.5)

    baseline = mutate_genome(genome, config, seed=1).mutated_genome.to_compact()
    variants = {
        mutate_genome(genome, config, seed=seed).mutated_genome.to_compact() for seed in range(2, 8)
    }

    assert any(item != baseline for item in variants)


def test_mutation_never_creates_non_binary_and_respects_max_bits() -> None:
    genome = SemanticGenome.from_compact("000001010011")
    config = MutationConfig(bit_flip_rate=1.0, insertion_rate=1.0, max_genome_bits=9)

    result = mutate_genome(genome, config, seed=7)

    assert set(result.mutated_genome.to_compact()) <= {"0", "1"}
    assert len(result.mutated_genome.to_compact()) <= 9
    assert len(result.mutated_genome.to_compact()) % 3 == 0


def test_mutation_does_not_mutate_original_genome() -> None:
    genome = SemanticGenome.from_compact("000001010")
    before = genome.to_compact()

    mutate_genome(genome, MutationConfig(bit_flip_rate=1.0), seed=3)

    assert genome.to_compact() == before


def test_mutation_rejects_seed_and_rng_together() -> None:
    genome = SemanticGenome.from_compact("000001010")

    with pytest.raises(ValueError, match="either seed or rng"):
        mutate_genome(genome, MutationConfig(bit_flip_rate=0.0), seed=1, rng=RNGManager(seed=2))
