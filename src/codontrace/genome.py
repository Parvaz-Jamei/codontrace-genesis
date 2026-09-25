"""Semantic genome representation for configurable GENESIS codon specs."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from typing import ClassVar

from codontrace._types import JsonValue
from codontrace.rng import RNGManager
from codontrace.specs import GenomeSpec


@dataclass(frozen=True, slots=True)
class BitSpan:
    """Codon-aligned interval that is stored on the tape and not executed.

    ``silent`` and ``payload`` are opaque kinds. The motor does not interpret them.
    """

    start: int
    end: int
    kind: str
    tag: str

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "start": self.start,
            "end": self.end,
            "kind": self.kind,
            "tag": self.tag,
        }

    @classmethod
    def from_dict(cls, data: dict[str, JsonValue]) -> BitSpan:
        return cls(
            start=int(data["start"]),
            end=int(data["end"]),
            kind=str(data["kind"]),
            tag=str(data["tag"]),
        )


def _normalize_spans(
    spans: tuple[BitSpan, ...], *, bit_length: int, codon_width: int
) -> tuple[BitSpan, ...]:
    if not spans:
        return ()
    ordered = tuple(sorted(spans, key=lambda item: (item.start, item.end, item.kind, item.tag)))
    tags: set[str] = set()
    covered = 0
    previous_end = 0
    for span in ordered:
        if span.kind not in {"silent", "payload"}:
            msg = "BitSpan.kind must be 'silent' or 'payload'."
            raise ValueError(msg)
        if not span.tag or span.tag in tags:
            msg = "BitSpan.tag must be unique and non-empty."
            raise ValueError(msg)
        tags.add(span.tag)
        if span.start < 0 or span.end > bit_length or span.start >= span.end:
            msg = "BitSpan must lie inside the genome."
            raise ValueError(msg)
        if span.start % codon_width or span.end % codon_width:
            msg = "BitSpan must be codon-aligned."
            raise ValueError(msg)
        if span.start < previous_end:
            msg = "BitSpans must not overlap."
            raise ValueError(msg)
        previous_end = span.end
        covered += span.end - span.start
    if bit_length - covered < codon_width:
        msg = "Mention spans must leave at least one executable codon."
        raise ValueError(msg)
    return ordered


def rebase_spans(
    spans: tuple[BitSpan, ...],
    operations: tuple[str, ...],
    *,
    codon_width: int,
    original_length: int,
) -> tuple[BitSpan, ...]:
    """Shift spans after edits that were already drawn. Overlapping edits drop the span."""

    current = list(spans)
    length = original_length
    for operation in operations:
        if operation.startswith("flip:"):
            continue
        if operation.startswith("insert:"):
            _kind, at_text, codon = operation.split(":", 2)
            at = int(at_text)
            width = len(codon)
            nxt: list[BitSpan] = []
            for span in current:
                if span.start < at < span.end:
                    continue
                if span.start >= at:
                    nxt.append(BitSpan(span.start + width, span.end + width, span.kind, span.tag))
                else:
                    nxt.append(span)
            current = nxt
            length += width
            continue
        if operation.startswith("delete:"):
            _kind, at_text, removed = operation.split(":", 2)
            at = int(at_text)
            width = len(removed)
            nxt = []
            for span in current:
                if span.end <= at:
                    nxt.append(span)
                elif span.start >= at + width:
                    nxt.append(BitSpan(span.start - width, span.end - width, span.kind, span.tag))
            current = nxt
            length -= width
            continue
        if operation.startswith("trim:"):
            removed = int(operation.split(":", 1)[1])
            cap = length - removed
            current = [span for span in current if span.end <= cap]
            length = cap
    return _normalize_spans(tuple(current), bit_length=length, codon_width=codon_width)


def splice_spans(
    outer: tuple[BitSpan, ...],
    inner: tuple[BitSpan, ...],
    start: int,
    end: int,
) -> tuple[BitSpan, ...]:
    """Keep outer spans wholly outside the swap and inner spans wholly inside it."""

    kept = [span for span in outer if span.end <= start or span.start >= end]
    kept.extend(span for span in inner if start <= span.start and span.end <= end)
    return tuple(sorted(kept, key=lambda item: (item.start, item.end, item.kind, item.tag)))


@dataclass(frozen=True, slots=True, init=False)
class SemanticGenome:
    """Validated immutable genome made of codons described by a GenomeSpec.

    The default remains the historic binary three-symbol codon genome. Custom
    specs make non-binary alphabets and wider codons available without changing
    source code.
    """

    _codons: tuple[str, ...] = field(repr=False)
    _spans: tuple[BitSpan, ...] = field(default=(), repr=False)
    spec: GenomeSpec = field(default_factory=GenomeSpec.binary3)

    CODON_LENGTH: ClassVar[int] = 3
    VALID_SYMBOLS: ClassVar[frozenset[str]] = frozenset({"0", "1"})

    def __init__(
        self,
        codons: list[str] | tuple[str, ...],
        spec: GenomeSpec | None = None,
        spans: tuple[BitSpan, ...] | list[BitSpan] = (),
    ) -> None:
        object.__setattr__(self, "_codons", tuple(codons))
        object.__setattr__(self, "spec", spec or GenomeSpec.binary3())
        object.__setattr__(self, "_spans", tuple(spans))
        self.__post_init__()

    def __post_init__(self) -> None:
        if not self._codons:
            msg = "Genome must contain at least one codon."
            raise ValueError(msg)
        for codon in self._codons:
            self.spec.validate_codon(codon)
        normalized = _normalize_spans(
            self._spans,
            bit_length=sum(len(codon) for codon in self._codons),
            codon_width=self.spec.codon_width,
        )
        object.__setattr__(self, "_spans", normalized)

    @classmethod
    def from_codons(
        cls,
        codons: list[str] | tuple[str, ...],
        spec: GenomeSpec | None = None,
        spans: tuple[BitSpan, ...] | list[BitSpan] = (),
    ) -> SemanticGenome:
        """Build a genome from explicit codon strings."""

        return cls(tuple(codons), spec=spec, spans=tuple(spans))

    @classmethod
    def from_compact(cls, symbols: str, spec: GenomeSpec | None = None) -> SemanticGenome:
        """Build a genome from a compact symbol string."""

        resolved_spec = spec or GenomeSpec.binary3()
        if not symbols:
            msg = "Compact genome string must not be empty."
            raise ValueError(msg)
        if len(symbols) % resolved_spec.codon_width != 0:
            msg = f"Compact genome length must be a multiple of {resolved_spec.codon_width}."
            raise ValueError(msg)
        return cls(
            tuple(
                symbols[index : index + resolved_spec.codon_width]
                for index in range(0, len(symbols), resolved_spec.codon_width)
            ),
            spec=resolved_spec,
        )

    @classmethod
    def random(
        cls,
        length: int,
        seed: int | None = None,
        rng: RNGManager | None = None,
        spec: GenomeSpec | None = None,
    ) -> SemanticGenome:
        """Create a deterministic genome with ``length`` codons."""

        resolved_spec = spec or GenomeSpec.binary3()
        if length <= 0:
            msg = "Genome length must be positive."
            raise ValueError(msg)
        if seed is not None and rng is not None:
            msg = "Provide either seed or rng, not both."
            raise ValueError(msg)
        stream = rng if rng is not None else RNGManager(seed=seed).fork("genome")
        codons = tuple(
            "".join(stream.choice(resolved_spec.alphabet) for _ in range(resolved_spec.codon_width))
            for _ in range(length)
        )
        return cls(codons, spec=resolved_spec)

    def to_codons(self) -> tuple[str, ...]:
        """Return codons as an immutable tuple."""

        return self._codons

    @property
    def spans(self) -> tuple[BitSpan, ...]:
        return self._spans

    def with_spans(self, spans: tuple[BitSpan, ...] | list[BitSpan]) -> SemanticGenome:
        return SemanticGenome(self._codons, spec=self.spec, spans=tuple(spans))

    def executable_bits(self) -> str:
        """Bits the ribosome may compile. Empty spans return the whole tape."""

        bits = self.to_compact()
        if not self._spans:
            return bits
        for span in sorted(self._spans, key=lambda item: item.start, reverse=True):
            bits = bits[: span.start] + bits[span.end :]
        return bits

    def to_compact(self) -> str:
        """Return all codons as a compact symbol string."""

        return "".join(self._codons)

    def to_dict(self) -> dict[str, JsonValue]:
        """Return a JSON-friendly genome payload."""

        payload: dict[str, JsonValue] = {
            "codons": list(self._codons),
            "spec": self.spec.to_dict(),
        }
        if self._spans:
            payload["spans"] = [span.to_dict() for span in self._spans]
        return payload

    @classmethod
    def from_dict(cls, data: dict[str, JsonValue]) -> SemanticGenome:
        """Restore a genome from ``to_dict()`` output."""

        raw_codons = data.get("codons")
        raw_spec = data.get("spec")
        if not isinstance(raw_codons, list) or not all(
            isinstance(item, str) for item in raw_codons
        ):
            msg = "SemanticGenome.codons must be a list of strings."
            raise ValueError(msg)
        codons = tuple(str(item) for item in raw_codons)
        if raw_spec is None:
            genome = cls.from_codons(codons)
        elif not isinstance(raw_spec, dict):
            msg = "SemanticGenome.spec must be an object."
            raise ValueError(msg)
        else:
            genome = cls.from_codons(codons, spec=GenomeSpec.from_dict(raw_spec))
        raw_spans = data.get("spans", ())
        if not raw_spans:
            return genome
        if not isinstance(raw_spans, list):
            msg = "SemanticGenome.spans must be a list."
            raise ValueError(msg)
        return genome.with_spans(
            tuple(BitSpan.from_dict(item) for item in raw_spans if isinstance(item, dict))
        )

    def pretty(self) -> str:
        """Return a human-readable codon sequence."""

        return " | ".join(self._codons)

    def digest(self) -> str:
        """Return a stable digest including the genome spec."""

        payload = json.dumps(self.to_dict(), sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    def __len__(self) -> int:
        return len(self._codons)

    @classmethod
    def _validate_codon(cls, codon: str) -> None:
        GenomeSpec.binary3().validate_codon(codon)


Genome = SemanticGenome
