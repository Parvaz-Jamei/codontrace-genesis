from __future__ import annotations

from dataclasses import dataclass

from codontrace.genesis.evidence_validation import EvidenceValidationContext


@dataclass(frozen=True)
class DummySemanticProxyReport:
    digest: str


def test_to_dict_includes_semantic_proxy_report_digests() -> None:
    context = EvidenceValidationContext(
        semantic_proxy_reports=(DummySemanticProxyReport("expected_digest"),)
    )

    payload = context.to_dict()

    assert payload["semantic_proxy_report_count"] == 1
    assert payload["semantic_proxy_report_digests"] == ["expected_digest"]
    assert "expected_digest" in context.artifact_digests
