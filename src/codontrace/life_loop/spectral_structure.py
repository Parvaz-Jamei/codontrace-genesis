"""INN-10 — Spectral Laplacian population-structure proxy on PhenotypeMap.

Affinity W_ij = Jaccard; combinatorial Laplacian L = D - W; return Fiedler
value and top-k smallest eigenvalues (Jacobi, pure Python). Inspired by
LAPSTRUCT / Spectral-GEM — observation only.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from codontrace._types import JsonValue
from codontrace.contracts.banned import BANNED_DOMAIN_TOKENS
from codontrace.errors import ConfigurationError
from codontrace.genesis.canonical import canonical_digest, require_finite_float
from codontrace.life_loop.match_rules import jaccard_overlap
from codontrace.life_loop.phenotype import PhenotypeMap

SCHEMA_VERSION = "life_loop_spectral_structure_v1"


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


def _jacobi_eigenvalues(matrix: list[list[float]], *, max_sweeps: int = 64) -> list[float]:
    """Classic Jacobi eigenvalue algorithm for small symmetric matrices."""

    n = len(matrix)
    if n == 0:
        return []
    a = [row[:] for row in matrix]
    for _ in range(max_sweeps):
        # find largest off-diagonal
        p = 0
        q = 1 if n > 1 else 0
        max_val = 0.0
        for i in range(n):
            for j in range(i + 1, n):
                if abs(a[i][j]) > max_val:
                    max_val = abs(a[i][j])
                    p, q = i, j
        if max_val < 1e-12:
            break
        app, aqq, apq = a[p][p], a[q][q], a[p][q]
        tau = (aqq - app) / (2.0 * apq) if apq != 0.0 else 0.0
        t = (
            1.0 / (abs(tau) + math.sqrt(1.0 + tau * tau))
            if tau != 0.0
            else 1.0
        )
        if tau < 0.0:
            t = -t
        c = 1.0 / math.sqrt(1.0 + t * t)
        s = t * c
        for i in range(n):
            if i in (p, q):
                continue
            aip, aiq = a[i][p], a[i][q]
            a[i][p] = a[p][i] = c * aip - s * aiq
            a[i][q] = a[q][i] = s * aip + c * aiq
        a[p][p] = app - t * apq
        a[q][q] = aqq + t * apq
        a[p][q] = a[q][p] = 0.0
    return sorted(a[i][i] for i in range(n))


def _laplacian(phenotype_map: PhenotypeMap) -> list[list[float]]:
    records = phenotype_map.records
    n = len(records)
    w = [[0.0] * n for _ in range(n)]
    deg = [0.0] * n
    for i in range(n):
        for j in range(i + 1, n):
            jac = jaccard_overlap(records[i].tag_set, records[j].tag_set)
            w[i][j] = w[j][i] = jac
            deg[i] += jac
            deg[j] += jac
    lap = [[0.0] * n for _ in range(n)]
    for i in range(n):
        for j in range(n):
            if i == j:
                lap[i][j] = deg[i]
            else:
                lap[i][j] = -w[i][j]
    return lap


@dataclass(frozen=True, slots=True)
class SpectralStructureSnapshot:
    """Digest-stable Laplacian spectrum fingerprint."""

    snapshot_id: str
    n_nodes: int
    fiedler_value: float
    eigenvalues: tuple[float, ...]
    spectral_gap: float
    claim_ceiling: str = "runtime_observation"
    arms_race_proved: bool = False
    digest: str = ""

    def __post_init__(self) -> None:
        sid = _refuse_banned_fragment(
            _as_str(self.snapshot_id, "snapshot_id"), "snapshot_id"
        )
        object.__setattr__(self, "snapshot_id", sid)
        object.__setattr__(self, "n_nodes", _as_int(self.n_nodes, "n_nodes", minimum=0))
        object.__setattr__(
            self,
            "fiedler_value",
            float(require_finite_float("fiedler_value", self.fiedler_value)),
        )
        ev = tuple(
            float(require_finite_float(f"eigenvalues[{i}]", v))
            for i, v in enumerate(self.eigenvalues)
        )
        object.__setattr__(self, "eigenvalues", ev)
        object.__setattr__(
            self,
            "spectral_gap",
            float(require_finite_float("spectral_gap", self.spectral_gap)),
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
        computed = canonical_digest(self._body(), prefix="spec_struct")
        object.__setattr__(
            self,
            "digest",
            _check_digest(self.digest, computed, "SpectralStructureSnapshot"),
        )

    def _body(self) -> dict[str, JsonValue]:
        return {
            "schema_version": SCHEMA_VERSION,
            "snapshot_id": self.snapshot_id,
            "n_nodes": self.n_nodes,
            "fiedler_value": self.fiedler_value,
            "eigenvalues": list(self.eigenvalues),
            "spectral_gap": self.spectral_gap,
            "claim_ceiling": self.claim_ceiling,
            "arms_race_proved": False,
        }

    def to_dict(self) -> dict[str, JsonValue]:
        return {**self._body(), "digest": self.digest}


def spectral_laplacian_structure(
    phenotype_map: PhenotypeMap,
    *,
    snapshot_id: str,
    top_k: int = 4,
    claim_ceiling: str = "runtime_observation",
) -> SpectralStructureSnapshot:
    """Return Fiedler value and smallest top_k Laplacian eigenvalues."""

    if not isinstance(phenotype_map, PhenotypeMap):
        raise ConfigurationError("phenotype_map must be a PhenotypeMap.")
    k = _as_int(top_k, "top_k", minimum=1)
    n = len(phenotype_map.records)
    if n == 0:
        return SpectralStructureSnapshot(
            snapshot_id=snapshot_id,
            n_nodes=0,
            fiedler_value=0.0,
            eigenvalues=(),
            spectral_gap=0.0,
            claim_ceiling=claim_ceiling,
        )
    lap = _laplacian(phenotype_map)
    ev = _jacobi_eigenvalues(lap)
    # numerical clamp near-zero algebraic connectivity floor
    ev = [max(0.0, round(x, 12)) for x in ev]
    fiedler = ev[1] if n >= 2 else 0.0
    kept = tuple(ev[: min(k, n)])
    gap = (ev[1] - ev[0]) if n >= 2 else 0.0
    return SpectralStructureSnapshot(
        snapshot_id=snapshot_id,
        n_nodes=n,
        fiedler_value=fiedler,
        eigenvalues=kept,
        spectral_gap=gap,
        claim_ceiling=claim_ceiling,
    )
