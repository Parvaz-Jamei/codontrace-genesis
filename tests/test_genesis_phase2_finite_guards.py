import pytest

from codontrace.errors import ConfigurationError
from codontrace.genesis.adf_runtime import ADFMacroRegistry, ADFMacroDefinition
from codontrace.genesis.adf_runtime import build_adf_usefulness_control_report
from codontrace.genesis.causal_validation import CausalEffectEstimate, CausalInterventionRunPair, InterventionSpec
from codontrace.genesis.contribution_ledger import build_micro_ablation_attribution_record
from codontrace.genesis.discovery_gate import D0CalibrationRun
from codontrace.genesis.structural_mutation import StructuralMutationConfig
from codontrace.genesis.translation_profile import TranslationWeight
from codontrace.genesis.social import SocialInteractionEvent


@pytest.mark.parametrize("value", [float("nan"), float("inf"), float("-inf")])
def test_phase2_reports_reject_non_finite_numbers(value):
    registry = ADFMacroRegistry().register(ADFMacroDefinition("ADF_ONE", ("WAIT",)))
    registry, _ = registry.expand("ADF_ONE")
    with pytest.raises(ConfigurationError):
        build_adf_usefulness_control_report(registry, "ADF_ONE", task_delta=value, null_macro_delta=0.0, permutation_control_delta=0.0)
    with pytest.raises(ConfigurationError):
        StructuralMutationConfig(codon_insert_rate=value)
    with pytest.raises(ConfigurationError):
        build_micro_ablation_attribution_record("target", "macro", original_metric=value, ablated_metric=0.0, contribution_ledger_digest="digest")
    with pytest.raises(ConfigurationError):
        TranslationWeight("000", "WAIT", value, 1, 0)
    with pytest.raises(ConfigurationError):
        SocialInteractionEvent("a", "b", "resource_competition", resource_delta=value)
    with pytest.raises(ConfigurationError):
        D0CalibrationRun("d0", value)
    with pytest.raises(ConfigurationError):
        CausalEffectEstimate(value, (0.0, 1.0), 1)
    spec = InterventionSpec("i", "x", "b", "t", "seed")
    with pytest.raises(ConfigurationError):
        CausalInterventionRunPair(spec, "b", "t", value, 1.0)
