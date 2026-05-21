from __future__ import annotations

import pytest

from codontrace import Codon, CodonTable, CodonTableSpec, GenomeSpec


def test_dna_codon_table_and_incompatible_codon_rejected() -> None:
    spec = CodonTableSpec(genome_spec=GenomeSpec.dna3(), table_name="dna_demo")
    table = CodonTable((Codon("ACG", "SENSE", 0.1, spec=spec.genome_spec),), spec=spec)
    assert table.decode("ACG").action_name == "SENSE"
    with pytest.raises(ValueError):
        table.extend(Codon("000", "BAD", 0.1))


def test_binary4_extended_table() -> None:
    spec = CodonTableSpec(genome_spec=GenomeSpec.binary4(), table_name="binary4")
    table = CodonTable((Codon("0000", "WAIT", 0.0),), spec=spec)
    assert table.validate("0000")
