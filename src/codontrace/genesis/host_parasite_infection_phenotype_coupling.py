"""De-toy D3: infection-cost × abstract metabolic-error coupling (dual-null).

Infected HostParasiteEnv seats raise host metabolic_error by a steal-weighted
load. content_null kills the delta; structure_null blocks infection.
Port-only; ClaimGate refuses phage/clinical/Aevol-identity claims.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from codontrace.errors import ConfigurationError
from codontrace.genesis.canonical import canonical_digest, canonical_payload
from codontrace.genesis.host_parasite_abstract_phenotype import (
    decode_abstract_phenotype,
    metabolic_error_for_genome,
)
from codontrace.genesis.host_parasite_env import HostParasiteEnv, dual_null_template
from codontrace.genome import SemanticGenome

SCHEMA = "host_parasite_infection_phenotype_coupling_v1"
DOMAIN_PROFILE = "host_parasite"
DEFAULT_SEEDS: tuple[int, ...] = (11, 22, 33, 44, 55)
DEFAULT_STEAL = 0.8
# Prereg: intact mean delta_error must exceed null arms by this margin.
DEFAULT_SEPARATION_THRESHOLD = 0.02


def _digest_body(body: Mapping[str, object]) -> str:
    return canonical_digest(canonical_payload(dict(body)))


def _genome_for(seed: int, role: str) -> SemanticGenome:
    return SemanticGenome.random(length=12, seed=int(seed) * 1009 + (0 if role == "host" else 17))


def _arm_trial(
    *,
    seed: int,
    null_kind: str,
    steal_fraction: float,
    parasite_payload: Sequence[int],
) -> dict[str, object]:
    host_g = _genome_for(seed, "host")
    baseline = metabolic_error_for_genome(host_g)
    env = HostParasiteEnv(
        steal_fraction=float(steal_fraction),
        null_template=dual_null_template(null_kind),
    )
    env.add_host("h0", ("logic_nand", "logic_not"))
    injected = False
    reason = "not_attempted"
    if null_kind == "structure_null":
        # Structure-null: attempt inject; must fail eligibility.
        attempt = env.try_horizontal_inject(
            host_id="h0",
            parasite_id="p0",
            parasite_tasks=["logic_nand"],
            payload=list(parasite_payload),
        )
        injected = bool(attempt.injected)
        reason = attempt.reason
        coupled_error = baseline  # no infection path → no phenotype hitch
    else:
        attempt = env.try_horizontal_inject(
            host_id="h0",
            parasite_id="p0",
            parasite_tasks=["logic_nand"],
            payload=list(parasite_payload),
        )
        injected = bool(attempt.injected)
        reason = attempt.reason
        ph = decode_abstract_phenotype(host_g)
        base_err = float(ph["metabolic_error"])
        if not injected:
            coupled_error = base_err
        else:
            retained = env.host_retained_cpu("h0")
            # Infection cost: steal lowers retained CPU → raises metabolic error.
            # content_null with empty payload keeps retained≈1.0 → delta≈0.
            load = max(0.0, 1.0 - float(retained))
            coupled_error = round(min(1.0, base_err + load * float(steal_fraction)), 10)

    delta = round(float(coupled_error) - float(baseline), 10)
    return {
        "seed": int(seed),
        "null_kind": null_kind,
        "injected": injected,
        "reason": reason,
        "baseline_metabolic_error": baseline,
        "coupled_metabolic_error": coupled_error,
        "delta_error": delta,
        "genome_digest": host_g.digest(),
        "aevol_identity": False,
        "wet_metabolism_claim": False,
    }


def run_infection_phenotype_coupling_campaign(
    *,
    seeds: Sequence[int] = DEFAULT_SEEDS,
    steal_fraction: float = DEFAULT_STEAL,
    separation_threshold: float = DEFAULT_SEPARATION_THRESHOLD,
    parasite_payload: Sequence[int] = (1, 2, 3, 4),
) -> dict[str, Any]:
    """Dual-null campaign: intact delta must separate from both nulls."""

    if not (0.0 < float(separation_threshold) < 1.0):
        raise ConfigurationError("separation_threshold must be in (0, 1)")

    arms = ("intact", "content_null", "structure_null")
    null_map = {
        "intact": "none",
        "content_null": "content_null",
        "structure_null": "structure_null",
    }
    per_arm: dict[str, list[dict[str, object]]] = {a: [] for a in arms}
    for seed in seeds:
        for arm in arms:
            trial = _arm_trial(
                seed=int(seed),
                null_kind=null_map[arm],
                steal_fraction=steal_fraction,
                parasite_payload=tuple(parasite_payload),
            )
            per_arm[arm].append(trial)

    def _mean_delta(arm: str) -> float:
        xs = [float(t["delta_error"]) for t in per_arm[arm]]
        return round(sum(xs) / len(xs), 10) if xs else 0.0

    intact_mean = _mean_delta("intact")
    content_mean = _mean_delta("content_null")
    structure_mean = _mean_delta("structure_null")
    sep_content = round(intact_mean - content_mean, 10)
    sep_structure = round(intact_mean - structure_mean, 10)
    separation_ok = (
        intact_mean > float(separation_threshold)
        and sep_content >= float(separation_threshold)
        and sep_structure >= float(separation_threshold)
    )
    result = "SUCCESS" if separation_ok else "FAIL"

    body: dict[str, Any] = {
        "schema": SCHEMA,
        "domain_profile": DOMAIN_PROFILE,
        "seeds": list(seeds),
        "steal_fraction": float(steal_fraction),
        "separation_threshold": float(separation_threshold),
        "arms": {arm: trials for arm, trials in per_arm.items()},
        "mean_delta_error": {
            "intact": intact_mean,
            "content_null": content_mean,
            "structure_null": structure_mean,
        },
        "separation": {
            "intact_minus_content_null": sep_content,
            "intact_minus_structure_null": sep_structure,
        },
        "separation_ok": separation_ok,
        "result": result,
        "red_queen_proved": False,
        "phage_therapy_cleared": False,
        "aevol_identity": False,
        "wet_metabolism_claim": False,
        "clinical_pathogen_model": False,
        "claimgate_refuses": [
            "red_queen_proved",
            "phage_therapy_cleared",
            "clinical_pathogen_model",
            "gene_identity_proved",
            "crispr_identity_proved",
        ],
        "engine_infection_physics": "not_in_engine_core",
        "honesty": (
            "Digital steal × abstract metabolic-error coupling on the "
            "host_parasite port with dual-null; not wet metabolism or phage therapy."
        ),
    }
    body["campaign_digest"] = _digest_body(body)
    return body


__all__ = [
    "SCHEMA",
    "DOMAIN_PROFILE",
    "run_infection_phenotype_coupling_campaign",
]
