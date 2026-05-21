"""Semantic genome representation for configurable GENESIS codon specs."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from typing import ClassVar

from codontrace._types import JsonValue
from codontrace.rng import RNGManager
from codontrace.specs import GenomeSpec


@dataclass(frozen=True, slots=True, init=False)
class SemanticGenome:
    """Validated immutable genome made of codons described by a GenomeSpec.

    The default remains the historic binary three-symbol codon genome. Custom
    specs make non-binary alphabets and wider codons available without changing
    source code.
    """

    _codons: tuple[str, ...] = field(repr=False)
    spec: GenomeSpec = field(default_factory=GenomeSpec.binary3)

    CODON_LENGTH: ClassVar[int] = 3
    VALID_SYMBOLS: ClassVar[frozenset[str]] = frozenset({"0", "1"})

    def __init__(
        self,
        codons: list[str] | tuple[str, ...],
        spec: GenomeSpec | None = None,
    ) -> None:
        object.__setattr__(self, "_codons", tuple(codons))
        object.__setattr__(self, "spec", spec or GenomeSpec.binary3())
        self.__post_init__()

    def __post_init__(self) -> None:
        if not self._codons:
            msg = "Genome must contain at least one codon."
            raise ValueError(msg)
        for codon in self._codons:
            self.spec.validate_codon(codon)

    @classmethod
    def from_codons(
        cls,
        codons: list[str] | tuple[str, ...],
        spec: GenomeSpec | None = None,
    ) -> SemanticGenome:
        """Build a genome from explicit codon strings."""

        return cls(tuple(codons), spec=spec)

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

    def to_compact(self) -> str:
        """Return all codons as a compact symbol string."""

        return "".join(self._codons)

    def to_dict(self) -> dict[str, JsonValue]:
        """Return a JSON-friendly genome payload."""

        return {"codons": list(self._codons), "spec": self.spec.to_dict()}

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
            return cls.from_codons(codons)
        if not isinstance(raw_spec, dict):
            msg = "SemanticGenome.spec must be an object."
            raise ValueError(msg)
        return cls.from_codons(codons, spec=GenomeSpec.from_dict(raw_spec))

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
