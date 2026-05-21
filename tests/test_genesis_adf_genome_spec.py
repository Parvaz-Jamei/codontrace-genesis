from __future__ import annotations

from codontrace import GenomeSpec
from codontrace.genesis import DynamicVocabularyConfig, DynamicVocabularyState


def test_dynamic_vocabulary_state_uses_non_binary_genome_spec() -> None:
    config = DynamicVocabularyConfig(extended_codon_width=3, genome_spec=GenomeSpec.dna3())
    state = DynamicVocabularyState.for_config("custom", config)
    assert state.codon_width == 3
    assert state.alphabet == ("A", "C", "G", "T")
    assert "AAA" in state.next_available_bits
    assert DynamicVocabularyState.from_dict(state.to_dict()).digest() == state.digest()
