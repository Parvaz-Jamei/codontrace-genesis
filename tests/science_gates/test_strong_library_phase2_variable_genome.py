import pytest

from codontrace.errors import ConfigurationError
from codontrace.genesis.structural_mutation import (
    GenomeDecodingRemainderPolicy,
    StructuralMutationConfig,
    build_genome_program,
    genome_length_distribution,
    genome_program_from_dict,
    mutate_genome_program,
)
from codontrace.rng import RNGManager


def test_structural_mutation_operates_on_codon_tokens_by_default():
    parent = build_genome_program("000001", codon_width=3)
    child, record = mutate_genome_program(
        parent, StructuralMutationConfig(), RNGManager(seed=7), kind="insert", payload_codon="111"
    )
    assert len(child.bits) % 3 == 0
    assert record.kind == "insert"
    assert record.parent_genome_digest == parent.digest
    assert child.structural_mutation_digest == record.digest


def test_bit_level_mutation_remainder_policy_nonviable_by_default():
    program = build_genome_program("00001", codon_width=3)
    assert program.viable is False
    assert program.nonviable_reason == "codon_remainder"
    with pytest.raises(ConfigurationError):
        build_genome_program(
            "00001", codon_width=3, remainder_policy=GenomeDecodingRemainderPolicy("reject")
        )


def test_variable_genome_structural_mutations_deterministic():
    parent = build_genome_program("000001010", codon_width=3)
    cfg = StructuralMutationConfig(max_codons=10)
    child_a, record_a = mutate_genome_program(
        parent, cfg, RNGManager(seed=22, namespace="m"), kind="duplicate"
    )
    child_b, record_b = mutate_genome_program(
        parent, cfg, RNGManager(seed=22, namespace="m"), kind="duplicate"
    )
    assert child_a.digest == child_b.digest
    assert record_a.digest == record_b.digest


def test_genome_program_digest_factory_import_validation():
    program = build_genome_program("000001", codon_width=3)
    restored = genome_program_from_dict(program.to_dict())
    assert restored.digest == program.digest
    tampered = program.to_dict()
    tampered["digest"] = "bad"
    with pytest.raises(ConfigurationError):
        genome_program_from_dict(tampered)


def test_variable_genome_length_distribution_recorded_and_bloat_guard():
    parent = build_genome_program("000001", codon_width=3)
    cfg = StructuralMutationConfig(max_codons=2, bloat_guard="mdl")
    child, _ = mutate_genome_program(
        parent, cfg, RNGManager(seed=1), kind="insert", payload_codon="111"
    )
    assert len(child.bits) // child.codon_width <= 2
    dist = genome_length_distribution([parent, child])
    assert dist["count"] == 2
