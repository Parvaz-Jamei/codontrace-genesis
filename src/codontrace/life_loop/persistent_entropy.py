"""INN-07 — Persistent-entropy proxy on PhenotypeMap Jaccard filtrations.

Shannon entropy of single-linkage merge lifetimes (H0 barcode proxy).
Complements β₀/β₁ cyclomatic proxies — no GUDHI/ripser dependency.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass

from codontrace._types import JsonValue
from codontrace.contracts.banned import BANNED_DOMAIN_TOKENS
from codontrace.errors import ConfigurationError
from codontrace.genesis.canonical import canonical_digest, require_finite_float
from codontrace.life_loop.match_rules import jaccard_overlap
from codontrace.life_loop.phenotype import PhenotypeMap

SCHEMA_VERSION = "life_loop_persistent_entropy_v1"


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


def _unit_interval(value: object, name: str) -> float:
    number = float(require_finite_float(name, value))
    if number < 0.0 or number > 1.0:
        raise ConfigurationError(f"{name} must be in [0, 1].")
    return number


def _pairwise_distances(phenotype_map: PhenotypeMap) -> list[tuple[int, int, float]]:
    records = phenotype_map.records
    pairs: list[tuple[int, int, float]] = []
    n = len(records)
    for i in range(n):
        for j in range(i + 1, n):
            jac = jaccard_overlap(records[i].tag_set, records[j].tag_set)
            # filtration distance: merge when distance <= t; d = 1 - jaccard
            pairs.append((i, j, max(0.0, 1.0 - jac)))
    pairs.sort(key=lambda t: (t[2], t[0], t[1]))
    return pairs


def _h0_lifetimes(n: int, pairs: Sequence[tuple[int, int, float]]) -> list[float]:
    """Single-linkage Kruskal merge heights as finite H0 bar lengths."""

    if n <= 0:
        return []
    if n == 1:
        return []
    parent = list(range(n))
    rank = [0] * n

    def find(i: int) -> int:
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    lifetimes: list[float] = []
    merges = 0
    for i, j, dist in pairs:
        ri, rj = find(i), find(j)
        if ri == rj:
            continue
        # finite bar dies at merge distance (birth at 0 for components)
        lifetimes.append(float(dist))
        if rank[ri] < rank[rj]:
            parent[ri] = rj
        elif rank[ri] > rank[rj]:
            parent[rj] = ri
        else:
            parent[rj] = ri
            rank[ri] += 1
        merges += 1
        if merges >= n - 1:
            break
    return lifetimes


def persistent_entropy_from_lifetimes(
    lifetimes: Sequence[float], *, normalize: bool = True
) -> float:
    """Shannon entropy of positive lifetimes; optional /log(n) normalization."""

    pos = [float(require_finite_float("lifetime", x)) for x in lifetimes if float(x) > 0.0]
    if not pos:
        return 0.0
    total = sum(pos)
    if total <= 0.0:
        return 0.0
    ent = 0.0
    for length in pos:
        p = length / total
        ent -= p * math.log(p)
    if normalize and len(pos) > 1:
        ent = ent / math.log(len(pos))
    return float(ent)


@dataclass(frozen=True, slots=True)
class PersistentEntropySnapshot:
    """Digest-stable persistent-entropy summary."""

    snapshot_id: str
    n_nodes: int
    n_bars: int
    persistent_entropy: float
    mean_lifetime: float
    max_lifetime: float
    normalized: bool = True
    claim_ceiling: str = "runtime_observation"
    arms_race_proved: bool = False
    digest: str = ""

    def __post_init__(self) -> None:
        sid = _refuse_banned_fragment(
            _as_str(self.snapshot_id, "snapshot_id"), "snapshot_id"
        )
        object.__setattr__(self, "snapshot_id", sid)
        object.__setattr__(self, "n_nodes", _as_int(self.n_nodes, "n_nodes", minimum=0))
        object.__setattr__(self, "n_bars", _as_int(self.n_bars, "n_bars", minimum=0))
        object.__setattr__(
            self,
            "persistent_entropy",
            float(require_finite_float("persistent_entropy", self.persistent_entropy)),
        )
        if self.persistent_entropy < 0.0:
            raise ConfigurationError("persistent_entropy must be >= 0.")
        object.__setattr__(
            self,
            "mean_lifetime",
            float(require_finite_float("mean_lifetime", self.mean_lifetime)),
        )
        object.__setattr__(
            self,
            "max_lifetime",
            float(require_finite_float("max_lifetime", self.max_lifetime)),
        )
        if not isinstance(self.normalized, bool):
            raise ConfigurationError("normalized must be a bool.")
        ceiling = _as_str(self.claim_ceiling, "claim_ceiling").casefold()
        if ceiling not in {"runtime_observation", "candidate_evidence"}:
            raise ConfigurationError(
                "claim_ceiling must be runtime_observation or candidate_evidence."
            )
        object.__setattr__(self, "claim_ceiling", ceiling)
        if self.arms_race_proved:
            raise ConfigurationError("refuses arms_race_proved=True.")
        object.__setattr__(self, "arms_race_proved", False)
        computed = canonical_digest(self._body(), prefix="pers_ent")
        object.__setattr__(
            self,
            "digest",
            _check_digest(self.digest, computed, "PersistentEntropySnapshot"),
        )

    def _body(self) -> dict[str, JsonValue]:
        return {
            "schema_version": SCHEMA_VERSION,
            "snapshot_id": self.snapshot_id,
            "n_nodes": self.n_nodes,
            "n_bars": self.n_bars,
            "persistent_entropy": self.persistent_entropy,
            "mean_lifetime": self.mean_lifetime,
            "max_lifetime": self.max_lifetime,
            "normalized": self.normalized,
            "claim_ceiling": self.claim_ceiling,
            "arms_race_proved": False,
        }

    def to_dict(self) -> dict[str, JsonValue]:
        return {**self._body(), "digest": self.digest}


def persistent_entropy_proxy(
    phenotype_map: PhenotypeMap,
    *,
    snapshot_id: str,
    normalize: bool = True,
    claim_ceiling: str = "runtime_observation",
) -> PersistentEntropySnapshot:
    """Compute persistent-entropy proxy from PhenotypeMap Jaccard distances."""

    if not isinstance(phenotype_map, PhenotypeMap):
        raise ConfigurationError("phenotype_map must be a PhenotypeMap.")
    if not isinstance(normalize, bool):
        raise ConfigurationError("normalize must be a bool.")
    n = len(phenotype_map.records)
    pairs = _pairwise_distances(phenotype_map)
    lifetimes = _h0_lifetimes(n, pairs)
    ent = persistent_entropy_from_lifetimes(lifetimes, normalize=normalize)
    mean_lt = (sum(lifetimes) / len(lifetimes)) if lifetimes else 0.0
    max_lt = max(lifetimes) if lifetimes else 0.0
    return PersistentEntropySnapshot(
        snapshot_id=snapshot_id,
        n_nodes=n,
        n_bars=len(lifetimes),
        persistent_entropy=ent,
        mean_lifetime=mean_lt,
        max_lifetime=max_lt,
        normalized=normalize,
        claim_ceiling=claim_ceiling,
    )
