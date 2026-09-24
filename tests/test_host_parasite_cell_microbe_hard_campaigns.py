"""Hard cell↔microbe campaigns — Genesis substrate × host_parasite ClaimGate.

Exercises multi-seed contingency, dual-genome Zaman, entropy/Hamming dual-null,
ARD→FSD cost-of-generalism, sequential Cornish, Scanlan mutator, and task–gene
dual-null panels with fail-closed ClaimGate ceilings. Not Wave-6 soft smoke.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from codontrace.claimgate.adapters.host_parasite import assert_claim_allowed
from codontrace.errors import ConfigurationError
from codontrace.genesis.host_parasite_cell_microbe_hard_campaigns import (
    SCHEMA,
    SEEDS_CONTINGENCY_MIXED,
    SEEDS_DIVERSITY,
    run_cell_microbe_hard_campaigns,
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
    / "cell_microbe_hard_campaigns_results.json"
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
_HARD_REFUSE = (
    "red_queen_proved",
    "phage_therapy_cleared",
    "complexity_emergence_proved",
    "gene_identity_proved",
    "intervention_supported",
    "crispr_identity_proved",
    "oee_modes_passed",
    "intelligence_proved",
)


@pytest.fixture(scope="module")
def pack_dict() -> dict:
    return run_cell_microbe_hard_campaigns().to_dict()


def test_pack_schema_and_honesty_flags(pack_dict: dict) -> None:
    assert pack_dict["schema"] == SCHEMA
    assert pack_dict["domain_profile"] == "host_parasite"
    assert pack_dict["cell_role"] == "semantic_genome_genesis_substrate"
    assert pack_dict["microbe_role"] == "cou_semantic_label_only"
    assert pack_dict["engine_infection_physics"] == "not_in_engine_core"
    assert pack_dict["raises_claim_ladder"] is False
    assert pack_dict["red_queen_proved"] is False
    assert pack_dict["complexity_emergence_proved"] is False
    assert pack_dict["intervention_supported"] is False
    assert pack_dict["gene_identity_proved"] is False
    assert len(pack_dict["campaigns"]) >= 6
    assert len(pack_dict["pack_digest"]) == 64


def test_cm1_contingency_falsifies_and_edge_stays_humble(pack_dict: dict) -> None:
    cm1 = next(c for c in pack_dict["campaigns"] if c["id"].startswith("CM1"))
    assert cm1["hypothesis_supported_mixed"] is False
    assert cm1["n_failing_under_parasitism"] >= 1
    assert cm1["n_rising_under_parasitism"] >= 1  # contingency heat, not all-fail
    assert cm1["complexity_emergence_proved"] is False
    assert cm1["seed_digests_are_distinct"] is True
    # Supporting-edge pack may still support the law — never proves emergence.
    assert cm1["hypothesis_supported_edge"] is True
    assert set(cm1["seeds_mixed"]) == set(SEEDS_CONTINGENCY_MIXED)


def test_cm2_genome_zaman_arms_distinct(pack_dict: dict) -> None:
    cm2 = next(c for c in pack_dict["campaigns"] if c["id"].startswith("CM2"))
    assert cm2["arms_are_distinct"] is True
    assert cm2["complexity_emergence_proved"] is False
    assert cm2["red_queen_proved"] is False
    assert len(cm2["arm_digests"]) == 3
    for arm, info in cm2["per_arm"].items():
        assert info["host_parasite_digest_pairs_distinct"] is True, arm


def test_cm3_dual_null_entropy_separation(pack_dict: dict) -> None:
    cm3 = next(c for c in pack_dict["campaigns"] if c["id"].startswith("CM3"))
    assert cm3["hypothesis_supported"] is False
    assert cm3["arms_are_distinct"] is True
    biotic = cm3["arm_stats"]["biotic_intact"]["mean_entropy_delta_vs_baseline"]
    content = cm3["arm_stats"]["content_null"]["mean_entropy_delta_vs_baseline"]
    assert biotic > 0.0
    assert content == 0.0
    assert cm3["biotic_minus_content_null_entropy_delta"] == pytest.approx(biotic - content)
    assert set(cm3["seeds"]) == set(SEEDS_DIVERSITY)


def test_cm4_ard_fsd_transition_and_costs(pack_dict: dict) -> None:
    cm4 = next(c for c in pack_dict["campaigns"] if c["id"].startswith("CM4"))
    assert cm4["transition_observed"] is True
    assert cm4["hypothesis_supported"] is False
    assert cm4["red_queen_proved"] is False
    assert cm4["wet_ard_fsd_identity"] is False
    spotlight = {r["slice_id"]: r for r in cm4["cost_spotlight"]}
    early = spotlight["parasite_coevolution:early:seed11"]
    late = spotlight["parasite_coevolution:late:seed11"]
    assert early["label"] == "ard_like"
    assert late["label"] == "fsd_like"
    assert late["mean_cost_of_generalism"] > early["mean_cost_of_generalism"]
    null_early = spotlight["structure_null_shuffled:early:seed11"]
    assert null_early["label"] == "undeclared"


def test_cm5_cornish_obs_match_refuses_intervention(pack_dict: dict) -> None:
    cm5 = next(c for c in pack_dict["campaigns"] if c["id"].startswith("CM5"))
    assert cm5["observational_match"] is True
    assert cm5["interventions_executed"] is True
    assert cm5["intervention_supported"] is False
    assert cm5["obs_score"] == pytest.approx(0.2)
    assert all(s > cm5["obs_score"] for s in cm5["intervention_scores"])
    assert all(step["intervention_supported"] is False for step in cm5["steps"])


def test_cm6_scanlan_constraint(pack_dict: dict) -> None:
    cm6 = next(c for c in pack_dict["campaigns"] if c["id"].startswith("CM6"))
    assert cm6["hypothesis_supported"] is False
    assert cm6["gene_identity_proved"] is False
    assert cm6["crispr_identity_proved"] is False
    assert cm6["arms_are_distinct"] is True
    # Abiotic elevated fitness beats coevolution-elevated (constraint).
    assert cm6["abiotic_elevated_minus_coevo_elevated_fitness"] > 0.0


def test_cm7_task_gene_dual_null_panel(pack_dict: dict) -> None:
    cm7 = next(c for c in pack_dict["campaigns"] if c["id"].startswith("CM7"))
    assert cm7["map_digests_pairwise_distinct"] is True
    assert cm7["gene_identity_proved"] is False
    for label, row in cm7["maps"].items():
        assert row["gene_identity_proved"] is False, label
        assert row["n_windows"] >= 1


def test_claimgate_ladder_and_blocked_claims(pack_dict: dict) -> None:
    audit = pack_dict["claimgate_audit"]
    assert audit["ladder_unchanged"] is True
    assert audit["ladder_before"] == audit["ladder_after"]
    for claim in _HARD_REFUSE:
        assert audit["blocked_spot_check"][claim] is True
        with pytest.raises(ConfigurationError):
            assert_claim_allowed(claim)


def test_pack_deterministic() -> None:
    a = run_cell_microbe_hard_campaigns().to_dict()["pack_digest"]
    b = run_cell_microbe_hard_campaigns().to_dict()["pack_digest"]
    assert a == b


def test_results_json_matches_live_pack(pack_dict: dict, tmp_path: Path) -> None:
    written = write_results_json(tmp_path / "out.json", pack=run_cell_microbe_hard_campaigns())
    disk = json.loads(written.read_text(encoding="utf-8"))
    assert disk["pack_digest"] == pack_dict["pack_digest"]
    assert RESULTS_JSON.is_file()
    committed = json.loads(RESULTS_JSON.read_text(encoding="utf-8"))
    assert committed["pack_digest"] == pack_dict["pack_digest"]
    assert committed["schema"] == SCHEMA


def test_baic_pins_byte_identical() -> None:
    for rel, expected in PIN_SPECS:
        raw = (ROOT / rel).read_bytes()
        got = hashlib.sha256(raw).hexdigest()
        assert got == expected, rel


def test_engine_empty_of_infection() -> None:
    src = _ENGINE.read_text(encoding="utf-8")
    assert "HostParasiteEnv" not in src
    assert "try_horizontal_inject" not in src
    assert "infection" not in src.lower()


def test_replay_policy_registers_pack() -> None:
    path = (
        "codontrace.genesis.host_parasite_cell_microbe_hard_campaigns."
        "CellMicrobeHardCampaignPack"
    )
    assert path in NON_REPLAY_CRITICAL_DIGEST_CLASSES
    assert audit_replay_digest_policy_registry() == ()


def test_refuses_high_claim_ceiling() -> None:
    with pytest.raises(ConfigurationError):
        run_cell_microbe_hard_campaigns(request_claim_ceiling="mechanism_support")
