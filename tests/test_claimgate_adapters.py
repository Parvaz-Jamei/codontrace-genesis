"""ClaimGate adapters: CodonTrace complete; Avida/MABE2 skeletons only."""

from __future__ import annotations

from pathlib import Path

from codontrace.claimgate import audit_bundle
from codontrace.claimgate.adapters.avida import bundle_from_avida_runs, parse_avida_dat
from codontrace.claimgate.adapters.codontrace import (
    bundle_from_hard_experiment_01,
    committed_results_v2_path,
)
from codontrace.claimgate.adapters.he01_arm_roles import canonical_role
from codontrace.claimgate.adapters.mabe2 import bundle_from_mabe2_csv, parse_mabe2_csv
from codontrace.genesis.claim_gate import ClaimRequest, ScientificClaimGate
from codontrace.genesis.engine import GenesisEngine
from codontrace.genesis.runtime_profiles import GenesisRuntimeProfile

FIXTURES = Path(__file__).resolve().parent / "fixtures"
HE01_V2_DIGEST = "2ba450ef1f2eb80f6860b865d91a15c52f506cad6e80811b6be1307ff2e158ae"
LIFE_LOOP_SPEC_DIGEST = "7d199ae51345872215dbbb0c45cf8f141aacfb4c31d6537eda6de246c0cb7aac"
LIFE_LOOP_SNAPSHOT_DIGEST = "76a5e62cb0123b20a089adde25acd1cfb6dc460bdfab52f33ee460533d76f43a"


def test_claimgate_does_not_break_phase_a_e_life_loop_pins() -> None:
    spec = GenesisRuntimeProfile.life_loop_world(seed=7, tick_count=12, population=6)
    result = GenesisEngine.from_spec(spec).run_ticks()
    assert spec.digest() == LIFE_LOOP_SPEC_DIGEST
    assert result.snapshot.digest() == LIFE_LOOP_SNAPSHOT_DIGEST


def test_avida_dat_reads_hash_n_headers() -> None:
    text = (FIXTURES / "avida" / "seed_11" / "average.dat").read_text(encoding="utf-8")
    columns, rows = parse_avida_dat(text)
    assert columns == ("update", "ave_fitness", "max_fitness", "ave_merit")
    assert rows[0] == (100.0, 0.50, 1.20, 10.0)
    assert len(rows) == 3


def test_avida_skeleton_uses_run_folder_as_seed_and_user_arm_map() -> None:
    bundle = bundle_from_avida_runs(
        (FIXTURES / "avida" / "seed_11", FIXTURES / "avida" / "seed_12"),
        {"seed_11": "treatment", "seed_12": "channel_off"},
        software_version="skeleton",
    )
    assert {arm.role for arm in bundle.arms} == {"treatment", "channel_off"}
    assert bundle.seeds == (1, 2)
    assert bundle.outcomes[0].metric == "ave_fitness"
    assert bundle.outcomes[0].values_by_arm["treatment"] == (0.60,)
    assert bundle.outcomes[0].values_by_arm["channel_off"] == (0.44,)
    assert bundle.extra is not None
    assert bundle.extra["full_avida_support"] is False
    report = audit_bundle(bundle)
    assert report.achieved_level <= 1
    assert "avida_adapter_is_a_skeleton_not_full_support" in report.warnings


def test_avida_adapter_aggregates_same_role_folders_on_ave_fitness() -> None:
    bundle = bundle_from_avida_runs(
        (FIXTURES / "avida" / "seed_11", FIXTURES / "avida" / "seed_12"),
        {"seed_11": "treatment", "seed_12": "treatment"},
        software_version="skeleton",
    )
    assert len(bundle.arms) == 1
    assert bundle.arms[0].role == "treatment"
    assert bundle.arms[0].n == 2
    assert bundle.outcomes[0].metric == "ave_fitness"
    assert bundle.outcomes[0].values_by_arm["treatment"] == (0.60, 0.44)
    assert "update" not in bundle.outcomes[0].values_by_arm


def test_mabe2_csv_skeleton_reads_datafile_export() -> None:
    columns, rows = parse_mabe2_csv((FIXTURES / "mabe2" / "score.csv").read_text(encoding="utf-8"))
    assert columns[0] == "update"
    assert rows[0][1] == "0.10"
    bundle = bundle_from_mabe2_csv(
        FIXTURES / "mabe2" / "score.csv",
        arm_name="baseline",
        arm_role="treatment",
        seeds=(1, 2, 3),
        metric="mean_score",
    )
    assert bundle.outcomes[0].metric == "mean_score"
    assert bundle.extra is not None
    assert bundle.extra["full_mabe2_support"] is False
    report = audit_bundle(bundle)
    assert report.achieved_level <= 1
    assert "mabe2_adapter_is_a_skeleton_not_full_support" in report.warnings


def test_codontrace_adapter_reproduces_he01_v2_runtime_observation() -> None:
    path = committed_results_v2_path()
    bundle = bundle_from_hard_experiment_01(path)
    assert bundle.software.name == "CodonTrace Genesis"
    assert bundle.preregistration_digest == (
        "cb4643a305a48a17250b4e38af3f423afc0c040b4ffac039c8b0ec1413b4fc40"
    )
    assert {arm.role for arm in bundle.arms} >= {
        "treatment",
        "mechanism_ablation",
        "channel_off",
        "negative_control",
        "dose",
    }
    assert len(bundle.seeds) == 30
    assert any(item.sha256 == HE01_V2_DIGEST for item in bundle.artifacts)
    assert bundle.extra is not None
    assert bundle.extra["assay_invalid"] is True
    report = audit_bundle(bundle)
    assert report.achieved_level == 1
    assert report.public_name == "runtime_observation"
    assert "consistent_measured_difference" in report.missing_for_next
    assert "assay_invalid_manipulation_not_realized" in report.warnings
    assert "interpretable_null_is_valid_not_mechanism_support" not in report.warnings
    gate = ScientificClaimGate()
    assert gate.decide(ClaimRequest("runtime_observation", {})).allowed is True
    assert gate.decide(ClaimRequest("intervention_supported", {})).allowed is False
    assert gate.decide(ClaimRequest("collective_intelligence", {})).allowed is False
    assert gate.decide(ClaimRequest("tokyo_type1_passed", {})).allowed is False


def test_he01_v7_roles_translate_to_schema() -> None:
    path = Path("docs/hard_experiment_01/results_v7.json")
    bundle = bundle_from_hard_experiment_01(path)
    roles = {arm.name: arm.role for arm in bundle.arms}
    assert roles["source_bias_on"] == "treatment"
    assert roles["source_bias_off"] == "mechanism_ablation"
    assert roles["capsules_off"] == "channel_off"
    assert roles["capsules_content_null"] == "negative_control"
    assert roles["capsules_activity_matched"] == "negative_control"
    assert roles["capsules_shuffled"] == "negative_control"
    assert roles["oracle_capsule"] == "dose"
    assert "dose_ladder" not in roles
    assert set(roles.values()) <= {
        "treatment",
        "mechanism_ablation",
        "channel_off",
        "negative_control",
        "dose",
    }
    assert "receiver_mean_terminal_runtime_atp" in {item.metric for item in bundle.outcomes}
    extra = bundle.extra or {}
    assert extra.get("assay_invalid") is not True


def test_canonical_role_maps_v7_aliases() -> None:
    assert canonical_role("oracle_capsule", "positive_control") == "dose"
    assert canonical_role("capsules_activity_matched", "auxiliary_control") == "negative_control"
    assert canonical_role("capsules_shuffled", "sensitivity_negative_control") == "negative_control"
    assert canonical_role("unknown_arm", "treatment") == "treatment"
    assert canonical_role("unknown_arm", "positive_control") == "dose"
    assert canonical_role("unknown_arm", "not_a_role") == ""
