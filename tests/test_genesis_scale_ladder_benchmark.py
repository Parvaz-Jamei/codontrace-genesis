import pytest

from codontrace.genesis import canonical_digest
from codontrace.genesis.phase_b_scientific_maturity import ScaleBenchmarkReport
from codontrace.errors import ConfigurationError


def D(name: str) -> str:
    return canonical_digest({"scale": name})


def test_scale_smoke_is_descriptive_not_scale_claim():
    report = ScaleBenchmarkReport(20, 2, 10, 1, 1, 0.1, 1.0, 0.01, D("ckpt"), D("resume"))
    assert report.scale_claim_status == "descriptive_only"
    assert report.digest() == ScaleBenchmarkReport(20, 2, 10, 1, 1, 0.1, 1.0, 0.01, D("ckpt"), D("resume")).digest()


def test_resource_budget_skip_is_explicit_not_hidden_failure():
    report = ScaleBenchmarkReport(100000, 100, 100, 10, 5, 0.0, 0.0, 0.0, D("ckpt"), D("resume"), "skipped_by_resource_budget")
    assert report.scale_claim_status == "skipped_by_resource_budget"


def test_scale_rejects_non_finite_metrics():
    with pytest.raises(ConfigurationError):
        ScaleBenchmarkReport(10, 1, 10, 1, 1, float("nan"), 1.0, 1.0, D("ckpt"), D("resume"))
