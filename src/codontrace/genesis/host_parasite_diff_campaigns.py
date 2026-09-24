"""Differentiation campaigns (DX1–DX8) — ClaimGate / causal-audit layer.

These campaigns showcase what CodonTrace Genesis is *not*: another Avida.
Competitors can evolve hosts and parasites; Genesis additionally fail-closes
claim promotion, Price≠causality, measurement-only OEE, content-null traps,
replay-bound digests, domain-mismatched auditor posture, Cornish intervention
honesty, and engine-boundary locks.

Honest spectacle only: dramatic contrasts where the science allows; never fake
wins. Red Queen / intelligence / phage therapy / MODES-passed stay refused.
"""

from __future__ import annotations

import ast
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from codontrace.claimgate.adapters.host_parasite import (
    assert_claim_allowed,
    attach_genome_zaman_campaign,
    attach_price_causality_caution,
    attach_sequential_cornish_campaign,
    bundle_from_host_parasite_cou,
)
from codontrace.claimgate.adapters.host_parasite_prereg import (
    attach_host_parasite_preregistration,
    host_parasite_preregistration,
)
from codontrace.claimgate.domain import PROFILES, bundle_from_declared_scores
from codontrace.errors import ConfigurationError
from codontrace.genesis.canonical import canonical_digest, canonical_payload
from codontrace.genesis.claim_gate import ClaimRequest, ScientificClaimGate
from codontrace.genesis.host_parasite_ard_fsd_transition import (
    run_ard_fsd_transition_campaign,
)
from codontrace.genesis.host_parasite_attach_registry import BLOCKED_CLAIM_MATRIX
from codontrace.genesis.host_parasite_campaign import run_host_parasite_campaign
from codontrace.genesis.host_parasite_cornish_sequential import (
    default_sequential_schedule,
    run_sequential_cornish_campaign,
)
from codontrace.genesis.host_parasite_genome_diversity import (
    run_genome_diversity_campaign,
)
from codontrace.genesis.host_parasite_genome_zaman import run_genome_zaman_campaign
from codontrace.genesis.host_parasite_price_caution import (
    run_price_causality_caution_assay,
)
from codontrace.genesis.tokyo_type1 import (
    build_tokyo_type1_measurement_protocol,
    evaluate_tokyo_type1_measurement_claim,
    evaluate_tokyo_type1_pass_claim,
)

SCHEMA_DX = "host_parasite_diff_campaigns_v1"
DOMAIN_PROFILE = "host_parasite"

SEEDS_DX = (11, 22, 33)
SEEDS_DX_REPLAY = (7, 14, 21)
SEEDS_DX_PRICE = (11, 22, 33, 44)
SEEDS_DX_CORNISH = (11, 22, 33, 44)

# Theatrical refuse list — looks "amazing" metrics still cannot unlock these.
_THEATRICAL_REFUSE = (
    "intelligence_proved",
    "intelligence",
    "red_queen_proved",
    "modes_passed_proved",
    "modes_passed",
    "oee_modes_passed",
    "tokyo_type1_passed",
    "collective_intelligence",
    "phage_therapy_cleared",
    "complexity_emergence_proved",
    "gene_identity_proved",
    "crispr_identity_proved",
    "intervention_supported",
    "major_transition_proved",
    "virulence_optimized_for_humans",
    "biosafety_level_certified",
    "clinical_pathogen_model",
)


def _digest_body(body: Mapping[str, object]) -> str:
    return canonical_digest(canonical_payload(dict(body)))


def _refuse_map(claims: Sequence[str]) -> dict[str, bool]:
    out: dict[str, bool] = {}
    for claim in claims:
        blocked = False
        try:
            assert_claim_allowed(claim)
        except ConfigurationError:
            blocked = True
        out[claim] = blocked
    return out


# ---------------------------------------------------------------------------
# DX1 — ClaimLadder theatrical fail-closed
# ---------------------------------------------------------------------------


def panel_dx1_claimladder_theatrical() -> dict[str, object]:
    """Spectacular runtime metrics still refuse claim promotion."""

    diversity = run_genome_diversity_campaign(seeds=SEEDS_DX + (44, 55)).to_dict()
    ard = run_ard_fsd_transition_campaign(seeds=SEEDS_DX, n_slices=8).to_dict()
    by_arm = {}
    for o in diversity["arm_outcomes"]:
        by_arm.setdefault(o["arm"], []).append(float(o["entropy_delta_vs_baseline"]))
    biotic_delta = sum(by_arm["biotic_intact"]) / len(by_arm["biotic_intact"])
    content_delta = sum(by_arm["content_null"]) / len(by_arm["content_null"])
    early = next(
        s
        for s in ard["slices"]
        if s["arm"] == "parasite_coevolution" and s["seed"] == SEEDS_DX[0] and "early" in s["slice_id"]
    )
    late = next(
        s
        for s in ard["slices"]
        if s["arm"] == "parasite_coevolution" and s["seed"] == SEEDS_DX[0] and "late" in s["slice_id"]
    )
    cost_jump = float(late["mean_cost_of_generalism"]) - float(early["mean_cost_of_generalism"])

    refuses = _refuse_map(_THEATRICAL_REFUSE)
    all_blocked = all(refuses.values())
    # Also matrix coverage.
    matrix_blocked = all(c in BLOCKED_CLAIM_MATRIX for c in (
        "intelligence_proved",
        "red_queen_proved",
        "modes_passed_proved",
        "tokyo_type1_passed",
        "phage_therapy_cleared",
    ))
    success = (
        biotic_delta > 0.3
        and content_delta == 0.0
        and cost_jump > 0.2
        and ard["transition_observed"] is True
        and all_blocked
        and matrix_blocked
    )
    result = "SUCCESS" if success else ("PARTIAL" if all_blocked else "FAIL")
    return {
        "id": "DX1_claimladder_theatrical_failclosed",
        "title": "ClaimLadder theatrical fail-closed — spectacular runtime ≠ claim promotion",
        "literature_prediction": (
            "Reproducible runtime metrics do not auto-promote scientific claims "
            "(ClaimGate ladder; Pineau reproducibility checklist spirit)."
        ),
        "doi": "internal:CLAIM_LADDER + Pineau checklist spirit",
        "setup": {
            "seeds_diversity": list(SEEDS_DX + (44, 55)),
            "seeds_ard": list(SEEDS_DX),
            "refuse_claims": list(_THEATRICAL_REFUSE),
        },
        "metric": "biotic entropy Δ + ARD→FSD cost jump vs refuse-map all True",
        "success_criterion": (
            "biotic_entropy_delta > 0.3 AND content_null_delta == 0 AND "
            "ARD cost_jump > 0.2 AND transition_observed AND all theatrical "
            "claims blocked on assert_claim_allowed"
        ),
        "claimgate_ceiling": "candidate_evidence",
        "claimgate_refuses": list(_THEATRICAL_REFUSE[:8]),
        "result": result,
        "spectacular_metrics": {
            "biotic_entropy_delta": round(biotic_delta, 10),
            "content_null_entropy_delta": round(content_delta, 10),
            "ard_early_cost": early["mean_cost_of_generalism"],
            "ard_late_cost": late["mean_cost_of_generalism"],
            "ard_cost_jump": round(cost_jump, 10),
            "ard_early_label": early["label"],
            "ard_late_label": late["label"],
            "transition_observed": ard["transition_observed"],
        },
        "refuse_map": refuses,
        "all_theatrical_claims_blocked": all_blocked,
        "matrix_spot_check_ok": matrix_blocked,
        "contrast_headline": (
            f"biotic Δentropy={biotic_delta:.3f}, ARD→FSD cost jump={cost_jump:.3f}, "
            f"yet {sum(refuses.values())}/{len(refuses)} overclaims still blocked"
        ),
        "honesty": (
            "Runtime spectacle is real digital evidence at observation/candidate "
            "ceilings only; ClaimGate refuses intelligence / Red Queen / MODES-passed / "
            "phage therapy promotion."
        ),
    }


# ---------------------------------------------------------------------------
# DX2 — Okasha Price ≠ causality
# ---------------------------------------------------------------------------


def panel_dx2_price_not_causality() -> dict[str, object]:
    assay = run_price_causality_caution_assay(seeds=SEEDS_DX_PRICE)
    d = assay.to_dict()
    refuses = _refuse_map(
        ("major_transition_proved", "red_queen_proved", "intervention_supported")
    )
    # Attach path: Price numbers present, causal flags False.
    prereg = host_parasite_preregistration(
        question_of_interest="Does Price covariance unlock major transition?",
        context_of_use="DX2 Okasha caution; digital ClaimGate only.",
        arms=("price_summary",),
        success_metrics=("summary_digest",),
        forbidden_claims=("major_transition_proved",),
    )
    bundle = bundle_from_host_parasite_cou(
        question_of_interest="Does Price covariance unlock major transition?",
        context_of_use="DX2 Okasha caution; digital ClaimGate only.",
        model_influence=1,
        decision_consequence=1,
        treatment_scores=(0.3,),
        control_scores=(1.0,),
    )
    ready = attach_host_parasite_preregistration(bundle, prereg)
    attached = attach_price_causality_caution(ready, assay)
    payload = attached.extra["price_causality_caution"]
    success = (
        float(d["price_covariance"]) != 0.0
        and d["price_summary_is_causal"] is False
        and d["major_transition_proved"] is False
        and d["refusal_assay_passed"] is True
        and all(refuses.values())
        and payload.get("price_summary_is_causal") is False
    )
    result = "SUCCESS" if success else "FAIL"
    return {
        "id": "DX2_okasha_price_not_causality",
        "title": "Okasha Price≠causality gate — descriptive Price present, causal promotion refused",
        "literature_prediction": (
            "Price equation partitions are descriptive identities, not causal proofs "
            "of major transitions (Okasha multilevel caution)."
        ),
        "doi": "10.1098/rstb.2019.0365",
        "setup": {
            "seeds": list(SEEDS_DX_PRICE),
            "api": "run_price_causality_caution_assay + attach_price_causality_caution",
        },
        "metric": "price_covariance present ∧ ¬price_summary_is_causal ∧ refusal_assay_passed",
        "success_criterion": (
            "nonzero price_covariance AND price_summary_is_causal=False AND "
            "major_transition_proved=False AND refusal_assay_passed AND "
            "major_transition_proved blocked on assert"
        ),
        "claimgate_ceiling": "runtime_observation",
        "claimgate_refuses": ["major_transition_proved", "red_queen_proved"],
        "result": result,
        "price_covariance": d["price_covariance"],
        "within_group_term": d["within_group_term"],
        "between_group_term": d["between_group_term"],
        "price_summary_is_causal": False,
        "major_transition_proved": False,
        "refusal_assay_passed": d["refusal_assay_passed"],
        "refuse_map": refuses,
        "attach_payload_causal_flag": payload.get("price_summary_is_causal"),
        "summary_digest": d["summary_digest"],
        "contrast_headline": (
            f"Price covariance={d['price_covariance']:.6f} available as diagnostic; "
            "ClaimGate keeps major_transition_proved=False (Okasha)"
        ),
        "honesty": "Descriptive scaffold only; not causal mechanism support.",
    }


# ---------------------------------------------------------------------------
# DX3 — Channon / MODES measurement-only honesty
# ---------------------------------------------------------------------------


def panel_dx3_modes_measurement_only() -> dict[str, object]:
    protocol = build_tokyo_type1_measurement_protocol(seed_count=3)
    pdata = protocol.to_dict()
    meas = evaluate_tokyo_type1_measurement_claim(protocol)
    pas = evaluate_tokyo_type1_pass_claim(protocol)
    refuses = _refuse_map(
        ("tokyo_type1_passed", "modes_passed", "modes_passed_proved", "oee_modes_passed")
    )
    # ScientificClaimGate direct overclaim.
    gate = ScientificClaimGate()
    modes_direct = gate.decide(ClaimRequest("modes_passed_proved", {}, evidence_digests=(protocol.digest,)))
    success = (
        meas.allowed is True
        and meas.final_claim == "tokyo_type1_measurement_only"
        and pas.allowed is False
        and pdata.get("tokyo_type1_passed") in (False, None)
        and all(refuses.values())
        and modes_direct.allowed is False
    )
    result = "SUCCESS" if success else "FAIL"
    return {
        "id": "DX3_channon_modes_measurement_only",
        "title": "Channon/MODES measurement-only — observe without pass-washing",
        "literature_prediction": (
            "Tokyo Type 1 / MODES surfaces can be *measured* without declaring "
            "pass (Channon 2024 procedure; Dolson et al. 2019 MODES)."
        ),
        "doi": "10.1162/artl_a_00280",
        "doi_channon": "10.1162/artl_a_00430",
        "setup": {
            "api": "build_tokyo_type1_measurement_protocol",
            "seed_count": 3,
        },
        "metric": "measurement claim allowed ∧ pass claims refused",
        "success_criterion": (
            "tokyo_type1_measurement_only allowed AND tokyo_type1_passed / "
            "modes_passed* refused"
        ),
        "claimgate_ceiling": "tokyo_type1_measurement_only",
        "claimgate_refuses": [
            "tokyo_type1_passed",
            "modes_passed",
            "modes_passed_proved",
            "oee_modes_passed",
        ],
        "result": result,
        "measurement_allowed": meas.allowed,
        "measurement_final_claim": meas.final_claim,
        "pass_allowed": pas.allowed,
        "pass_final_claim": pas.final_claim,
        "measurement_status": pdata.get("measurement_status"),
        "refuse_map": refuses,
        "modes_direct_allowed": modes_direct.allowed,
        "contrast_headline": (
            f"measurement_only ALLOWED ({meas.final_claim}); "
            f"tokyo_type1_passed / modes_passed* REFUSED"
        ),
        "honesty": "Measurement vocabulary ≠ Type-1 / MODES pass verdict.",
    }


# ---------------------------------------------------------------------------
# DX4 — Replay integrity spectacle
# ---------------------------------------------------------------------------


def panel_dx4_replay_integrity_spectacle() -> dict[str, object]:
    same_a = []
    same_b = []
    for seed in SEEDS_DX_REPLAY:
        same_a.append(run_genome_diversity_campaign(seeds=(seed,)).to_dict()["campaign_digest"])
        same_b.append(run_genome_diversity_campaign(seeds=(seed,)).to_dict()["campaign_digest"])
    stable = same_a == same_b
    # Mutated seed → mismatch.
    base = run_genome_diversity_campaign(seeds=(SEEDS_DX_REPLAY[0],)).to_dict()["campaign_digest"]
    mutated_seed = run_genome_diversity_campaign(
        seeds=(SEEDS_DX_REPLAY[0] + 1,)
    ).to_dict()["campaign_digest"]
    seed_mismatch = base != mutated_seed
    # Mutated claim payload → refuse.
    claim_refuse_ok = False
    try:
        assert_claim_allowed("red_queen_proved")
    except ConfigurationError:
        claim_refuse_ok = True
    # Mutated attach: evil intervention_supported on Cornish.
    prereg = host_parasite_preregistration(
        question_of_interest="Replay spectacle Cornish",
        context_of_use="DX4; digital only.",
        arms=tuple(s["step_id"] for s in default_sequential_schedule()),
        success_metrics=("campaign_digest",),
        forbidden_claims=("intervention_supported",),
    )
    camp = run_sequential_cornish_campaign(
        seeds=SEEDS_DX_CORNISH,
        request_claim_ceiling="candidate_evidence",
        preregistration_digest=str(prereg.to_dict()["digest"]),
    )
    bundle = bundle_from_host_parasite_cou(
        question_of_interest="Replay spectacle Cornish",
        context_of_use="DX4; digital only.",
        model_influence=1,
        decision_consequence=1,
        treatment_scores=(0.2,),
        control_scores=(1.0,),
    )
    ready = attach_host_parasite_preregistration(bundle, prereg)
    attach_sequential_cornish_campaign(ready, camp)  # honest attach OK
    from dataclasses import replace

    evil = replace(camp, intervention_supported=True)
    evil_refused = False
    try:
        attach_sequential_cornish_campaign(ready, evil)
    except ConfigurationError:
        evil_refused = True
    cross_distinct = len(set(same_a)) == len(same_a)
    success = stable and seed_mismatch and claim_refuse_ok and evil_refused and cross_distinct
    result = "SUCCESS" if success else "FAIL"
    return {
        "id": "DX4_replay_integrity_spectacle",
        "title": "Replay integrity spectacle — same seed identical; mutated seed/claim diverge or refuse",
        "literature_prediction": (
            "Bit-stable digests under identical seeds; claim-bound attach refuses "
            "mutated honesty flags (Genesis ENGINE_REPLAY_CONTRACT)."
        ),
        "doi": "internal:ENGINE_REPLAY_CONTRACT",
        "setup": {
            "seeds": list(SEEDS_DX_REPLAY),
            "apis": [
                "run_genome_diversity_campaign",
                "attach_sequential_cornish_campaign",
            ],
        },
        "metric": "digest equality / inequality / attach refuse on mutated flags",
        "success_criterion": (
            "within-seed digests identical AND mutated seed mismatches AND "
            "overclaim assert refuses AND evil intervention_supported attach refuses"
        ),
        "claimgate_ceiling": "runtime_observation",
        "claimgate_refuses": ["red_queen_proved", "intervention_supported"],
        "result": result,
        "within_seed_stable": stable,
        "cross_seed_distinct": cross_distinct,
        "mutated_seed_mismatches": seed_mismatch,
        "overclaim_assert_refused": claim_refuse_ok,
        "mutated_attach_refused": evil_refused,
        "digest_rep1_prefixes": [d[:16] for d in same_a],
        "digest_rep2_prefixes": [d[:16] for d in same_b],
        "base_vs_mutated_prefixes": [base[:16], mutated_seed[:16]],
        "contrast_headline": (
            "Identical seeds → identical digests; seed+1 → mismatch; "
            "forged intervention_supported attach → ConfigurationError"
        ),
        "honesty": "Replay/claim binding only; not scientific escalation.",
    }


# ---------------------------------------------------------------------------
# DX5 — Content-null / HE-style trap
# ---------------------------------------------------------------------------


def panel_dx5_content_null_trap() -> dict[str, object]:
    # Without content_null → candidate_evidence fail-closed.
    missing_null_refused = False
    missing_msg = ""
    try:
        run_host_parasite_campaign(
            seeds=(1, 2),
            arms=("intact", "structure_null"),
            request_claim_ceiling="candidate_evidence",
        )
    except ConfigurationError as exc:
        missing_null_refused = True
        missing_msg = str(exc)
    abiotic_only_refused = False
    try:
        run_host_parasite_campaign(
            seeds=(1, 2),
            arms=("intact", "abiotic_only"),
            request_claim_ceiling="candidate_evidence",
        )
    except ConfigurationError:
        abiotic_only_refused = True

    ok = run_host_parasite_campaign(
        seeds=(1, 2),
        arms=("intact", "content_null", "abiotic_only"),
        request_claim_ceiling="candidate_evidence",
        steal_fraction=0.8,
    )
    d = ok.to_dict()
    scores = {a["arm"]: float(a["mean_score"]) for a in d["arm_results"]}
    # Eye-catching: intact looks "damaged" (0.2) vs content_null (1.0) —
    # naive reader might skip the null; ClaimGate requires it for ceiling.
    dramatic = scores["intact"] < 0.5 and scores["content_null"] > 0.8
    success = (
        missing_null_refused
        and abiotic_only_refused
        and d["falsification_rules_passed"] is True
        and d["claim_ceiling"] == "candidate_evidence"
        and dramatic
    )
    result = "SUCCESS" if success else "FAIL"
    return {
        "id": "DX5_content_null_he_trap",
        "title": "Content-null HE-style trap — treatment looks dramatic until null required",
        "literature_prediction": (
            "Candidate evidence requires content-null falsifiers (HE / Floreano "
            "honesty; Genesis host_parasite campaign ceiling rules)."
        ),
        "doi": "internal:HE02 dual-null + Floreano honesty",
        "setup": {
            "seeds": [1, 2],
            "arms_fail": ["intact+structure_null", "intact+abiotic_only"],
            "arms_pass": ["intact", "content_null", "abiotic_only"],
            "steal_fraction": 0.8,
        },
        "metric": "candidate_evidence refuse without content_null; scores intact vs null",
        "success_criterion": (
            "structure/abiotic-only paths raise ConfigurationError AND "
            "intact+content_null clears candidate_evidence AND intact score << content_null"
        ),
        "claimgate_ceiling": "candidate_evidence",
        "claimgate_refuses": ["red_queen_proved", "phage_therapy_cleared"],
        "result": result,
        "missing_content_null_refused": missing_null_refused,
        "abiotic_only_refused": abiotic_only_refused,
        "refusal_message_prefix": missing_msg[:120],
        "arm_mean_scores": scores,
        "falsification_rules_passed": d["falsification_rules_passed"],
        "granted_ceiling": d["claim_ceiling"],
        "contrast_headline": (
            f"intact mean_score={scores['intact']:.2f} vs content_null={scores['content_null']:.2f}; "
            "without content_null arm, candidate_evidence is refused"
        ),
        "honesty": (
            "Low intact score is digital steal drawdown, not clinical harm; "
            "null proves the contrast is payload-dependent."
        ),
    }


# ---------------------------------------------------------------------------
# DX6 — Cross-simulator auditor posture
# ---------------------------------------------------------------------------


def panel_dx6_cross_domain_auditor() -> dict[str, object]:
    hp_blocks: dict[str, bool] = {}
    for claim in (
        "phage_therapy_cleared",
        "red_queen_proved",
        "biosafety_level_certified",
        "clinical_pathogen_model",
    ):
        blocked = False
        try:
            bundle_from_declared_scores(
                profile="host_parasite",
                question_of_interest="Auditor posture probe",
                context_of_use="DX6 domain matrix; digital only.",
                model_influence=1,
                decision_consequence=1,
                treatment_scores=(0.9,),
                control_scores=(0.1,),
                claimed=claim,
            )
        except ConfigurationError:
            blocked = True
        hp_blocks[claim] = blocked

    # Other domains do NOT share the HP clinical refuse list for phage —
    # that is the auditor-as-port differentiation (profile-scoped matrix).
    other_allows_phage: dict[str, bool] = {}
    for name in PROFILES:
        if name == "host_parasite":
            continue
        allowed = True
        try:
            bundle_from_declared_scores(
                profile=name,
                question_of_interest="Auditor posture probe",
                context_of_use="DX6 wrong-domain contrast; digital only.",
                model_influence=1,
                decision_consequence=1,
                treatment_scores=(0.9,),
                control_scores=(0.1,),
                claimed="phage_therapy_cleared",
            )
        except ConfigurationError:
            allowed = False
        other_allows_phage[name] = allowed

    # Attach requires host_parasite domain bundle.
    zaman = run_genome_zaman_campaign(seeds=SEEDS_DX, steps=3)
    prereg = host_parasite_preregistration(
        question_of_interest="Domain attach probe",
        context_of_use="DX6; digital only.",
        arms=("zaman",),
        success_metrics=("campaign_digest",),
        forbidden_claims=("red_queen_proved",),
    )
    good = bundle_from_host_parasite_cou(
        question_of_interest="Domain attach probe",
        context_of_use="DX6; digital only.",
        model_influence=1,
        decision_consequence=1,
        treatment_scores=(0.2,),
        control_scores=(1.0,),
    )
    good = attach_host_parasite_preregistration(good, prereg)
    attach_ok = False
    try:
        attach_genome_zaman_campaign(good, zaman)
        attach_ok = True
    except ConfigurationError:
        attach_ok = False

    # Wrong-domain bundle (alife) must refuse HP attach.
    wrong = bundle_from_declared_scores(
        profile="alife",
        question_of_interest="Domain attach probe",
        context_of_use="DX6 wrong domain; digital only.",
        model_influence=1,
        decision_consequence=1,
        treatment_scores=(0.2,),
        control_scores=(1.0,),
        claimed="runtime_observation",
    )
    # alife bundle has no HP prereg; attach should refuse domain.
    wrong_attach_refused = False
    try:
        attach_genome_zaman_campaign(wrong, zaman)
    except ConfigurationError:
        wrong_attach_refused = True

    success = (
        all(hp_blocks.values())
        and any(other_allows_phage.values())  # matrix is profile-scoped
        and attach_ok
        and wrong_attach_refused
    )
    result = "SUCCESS" if success else "FAIL"
    return {
        "id": "DX6_cross_domain_auditor_posture",
        "title": "Cross-simulator auditor posture — ClaimGate matrix is DomainProfile-scoped",
        "literature_prediction": (
            "Auditor-not-engine: the same ClaimGate refuse matrix applies to the "
            "host_parasite DomainProfile port; mismatched domain attaches refuse."
        ),
        "doi": "internal:ARCHITECTURE_PORTS + DomainProfile",
        "setup": {
            "profiles": list(PROFILES),
            "hp_blocked_probes": list(hp_blocks),
            "attach_api": "attach_genome_zaman_campaign",
        },
        "metric": "HP blocks clinical/RQ claims; wrong-domain attach refuses; HP attach OK",
        "success_criterion": (
            "host_parasite blocks phage/RQ/BSL/clinical AND at least one other "
            "profile does not share phage block AND HP attach works AND alife "
            "attach of HP campaign refuses"
        ),
        "claimgate_ceiling": "runtime_observation",
        "claimgate_refuses": list(hp_blocks),
        "result": result,
        "host_parasite_blocks": hp_blocks,
        "other_profiles_allow_phage_string": other_allows_phage,
        "hp_attach_ok": attach_ok,
        "wrong_domain_attach_refused": wrong_attach_refused,
        "contrast_headline": (
            "host_parasite DomainProfile blocks phage_therapy_cleared; "
            f"other profiles allow the string ({other_allows_phage}); "
            "HP campaign attach refused on alife bundle"
        ),
        "honesty": (
            "Profile-scoped refuse lists are an auditor feature, not a claim that "
            "other domains cleared phage therapy."
        ),
    }


# ---------------------------------------------------------------------------
# DX7 — Cornish headline (looks fixed, ClaimGate says no)
# ---------------------------------------------------------------------------


def panel_dx7_cornish_headline() -> dict[str, object]:
    prereg = host_parasite_preregistration(
        question_of_interest="Looks fixed — does ClaimGate grant intervention_supported?",
        context_of_use="DX7 Cornish headline; digital only.",
        arms=tuple(s["step_id"] for s in default_sequential_schedule()),
        success_metrics=("campaign_digest", "intervention_supported"),
        forbidden_claims=("intervention_supported", "red_queen_proved"),
    )
    digest = str(prereg.to_dict()["digest"])
    camp = run_sequential_cornish_campaign(
        seeds=SEEDS_DX_CORNISH,
        request_claim_ceiling="candidate_evidence",
        preregistration_digest=digest,
    )
    d = camp.to_dict()
    steps = d["step_outcomes"]
    obs = next(s for s in steps if s["kind"] == "observational")
    ints = [s for s in steps if s["kind"] == "intervention"]
    obs_score = float(obs["score"])
    int_scores = [float(s["score"]) for s in ints]
    success = (
        d["observational_match"] is True
        and d["interventions_executed"] is True
        and d["intervention_supported"] is False
        and obs_score <= 0.25
        and all(s >= 0.99 for s in int_scores)
    )
    result = "SUCCESS" if success else "FAIL"
    return {
        "id": "DX7_cornish_looks_fixed_claimgate_says_no",
        "title": "Cornish headline — obs 0.2 vs forced ints 1.0/1.0/1.0 still refuses intervention_supported",
        "literature_prediction": (
            "Observational history match does not license interventional claims "
            "(Cornish et al. JMLR / arXiv:2301.07210)."
        ),
        "doi": "arXiv:2301.07210",
        "setup": {
            "seeds": list(SEEDS_DX_CORNISH),
            "api": "run_sequential_cornish_campaign",
        },
        "metric": "obs_score ≤ 0.25 ∧ all intervention scores ≥ 0.99 ∧ ¬intervention_supported",
        "success_criterion": (
            "observational_match AND interventions_executed AND "
            "intervention_supported=False AND obs≤0.25 AND ints all ≥0.99"
        ),
        "claimgate_ceiling": "candidate_evidence",
        "claimgate_refuses": ["intervention_supported", "phage_therapy_cleared"],
        "result": result,
        "obs_score": obs_score,
        "intervention_scores": int_scores,
        "observational_match": d["observational_match"],
        "interventions_executed": d["interventions_executed"],
        "intervention_supported": False,
        "later_intervention_failed": d["later_intervention_failed"],
        "contrast_headline": (
            f"obs_score={obs_score} vs intervention_scores={int_scores} — "
            "looks fixed; ClaimGate intervention_supported=False"
        ),
        "honesty": "Cornish rule; not clinical decision support.",
    }


# ---------------------------------------------------------------------------
# DX8 — Engine boundary hard lock (AST)
# ---------------------------------------------------------------------------


def panel_dx8_engine_boundary() -> dict[str, object]:
    root = Path(__file__).resolve().parents[3]
    genesis_engine = root / "src" / "codontrace" / "genesis" / "engine.py"
    core_engine = root / "src" / "codontrace" / "engine.py"
    env_path = root / "src" / "codontrace" / "genesis" / "host_parasite_env.py"
    forbidden = (
        "try_horizontal_inject",
        "infection_eligible",
        "seed_parasite_seat",
        "HostParasiteEnv",
        "steal_fraction",
        "parasite_payload",
        "virulence_optimized_for_humans",
    )
    hits: list[dict[str, str]] = []
    for path in (genesis_engine, core_engine):
        text = path.read_text(encoding="utf-8")
        for tok in forbidden:
            if tok in text:
                hits.append({"file": str(path.relative_to(root)), "token": tok})
    env_text = env_path.read_text(encoding="utf-8")
    env_ok = all(
        tok in env_text
        for tok in ("try_horizontal_inject", "infection_eligible", "HostParasiteEnv")
    )
    # AST: no FunctionDef named like infection in core engine.
    core_tree = ast.parse(core_engine.read_text(encoding="utf-8"))
    fn_names = {
        n.name
        for n in ast.walk(core_tree)
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
    }
    bad_fns = sorted(
        n
        for n in fn_names
        if any(k in n.lower() for k in ("infect", "parasite_inject", "viral_load"))
    )
    thin = "from codontrace.engine import" in genesis_engine.read_text(encoding="utf-8")
    success = len(hits) == 0 and env_ok and not bad_fns and thin
    result = "SUCCESS" if success else "FAIL"
    return {
        "id": "DX8_engine_boundary_hard_lock",
        "title": "Engine boundary hard lock — infection/virulence physics absent from engine.py",
        "literature_prediction": (
            "ALife = engine; host–parasite = DomainProfile/port "
            "(CodonTrace Genesis ARCHITECTURE_PORTS)."
        ),
        "doi": "internal:ARCHITECTURE_PORTS",
        "setup": {
            "scanned": [
                "src/codontrace/genesis/engine.py",
                "src/codontrace/engine.py",
            ],
            "positive_control": "src/codontrace/genesis/host_parasite_env.py",
            "forbidden_tokens": list(forbidden),
        },
        "metric": "zero forbidden tokens in engines; env retains inject; no infect* fn in core",
        "success_criterion": (
            "No infection/virulence helpers in engine modules AND env has inject "
            "APIs AND core engine has no infect*/parasite_inject functions"
        ),
        "claimgate_ceiling": "runtime_observation",
        "claimgate_refuses": ["phage_therapy_cleared", "biosafety_level_certified"],
        "result": result,
        "forbidden_hits": hits,
        "env_has_infection_helpers": env_ok,
        "core_engine_bad_functions": bad_fns,
        "genesis_engine_thin_reexport": thin,
        "contrast_headline": (
            "engine.py: zero infection tokens; host_parasite_env.py: inject APIs present"
        ),
        "honesty": "Architecture regression; not a biological claim.",
    }


def run_diff_campaigns() -> tuple[dict[str, object], ...]:
    """Execute DX1–DX8 differentiation panels."""

    return (
        panel_dx1_claimladder_theatrical(),
        panel_dx2_price_not_causality(),
        panel_dx3_modes_measurement_only(),
        panel_dx4_replay_integrity_spectacle(),
        panel_dx5_content_null_trap(),
        panel_dx6_cross_domain_auditor(),
        panel_dx7_cornish_headline(),
        panel_dx8_engine_boundary(),
    )


__all__ = [
    "SCHEMA_DX",
    "DOMAIN_PROFILE",
    "run_diff_campaigns",
    "panel_dx1_claimladder_theatrical",
    "panel_dx2_price_not_causality",
    "panel_dx3_modes_measurement_only",
    "panel_dx4_replay_integrity_spectacle",
    "panel_dx5_content_null_trap",
    "panel_dx6_cross_domain_auditor",
    "panel_dx7_cornish_headline",
    "panel_dx8_engine_boundary",
]
