from codontrace.genesis.adf_runtime import (
    ADFExecutionPolicy,
    ADFInheritancePolicy,
    ADFMacroDefinition,
    ADFMacroRegistry,
    MacroUtilityRecord,
)


def test_adf_macro_definition_digest_factory_and_compat_constructor():
    old = ADFMacroDefinition("ADF_FORAGE", ("MOVE_EAST", "EAT_LUMEN"))
    new = ADFMacroDefinition(
        macro_id="ADF_FORAGE",
        body_codons=("000", "001"),
        primitive_actions=("MOVE_EAST", "EAT_LUMEN"),
    )
    assert old.name == old.macro_id == "ADF_FORAGE"
    assert new.digest() == ADFMacroDefinition.from_dict(new.to_dict()).digest()


def test_adf_macro_expands_to_bounded_subroutine_and_preserves_source_map():
    registry = ADFMacroRegistry().register(
        ADFMacroDefinition(
            macro_id="ADF_FORAGE",
            body_codons=("000", "001"),
            primitive_actions=("MOVE_EAST", "EAT_LUMEN"),
        )
    )
    registry, result = registry.expand("ADF_FORAGE", ADFExecutionPolicy(max_expansion_length=4))
    assert result.executed
    assert result.status == "expanded"
    assert result.expanded_actions == ("MOVE_EAST", "EAT_LUMEN")
    assert all(source.macro_id == "ADF_FORAGE" for source in result.expanded_sources)
    assert registry.usage_counts["ADF_FORAGE"] == 1


def test_adf_recursive_expansion_blocked():
    registry = ADFMacroRegistry().register(ADFMacroDefinition("ADF_LOOP", ("ADF_LOOP",)))
    _, result = registry.expand("ADF_LOOP", ADFExecutionPolicy(max_expansion_depth=2))
    assert not result.executed
    assert result.status == "blocked_depth"


def test_adf_macro_inheritance_and_pruning_policy_staged():
    registry = ADFMacroRegistry().register(ADFMacroDefinition("ADF_KEEP", ("WAIT",)))
    inherited = ADFInheritancePolicy("copy_accepted_macros").inherit(registry)
    assert inherited.get("ADF_KEEP") is not None
    decision = inherited.pruning_decision("ADF_KEEP", mean_fitness_delta=-1.0)
    assert decision.decision == "review"
    utility = MacroUtilityRecord("ADF_KEEP", 0, 0.0, 1, None, None, "insufficient_data")
    assert utility.digest
