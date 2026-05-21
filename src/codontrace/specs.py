"""Configurable genome and codon-table specifications for GENESIS extensions."""

from __future__ import annotations

import hashlib
import itertools
import json
from dataclasses import dataclass

from codontrace._types import JsonValue
from codontrace.errors import ConfigurationError


@dataclass(frozen=True, slots=True)
class GenomeSpec:
    """Alphabet and codon-width contract for semantic genomes."""

    codon_width: int = 3
    alphabet: tuple[str, ...] = ("0", "1")
    name: str = "binary3"

    def __post_init__(self) -> None:
        if isinstance(self.codon_width, bool) or not isinstance(self.codon_width, int):
            msg = "GenomeSpec.codon_width must be an integer; bool is not accepted."
            raise ConfigurationError(msg)
        if self.codon_width <= 0:
            msg = "GenomeSpec.codon_width must be positive."
            raise ConfigurationError(msg)
        if not self.alphabet:
            msg = "GenomeSpec.alphabet must not be empty."
            raise ConfigurationError(msg)
        if len(set(self.alphabet)) != len(self.alphabet):
            msg = "GenomeSpec.alphabet symbols must be unique."
            raise ConfigurationError(msg)
        if any(not isinstance(symbol, str) or len(symbol) != 1 for symbol in self.alphabet):
            msg = "GenomeSpec.alphabet entries must be single-character strings."
            raise ConfigurationError(msg)
        if not self.name:
            msg = "GenomeSpec.name must not be empty."
            raise ConfigurationError(msg)

    @classmethod
    def binary3(cls) -> GenomeSpec:
        return cls(codon_width=3, alphabet=("0", "1"), name="binary3")

    @classmethod
    def binary4(cls) -> GenomeSpec:
        return cls(codon_width=4, alphabet=("0", "1"), name="binary4")

    @classmethod
    def dna3(cls) -> GenomeSpec:
        return cls(codon_width=3, alphabet=("A", "C", "G", "T"), name="dna3")

    @classmethod
    def ternary2(cls) -> GenomeSpec:
        return cls(codon_width=2, alphabet=("0", "1", "2"), name="ternary2")

    def validate_symbol(self, symbol: str) -> None:
        """Fail clearly if ``symbol`` is outside this spec's alphabet."""

        if symbol not in self.alphabet:
            msg = f"Invalid genome symbol {symbol!r} for GenomeSpec {self.name!r}."
            raise ConfigurationError(msg)

    def validate_codon(self, codon: str) -> None:
        """Fail clearly if ``codon`` does not match this spec."""

        if len(codon) != self.codon_width:
            msg = (
                f"Invalid codon {codon!r}: expected width {self.codon_width} "
                f"for GenomeSpec {self.name!r}."
            )
            raise ConfigurationError(msg)
        for symbol in codon:
            self.validate_symbol(symbol)

    def all_codons(self) -> tuple[str, ...]:
        """Return all codons in deterministic lexicographic alphabet order."""

        return tuple(
            "".join(items) for items in itertools.product(self.alphabet, repeat=self.codon_width)
        )

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "codon_width": self.codon_width,
            "alphabet": list(self.alphabet),
            "name": self.name,
        }

    @classmethod
    def from_dict(cls, data: dict[str, JsonValue]) -> GenomeSpec:
        width = data.get("codon_width")
        alphabet = data.get("alphabet")
        name = data.get("name", "custom")
        if isinstance(width, bool) or not isinstance(width, int):
            msg = "GenomeSpec.codon_width must be an integer."
            raise ConfigurationError(msg)
        if not isinstance(alphabet, list) or not all(isinstance(item, str) for item in alphabet):
            msg = "GenomeSpec.alphabet must be a list of strings."
            raise ConfigurationError(msg)
        if not isinstance(name, str):
            msg = "GenomeSpec.name must be a string."
            raise ConfigurationError(msg)
        alphabet_tuple = tuple(str(item) for item in alphabet)
        return cls(codon_width=width, alphabet=alphabet_tuple, name=name)

    def digest(self) -> str:
        payload = json.dumps(self.to_dict(), sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()


@dataclass(frozen=True, slots=True)
class CodonTableSpec:
    """Validation contract carried by a CodonTable."""

    genome_spec: GenomeSpec = GenomeSpec.binary3()
    allow_partial_tail: bool = False
    table_name: str = "custom"

    def __post_init__(self) -> None:
        if not self.table_name:
            msg = "CodonTableSpec.table_name must not be empty."
            raise ConfigurationError(msg)

    @classmethod
    def genesis_v0(cls) -> CodonTableSpec:
        return cls(
            genome_spec=GenomeSpec.binary3(), allow_partial_tail=False, table_name="genesis_v0"
        )

    @classmethod
    def genesis_toolchain_v0(cls) -> CodonTableSpec:
        return cls(
            genome_spec=GenomeSpec.binary4(), allow_partial_tail=False, table_name="genesis_toolchain_v0"
        )

    @classmethod
    def default_minimal(cls) -> CodonTableSpec:
        return cls(
            genome_spec=GenomeSpec.binary3(), allow_partial_tail=False, table_name="default_minimal"
        )

    def validate_codon(self, codon: str) -> None:
        self.genome_spec.validate_codon(codon)

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "genome_spec": self.genome_spec.to_dict(),
            "allow_partial_tail": self.allow_partial_tail,
            "table_name": self.table_name,
        }

    @classmethod
    def from_dict(cls, data: dict[str, JsonValue]) -> CodonTableSpec:
        raw_spec = data.get("genome_spec")
        allow_partial_tail = data.get("allow_partial_tail", False)
        table_name = data.get("table_name", "custom")
        if not isinstance(raw_spec, dict):
            msg = "CodonTableSpec.genome_spec must be an object."
            raise ConfigurationError(msg)
        if not isinstance(allow_partial_tail, bool):
            msg = "CodonTableSpec.allow_partial_tail must be a bool."
            raise ConfigurationError(msg)
        if not isinstance(table_name, str):
            msg = "CodonTableSpec.table_name must be a string."
            raise ConfigurationError(msg)
        return cls(
            genome_spec=GenomeSpec.from_dict(raw_spec),
            allow_partial_tail=allow_partial_tail,
            table_name=table_name,
        )

    def digest(self) -> str:
        payload = json.dumps(self.to_dict(), sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()
