"""Parasitism–mutualism continuum + VT × spatial factorial (Phase 8).

Interaction value in [-1, +1] is owned by ``HostParasiteEnv`` (antagonism →
mutualism). This module runs a factorial campaign over
``vertical_transmission_probability`` × ``spatial_mode`` with canonical
digests. Mutualism is never narrated as success. Does not modify
``engine.py``. Does not prove Red Queen, major transition, CRISPR identity,
phage therapy, vaccine effect, epidemic forecast, or BSL.
"""

from __future__ import annotations

import hashlib
from collections.abc import Sequence
from dataclasses import dataclass

from codontrace.errors import ConfigurationError
from codontrace.genesis.canonical import canonical_digest, canonical_payload
from codontrace.genesis.host_parasite_env import (
    DEFAULT_STEAL_FRACTION,
    HostParasiteEnv,
)

_SPATIAL_MODES = frozenset({"well_mixed", "local_neighborhood"})


def _digest_body(body: dict[str, object]) -> str:
    return canonical_digest(canonical_payload(body))


def _seed_unit(seed: int, salt: str) -> float:
    digest = hashlib.sha256(f"{int(seed)}|{salt}".encode()).digest()
    return digest[0] / 255.0


@dataclass(frozen=True, slots=True)
class ContinuumCellResult:
    vertical_transmission_probability: float
    spatial_mode: str
    interaction_value: float
    mean_score: float
    injected_or_transmitted: int
    host_count: int
    cell_digest: str

    def to_dict(self) -> dict[str, object]:
        return {
            "vertical_transmission_probability": self.vertical_transmission_probability,
            "spatial_mode": self.spatial_mode,
            "interaction_value": self.interaction_value,
            "mean_score": self.mean_score,
            "injected_or_transmitted": self.injected_or_transmitted,
            "host_count": self.host_count,
            "cell_digest": self.cell_digest,
            "mutualism_equals_success": False,
        }


@dataclass(frozen=True, slots=True)
class ContinuumFactorialResult:
    schema: str
    seeds: tuple[int, ...]
    vt_levels: tuple[float, ...]
    spatial_modes: tuple[str, ...]
    interaction_value: float
    steal_fraction: float
    cells: tuple[ContinuumCellResult, ...]
    claim_ceiling: str
    mutualism_equals_success: bool
    red_queen_proved: bool

    def to_dict(self) -> dict[str, object]:
        body: dict[str, object] = {
            "schema": self.schema,
            "seeds": list(self.seeds),
            "vt_levels": list(self.vt_levels),
            "spatial_modes": list(self.spatial_modes),
            "interaction_value": self.interaction_value,
            "steal_fraction": self.steal_fraction,
            "cells": [cell.to_dict() for cell in self.cells],
            "cell_digests": {
                f"vt{cell.vertical_transmission_probability}|{cell.spatial_mode}": cell.cell_digest
                for cell in self.cells
            },
            "claim_ceiling": self.claim_ceiling,
            "mutualism_equals_success": self.mutualism_equals_success,
            "red_queen_proved": self.red_queen_proved,
            "interaction_continuum": "antagonism_to_mutualism",
            "raises_claim_ladder": False,
            "engine_infection_physics": "not_in_engine_core",
        }
        body["factorial_digest"] = _digest_body(
            {k: body[k] for k in body if k not in {"factorial_digest", "digest"}}
        )
        body["digest"] = body["factorial_digest"]
        return body


def _require_seeds(seeds: Sequence[int]) -> tuple[int, ...]:
    if not seeds:
        raise ConfigurationError("continuum factorial requires at least one seed.")
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


def _run_cell(
    *,
    seed: int,
    vt: float,
    spatial_mode: str,
    interaction_value: float,
    steal_fraction: float,
) -> ContinuumCellResult:
    """One VT × spatial cell: seed parent, optional vertical child, local/well inject."""

    # Shared topology: H0 source, H1 neighbor, H_far distant (Chebyshev > 1).
    # Local mode blocks H_far inject; well_mixed allows it — spatial factor bites.
    if spatial_mode == "local_neighborhood":
        env = HostParasiteEnv(
            steal_fraction=steal_fraction,
            transmission_mode="mixed",
            vertical_transmission_probability=vt,
            spatial_mode="local_neighborhood",
            grid_rows=3,
            grid_cols=3,
            interaction_value=interaction_value,
        )
        env.add_host("H0", ("and", "or"), row=0, col=0)
        env.add_host("H1", ("and", "nand"), row=0, col=1)
        env.add_host("H_far", ("and", "xor"), row=2, col=2)
        env.seed_parasite_seat(
            host_id="H0",
            parasite_id="P0",
            parasite_tasks=("and",),
            payload=(1, 2, int(seed % 251)),
        )
        draw = _seed_unit(seed, f"vt_draw_{vt}_{spatial_mode}")
        env.replicate_host(
            parent_id="H0",
            child_id="H2",
            draw=draw,
            child_row=1,
            child_col=0,
        )
        near = env.try_local_inject(
            source_host_id="H0",
            target_host_id="H1",
            parasite_id="P_near",
            parasite_tasks=("and",),
            payload=(3, 4),
        )
        far = env.try_local_inject(
            source_host_id="H0",
            target_host_id="H_far",
            parasite_id="P_far",
            parasite_tasks=("and",),
            payload=(5, 6),
        )
        transmitted = sum(
            1 for event in env.replication_events if event.get("transmitted")
        )
        injected = int(near.injected) + int(far.injected)
        score = env.population_outcome_score()
        host_count = len(env.hosts)
        events = transmitted + injected
    else:
        env = HostParasiteEnv(
            steal_fraction=steal_fraction,
            transmission_mode="mixed",
            vertical_transmission_probability=vt,
            spatial_mode="well_mixed",
            interaction_value=interaction_value,
        )
        env.add_host("H0", ("and", "or"), row=0, col=0)
        env.add_host("H1", ("and", "nand"), row=0, col=1)
        env.add_host("H_far", ("and", "xor"), row=2, col=2)
        env.seed_parasite_seat(
            host_id="H0",
            parasite_id="P0",
            parasite_tasks=("and",),
            payload=(1, 2, int(seed % 251)),
        )
        draw = _seed_unit(seed, f"vt_draw_{vt}_{spatial_mode}")
        env.replicate_host(parent_id="H0", child_id="H2", draw=draw)
        near = env.try_local_inject(
            source_host_id="H0",
            target_host_id="H1",
            parasite_id="P_near",
            parasite_tasks=("and",),
            payload=(3, 4),
        )
        far = env.try_local_inject(
            source_host_id="H0",
            target_host_id="H_far",
            parasite_id="P_far",
            parasite_tasks=("and",),
            payload=(5, 6),
        )
        transmitted = sum(
            1 for event in env.replication_events if event.get("transmitted")
        )
        injected = int(near.injected) + int(far.injected)
        score = env.population_outcome_score()
        host_count = len(env.hosts)
        events = transmitted + injected

    body = {
        "seed": seed,
        "vertical_transmission_probability": vt,
        "spatial_mode": spatial_mode,
        "interaction_value": interaction_value,
        "mean_score": score,
        "injected_or_transmitted": events,
        "host_count": host_count,
        "snapshot_digest": env.snapshot()["digest"],
        "mutualism_equals_success": False,
    }
    return ContinuumCellResult(
        vertical_transmission_probability=vt,
        spatial_mode=spatial_mode,
        interaction_value=interaction_value,
        mean_score=score,
        injected_or_transmitted=events,
        host_count=host_count,
        cell_digest=_digest_body(body),
    )


def run_vt_spatial_factorial(
    *,
    seeds: Sequence[int],
    vt_levels: Sequence[float] = (0.0, 1.0),
    spatial_modes: Sequence[str] = ("well_mixed", "local_neighborhood"),
    interaction_value: float = -1.0,
    steal_fraction: float = DEFAULT_STEAL_FRACTION,
    request_claim_ceiling: str = "runtime_observation",
) -> ContinuumFactorialResult:
    """Factorial over vertical_transmission_probability × spatial_mode.

    Cells aggregate mean scores across seeds. Digests must differ across the
    grid when VT or spatial mode changes under infection. Mutualism
    (``interaction_value > 0``) is recorded honestly and never labeled success.
    """

    seed_tuple = _require_seeds(seeds)
    if not vt_levels:
        raise ConfigurationError("vt_levels must be non-empty.")
    if not spatial_modes:
        raise ConfigurationError("spatial_modes must be non-empty.")
    vt_tuple: list[float] = []
    for index, raw in enumerate(vt_levels):
        number = float(raw)
        if number != number or number < 0.0 or number > 1.0:
            raise ConfigurationError(f"vt_levels[{index}] must be in [0, 1].")
        vt_tuple.append(number)
    spatial_tuple: list[str] = []
    for index, raw in enumerate(spatial_modes):
        if not isinstance(raw, str) or not raw.strip():
            raise ConfigurationError(f"spatial_modes[{index}] must be a non-empty string.")
        key = raw.strip().lower()
        if key not in _SPATIAL_MODES:
            raise ConfigurationError(
                f"spatial_modes[{index}] must be one of {sorted(_SPATIAL_MODES)}."
            )
        spatial_tuple.append(key)
    iv = float(interaction_value)
    if iv != iv or iv < -1.0 or iv > 1.0:
        raise ConfigurationError("interaction_value must be in [-1, +1].")
    steal = float(steal_fraction)
    if steal != steal or steal < 0.0 or steal > 1.0:
        raise ConfigurationError("steal_fraction must be in [0, 1].")
    ceiling = str(request_claim_ceiling).strip().lower()
    if ceiling not in {"runtime_observation", "candidate_evidence"}:
        raise ConfigurationError(
            "request_claim_ceiling must be runtime_observation or candidate_evidence."
        )

    cells: list[ContinuumCellResult] = []
    for vt in vt_tuple:
        for spatial in spatial_tuple:
            per_seed: list[ContinuumCellResult] = [
                _run_cell(
                    seed=seed,
                    vt=vt,
                    spatial_mode=spatial,
                    interaction_value=iv,
                    steal_fraction=steal,
                )
                for seed in seed_tuple
            ]
            mean_score = round(
                sum(item.mean_score for item in per_seed) / len(per_seed), 10
            )
            events = sum(item.injected_or_transmitted for item in per_seed)
            host_count = per_seed[0].host_count
            aggregate = {
                "vertical_transmission_probability": vt,
                "spatial_mode": spatial,
                "interaction_value": iv,
                "mean_score": mean_score,
                "injected_or_transmitted": events,
                "host_count": host_count,
                "seed_cell_digests": [item.cell_digest for item in per_seed],
                "mutualism_equals_success": False,
            }
            cells.append(
                ContinuumCellResult(
                    vertical_transmission_probability=vt,
                    spatial_mode=spatial,
                    interaction_value=iv,
                    mean_score=mean_score,
                    injected_or_transmitted=events,
                    host_count=host_count,
                    cell_digest=_digest_body(aggregate),
                )
            )

    digests = {cell.cell_digest for cell in cells}
    if ceiling == "candidate_evidence" and len(digests) < 2:
        raise ConfigurationError(
            "candidate_evidence refused: VT×spatial cells lack digest contrast."
        )
    return ContinuumFactorialResult(
        schema="host_parasite_vt_spatial_factorial_v1",
        seeds=seed_tuple,
        vt_levels=tuple(vt_tuple),
        spatial_modes=tuple(spatial_tuple),
        interaction_value=iv,
        steal_fraction=steal,
        cells=tuple(cells),
        claim_ceiling=ceiling,
        mutualism_equals_success=False,
        red_queen_proved=False,
    )


__all__ = [
    "ContinuumCellResult",
    "ContinuumFactorialResult",
    "run_vt_spatial_factorial",
]
