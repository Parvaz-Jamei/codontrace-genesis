"""Compatibility facade for the canonical ADF runtime implementation.

Historically this module carried a small standalone ADF lifecycle scaffold.
That duplicated ``adf_runtime`` and made lifecycle behavior easier to drift
from the engine path.  It now re-exports the runtime-backed classes so old
imports keep working while execution, inheritance, pruning, usage accounting,
digests, and source maps all flow through one canonical implementation.
"""

from __future__ import annotations

from codontrace.genesis.adf_runtime import (
    ADFExecutionPolicy,
    ADFExpansionResult,
    ADFInheritancePolicy,
    ADFMacroRegistry,
    ADFPruningPolicy,
    ADFUsefulnessReport,
)

__all__ = [
    "ADFExecutionPolicy",
    "ADFExpansionResult",
    "ADFInheritancePolicy",
    "ADFMacroRegistry",
    "ADFPruningPolicy",
    "ADFUsefulnessReport",
]
