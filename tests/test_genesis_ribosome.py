from __future__ import annotations

import pytest

from codontrace.genesis import CompiledBrain, Ribosome


def test_9_bit_genome_produces_3_tokens() -> None:
    result = Ribosome.genesis_v0().translate("000001010")
    assert len(result.compiled_brain.tokens) == 3
    assert result.skipped_tail_bits == ""


def test_10_bit_genome_records_tail_bit() -> None:
    result = Ribosome.genesis_v0().translate("0000010101")
    assert len(result.compiled_brain.tokens) == 3
    assert result.skipped_tail_bits == "1"


def test_invalid_non_binary_genome_fails_clearly() -> None:
    with pytest.raises(ValueError):
        Ribosome.genesis_v0().translate("00020")


def test_all_8_codons_decode_correctly() -> None:
    result = Ribosome.genesis_v0().translate("000001010011100101110111")
    assert [token.action for token in result.compiled_brain.tokens] == [
        "WAIT",
        "SENSE_FOOD",
        "SENSE_DANGER",
        "MOVE_TOWARD",
        "MOVE_AWAY",
        "EAT_LUMEN",
        "EMIT_NEXUS",
        "COPY_SELF",
    ]


def test_compiled_brain_is_immutable_and_digest_deterministic() -> None:
    result = Ribosome.genesis_v0().translate("000001010")
    assert isinstance(result.compiled_brain, CompiledBrain)
    with pytest.raises(AttributeError):
        result.compiled_brain.tokens = ()  # type: ignore[misc]
    assert result.digest() == Ribosome.genesis_v0().translate("000001010").digest()
