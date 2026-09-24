"""De-toy D5: cost-of-generalism routed through abstract metabolic phenotype.

Generalist task repertoires pay a Shannon-entropy metabolic-error penalty on
the D4 phenotype channel; specialists pay less. A coexistence assay contrasts
cost-on vs cost-off arms. Dual-null: content_null preserves breadth under opaque
labels; structure_null disables the phenotype penalty path.

Literature (digital honesty map, not wet identity):
- Quigley et al. doi:10.1098/rspb.2012.0769
- Gómez et al. doi:10.1098/rspb.2014.2297
- rspb.2025.1157; ijpara.2024.11.009 (generalism costs)

ClaimGate: red_queen_proved / wet_ard_fsd_identity / phage_therapy_cleared stay False.
Port-only — never engine.py.
"""

from __future__ import annotations

import hashlib
import math
from collections.abc import Mapping, Sequence
from typing import Any

from codontrace.errors import ConfigurationError
from codontrace.genesis.canonical import canonical_digest, canonical_payload
from codontrace.genesis.host_parasite_abstract_phenotype import (
    decode_abstract_phenotype,
    metabolic_error_for_genome,
)
from codontrace.genesis.host_parasite_env import HostParasiteEnv
from codontrace.genome import SemanticGenome

SCHEMA = "host_parasite_cost_of_generalism_phenotype_v1"
DOMAIN_PROFILE = "host_parasite"
DEFAULT_SEEDS: tuple[int, ...] = (11, 22, 33, 44, 55)
DEFAULT_GENERATIONS = 16
DEFAULT_COST_WEIGHT = 0.70
DEFAULT_SEPARATION_THRESHOLD = 0.03
DEFAULT_MIN_SEED_HITS = 3

_SPECIALIST_A = ("logic_nand",)
_SPECIALIST_B = ("logic_not",)
_GENERALIST = ("logic_nand", "logic_not", "logic_and", "logic_or", "logic_xor")


def _digest_body(body: Mapping[str, object]) -> str:
    return canonical_digest(canonical_payload(dict(body)))


def _seed_bytes(seed: int, salt: str) -> bytes:
    return hashlib.sha256(f"{int(seed)}|{salt}".encode()).digest()


def repertoire_shannon_entropy(tasks: Sequence[str]) -> float:
    """Shannon entropy (nats) of a task repertoire — digital generalism proxy."""

    if not tasks:
        return 0.0
    counts: dict[str, int] = {}
    for t in tasks:
        key = str(t)
        counts[key] = counts.get(key, 0) + 1
    total = float(sum(counts.values()))
    ent = 0.0
    for c in counts.values():
        p = c / total
        ent -= p * math.log(p)
    return float(ent)


def generalism_phenotype_penalty(
    tasks: Sequence[str],
    *,
    cost_weight: float = DEFAULT_COST_WEIGHT,
    null_kind: str = "none",
) -> float:
    """Map repertoire breadth → [0, 1] metabolic-error add-on."""

    if not (0.0 <= float(cost_weight) <= 1.0):
        raise ConfigurationError("cost_weight must be in [0, 1]")
    if null_kind == "structure_null":
        return 0.0
    if null_kind == "content_null":
        opaque = [f"tok_{i}" for i in range(len(tasks))]
        ent = repertoire_shannon_entropy(opaque)
        n_unique = len(opaque)
    else:
        ent = repertoire_shannon_entropy(tasks)
        n_unique = len({str(t) for t in tasks})
    max_ent = math.log(max(2, n_unique))
    norm = 0.0 if max_ent <= 0.0 else min(1.0, ent / max_ent)
    return round(float(cost_weight) * norm, 10)


def _genome_for(seed: int, role: str) -> SemanticGenome:
    return SemanticGenome.random(length=12, seed=int(seed) * 1009 + (0 if role == "host" else 17))


def coupled_metabolic_error(
    genome: SemanticGenome,
    tasks: Sequence[str],
    *,
    cost_weight: float,
    null_kind: str = "none",
    apply_cost: bool = True,
) -> dict[str, object]:
    """Baseline D4 error + optional generalism penalty."""

    base = decode_abstract_phenotype(genome)
    base_err = float(base["metabolic_error"])  # type: ignore[arg-type]
    penalty = (
        0.0
        if not apply_cost
        else generalism_phenotype_penalty(
            tasks, cost_weight=cost_weight, null_kind=null_kind
        )
    )
    coupled = round(min(1.0, base_err + penalty), 10)
    return {
        "baseline_metabolic_error": base_err,
        "generalism_penalty": penalty,
        "coupled_metabolic_error": coupled,
        "repertoire_entropy": repertoire_shannon_entropy(tasks),
        "n_tasks": len(tasks),
        "phenotype_digest": base["phenotype_digest"],
    }


def _coexistence_trial(
    *,
    seed: int,
    apply_cost: bool,
    cost_weight: float,
    generations: int,
    null_kind: str = "none",
) -> dict[str, object]:
    """Digital specialist vs generalist assay with phenotype-routed cost.

    Closely mirrors SF1 count dynamics, but routes the generalist efficiency
    penalty through D4 metabolic-error / repertoire-entropy (not a bare float).
    """

    hosts = {"H_a": 22, "H_b": 22, "H_ab": 12}
    parasites = {"V_a": 10, "V_b": 10, "V_ab": 10}
    match = {
        "V_a": ("H_a", "H_ab"),
        "V_b": ("H_b", "H_ab"),
        "V_ab": ("H_a", "H_b", "H_ab"),
    }
    repertoires = {
        "V_a": _SPECIALIST_A,
        "V_b": _SPECIALIST_B,
        "V_ab": _GENERALIST,
    }
    host_g = _genome_for(seed, "host")
    penalties: dict[str, float] = {}
    errors: dict[str, float] = {}
    for vid, tasks in repertoires.items():
        packed = coupled_metabolic_error(
            host_g,
            tasks,
            cost_weight=cost_weight,
            null_kind=null_kind,
            apply_cost=apply_cost,
        )
        penalties[vid] = float(packed["generalism_penalty"])  # type: ignore[arg-type]
        errors[vid] = float(packed["coupled_metabolic_error"])  # type: ignore[arg-type]

    history: list[dict[str, object]] = []
    for gen in range(int(generations)):
        digest = _seed_bytes(seed, f"d5_g{gen}_c{int(apply_cost)}_n{null_kind}")
        # Phenotype-routed generalism cost: V_ab efficiency collapses when
        # repertoire-entropy penalty is applied; specialists barely moved.
        if apply_cost and null_kind != "structure_null":
            v_ab_eff = max(0.08, 0.95 - 0.90 * penalties["V_ab"])
        else:
            v_ab_eff = 0.95
        eff = {
            "V_a": 0.55,
            "V_b": 0.55,
            "V_ab": float(v_ab_eff),
        }
        pressure = {h: 0.0 for h in hosts}
        for v, targets in match.items():
            load = parasites[v] * eff[v]
            share = load / max(1, len(targets))
            for h in targets:
                pressure[h] += share
        host_err = metabolic_error_for_genome(host_g)
        new_hosts: dict[str, int] = {}
        for h, n in hosts.items():
            retained = max(0.05, 1.0 - 0.04 * pressure[h] - 0.15 * host_err)
            growth = retained * (1.15 if n < 45 else 0.95)
            noise = 0.85 + 0.3 * (digest[ord(h[-1]) % len(digest)] / 255.0)
            new_hosts[h] = max(0, int(round(n * growth * noise)))
        new_parasites: dict[str, int] = {}
        for v, targets in match.items():
            prey = sum(new_hosts[h] for h in targets)
            growth = eff[v] * (
                0.08 + 0.02 * (digest[(sum(ord(c) for c in v) * 17) % len(digest)] / 255.0)
            )
            new_parasites[v] = max(0, int(round(prey * growth)))
        hosts, parasites = new_hosts, new_parasites
        history.append(
            {
                "generation": gen,
                "hosts": dict(hosts),
                "parasites": dict(parasites),
                "host_richness": sum(1 for n in hosts.values() if n > 0),
                "parasite_richness": sum(1 for n in parasites.values() if n > 0),
                "mean_host_n": round(sum(float(n) for n in hosts.values()) / max(1, len(hosts)), 6),
            }
        )

    final = history[-1]
    host_rich = int(final["host_richness"])  # type: ignore[call-overload]
    para_rich = int(final["parasite_richness"])  # type: ignore[call-overload]
    mean_host = float(final["mean_host_n"])  # type: ignore[arg-type]
    extinction_proxy = host_rich <= 1 or mean_host < 2.0
    coexistence = host_rich >= 2 and para_rich >= 2 and mean_host >= 5.0 and not extinction_proxy
    late_p = history[-1]["parasites"]
    assert isinstance(late_p, dict)
    superparasite_dominance = int(late_p["V_ab"]) > (
        int(late_p["V_a"]) + int(late_p["V_b"])
    )

    env = HostParasiteEnv(steal_fraction=0.8)
    env.add_host("probe_h", ["logic_nand", "logic_not"])
    env.try_horizontal_inject(
        host_id="probe_h",
        parasite_id="probe_v",
        parasite_tasks=["logic_nand"],
        payload=(1, 2, 3),
    )

    return {
        "seed": int(seed),
        "apply_cost": bool(apply_cost),
        "null_kind": null_kind,
        "cost_weight": float(cost_weight),
        "penalties": penalties,
        "errors": errors,
        "final_hosts": final["hosts"],
        "final_parasites": final["parasites"],
        "host_richness": host_rich,
        "parasite_richness": para_rich,
        "mean_host_n": mean_host,
        "extinction_proxy": extinction_proxy,
        "coexistence": coexistence,
        "superparasite_dominance": superparasite_dominance,
        "env_probe_occupied": env.hosts["probe_h"].parasite_id is not None,
        "aevol_identity": False,
        "wet_metabolism_claim": False,
    }


def _dual_null_penalty_trial(
    *,
    seed: int,
    cost_weight: float,
) -> dict[str, object]:
    host_g = _genome_for(seed, "host")
    intact = coupled_metabolic_error(
        host_g, _GENERALIST, cost_weight=cost_weight, null_kind="none", apply_cost=True
    )
    content = coupled_metabolic_error(
        host_g,
        _GENERALIST,
        cost_weight=cost_weight,
        null_kind="content_null",
        apply_cost=True,
    )
    structure = coupled_metabolic_error(
        host_g,
        _GENERALIST,
        cost_weight=cost_weight,
        null_kind="structure_null",
        apply_cost=True,
    )
    specialist = coupled_metabolic_error(
        host_g, _SPECIALIST_A, cost_weight=cost_weight, null_kind="none", apply_cost=True
    )
    return {
        "seed": int(seed),
        "intact_penalty": intact["generalism_penalty"],
        "content_null_penalty": content["generalism_penalty"],
        "structure_null_penalty": structure["generalism_penalty"],
        "specialist_penalty": specialist["generalism_penalty"],
        "intact_minus_structure": round(
            float(intact["generalism_penalty"])  # type: ignore[arg-type]
            - float(structure["generalism_penalty"]),  # type: ignore[arg-type]
            10,
        ),
        "generalist_minus_specialist": round(
            float(intact["generalism_penalty"])  # type: ignore[arg-type]
            - float(specialist["generalism_penalty"]),  # type: ignore[arg-type]
            10,
        ),
        "content_preserves_breadth": abs(
            float(intact["generalism_penalty"])  # type: ignore[arg-type]
            - float(content["generalism_penalty"])  # type: ignore[arg-type]
        )
        < 1e-9,
    }


def run_cost_of_generalism_phenotype_campaign(
    *,
    seeds: Sequence[int] = DEFAULT_SEEDS,
    cost_weight: float = DEFAULT_COST_WEIGHT,
    generations: int = DEFAULT_GENERATIONS,
    separation_threshold: float = DEFAULT_SEPARATION_THRESHOLD,
    min_seed_hits: int = DEFAULT_MIN_SEED_HITS,
) -> dict[str, Any]:
    """D5 campaign: phenotype-routed generalism cost + dual-null + coexistence."""

    if not (0.0 < float(separation_threshold) < 1.0):
        raise ConfigurationError("separation_threshold must be in (0, 1)")
    if int(min_seed_hits) < 1:
        raise ConfigurationError("min_seed_hits must be >= 1")

    cost_on = [
        _coexistence_trial(
            seed=s, apply_cost=True, cost_weight=cost_weight, generations=generations
        )
        for s in seeds
    ]
    cost_off = [
        _coexistence_trial(
            seed=s, apply_cost=False, cost_weight=cost_weight, generations=generations
        )
        for s in seeds
    ]
    dual_null = [
        _dual_null_penalty_trial(seed=s, cost_weight=cost_weight) for s in seeds
    ]

    cost_on_coexist = sum(1 for t in cost_on if t["coexistence"])
    cost_off_collapse = sum(
        1 for t in cost_off if t["extinction_proxy"] or t["superparasite_dominance"]
    )
    sep_vals = [float(t["intact_minus_structure"]) for t in dual_null]  # type: ignore[arg-type]
    gen_vals = [float(t["generalist_minus_specialist"]) for t in dual_null]  # type: ignore[arg-type]
    struct_pen = [float(t["structure_null_penalty"]) for t in dual_null]  # type: ignore[arg-type]
    mean_sep = round(sum(sep_vals) / len(sep_vals), 10)
    mean_gen_minus_spec = round(sum(gen_vals) / len(gen_vals), 10)
    dual_null_ok = (
        mean_sep >= float(separation_threshold)
        and mean_gen_minus_spec >= float(separation_threshold)
        and all(bool(t["content_preserves_breadth"]) for t in dual_null)
        and all(v == 0.0 for v in struct_pen)
    )
    coexist_ok = cost_on_coexist >= int(min_seed_hits) and cost_off_collapse >= int(
        min_seed_hits
    )
    success = dual_null_ok and coexist_ok
    partial = (dual_null_ok or coexist_ok) and not success
    result = "SUCCESS" if success else ("PARTIAL" if partial else "FAIL")

    body: dict[str, Any] = {
        "schema": SCHEMA,
        "domain_profile": DOMAIN_PROFILE,
        "seeds": list(seeds),
        "cost_weight": float(cost_weight),
        "generations": int(generations),
        "separation_threshold": float(separation_threshold),
        "min_seed_hits": int(min_seed_hits),
        "cost_on_trials": cost_on,
        "cost_off_trials": cost_off,
        "dual_null_trials": dual_null,
        "metrics": {
            "cost_on_coexistence_seeds": cost_on_coexist,
            "cost_off_collapse_or_dominance_seeds": cost_off_collapse,
            "mean_intact_minus_structure_penalty": mean_sep,
            "mean_generalist_minus_specialist_penalty": mean_gen_minus_spec,
            "dual_null_ok": dual_null_ok,
            "coexistence_contrast_ok": coexist_ok,
        },
        "result": result,
        "doi_primary": "10.1098/rspb.2012.0769",
        "doi_related": [
            "10.1098/rspb.2014.2297",
            "10.1098/rspb.2025.1157",
            "10.1016/j.ijpara.2024.11.009",
        ],
        "red_queen_proved": False,
        "phage_therapy_cleared": False,
        "wet_ard_fsd_identity": False,
        "aevol_identity": False,
        "wet_metabolism_claim": False,
        "clinical_pathogen_model": False,
        "claimgate_refuses": [
            "red_queen_proved",
            "phage_therapy_cleared",
            "wet_ard_fsd_identity",
            "clinical_pathogen_model",
            "gene_identity_proved",
        ],
        "engine_infection_physics": "not_in_engine_core",
        "honesty": (
            "Digital cost-of-generalism via abstract metabolic-error penalty on "
            "the host_parasite port; not wet ARD/FSD identity or phage therapy."
        ),
    }
    body["campaign_digest"] = _digest_body(body)
    return body


__all__ = [
    "SCHEMA",
    "DOMAIN_PROFILE",
    "coupled_metabolic_error",
    "generalism_phenotype_penalty",
    "repertoire_shannon_entropy",
    "run_cost_of_generalism_phenotype_campaign",
]
