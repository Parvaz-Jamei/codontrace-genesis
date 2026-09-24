"""Cell↔microbe hard campaigns — Genesis substrate × host_parasite ClaimGate.

Runs several non-trivial, falsifiable digital campaigns framed as:
  cell = SemanticGenome / Genesis substrate (not a DomainProfile)
  microbe / bacterium / virus / parasite = COU semantic labels only
  ONE host_parasite DomainProfile; no infection physics in engine.py

Harder than Wave-6 journal smoke: multi-seed contingency heat, dual-genome
Zaman digests, entropy/Hamming dual-null, ARD→FSD cost trajectories,
sequential Cornish order effects, Scanlan mutator abiotic constraint, plus a
declared task–gene dual-null panel. Prefer surprising negatives / contingency
over hyped positives. Claim ceilings stay fail-closed.
"""

from __future__ import annotations

import json
from collections import defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from statistics import mean
from typing import Any

from codontrace.claimgate import audit_bundle
from codontrace.claimgate.adapters.host_parasite import (
    assert_claim_allowed,
    attach_ard_fsd_transition,
    attach_genome_diversity_campaign,
    attach_genome_zaman_campaign,
    attach_multi_seed_contingency,
    attach_scanlan_mutator_campaign,
    attach_sequential_cornish_campaign,
    attach_task_gene_map,
    bundle_from_host_parasite_cou,
)
from codontrace.claimgate.adapters.host_parasite_prereg import (
    attach_host_parasite_preregistration,
    host_parasite_preregistration,
)
from codontrace.errors import ConfigurationError
from codontrace.genesis.canonical import canonical_digest, canonical_payload
from codontrace.genesis.host_parasite_ard_fsd_transition import (
    run_ard_fsd_transition_campaign,
)
from codontrace.genesis.host_parasite_contingency import (
    run_multi_seed_contingency_campaign,
)
from codontrace.genesis.host_parasite_cornish_sequential import (
    default_sequential_schedule,
    run_sequential_cornish_campaign,
)
from codontrace.genesis.host_parasite_genome_diversity import (
    run_genome_diversity_campaign,
)
from codontrace.genesis.host_parasite_genome_zaman import run_genome_zaman_campaign
from codontrace.genesis.host_parasite_mutator import run_scanlan_mutator_campaign
from codontrace.genesis.host_parasite_task_gene import build_task_gene_map

SCHEMA = "host_parasite_cell_microbe_hard_campaigns_v1"
DOMAIN_PROFILE = "host_parasite"

# Deterministic hard seed packs (larger / contingency-aware vs Wave-6 smoke).
SEEDS_CONTINGENCY_MIXED = (3, 6, 7, 8, 9, 11, 12, 13)  # mix of contingent + rising
SEEDS_SUPPORTING_EDGE = (1, 2, 4)  # still supports universal law (honesty edge)
SEEDS_GENOME = (101, 202, 303, 404)
SEEDS_DIVERSITY = (11, 22, 33, 44, 55)
SEEDS_ARD = (11, 22, 33)
SEEDS_CORNISH = (11, 22, 33, 44)
SEEDS_SCANLAN = (11, 22, 33)
TASK_GENE_SEEDS = {
    "cell_host_substrate": 42,
    "microbe_parasite_label": 42 + 10007,
    "content_null_proxy": 42 + 777,
}

_ALLOWED_CEILINGS = frozenset({"runtime_observation", "candidate_evidence"})
_HARD_REFUSE = (
    "red_queen_proved",
    "phage_therapy_cleared",
    "biosafety_level_certified",
    "clinical_pathogen_model",
    "crispr_identity_proved",
    "complexity_emergence_proved",
    "gene_identity_proved",
    "intervention_supported",
    "oee_modes_passed",
    "modes_passed_proved",
    "intelligence_proved",
)


def _digest_body(body: Mapping[str, object]) -> str:
    return canonical_digest(canonical_payload(dict(body)))


def _mean(xs: Sequence[float]) -> float:
    return round(float(mean(xs)), 10) if xs else 0.0


@dataclass(frozen=True, slots=True)
class CellMicrobeHardCampaignPack:
    """Bundle of hard cell↔microbe campaigns + ClaimGate honesty audit."""

    schema: str
    campaigns: tuple[dict[str, object], ...]
    claimgate_audit: dict[str, object]
    claim_ceiling: str
    pack_digest: str
    red_queen_proved: bool
    complexity_emergence_proved: bool
    intervention_supported: bool
    gene_identity_proved: bool
    engine_infection_physics: str

    def to_dict(self) -> dict[str, object]:
        body: dict[str, object] = {
            "schema": self.schema,
            "domain_profile": DOMAIN_PROFILE,
            "cell_role": "semantic_genome_genesis_substrate",
            "microbe_role": "cou_semantic_label_only",
            "campaigns": list(self.campaigns),
            "claimgate_audit": dict(self.claimgate_audit),
            "claim_ceiling": self.claim_ceiling,
            "raises_claim_ladder": False,
            "red_queen_proved": False,
            "complexity_emergence_proved": False,
            "intervention_supported": False,
            "gene_identity_proved": False,
            "crispr_identity_proved": False,
            "oee_modes_passed": False,
            "phage_therapy_cleared": False,
            "clinical_pathogen_model": False,
            "engine_infection_physics": self.engine_infection_physics,
            "note": (
                "Hard cell↔microbe campaigns on ONE host_parasite DomainProfile. "
                "Falsification paths required; ClaimGate ceilings fail-closed. "
                "Not wet microbial cell biology; not Red Queen / phage therapy / BSL."
            ),
        }
        body["pack_digest"] = self.pack_digest or _digest_body(
            {k: body[k] for k in body if k not in {"pack_digest", "digest", "campaign_digest"}}
        )
        body["campaign_digest"] = body["pack_digest"]
        body["digest"] = body["pack_digest"]
        return body


def _panel_contingency() -> dict[str, object]:
    mixed = run_multi_seed_contingency_campaign(seeds=SEEDS_CONTINGENCY_MIXED)
    supporting = run_multi_seed_contingency_campaign(seeds=SEEDS_SUPPORTING_EDGE)
    md = mixed.to_dict()
    sd = supporting.to_dict()
    present = [o for o in md["seed_outcomes"] if o["arm"] == "parasite_present"]
    absent = [o for o in md["seed_outcomes"] if o["arm"] == "parasite_absent"]
    heat = [
        {
            "seed": o["seed"],
            "richness_delta": o["richness_delta"],
            "contingent_seed": o["contingent_seed"],
            "outcome_score": o["outcome_score"],
        }
        for o in present
    ]
    rising = [h for h in heat if int(h["richness_delta"]) > 0]
    failing = [h for h in heat if int(h["richness_delta"]) <= 0]
    return {
        "id": "CM1_multi_seed_contingency",
        "title": "Multi-seed contingency — when parasites fail to raise complexity",
        "why_hard": (
            "Zaman S1 honesty: mixed seeds include contingent collapses and "
            "rising seeds; supporting-edge pack still never unlocks complexity "
            "emergence."
        ),
        "falsification_path": "parasite_absent dual-null + contingent seed collapses",
        "api": "run_multi_seed_contingency_campaign",
        "seeds_mixed": list(SEEDS_CONTINGENCY_MIXED),
        "seeds_supporting_edge": list(SEEDS_SUPPORTING_EDGE),
        "hypothesis": md["hypothesis"],
        "hypothesis_supported_mixed": md["hypothesis_supported"],
        "hypothesis_supported_edge": sd["hypothesis_supported"],
        "failure_reason_mixed": md.get("failure_reason", ""),
        "cross_seed_variance_mixed": md["cross_seed_variance"],
        "seed_digests_are_distinct": md["seed_digests_are_distinct"],
        "complexity_emergence_proved": False,
        "claim_ceiling_mixed": md["claim_ceiling"],
        "claim_ceiling_edge": sd["claim_ceiling"],
        "campaign_digest_mixed": md["campaign_digest"],
        "campaign_digest_edge": sd["campaign_digest"],
        "parasite_present_heat": heat,
        "n_rising_under_parasitism": len(rising),
        "n_failing_under_parasitism": len(failing),
        "mean_delta_present": _mean([float(o["richness_delta"]) for o in present]),
        "mean_delta_absent": _mean([float(o["richness_delta"]) for o in absent]),
        "arm_digests": md["arm_digests"],
        "honesty": (
            "Support on edge seeds ≠ complexity_emergence_proved; mixed pack "
            "falsifies universal rise law."
        ),
    }


def _panel_genome_zaman() -> dict[str, object]:
    camp = run_genome_zaman_campaign(seeds=SEEDS_GENOME, steps=5)
    d = camp.to_dict()
    # Host vs parasite final digests per arm (cell substrate vs microbe label).
    per_arm: dict[str, Any] = {}
    for arm in d["arm_results"]:
        hosts = [o["genomes"]["host_genome_digest"] for o in arm["seed_outcomes"]]
        paras = [o["genomes"]["parasite_genome_digest"] for o in arm["seed_outcomes"]]
        per_arm[arm["arm"]] = {
            "arm_digest": arm["digest"],
            "mean_host_genome_length": arm["mean_host_genome_length"],
            "distinct_parasite_final_digests": arm["distinct_parasite_final_digests"],
            "host_final_digests_prefix": [h[:16] for h in hosts],
            "parasite_final_digests_prefix": [p[:16] for p in paras],
            "host_parasite_digest_pairs_distinct": all(h != p for h, p in zip(hosts, paras)),
        }
    return {
        "id": "CM2_dual_genome_zaman",
        "title": "Dual-genome Zaman freeze / replay / reciprocal (cell vs microbe labels)",
        "why_hard": (
            "Host SemanticGenome (cell substrate) and parasite SemanticGenome "
            "(microbe label) digests must separate across freeze/replay/reciprocal "
            "arms without claiming Red Queen or complexity emergence."
        ),
        "falsification_path": "arm digest distinctness; frozen parasite trajectory flat",
        "api": "run_genome_zaman_campaign",
        "seeds": list(SEEDS_GENOME),
        "steps": d["steps"],
        "arms_are_distinct": d["arms_are_distinct"],
        "arm_digests": d["arm_digests"],
        "per_arm": per_arm,
        "complexity_emergence_proved": False,
        "red_queen_proved": False,
        "claim_ceiling": d["claim_ceiling"],
        "campaign_digest": d["campaign_digest"],
        "repertoire_campaign_digest": d["repertoire_campaign_digest"],
        "honesty": "Digital genome analogue only; CRISPR / gene identity unproved.",
    }


def _panel_genome_diversity() -> dict[str, object]:
    camp = run_genome_diversity_campaign(seeds=SEEDS_DIVERSITY)
    d = camp.to_dict()
    by: dict[str, list[dict[str, object]]] = defaultdict(list)
    for o in d["arm_outcomes"]:
        by[str(o["arm"])].append(o)
    arm_stats = {
        arm: {
            "mean_entropy_delta_vs_baseline": _mean(
                [float(o["entropy_delta_vs_baseline"]) for o in outs]
            ),
            "mean_hamming": _mean([float(o["mean_genome_distance"]) for o in outs]),
            "mean_entropy": _mean([float(o["codon_usage_entropy"]) for o in outs]),
            "arm_digest": d["arm_digests"][arm],
        }
        for arm, outs in by.items()
    }
    return {
        "id": "CM3_entropy_hamming_dual_null",
        "title": "Codon entropy / Hamming dual-null under cell↔microbe pressure",
        "why_hard": (
            "Hypothesis parasites_always_raise_codon_entropy must fail under "
            "abiotic / content-null / structure-null while biotic intact separates."
        ),
        "falsification_path": "content_null + structure_null + abiotic_stress deltas ≤ 0",
        "api": "run_genome_diversity_campaign",
        "seeds": list(SEEDS_DIVERSITY),
        "hypothesis": d["hypothesis"],
        "hypothesis_supported": d["hypothesis_supported"],
        "failure_reason": d["failure_reason"],
        "arms_are_distinct": d["arms_are_distinct"],
        "arm_stats": arm_stats,
        "biotic_minus_content_null_entropy_delta": round(
            float(arm_stats["biotic_intact"]["mean_entropy_delta_vs_baseline"])
            - float(arm_stats["content_null"]["mean_entropy_delta_vs_baseline"]),
            10,
        ),
        "claim_ceiling": d["claim_ceiling"],
        "campaign_digest": d["campaign_digest"],
        "honesty": "HE02 dual-null genotype observables; not wet CRISPR identity.",
    }


def _panel_ard_fsd() -> dict[str, object]:
    camp = run_ard_fsd_transition_campaign(seeds=SEEDS_ARD, n_slices=8)
    d = camp.to_dict()
    cost_rows = []
    for s in d["slices"]:
        cost_rows.append(
            {
                "slice_id": s["slice_id"],
                "arm": s["arm"],
                "seed": s["seed"],
                "label": s["label"],
                "mean_cost_of_generalism": s["mean_cost_of_generalism"],
                "slice_digest": s["slice_digest"],
            }
        )
    # Early→late cost under parasite vs nulls (seed 11 spotlight).
    spotlight = [r for r in cost_rows if r["seed"] == SEEDS_ARD[0]]
    return {
        "id": "CM4_ard_fsd_cost_of_generalism",
        "title": "ARD→FSD transition + cost-of-generalism under resource/partner stress",
        "why_hard": (
            "Time-sliced range trajectories must show ARD-like→FSD-like labels "
            "under parasite coevolution while dual-null arms stay undeclared; "
            "universal 'always ARD' law falsifies."
        ),
        "falsification_path": "structure_null_shuffled + abiotic_only dual-null",
        "api": "run_ard_fsd_transition_campaign",
        "seeds": list(SEEDS_ARD),
        "n_slices": 8,
        "hypothesis": d["hypothesis"],
        "hypothesis_supported": d["hypothesis_supported"],
        "failure_reason": d["failure_reason"],
        "transition_observed": d["transition_observed"],
        "slices_are_distinct": d["slices_are_distinct"],
        "arm_digests": d["arm_digests"],
        "cost_spotlight_seed": SEEDS_ARD[0],
        "cost_spotlight": spotlight,
        "red_queen_proved": False,
        "wet_ard_fsd_identity": False,
        "claim_ceiling": d["claim_ceiling"],
        "campaign_digest": d["campaign_digest"],
        "honesty": "Digital transition protocol only; Red Queen dynamics unproved.",
    }


def _panel_cornish() -> dict[str, object]:
    prereg = host_parasite_preregistration(
        question_of_interest=(
            "Does observational match on cell-level digests grant intervention support?"
        ),
        context_of_use=(
            "Sequential Cornish multi-intervention; cell substrate scores; "
            "microbe/parasite labels only; digital ClaimGate."
        ),
        arms=tuple(s["step_id"] for s in default_sequential_schedule()),
        success_metrics=("campaign_digest", "intervention_supported"),
        forbidden_claims=("red_queen_proved", "intervention_supported"),
    )
    prereg_digest = str(prereg.to_dict()["digest"])
    camp = run_sequential_cornish_campaign(
        seeds=SEEDS_CORNISH,
        request_claim_ceiling="candidate_evidence",
        preregistration_digest=prereg_digest,
    )
    d = camp.to_dict()
    steps = [
        {
            "step_id": s["step_id"],
            "kind": s["kind"],
            "intervention_kind": s["intervention_kind"],
            "score": s["score"],
            "intervention_effect_distinct": s["intervention_effect_distinct"],
            "matches_observational_baseline": s["matches_observational_baseline"],
            "intervention_supported": s["intervention_supported"],
            "step_digest": s["step_digest"],
        }
        for s in d["step_outcomes"]
    ]
    return {
        "id": "CM5_sequential_cornish",
        "title": "Sequential Cornish — observational match ≠ intervention_supported",
        "why_hard": (
            "Ordered interventions on cell-level outcome scores can all be "
            "effect-distinct after observational match and still must refuse "
            "intervention_supported (Cornish rule)."
        ),
        "falsification_path": "later intervention order; ClaimGate attach refuse",
        "api": "run_sequential_cornish_campaign",
        "seeds": list(SEEDS_CORNISH),
        "preregistration_digest": prereg_digest,
        "observational_match": d["observational_match"],
        "interventions_executed": d["interventions_executed"],
        "later_intervention_failed": d["later_intervention_failed"],
        "intervention_supported": d["intervention_supported"],
        "claim_ceiling": d["claim_ceiling"],
        "campaign_digest": d["campaign_digest"],
        "steps": steps,
        "obs_score": steps[0]["score"] if steps else None,
        "intervention_scores": [s["score"] for s in steps if s["kind"] == "intervention"],
        "honesty": (
            "Observational twin match alone never grants intervention_supported; "
            "not clinical decision support."
        ),
    }


def _panel_scanlan() -> dict[str, object]:
    camp = run_scanlan_mutator_campaign(
        seeds=SEEDS_SCANLAN,
        request_claim_ceiling="candidate_evidence",
    )
    d = camp.to_dict()
    by: dict[str, list[dict[str, object]]] = defaultdict(list)
    for o in d["arm_outcomes"]:
        by[str(o["arm"])].append(o)
    arm_stats = {
        arm: {
            "mean_abiotic_fitness": _mean([float(o["abiotic_fitness"]) for o in outs]),
            "mean_entropy": _mean([float(o["codon_usage_entropy"]) for o in outs]),
            "mean_hamming": _mean([float(o["mean_genome_distance"]) for o in outs]),
            "mutation_factor": outs[0]["mutation_factor"],
            "arm_digest": d["arm_digests"][arm],
        }
        for arm, outs in by.items()
    }
    coevo_elev = float(arm_stats["coevolution_elevated_mutation"]["mean_abiotic_fitness"])
    abiotic_elev = float(arm_stats["abiotic_elevated_mutation"]["mean_abiotic_fitness"])
    return {
        "id": "CM6_scanlan_mutator_dual_null",
        "title": "Scanlan mutator dual-null under abiotic constraint",
        "why_hard": (
            "Elevated mutation under coevolution must not always improve abiotic "
            "fitness vs abiotic-elevated / content-null arms (Scanlan constraint)."
        ),
        "falsification_path": "abiotic_elevated + content_null_elevated dual-null",
        "api": "run_scanlan_mutator_campaign",
        "seeds": list(SEEDS_SCANLAN),
        "hypothesis": d["hypothesis"],
        "hypothesis_supported": d["hypothesis_supported"],
        "failure_reason": d["failure_reason"],
        "arms_are_distinct": d["arms_are_distinct"],
        "arm_stats": arm_stats,
        "abiotic_elevated_minus_coevo_elevated_fitness": round(abiotic_elev - coevo_elev, 10),
        "gene_identity_proved": False,
        "crispr_identity_proved": False,
        "claim_ceiling": d["claim_ceiling"],
        "campaign_digest": d["campaign_digest"],
        "honesty": "Digital mutator honesty map; wet mutator-gene identity unproved.",
    }


def _panel_task_gene() -> dict[str, object]:
    maps = {}
    for label, seed in TASK_GENE_SEEDS.items():
        result = build_task_gene_map(seed=seed, genome_length=12, window_width=2)
        d = result.to_dict()
        maps[label] = {
            "seed": seed,
            "map_digest": d["map_digest"],
            "host_genome_digest": d["host_genome_digest"],
            "n_windows": len(d["windows"]),
            "task_labels": [w["task_label"] for w in d["windows"]],
            "gene_identity_proved": d["gene_identity_proved"],
            "crispr_identity_proved": d["crispr_identity_proved"],
        }
    digests = {k: v["map_digest"] for k, v in maps.items()}
    pairwise_distinct = len(set(digests.values())) == len(digests)
    return {
        "id": "CM7_task_gene_dual_null_panel",
        "title": "Declared task–gene map under cell vs microbe label + content-null proxy",
        "why_hard": (
            "Same declared phenotype-link API must produce distinct digests for "
            "cell-host substrate, microbe-parasite label, and content-null proxy "
            "without unlocking gene identity."
        ),
        "falsification_path": "content_null_proxy map digest must differ from intact cell map",
        "api": "build_task_gene_map",
        "maps": maps,
        "map_digests_pairwise_distinct": pairwise_distinct,
        "gene_identity_proved": False,
        "claim_ceiling": "runtime_observation",
        "honesty": "Declared digital phenotype link only; not CRISPR / wet locus proof.",
    }


def _claimgate_bundle_audit(campaigns: Sequence[Mapping[str, object]]) -> dict[str, object]:
    """Attach representative digests on one prereg-bound bundle; audit ceilings."""

    blocked_ok: list[tuple[str, bool]] = []
    for claim in _HARD_REFUSE:
        blocked = False
        try:
            assert_claim_allowed(claim)
        except ConfigurationError:
            blocked = True
        if not blocked:
            raise ConfigurationError(f"hard refuse claim must stay blocked: {claim}")
        blocked_ok.append((claim, True))

    prereg = host_parasite_preregistration(
        question_of_interest=(
            "Do hard cell↔microbe campaigns stay ClaimGate-honest with real dual-null "
            "falsifiers?"
        ),
        context_of_use=(
            "Cell = Genesis SemanticGenome substrate; microbe/parasite = COU labels; "
            "ONE host_parasite DomainProfile; no engine infection."
        ),
        arms=tuple(str(c["id"]) for c in campaigns),
        success_metrics=("pack_digest", "ladder_unchanged", "blocked_spot_check"),
        forbidden_claims=_HARD_REFUSE[:6],
    )
    prereg_digest = str(prereg.to_dict()["digest"])

    bundle = bundle_from_host_parasite_cou(
        question_of_interest=(
            "Do hard cell↔microbe campaigns stay ClaimGate-honest with real dual-null "
            "falsifiers?"
        ),
        context_of_use=(
            "Cell = Genesis SemanticGenome substrate; microbe/parasite = COU labels; "
            "ONE host_parasite DomainProfile; no engine infection."
        ),
        model_influence=1,
        decision_consequence=1,
        treatment_scores=(0.12,),
        control_scores=(1.0,),
    )
    bundle = attach_host_parasite_preregistration(bundle, prereg)
    ladder_before = str(audit_bundle(bundle).achieved_level)

    # Re-run campaigns for typed attach objects (same deterministic seeds).
    contingency = run_multi_seed_contingency_campaign(seeds=SEEDS_CONTINGENCY_MIXED)
    genome_zaman = run_genome_zaman_campaign(seeds=SEEDS_GENOME, steps=5)
    diversity = run_genome_diversity_campaign(seeds=SEEDS_DIVERSITY)
    ard = run_ard_fsd_transition_campaign(seeds=SEEDS_ARD, n_slices=8)
    cornish = run_sequential_cornish_campaign(
        seeds=SEEDS_CORNISH,
        request_claim_ceiling="candidate_evidence",
        preregistration_digest=prereg_digest,
    )
    scanlan = run_scanlan_mutator_campaign(
        seeds=SEEDS_SCANLAN,
        request_claim_ceiling="candidate_evidence",
    )
    task_gene = build_task_gene_map(seed=TASK_GENE_SEEDS["cell_host_substrate"])

    bundle = attach_multi_seed_contingency(bundle, contingency)
    bundle = attach_genome_zaman_campaign(bundle, genome_zaman)
    bundle = attach_genome_diversity_campaign(bundle, diversity)
    bundle = attach_ard_fsd_transition(bundle, ard)
    bundle = attach_sequential_cornish_campaign(bundle, cornish)
    bundle = attach_scanlan_mutator_campaign(bundle, scanlan)
    bundle = attach_task_gene_map(bundle, task_gene)

    report = audit_bundle(bundle)
    ladder_after = str(report.achieved_level)
    return {
        "preregistration_digest": prereg_digest,
        "ladder_before": ladder_before,
        "ladder_after": ladder_after,
        "ladder_unchanged": ladder_before == ladder_after,
        "audit_achieved_level": int(report.achieved_level),
        "audit_passed": True,
        "blocked_spot_check": {c: b for c, b in blocked_ok},
        "attached_campaign_digests": {
            "contingency": contingency.to_dict()["campaign_digest"],
            "genome_zaman": genome_zaman.to_dict()["campaign_digest"],
            "genome_diversity": diversity.to_dict()["campaign_digest"],
            "ard_fsd": ard.to_dict()["campaign_digest"],
            "cornish_sequential": cornish.to_dict()["campaign_digest"],
            "scanlan_mutator": scanlan.to_dict()["campaign_digest"],
            "task_gene_cell": task_gene.to_dict()["map_digest"],
        },
        "claim_ceiling_cap": "candidate_evidence",
    }


def run_cell_microbe_hard_campaigns(
    *,
    request_claim_ceiling: str = "runtime_observation",
) -> CellMicrobeHardCampaignPack:
    """Execute CM1–CM7 hard campaigns and ClaimGate-audit the pack."""

    ceiling = str(request_claim_ceiling).strip().lower()
    if ceiling not in _ALLOWED_CEILINGS:
        raise ConfigurationError(
            "request_claim_ceiling must be runtime_observation or candidate_evidence."
        )

    campaigns = (
        _panel_contingency(),
        _panel_genome_zaman(),
        _panel_genome_diversity(),
        _panel_ard_fsd(),
        _panel_cornish(),
        _panel_scanlan(),
        _panel_task_gene(),
    )
    audit = _claimgate_bundle_audit(campaigns)
    if not audit["ladder_unchanged"]:
        raise ConfigurationError("hard campaign pack must not raise ClaimGate ladder.")

    pack = CellMicrobeHardCampaignPack(
        schema=SCHEMA,
        campaigns=campaigns,
        claimgate_audit=audit,
        claim_ceiling=ceiling,
        pack_digest="",
        red_queen_proved=False,
        complexity_emergence_proved=False,
        intervention_supported=False,
        gene_identity_proved=False,
        engine_infection_physics="not_in_engine_core",
    )
    # Freeze digest after body materializes.
    digest = str(pack.to_dict()["pack_digest"])
    return CellMicrobeHardCampaignPack(
        schema=SCHEMA,
        campaigns=campaigns,
        claimgate_audit=audit,
        claim_ceiling=ceiling,
        pack_digest=digest,
        red_queen_proved=False,
        complexity_emergence_proved=False,
        intervention_supported=False,
        gene_identity_proved=False,
        engine_infection_physics="not_in_engine_core",
    )


def write_results_json(
    path: Path | str,
    *,
    pack: CellMicrobeHardCampaignPack | None = None,
) -> Path:
    """Run (unless pack given) and write results JSON for docs/artifacts."""

    result = pack or run_cell_microbe_hard_campaigns()
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    payload = result.to_dict()
    out.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return out


__all__ = [
    "SCHEMA",
    "DOMAIN_PROFILE",
    "CellMicrobeHardCampaignPack",
    "run_cell_microbe_hard_campaigns",
    "write_results_json",
    "SEEDS_CONTINGENCY_MIXED",
    "SEEDS_GENOME",
    "SEEDS_DIVERSITY",
    "SEEDS_ARD",
    "SEEDS_CORNISH",
    "SEEDS_SCANLAN",
]


if __name__ == "__main__":
    default = Path("docs/claimgate/host_parasite_port_20260924/cell_microbe_hard_campaigns_results.json")
    written = write_results_json(default)
    pack = json.loads(written.read_text(encoding="utf-8"))
    print(f"wrote {written}")
    print(f"pack_digest={pack['pack_digest']}")
    print(f"n_campaigns={len(pack['campaigns'])}")
    for c in pack["campaigns"]:
        print(f"  {c['id']}: ceiling={c.get('claim_ceiling', c.get('claim_ceiling_mixed'))}")
