"""INN-08 — Mapper-lite cover / nerve graph on PhenotypeMap.

Lens = tag-count; cover bins; nerve edge when cross-bin Jaccard max >=
threshold. Lightweight stand-in for KeplerMapper — no deps.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from codontrace._types import JsonValue
from codontrace.contracts.banned import BANNED_DOMAIN_TOKENS
from codontrace.errors import ConfigurationError
from codontrace.genesis.canonical import canonical_digest, require_finite_float
from codontrace.life_loop.match_rules import jaccard_overlap
from codontrace.life_loop.phenotype import PhenotypeMap

SCHEMA_VERSION = "life_loop_mapper_cover_v1"


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


def _union_find_components(n: int, edges: Sequence[tuple[int, int]]) -> int:
    parent = list(range(n))

    def find(i: int) -> int:
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    def union(a: int, b: int) -> None:
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[rb] = ra

    for a, b in edges:
        union(a, b)
    return len({find(i) for i in range(n)}) if n else 0


@dataclass(frozen=True, slots=True)
class MapperCoverSnapshot:
    """Digest-stable Mapper-lite nerve summary."""

    snapshot_id: str
    n_members: int
    n_bins: int
    n_edges: int
    n_components: int
    overlap_threshold: float
    mean_bin_size: float
    claim_ceiling: str = "runtime_observation"
    arms_race_proved: bool = False
    digest: str = ""

    def __post_init__(self) -> None:
        sid = _refuse_banned_fragment(
            _as_str(self.snapshot_id, "snapshot_id"), "snapshot_id"
        )
        object.__setattr__(self, "snapshot_id", sid)
        object.__setattr__(
            self, "n_members", _as_int(self.n_members, "n_members", minimum=0)
        )
        object.__setattr__(self, "n_bins", _as_int(self.n_bins, "n_bins", minimum=0))
        object.__setattr__(self, "n_edges", _as_int(self.n_edges, "n_edges", minimum=0))
        object.__setattr__(
            self, "n_components", _as_int(self.n_components, "n_components", minimum=0)
        )
        object.__setattr__(
            self,
            "overlap_threshold",
            _unit_interval(self.overlap_threshold, "overlap_threshold"),
        )
        object.__setattr__(
            self,
            "mean_bin_size",
            float(require_finite_float("mean_bin_size", self.mean_bin_size)),
        )
        ceiling = _as_str(self.claim_ceiling, "claim_ceiling").casefold()
        if ceiling not in {"runtime_observation", "candidate_evidence"}:
            raise ConfigurationError(
                "claim_ceiling must be runtime_observation or candidate_evidence."
            )
        object.__setattr__(self, "claim_ceiling", ceiling)
        if self.arms_race_proved:
            raise ConfigurationError("refuses arms_race_proved=True.")
        object.__setattr__(self, "arms_race_proved", False)
        computed = canonical_digest(self._body(), prefix="mapper_cov")
        object.__setattr__(
            self, "digest", _check_digest(self.digest, computed, "MapperCoverSnapshot")
        )

    def _body(self) -> dict[str, JsonValue]:
        return {
            "schema_version": SCHEMA_VERSION,
            "snapshot_id": self.snapshot_id,
            "n_members": self.n_members,
            "n_bins": self.n_bins,
            "n_edges": self.n_edges,
            "n_components": self.n_components,
            "overlap_threshold": self.overlap_threshold,
            "mean_bin_size": self.mean_bin_size,
            "claim_ceiling": self.claim_ceiling,
            "arms_race_proved": False,
        }

    def to_dict(self) -> dict[str, JsonValue]:
        return {**self._body(), "digest": self.digest}


def mapper_cover_proxy(
    phenotype_map: PhenotypeMap,
    *,
    snapshot_id: str,
    overlap_threshold: float = 0.25,
    n_lens_bins: int = 4,
    claim_ceiling: str = "runtime_observation",
) -> MapperCoverSnapshot:
    """Bin members by tag-count lens; nerve edge if max cross-bin Jaccard >= thr."""

    if not isinstance(phenotype_map, PhenotypeMap):
        raise ConfigurationError("phenotype_map must be a PhenotypeMap.")
    thr = _unit_interval(overlap_threshold, "overlap_threshold")
    bins_n = _as_int(n_lens_bins, "n_lens_bins", minimum=1)
    records = phenotype_map.records
    n = len(records)
    if n == 0:
        return MapperCoverSnapshot(
            snapshot_id=snapshot_id,
            n_members=0,
            n_bins=0,
            n_edges=0,
            n_components=0,
            overlap_threshold=thr,
            mean_bin_size=0.0,
            claim_ceiling=claim_ceiling,
        )
    counts = [len(r.feature_tags) for r in records]
    cmin, cmax = min(counts), max(counts)
    span = max(1, cmax - cmin)
    bin_members: dict[int, list[int]] = {i: [] for i in range(bins_n)}
    for idx, c in enumerate(counts):
        frac = (c - cmin) / span
        b = min(bins_n - 1, int(frac * bins_n))
        bin_members[b].append(idx)
    active = [b for b in range(bins_n) if bin_members[b]]
    idx_of = {b: i for i, b in enumerate(active)}
    re_edges: list[tuple[int, int]] = []
    for a_i, ba in enumerate(active):
        for bb in active[a_i + 1 :]:
            max_jac = 0.0
            for i in bin_members[ba]:
                for j in bin_members[bb]:
                    jac = jaccard_overlap(records[i].tag_set, records[j].tag_set)
                    if jac > max_jac:
                        max_jac = jac
            if max_jac + 1e-15 >= thr:
                re_edges.append((idx_of[ba], idx_of[bb]))
    n_bins = len(active)
    n_edges = len(re_edges)
    n_comp = _union_find_components(n_bins, re_edges) if n_bins else 0
    mean_sz = (sum(len(bin_members[b]) for b in active) / n_bins) if n_bins else 0.0
    return MapperCoverSnapshot(
        snapshot_id=snapshot_id,
        n_members=n,
        n_bins=n_bins,
        n_edges=n_edges,
        n_components=n_comp,
        overlap_threshold=thr,
        mean_bin_size=mean_sz,
        claim_ceiling=claim_ceiling,
    )
