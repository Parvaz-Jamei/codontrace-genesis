"""Phase 15 — genome × (VT × spatial × continuum) factorial digests.

Crosses Wave-2 continuum knobs with Wave-3 SemanticGenome digests per cell.
Mutualism is never labeled success. Digital ClaimGate surface only; no
infection physics in ``engine.py``. Does not prove Red Queen, major transition,
human virulence optimization, phage therapy, vaccine effect, epidemic forecast,
BSL, or CRISPR identity.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from codontrace.errors import ConfigurationError
from codontrace.genesis.canonical import canonical_digest, canonical_payload
from codontrace.genesis.host_parasite_genome_zaman import _flip_codons, _genome_for_seed
from codontrace.genome import SemanticGenome

SCHEMA = "host_parasite_genome_vt_spatial_continuum_factorial_v1"
_SPATIAL = frozenset({"well_mixed", "local_neighborhood"})
_ALLOWED_CEILINGS = frozenset({"runtime_observation", "candidate_evidence"})


def _digest_body(body: Mapping[str, object]) -> str:
    return canonical_digest(canonical_payload(dict(body)))


def _require_seeds(seeds: Sequence[int]) -> tuple[int, ...]:
    if not seeds:
        raise ConfigurationError("seeds must be non-empty.")
    out: list[int] = []
    seen: set[int] = set()
    for index, seed in enumerate(seeds):
        if isinstance(seed, bool) or not isinstance(seed, int) or seed < 0:
            raise ConfigurationError(f"seeds[{index}] must be a non-negative int.")
        if seed in seen:
            raise ConfigurationError(f"duplicate seed {seed}.")
        seen.add(seed)
        out.append(seed)
    return tuple(out)


def _mean_hamming(genomes: Sequence[SemanticGenome]) -> float:
    if len(genomes) < 2:
        return 0.0
    total = 0.0
    pairs = 0
    for i, left in enumerate(genomes):
        left_c = left.to_codons()
        for right in genomes[i + 1 :]:
            right_c = right.to_codons()
            width = min(len(left_c), len(right_c))
            if width == 0:
                continue
            diffs = sum(1 for a, b in zip(left_c[:width], right_c[:width]) if a != b)
            total += diffs / width
            pairs += 1
    return total / pairs if pairs else 0.0


@dataclass(frozen=True, slots=True)
class GenomeFactorialCell:
    vertical_transmission_probability: float
    spatial_mode: str
    interaction_value: float
    host_genome_digest: str
    parasite_genome_digest: str
    host_unique: int
    parasite_unique: int
    mean_host_hamming: float
    mean_parasite_hamming: float
    continuum_score: float
    cell_digest: str

    def to_dict(self) -> dict[str, object]:
        return {
            "vertical_transmission_probability": self.vertical_transmission_probability,
            "spatial_mode": self.spatial_mode,
            "interaction_value": self.interaction_value,
            "host_genome_digest": self.host_genome_digest,
            "parasite_genome_digest": self.parasite_genome_digest,
            "host_unique": self.host_unique,
            "parasite_unique": self.parasite_unique,
            "mean_host_hamming": self.mean_host_hamming,
            "mean_parasite_hamming": self.mean_parasite_hamming,
            "continuum_score": self.continuum_score,
            "cell_digest": self.cell_digest,
            "mutualism_equals_success": False,
        }


@dataclass(frozen=True, slots=True)
class GenomeFactorialResult:
    schema: str
    seeds: tuple[int, ...]
    vt_levels: tuple[float, ...]
    spatial_modes: tuple[str, ...]
    interaction_values: tuple[float, ...]
    cells: tuple[GenomeFactorialCell, ...]
    claim_ceiling: str
    cells_are_distinct: bool
    mutualism_equals_success: bool
    red_queen_proved: bool
    major_transition_proved: bool

    def to_dict(self) -> dict[str, object]:
        cells = [cell.to_dict() for cell in self.cells]
        cell_digests = {
            f"vt{cell.vertical_transmission_probability}|{cell.spatial_mode}|iv{cell.interaction_value}": cell.cell_digest
            for cell in self.cells
        }
        body: dict[str, object] = {
            "schema": self.schema,
            "seeds": list(self.seeds),
            "vt_levels": list(self.vt_levels),
            "spatial_modes": list(self.spatial_modes),
            "interaction_values": list(self.interaction_values),
            "cells": cells,
            "cell_digests": cell_digests,
            "claim_ceiling": self.claim_ceiling,
            "cells_are_distinct": self.cells_are_distinct,
            "mutualism_equals_success": False,
            "red_queen_proved": False,
            "major_transition_proved": False,
            "raises_claim_ladder": False,
            "engine_infection_physics": "not_in_engine_core",
            "domain_profile": "host_parasite",
            "cross_wave": "wave2_continuum_x_wave3_genomes",
        }
        body["factorial_digest"] = _digest_body(
            {k: body[k] for k in body if k not in {"factorial_digest", "digest"}}
        )
        body["digest"] = body["factorial_digest"]
        return body


def _run_cell(
    *,
    seeds: Sequence[int],
    vt: float,
    spatial_mode: str,
    interaction_value: float,
) -> GenomeFactorialCell:
    """Genome observables modulated by VT, spatial mode, and interaction value."""

    hosts: list[SemanticGenome] = []
    parasites: list[SemanticGenome] = []
    for seed in seeds:
        host = _genome_for_seed(seed, f"host_vt{vt}_{spatial_mode}_{interaction_value}")
        parasite = _genome_for_seed(seed, f"parasite_vt{vt}_{spatial_mode}_{interaction_value}")
        # Continuum antagonism (<0) pressures more host flips; mutualism fewer.
        host_flips = 2 + int(max(0.0, -interaction_value) * 3)
        host = _flip_codons(host, seed, step=1, flips=host_flips)
        # VT copies parasite trajectory into host-adjacent lineage (co-copy analogue).
        if vt >= 0.5:
            parasite = _flip_codons(parasite, seed, step=2, flips=1)
            # Co-copy: host also inherits a parasite-window flip fingerprint.
            host = _flip_codons(host, seed + 17, step=3, flips=1)
        else:
            parasite = _flip_codons(parasite, seed, step=2, flips=2)
        # Local neighborhood constrains parasite exploration vs well_mixed.
        if spatial_mode == "local_neighborhood":
            parasites.append(parasite)
            parasites.append(parasite)  # clone-heavy local seat
        else:
            parasites.append(parasite)
            parasites.append(_flip_codons(parasite, seed, step=4, flips=2))
        hosts.append(host)
        hosts.append(_flip_codons(host, seed, step=5, flips=1 if vt < 0.5 else 2))

    host_digests = sorted({g.digest() for g in hosts})
    parasite_digests = sorted({g.digest() for g in parasites})
    # Continuum score: antagonism drains; mutualism raises score but never success.
    continuum_score = round(interaction_value * (0.5 + 0.5 * vt) - (0.1 if spatial_mode == "local_neighborhood" else 0.0), 10)
    body = {
        "vertical_transmission_probability": vt,
        "spatial_mode": spatial_mode,
        "interaction_value": interaction_value,
        "host_genome_digests": host_digests,
        "parasite_genome_digests": parasite_digests,
        "host_unique": len(host_digests),
        "parasite_unique": len(parasite_digests),
        "mean_host_hamming": round(_mean_hamming(hosts), 10),
        "mean_parasite_hamming": round(_mean_hamming(parasites), 10),
        "continuum_score": continuum_score,
        "mutualism_equals_success": False,
        "seeds": list(seeds),
    }
    return GenomeFactorialCell(
        vertical_transmission_probability=vt,
        spatial_mode=spatial_mode,
        interaction_value=interaction_value,
        host_genome_digest=_digest_body({"hosts": host_digests}),
        parasite_genome_digest=_digest_body({"parasites": parasite_digests}),
        host_unique=len(host_digests),
        parasite_unique=len(parasite_digests),
        mean_host_hamming=float(body["mean_host_hamming"]),
        mean_parasite_hamming=float(body["mean_parasite_hamming"]),
        continuum_score=continuum_score,
        cell_digest=_digest_body(body),
    )


def run_genome_vt_spatial_continuum_factorial(
    *,
    seeds: Sequence[int],
    vt_levels: Sequence[float] = (0.0, 1.0),
    spatial_modes: Sequence[str] = ("well_mixed", "local_neighborhood"),
    interaction_values: Sequence[float] = (-1.0, 1.0),
    request_claim_ceiling: str = "runtime_observation",
) -> GenomeFactorialResult:
    """Factorial grid with per-cell host/parasite genome digests."""

    seed_tuple = _require_seeds(seeds)
    if not vt_levels:
        raise ConfigurationError("vt_levels must be non-empty.")
    if not spatial_modes:
        raise ConfigurationError("spatial_modes must be non-empty.")
    if not interaction_values:
        raise ConfigurationError("interaction_values must be non-empty.")
    vt_tuple: list[float] = []
    for index, raw in enumerate(vt_levels):
        value = float(raw)
        if value != value or value < 0.0 or value > 1.0:
            raise ConfigurationError(f"vt_levels[{index}] must be in [0, 1].")
        vt_tuple.append(value)
    spatial_tuple: list[str] = []
    for index, raw in enumerate(spatial_modes):
        if not isinstance(raw, str) or not raw.strip():
            raise ConfigurationError(f"spatial_modes[{index}] must be a non-empty string.")
        key = raw.strip().lower()
        if key not in _SPATIAL:
            raise ConfigurationError(
                f"spatial_modes[{index}] must be one of {sorted(_SPATIAL)}."
            )
        spatial_tuple.append(key)
    iv_tuple: list[float] = []
    for index, raw in enumerate(interaction_values):
        value = float(raw)
        if value != value or value < -1.0 or value > 1.0:
            raise ConfigurationError(f"interaction_values[{index}] must be in [-1, +1].")
        iv_tuple.append(value)
    ceiling = str(request_claim_ceiling).strip().lower()
    if ceiling not in _ALLOWED_CEILINGS:
        raise ConfigurationError(
            "request_claim_ceiling must be runtime_observation or candidate_evidence."
        )

    cells = [
        _run_cell(
            seeds=seed_tuple,
            vt=vt,
            spatial_mode=spatial,
            interaction_value=iv,
        )
        for vt in vt_tuple
        for spatial in spatial_tuple
        for iv in iv_tuple
    ]
    digests = {cell.cell_digest for cell in cells}
    distinct = len(digests) == len(cells) and len(cells) >= 2
    if ceiling == "candidate_evidence" and not distinct:
        raise ConfigurationError(
            "candidate_evidence refused: genome×VT×spatial×continuum cells lack digest contrast."
        )
    return GenomeFactorialResult(
        schema=SCHEMA,
        seeds=seed_tuple,
        vt_levels=tuple(vt_tuple),
        spatial_modes=tuple(spatial_tuple),
        interaction_values=tuple(iv_tuple),
        cells=tuple(cells),
        claim_ceiling=ceiling if distinct or ceiling == "runtime_observation" else "runtime_observation",
        cells_are_distinct=distinct,
        mutualism_equals_success=False,
        red_queen_proved=False,
        major_transition_proved=False,
    )


__all__ = [
    "GenomeFactorialCell",
    "GenomeFactorialResult",
    "SCHEMA",
    "run_genome_vt_spatial_continuum_factorial",
]
