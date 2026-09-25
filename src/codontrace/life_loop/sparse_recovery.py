"""INN-14 — Sparse phenotype-tag recovery (compressive-sensing lite).

Soft-threshold iterative pursuit of tag coefficients against a binary
outcome vector. Observational sparse support — never gene_identity_proved.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from codontrace._types import JsonValue
from codontrace.contracts.banned import BANNED_DOMAIN_TOKENS
from codontrace.errors import ConfigurationError
from codontrace.genesis.canonical import canonical_digest, require_finite_float
from codontrace.life_loop.phenotype import PhenotypeMap

SCHEMA_VERSION = "life_loop_sparse_recovery_v1"


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
class SparseCoefficient:
    tag: str
    coefficient: float
    digest: str = ""

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "tag", _refuse_banned_fragment(_as_str(self.tag, "tag"), "tag")
        )
        object.__setattr__(
            self,
            "coefficient",
            float(require_finite_float("coefficient", self.coefficient)),
        )
        computed = canonical_digest(
            {"tag": self.tag, "coefficient": self.coefficient}, prefix="sparse_coef"
        )
        object.__setattr__(
            self, "digest", _check_digest(self.digest, computed, "SparseCoefficient")
        )

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "tag": self.tag,
            "coefficient": self.coefficient,
            "digest": self.digest,
        }


@dataclass(frozen=True, slots=True)
class SparseRecoveryResult:
    result_id: str
    outcome_key: str
    coefficients: tuple[SparseCoefficient, ...]
    support_size: int
    residual_mse: float
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
        object.__setattr__(self, "coefficients", tuple(self.coefficients))
        object.__setattr__(
            self, "support_size", _as_int(self.support_size, "support_size", minimum=0)
        )
        object.__setattr__(
            self,
            "residual_mse",
            float(require_finite_float("residual_mse", self.residual_mse)),
        )
        if self.residual_mse < 0.0:
            raise ConfigurationError("residual_mse must be >= 0.")
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
        computed = canonical_digest(self._body(), prefix="sparse_rec")
        object.__setattr__(
            self, "digest", _check_digest(self.digest, computed, "SparseRecoveryResult")
        )

    def _body(self) -> dict[str, JsonValue]:
        return {
            "schema_version": SCHEMA_VERSION,
            "result_id": self.result_id,
            "outcome_key": self.outcome_key,
            "coefficients": [c.to_dict() for c in self.coefficients],
            "support_size": self.support_size,
            "residual_mse": self.residual_mse,
            "claim_ceiling": self.claim_ceiling,
            "gene_identity_proved": False,
            "locus_identity_proved": False,
        }

    def to_dict(self) -> dict[str, JsonValue]:
        return {**self._body(), "digest": self.digest}


def sparse_phenotype_recovery(
    phenotype_map: PhenotypeMap,
    outcomes: Mapping[str, float],
    *,
    result_id: str,
    outcome_key: str = "match_score",
    soft_threshold: float = 0.15,
    n_iters: int = 8,
    claim_ceiling: str = "runtime_observation",
) -> SparseRecoveryResult:
    """ISTA-lite soft-threshold pursuit of tag coefficients vs outcomes."""

    if not isinstance(phenotype_map, PhenotypeMap):
        raise ConfigurationError("phenotype_map must be a PhenotypeMap.")
    if not isinstance(outcomes, Mapping):
        raise ConfigurationError("outcomes must be a mapping.")
    thr = float(require_finite_float("soft_threshold", soft_threshold))
    if thr < 0.0:
        raise ConfigurationError("soft_threshold must be >= 0.")
    iters = _as_int(n_iters, "n_iters", minimum=1)
    members: list[tuple[frozenset[str], float]] = []
    tags: set[str] = set()
    for rec in phenotype_map.records:
        if rec.member_id not in outcomes:
            continue
        y = float(require_finite_float(f"outcomes[{rec.member_id}]", outcomes[rec.member_id]))
        members.append((rec.tag_set, y))
        tags.update(rec.feature_tags)
    tag_list = sorted(tags)
    if not members or not tag_list:
        return SparseRecoveryResult(
            result_id=result_id,
            outcome_key=outcome_key,
            coefficients=(),
            support_size=0,
            residual_mse=0.0,
            claim_ceiling=claim_ceiling,
        )
    n = len(members)
    p = len(tag_list)
    # design X[i][j] in {0,1}
    x = [[1.0 if tag_list[j] in members[i][0] else 0.0 for j in range(p)] for i in range(n)]
    y = [members[i][1] for i in range(n)]
    coef = [0.0] * p
    # step size ~ 1 / ||X||^2 rough
    step = 1.0 / max(1.0, float(p))
    for _ in range(iters):
        # residual r = y - X coef
        pred = [
            sum(x[i][j] * coef[j] for j in range(p)) for i in range(n)
        ]
        resid = [y[i] - pred[i] for i in range(n)]
        grad = [
            -sum(x[i][j] * resid[i] for i in range(n)) / n for j in range(p)
        ]
        for j in range(p):
            z = coef[j] - step * grad[j]
            # soft threshold
            if z > thr:
                coef[j] = z - thr
            elif z < -thr:
                coef[j] = z + thr
            else:
                coef[j] = 0.0
    pred = [sum(x[i][j] * coef[j] for j in range(p)) for i in range(n)]
    mse = sum((y[i] - pred[i]) ** 2 for i in range(n)) / n
    coeffs = [
        SparseCoefficient(tag=tag_list[j], coefficient=round(coef[j], 10))
        for j in range(p)
        if abs(coef[j]) > 1e-12
    ]
    coeffs.sort(key=lambda c: c.tag)
    return SparseRecoveryResult(
        result_id=result_id,
        outcome_key=outcome_key,
        coefficients=tuple(coeffs),
        support_size=len(coeffs),
        residual_mse=float(mse),
        claim_ceiling=claim_ceiling,
    )
