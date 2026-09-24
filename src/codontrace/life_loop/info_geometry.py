"""INN-02 — Information-geometry distances on phenotype frequency simplices.

Jensen–Shannon divergence and a discrete Fisher–Rao chordal distance on
normalized tag-frequency vectors from PhenotypeMap. Observation only.
"""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from codontrace._types import JsonValue
from codontrace.contracts.banned import BANNED_DOMAIN_TOKENS
from codontrace.errors import ConfigurationError
from codontrace.genesis.canonical import canonical_digest, require_finite_float
from codontrace.life_loop.phenotype import PhenotypeMap

SCHEMA_VERSION = "life_loop_info_geometry_v1"


def _as_str(value: object, name: str, *, allow_empty: bool = False) -> str:
    if not isinstance(value, str):
        raise ConfigurationError(f"{name} must be a string.")
    text = value.strip()
    if not text and not allow_empty:
        raise ConfigurationError(f"{name} must be a non-empty string.")
    return text


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


def phenotype_tag_frequencies(phenotype_map: PhenotypeMap) -> dict[str, float]:
    """Normalized multiset frequencies of feature tags across members."""

    if not isinstance(phenotype_map, PhenotypeMap):
        raise ConfigurationError("phenotype_map must be a PhenotypeMap.")
    counts: dict[str, int] = {}
    for rec in phenotype_map.records:
        for tag in rec.feature_tags:
            counts[tag] = counts.get(tag, 0) + 1
    total = sum(counts.values())
    if total <= 0:
        return {}
    return {k: v / total for k, v in sorted(counts.items())}


def _aligned_probs(
    p: Mapping[str, float], q: Mapping[str, float]
) -> tuple[tuple[float, ...], tuple[float, ...]]:
    keys = sorted(set(p) | set(q))
    if not keys:
        return ((), ())
    pv = tuple(float(p.get(k, 0.0)) for k in keys)
    qv = tuple(float(q.get(k, 0.0)) for k in keys)
    # renormalize after alignment (zeros for missing)
    ps, qs = sum(pv), sum(qv)
    if ps <= 0.0 or qs <= 0.0:
        raise ConfigurationError("both distributions must have positive mass.")
    return tuple(x / ps for x in pv), tuple(x / qs for x in qv)


def _kl(a: Sequence[float], b: Sequence[float]) -> float:
    total = 0.0
    for ai, bi in zip(a, b, strict=True):
        if ai <= 0.0:
            continue
        if bi <= 0.0:
            # JS mixes with midpoint so bi>0 in practice; guard
            continue
        total += ai * math.log(ai / bi)
    return total


def js_divergence(
    p: Mapping[str, float], q: Mapping[str, float]
) -> float:
    """Jensen–Shannon divergence in nats; symmetric, in [0, ln 2]."""

    pv, qv = _aligned_probs(p, q)
    if not pv:
        return 0.0
    mv = tuple(0.5 * (a + b) for a, b in zip(pv, qv, strict=True))
    return 0.5 * _kl(pv, mv) + 0.5 * _kl(qv, mv)


def fisher_simplex_distance(
    p: Mapping[str, float], q: Mapping[str, float]
) -> float:
    """Discrete Fisher–Rao chordal distance: 2*arccos(sum sqrt(p_i q_i))."""

    pv, qv = _aligned_probs(p, q)
    if not pv:
        return 0.0
    bhattacharyya = sum(math.sqrt(max(0.0, a) * max(0.0, b)) for a, b in zip(pv, qv, strict=True))
    # numerical clamp
    bhattacharyya = max(-1.0, min(1.0, bhattacharyya))
    return 2.0 * math.acos(bhattacharyya)


@dataclass(frozen=True, slots=True)
class InfoGeometryContrast:
    """Digest-stable distance between two phenotype frequency maps."""

    contrast_id: str
    js_divergence: float
    fisher_distance: float
    n_tags_union: int
    claim_ceiling: str = "runtime_observation"
    digest: str = ""

    def __post_init__(self) -> None:
        cid = _refuse_banned_fragment(
            _as_str(self.contrast_id, "contrast_id"), "contrast_id"
        )
        object.__setattr__(self, "contrast_id", cid)
        object.__setattr__(
            self,
            "js_divergence",
            float(require_finite_float("js_divergence", self.js_divergence)),
        )
        object.__setattr__(
            self,
            "fisher_distance",
            float(require_finite_float("fisher_distance", self.fisher_distance)),
        )
        if self.js_divergence < 0.0:
            raise ConfigurationError("js_divergence must be >= 0.")
        if self.fisher_distance < 0.0:
            raise ConfigurationError("fisher_distance must be >= 0.")
        if not isinstance(self.n_tags_union, int) or isinstance(self.n_tags_union, bool):
            raise ConfigurationError("n_tags_union must be an integer.")
        if self.n_tags_union < 0:
            raise ConfigurationError("n_tags_union must be >= 0.")
        ceiling = _as_str(self.claim_ceiling, "claim_ceiling").casefold()
        if ceiling not in {"runtime_observation", "candidate_evidence"}:
            raise ConfigurationError(
                "claim_ceiling must be runtime_observation or candidate_evidence."
            )
        object.__setattr__(self, "claim_ceiling", ceiling)
        computed = canonical_digest(self._body(), prefix="info_geom")
        object.__setattr__(
            self, "digest", _check_digest(self.digest, computed, "InfoGeometryContrast")
        )

    def _body(self) -> dict[str, JsonValue]:
        return {
            "schema_version": SCHEMA_VERSION,
            "contrast_id": self.contrast_id,
            "js_divergence": self.js_divergence,
            "fisher_distance": self.fisher_distance,
            "n_tags_union": self.n_tags_union,
            "claim_ceiling": self.claim_ceiling,
        }

    def to_dict(self) -> dict[str, JsonValue]:
        return {**self._body(), "digest": self.digest}


def contrast_phenotype_maps(
    map_a: PhenotypeMap,
    map_b: PhenotypeMap,
    *,
    contrast_id: str,
    claim_ceiling: str = "runtime_observation",
) -> InfoGeometryContrast:
    fa = phenotype_tag_frequencies(map_a)
    fb = phenotype_tag_frequencies(map_b)
    n_union = len(set(fa) | set(fb))
    if not fa and not fb:
        js = 0.0
        fisher = 0.0
    elif not fa or not fb:
        # one empty → maximal separation on simplex (treat empty as impossible;
        # use unit mass on synthetic sentinel then distance to other)
        raise ConfigurationError(
            "both phenotype maps must have at least one feature tag for contrast."
        )
    else:
        js = js_divergence(fa, fb)
        fisher = fisher_simplex_distance(fa, fb)
    return InfoGeometryContrast(
        contrast_id=contrast_id,
        js_divergence=js,
        fisher_distance=fisher,
        n_tags_union=n_union,
        claim_ceiling=claim_ceiling,
    )
