"""Strict locks for motor holes the older suite does not cover."""

from __future__ import annotations

from pathlib import Path

from codontrace.genesis.atp import GenesisATPState
from codontrace.genesis.birth import (
    ReproductionMode,
    SexualRecombinationConfig,
    recombine_positional_segment,
)
from codontrace.genesis.population import ReproductionConfig
from codontrace.genesis.ribosome import Ribosome
from codontrace.genome import BitSpan, SemanticGenome, rebase_spans, splice_spans
from codontrace.rng import RNGManager

_COMPACT = "101111000"
_REPO = Path(__file__).resolve().parents[2]


def test_compact_dict_keys_and_digest_are_stable() -> None:
    first = SemanticGenome.from_compact(_COMPACT)
    second = SemanticGenome.from_compact(_COMPACT)
    payload = first.to_dict()
    assert set(payload) == {"codons", "spec"}
    assert first.digest() == second.digest()


def test_middle_payload_span_drops_one_translated_token() -> None:
    spanned = SemanticGenome.from_compact(_COMPACT).with_spans(
        (BitSpan(3, 6, "payload", "mid"),)
    )
    executable = spanned.executable_bits()
    compact = spanned.to_compact()
    assert len(executable) == 6
    assert len(compact) == 9
    ribosome = Ribosome.genesis_v0()
    executable_tokens = ribosome.translate(SemanticGenome.from_compact(executable)).compiled_brain.tokens
    compact_tokens = ribosome.translate(SemanticGenome.from_compact(compact)).compiled_brain.tokens
    assert len(executable_tokens) == len(compact_tokens) - 1


def test_rebase_trim_that_cuts_a_span_drops_it() -> None:
    original_length = 12
    removed = 6
    cap = original_length - removed
    kept = BitSpan(0, 3, "silent", "keep")
    cut = BitSpan(3, 9, "payload", "cut")
    assert cut.start < cap < cut.end
    rebased = rebase_spans(
        (kept, cut),
        (f"trim:{removed}",),
        codon_width=3,
        original_length=original_length,
    )
    assert [span.tag for span in rebased] == ["keep"]


def _straddling_span(start: int, end: int, length: int, codon_width: int = 3) -> BitSpan:
    if start > 0:
        return BitSpan(start - codon_width, end, "payload", "straddle")
    if end < length:
        return BitSpan(0, length, "payload", "straddle")
    raise AssertionError(f"window [{start}, {end}) covers length {length}")


def test_sexual_equal_parents_drop_span_straddling_crossover() -> None:
    reproduction = ReproductionConfig(reproduction_mode=ReproductionMode.SEXUAL_CROSSOVER)
    sexual = SexualRecombinationConfig(
        enabled=True,
        recombination_prob=1.0,
        same_length_only=True,
    )
    assert reproduction.is_sexual
    assert sexual.recombination_prob == 1.0
    parent_a = _COMPACT
    parent_b = "000000111"
    assert len(parent_a) == len(parent_b)
    record = recombine_positional_segment(
        parent_a_id="parent-a",
        parent_b_id="parent-b",
        parent_a_bits=parent_a,
        parent_b_bits=parent_b,
        parent_a_genome_digest=SemanticGenome.from_compact(parent_a).digest(),
        parent_b_genome_digest=SemanticGenome.from_compact(parent_b).digest(),
        rng=RNGManager(seed=11).fork("recombination"),
        codon_width=3,
    )
    assert len(record.child_genome_bits) == len(parent_a) == len(parent_b)
    span = _straddling_span(record.start_index, record.end_index, len(parent_a), record.codon_width)
    wholly_outside = span.end <= record.start_index or span.start >= record.end_index
    wholly_inside = record.start_index <= span.start and span.end <= record.end_index
    assert not wholly_outside and not wholly_inside
    child = SemanticGenome.from_compact(record.child_genome_bits).with_spans(
        splice_spans((span,), (), record.start_index, record.end_index)
    )
    assert span.tag not in {item.tag for item in child.spans}
    assert len(child) == len(SemanticGenome.from_compact(parent_a))


def test_debit_runtime_overdraw_returns_none_and_keeps_atp() -> None:
    state = GenesisATPState.from_runtime(1.5)
    before_atp = state.runtime_available
    before_ledger = state.ledger_digest()
    before_entries = len(state.runtime.ledger)
    result = state.debit_runtime(
        before_atp + 1.0,
        tick=3,
        organism_id="motor",
        codon="101",
        action="EAT_LUMEN",
    )
    assert result is None
    assert state.runtime_available == before_atp
    assert state.runtime.current_atp == before_atp
    assert len(state.runtime.ledger) == before_entries
    assert state.ledger_digest() == before_ledger


def test_engine_py_has_no_biology_plugin_words() -> None:
    engine = (_REPO / "src" / "codontrace" / "engine.py").read_text(encoding="utf-8")
    for word in ("outcross", "kappa", "BitSpan"):
        assert word not in engine, word
