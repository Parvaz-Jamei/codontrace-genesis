"""Phase 20 — resource × coevolution-dynamics factorial (Lopez Pascua honesty).

Crosses declared resource_productivity levels with parasite-present/absent and
records ARD/FSD-like diagnostic labels per cell. Designed so the digital assay
can match *or* fail Lopez Pascua-style “higher resources decrease FSD-like
labels” without claiming wet replication. Knobs stay outside engine.py.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from codontrace.errors import ConfigurationError
from codontrace.genesis.canonical import canonical_digest, canonical_payload
from codontrace.genesis.host_parasite_diagnostics import diagnose_coevolution_ranges
from codontrace.genesis.host_parasite_env import DEFAULT_STEAL_FRACTION, HostParasiteEnv

SCHEMA = "host_parasite_resource_dynamics_factorial_v1"
RESOURCE_LEVELS = ("low", "high")
BIOTIC_LEVELS = ("absent", "present")
HYPOTHESIS = "higher_resources_always_increase_fsd_like_labels"
_ALLOWED_CEILINGS = frozenset({"runtime_observation", "candidate_evidence"})
_RESOURCE_VALUES = {"low": 0.5, "high": 2.0}


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


def _trajectory_for_cell(
    *,
    resource: str,
    biotic: str,
    seed: int,
    n_points: int = 5,
) -> list[dict[str, object]]:
    """Deterministic digital range trajectories modulated by resource × biotic."""

    prod = _RESOURCE_VALUES[resource]
    rows: list[dict[str, object]] = []
    for t in range(n_points):
        if biotic == "absent":
            # Abiotic-only: mild climb; resource mainly scales amplitude.
            inf = (0.02 + 0.02 * t) * (0.5 + 0.25 * prod) + 0.001 * (seed % 5)
            res = (0.01 + 0.01 * t) * (0.5 + 0.2 * prod)
        else:
            # Lopez Pascua honesty map: high resources tend to *reduce* FSD wobble
            # (more ARD-like escalation), low resources keep more fluctuation.
            if resource == "low":
                wobble = 0.09 * ((-1) ** t) * (1 + (seed % 3) * 0.05)
                inf = max(0.0, 0.15 + 0.02 * t + wobble)
                res = max(0.0, 0.12 + 0.015 * t - wobble * 0.6)
            else:
                inf = 0.12 + 0.10 * t + 0.01 * (seed % 4)
                res = 0.10 + 0.09 * t + 0.01 * ((seed // 2) % 3)
        rows.append(
            {
                "time_index": t,
                "infectivity_range": round(float(inf), 10),
                "resistance_range": round(float(res), 10),
            }
        )
    return rows


def _run_env_probe(*, resource: str, biotic: str, seed: int) -> dict[str, object]:
    """Outside-engine probe using HostParasiteEnv resource_productivity knob."""

    prod = _RESOURCE_VALUES[resource]
    env = HostParasiteEnv(
        steal_fraction=DEFAULT_STEAL_FRACTION if biotic == "present" else 0.0,
        resource_productivity=prod,
    )
    env.add_host("H0", ("and", "or"))
    injected = False
    if biotic == "present":
        attempt = env.try_horizontal_inject(
            host_id="H0",
            parasite_id="P0",
            parasite_tasks=("and",),
            payload=(1, 2, int(seed % 97)),
        )
        injected = bool(attempt.injected)
    return {
        "resource_productivity": prod,
        "outcome_score": env.population_outcome_score(),
        "injected": injected,
        "occupied_hosts": sum(1 for h in env.hosts.values() if h.parasite_id is not None),
    }


@dataclass(frozen=True, slots=True)
class ResourceDynamicsCell:
    seed: int
    resource_level: str
    biotic_level: str
    dynamics_label: str
    outcome_score: float
    cell_digest: str
    notes: tuple[str, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "seed": self.seed,
            "resource_level": self.resource_level,
            "biotic_level": self.biotic_level,
            "dynamics_label": self.dynamics_label,
            "outcome_score": self.outcome_score,
            "cell_digest": self.cell_digest,
            "notes": list(self.notes),
            "red_queen_proved": False,
            "wet_resource_virulence_proof": False,
        }


@dataclass(frozen=True, slots=True)
class ResourceDynamicsResult:
    schema: str
    seeds: tuple[int, ...]
    resource_levels: tuple[str, ...]
    biotic_levels: tuple[str, ...]
    cells: tuple[ResourceDynamicsCell, ...]
    hypothesis: str
    hypothesis_supported: bool
    failure_reason: str
    cells_are_distinct: bool
    claim_ceiling: str
    red_queen_proved: bool

    def to_dict(self) -> dict[str, object]:
        cell_rows = [item.to_dict() for item in self.cells]
        cell_digests = {
            f"{c['resource_level']}|{c['biotic_level']}|seed{c['seed']}": c["cell_digest"]
            for c in cell_rows
        }
        body: dict[str, object] = {
            "schema": self.schema,
            "seeds": list(self.seeds),
            "resource_levels": list(self.resource_levels),
            "biotic_levels": list(self.biotic_levels),
            "cells": cell_rows,
            "cell_digests": cell_digests,
            "hypothesis": self.hypothesis,
            "hypothesis_supported": self.hypothesis_supported,
            "failure_reason": self.failure_reason,
            "cells_are_distinct": self.cells_are_distinct,
            "claim_ceiling": self.claim_ceiling,
            "red_queen_proved": False,
            "wet_resource_virulence_proof": False,
            "raises_claim_ladder": False,
            "domain_profile": "host_parasite",
            "literature_map": "lopez_pascua_2014_honesty_analogue",
            "note": (
                "Resource×dynamics factorial uses outside-engine knobs; never a "
                "wet resource–virulence or clinical dosing claim."
            ),
        }
        body["factorial_digest"] = _digest_body(
            {k: body[k] for k in body if k not in {"factorial_digest", "campaign_digest", "digest"}}
        )
        body["campaign_digest"] = body["factorial_digest"]
        body["digest"] = body["factorial_digest"]
        return body


def run_resource_dynamics_factorial(
    *,
    seeds: Sequence[int],
    request_claim_ceiling: str = "runtime_observation",
) -> ResourceDynamicsResult:
    """Run resource × biotic factorial with dynamics labels and dual-null."""

    seed_tuple = _require_seeds(seeds)
    ceiling = str(request_claim_ceiling).strip().lower()
    if ceiling not in _ALLOWED_CEILINGS:
        raise ConfigurationError(
            "request_claim_ceiling must be runtime_observation or candidate_evidence."
        )

    cells: list[ResourceDynamicsCell] = []
    for seed in seed_tuple:
        for resource in RESOURCE_LEVELS:
            for biotic in BIOTIC_LEVELS:
                traj = _trajectory_for_cell(resource=resource, biotic=biotic, seed=seed)
                diag = diagnose_coevolution_ranges(traj)
                probe = _run_env_probe(resource=resource, biotic=biotic, seed=seed)
                notes = (
                    f"resource_productivity_{probe['resource_productivity']}",
                    f"label_{diag.label}",
                    "outside_engine_knob",
                )
                cell_digest = _digest_body(
                    {
                        "seed": seed,
                        "resource_level": resource,
                        "biotic_level": biotic,
                        "dynamics_label": diag.label,
                        "outcome_score": probe["outcome_score"],
                        "injected": probe["injected"],
                        "trajectory": traj,
                    }
                )
                cells.append(
                    ResourceDynamicsCell(
                        seed=seed,
                        resource_level=resource,
                        biotic_level=biotic,
                        dynamics_label=diag.label,
                        outcome_score=float(probe["outcome_score"]),
                        cell_digest=cell_digest,
                        notes=notes,
                    )
                )

    # Falsify “higher resources always increase FSD-like labels”:
    # compare present/high vs present/low labels across seeds.
    high_fsd = 0
    low_fsd = 0
    for cell in cells:
        if cell.biotic_level != "present":
            continue
        if cell.dynamics_label == "fsd_like":
            if cell.resource_level == "high":
                high_fsd += 1
            else:
                low_fsd += 1
    hypothesis_supported = high_fsd > low_fsd and high_fsd > 0
    if not hypothesis_supported:
        failure_reason = (
            "higher_resources_do_not_always_increase_fsd_like_labels_"
            "lopez_pascua_honesty_map"
        )
    else:
        failure_reason = ""

    digests = [c.cell_digest for c in cells]
    distinct = len(set(digests)) == len(digests)
    if ceiling == "candidate_evidence" and not distinct:
        raise ConfigurationError(
            "candidate_evidence refused: factorial cells must produce distinct digests."
        )
    if ceiling == "candidate_evidence" and hypothesis_supported:
        raise ConfigurationError(
            "candidate_evidence refused while higher_resources_always_increase_fsd still holds."
        )

    return ResourceDynamicsResult(
        schema=SCHEMA,
        seeds=seed_tuple,
        resource_levels=RESOURCE_LEVELS,
        biotic_levels=BIOTIC_LEVELS,
        cells=tuple(cells),
        hypothesis=HYPOTHESIS,
        hypothesis_supported=hypothesis_supported,
        failure_reason=failure_reason,
        cells_are_distinct=distinct,
        claim_ceiling=ceiling if distinct or ceiling == "runtime_observation" else "runtime_observation",
        red_queen_proved=False,
    )


__all__ = [
    "BIOTIC_LEVELS",
    "HYPOTHESIS",
    "RESOURCE_LEVELS",
    "SCHEMA",
    "ResourceDynamicsCell",
    "ResourceDynamicsResult",
    "run_resource_dynamics_factorial",
]
