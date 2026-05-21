"""Codon table and extensible action vocabulary."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from types import MappingProxyType
from typing import Final, TypeAlias

from codontrace.specs import CodonTableSpec, GenomeSpec

ActionName: TypeAlias = str


class Action(str, Enum):
    """Backward-compatible Core Kernel and GENESIS Foundation action vocabulary."""

    WAIT = "WAIT"
    SENSE_RESOURCE = "SENSE_RESOURCE"
    SENSE_DANGER = "SENSE_DANGER"
    MOVE_NORTH = "MOVE_NORTH"
    MOVE_SOUTH = "MOVE_SOUTH"
    MOVE_EAST = "MOVE_EAST"
    MOVE_WEST = "MOVE_WEST"
    COLLECT_RESOURCE = "COLLECT_RESOURCE"
    SENSE_FOOD = "SENSE_FOOD"
    MOVE_TOWARD = "MOVE_TOWARD"
    MOVE_AWAY = "MOVE_AWAY"
    EAT_LUMEN = "EAT_LUMEN"
    EMIT_NEXUS = "EMIT_NEXUS"
    COPY_SELF = "COPY_SELF"


@dataclass(frozen=True, slots=True)
class Codon:
    """A codon mapped to an executable action name.

    ``bits`` is kept as the public attribute for compatibility. For non-binary
    specs it means the codon symbol sequence, not literal bits.
    """

    bits: str
    action: Action | str
    cost: float
    description: str = ""
    spec: GenomeSpec | None = field(default=None, kw_only=True, compare=False)

    def __post_init__(self) -> None:
        if self.spec is None:
            if len(self.bits) < 3 or any(symbol not in {"0", "1"} for symbol in self.bits):
                msg = (
                    f"Invalid codon bits {self.bits!r}. Expected at least three binary digits. "
                    "For non-binary alphabets use Codon.from_sequence(..., spec=GenomeSpec.dna3()) "
                    "or pass spec= explicitly."
                )
                raise ValueError(msg)
        else:
            self.spec.validate_codon(self.bits)
        if self.cost < 0:
            msg = "Action cost cannot be negative."
            raise ValueError(msg)
        if not self.action_name:
            msg = "Action name cannot be empty."
            raise ValueError(msg)

    @classmethod
    def from_sequence(
        cls,
        sequence: str,
        action: Action | str,
        cost: float,
        description: str = "",
        *,
        spec: GenomeSpec,
    ) -> Codon:
        """Create a codon validated against a non-default GenomeSpec.

        This is the preferred constructor for DNA, ternary, or other custom
        alphabets because the default ``Codon(...)`` constructor remains
        backward-compatible with binary codons.
        """

        return cls(sequence, action, cost, description, spec=spec)

    @property
    def action_name(self) -> str:
        """Return the string action name for Enum and custom string actions."""

        return self.action.value if isinstance(self.action, Action) else self.action


class CodonTable:
    """Immutable decoder from codons to actions."""

    def __init__(
        self,
        codons: list[Codon] | tuple[Codon, ...],
        spec: CodonTableSpec | None = None,
    ) -> None:
        if not codons:
            msg = "CodonTable requires at least one codon."
            raise ValueError(msg)
        resolved_spec = spec or _infer_binary_table_spec(codons)
        mapping: dict[str, Codon] = {}
        for codon in codons:
            _validate_table_codon(codon.bits, resolved_spec)
            if codon.bits in mapping:
                msg = f"Duplicate codon {codon.bits!r}."
                raise ValueError(msg)
            mapping[codon.bits] = codon
        self._mapping = MappingProxyType(mapping)
        self.spec = resolved_spec

    @classmethod
    def default_minimal(cls) -> CodonTable:
        """Return the complete minimal default codon table."""

        return cls(DEFAULT_MINIMAL_CODONS, spec=CodonTableSpec.default_minimal())

    @classmethod
    def genesis_v0(cls) -> CodonTable:
        """Return the GENESIS Foundation v0 codon table without replacing defaults."""

        return cls(GENESIS_V0_CODONS, spec=CodonTableSpec.genesis_v0())

    @classmethod
    def genesis_toolchain_v0(cls) -> CodonTable:
        """Return an official GENESIS v0 tool-chain codon table."""

        return cls(GENESIS_TOOLCHAIN_V0_CODONS, spec=CodonTableSpec.genesis_toolchain_v0())

    @property
    def codon_lengths(self) -> tuple[int, ...]:
        """Return all codon lengths present in this table, longest first.

        Historic tables contain one length only. ADF-extended tables may contain
        longer codons; ribosome decoding uses deterministic longest-match
        semantics over these lengths.
        """

        return tuple(sorted({len(bits) for bits in self._mapping}, reverse=True))

    @property
    def supports_variable_width(self) -> bool:
        """Return whether the table contains codons with more than one width."""

        return len(self.codon_lengths) > 1

    def decode(self, bits: str) -> Codon:
        """Decode codon symbols or fail clearly for unknown codons."""

        try:
            _validate_table_codon(bits, self.spec)
        except ValueError as exc:
            msg = f"Unknown codon {bits!r}."
            raise KeyError(msg) from exc
        try:
            return self._mapping[bits]
        except KeyError as exc:
            msg = f"Unknown codon {bits!r}."
            raise KeyError(msg) from exc

    def longest_match(self, symbols: str, offset: int = 0) -> Codon | None:
        """Return the deterministic longest codon matching ``symbols[offset:]``.

        Prefix overlaps such as ``100`` and ``1000`` are intentionally resolved
        by longest-match. Ties cannot occur because duplicate codons are rejected
        at table construction. ``None`` means that no configured codon starts at
        ``offset``.
        """

        if offset < 0 or offset > len(symbols):
            msg = "offset is outside the symbol string."
            raise ValueError(msg)
        for length in self.codon_lengths:
            end = offset + length
            if end > len(symbols):
                continue
            candidate = symbols[offset:end]
            if candidate in self._mapping:
                return self._mapping[candidate]
        return None

    def extend(self, codon: Codon) -> CodonTable:
        """Return a new codon table with ``codon`` added."""

        _validate_table_codon(codon.bits, self.spec)
        if codon.bits in self._mapping:
            msg = f"Codon {codon.bits!r} already exists. Use replace()."
            raise ValueError(msg)
        return CodonTable((*self.actions(), codon), spec=self.spec)

    def replace(self, codon: Codon) -> CodonTable:
        """Return a new codon table replacing an existing codon."""

        _validate_table_codon(codon.bits, self.spec)
        if codon.bits not in self._mapping:
            msg = f"Cannot replace unknown codon {codon.bits!r}. Use extend()."
            raise ValueError(msg)
        return CodonTable(
            tuple(codon if item.bits == codon.bits else item for item in self.actions()),
            spec=self.spec,
        )

    def validate(self, bits: str) -> bool:
        """Return whether ``bits`` exists in this table and matches its spec."""

        try:
            _validate_table_codon(bits, self.spec)
        except (ValueError, RuntimeError):
            return False
        return bits in self._mapping

    def actions(self) -> tuple[Codon, ...]:
        """Return codons in deterministic bit-string order."""

        return tuple(self._mapping[key] for key in sorted(self._mapping))


def _infer_binary_table_spec(codons: list[Codon] | tuple[Codon, ...]) -> CodonTableSpec:
    widths = {len(codon.bits) for codon in codons}
    if len(widths) != 1:
        msg = "CodonTable codons must use one consistent codon width."
        raise ValueError(msg)
    width = next(iter(widths))
    return CodonTableSpec(
        genome_spec=GenomeSpec(codon_width=width, alphabet=("0", "1"), name=f"binary{width}"),
        allow_partial_tail=False,
        table_name="custom",
    )


def _validate_table_codon(bits: str, spec: CodonTableSpec) -> None:
    if len(bits) < spec.genome_spec.codon_width:
        msg = f"Invalid codon {bits!r}: expected at least width {spec.genome_spec.codon_width}."
        raise ValueError(msg)
    for symbol in bits:
        spec.genome_spec.validate_symbol(symbol)


DEFAULT_MINIMAL_CODONS: Final[tuple[Codon, ...]] = (
    Codon("000", Action.WAIT, 0.1, "Wait for one tick."),
    Codon("001", Action.SENSE_RESOURCE, 0.4, "Sense nearby resources."),
    Codon("010", Action.SENSE_DANGER, 0.4, "Sense nearby walls."),
    Codon("011", Action.MOVE_NORTH, 1.0, "Move one cell north."),
    Codon("100", Action.MOVE_SOUTH, 1.0, "Move one cell south."),
    Codon("101", Action.MOVE_EAST, 1.0, "Move one cell east."),
    Codon("110", Action.MOVE_WEST, 1.0, "Move one cell west."),
    Codon("111", Action.COLLECT_RESOURCE, 0.8, "Collect a resource on the current cell."),
)

GENESIS_V0_CODONS: Final[tuple[Codon, ...]] = (
    Codon("000", Action.WAIT, 0.1, "Wait for one tick."),
    Codon("001", Action.SENSE_FOOD, 0.4, "Sense nearby Lumen/food."),
    Codon("010", Action.SENSE_DANGER, 0.4, "Sense nearby Ignis/hazard/wall."),
    Codon("011", Action.MOVE_TOWARD, 1.2, "Move deterministically toward sensed food."),
    Codon("100", Action.MOVE_AWAY, 1.5, "Move deterministically away from sensed danger."),
    Codon("101", Action.EAT_LUMEN, 0.8, "Consume Lumen/resource into runtime ATP."),
    Codon("110", Action.EMIT_NEXUS, 0.5, "Emit a local Nexus signal marker."),
    Codon("111", Action.COPY_SELF, 8.0, "Trace a deferred reproduction attempt."),
)


GENESIS_TOOLCHAIN_V0_CODONS: Final[tuple[Codon, ...]] = (
    Codon("0000", Action.WAIT, 0.1, "Wait for one tick.", spec=CodonTableSpec.genesis_toolchain_v0().genome_spec),
    Codon("0001", Action.SENSE_RESOURCE, 0.4, "Sense nearby resources.", spec=CodonTableSpec.genesis_toolchain_v0().genome_spec),
    Codon("0010", Action.MOVE_NORTH, 1.0, "Move one cell north.", spec=CodonTableSpec.genesis_toolchain_v0().genome_spec),
    Codon("0011", Action.MOVE_SOUTH, 1.0, "Move one cell south.", spec=CodonTableSpec.genesis_toolchain_v0().genome_spec),
    Codon("0100", Action.MOVE_EAST, 1.0, "Move one cell east.", spec=CodonTableSpec.genesis_toolchain_v0().genome_spec),
    Codon("0101", Action.MOVE_WEST, 1.0, "Move one cell west.", spec=CodonTableSpec.genesis_toolchain_v0().genome_spec),
    Codon("0110", Action.COLLECT_RESOURCE, 0.8, "Collect a resource on the current cell.", spec=CodonTableSpec.genesis_toolchain_v0().genome_spec),
    Codon("0111", "CRAFT_ITEM", 1.0, "Craft an item from inventory inputs.", spec=CodonTableSpec.genesis_toolchain_v0().genome_spec),
    Codon("1000", "USE_ITEM", 0.5, "Use an inventory item.", spec=CodonTableSpec.genesis_toolchain_v0().genome_spec),
    Codon("1001", "UNLOCK_CELL", 1.0, "Unlock a cell or gate using a key/tool.", spec=CodonTableSpec.genesis_toolchain_v0().genome_spec),
    Codon("1010", "CROSS_TERRAIN", 1.0, "Cross constrained terrain using a tool.", spec=CodonTableSpec.genesis_toolchain_v0().genome_spec),
    Codon("1011", "DEPOSIT_RESOURCE", 0.8, "Deposit a carried resource.", spec=CodonTableSpec.genesis_toolchain_v0().genome_spec),
    Codon("1100", "RETURN_TO_TARGET", 0.8, "Return to a target/home cell.", spec=CodonTableSpec.genesis_toolchain_v0().genome_spec),
    Codon("1101", Action.COPY_SELF, 8.0, "Attempt reproduction when configured.", spec=CodonTableSpec.genesis_toolchain_v0().genome_spec),
)
