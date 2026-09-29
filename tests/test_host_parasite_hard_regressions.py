"""Hard unsolved host–parasite ClaimGate regressions (post Wave 6).

These cases target honesty / wiring holes that soft Wave-5/6 smoke does not
stress: adversarial claimed= strings, content-null fail-closed ceilings,
Cornish all-success schedules, HE_HP schema integrity, contingency support
edges, and replay-digest registration drift (#50).
"""

from __future__ import annotations

import ast
import json
from dataclasses import replace
from pathlib import Path

import pytest

from codontrace.claimgate import HOST_PARASITE, audit_bundle
from codontrace.claimgate.adapters.host_parasite import (
    BLOCKED_HOST_PARASITE_CLAIMS,
    assert_claim_allowed,
    attach_multi_seed_contingency,
    attach_sequential_cornish_campaign,
    bundle_from_host_parasite_cou,
)
from codontrace.claimgate.adapters.host_parasite_prereg import (
    attach_host_parasite_preregistration,
    host_parasite_preregistration,
)
from codontrace.errors import ConfigurationError
from codontrace.genesis.host_parasite_attach_registry import BLOCKED_CLAIM_MATRIX
from codontrace.genesis.host_parasite_campaign import run_host_parasite_campaign
from codontrace.genesis.host_parasite_contingency import run_multi_seed_contingency_campaign
from codontrace.genesis.host_parasite_cornish_sequential import (
    run_sequential_cornish_campaign,
)
from codontrace.genesis.host_parasite_he_hp_refresh import (
    build_he_hp_locked_digest_refresh_note,
    validate_he_hp_locked_pack,
)
from codontrace.genesis.replay_integrity import (
    NON_REPLAY_CRITICAL_DIGEST_CLASSES,
    STRICT_REPLAY_CRITICAL_DIGEST_CLASSES,
    audit_replay_digest_policy_registry,
)
from codontrace.genesis.text_digest import sha256_text_file

ROOT = Path(__file__).resolve().parents[1]
PIN_SPECS = (
    (
        "docs/hard_experiment_01/results_v7.json",
        "35bb593604438797755e5e7b28af4d1371992a6181a403d08005f7f45421cbd6",
    ),
    (
        "docs/claimgate/risk_bar.json",
        "4dbe4aa3a6ef8e771f180d2a6589c64b0dd5ffebe0aa73703a7256c17d771cd7",
    ),
    (
        "docs/claimgate/biomedical_study.json",
        "9685f2fbafb21477d977dfa0c0bf73e02bea81d084e7605978ea25c47bf5ddce",
    ),
)
_HE_HP_PATH = ROOT / "docs" / "hard_experiment_hp" / "locked_campaign_digests.json"

# Matrix / hard-lock refuse strings that soft Phase-18 tests previously
# papered over with a synthetic raise instead of assert_claim_allowed.
_HARD_REFUSE_CLAIMS = (
    "modes_passed_proved",
    "oee_type1_proved",
    "complexity_emergence_proved",
    "gene_identity_proved",
    "intelligence_proved",
    "intervention_supported",
    "oee_modes_passed",
    "modes_passed",
    "phage_therapy_cleared",
    "red_queen_proved",
    "crispr_identity_proved",
    "biosafety_level_certified",
    "clinical_pathogen_model",
)


@pytest.mark.parametrize("claim", _HARD_REFUSE_CLAIMS)
def test_hc1_matrix_claims_fail_closed_on_assert_and_bundle(claim: str) -> None:
    """HC1: journal matrix refuse-list must be fail-closed on claimed=."""

    assert claim in BLOCKED_CLAIM_MATRIX
    assert claim in HOST_PARASITE.blocked_claims
    assert claim in BLOCKED_HOST_PARASITE_CLAIMS
    with pytest.raises(ConfigurationError):
        assert_claim_allowed(claim)
    with pytest.raises(ConfigurationError):
        bundle_from_host_parasite_cou(
            question_of_interest="Adversarial claimed= probe",
            context_of_use="Hard regression only; digital ClaimGate.",
            model_influence=1,
            decision_consequence=1,
            treatment_scores=(0.2,),
            control_scores=(1.0,),
            claimed=claim,
        )


def test_hc2_adversarial_aliases_cannot_bypass_intelligence_or_modes() -> None:
    """HC2: alias spellings must not bypass blocked intelligence / OEE-MODES."""

    # Canonical block exists.
    with pytest.raises(ConfigurationError):
        assert_claim_allowed("intelligence")
    # Alias that previously slipped through.
    with pytest.raises(ConfigurationError):
        assert_claim_allowed("intelligence_proved")
    with pytest.raises(ConfigurationError):
        assert_claim_allowed("modes_passed")
    with pytest.raises(ConfigurationError):
        assert_claim_allowed("oee_modes_passed")


def test_hc3_sequential_all_success_still_refuses_intervention_supported() -> None:
    """HC3: Cornish — later_intervention_failed=False must not grant support."""

    prereg = host_parasite_preregistration(
        question_of_interest="Does observational match grant intervention support?",
        context_of_use="Sequential Cornish deepening; digital only.",
        arms=(
            "obs_baseline",
            "int_remove_parasites",
            "int_content_null",
            "int_steal_ablation",
        ),
        success_metrics=("campaign_digest", "intervention_supported"),
        forbidden_claims=("red_queen_proved",),
    )
    digest = prereg.to_dict()["digest"]
    result = run_sequential_cornish_campaign(
        seeds=(1,),
        preregistration_digest=digest,
    )
    assert result.observational_match is True
    assert result.interventions_executed is True
    # Default schedule: interventions are effect-distinct → later_failed False.
    assert result.later_intervention_failed is False
    assert result.intervention_supported is False

    bundle = bundle_from_host_parasite_cou(
        question_of_interest="Does observational match grant intervention support?",
        context_of_use="Sequential Cornish deepening; digital only.",
        model_influence=1,
        decision_consequence=1,
        treatment_scores=(0.2,),
        control_scores=(1.0,),
    )
    ready = attach_host_parasite_preregistration(bundle, prereg)
    before = audit_bundle(ready).achieved_level
    attached = attach_sequential_cornish_campaign(ready, result)
    assert attached.extra["cornish_sequential_campaign"]["intervention_supported"] is False
    assert audit_bundle(attached).achieved_level == before

    evil = replace(result, intervention_supported=True)
    with pytest.raises(ConfigurationError, match="intervention_supported"):
        attach_sequential_cornish_campaign(ready, evil)


def test_hc4_candidate_evidence_requires_content_null_arm() -> None:
    """HC4: Floreano honesty — structure/abiotic alone cannot clear ceiling."""

    with pytest.raises(ConfigurationError, match="falsification"):
        run_host_parasite_campaign(
            seeds=(1, 2),
            arms=("intact", "structure_null"),
            request_claim_ceiling="candidate_evidence",
        )
    with pytest.raises(ConfigurationError, match="falsification"):
        run_host_parasite_campaign(
            seeds=(1, 2),
            arms=("intact", "abiotic_only"),
            request_claim_ceiling="candidate_evidence",
        )
    # Content-null present (with intact) can clear when contrast holds.
    ok = run_host_parasite_campaign(
        seeds=(1, 2),
        arms=("intact", "content_null", "abiotic_only"),
        request_claim_ceiling="candidate_evidence",
        steal_fraction=0.8,
    )
    assert ok.falsification_rules_passed is True
    assert ok.claim_ceiling == "candidate_evidence"
    # steal=0 still distinguishes content-null via empty payloads.
    zero = run_host_parasite_campaign(
        seeds=(3, 4),
        arms=("intact", "content_null", "structure_null"),
        request_claim_ceiling="candidate_evidence",
        steal_fraction=0.0,
    )
    assert zero.falsification_rules_passed is True


def test_hc5_he_hp_locked_pack_schema_integrity() -> None:
    """HC5: HE_HP JSON schema / engine / honesty flags stay fail-closed."""

    locked = json.loads(_HE_HP_PATH.read_text(encoding="utf-8"))
    validate_he_hp_locked_pack(locked)
    assert locked["schema"] == "hard_experiment_hp_locked_digests_v1"
    assert locked["engine_infection_physics"] == "not_in_engine_core"
    assert locked["intervention_supported"] is False
    assert locked["complexity_emergence_proved"] is False
    assert locked["mutualism_equals_success"] is False
    note = build_he_hp_locked_digest_refresh_note()
    assert note.locks_still_valid is True
    assert note.baic_pins_untouched is True

    evil = dict(locked)
    evil["engine_infection_physics"] = "in_engine_core"
    with pytest.raises(ConfigurationError, match="engine_infection_physics"):
        validate_he_hp_locked_pack(evil)
    evil2 = dict(locked)
    evil2["schema"] = "host_parasite_forged_v9"
    with pytest.raises(ConfigurationError, match="schema"):
        validate_he_hp_locked_pack(evil2)
    evil3 = dict(locked)
    evil3["intervention_supported"] = True
    with pytest.raises(ConfigurationError, match="intervention_supported"):
        validate_he_hp_locked_pack(evil3)


def test_hc6_contingency_supporting_seeds_cannot_prove_complexity() -> None:
    """HC6: seed triples that still 'support' the law must not prove emergence."""

    # (1, 2, 4) is a known supporting triple under runtime_observation.
    result = run_multi_seed_contingency_campaign(
        seeds=(1, 2, 4),
        request_claim_ceiling="runtime_observation",
    )
    assert result.hypothesis_supported is True
    assert result.complexity_emergence_proved is False
    assert result.red_queen_proved is False
    assert result.seed_digests_are_distinct is True
    present = [o for o in result.seed_outcomes if o.arm == "parasite_present"]
    absent = [o for o in result.seed_outcomes if o.arm == "parasite_absent"]
    assert present and absent
    assert {o.seed_digest for o in present} != {o.seed_digest for o in absent}

    with pytest.raises(ConfigurationError, match="candidate_evidence"):
        run_multi_seed_contingency_campaign(
            seeds=(1, 2, 4),
            request_claim_ceiling="candidate_evidence",
        )

    prereg = host_parasite_preregistration(
        question_of_interest="Is complexity rise under parasitism seed-contingent?",
        context_of_use="S1 multi-seed contingency; complexity emergence unproved.",
        arms=("parasite_present", "parasite_absent"),
        success_metrics=("seed_digests_are_distinct", "cross_seed_variance"),
        forbidden_claims=("red_queen_proved",),
    )
    bundle = bundle_from_host_parasite_cou(
        question_of_interest="Is complexity rise under parasitism seed-contingent?",
        context_of_use="S1 multi-seed contingency; complexity emergence unproved.",
        model_influence=1,
        decision_consequence=1,
        treatment_scores=(0.2,),
        control_scores=(1.0,),
    )
    ready = attach_host_parasite_preregistration(bundle, prereg)
    before = audit_bundle(ready).achieved_level
    attached = attach_multi_seed_contingency(ready, result)
    record = attached.extra["multi_seed_contingency"]
    assert record["complexity_emergence_proved"] is False
    assert record["raises_claim_ladder"] is False
    assert record["hypothesis_supported"] is True
    assert audit_bundle(attached).achieved_level == before

    evil = replace(result, complexity_emergence_proved=True)
    with pytest.raises(ConfigurationError, match="proved flags"):
        attach_multi_seed_contingency(ready, evil)


def test_hc7_host_parasite_digest_classes_stay_registered() -> None:
    """HC7: replay-policy registration regression (#50) for HP digests."""

    registered = set(NON_REPLAY_CRITICAL_DIGEST_CLASSES) | set(
        STRICT_REPLAY_CRITICAL_DIGEST_CLASSES
    )
    found: set[str] = set()
    for source in (ROOT / "src" / "codontrace" / "genesis").glob("host_parasite*.py"):
        tree = ast.parse(source.read_text(encoding="utf-8"))
        module = f"codontrace.genesis.{source.stem}"
        for node in ast.walk(tree):
            if not isinstance(node, ast.ClassDef):
                continue
            is_dc = False
            for decorator in node.decorator_list:
                if isinstance(decorator, ast.Name) and decorator.id == "dataclass":
                    is_dc = True
                if isinstance(decorator, ast.Call):
                    fn = decorator.func
                    if isinstance(fn, ast.Name) and fn.id == "dataclass":
                        is_dc = True
                    if isinstance(fn, ast.Attribute) and fn.attr == "dataclass":
                        is_dc = True
            if not is_dc:
                continue
            has_digest = False
            for item in node.body:
                if isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name):
                    name = item.target.id
                    if name == "digest" or name.endswith("_digest"):
                        has_digest = True
            if has_digest:
                found.add(f"{module}.{node.name}")
    missing = sorted(found - registered)
    assert missing == [], f"unregistered host_parasite digests: {missing}"
    assert audit_replay_digest_policy_registry() == ()
    assert len(found) >= 20


def test_baic_pins_and_engine_untouched() -> None:
    for rel, expected in PIN_SPECS:
        digest = sha256_text_file(ROOT / rel)
        assert digest == expected, rel
    engine = (ROOT / "src" / "codontrace" / "engine.py").read_text(encoding="utf-8")
    # Infection physics must stay out of engine.py (hard lock).
    assert "HostParasiteEnv" not in engine
    assert "try_horizontal_inject" not in engine
