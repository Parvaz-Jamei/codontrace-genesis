from __future__ import annotations

import inspect

import codontrace.genesis as genesis
from codontrace.genesis import adf_lifecycle, adf_runtime


def test_adf_lifecycle_facade_uses_canonical_runtime_classes() -> None:
    assert adf_lifecycle.ADFExecutionPolicy is adf_runtime.ADFExecutionPolicy
    assert adf_lifecycle.ADFExpansionResult is adf_runtime.ADFExpansionResult
    assert adf_lifecycle.ADFInheritancePolicy is adf_runtime.ADFInheritancePolicy
    assert adf_lifecycle.ADFMacroRegistry is adf_runtime.ADFMacroRegistry
    assert adf_lifecycle.ADFPruningPolicy is adf_runtime.ADFPruningPolicy
    assert adf_lifecycle.ADFUsefulnessReport is adf_runtime.ADFUsefulnessReport


def test_public_adf_api_resolves_to_runtime_not_standalone_scaffold() -> None:
    assert genesis.ADFMacroRegistry is adf_runtime.ADFMacroRegistry
    assert genesis.RuntimeADFMacroRegistry is adf_runtime.ADFMacroRegistry
    assert genesis.ADFExecutionPolicy is adf_runtime.ADFExecutionPolicy
    assert genesis.RuntimeADFExecutionPolicy is adf_runtime.ADFExecutionPolicy


def test_legacy_adf_lifecycle_shape_runs_through_runtime_digest_path() -> None:
    registry = adf_lifecycle.ADFMacroRegistry().register(
        "ADF_COMPAT", ("MOVE_NORTH", "EAT_LUMEN")
    )
    next_registry, expansion = registry.expand("ADF_COMPAT")
    child = adf_lifecycle.ADFInheritancePolicy().inherit(next_registry)

    assert expansion.executed is True
    assert expansion.adf_name == "ADF_COMPAT"
    assert expansion.expanded_actions == ("MOVE_NORTH", "EAT_LUMEN")
    assert next_registry.usefulness_report("ADF_COMPAT").adf_name == "ADF_COMPAT"
    assert next_registry.usefulness_report("ADF_COMPAT").usage_count == 1
    assert child.digest() == next_registry.digest()
    assert child.macros == (("ADF_COMPAT", ("MOVE_NORTH", "EAT_LUMEN")),)


def test_adf_lifecycle_module_has_no_local_scaffold_class_definitions() -> None:
    source = inspect.getsource(adf_lifecycle)
    assert "class ADFMacroRegistry" not in source
    assert "class ADFExecutionPolicy" not in source
