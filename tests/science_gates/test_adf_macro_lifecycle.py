from codontrace.genesis.adf_lifecycle import (
    ADFInheritancePolicy,
    ADFMacroRegistry,
    ADFPruningPolicy,
)


def test_adf_macro_expand_usage_inherit_and_prune():
    registry = ADFMacroRegistry().register("ADF_1000", ("MOVE_NORTH", "EAT_LUMEN"))
    registry, expansion = registry.expand("ADF_1000")

    assert expansion.executed is True
    assert expansion.expanded_actions == ("MOVE_NORTH", "EAT_LUMEN")
    assert registry.usefulness_report("ADF_1000").usage_count == 1

    child = ADFInheritancePolicy().inherit(registry)
    assert child.digest() == registry.digest()

    pruned = child.prune(ADFPruningPolicy(min_usage_count=2))
    assert pruned.macros == ()
