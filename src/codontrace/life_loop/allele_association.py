"""INN-06 — Observational allele↔outcome association (popGWAS-lite).

Scores co-occurrence of phenotype feature tags with binary outcomes
(match_pass / attach success). Refuse-safe; never gene_identity_proved.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from codontrace._types import JsonValue
from codontrace.contracts.banned import BANNED_DOMAIN_TOKENS
from codontrace.errors import ConfigurationError
from codontrace.genesis.canonical import canonical_digest, require_finite_float
from codontrace.life_loop.phenotype import PhenotypeMap

SCHEMA_VERSION = "life_loop_allele_association_v1"


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
class AlleleAssociationScore:
    """Per-tag observational association with a binary outcome."""

    tag: str
    n_with_tag: int
    n_outcome_with_tag: int
    n_without_tag: int
    n_outcome_without_tag: int
    risk_diff: float
    digest: str = ""

    def __post_init__(self) -> None:
        tag = _refuse_banned_fragment(_as_str(self.tag, "tag"), "tag")
        object.__setattr__(self, "tag", tag)
        object.__setattr__(
            self, "n_with_tag", _as_int(self.n_with_tag, "n_with_tag", minimum=0)
        )
        object.__setattr__(
            self,
            "n_outcome_with_tag",
            _as_int(self.n_outcome_with_tag, "n_outcome_with_tag", minimum=0),
        )
        object.__setattr__(
            self, "n_without_tag", _as_int(self.n_without_tag, "n_without_tag", minimum=0)
        )
        object.__setattr__(
            self,
            "n_outcome_without_tag",
            _as_int(self.n_outcome_without_tag, "n_outcome_without_tag", minimum=0),
        )
        if self.n_outcome_with_tag > self.n_with_tag:
            raise ConfigurationError("n_outcome_with_tag cannot exceed n_with_tag.")
        if self.n_outcome_without_tag > self.n_without_tag:
            raise ConfigurationError(
                "n_outcome_without_tag cannot exceed n_without_tag."
            )
        object.__setattr__(
            self, "risk_diff", float(require_finite_float("risk_diff", self.risk_diff))
        )
        computed = canonical_digest(self._body(), prefix="allele_score")
        object.__setattr__(
            self, "digest", _check_digest(self.digest, computed, "AlleleAssociationScore")
        )

    def _body(self) -> dict[str, JsonValue]:
        return {
            "tag": self.tag,
            "n_with_tag": self.n_with_tag,
            "n_outcome_with_tag": self.n_outcome_with_tag,
            "n_without_tag": self.n_without_tag,
            "n_outcome_without_tag": self.n_outcome_without_tag,
            "risk_diff": self.risk_diff,
        }

    def to_dict(self) -> dict[str, JsonValue]:
        return {**self._body(), "digest": self.digest}


@dataclass(frozen=True, slots=True)
class AlleleAssociationResult:
    """Digest-stable association table; Honesty-ceiling pinned."""

    result_id: str
    outcome_key: str
    scores: tuple[AlleleAssociationScore, ...]
    claim_ceiling: str = "runtime_observation"
    gene_identity_proved: bool = False
    locus_identity_proved: bool = False
    digest: str = ""

    def __post_init__(self) -> None:
        rid = _refuse_banned_fragment(_as_str(self.result_id, "result_id"), "result_id")
        object.__setattr__(self, "result_id", rid)
        object.__setattr__(
            self,
            "outcome_key",
            _refuse_banned_fragment(
                _as_str(self.outcome_key, "outcome_key"), "outcome_key"
            ),
        )
        object.__setattr__(self, "scores", tuple(self.scores))
        ceiling = _as_str(self.claim_ceiling, "claim_ceiling").casefold()
        if ceiling not in {"runtime_observation", "candidate_evidence"}:
            raise ConfigurationError(
                "claim_ceiling must be runtime_observation or candidate_evidence."
            )
        object.__setattr__(self, "claim_ceiling", ceiling)
        if self.gene_identity_proved:
            raise ConfigurationError("refuses gene_identity_proved=True.")
        if self.locus_identity_proved:
            raise ConfigurationError("refuses locus_identity_proved=True.")
        object.__setattr__(self, "gene_identity_proved", False)
        object.__setattr__(self, "locus_identity_proved", False)
        computed = canonical_digest(self._body(), prefix="allele_assoc")
        object.__setattr__(
            self, "digest", _check_digest(self.digest, computed, "AlleleAssociationResult")
        )

    def _body(self) -> dict[str, JsonValue]:
        return {
            "schema_version": SCHEMA_VERSION,
            "result_id": self.result_id,
            "outcome_key": self.outcome_key,
            "scores": [s.to_dict() for s in self.scores],
            "claim_ceiling": self.claim_ceiling,
            "gene_identity_proved": False,
            "locus_identity_proved": False,
        }

    def to_dict(self) -> dict[str, JsonValue]:
        return {**self._body(), "digest": self.digest}


def allele_outcome_association(
    phenotype_map: PhenotypeMap,
    outcomes: Mapping[str, bool],
    *,
    result_id: str,
    outcome_key: str = "match_pass",
    claim_ceiling: str = "runtime_observation",
) -> AlleleAssociationResult:
    """Compute risk-difference association of each tag with binary outcomes.

    ``outcomes`` maps member_id → bool. Members missing from outcomes are skipped.
    """

    if not isinstance(phenotype_map, PhenotypeMap):
        raise ConfigurationError("phenotype_map must be a PhenotypeMap.")
    if not isinstance(outcomes, Mapping):
        raise ConfigurationError("outcomes must be a mapping.")
    # collect tags
    tags: set[str] = set()
    members: list[tuple[str, frozenset[str], bool]] = []
    for rec in phenotype_map.records:
        if rec.member_id not in outcomes:
            continue
        flag = outcomes[rec.member_id]
        if not isinstance(flag, bool):
            raise ConfigurationError(f"outcomes[{rec.member_id!r}] must be bool.")
        tags.update(rec.feature_tags)
        members.append((rec.member_id, rec.tag_set, flag))
    scores: list[AlleleAssociationScore] = []
    for tag in sorted(tags):
        n_with = n_out_with = n_without = n_out_without = 0
        for _mid, tag_set, flag in members:
            if tag in tag_set:
                n_with += 1
                if flag:
                    n_out_with += 1
            else:
                n_without += 1
                if flag:
                    n_out_without += 1
        p1 = (n_out_with / n_with) if n_with else 0.0
        p0 = (n_out_without / n_without) if n_without else 0.0
        scores.append(
            AlleleAssociationScore(
                tag=tag,
                n_with_tag=n_with,
                n_outcome_with_tag=n_out_with,
                n_without_tag=n_without,
                n_outcome_without_tag=n_out_without,
                risk_diff=p1 - p0,
            )
        )
    return AlleleAssociationResult(
        result_id=result_id,
        outcome_key=outcome_key,
        scores=tuple(scores),
        claim_ceiling=claim_ceiling,
    )
