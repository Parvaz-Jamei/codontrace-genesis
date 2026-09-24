"""Scientific Simulation Fidelity (SF) + Differentiation (DX) campaigns."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from codontrace.claimgate.adapters.host_parasite import assert_claim_allowed
from codontrace.errors import ConfigurationError
from codontrace.genesis.host_parasite_sim_fidelity_campaigns import (
    SCHEMA,
    SEEDS_SF1,
    SEEDS_SF2,
    SEEDS_SF4,
    run_sim_fidelity_campaigns,
    write_results_json,
)
from codontrace.genesis.replay_integrity import (
    NON_REPLAY_CRITICAL_DIGEST_CLASSES,
    audit_replay_digest_policy_registry,
)

ROOT = Path(__file__).resolve().parents[1]
RESULTS_JSON = (
    ROOT
    / "docs"
    / "claimgate"
    / "host_parasite_port_20260924"
    / "sim_fidelity_campaigns_results.json"
)
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
_ENGINE = ROOT / "src" / "codontrace" / "genesis" / "engine.py"
_CORE_ENGINE = ROOT / "src" / "codontrace" / "engine.py"
_HARD_REFUSE = (
    "red_queen_proved",
    "phage_therapy_cleared",
    "complexity_emergence_proved",
    "gene_identity_proved",
    "intervention_supported",
    "crispr_identity_proved",
    "oee_modes_passed",
    "intelligence_proved",
    "virulence_optimized_for_humans",
    "major_transition_proved",
    "tokyo_type1_passed",
    "modes_passed_proved",
)


@pytest.fixture(scope="module")
def pack_dict() -> dict:
    return run_sim_fidelity_campaigns().to_dict()


def _by_id(pack_dict: dict, prefix: str) -> dict:
    return next(c for c in pack_dict["campaigns"] if c["id"].startswith(prefix))


def test_pack_schema_honesty_and_counts(pack_dict: dict) -> None:
    assert pack_dict["schema"] == SCHEMA
    assert pack_dict["domain_profile"] == "host_parasite"
    assert pack_dict["cell_role"] == "semantic_genome_genesis_substrate"
    assert pack_dict["microbe_role"] == "cou_semantic_label_only"
    assert pack_dict["engine_infection_physics"] == "not_in_engine_core"
    assert pack_dict["raises_claim_ladder"] is False
    assert pack_dict["red_queen_proved"] is False
    assert pack_dict["n_sf"] == 8
    assert pack_dict["n_dx"] == 8
    assert len(pack_dict["campaigns"]) == 16
    assert pack_dict["n_success"] + pack_dict["n_partial"] + pack_dict["n_fail"] == 16
    assert pack_dict["n_success"] >= 12
    assert pack_dict["n_fail"] >= 1
    assert len(pack_dict["pack_digest"]) == 64


def test_sf1_coexistence_cost_of_generalism(pack_dict: dict) -> None:
    sf1 = _by_id(pack_dict, "SF1")
    assert sf1["result"] == "SUCCESS"
    assert sf1["zero_cost_extinction_or_dominance_count"] >= 3
    assert sf1["with_cost_coexistence_count"] >= 3
    assert set(sf1["setup"]["seeds"]) == set(SEEDS_SF1)


def test_sf2_biotic_abiotic_entropy(pack_dict: dict) -> None:
    sf2 = _by_id(pack_dict, "SF2")
    assert sf2["result"] == "SUCCESS"
    assert sf2["hypothesis_supported"] is False
    assert sf2["biotic_minus_abiotic"] > 0.0
    assert set(sf2["setup"]["seeds"]) == set(SEEDS_SF2)


def test_sf3_ard_fsd_transition(pack_dict: dict) -> None:
    sf3 = _by_id(pack_dict, "SF3")
    assert sf3["result"] == "SUCCESS"
    assert sf3["transition_observed"] is True
    assert sf3["early_label"] == "ard_like"
    assert sf3["late_label"] == "fsd_like"
    assert sf3["late_cost"] > sf3["early_cost"]


def test_sf4_intentional_hard_failure_nfd(pack_dict: dict) -> None:
    sf4 = _by_id(pack_dict, "SF4")
    assert sf4["result"] == "FAIL"
    assert sf4["intentional_hard_failure"] is True
    assert sf4["red_queen_proved"] is False
    assert sf4["n_cycling_seeds"] == 0
    assert set(sf4["setup"]["seeds"]) == set(SEEDS_SF4)


def test_sf5_dual_genome_divergence(pack_dict: dict) -> None:
    sf5 = _by_id(pack_dict, "SF5")
    assert sf5["result"] == "SUCCESS"
    assert sf5["arms_are_distinct"] is True
    assert sf5["coevo_vs_freeze_distinct"] is True


def test_sf6_cornish_refuse_intervention(pack_dict: dict) -> None:
    sf6 = _by_id(pack_dict, "SF6")
    assert sf6["result"] == "SUCCESS"
    assert sf6["intervention_supported"] is False
    assert all(s > sf6["obs_score"] for s in sf6["intervention_scores"])


def test_sf7_replay_digest_stability(pack_dict: dict) -> None:
    sf7 = _by_id(pack_dict, "SF7")
    assert sf7["result"] == "SUCCESS"
    assert sf7["within_seed_stable"] is True
    assert sf7["zaman_pack_stable"] is True


def test_sf8_engine_hygiene(pack_dict: dict) -> None:
    sf8 = _by_id(pack_dict, "SF8")
    assert sf8["result"] == "SUCCESS"
    assert sf8["forbidden_hits"] == []
    engine_text = _ENGINE.read_text(encoding="utf-8")
    core_text = _CORE_ENGINE.read_text(encoding="utf-8")
    for tok in ("HostParasiteEnv", "try_horizontal_inject", "infection_eligible"):
        assert tok not in engine_text
        assert tok not in core_text


def test_dx1_theatrical_failclosed(pack_dict: dict) -> None:
    dx1 = _by_id(pack_dict, "DX1")
    assert dx1["result"] == "SUCCESS"
    assert dx1["all_theatrical_claims_blocked"] is True
    m = dx1["spectacular_metrics"]
    assert m["biotic_entropy_delta"] > 0.3
    assert m["ard_cost_jump"] > 0.2
    assert all(dx1["refuse_map"].values())


def test_dx2_price_not_causality(pack_dict: dict) -> None:
    dx2 = _by_id(pack_dict, "DX2")
    assert dx2["result"] == "SUCCESS"
    assert dx2["price_covariance"] != 0.0
    assert dx2["price_summary_is_causal"] is False
    assert dx2["major_transition_proved"] is False
    assert dx2["refusal_assay_passed"] is True


def test_dx3_modes_measurement_only(pack_dict: dict) -> None:
    dx3 = _by_id(pack_dict, "DX3")
    assert dx3["result"] == "SUCCESS"
    assert dx3["measurement_allowed"] is True
    assert dx3["measurement_final_claim"] == "tokyo_type1_measurement_only"
    assert dx3["pass_allowed"] is False
    assert dx3["refuse_map"]["tokyo_type1_passed"] is True
    assert dx3["refuse_map"]["modes_passed_proved"] is True


def test_dx4_replay_spectacle(pack_dict: dict) -> None:
    dx4 = _by_id(pack_dict, "DX4")
    assert dx4["result"] == "SUCCESS"
    assert dx4["within_seed_stable"] is True
    assert dx4["mutated_seed_mismatches"] is True
    assert dx4["mutated_attach_refused"] is True


def test_dx5_content_null_trap(pack_dict: dict) -> None:
    dx5 = _by_id(pack_dict, "DX5")
    assert dx5["result"] == "SUCCESS"
    assert dx5["missing_content_null_refused"] is True
    assert dx5["arm_mean_scores"]["intact"] == pytest.approx(0.2)
    assert dx5["arm_mean_scores"]["content_null"] == pytest.approx(1.0)
    assert dx5["granted_ceiling"] == "candidate_evidence"


def test_dx6_cross_domain_auditor(pack_dict: dict) -> None:
    dx6 = _by_id(pack_dict, "DX6")
    assert dx6["result"] == "SUCCESS"
    assert all(dx6["host_parasite_blocks"].values())
    assert any(dx6["other_profiles_allow_phage_string"].values())
    assert dx6["hp_attach_ok"] is True
    assert dx6["wrong_domain_attach_refused"] is True


def test_dx7_cornish_headline(pack_dict: dict) -> None:
    dx7 = _by_id(pack_dict, "DX7")
    assert dx7["result"] == "SUCCESS"
    assert dx7["obs_score"] == pytest.approx(0.2)
    assert dx7["intervention_scores"] == [1.0, 1.0, 1.0]
    assert dx7["intervention_supported"] is False


def test_dx8_engine_boundary(pack_dict: dict) -> None:
    dx8 = _by_id(pack_dict, "DX8")
    assert dx8["result"] == "SUCCESS"
    assert dx8["forbidden_hits"] == []
    assert dx8["env_has_infection_helpers"] is True
    assert dx8["core_engine_bad_functions"] == []


def test_claimgate_ceilings_and_ladder(pack_dict: dict) -> None:
    audit = pack_dict["claimgate_audit"]
    assert audit["ladder_unchanged"] is True
    for claim in _HARD_REFUSE:
        with pytest.raises(ConfigurationError):
            assert_claim_allowed(claim)


@pytest.mark.parametrize("path,expected", PIN_SPECS)
def test_baic_pins_intact(path: str, expected: str) -> None:
    digest = hashlib.sha256((ROOT / path).read_bytes()).hexdigest()
    assert digest == expected


def test_results_json_roundtrip(tmp_path: Path, pack_dict: dict) -> None:
    out = write_results_json(tmp_path / "sf.json")
    loaded = json.loads(out.read_text(encoding="utf-8"))
    assert loaded["pack_digest"] == pack_dict["pack_digest"]
    assert loaded["n_dx"] == 8


def test_committed_results_json_matches_live_pack(pack_dict: dict) -> None:
    if not RESULTS_JSON.exists():
        pytest.skip("results json not yet committed")
    committed = json.loads(RESULTS_JSON.read_text(encoding="utf-8"))
    assert committed["pack_digest"] == pack_dict["pack_digest"]
    assert committed["n_success"] == pack_dict["n_success"]
    assert committed["n_fail"] == pack_dict["n_fail"]


def test_sf_digests_registered_non_replay_critical() -> None:
    assert (
        "codontrace.genesis.host_parasite_sim_fidelity_campaigns.SimFidelityPack"
        in NON_REPLAY_CRITICAL_DIGEST_CLASSES
    )
    assert audit_replay_digest_policy_registry() == ()
