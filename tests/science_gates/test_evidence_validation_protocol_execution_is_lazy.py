from __future__ import annotations

from codontrace.genesis.evidence_validation import EvidenceValidationContext


class LazyEvidenceValidationContext(EvidenceValidationContext):
    calls: list[str]

    def __init__(self) -> None:
        super().__init__(predictive_probe_results=(object(),))  # type: ignore[arg-type]
        object.__setattr__(self, "calls", [])

    def has_predictive_probe_artifact(self) -> bool:
        self.calls.append("predictive")
        return True

    def has_validated_intervention_result(self) -> bool:
        self.calls.append("intervention")
        raise AssertionError("intervention check should not run after predictive evidence")

    def has_intervention_protocol_artifact(self) -> bool:
        self.calls.append("intervention_protocol")
        raise AssertionError("intervention protocol check should not run after predictive evidence")

    def has_oee_candidate_report(self) -> bool:
        self.calls.append("oee")
        raise AssertionError("OEE check should not run after predictive evidence")

    def has_semantic_proxy_artifact(self) -> bool:
        self.calls.append("semantic")
        raise AssertionError("semantic check should not run after predictive evidence")


def test_scientific_validation_protocol_executed_short_circuits_after_predictive_probe() -> None:
    context = LazyEvidenceValidationContext()

    assert context.scientific_validation_protocol_executed() is True
    assert context.calls == ["predictive"]
