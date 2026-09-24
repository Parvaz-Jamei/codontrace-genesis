"""INN-13 — ESS invasion-fitness indicator (refuse-safe).

Pairwise payoff from phenotype-tag overlap; invasion score =
payoff(mutant, resident) - payoff(resident, resident). ess_candidate when
all tested mutants have invasion_score <= 0. Never ess_proved.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from codontrace._types import JsonValue
from codontrace.contracts.banned import BANNED_DOMAIN_TOKENS
from codontrace.errors import ConfigurationError
from codontrace.genesis.canonical import canonical_digest, require_finite_float
from codontrace.life_loop.match_rules import jaccard_overlap
from codontrace.life_loop.phenotype import PhenotypeMap

SCHEMA_VERSION = "life_loop_ess_invasion_v1"


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


@dataclass(frozen=True, slots=True)
class InvasionScore:
    """One mutant vs resident invasion observation."""

    mutant_id: str
    resident_id: str
    invasion_score: float
    digest: str = ""

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "mutant_id",
            _refuse_banned_fragment(_as_str(self.mutant_id, "mutant_id"), "mutant_id"),
        )
        object.__setattr__(
            self,
            "resident_id",
            _refuse_banned_fragment(
                _as_str(self.resident_id, "resident_id"), "resident_id"
            ),
        )
        object.__setattr__(
            self,
            "invasion_score",
            float(require_finite_float("invasion_score", self.invasion_score)),
        )
        computed = canonical_digest(
            {
                "mutant_id": self.mutant_id,
                "resident_id": self.resident_id,
                "invasion_score": self.invasion_score,
            },
            prefix="inv_score",
        )
        object.__setattr__(
            self, "digest", _check_digest(self.digest, computed, "InvasionScore")
        )

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "mutant_id": self.mutant_id,
            "resident_id": self.resident_id,
            "invasion_score": self.invasion_score,
            "digest": self.digest,
        }


@dataclass(frozen=True, slots=True)
class EssInvasionResult:
    """Digest-stable ESS-candidate observation table."""

    result_id: str
    resident_id: str
    scores: tuple[InvasionScore, ...]
    ess_candidate: bool
    max_invasion: float
    claim_ceiling: str = "runtime_observation"
    ess_proved: bool = False
    digest: str = ""

    def __post_init__(self) -> None:
        rid = _refuse_banned_fragment(_as_str(self.result_id, "result_id"), "result_id")
        object.__setattr__(self, "result_id", rid)
        object.__setattr__(
            self,
            "resident_id",
            _refuse_banned_fragment(
                _as_str(self.resident_id, "resident_id"), "resident_id"
            ),
        )
        object.__setattr__(self, "scores", tuple(self.scores))
        if not isinstance(self.ess_candidate, bool):
            raise ConfigurationError("ess_candidate must be a bool.")
        object.__setattr__(
            self,
            "max_invasion",
            float(require_finite_float("max_invasion", self.max_invasion)),
        )
        ceiling = _as_str(self.claim_ceiling, "claim_ceiling").casefold()
        if ceiling not in {"runtime_observation", "candidate_evidence"}:
            raise ConfigurationError(
                "claim_ceiling must be runtime_observation or candidate_evidence."
            )
        object.__setattr__(self, "claim_ceiling", ceiling)
        if self.ess_proved:
            raise ConfigurationError("refuses ess_proved=True.")
        object.__setattr__(self, "ess_proved", False)
        computed = canonical_digest(self._body(), prefix="ess_inv")
        object.__setattr__(
            self, "digest", _check_digest(self.digest, computed, "EssInvasionResult")
        )

    def _body(self) -> dict[str, JsonValue]:
        return {
            "schema_version": SCHEMA_VERSION,
            "result_id": self.result_id,
            "resident_id": self.resident_id,
            "scores": [s.to_dict() for s in self.scores],
            "ess_candidate": self.ess_candidate,
            "max_invasion": self.max_invasion,
            "claim_ceiling": self.claim_ceiling,
            "ess_proved": False,
        }

    def to_dict(self) -> dict[str, JsonValue]:
        return {**self._body(), "digest": self.digest}


def _payoff(tags_a: frozenset[str], tags_b: frozenset[str]) -> float:
    # self-play baseline uses jaccard; empty tags → 0
    if not tags_a and not tags_b:
        return 0.0
    return float(jaccard_overlap(tags_a, tags_b))


def ess_invasion_indicator(
    phenotype_map: PhenotypeMap,
    *,
    result_id: str,
    resident_id: str,
    claim_ceiling: str = "runtime_observation",
) -> EssInvasionResult:
    """Invasion fitness of every other member against a named resident."""

    if not isinstance(phenotype_map, PhenotypeMap):
        raise ConfigurationError("phenotype_map must be a PhenotypeMap.")
    by_id = {r.member_id: r for r in phenotype_map.records}
    if resident_id not in by_id:
        raise ConfigurationError(f"resident_id {resident_id!r} not in phenotype_map.")
    resident = by_id[resident_id]
    self_pay = _payoff(resident.tag_set, resident.tag_set)
    scores: list[InvasionScore] = []
    for mid, rec in sorted(by_id.items()):
        if mid == resident_id:
            continue
        inv = _payoff(rec.tag_set, resident.tag_set) - self_pay
        scores.append(
            InvasionScore(mutant_id=mid, resident_id=resident_id, invasion_score=inv)
        )
    max_inv = max((s.invasion_score for s in scores), default=0.0)
    ess_cand = all(s.invasion_score <= 1e-12 for s in scores) if scores else True
    return EssInvasionResult(
        result_id=result_id,
        resident_id=resident_id,
        scores=tuple(scores),
        ess_candidate=ess_cand,
        max_invasion=max_inv,
        claim_ceiling=claim_ceiling,
    )
