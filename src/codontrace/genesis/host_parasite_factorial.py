"""Abiotic × biotic factorial campaign template + interaction network digests.

Fortuna 2021 opportunity / Scanlan–Buckling constraint humility: factorial
cells separate abiotic productivity from biotic infection so one-sided
“parasites raise complexity” stories can be challenged. Adaptive-origin gate
(Fortuna et al. 2017 Phil Trans B analogy) is a declared digital control only.

Does not modify engine.py. Does not prove Red Queen, major transition, CRISPR
identity, phage therapy, vaccine effect, epidemic forecast, or BSL.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from codontrace.errors import ConfigurationError
from codontrace.genesis.canonical import canonical_digest, canonical_payload
from codontrace.genesis.host_parasite_campaign import run_host_parasite_campaign

_ABIOTIC_LEVELS = frozenset({"low", "high"})
_BIOTIC_LEVELS = frozenset({"absent", "present"})


@dataclass(frozen=True, slots=True)
class AdaptiveOriginGate:
    """Declared digital control: allow vs suppress exaptation-like task gains."""

    allow_exaptation_like_gains: bool
    note: str

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": "host_parasite_adaptive_origin_gate_v1",
            "allow_exaptation_like_gains": self.allow_exaptation_like_gains,
            "note": self.note,
            "wet_claim": False,
            "raises_claim_ladder": False,
            "source": "fortuna_et_al_2017_digital_control_only",
        }


def adaptive_origin_gate(*, allow_exaptation_like_gains: bool) -> AdaptiveOriginGate:
    """Build the Fortuna-2017-inspired adaptive-origin gate (digital only)."""

    if allow_exaptation_like_gains:
        note = (
            "Exaptation-like task gains allowed as a declared digital control; "
            "not a wet adaptive-origin proof."
        )
    else:
        note = (
            "Exaptation-like task gains suppressed as a declared digital control; "
            "not a wet adaptive-origin proof."
        )
    return AdaptiveOriginGate(bool(allow_exaptation_like_gains), note)


@dataclass(frozen=True, slots=True)
class InteractionNetworkSummary:
    """Host–parasite interaction network summary with canonical digest."""

    edge_count: int
    host_count: int
    parasite_count: int
    mean_edge_strength: float
    strength_heterogeneity: float
    edges: tuple[dict[str, object], ...]

    def to_dict(self) -> dict[str, object]:
        body: dict[str, object] = {
            "schema": "host_parasite_interaction_network_v1",
            "edge_count": self.edge_count,
            "host_count": self.host_count,
            "parasite_count": self.parasite_count,
            "mean_edge_strength": self.mean_edge_strength,
            "strength_heterogeneity": self.strength_heterogeneity,
            "edges": list(self.edges),
            "raises_claim_ladder": False,
            "red_queen_proved": False,
        }
        body["digest"] = canonical_digest(
            canonical_payload({k: body[k] for k in body if k != "digest"})
        )
        return body


def summarize_interaction_network(
    edges: Sequence[Mapping[str, object]],
) -> InteractionNetworkSummary:
    """Summarize directed host←parasite edges with strength heterogeneity."""

    if not isinstance(edges, Sequence) or isinstance(edges, (str, bytes)):
        raise ConfigurationError("edges must be a sequence of mappings.")
    parsed: list[dict[str, object]] = []
    hosts: set[str] = set()
    parasites: set[str] = set()
    strengths: list[float] = []
    for index, raw in enumerate(edges):
        if not isinstance(raw, Mapping):
            raise ConfigurationError(f"edges[{index}] must be a mapping.")
        host = raw.get("host_id")
        parasite = raw.get("parasite_id")
        strength = raw.get("strength", 1.0)
        if not isinstance(host, str) or not host.strip():
            raise ConfigurationError(f"edges[{index}].host_id is required.")
        if not isinstance(parasite, str) or not parasite.strip():
            raise ConfigurationError(f"edges[{index}].parasite_id is required.")
        number = float(strength)
        if number != number or number in (float("inf"), float("-inf")) or number < 0.0:
            raise ConfigurationError(f"edges[{index}].strength must be finite and >= 0.")
        hosts.add(host.strip())
        parasites.add(parasite.strip())
        strengths.append(number)
        parsed.append(
            {
                "host_id": host.strip(),
                "parasite_id": parasite.strip(),
                "strength": number,
            }
        )
    if not parsed:
        mean = 0.0
        hetero = 0.0
    else:
        mean = round(sum(strengths) / len(strengths), 10)
        if len(strengths) < 2:
            hetero = 0.0
        else:
            var = sum((value - mean) ** 2 for value in strengths) / (len(strengths) - 1)
            hetero = round(var**0.5, 10)
    return InteractionNetworkSummary(
        edge_count=len(parsed),
        host_count=len(hosts),
        parasite_count=len(parasites),
        mean_edge_strength=mean,
        strength_heterogeneity=hetero,
        edges=tuple(parsed),
    )


@dataclass(frozen=True, slots=True)
class FactorialCellResult:
    abiotic: str
    biotic: str
    resource_productivity: float
    mean_score: float
    campaign_digest: str
    arm_digests: dict[str, str]

    def to_dict(self) -> dict[str, object]:
        return {
            "abiotic": self.abiotic,
            "biotic": self.biotic,
            "resource_productivity": self.resource_productivity,
            "mean_score": self.mean_score,
            "campaign_digest": self.campaign_digest,
            "arm_digests": dict(self.arm_digests),
        }


@dataclass(frozen=True, slots=True)
class FactorialCampaignResult:
    schema: str
    seeds: tuple[int, ...]
    cells: tuple[FactorialCellResult, ...]
    adaptive_origin_gate: AdaptiveOriginGate
    network: InteractionNetworkSummary | None
    claim_ceiling: str
    red_queen_proved: bool

    def to_dict(self) -> dict[str, object]:
        body: dict[str, object] = {
            "schema": self.schema,
            "seeds": list(self.seeds),
            "cells": [cell.to_dict() for cell in self.cells],
            "adaptive_origin_gate": self.adaptive_origin_gate.to_dict(),
            "network": None if self.network is None else self.network.to_dict(),
            "claim_ceiling": self.claim_ceiling,
            "red_queen_proved": self.red_queen_proved,
            "raises_claim_ladder": False,
            "engine_infection_physics": "not_in_engine_core",
        }
        body["factorial_digest"] = canonical_digest(
            canonical_payload(
                {k: body[k] for k in body if k not in {"factorial_digest", "digest"}}
            )
        )
        body["digest"] = body["factorial_digest"]
        return body


def run_abiotic_biotic_factorial(
    *,
    seeds: Sequence[int],
    abiotic_levels: Sequence[str] = ("low", "high"),
    biotic_levels: Sequence[str] = ("absent", "present"),
    low_productivity: float = 0.5,
    high_productivity: float = 2.0,
    allow_exaptation_like_gains: bool = False,
    request_claim_ceiling: str = "runtime_observation",
    network_edges: Sequence[Mapping[str, object]] | None = None,
) -> FactorialCampaignResult:
    """Run a 2×2 abiotic × biotic factorial using the Phase 4 campaign runner.

    Biotic-absent cells run ``abiotic_only``. Biotic-present cells run intact +
    null contrasts. ``resource_productivity`` is a declared factorial factor
    recorded on each cell. Adaptive-origin is a declared gate only.
    """

    if not seeds:
        raise ConfigurationError("factorial requires at least one seed.")
    abiotic = tuple(str(item).strip().lower() for item in abiotic_levels)
    biotic = tuple(str(item).strip().lower() for item in biotic_levels)
    if set(abiotic) - _ABIOTIC_LEVELS:
        raise ConfigurationError(f"abiotic_levels must be in {sorted(_ABIOTIC_LEVELS)}.")
    if set(biotic) - _BIOTIC_LEVELS:
        raise ConfigurationError(f"biotic_levels must be in {sorted(_BIOTIC_LEVELS)}.")
    if float(low_productivity) <= 0.0 or float(high_productivity) <= 0.0:
        raise ConfigurationError("productivity levels must be > 0.")
    ceiling = str(request_claim_ceiling).strip().lower()
    if ceiling not in {"runtime_observation", "candidate_evidence"}:
        raise ConfigurationError(
            "request_claim_ceiling must be runtime_observation or candidate_evidence."
        )
    gate = adaptive_origin_gate(allow_exaptation_like_gains=allow_exaptation_like_gains)
    cells: list[FactorialCellResult] = []
    for abiotic_level in abiotic:
        productivity = (
            float(low_productivity) if abiotic_level == "low" else float(high_productivity)
        )
        for biotic_level in biotic:
            if biotic_level == "absent":
                arms: tuple[str, ...] = ("abiotic_only",)
            else:
                arms = ("intact", "content_null", "structure_null")
            # Higher abiotic productivity reduces relative steal when parasites
            # are present (Lopez Pascua resource analogy). Absent cells keep
            # default steal (unused because abiotic_only injects nothing).
            if biotic_level == "present":
                steal = min(1.0, 0.8 / productivity)
            else:
                steal = 0.8
            campaign = run_host_parasite_campaign(
                seeds=seeds,
                arms=arms,
                steal_fraction=steal,
                request_claim_ceiling="runtime_observation",
            )
            by_arm = {item.arm: item for item in campaign.arm_results}
            primary = "intact" if biotic_level == "present" else "abiotic_only"
            mean_score = by_arm[primary].mean_score
            payload = campaign.to_dict()
            cells.append(
                FactorialCellResult(
                    abiotic=abiotic_level,
                    biotic=biotic_level,
                    resource_productivity=productivity,
                    mean_score=mean_score,
                    campaign_digest=str(payload["campaign_digest"]),
                    arm_digests={
                        key: str(value) for key, value in payload["arm_digests"].items()
                    },
                )
            )
    network = (
        None if network_edges is None else summarize_interaction_network(network_edges)
    )
    if ceiling == "candidate_evidence":
        score_map = {(cell.abiotic, cell.biotic): cell.mean_score for cell in cells}
        if len(score_map) < 4 or len(set(score_map.values())) < 2:
            raise ConfigurationError(
                "candidate_evidence refused: factorial cells do not provide a contrast."
            )
    return FactorialCampaignResult(
        schema="host_parasite_abiotic_biotic_factorial_v1",
        seeds=tuple(int(seed) for seed in seeds),
        cells=tuple(cells),
        adaptive_origin_gate=gate,
        network=network,
        claim_ceiling=ceiling,
        red_queen_proved=False,
    )


__all__ = [
    "AdaptiveOriginGate",
    "FactorialCampaignResult",
    "FactorialCellResult",
    "InteractionNetworkSummary",
    "adaptive_origin_gate",
    "run_abiotic_biotic_factorial",
    "summarize_interaction_network",
]
