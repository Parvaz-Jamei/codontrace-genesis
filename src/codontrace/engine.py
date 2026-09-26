"""Unified GENESIS experiment engine orchestration layer.

This module is the stable public facade. Implementation lives in principled
siblings:

- ``codontrace.engine_spec`` — config, experiment spec, generation-boundary observer
- ``codontrace.engine_runtime`` — ``GenesisEngine`` orchestrator
- ``codontrace.engine_run_result`` — ``GenesisRunResult`` evidence surface
- ``codontrace.engine_claims`` — claim ladder / protocol / summary helpers
- ``codontrace.engine_results`` — tick / snapshot / run identity types
- ``codontrace.engine_digest`` — replay-critical hashing

Historical imports (``from codontrace.engine import …``) stay stable.
See ``docs/ENGINE_REPLAY_CONTRACT.md``.
"""

from __future__ import annotations

from codontrace.engine_claims import (
    _execution_source_digest,
    _phase2_hashes,
    apply_human_review,
    attach_review_result,
)
from codontrace.engine_digest import (
    _action_registry_hash,
    _adf_vocabulary_hash,
    _codon_table_hash,
    _digest,
    _digest_sequence,
    _genome_spec_hash,
    _json_float_value,
    _json_str_tuple,
    _jsonish_for_digest,
    _object_hash,
    _ribosome_hash,
    _stable_default_action_registry_hash,
    _status_registry_digest,
)
from codontrace.engine_results import (
    ConsistencyValidationResult,
    GenesisRun,
    GenesisRunSummary,
    GenesisSnapshot,
    GenesisTickResult,
)
from codontrace.engine_run_result import GenesisRunResult
from codontrace.engine_runtime import (
    GenesisEngine,
    _default_qd_archive,
    _effective_evolution_config,
)
from codontrace.engine_spec import (
    GenerationBoundaryObserver,
    GenesisEngineConfig,
    GenesisExperimentSpec,
)

__all__ = [
    "ConsistencyValidationResult",
    "GenerationBoundaryObserver",
    "GenesisEngine",
    "GenesisEngineConfig",
    "GenesisExperimentSpec",
    "GenesisRun",
    "GenesisRunResult",
    "GenesisRunSummary",
    "GenesisSnapshot",
    "GenesisTickResult",
    "apply_human_review",
    "attach_review_result",
    "_action_registry_hash",
    "_adf_vocabulary_hash",
    "_codon_table_hash",
    "_default_qd_archive",
    "_digest",
    "_digest_sequence",
    "_effective_evolution_config",
    "_execution_source_digest",
    "_genome_spec_hash",
    "_json_float_value",
    "_json_str_tuple",
    "_jsonish_for_digest",
    "_object_hash",
    "_phase2_hashes",
    "_ribosome_hash",
    "_stable_default_action_registry_hash",
    "_status_registry_digest",
]
