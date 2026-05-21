import json
import subprocess
import sys

REQUIRED = {
    "integration_run_config.json",
    "integration_run_records.csv",
    "integration_artifact_manifest.json",
    "integration_replay_bundle_index.json",
    "integration_evidence_lineage_dag.json",
    "integration_final_claim_manifest.json",
    "integration_release_evidence_pack.json",
    "integration_negative_results.json",
    "integration_public_api_manifest.json",
    "integration_scientific_freshness_matrix.json",
    "integration_validation_summary.html",
}


def test_integration_e2e_smoke_outputs_required_artifacts_and_stable_digest(tmp_path):
    out1 = tmp_path / "e2e_a"
    out2 = tmp_path / "e2e_b"
    subprocess.run([sys.executable, "examples/genesis_integration_end_to_end_validation.py", "--profile", "smoke", "--out", str(out1)], check=True)
    subprocess.run([sys.executable, "examples/genesis_integration_end_to_end_validation.py", "--profile", "smoke", "--out", str(out2)], check=True)
    names = {p.name for p in out1.iterdir()}
    assert REQUIRED <= names
    for name in REQUIRED:
        assert (out1 / name).stat().st_size > 0
    claims = json.loads((out1 / "integration_final_claim_manifest.json").read_text(encoding="utf-8"))["claims"]
    assert any(c["status"] == "allowed" for c in claims)
    assert any(c["status"] in {"downgraded", "blocked", "rejected"} for c in claims)
    s1 = json.loads((out1 / "integration_validation_summary.json").read_text(encoding="utf-8"))
    s2 = json.loads((out2 / "integration_validation_summary.json").read_text(encoding="utf-8"))
    assert s1["run_digest"] == s2["run_digest"]
