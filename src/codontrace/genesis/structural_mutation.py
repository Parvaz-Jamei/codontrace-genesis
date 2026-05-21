"""Variable genome and codon-level structural mutation policies.

This module keeps CodonTrace library-first and dependency-free. Structural
mutation operates on decoded codon tokens by default; bit-level remainders are
made explicit by GenomeDecodingRemainderPolicy and never silently padded or
truncated unless the caller asks for that policy.
"""

from __future__ import annotations

import hashlib
import json
import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import cast

from codontrace._types import JsonValue
from codontrace.errors import ConfigurationError
from codontrace.rng import RNGManager, RNGProtocol

_ALLOWED_REMAINDER = {"nonviable_but_safe", "truncate", "pad", "reject"}
_MUTATION_KINDS = {
    "substitute",
    "bit_flip",
    "insert",
    "delete",
    "duplicate",
    "invert",
    "translocate",
}


def _digest(payload: Mapping[str, JsonValue]) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _require_finite(value: float, name: str) -> float:
    value = float(value)
    if not math.isfinite(value):
        raise ConfigurationError(f"{name} must be finite.")
    return value


@dataclass(frozen=True, slots=True)
class GenomeDecodingRemainderPolicy:
    mode: str = "nonviable_but_safe"
    pad_symbol: str = "0"

    def __post_init__(self) -> None:
        if self.mode not in _ALLOWED_REMAINDER:
            raise ConfigurationError(f"Unsupported remainder policy {self.mode!r}.")
        if self.pad_symbol not in {"0", "1"}:
            raise ConfigurationError("pad_symbol must be '0' or '1'.")

    def to_dict(self) -> dict[str, JsonValue]:
        return {"mode": self.mode, "pad_symbol": self.pad_symbol}

    @classmethod
    def from_dict(cls, data: Mapping[str, JsonValue]) -> GenomeDecodingRemainderPolicy:
        return cls(mode=_str(data, "mode"), pad_symbol=_str(data, "pad_symbol"))


@dataclass(frozen=True, slots=True)
class StructuralMutationConfig:
    bit_flip_rate: float = 0.001
    codon_insert_rate: float = 0.001
    codon_delete_rate: float = 0.001
    codon_duplicate_rate: float = 0.001
    codon_invert_rate: float = 0.0005
    codon_translocate_rate: float = 0.0002
    min_codons: int = 1
    max_codons: int = 2048
    bloat_guard: str = "mdl"
    remainder_policy: GenomeDecodingRemainderPolicy = GenomeDecodingRemainderPolicy()

    def __post_init__(self) -> None:
        for value, name in (
            (self.bit_flip_rate, "bit_flip_rate"),
            (self.codon_insert_rate, "codon_insert_rate"),
            (self.codon_delete_rate, "codon_delete_rate"),
            (self.codon_duplicate_rate, "codon_duplicate_rate"),
            (self.codon_invert_rate, "codon_invert_rate"),
            (self.codon_translocate_rate, "codon_translocate_rate"),
        ):
            value = _require_finite(value, name)
            object.__setattr__(self, name, value)
            if value < 0 or value > 1:
                raise ConfigurationError(f"{name} must be in [0, 1].")
        if self.min_codons < 0 or self.max_codons < self.min_codons:
            raise ConfigurationError("Invalid min_codons/max_codons.")
        if self.bloat_guard not in {"none", "parsimony", "mdl"}:
            raise ConfigurationError("bloat_guard must be none, parsimony, or mdl.")

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "bit_flip_rate": self.bit_flip_rate,
            "codon_insert_rate": self.codon_insert_rate,
            "codon_delete_rate": self.codon_delete_rate,
            "codon_duplicate_rate": self.codon_duplicate_rate,
            "codon_invert_rate": self.codon_invert_rate,
            "codon_translocate_rate": self.codon_translocate_rate,
            "min_codons": self.min_codons,
            "max_codons": self.max_codons,
            "bloat_guard": self.bloat_guard,
            "remainder_policy": self.remainder_policy.to_dict(),
        }

    def digest(self) -> str:
        return _digest(self.to_dict())

    @classmethod
    def from_dict(cls, data: Mapping[str, JsonValue]) -> StructuralMutationConfig:
        remainder_raw = data.get("remainder_policy", {})
        return cls(
            bit_flip_rate=_float(data, "bit_flip_rate", 0.001),
            codon_insert_rate=_float(data, "codon_insert_rate", 0.001),
            codon_delete_rate=_float(data, "codon_delete_rate", 0.001),
            codon_duplicate_rate=_float(data, "codon_duplicate_rate", 0.001),
            codon_invert_rate=_float(data, "codon_invert_rate", 0.0005),
            codon_translocate_rate=_float(data, "codon_translocate_rate", 0.0002),
            min_codons=_int(data, "min_codons", 1),
            max_codons=_int(data, "max_codons", 2048),
            bloat_guard=_str(data, "bloat_guard"),
            remainder_policy=GenomeDecodingRemainderPolicy.from_dict(remainder_raw)
            if isinstance(remainder_raw, Mapping)
            else GenomeDecodingRemainderPolicy(),
        )


@dataclass(frozen=True, slots=True)
class GenomeProgram:
    bits: str
    codon_width: int
    macro_registry_digest: str | None
    lineage_tags: tuple[str, ...]
    structural_mutation_digest: str | None
    digest: str
    viable: bool = True
    nonviable_reason: str | None = None
    identity_digest: str = ""
    provenance_digest: str = ""
    artifact_digest: str = ""

    def __post_init__(self) -> None:
        identity = genome_identity_digest(
            self.bits,
            self.codon_width,
            self.macro_registry_digest,
            self.viable,
            self.nonviable_reason,
        )
        provenance = genome_provenance_digest(
            identity, self.lineage_tags, self.structural_mutation_digest
        )
        artifact = _digest({"identity_digest": identity, "provenance_digest": provenance})
        if self.identity_digest and self.identity_digest != identity:
            raise ConfigurationError("GenomeProgram identity_digest mismatch.")
        if self.provenance_digest and self.provenance_digest != provenance:
            raise ConfigurationError("GenomeProgram provenance_digest mismatch.")
        if self.artifact_digest and self.artifact_digest != artifact:
            raise ConfigurationError("GenomeProgram artifact_digest mismatch.")
        # ``digest`` is retained as the legacy identity digest for backward compatibility.
        if self.digest and self.digest != identity:
            raise ConfigurationError("GenomeProgram digest mismatch.")
        object.__setattr__(self, "identity_digest", identity)
        object.__setattr__(self, "provenance_digest", provenance)
        object.__setattr__(self, "artifact_digest", artifact)
        object.__setattr__(self, "digest", identity)

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "bits": self.bits,
            "codon_width": self.codon_width,
            "macro_registry_digest": self.macro_registry_digest,
            "lineage_tags": list(self.lineage_tags),
            "structural_mutation_digest": self.structural_mutation_digest,
            "digest": self.digest,
            "identity_digest": self.identity_digest,
            "provenance_digest": self.provenance_digest,
            "artifact_digest": self.artifact_digest,
            "viable": self.viable,
            "nonviable_reason": self.nonviable_reason,
        }


def _canonical_genome_payload(
    *,
    bits: str,
    codon_width: int,
    macro_registry_digest: str | None,
    lineage_tags: Sequence[str],
    structural_mutation_digest: str | None,
    viable: bool,
    nonviable_reason: str | None,
) -> dict[str, JsonValue]:
    return {
        "bits": bits,
        "codon_width": codon_width,
        "macro_registry_digest": macro_registry_digest,
        "lineage_tags": cast(JsonValue, list(sorted(str(tag) for tag in lineage_tags))),
        "structural_mutation_digest": structural_mutation_digest,
        "viable": viable,
        "nonviable_reason": nonviable_reason,
    }


def genome_identity_digest(
    bits: str,
    codon_width: int,
    macro_registry_digest: str | None,
    viable: bool = True,
    nonviable_reason: str | None = None,
) -> str:
    return _digest(
        {
            "bits": bits,
            "codon_width": codon_width,
            "macro_registry_digest": macro_registry_digest,
            "viable": viable,
            "nonviable_reason": nonviable_reason,
        }
    )


def genome_provenance_digest(
    identity_digest: str,
    lineage_tags: Sequence[str],
    structural_mutation_digest: str | None,
) -> str:
    return _digest(
        {
            "identity_digest": identity_digest,
            "lineage_tags": cast(JsonValue, list(sorted(str(tag) for tag in lineage_tags))),
            "structural_mutation_digest": structural_mutation_digest,
        }
    )


def build_genome_program(
    bits: str,
    *,
    codon_width: int = 3,
    macro_registry_digest: str | None = None,
    lineage_tags: Sequence[str] = (),
    structural_mutation_digest: str | None = None,
    remainder_policy: GenomeDecodingRemainderPolicy | None = None,
) -> GenomeProgram:
    if codon_width <= 0:
        raise ConfigurationError("codon_width must be > 0.")
    if any(bit not in {"0", "1"} for bit in bits):
        raise ConfigurationError("GenomeProgram.bits must be binary.")
    policy = remainder_policy or GenomeDecodingRemainderPolicy()
    remainder = len(bits) % codon_width
    viable = True
    reason: str | None = None
    normalized_bits = bits
    if remainder:
        if policy.mode == "reject":
            raise ConfigurationError("Genome bits have a codon remainder.")
        if policy.mode == "truncate":
            normalized_bits = bits[: len(bits) - remainder]
        elif policy.mode == "pad":
            normalized_bits = bits + (policy.pad_symbol * (codon_width - remainder))
        else:
            viable = False
            reason = "codon_remainder"
    payload = _canonical_genome_payload(
        bits=normalized_bits,
        codon_width=codon_width,
        macro_registry_digest=macro_registry_digest,
        lineage_tags=lineage_tags,
        structural_mutation_digest=structural_mutation_digest,
        viable=viable,
        nonviable_reason=reason,
    )
    return GenomeProgram(
        bits=normalized_bits,
        codon_width=codon_width,
        macro_registry_digest=macro_registry_digest,
        lineage_tags=tuple(str(tag) for tag in cast(list[JsonValue], payload["lineage_tags"])),
        structural_mutation_digest=structural_mutation_digest,
        digest="",
        viable=viable,
        nonviable_reason=reason,
    )


def genome_program_from_dict(data: Mapping[str, JsonValue]) -> GenomeProgram:
    bits = _str(data, "bits")
    width = _int(data, "codon_width", 3)
    tags = tuple(str(item) for item in _list(data.get("lineage_tags")))
    obj = build_genome_program(
        bits,
        codon_width=width,
        macro_registry_digest=_optional_str(data.get("macro_registry_digest")),
        lineage_tags=tags,
        structural_mutation_digest=_optional_str(data.get("structural_mutation_digest")),
    )
    # Preserve explicit nonviable state if imported object carried it.
    if data.get("viable") is False:
        obj = build_genome_program(
            bits,
            codon_width=width,
            macro_registry_digest=_optional_str(data.get("macro_registry_digest")),
            lineage_tags=tags,
            structural_mutation_digest=_optional_str(data.get("structural_mutation_digest")),
            remainder_policy=GenomeDecodingRemainderPolicy("nonviable_but_safe"),
        )
    expected_digest = data.get("digest") or data.get("artifact_digest")
    if expected_digest is not None and obj.digest != expected_digest:
        raise ConfigurationError("GenomeProgram digest mismatch.")
    if data.get("identity_digest") is not None and obj.identity_digest != data.get(
        "identity_digest"
    ):
        raise ConfigurationError("GenomeProgram identity_digest mismatch.")
    if data.get("provenance_digest") is not None and obj.provenance_digest != data.get(
        "provenance_digest"
    ):
        raise ConfigurationError("GenomeProgram provenance_digest mismatch.")
    return obj


@dataclass(frozen=True, slots=True)
class StructuralMutationRecord:
    mutation_id: str
    parent_genome_digest: str
    child_genome_digest: str
    kind: str
    start_codon: int
    end_codon: int | None
    payload_digest: str | None
    rng_backend_kind: str
    rng_state_digest_before: str
    rng_state_digest_after: str
    digest: str = ""
    child_genome_identity_digest: str | None = None
    child_genome_provenance_digest: str | None = None
    schema_version: str = "structural_mutation_record_v2"
    codon_width: int | None = None
    token_index: int | None = None
    token_range: tuple[int, int] | None = None
    before_tokens_digest: str | None = None
    after_tokens_digest: str | None = None
    rng_seed_or_stream_id: str | None = None
    validity_status: str = "valid"
    blocked_reason: str | None = None
    effect_status: str = "effect_not_measured"

    def __post_init__(self) -> None:
        if self.kind not in _MUTATION_KINDS:
            raise ConfigurationError(f"Unsupported mutation kind {self.kind!r}.")
        if self.validity_status not in {"valid", "invalid", "blocked"}:
            raise ConfigurationError("Unsupported structural mutation validity_status.")
        if self.effect_status not in {
            "effect_not_measured",
            "lineage_recorded",
            "fitness_observed",
            "survival_observed",
            "selection_observed",
        }:
            raise ConfigurationError("Unsupported structural mutation effect_status.")
        identity = self.child_genome_identity_digest or self.child_genome_digest
        if self.child_genome_digest != identity:
            raise ConfigurationError(
                "StructuralMutationRecord.child_genome_digest must match final child "
                "identity digest."
            )
        object.__setattr__(self, "child_genome_identity_digest", identity)
        if self.token_index is None:
            object.__setattr__(self, "token_index", self.start_codon)
        if self.token_range is None:
            object.__setattr__(
                self,
                "token_range",
                (self.start_codon, self.end_codon if self.end_codon is not None else self.start_codon + 1),
            )
        computed = _digest(self._digest_payload(identity))
        if self.digest and self.digest != computed:
            raise ConfigurationError("StructuralMutationRecord digest mismatch.")
        object.__setattr__(self, "digest", computed)
        if self.child_genome_provenance_digest is None:
            object.__setattr__(
                self,
                "child_genome_provenance_digest",
                _digest({"child_identity_digest": identity, "mutation_record_base": computed}),
            )

    @property
    def mutation_kind(self) -> str:
        """Phase 2 alias that keeps the legacy ``kind`` field intact."""

        return self.kind

    def _digest_payload(self, identity: str | None = None) -> dict[str, JsonValue]:
        return {
            "schema_version": self.schema_version,
            "parent_genome_digest": self.parent_genome_digest,
            "child_genome_digest": self.child_genome_digest,
            "kind": self.kind,
            "start_codon": self.start_codon,
            "end_codon": self.end_codon,
            "payload_digest": self.payload_digest,
            "rng_backend_kind": self.rng_backend_kind,
            "rng_state_digest_before": self.rng_state_digest_before,
            "rng_state_digest_after": self.rng_state_digest_after,
            "child_genome_identity_digest": (
                identity or self.child_genome_identity_digest or self.child_genome_digest
            ),
            "mutation_id": self.mutation_id,
            "codon_width": self.codon_width,
            "token_index": self.token_index,
            "token_range": list(self.token_range) if self.token_range is not None else None,
            "before_tokens_digest": self.before_tokens_digest,
            "after_tokens_digest": self.after_tokens_digest,
            "rng_seed_or_stream_id": self.rng_seed_or_stream_id,
            "validity_status": self.validity_status,
            "blocked_reason": self.blocked_reason,
            "effect_status": self.effect_status,
        }

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "schema_version": self.schema_version,
            "mutation_id": self.mutation_id,
            "parent_genome_digest": self.parent_genome_digest,
            "child_genome_digest": self.child_genome_digest,
            "kind": self.kind,
            "mutation_kind": self.mutation_kind,
            "start_codon": self.start_codon,
            "end_codon": self.end_codon,
            "token_index": self.token_index,
            "token_range": list(self.token_range) if self.token_range is not None else None,
            "codon_width": self.codon_width,
            "before_tokens_digest": self.before_tokens_digest,
            "after_tokens_digest": self.after_tokens_digest,
            "payload_digest": self.payload_digest,
            "rng_backend_kind": self.rng_backend_kind,
            "rng_state_digest_before": self.rng_state_digest_before,
            "rng_state_digest_after": self.rng_state_digest_after,
            "rng_seed_or_stream_id": self.rng_seed_or_stream_id,
            "validity_status": self.validity_status,
            "blocked_reason": self.blocked_reason,
            "effect_status": self.effect_status,
            "digest": self.digest,
            "child_genome_identity_digest": self.child_genome_identity_digest,
            "child_genome_provenance_digest": self.child_genome_provenance_digest,
        }


def build_structural_mutation_record(
    *,
    parent_genome_digest: str,
    child_genome_digest: str,
    kind: str,
    start_codon: int,
    end_codon: int | None,
    payload_digest: str | None,
    rng_backend_kind: str,
    rng_state_digest_before: str,
    rng_state_digest_after: str,
    child_genome_identity_digest: str | None = None,
    child_genome_provenance_digest: str | None = None,
    codon_width: int | None = None,
    token_index: int | None = None,
    token_range: tuple[int, int] | None = None,
    before_tokens_digest: str | None = None,
    after_tokens_digest: str | None = None,
    rng_seed_or_stream_id: str | None = None,
    validity_status: str = "valid",
    blocked_reason: str | None = None,
    effect_status: str = "effect_not_measured",
) -> StructuralMutationRecord:
    payload: dict[str, JsonValue] = {
        "schema_version": "structural_mutation_record_v2",
        "parent_genome_digest": parent_genome_digest,
        "child_genome_digest": child_genome_digest,
        "kind": kind,
        "start_codon": start_codon,
        "end_codon": end_codon,
        "payload_digest": payload_digest,
        "rng_backend_kind": rng_backend_kind,
        "rng_state_digest_before": rng_state_digest_before,
        "rng_state_digest_after": rng_state_digest_after,
        "child_genome_identity_digest": child_genome_identity_digest or child_genome_digest,
        "codon_width": codon_width,
        "token_index": token_index if token_index is not None else start_codon,
        "token_range": list(token_range) if token_range is not None else [start_codon, end_codon if end_codon is not None else start_codon + 1],
        "before_tokens_digest": before_tokens_digest,
        "after_tokens_digest": after_tokens_digest,
        "rng_seed_or_stream_id": rng_seed_or_stream_id,
        "validity_status": validity_status,
        "blocked_reason": blocked_reason,
        "effect_status": effect_status,
    }
    mutation_id = _digest(payload)[:16]
    record_payload: dict[str, JsonValue] = {**payload, "mutation_id": mutation_id}
    return StructuralMutationRecord(
        mutation_id=mutation_id,
        parent_genome_digest=parent_genome_digest,
        child_genome_digest=child_genome_digest,
        kind=kind,
        start_codon=start_codon,
        end_codon=end_codon,
        payload_digest=payload_digest,
        rng_backend_kind=rng_backend_kind,
        rng_state_digest_before=rng_state_digest_before,
        rng_state_digest_after=rng_state_digest_after,
        child_genome_identity_digest=child_genome_identity_digest or child_genome_digest,
        child_genome_provenance_digest=child_genome_provenance_digest,
        digest=_digest(record_payload),
        codon_width=codon_width,
        token_index=token_index if token_index is not None else start_codon,
        token_range=token_range if token_range is not None else (start_codon, end_codon if end_codon is not None else start_codon + 1),
        before_tokens_digest=before_tokens_digest,
        after_tokens_digest=after_tokens_digest,
        rng_seed_or_stream_id=rng_seed_or_stream_id,
        validity_status=validity_status,
        blocked_reason=blocked_reason,
        effect_status=effect_status,
    )


def structural_mutation_record_from_dict(data: Mapping[str, JsonValue]) -> StructuralMutationRecord:
    record = build_structural_mutation_record(
        parent_genome_digest=_str(data, "parent_genome_digest"),
        child_genome_digest=_str(data, "child_genome_digest"),
        kind=_str(data, "kind"),
        start_codon=_int(data, "start_codon", 0),
        end_codon=None if data.get("end_codon") is None else _int(data, "end_codon", 0),
        payload_digest=_optional_str(data.get("payload_digest")),
        rng_backend_kind=_str(data, "rng_backend_kind"),
        rng_state_digest_before=_str(data, "rng_state_digest_before"),
        rng_state_digest_after=_str(data, "rng_state_digest_after"),
        child_genome_identity_digest=_optional_str(data.get("child_genome_identity_digest")),
        child_genome_provenance_digest=_optional_str(data.get("child_genome_provenance_digest")),
        codon_width=None if data.get("codon_width") is None else _int(data, "codon_width", 0),
        token_index=None if data.get("token_index") is None else _int(data, "token_index", 0),
        token_range=_token_range(data.get("token_range")),
        before_tokens_digest=_optional_str(data.get("before_tokens_digest")),
        after_tokens_digest=_optional_str(data.get("after_tokens_digest")),
        rng_seed_or_stream_id=_optional_str(data.get("rng_seed_or_stream_id")),
        validity_status=_str(data, "validity_status") if data.get("validity_status") is not None else "valid",
        blocked_reason=_optional_str(data.get("blocked_reason")),
        effect_status=_str(data, "effect_status") if data.get("effect_status") is not None else "effect_not_measured",
    )
    if record.digest != data.get("digest"):
        raise ConfigurationError("StructuralMutationRecord digest mismatch.")
    return record


def codon_tokens(bits: str, codon_width: int) -> tuple[str, ...]:
    if codon_width <= 0:
        raise ConfigurationError("codon_width must be > 0.")
    return tuple(
        bits[index : index + codon_width]
        for index in range(0, len(bits) - (len(bits) % codon_width), codon_width)
    )


def mutate_genome_program(
    program: GenomeProgram,
    config: StructuralMutationConfig | None = None,
    rng: RNGProtocol | None = None,
    *,
    kind: str | None = None,
    payload_codon: str | None = None,
) -> tuple[GenomeProgram, StructuralMutationRecord]:
    cfg = config or StructuralMutationConfig()
    stream = rng or RNGManager(seed=0, namespace="structural_mutation")
    before = stream.state_digest()
    tokens = list(codon_tokens(program.bits, program.codon_width))
    if not tokens:
        tokens = ["0" * program.codon_width]
    chosen = kind or _choose_kind(stream, tokens, cfg)
    if chosen not in _MUTATION_KINDS:
        raise ConfigurationError(f"Unsupported mutation kind {chosen!r}.")
    start = stream.randrange(0, max(len(tokens), 1))
    end: int | None = None
    payload = payload_codon or ("1" * program.codon_width)
    if len(payload) != program.codon_width or any(bit not in {"0", "1"} for bit in payload):
        raise ConfigurationError("payload_codon must be one codon of binary bits.")
    if chosen == "bit_flip":
        token = list(tokens[start])
        bit_index = stream.randrange(0, len(token))
        token[bit_index] = "1" if token[bit_index] == "0" else "0"
        tokens[start] = "".join(token)
    elif chosen == "substitute":
        tokens[start] = payload
    elif chosen == "insert":
        tokens.insert(start, payload)
    elif chosen == "delete":
        if len(tokens) > cfg.min_codons:
            del tokens[start]
    elif chosen == "duplicate":
        tokens.insert(start, tokens[start])
    elif chosen == "invert":
        end = min(len(tokens), start + max(1, stream.randrange(1, min(4, len(tokens)) + 1)))
        tokens[start:end] = list(reversed(tokens[start:end]))
    elif chosen == "translocate":
        moved_token = tokens.pop(start)
        dest = stream.randrange(0, len(tokens) + 1)
        tokens.insert(dest, moved_token)
        end = dest
    if len(tokens) > cfg.max_codons:
        if cfg.bloat_guard in {"parsimony", "mdl"}:
            tokens = tokens[: cfg.max_codons]
        else:
            tokens = tokens[: cfg.max_codons]
    bits = "".join(tokens)
    child_no_record = build_genome_program(
        bits,
        codon_width=program.codon_width,
        macro_registry_digest=program.macro_registry_digest,
        lineage_tags=(*program.lineage_tags, "variable_genome"),
        remainder_policy=cfg.remainder_policy,
    )
    after = stream.state_digest()
    payload_digest = (
        _digest({"payload_codon": payload}) if chosen in {"insert", "substitute"} else None
    )
    before_tokens_digest = _digest({"tokens": cast(JsonValue, list(codon_tokens(program.bits, program.codon_width)))})
    after_tokens_digest = _digest({"tokens": cast(JsonValue, list(tokens))})
    record = build_structural_mutation_record(
        parent_genome_digest=program.identity_digest,
        child_genome_digest=child_no_record.identity_digest,
        kind=chosen,
        start_codon=start,
        end_codon=end,
        payload_digest=payload_digest,
        rng_backend_kind=stream.backend_kind,
        rng_state_digest_before=before,
        rng_state_digest_after=after,
        codon_width=program.codon_width,
        token_index=start,
        token_range=(start, end if end is not None else start + 1),
        before_tokens_digest=before_tokens_digest,
        after_tokens_digest=after_tokens_digest,
        rng_seed_or_stream_id=getattr(stream, "namespace", "structural_mutation"),
        validity_status="valid" if child_no_record.viable else "invalid",
        blocked_reason=child_no_record.nonviable_reason,
        effect_status="lineage_recorded",
    )
    child = build_genome_program(
        bits,
        codon_width=program.codon_width,
        macro_registry_digest=program.macro_registry_digest,
        lineage_tags=child_no_record.lineage_tags,
        structural_mutation_digest=record.digest,
        remainder_policy=cfg.remainder_policy,
    )
    return child, record


def genome_length_distribution(programs: Sequence[GenomeProgram]) -> dict[str, JsonValue]:
    lengths = [len(item.bits) // item.codon_width for item in programs]
    if not lengths:
        return {"count": 0, "min_codons": 0, "max_codons": 0, "mean_codons": 0.0}
    return {
        "count": len(lengths),
        "min_codons": min(lengths),
        "max_codons": max(lengths),
        "mean_codons": round(sum(lengths) / len(lengths), 10),
    }


def _choose_kind(rng: RNGProtocol, tokens: Sequence[str], cfg: StructuralMutationConfig) -> str:
    rates = (
        ("bit_flip", cfg.bit_flip_rate),
        ("insert", cfg.codon_insert_rate),
        ("delete", cfg.codon_delete_rate),
        ("duplicate", cfg.codon_duplicate_rate),
        ("invert", cfg.codon_invert_rate),
        ("translocate", cfg.codon_translocate_rate),
    )
    roll = rng.random()
    total = 0.0
    for name, rate in rates:
        total += rate
        if roll <= total:
            return name
    return "substitute"


def _token_range(value: object) -> tuple[int, int] | None:
    if value is None:
        return None
    if not isinstance(value, list | tuple) or len(value) != 2:
        raise ConfigurationError("token_range must be a pair or null.")
    left, right = value
    if isinstance(left, bool) or isinstance(right, bool) or not isinstance(left, int) or not isinstance(right, int):
        raise ConfigurationError("token_range values must be integers.")
    return (left, right)


def _str(data: Mapping[str, JsonValue], key: str) -> str:
    value = data.get(key)
    if not isinstance(value, str):
        raise ConfigurationError(f"{key} must be a string.")
    return value


def _optional_str(value: object) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise ConfigurationError("value must be a string or null.")
    return value


def _int(data: Mapping[str, JsonValue], key: str, default: int) -> int:
    value = data.get(key, default)
    if isinstance(value, bool) or not isinstance(value, int):
        raise ConfigurationError(f"{key} must be an integer.")
    return value


def _float(data: Mapping[str, JsonValue], key: str, default: float) -> float:
    value = data.get(key, default)
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise ConfigurationError(f"{key} must be numeric.")
    return _require_finite(value, key)


def _list(value: object) -> list[object]:
    if value is None:
        return []
    if not isinstance(value, list):
        raise ConfigurationError("expected list")
    return value
