"""Domain-free phenotype maps for the life-loop.

Opaque member_id → feature tags (and optional signal vector). Digest-stable
configuration only — no tick physics, no discipline vocabulary, no claim-ladder
imports. Gene→phenotype decoding stays in module config that seeds this map.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from codontrace._types import JsonValue
from codontrace.contracts.banned import BANNED_DOMAIN_TOKENS
from codontrace.errors import ConfigurationError
from codontrace.genesis.canonical import canonical_digest, require_finite_float

SCHEMA_VERSION = "life_loop_phenotype_v1"


def _as_str(value: object, name: str, *, allow_empty: bool = False) -> str:
    if not isinstance(value, str):
        raise ConfigurationError(f"{name} must be a string.")
    text = value.strip()
    if not text and not allow_empty:
        raise ConfigurationError(f"{name} must be a non-empty string.")
    return text


def _as_int(value: object, name: str, *, minimum: int | None = None) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ConfigurationError(f"{name} must be an integer.")
    if minimum is not None and value < minimum:
        raise ConfigurationError(f"{name} must be >= {minimum}.")
    return value


def _refuse_banned_fragment(text: str, name: str) -> str:
    lowered = text.casefold()
    for token in BANNED_DOMAIN_TOKENS:
        if token.casefold() in lowered:
            raise ConfigurationError(f"{name} contains a banned fragment.")
    return text


def _check_digest(existing: str, computed: str, label: str) -> str:
    if existing and existing != computed:
        raise ConfigurationError(f"{label} digest mismatch.")
    return computed


def _normalize_tags(tags: Sequence[str], name: str) -> tuple[str, ...]:
    if not isinstance(tags, (list, tuple)):
        raise ConfigurationError(f"{name} must be a list or tuple.")
    cleaned: list[str] = []
    seen: set[str] = set()
    for item in tags:
        tag = _refuse_banned_fragment(_as_str(item, f"{name}.item"), f"{name}.item")
        if tag not in seen:
            seen.add(tag)
            cleaned.append(tag)
    return tuple(sorted(cleaned))


def _normalize_vector(vector: Sequence[float] | None, name: str) -> tuple[float, ...]:
    if vector is None:
        return ()
    if not isinstance(vector, (list, tuple)):
        raise ConfigurationError(f"{name} must be a list or tuple.")
    out: list[float] = []
    for i, item in enumerate(vector):
        out.append(float(require_finite_float(f"{name}[{i}]", item)))
    return tuple(out)


@dataclass(frozen=True, slots=True)
class PhenotypeRecord:
    """Immutable opaque phenotype for one member."""

    member_id: str
    feature_tags: tuple[str, ...] = ()
    signal_vector: tuple[float, ...] = ()
    digest: str = ""

    def __post_init__(self) -> None:
        mid = _refuse_banned_fragment(
            _as_str(self.member_id, "member_id"), "member_id"
        )
        object.__setattr__(self, "member_id", mid)
        object.__setattr__(
            self, "feature_tags", _normalize_tags(self.feature_tags, "feature_tags")
        )
        object.__setattr__(
            self,
            "signal_vector",
            _normalize_vector(self.signal_vector, "signal_vector"),
        )
        computed = canonical_digest(self._body(), prefix="pheno_rec")
        object.__setattr__(
            self, "digest", _check_digest(self.digest, computed, "PhenotypeRecord")
        )

    def _body(self) -> dict[str, JsonValue]:
        return {
            "schema_version": SCHEMA_VERSION,
            "member_id": self.member_id,
            "feature_tags": list(self.feature_tags),
            "signal_vector": list(self.signal_vector),
        }

    def to_dict(self) -> dict[str, JsonValue]:
        return {**self._body(), "digest": self.digest}

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> PhenotypeRecord:
        tags = data.get("feature_tags", ())
        vec = data.get("signal_vector", ())
        if not isinstance(tags, (list, tuple)):
            raise ConfigurationError("feature_tags must be a list or tuple.")
        if not isinstance(vec, (list, tuple)):
            raise ConfigurationError("signal_vector must be a list or tuple.")
        return cls(
            member_id=_as_str(data.get("member_id"), "member_id"),
            feature_tags=tuple(str(t) for t in tags),
            signal_vector=tuple(float(v) for v in vec),
            digest=_as_str(data.get("digest", ""), "digest", allow_empty=True),
        )

    @property
    def tag_set(self) -> frozenset[str]:
        return frozenset(self.feature_tags)


@dataclass(frozen=True, slots=True)
class PhenotypeMap:
    """Immutable member_id → PhenotypeRecord book (digest-stable)."""

    map_id: str
    records: tuple[PhenotypeRecord, ...] = ()
    digest: str = ""

    def __post_init__(self) -> None:
        mid = _refuse_banned_fragment(_as_str(self.map_id, "map_id"), "map_id")
        object.__setattr__(self, "map_id", mid)
        if not isinstance(self.records, tuple):
            raise ConfigurationError("records must be a tuple.")
        cleaned: list[PhenotypeRecord] = []
        seen: set[str] = set()
        for rec in self.records:
            if not isinstance(rec, PhenotypeRecord):
                raise ConfigurationError("records must contain PhenotypeRecord values.")
            if rec.member_id in seen:
                raise ConfigurationError(
                    f"duplicate phenotype member_id {rec.member_id!r}."
                )
            seen.add(rec.member_id)
            cleaned.append(rec)
        cleaned.sort(key=lambda r: r.member_id)
        object.__setattr__(self, "records", tuple(cleaned))
        computed = canonical_digest(self._body(), prefix="pheno_map")
        object.__setattr__(
            self, "digest", _check_digest(self.digest, computed, "PhenotypeMap")
        )

    def _body(self) -> dict[str, JsonValue]:
        return {
            "schema_version": SCHEMA_VERSION,
            "map_id": self.map_id,
            "records": [r.to_dict() for r in self.records],
        }

    def to_dict(self) -> dict[str, JsonValue]:
        return {**self._body(), "digest": self.digest}

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> PhenotypeMap:
        raw = data.get("records", ())
        if not isinstance(raw, (list, tuple)):
            raise ConfigurationError("records must be a list or tuple.")
        records = tuple(
            PhenotypeRecord.from_dict(item) if isinstance(item, Mapping) else item
            for item in raw
        )
        return cls(
            map_id=_as_str(data.get("map_id"), "map_id"),
            records=records,
            digest=_as_str(data.get("digest", ""), "digest", allow_empty=True),
        )

    @classmethod
    def from_tag_mapping(
        cls,
        map_id: str,
        tags_by_member: Mapping[str, Sequence[str]],
        *,
        vectors_by_member: Mapping[str, Sequence[float]] | None = None,
    ) -> PhenotypeMap:
        """Build a map from opaque member → tag sequences."""

        vectors = vectors_by_member or {}
        records = tuple(
            PhenotypeRecord(
                member_id=str(member),
                feature_tags=tuple(str(t) for t in tag_seq),
                signal_vector=tuple(float(x) for x in vectors.get(str(member), ())),
            )
            for member, tag_seq in sorted(tags_by_member.items(), key=lambda kv: str(kv[0]))
        )
        return cls(map_id=map_id, records=records)

    def get(self, member_id: str) -> PhenotypeRecord | None:
        mid = _as_str(member_id, "member_id")
        for rec in self.records:
            if rec.member_id == mid:
                return rec
        return None

    def require(self, member_id: str) -> PhenotypeRecord:
        rec = self.get(member_id)
        if rec is None:
            raise ConfigurationError(f"missing phenotype for member {member_id!r}.")
        return rec

    def member_ids(self) -> tuple[str, ...]:
        return tuple(r.member_id for r in self.records)

    def __len__(self) -> int:
        return len(self.records)


__all__ = [
    "SCHEMA_VERSION",
    "PhenotypeMap",
    "PhenotypeRecord",
]
