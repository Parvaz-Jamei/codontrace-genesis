from codontrace.genesis.adf_runtime import (
    ADFInheritancePolicy,
    ADFMacroDefinition,
    ADFMacroRegistry,
    ADFPruningPolicy,
)
from codontrace.genesis.adf_validation import (
    ADFAblationReport,
    ADFClaimDecision,
    ADFValidationControls,
    validate_adf_candidate,
)


def test_adf_macro_expansion_executes_primitives_and_tracks_usage() -> None:
    definition = ADFMacroDefinition("ADF_FORAGE", ("MOVE_EAST", "EAT_LUMEN"))
    registry = ADFMacroRegistry().register(definition)
    next_registry, expansion, outputs = registry.execute(
        "ADF_FORAGE", lambda action: {"action": action}
    )
    assert expansion.executed
    assert expansion.expanded_actions == ("MOVE_EAST", "EAT_LUMEN")
    assert len(outputs) == 2
    assert next_registry.usage_counts["ADF_FORAGE"] == 1


def test_adf_null_models_and_ablation_control_gate_claim() -> None:
    candidate = ADFMacroDefinition("ADF_FORAGE", ("MOVE_EAST", "EAT_LUMEN"))
    traces = [("MOVE_EAST", "EAT_LUMEN", "MOVE_EAST", "EAT_LUMEN") for _ in range(4)]
    report = validate_adf_candidate(
        candidate=candidate,
        traces=traces,
        controls=ADFValidationControls(permutation_controls=0, random_baseline_controls=0),
        ablation=ADFAblationReport(with_adf_metric=2.0, without_adf_metric=1.0),
    )
    assert report.null_model.passed
    assert report.decision is ADFClaimDecision.MACRO_SUPPORTED


def test_adf_inheritance_and_pruning() -> None:
    definition = ADFMacroDefinition("ADF_UNUSED", ("WAIT", "WAIT"))
    registry = ADFMacroRegistry().register(definition)
    child = ADFInheritancePolicy().inherit(registry)
    assert child.get("ADF_UNUSED") is not None
    pruned = child.prune(ADFPruningPolicy(min_usage_count=1))
    assert pruned.get("ADF_UNUSED") is None
