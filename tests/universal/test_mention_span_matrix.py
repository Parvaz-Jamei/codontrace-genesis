from __future__ import annotations

import pytest

from codontrace.genesis.population import MutationConfig, mutate_genome
from codontrace.genome import BitSpan, SemanticGenome, rebase_spans, splice_spans


def test_empty_spans_omitted_from_dict_and_digest_matches_span_free() -> None:
    plain = SemanticGenome.from_compact("010011100101")
    empty = plain.with_spans(())
    cleared = plain.with_spans((BitSpan(0, 3, "silent", "quiet"),)).with_spans(())

    assert empty.spans == ()
    assert cleared.spans == ()
    assert "spans" not in plain.to_dict()
    assert "spans" not in empty.to_dict()
    assert "spans" not in cleared.to_dict()
    assert empty.to_dict() == plain.to_dict()
    assert cleared.to_dict() == plain.to_dict()
    assert empty.digest() == plain.digest()
    assert cleared.digest() == plain.digest()
    assert empty.executable_bits() == plain.to_compact()


def test_payload_span_absent_from_executable_bits_but_kept_on_compact_tape() -> None:
    tape = "110000111001"
    payload = BitSpan(6, 9, "payload", "cargo")
    mixed = SemanticGenome.from_compact(tape).with_spans((payload,))

    assert mixed.to_compact() == tape
    assert mixed.to_compact()[payload.start : payload.end] == "111"
    assert "111" in mixed.to_compact()
    assert mixed.executable_bits() == "110000001"
    assert "111" not in mixed.executable_bits()
    assert mixed.executable_bits() == tape[: payload.start] + tape[payload.end :]


def test_two_nonoverlapping_spans_and_overlap_raises() -> None:
    tape = "110000111001"
    quiet = BitSpan(0, 3, "silent", "quiet")
    cargo = BitSpan(6, 9, "payload", "cargo")
    mixed = SemanticGenome.from_compact(tape).with_spans((cargo, quiet))

    assert mixed.spans == (quiet, cargo)
    assert mixed.spans[0].kind == "silent"
    assert mixed.spans[1].kind == "payload"
    assert mixed.to_compact() == tape
    assert mixed.executable_bits() == "000001"
    assert tape[quiet.start : quiet.end] not in mixed.executable_bits()
    assert tape[cargo.start : cargo.end] not in mixed.executable_bits()

    with pytest.raises(ValueError, match="BitSpans must not overlap."):
        SemanticGenome.from_compact(tape).with_spans(
            (
                BitSpan(0, 6, "silent", "quiet"),
                BitSpan(3, 9, "payload", "cargo"),
            )
        )


def test_unaligned_span_raises() -> None:
    genome = SemanticGenome.from_compact("110000111001")

    with pytest.raises(ValueError, match="BitSpan must be codon-aligned."):
        genome.with_spans((BitSpan(1, 4, "silent", "skew"),))
    with pytest.raises(ValueError, match="BitSpan must be codon-aligned."):
        genome.with_spans((BitSpan(0, 5, "payload", "skew-end"),))
    with pytest.raises(ValueError, match="BitSpan must be codon-aligned."):
        genome.with_spans((BitSpan(2, 8, "payload", "skew-both"),))


@pytest.mark.parametrize("kind", ["silent", "payload"])
def test_span_covering_every_codon_raises(kind: str) -> None:
    genome = SemanticGenome.from_compact("111000101")

    with pytest.raises(ValueError, match="Mention spans must leave at least one executable codon."):
        genome.with_spans((BitSpan(0, 9, kind, "wall"),))


def test_bit_flip_rate_zero_keeps_span_coordinates() -> None:
    tape = "010011100101111000"
    spans = (
        BitSpan(0, 3, "silent", "quiet"),
        BitSpan(9, 15, "payload", "cargo"),
    )
    genome = SemanticGenome.from_compact(tape).with_spans(spans)
    result = mutate_genome(genome, MutationConfig(bit_flip_rate=0.0), seed=8)

    assert result.operations == ()
    assert result.mutated_genome.spans == spans
    assert result.mutated_genome.spans[0].start == 0
    assert result.mutated_genome.spans[0].end == 3
    assert result.mutated_genome.spans[1].start == 9
    assert result.mutated_genome.spans[1].end == 15
    assert result.mutated_genome.to_compact() == tape
    assert result.mutated_genome.executable_bits() == "011100000"
    assert genome.spans == spans


def test_one_insertion_before_span_shifts_and_inside_drops() -> None:
    tape = "110000111001010101"
    span = BitSpan(3, 12, "payload", "cargo")
    genome = SemanticGenome.from_compact(tape).with_spans((span,))
    width = 3

    shifted = rebase_spans(
        genome.spans,
        ("insert:0:101",),
        codon_width=width,
        original_length=len(tape),
    )
    assert shifted == (BitSpan(span.start + width, span.end + width, "payload", "cargo"),)

    dropped = rebase_spans(
        genome.spans,
        ("insert:6:110",),
        codon_width=width,
        original_length=len(tape),
    )
    assert dropped == ()

    before = mutate_genome(
        genome,
        MutationConfig(bit_flip_rate=0.0, insertion_rate=1.0, deletion_rate=0.0),
        seed=5,
    )
    assert before.operations == ("insert:0:101",)
    assert before.mutated_genome.to_compact() == "101110000111001010101"
    assert before.mutated_genome.spans == (
        BitSpan(span.start + width, span.end + width, "payload", "cargo"),
    )
    assert before.mutated_genome.executable_bits() == "101110010101"
    assert (
        before.mutated_genome.to_compact()[
            span.start + width : span.end + width
        ]
        == tape[span.start : span.end]
    )

    inside = mutate_genome(
        genome,
        MutationConfig(bit_flip_rate=0.0, insertion_rate=1.0, deletion_rate=0.0),
        seed=0,
    )
    assert inside.operations == ("insert:6:110",)
    assert span.start < 6 < span.end
    assert inside.mutated_genome.spans == ()
    assert inside.mutated_genome.to_compact() == "110000110111001010101"
    assert inside.mutated_genome.executable_bits() == inside.mutated_genome.to_compact()
    assert genome.spans == (span,)


def test_one_deletion_before_span_shifts_and_inside_drops() -> None:
    tape = "110000111001010101"
    span = BitSpan(3, 12, "silent", "quiet")
    genome = SemanticGenome.from_compact(tape).with_spans((span,))
    width = 3

    shifted = rebase_spans(
        genome.spans,
        ("delete:0:110",),
        codon_width=width,
        original_length=len(tape),
    )
    assert shifted == (BitSpan(span.start - width, span.end - width, "silent", "quiet"),)

    dropped = rebase_spans(
        genome.spans,
        ("delete:6:111",),
        codon_width=width,
        original_length=len(tape),
    )
    assert dropped == ()

    before = mutate_genome(
        genome,
        MutationConfig(bit_flip_rate=0.0, insertion_rate=0.0, deletion_rate=1.0),
        seed=1,
    )
    assert before.operations == ("delete:0:110",)
    assert before.mutated_genome.to_compact() == "000111001010101"
    assert before.mutated_genome.spans == (
        BitSpan(span.start - width, span.end - width, "silent", "quiet"),
    )
    assert before.mutated_genome.to_compact()[
        span.start - width : span.end - width
    ] == tape[span.start : span.end]
    assert before.mutated_genome.executable_bits() == "010101"

    inside = mutate_genome(
        genome,
        MutationConfig(bit_flip_rate=0.0, insertion_rate=0.0, deletion_rate=1.0),
        seed=0,
    )
    assert inside.operations == ("delete:6:111",)
    assert span.start < 6 < span.end
    assert inside.mutated_genome.spans == ()
    assert inside.mutated_genome.to_compact() == "110000001010101"
    assert inside.mutated_genome.executable_bits() == inside.mutated_genome.to_compact()
    assert genome.spans == (span,)


def test_splice_spans_keeps_outside_outer_and_inside_inner_drops_straddle() -> None:
    window_start, window_end = 6, 12
    outer_out = BitSpan(0, 3, "silent", "outer-out")
    outer_cut = BitSpan(3, 9, "payload", "outer-cut")
    outer_after = BitSpan(12, 15, "silent", "outer-after")
    inner_in = BitSpan(6, 9, "payload", "inner-in")
    inner_cut = BitSpan(9, 15, "silent", "inner-cut")

    spliced = splice_spans(
        (outer_out, outer_cut, outer_after),
        (inner_in, inner_cut),
        window_start,
        window_end,
    )

    assert outer_out.end <= window_start
    assert outer_after.start >= window_end
    assert window_start <= inner_in.start and inner_in.end <= window_end
    assert outer_cut.start < window_start < outer_cut.end
    assert inner_cut.start < window_end < inner_cut.end
    assert spliced == (outer_out, inner_in, outer_after)
    assert outer_cut not in spliced
    assert inner_cut not in spliced

    tape = "010011100101111000"
    genome = SemanticGenome.from_compact(tape).with_spans(spliced)
    assert genome.spans == spliced
    assert genome.executable_bits() == "011101000"
    assert tape[outer_cut.start : outer_cut.end] in genome.to_compact()
    assert tape[inner_cut.start : inner_cut.end] in genome.to_compact()


def test_semantic_genome_from_dict_roundtrip() -> None:
    tape = "110000111001"
    genome = SemanticGenome.from_compact(tape).with_spans(
        (
            BitSpan(9, 12, "payload", "cargo"),
            BitSpan(0, 3, "silent", "quiet"),
        )
    )
    payload = genome.to_dict()
    restored = SemanticGenome.from_dict(payload)

    assert isinstance(payload["spans"], list)
    assert restored == genome
    assert restored.digest() == genome.digest()
    assert restored.spans == (
        BitSpan(0, 3, "silent", "quiet"),
        BitSpan(9, 12, "payload", "cargo"),
    )
    assert restored.to_compact() == tape
    assert restored.executable_bits() == genome.executable_bits() == "000111"
    assert restored.to_dict() == payload
    assert {span.kind for span in restored.spans} == {"silent", "payload"}
