"""Deterministic Phase 3 test suite for Evidence & Connection audit remediation.

Tests Section 5 & Acceptance Matrix (AUDIT_P01_L05_PHASES1_4.md):
- Evaluator integrity: lifecycle gate before candidate evaluation, no false positive bypass.
- Finite checks: NaN, +Inf, -Inf rejection across all selection, novelty, and information metrics.
- Reference controls: controls_passed validation and valid positive control assertions.
- Separation of unsupported from invalid evidence.
- Runtime wiring audit: genuine consumer tracing and consumer deletion tests.
- Dynamic source digest recalculation / cache invalidation on file mutation.
- Schema integrity: MetricRecord and HypothesisAssessment finite & digest checks.
- Model boundary provenance in details and manifests.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from codontrace.console.evaluator import evaluate_run_hypothesis
from codontrace.genesis import GenesisEngine
from codontrace.genesis.artifacts import compute_source_digest, verify_artifact_bytes
from codontrace.genesis.runtime_profiles import GenesisRuntimeProfile
from codontrace.genesis.runtime_wiring_audit import audit_runtime_wiring
from codontrace.genesis.schema import HypothesisAssessment, MetricRecord

# ---------------------------------------------------------------------------
# Evaluator Integrity & Rejection of False Positives
# ---------------------------------------------------------------------------

def test_evaluator_rejects_failed_run_with_embedded_supported() -> None:
    """A run ending in FAILED with an embedded 'supported' candidate MUST be marked invalid."""
    res = evaluate_run_hypothesis({
        "status": "FAILED",
        "execution": {
            "complete": False,
            "hypothesis_assessment": {
                "verdict": "supported",
                "confidence": 0.95,
                "rationale": "Fabricated success in aborted run",
            },
        },
    })
    assert res["verdict"] == "invalid"
    assert res["confidence"] == 0.0
    assert res["controls_passed"] is False


def test_evaluator_rejects_validation_failures_with_embedded_supported() -> None:
    """A run with validation failures MUST be invalid even if complete=True and candidate claims supported."""
    res = evaluate_run_hypothesis({
        "status": "COMPLETED",
        "execution": {
            "complete": True,
            "validation_failures": ["corrupt_archive_checksum"],
            "hypothesis_assessment": {
                "verdict": "supported",
                "confidence": 0.99,
                "controls_passed": True,
            },
        },
    })
    assert res["verdict"] == "invalid"
    assert res["confidence"] == 0.0
    assert res["controls_passed"] is False


def test_evaluator_rejects_nan_and_infinity_in_metrics() -> None:
    """Non-finite floats (NaN, +Inf, -Inf) must evaluate to invalid with confidence 0.0."""
    # 1. MLS_PRICE with Infinity in between_deme_selection_term
    res_mls_inf = evaluate_run_hypothesis({
        "status": "COMPLETED",
        "execution": {
            "complete": True,
            "challenge": "MLS_PRICE",
            "summary": {
                "between_deme_selection_term": float("inf"),
                "within_deme_selection_term": 0.05,
            },
        },
    })
    assert res_mls_inf["verdict"] == "invalid"
    assert res_mls_inf["confidence"] == 0.0
    assert res_mls_inf["controls_passed"] is False

    # 2. MLS_PRICE with NaN
    res_mls_nan = evaluate_run_hypothesis({
        "status": "COMPLETED",
        "execution": {
            "complete": True,
            "challenge": "MLS_PRICE",
            "summary": {
                "between_deme_selection_term": float("nan"),
                "within_deme_selection_term": 0.05,
            },
        },
    })
    assert res_mls_nan["verdict"] == "invalid"
    assert res_mls_nan["confidence"] == 0.0

    # 3. OEE_NOVELTY with Infinity in activity_slope
    res_oee_inf = evaluate_run_hypothesis({
        "status": "COMPLETED",
        "execution": {
            "complete": True,
            "challenge": "OEE_NOVELTY",
            "summary": {
                "activity_slope": float("inf"),
                "total_generations": 5000,
            },
        },
    })
    assert res_oee_inf["verdict"] == "invalid"
    assert res_oee_inf["confidence"] == 0.0

    # 4. FUNCTIONAL_INFO with NaN
    res_fi_nan = evaluate_run_hypothesis({
        "status": "COMPLETED",
        "execution": {
            "complete": True,
            "challenge": "FUNCTIONAL_INFO",
            "summary": {
                "hazen_functional_info_bits": float("nan"),
                "neutral_percolation_rate": 0.35,
            },
        },
    })
    assert res_fi_nan["verdict"] == "invalid"
    assert res_fi_nan["confidence"] == 0.0

    # 5. Candidate assessment with NaN confidence
    res_cand_nan = evaluate_run_hypothesis({
        "status": "COMPLETED",
        "execution": {
            "complete": True,
            "hypothesis_assessment": {
                "verdict": "supported",
                "confidence": float("nan"),
            },
        },
    })
    assert res_cand_nan["verdict"] == "invalid"
    assert res_cand_nan["confidence"] == 0.0


def test_evaluator_rejects_failed_reference_controls() -> None:
    """When controls explicitly fail or are unverified, verdict cannot be supported."""
    res = evaluate_run_hypothesis({
        "status": "COMPLETED",
        "execution": {
            "complete": True,
            "challenge": "OEE_NOVELTY",
            "controls_passed": False,
            "summary": {
                "activity_slope": 0.25,
                "total_generations": 5000,
            },
        },
    })
    assert res["verdict"] == "invalid"
    assert res["controls_passed"] is False


def test_evaluator_accepts_valid_positive_controls() -> None:
    """Valid runs with genuine positive signals and passing controls must be supported."""
    # OEE positive control
    res_oee = evaluate_run_hypothesis({
        "status": "COMPLETED",
        "execution": {
            "complete": True,
            "challenge": "OEE_NOVELTY",
            "total_generations": 5000,
            "summary": {
                "activity_slope": 0.185,
                "total_generations": 5000,
            },
        },
    })
    assert res_oee["verdict"] == "supported"
    assert res_oee["confidence"] == 0.95
    assert res_oee["controls_passed"] is True

    # MLS Price positive control
    res_mls = evaluate_run_hypothesis({
        "status": "COMPLETED",
        "execution": {
            "complete": True,
            "challenge": "MLS_PRICE",
            "summary": {
                "between_deme_selection_term": 0.25,
                "within_deme_selection_term": 0.01,
            },
        },
    })
    assert res_mls["verdict"] == "supported"
    assert res_mls["confidence"] == 0.92
    assert res_mls["controls_passed"] is True

    # Hazen FI positive control
    res_fi = evaluate_run_hypothesis({
        "status": "COMPLETED",
        "execution": {
            "complete": True,
            "challenge": "FUNCTIONAL_INFO",
            "summary": {
                "hazen_functional_info_bits": 12.4,
                "neutral_percolation_rate": 0.42,
            },
        },
    })
    assert res_fi["verdict"] == "supported"
    assert res_fi["confidence"] == 0.95
    assert res_fi["controls_passed"] is True


def test_evaluator_separates_not_supported_from_invalid() -> None:
    """A valid run that simply fails to meet the empirical threshold is 'not_supported', not 'invalid'."""
    res_bounded = evaluate_run_hypothesis({
        "status": "COMPLETED",
        "execution": {
            "complete": True,
            "challenge": "OEE_NOVELTY",
            "total_generations": 5000,
            "summary": {
                "activity_slope": 0.02,
                "total_generations": 5000,
            },
        },
    })
    assert res_bounded["verdict"] == "not_supported"
    assert res_bounded["confidence"] == 0.90
    assert res_bounded["controls_passed"] is True


# ---------------------------------------------------------------------------
# Runtime Wiring Audit & Consumer Deletion
# ---------------------------------------------------------------------------

class _MockResultWithConsumer:
    """Wrapper that mimics a GenesisRunResult with modifiable dict payload."""

    def __init__(self, real_result: Any) -> None:
        self._real = real_result
        self._dict_copy = dict(real_result.to_dict())
        self.evidence_manifest = real_result.evidence_manifest

    def to_dict(self) -> dict[str, Any]:
        return self._dict_copy


def test_runtime_wiring_audit_consumer_deletion() -> None:
    """Deleting or emptying a consumer payload must cause runtime wiring audit to fail."""
    real_res = GenesisEngine.from_spec(GenesisRuntimeProfile.toolchain_pilot_world(seed=23, tick_count=2)).run_ticks()
    
    # Baseline: unmodified result must pass
    baseline_audit = audit_runtime_wiring(real_res)
    assert baseline_audit["passed"] is True
    assert baseline_audit["runtime_verified"] is True

    # Consumer deletion test 1: remove ablation_witnesses from phase_b report
    mock_run = _MockResultWithConsumer(real_res)
    pb_report = dict(mock_run._dict_copy.get("phase_b_scientific_maturity_report", {}))
    pb_report["ablation_witnesses"] = ()  # emptied consumer payload
    mock_run._dict_copy["phase_b_scientific_maturity_report"] = pb_report

    audit_del1 = audit_runtime_wiring(mock_run)
    assert audit_del1["passed"] is False
    assert any("ablation_witness" in str(issue) for issue in audit_del1["issues"])

    # Consumer deletion test 2: delete entire phase1_runtime_maturity_report
    mock_run2 = _MockResultWithConsumer(real_res)
    del mock_run2._dict_copy["phase1_runtime_maturity_report"]

    audit_del2 = audit_runtime_wiring(mock_run2)
    assert audit_del2["passed"] is False
    assert any("mutation_operator_maturity" in str(issue) for issue in audit_del2["issues"])


# ---------------------------------------------------------------------------
# Source Digest Dynamic Invalidation on File Mutation
# ---------------------------------------------------------------------------

def test_source_digest_invalidation_on_file_mutation(tmp_path: Path) -> None:
    """Mutating a file in the tracked tree must immediately change the computed source digest."""
    root = tmp_path / "project"
    src_dir = root / "src" / "codontrace"
    src_dir.mkdir(parents=True)
    (root / "pyproject.toml").write_text("[project]\nname = 'test'\n", encoding="utf-8")
    test_file = src_dir / "module.py"
    test_file.write_text("x = 1\n", encoding="utf-8")

    digest_v1 = compute_source_digest(str(root), force_refresh=True)

    # Mutate the file
    test_file.write_text("x = 2  # modified\n", encoding="utf-8")

    digest_v2 = compute_source_digest(str(root), force_refresh=True)

    assert digest_v1 != digest_v2, "Source digest must change when tracked file content is modified"


def test_verify_artifact_bytes(tmp_path: Path) -> None:
    """verify_artifact_bytes must validate actual file bytes on disk against SHA256."""
    target = tmp_path / "artifact.dat"
    target.write_bytes(b"deterministic_binary_content_12345")
    import hashlib
    valid_hash = hashlib.sha256(b"deterministic_binary_content_12345").hexdigest()

    assert verify_artifact_bytes(target, valid_hash) is True
    assert verify_artifact_bytes(target, "wrong_hash_0000000000000000000000000000000000000000") is False
    assert verify_artifact_bytes(tmp_path / "nonexistent.dat", valid_hash) is False


# ---------------------------------------------------------------------------
# Schema Integrity (MetricRecord & HypothesisAssessment)
# ---------------------------------------------------------------------------

def test_schema_validates_finite_and_real_evidence_digests() -> None:
    """MetricRecord and HypothesisAssessment dataclasses must enforce finite numbers and valid digests."""
    # Non-finite MetricRecord must raise ValueError
    with pytest.raises(ValueError, match="finite float"):
        MetricRecord(metric_name="entropy", value=float("inf"), unit="bits")

    with pytest.raises(ValueError, match="finite float"):
        MetricRecord(metric_name="entropy", value=float("nan"), unit="bits")

    # Valid MetricRecord
    valid_metric = MetricRecord(metric_name="entropy", value=4.5, unit="bits")
    assert valid_metric.value == 4.5

    # Non-finite or out-of-range HypothesisAssessment confidence
    with pytest.raises(ValueError, match="finite"):
        HypothesisAssessment(hypothesis_id="h1", conclusion="c", confidence=float("nan"), evidence_digests=("sha256:123",))

    with pytest.raises(ValueError, match="between 0.0 and 1.0"):
        HypothesisAssessment(hypothesis_id="h1", conclusion="c", confidence=1.5, evidence_digests=("sha256:123",))

    # Fake or placeholder evidence digest
    with pytest.raises(ValueError, match="fake evidence digest"):
        HypothesisAssessment(hypothesis_id="h1", conclusion="c", confidence=0.8, evidence_digests=("fake_digest_42",))

    with pytest.raises(ValueError, match="fake evidence digest"):
        HypothesisAssessment(hypothesis_id="h1", conclusion="c", confidence=0.8, evidence_digests=("placeholder",))

    # Valid HypothesisAssessment
    valid_ha = HypothesisAssessment(hypothesis_id="h1", conclusion="c", confidence=0.85, evidence_digests=("sha256:valid_digest_string",))
    assert valid_ha.confidence == 0.85


# ---------------------------------------------------------------------------
# Manifest & Details Execution Boundary Provenance
# ---------------------------------------------------------------------------

def test_get_run_details_includes_boundary_and_assessment(tmp_path: Path, monkeypatch: Any) -> None:
    """get_run_details must return top-level executionBoundary and hypothesis_assessment."""
    monkeypatch.setenv("CODONTRACE_RUNS_DIR", str(tmp_path / "runs"))
    from codontrace.console.runs import get_run_details, launch_simulation_run

    res = launch_simulation_run({
        "generations": 2,
        "workers": 1,
        "seeds": [16001],
        "title": "phase3_boundary_test",
    })
    assert res["ok"] is True
    details = get_run_details(res["runId"])
    assert details is not None
    assert "executionBoundary" in details
    assert details["executionBoundary"]["engineBackend"] == "genesis_engine"
    assert details["executionBoundary"]["isGenesisEngine"] is True
    assert details["executionBoundary"]["isFrontierReference"] is False
    assert "hypothesis_assessment" in details
    assert "verdict" in details["hypothesis_assessment"]
