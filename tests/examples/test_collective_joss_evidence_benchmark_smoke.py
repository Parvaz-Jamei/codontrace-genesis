from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
RUNNER = ROOT / "examples" / "collective_joss_evidence_benchmark.py"


def _load_runner_module():
    spec = importlib.util.spec_from_file_location(
        "collective_joss_evidence_benchmark",
        RUNNER,
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_collective_joss_evidence_benchmark_smoke_plan_covers_core_surfaces() -> None:
    """The smoke profile should include the main mechanism families.

    This is a fast structural check so CI does not need to execute every family
    on every run, while the manual smoke/quick profiles still cover them.
    """
    runner = _load_runner_module()
    plan = runner.make_plan("smoke", seed_count=1)

    assert ("evolution", "birth_friendly") in plan
    assert ("evolution", "no_reproduction") in plan

    assert ("capsule", "high_communication") in plan
    assert ("capsule", "no_capsules") in plan

    assert ("memory", "baseline") in plan
    assert ("memory", "no_memory") in plan

    assert ("qd", "qd_pressure") in plan
    assert ("evolution", "no_qd") in plan

    assert ("social", "collective_mixed") in plan
    assert ("social", "no_capsules") in plan


def test_collective_joss_evidence_benchmark_smoke_execution(tmp_path: Path) -> None:
    """Run the JOSS evidence benchmark in a tiny CI-safe mode.

    This test intentionally does not try to prove collective intelligence.
    It checks that the runner can execute a small controlled scenario set and
    emit the evidence artifacts expected by the reproducibility and benchmark docs.
    """
    out_dir = tmp_path / "joss_evidence_smoke"

    env = os.environ.copy()
    src = ROOT / "src"
    if src.exists():
        env["PYTHONPATH"] = str(src) + (
            os.pathsep + env["PYTHONPATH"] if env.get("PYTHONPATH") else ""
        )

    cmd = [
        sys.executable,
        str(RUNNER),
        "--out",
        str(out_dir),
        "--profile",
        "smoke",
        "--seed-count",
        "1",
        "--ticks",
        "3",
        "--population",
        "4",
        "--workers",
        "1",
        "--max-runs",
        "6",
        "--per-run-timeout",
        "90",
    ]

    completed = subprocess.run(
        cmd,
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=240,
    )

    assert completed.returncode == 0, completed.stdout + "\n" + completed.stderr

    required_files = [
        "run_config.json",
        "summary.json",
        "run_records.csv",
        "feature_matrix.csv",
        "counterfactual_pairs.csv",
        "claim_readiness.json",
        "artifact_manifest.json",
        "environment.txt",
        "report.html",
    ]

    for name in required_files:
        assert (out_dir / name).exists(), f"missing benchmark artifact: {name}"

    run_config = json.loads((out_dir / "run_config.json").read_text(encoding="utf-8"))
    assert run_config["runner"] == "collective_joss_evidence_benchmark"
    assert run_config["target_public_version"] == "0.3.0a2"
    assert run_config["release_doi"] == "10.5281/zenodo.20337435"
    assert "not a proof of collective intelligence" in run_config["claim_boundary"]

    summary_payload = json.loads((out_dir / "summary.json").read_text(encoding="utf-8"))
    summary = summary_payload["summary"]

    assert summary["status"] == "passed"
    assert summary["runs_planned"] == 6
    assert summary["runs_completed"] == 6
    assert summary["runs_failed"] == 0
    assert summary["unique_result_digests"] == 6

    counts = summary["aggregate_counts"]
    assert counts.get("birth_event_records", 0) > 0
    assert counts.get("mutation_result_records", 0) > 0
    assert counts.get("capsule_adoption_records", 0) > 0
    assert counts.get("capsule_utility_records", 0) > 0
    assert counts.get("memory_use_records", 0) > 0
    assert counts.get("role_records", 0) > 0
    assert counts.get("behavior_descriptors", 0) > 0

    readiness = json.loads(
        (out_dir / "claim_readiness.json").read_text(encoding="utf-8")
    )
    assert "collective_intelligence_claim_ready" in readiness
    assert readiness["collective_intelligence_claim_ready"] is False

    manifest = json.loads(
        (out_dir / "artifact_manifest.json").read_text(encoding="utf-8")
    )
    generated = set(manifest.get("generated_files", []))

    assert "summary.json" in generated
    assert "run_records.csv" in generated
    assert "claim_readiness.json" in generated
