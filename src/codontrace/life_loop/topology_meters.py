"""INN-01 — Topology meters (TDA lite) on PhenotypeMap Jaccard graphs.

Refuse-safe β₀ (connected components) and β₁-proxy (cycle excess) at a
filtration threshold ε. Inspired by persistent-homology summaries of
reticulate / HGT structure — no external TDA library, no proved claims.
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

SCHEMA_VERSION = "life_loop_topology_meters_v1"


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
class TopologyMeterSnapshot:
    """Digest-stable β₀ / β₁-proxy at one filtration ε."""

    snapshot_id: str
    epsilon: float
    n_nodes: int
    n_edges: int
    beta0: int
    beta1_proxy: int
    mean_jaccard: float
    claim_ceiling: str = "runtime_observation"
    arms_race_proved: bool = False
    transition_proved: bool = False
    digest: str = ""

    def __post_init__(self) -> None:
        sid = _refuse_banned_fragment(
            _as_str(self.snapshot_id, "snapshot_id"), "snapshot_id"
        )
        object.__setattr__(self, "snapshot_id", sid)
        object.__setattr__(self, "epsilon", _unit_interval(self.epsilon, "epsilon"))
        object.__setattr__(self, "n_nodes", _as_int(self.n_nodes, "n_nodes", minimum=0))
        object.__setattr__(self, "n_edges", _as_int(self.n_edges, "n_edges", minimum=0))
        object.__setattr__(self, "beta0", _as_int(self.beta0, "beta0", minimum=0))
        object.__setattr__(
            self, "beta1_proxy", _as_int(self.beta1_proxy, "beta1_proxy", minimum=0)
        )
        object.__setattr__(
            self,
            "mean_jaccard",
            float(require_finite_float("mean_jaccard", self.mean_jaccard)),
        )
        ceiling = _as_str(self.claim_ceiling, "claim_ceiling").casefold()
        if ceiling not in {"runtime_observation", "candidate_evidence"}:
            raise ConfigurationError("claim_ceiling must be runtime_observation or candidate_evidence.")
        object.__setattr__(self, "claim_ceiling", ceiling)
        if self.arms_race_proved:
            raise ConfigurationError("refuses arms_race_proved=True.")
        if self.transition_proved:
            raise ConfigurationError("refuses transition_proved=True.")
        object.__setattr__(self, "arms_race_proved", False)
        object.__setattr__(self, "transition_proved", False)
        computed = canonical_digest(self._body(), prefix="topo_meter")
        object.__setattr__(
            self, "digest", _check_digest(self.digest, computed, "TopologyMeterSnapshot")
        )

    def _body(self) -> dict[str, JsonValue]:
        return {
            "schema_version": SCHEMA_VERSION,
            "snapshot_id": self.snapshot_id,
            "epsilon": self.epsilon,
            "n_nodes": self.n_nodes,
            "n_edges": self.n_edges,
            "beta0": self.beta0,
            "beta1_proxy": self.beta1_proxy,
            "mean_jaccard": self.mean_jaccard,
            "claim_ceiling": self.claim_ceiling,
            "arms_race_proved": False,
            "transition_proved": False,
        }

    def to_dict(self) -> dict[str, JsonValue]:
        return {**self._body(), "digest": self.digest}


def betti_proxy(
    phenotype_map: PhenotypeMap,
    *,
    snapshot_id: str,
    epsilon: float = 0.5,
    claim_ceiling: str = "runtime_observation",
) -> TopologyMeterSnapshot:
    """Build Jaccard graph at threshold ε; return β₀ and cycle-excess β₁ proxy.

    Edge (i,j) exists when jaccard(i,j) >= epsilon.
    β₁_proxy = max(0, n_edges - n_nodes + beta0)  (cyclomatic number on undirected graph).
    """

    if not isinstance(phenotype_map, PhenotypeMap):
        raise ConfigurationError("phenotype_map must be a PhenotypeMap.")
    eps = _unit_interval(epsilon, "epsilon")
    records = phenotype_map.records
    n = len(records)
    edges: list[tuple[int, int]] = []
    jacc_sum = 0.0
    pair_count = 0
    for i in range(n):
        for j in range(i + 1, n):
            jac = jaccard_overlap(records[i].tag_set, records[j].tag_set)
            jacc_sum += jac
            pair_count += 1
            if jac + 1e-15 >= eps:
                edges.append((i, j))
    beta0 = _union_find_components(n, edges) if n else 0
    n_edges = len(edges)
    beta1 = max(0, n_edges - n + beta0) if n else 0
    mean_j = (jacc_sum / pair_count) if pair_count else 0.0
    return TopologyMeterSnapshot(
        snapshot_id=snapshot_id,
        epsilon=eps,
        n_nodes=n,
        n_edges=n_edges,
        beta0=beta0,
        beta1_proxy=beta1,
        mean_jaccard=mean_j,
        claim_ceiling=claim_ceiling,
    )


def topology_continuum_structure(
    snapshots: Sequence[TopologyMeterSnapshot],
) -> dict[str, JsonValue]:
    """Summarize structure across ε (or cells): max β₁-proxy and span of β₀."""

    if not snapshots:
        raise ConfigurationError("snapshots must be non-empty.")
    beta1_vals = [s.beta1_proxy for s in snapshots]
    beta0_vals = [s.beta0 for s in snapshots]
    body: dict[str, JsonValue] = {
        "schema_version": SCHEMA_VERSION,
        "n_snapshots": len(snapshots),
        "max_beta1_proxy": max(beta1_vals),
        "min_beta0": min(beta0_vals),
        "max_beta0": max(beta0_vals),
        "mean_jaccard_max": max(s.mean_jaccard for s in snapshots),
        "arms_race_proved": False,
        "claim_status": "topology_structure_observation",
    }
    body["digest"] = canonical_digest(body, prefix="topo_cont")
    return body
