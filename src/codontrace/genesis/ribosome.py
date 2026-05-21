"""GENESIS Ribosome translation from Nexus genome bits to CompiledBrain."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from dataclasses import dataclass

from codontrace._types import JsonValue
from codontrace.codon import CodonTable
from codontrace.genome import SemanticGenome


@dataclass(frozen=True, slots=True)
class BrainTokenSource:
    """Source-map entry from an executable token to genome/macro origin."""

    genome_pos: int
    codon: str
    macro_id: str | None = None
    macro_stack: tuple[str, ...] = ()
    expansion_depth: int = 0

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "genome_pos": self.genome_pos,
            "codon": self.codon,
            "macro_id": self.macro_id,
            "macro_stack": list(self.macro_stack),
            "expansion_depth": self.expansion_depth,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, JsonValue]) -> BrainTokenSource:
        return cls(
            genome_pos=_json_int(data.get("genome_pos", 0), "genome_pos"),
            codon=str(data.get("codon", "")),
            macro_id=None if data.get("macro_id") is None else str(data.get("macro_id")),
            macro_stack=_string_tuple(data.get("macro_stack")),
            expansion_depth=_json_int(data.get("expansion_depth", 0), "expansion_depth"),
        )

    def digest(self) -> str:
        payload = json.dumps(self.to_dict(), sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()


@dataclass(frozen=True, slots=True)
class CodonExecutionRecord:
    """Audit record linking one executed action to its codon source."""

    organism_id: str
    tick: int
    token_index: int
    source: BrainTokenSource
    resolved_action: str
    action_status: str
    atp_before: float
    atp_after: float
    context_digest: str
    trace_event_ref: str

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "organism_id": self.organism_id,
            "tick": self.tick,
            "token_index": self.token_index,
            "source": self.source.to_dict(),
            "resolved_action": self.resolved_action,
            "action_status": self.action_status,
            "atp_before": self.atp_before,
            "atp_after": self.atp_after,
            "context_digest": self.context_digest,
            "trace_event_ref": self.trace_event_ref,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, JsonValue]) -> CodonExecutionRecord:
        source_raw = data.get("source")
        if not isinstance(source_raw, Mapping):
            raise ValueError("CodonExecutionRecord.source must be an object.")
        return cls(
            organism_id=str(data["organism_id"]),
            tick=_json_int(data["tick"], "tick"),
            token_index=_json_int(data["token_index"], "token_index"),
            source=BrainTokenSource.from_dict(source_raw),
            resolved_action=str(data["resolved_action"]),
            action_status=str(data["action_status"]),
            atp_before=_json_float(data["atp_before"], "atp_before"),
            atp_after=_json_float(data["atp_after"], "atp_after"),
            context_digest=str(data["context_digest"]),
            trace_event_ref=str(data["trace_event_ref"]),
        )

    def digest(self) -> str:
        payload = json.dumps(self.to_dict(), sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _json_int(value: JsonValue, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{field} must be an integer")
    return value


def _json_float(value: JsonValue, field: str) -> float:
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise ValueError(f"{field} must be numeric")
    return float(value)


def _string_tuple(value: JsonValue | None) -> tuple[str, ...]:
    if not isinstance(value, list):
        return ()
    return tuple(str(item) for item in value if isinstance(item, str))


@dataclass(frozen=True, slots=True)
class CompiledToken:
    """One immutable decoded GENESIS token."""

    bits: str
    action: str
    cost: float
    index: int
    source: BrainTokenSource | None = None

    def to_dict(self) -> dict[str, JsonValue]:
        """Return a JSON-friendly token dictionary."""

        return {
            "bits": self.bits,
            "action": self.action,
            "cost": self.cost,
            "index": self.index,
            "source": None if self.source is None else self.source.to_dict(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, JsonValue]) -> CompiledToken:
        """Restore a compiled token."""

        bits = data.get("bits")
        action = data.get("action")
        cost = data.get("cost")
        index = data.get("index")
        if not isinstance(bits, str) or not isinstance(action, str):
            msg = "CompiledToken bits/action must be strings."
            raise ValueError(msg)
        if isinstance(cost, bool) or not isinstance(cost, int | float):
            msg = "CompiledToken cost must be numeric."
            raise ValueError(msg)
        if isinstance(index, bool) or not isinstance(index, int):
            msg = "CompiledToken index must be an integer."
            raise ValueError(msg)
        source_raw = data.get("source")
        source = BrainTokenSource.from_dict(source_raw) if isinstance(source_raw, dict) else None
        return cls(bits=bits, action=action, cost=float(cost), index=index, source=source)


@dataclass(frozen=True, slots=True)
class CompiledBrain:
    """Immutable token program produced by Ribosome translation."""

    tokens: tuple[CompiledToken, ...]
    codon_table_version: str = "genesis_v0"

    def __post_init__(self) -> None:
        if not self.tokens:
            msg = "CompiledBrain requires at least one token."
            raise ValueError(msg)

    def to_dict(self) -> dict[str, JsonValue]:
        """Return a JSON-friendly compiled program."""

        return {
            "codon_table_version": self.codon_table_version,
            "tokens": [token.to_dict() for token in self.tokens],
        }

    def digest(self) -> str:
        """Return a stable digest of compiled tokens."""

        payload = json.dumps(self.to_dict(), sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    @classmethod
    def from_dict(cls, data: dict[str, JsonValue]) -> CompiledBrain:
        """Restore a compiled brain."""

        tokens_raw = data.get("tokens")
        version = data.get("codon_table_version", "genesis_v0")
        if not isinstance(tokens_raw, list):
            msg = "CompiledBrain.tokens must be a list."
            raise ValueError(msg)
        if not isinstance(version, str):
            msg = "CompiledBrain.codon_table_version must be a string."
            raise ValueError(msg)
        tokens = []
        for item in tokens_raw:
            if not isinstance(item, dict):
                msg = "CompiledBrain token entries must be objects."
                raise ValueError(msg)
            tokens.append(CompiledToken.from_dict(item))
        return cls(tokens=tuple(tokens), codon_table_version=version)


@dataclass(frozen=True, slots=True)
class TranslationResult:
    """Result of translating a Nexus genome bit string."""

    genome_bits: str
    compiled_brain: CompiledBrain
    skipped_tail_bits: str
    valid: bool

    def to_dict(self) -> dict[str, JsonValue]:
        """Return a JSON-friendly translation result."""

        return {
            "genome_bits": self.genome_bits,
            "compiled_brain": self.compiled_brain.to_dict(),
            "skipped_tail_bits": self.skipped_tail_bits,
            "valid": self.valid,
        }

    def digest(self) -> str:
        """Return a stable digest of translation output."""

        payload = json.dumps(self.to_dict(), sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()


@dataclass(frozen=True, slots=True)
class Ribosome:
    """Translate Nexus genome bits into immutable CompiledBrain objects."""

    codon_table: CodonTable
    min_vitae: float = 0.0
    codon_table_version: str = "genesis_v0"

    def __post_init__(self) -> None:
        if self.min_vitae < 0:
            msg = "min_vitae cannot be negative."
            raise ValueError(msg)

    @classmethod
    def genesis_v0(cls) -> Ribosome:
        """Return a Ribosome backed by the GENESIS v0 codon table."""

        return cls(codon_table=CodonTable.genesis_v0(), codon_table_version="genesis_v0")

    def translate(self, genome: str | SemanticGenome) -> TranslationResult:
        """Translate a Nexus genome into an immutable CompiledBrain.

        Tail symbols shorter than one complete codon are recorded rather than
        treated as syntax errors when the table permits partial tails.
        """

        spec = self.codon_table.spec.genome_spec
        bits = genome.to_compact() if isinstance(genome, SemanticGenome) else genome
        if not bits:
            msg = "Nexus genome bits must not be empty."
            raise ValueError(msg)
        for symbol in bits:
            spec.validate_symbol(symbol)
        tokens: list[CompiledToken] = []
        offset = 0
        skipped_tail = ""
        valid = True
        minimum_width = min(self.codon_table.codon_lengths)
        while offset < len(bits):
            codon = self.codon_table.longest_match(bits, offset)
            if codon is None:
                skipped_tail = bits[offset:]
                # A short unmatched suffix is the historic partial-tail case; a
                # full-width unmatched suffix is a deterministic unknown tail.
                valid = len(skipped_tail) < minimum_width
                break
            tokens.append(
                CompiledToken(
                    bits=codon.bits,
                    action=codon.action_name,
                    cost=codon.cost,
                    index=len(tokens),
                    source=BrainTokenSource(genome_pos=offset, codon=codon.bits),
                )
            )
            offset += len(codon.bits)
        if skipped_tail and not self.codon_table.spec.allow_partial_tail:
            # Preserve historic behavior for strings by recording the tail; table users can
            # choose to reject earlier at SemanticGenome construction.
            pass
        if not tokens:
            msg = f"Nexus genome must contain at least one complete {minimum_width}-symbol codon."
            raise ValueError(msg)
        return TranslationResult(
            genome_bits=bits,
            compiled_brain=CompiledBrain(
                tokens=tuple(tokens),
                codon_table_version=self.codon_table_version,
            ),
            skipped_tail_bits=skipped_tail,
            valid=valid,
        )
