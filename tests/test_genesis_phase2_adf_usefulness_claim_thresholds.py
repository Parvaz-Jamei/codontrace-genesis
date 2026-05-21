from codontrace.genesis.adf_runtime import ADFMacroRegistry, ADFMacroDefinition
from codontrace.genesis.adf_runtime import build_adf_usefulness_control_report


def test_single_action_adf_macro_without_compression_is_not_claim_eligible():
    registry = ADFMacroRegistry().register(ADFMacroDefinition("ADF_ONE", ("WAIT",)))
    registry, _ = registry.expand("ADF_ONE")
    registry, _ = registry.expand("ADF_ONE")
    report = build_adf_usefulness_control_report(
        registry,
        "ADF_ONE",
        task_delta=10.0,
        null_macro_delta=0.0,
        permutation_control_delta=0.0,
        source_map_digest="source",
    )
    assert report.compression_ratio == 0.0
    assert not report.claim_eligible


def test_multi_action_adf_macro_with_controls_source_map_and_reuse_can_be_claim_eligible():
    registry = ADFMacroRegistry().register(ADFMacroDefinition("ADF_TWO", ("SENSE_FOOD", "MOVE_TOWARD", "EAT_LUMEN")))
    registry, _ = registry.expand("ADF_TWO")
    registry, _ = registry.expand("ADF_TWO")
    report = build_adf_usefulness_control_report(
        registry,
        "ADF_TWO",
        task_delta=10.0,
        runtime_cost_delta=1.0,
        learning_cost_delta=1.0,
        null_macro_delta=0.0,
        permutation_control_delta=0.0,
        source_map_digest="source",
    )
    assert report.compression_ratio > 0.0
    assert report.claim_eligible
