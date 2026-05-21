from __future__ import annotations

from codontrace.codon import Codon, CodonTable
from codontrace.genesis import GenesisOrganism, Ribosome
from codontrace.specs import CodonTableSpec, GenomeSpec


def test_from_bits_default_binary3_is_backward_compatible() -> None:
    organism = GenesisOrganism.from_bits("org", "000001011", initial_runtime_atp=5.0)

    assert organism.genome.to_codons() == ("000", "001", "011")
    assert [token.bits for token in organism.compiled_brain.tokens] == ["000", "001", "011"]


def test_from_bits_uses_ribosome_genome_spec_for_binary4() -> None:
    spec = GenomeSpec.binary4()
    table = CodonTable(
        [Codon("0000", "WAIT", 0.0), Codon("0001", "SENSE_FOOD", 0.0)],
        spec=CodonTableSpec(spec, table_name="binary4_test"),
    )
    organism = GenesisOrganism.from_bits("org", "00000001", ribosome=Ribosome(table))

    assert organism.genome.spec.codon_width == 4
    assert organism.genome.to_codons() == ("0000", "0001")
    assert [token.bits for token in organism.compiled_brain.tokens] == ["0000", "0001"]
