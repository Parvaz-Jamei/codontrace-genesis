"""Runtime ADF macro registry and bounded expansion helpers.

The API is backward-compatible with earlier ``ADFMacroDefinition(name,
primitive_actions)`` tests and also supports the stronger Phase 2 shape
``ADFMacroDefinition(macro_id=..., body_codons=...)``. Macro expansion is a
bounded subroutine mechanism; it is not a claim of language emergence or
semantic closure.
"""

from __future__ import annotations

import hashlib
import json
import math
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from typing import cast

from codontrace._types import JsonValue
from codontrace.errors import ConfigurationError
from codontrace.genesis.ribosome import BrainTokenSource


def _digest(payload: Mapping[str, JsonValue]) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _require_finite(value: float, name: str) -> float:
    value = float(value)
    if not math.isfinite(value):
        raise ConfigurationError(f"{name} must be finite.")
    return value


@dataclass(frozen=True, slots=True, init=False)
class ADFMacroDefinition:
    """Executable ADF macro definition with compatibility aliases.

    Old code can construct ``ADFMacroDefinition("ADF_X", ("MOVE",))``. New
    Phase 2 code can construct ``ADFMacroDefinition(macro_id="ADF_X",
    body_codons=("000",))``. ``primitive_actions`` remains the executable body;
    ``body_codons`` is source/provenance metadata when codons are known.
    """

    name: str
    primitive_actions: tuple[str, ...]
    description: str
    metadata: dict[str, JsonValue]
    macro_id: str
    body_codons: tuple[str, ...]
    created_by_organism: str | None
    created_at_generation: int
    parent_macro_id: str | None
    source_pattern_digest: str | None
    definition_digest: str

    def __init__(
        self,
        name: str | None = None,
        primitive_actions: Sequence[str] | None = None,
        description: str = "",
        metadata: Mapping[str, JsonValue] | None = None,
        *,
        macro_id: str | None = None,
        body_codons: Sequence[str] | None = None,
        created_by_organism: str | None = None,
        created_at_generation: int = 0,
        parent_macro_id: str | None = None,
        source_pattern_digest: str | None = None,
        digest: str | None = None,
    ) -> None:
        resolved_id = macro_id or name
        if not resolved_id or not str(resolved_id).startswith("ADF_"):
            raise ConfigurationError("ADFMacroDefinition macro_id/name must start with 'ADF_'.")
        actions = tuple(str(item) for item in (primitive_actions or ()))
        codons = tuple(str(item) for item in (body_codons or ()))
        if not actions and codons:
            actions = codons
        if not actions:
            raise ConfigurationError(
                "ADFMacroDefinition requires primitive_actions or body_codons."
            )
        payload: dict[str, JsonValue] = {
            "macro_id": str(resolved_id),
            "primitive_actions": cast(JsonValue, list(actions)),
            "body_codons": cast(JsonValue, list(codons)),
            "description": description,
            "metadata": dict(sorted((metadata or {}).items())),
            "created_by_organism": created_by_organism,
            "created_at_generation": created_at_generation,
            "parent_macro_id": parent_macro_id,
            "source_pattern_digest": source_pattern_digest,
        }
        computed = _digest(payload)
        if digest is not None and digest != computed:
            raise ConfigurationError("ADFMacroDefinition digest mismatch.")
        object.__setattr__(self, "name", str(resolved_id))
        object.__setattr__(self, "macro_id", str(resolved_id))
        object.__setattr__(self, "primitive_actions", actions)
        object.__setattr__(self, "body_codons", codons)
        object.__setattr__(self, "description", description)
        object.__setattr__(self, "metadata", dict(metadata or {}))
        object.__setattr__(self, "created_by_organism", created_by_organism)
        object.__setattr__(self, "created_at_generation", created_at_generation)
        object.__setattr__(self, "parent_macro_id", parent_macro_id)
        object.__setattr__(self, "source_pattern_digest", source_pattern_digest)
        object.__setattr__(self, "definition_digest", computed)

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "name": self.name,
            "macro_id": self.macro_id,
            "primitive_actions": list(self.primitive_actions),
            "body_codons": list(self.body_codons),
            "description": self.description,
            "metadata": dict(sorted(self.metadata.items())),
            "created_by_organism": self.created_by_organism,
            "created_at_generation": self.created_at_generation,
            "parent_macro_id": self.parent_macro_id,
            "source_pattern_digest": self.source_pattern_digest,
            "digest": self.definition_digest,
        }

    def digest(self) -> str:
        return self.definition_digest

    @classmethod
    def from_dict(cls, data: Mapping[str, JsonValue]) -> ADFMacroDefinition:
        return cls(
            macro_id=str(data.get("macro_id") or data.get("name")),
            primitive_actions=tuple(str(item) for item in _list(data.get("primitive_actions"))),
            body_codons=tuple(str(item) for item in _list(data.get("body_codons"))),
            description=str(data.get("description", "")),
            metadata=cast(Mapping[str, JsonValue], data.get("metadata"))
            if isinstance(data.get("metadata"), Mapping)
            else None,
            created_by_organism=None
            if data.get("created_by_organism") is None
            else str(data.get("created_by_organism")),
            created_at_generation=_json_int(
                data.get("created_at_generation", 0), "created_at_generation"
            ),
            parent_macro_id=None
            if data.get("parent_macro_id") is None
            else str(data.get("parent_macro_id")),
            source_pattern_digest=None
            if data.get("source_pattern_digest") is None
            else str(data.get("source_pattern_digest")),
            digest=None if data.get("digest") is None else str(data.get("digest")),
        )


@dataclass(frozen=True, slots=True)
class ADFExecutionPolicy:
    max_expansion_length: int = 32
    unknown_token_policy: str = "block"
    count_usage: bool = True
    max_expansion_depth: int = 4
    mode: str = "expand_to_primitive_sequence"

    def __post_init__(self) -> None:
        if self.max_expansion_length <= 0 or self.max_expansion_depth <= 0:
            raise ConfigurationError("max expansion length/depth must be > 0.")
        if self.unknown_token_policy not in {"block", "pass_through"}:
            raise ConfigurationError("unknown_token_policy must be 'block' or 'pass_through'.")
        if self.mode != "expand_to_primitive_sequence":
            raise ConfigurationError("ADFExecutionPolicy.mode must be 'expand_to_primitive_sequence'.")

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "mode": self.mode,
            "max_expansion_length": self.max_expansion_length,
            "unknown_token_policy": self.unknown_token_policy,
            "count_usage": self.count_usage,
            "max_expansion_depth": self.max_expansion_depth,
        }


@dataclass(frozen=True, slots=True, init=False)
class ADFExpansionResult:
    token: str
    macro_id: str
    expanded_sources: tuple[BrainTokenSource, ...]
    expanded_actions: tuple[str, ...]
    expansion_depth: int
    status: str
    executed: bool
    reason: str
    usage_count_after: int
    expansion_digest: str

    def __init__(
        self,
        token: str | None = None,
        expanded_actions: Sequence[str] = (),
        executed: bool | None = None,
        reason: str | None = None,
        usage_count_after: int = 0,
        *,
        macro_id: str | None = None,
        expanded_sources: Sequence[BrainTokenSource] = (),
        expansion_depth: int = 0,
        status: str | None = None,
        digest: str | None = None,
    ) -> None:
        resolved = macro_id or token or ""
        if not resolved:
            raise ConfigurationError("ADFExpansionResult requires token or macro_id.")
        st = status or ("expanded" if executed else (reason or "blocked"))
        ex = bool(executed) if executed is not None else st == "expanded"
        rsn = reason or st
        actions = tuple(str(item) for item in expanded_actions)
        sources = tuple(expanded_sources)
        payload: dict[str, JsonValue] = {
            "macro_id": resolved,
            "expanded_sources": cast(JsonValue, [source.to_dict() for source in sources]),
            "expanded_actions": cast(JsonValue, list(actions)),
            "expansion_depth": expansion_depth,
            "status": st,
            "executed": ex,
            "reason": rsn,
            "usage_count_after": usage_count_after,
        }
        computed = _digest(payload)
        if digest is not None and digest != computed:
            raise ConfigurationError("ADFExpansionResult digest mismatch.")
        object.__setattr__(self, "token", resolved)
        object.__setattr__(self, "macro_id", resolved)
        object.__setattr__(self, "expanded_sources", sources)
        object.__setattr__(self, "expanded_actions", actions)
        object.__setattr__(self, "expansion_depth", expansion_depth)
        object.__setattr__(self, "status", st)
        object.__setattr__(self, "executed", ex)
        object.__setattr__(self, "reason", rsn)
        object.__setattr__(self, "usage_count_after", usage_count_after)
        object.__setattr__(self, "expansion_digest", computed)

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "token": self.token,
            "macro_id": self.macro_id,
            "expanded_sources": [source.to_dict() for source in self.expanded_sources],
            "expanded_actions": list(self.expanded_actions),
            "expansion_depth": self.expansion_depth,
            "status": self.status,
            "executed": self.executed,
            "reason": self.reason,
            "usage_count_after": self.usage_count_after,
            "digest": self.expansion_digest,
        }

    @property
    def adf_name(self) -> str:
        """Backward-compatible name used by the older adf_lifecycle facade."""
        return self.token

    def digest(self) -> str:
        return self.expansion_digest


@dataclass(frozen=True, slots=True)
class ADFUsefulnessReport:
    token: str
    usage_count: int
    compression_gain: float
    fitness_delta: float
    useful: bool

    @property
    def adf_name(self) -> str:
        """Backward-compatible name used by the older adf_lifecycle facade."""
        return self.token

    @property
    def reuse_score(self) -> float:
        """Backward-compatible reuse score; canonical runtime uses compression_gain."""
        return self.compression_gain

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "token": self.token,
            "adf_name": self.adf_name,
            "usage_count": self.usage_count,
            "compression_gain": self.compression_gain,
            "reuse_score": self.reuse_score,
            "fitness_delta": self.fitness_delta,
            "useful": self.useful,
        }


@dataclass(frozen=True, slots=True)
class ADFUsefulnessControlReport:
    """Phase 2 ADF usefulness evidence with explicit controls and costs.

    This report separates compression from utility: a compact macro is not
    claim-ready unless it also has task/cost evidence and beats null or
    permutation controls.
    """

    macro_id: str
    reuse_count: int
    compression_ratio: float
    task_delta: float
    runtime_cost_delta: float
    learning_cost_delta: float
    null_macro_delta: float
    permutation_control_delta: float
    utility_status: str
    source_map_digest: str | None = None
    schema_version: str = "adf_usefulness_control_report_v1"
    digest: str = ""

    def __post_init__(self) -> None:
        if self.utility_status not in {
            "control_supported",
            "provisional",
            "insufficient_data",
            "control_failed",
        }:
            raise ConfigurationError("Unsupported ADFUsefulnessControlReport.utility_status.")
        for attr in (
            "compression_ratio",
            "task_delta",
            "runtime_cost_delta",
            "learning_cost_delta",
            "null_macro_delta",
            "permutation_control_delta",
        ):
            object.__setattr__(self, attr, round(_require_finite(getattr(self, attr), attr), 10))
        if self.reuse_count < 0:
            raise ConfigurationError("reuse_count must be non-negative.")
        computed = _digest(self._payload())
        if self.digest and self.digest != computed:
            raise ConfigurationError("ADFUsefulnessControlReport digest mismatch.")
        object.__setattr__(self, "digest", computed)

    @property
    def claim_eligible(self) -> bool:
        return (
            self.utility_status == "control_supported"
            and self.source_map_digest is not None
            and self.reuse_count >= 2
            and self.compression_ratio > 0.0
        )

    def _payload(self) -> dict[str, JsonValue]:
        return {
            "schema_version": self.schema_version,
            "macro_id": self.macro_id,
            "reuse_count": self.reuse_count,
            "compression_ratio": self.compression_ratio,
            "task_delta": self.task_delta,
            "runtime_cost_delta": self.runtime_cost_delta,
            "learning_cost_delta": self.learning_cost_delta,
            "null_macro_delta": self.null_macro_delta,
            "permutation_control_delta": self.permutation_control_delta,
            "utility_status": self.utility_status,
            "source_map_digest": self.source_map_digest,
        }

    def to_dict(self) -> dict[str, JsonValue]:
        return {**self._payload(), "claim_eligible": self.claim_eligible, "digest": self.digest}


def build_adf_usefulness_control_report(
    registry: "ADFMacroRegistry",
    macro_id: str,
    *,
    task_delta: float = 0.0,
    runtime_cost_delta: float = 0.0,
    learning_cost_delta: float = 0.0,
    null_macro_delta: float = 0.0,
    permutation_control_delta: float = 0.0,
    source_map_digest: str | None = None,
) -> ADFUsefulnessControlReport:
    definition = registry.get(macro_id)
    usage = registry.usage_counts.get(macro_id, 0)
    primitive_count = 0 if definition is None else len(definition.primitive_actions)
    compression_ratio = 0.0 if primitive_count <= 1 else round((primitive_count - 1) / primitive_count, 10)
    task_delta = _require_finite(task_delta, "task_delta")
    runtime_cost_delta = _require_finite(runtime_cost_delta, "runtime_cost_delta")
    learning_cost_delta = _require_finite(learning_cost_delta, "learning_cost_delta")
    null_macro_delta = _require_finite(null_macro_delta, "null_macro_delta")
    permutation_control_delta = _require_finite(permutation_control_delta, "permutation_control_delta")
    net_task = task_delta - runtime_cost_delta - learning_cost_delta
    beats_controls = net_task > null_macro_delta and net_task > permutation_control_delta
    has_claim_shape = (
        definition is not None
        and usage >= 2
        and source_map_digest is not None
        and compression_ratio > 0.0
    )
    if usage <= 0 or definition is None:
        status = "insufficient_data"
    elif beats_controls and has_claim_shape:
        status = "control_supported"
    elif task_delta > 0 or compression_ratio > 0:
        status = "provisional"
    else:
        status = "control_failed"
    return ADFUsefulnessControlReport(
        macro_id=macro_id,
        reuse_count=usage,
        compression_ratio=compression_ratio,
        task_delta=round(float(task_delta), 10),
        runtime_cost_delta=round(float(runtime_cost_delta), 10),
        learning_cost_delta=round(float(learning_cost_delta), 10),
        null_macro_delta=round(float(null_macro_delta), 10),
        permutation_control_delta=round(float(permutation_control_delta), 10),
        utility_status=status,
        source_map_digest=source_map_digest,
    )


@dataclass(frozen=True, slots=True)
class MacroUtilityRecord:
    macro_id: str
    usage_count: int
    expansion_success_rate: float
    inherited_generations: int
    provisional_mean_reward_delta: float | None
    contribution_ledger_digest: str | None
    status: str
    digest: str = ""

    def __post_init__(self) -> None:
        if self.status not in {"provisional", "ledger_supported", "insufficient_data"}:
            raise ConfigurationError("Unsupported MacroUtilityRecord.status.")
        computed = _digest(self._payload())
        if self.digest and self.digest != computed:
            raise ConfigurationError("MacroUtilityRecord digest mismatch.")
        object.__setattr__(self, "digest", computed)

    def _payload(self) -> dict[str, JsonValue]:
        return {
            "macro_id": self.macro_id,
            "usage_count": self.usage_count,
            "expansion_success_rate": self.expansion_success_rate,
            "inherited_generations": self.inherited_generations,
            "provisional_mean_reward_delta": self.provisional_mean_reward_delta,
            "contribution_ledger_digest": self.contribution_ledger_digest,
            "status": self.status,
        }

    def to_dict(self) -> dict[str, JsonValue]:
        return {**self._payload(), "digest": self.digest}


@dataclass(frozen=True, slots=True)
class MacroPruningDecision:
    macro_id: str
    reason: str
    usage_count: int
    utility_status: str
    mean_fitness_delta: float | None
    mean_novelty_delta: float | None
    decision: str
    digest: str = ""

    def __post_init__(self) -> None:
        if self.decision not in {"keep", "prune", "protect", "review"}:
            raise ConfigurationError("Unsupported MacroPruningDecision.decision.")
        computed = _digest(self._payload())
        if self.digest and self.digest != computed:
            raise ConfigurationError("MacroPruningDecision digest mismatch.")
        object.__setattr__(self, "digest", computed)

    def _payload(self) -> dict[str, JsonValue]:
        return {
            "macro_id": self.macro_id,
            "reason": self.reason,
            "usage_count": self.usage_count,
            "utility_status": self.utility_status,
            "mean_fitness_delta": self.mean_fitness_delta,
            "mean_novelty_delta": self.mean_novelty_delta,
            "decision": self.decision,
        }

    def to_dict(self) -> dict[str, JsonValue]:
        return {**self._payload(), "digest": self.digest}


@dataclass(frozen=True, slots=True)
class ADFPruningPolicy:
    min_usage_count: int = 1
    min_compression_gain: float = 0.0
    min_fitness_delta: float = 0.0
    allow_fitness_pruning_without_ledger: bool = False

    def should_prune(self, report: ADFUsefulnessReport) -> bool:
        return (
            report.usage_count < self.min_usage_count
            or report.compression_gain < self.min_compression_gain
            or (
                self.allow_fitness_pruning_without_ledger
                and report.fitness_delta < self.min_fitness_delta
            )
        )


@dataclass(frozen=True, slots=True)
class ADFInheritancePolicy:
    mode: str = "copy_accepted_macros"

    def inherit(self, registry: ADFMacroRegistry) -> ADFMacroRegistry:
        if self.mode == "none":
            return ADFMacroRegistry()
        if self.mode in {"copy_accepted_macros", "copy_registry", "copy_with_usage"}:
            return ADFMacroRegistry(
                registry.definitions,
                dict(registry.usage_counts),
                dict(registry.inherited_generations),
            )
        raise ConfigurationError("Unsupported ADFInheritancePolicy.mode.")


@dataclass(frozen=True, slots=True)
class ADFMacroRegistry:
    definitions: tuple[ADFMacroDefinition, ...] = ()
    usage_counts: dict[str, int] = field(default_factory=dict)
    inherited_generations: dict[str, int] = field(default_factory=dict)

    def __post_init__(self) -> None:
        names = [item.name for item in self.definitions]
        if len(names) != len(set(names)):
            raise ConfigurationError("Duplicate ADF macro definition names.")
        object.__setattr__(
            self, "definitions", tuple(sorted(self.definitions, key=lambda item: item.name))
        )
        object.__setattr__(self, "usage_counts", dict(self.usage_counts))
        object.__setattr__(self, "inherited_generations", dict(self.inherited_generations))

    @property
    def macros(self) -> tuple[tuple[str, tuple[str, ...]], ...]:
        """Backward-compatible lifecycle view over canonical runtime definitions."""
        return tuple((item.name, item.primitive_actions) for item in self.definitions)

    def register(
        self,
        definition: ADFMacroDefinition | str,
        primitive_actions: Sequence[str] | None = None,
    ) -> ADFMacroRegistry:
        """Register a macro using the canonical definition or the legacy facade shape."""
        if isinstance(definition, str):
            definition = ADFMacroDefinition(definition, primitive_actions or ())
        elif primitive_actions is not None:
            raise ConfigurationError("primitive_actions are only accepted with a string macro name.")
        if self.get(definition.name) is not None:
            raise ConfigurationError(f"ADF macro {definition.name!r} already exists.")
        return ADFMacroRegistry(
            (*self.definitions, definition),
            dict(self.usage_counts),
            dict(self.inherited_generations),
        )

    def get(self, token: str) -> ADFMacroDefinition | None:
        for definition in self.definitions:
            if definition.name == token or definition.macro_id == token:
                return definition
        return None

    def expand(
        self,
        token: str,
        policy: ADFExecutionPolicy | None = None,
        *,
        _stack: tuple[str, ...] = (),
        _depth: int = 0,
    ) -> tuple[ADFMacroRegistry, ADFExpansionResult]:
        policy = policy or ADFExecutionPolicy()
        definition = self.get(token)
        if definition is None:
            if policy.unknown_token_policy == "pass_through":
                return self, ADFExpansionResult(
                    token, (token,), False, "unknown_pass_through", self.usage_counts.get(token, 0)
                )
            return self, ADFExpansionResult(
                token,
                (),
                False,
                "unknown_adf",
                self.usage_counts.get(token, 0),
                status="invalid_macro",
            )
        if token in _stack or _depth >= policy.max_expansion_depth:
            return self, ADFExpansionResult(
                token,
                (),
                False,
                "recursive_or_depth_blocked",
                self.usage_counts.get(token, 0),
                macro_id=definition.macro_id,
                expansion_depth=_depth,
                status="blocked_depth",
            )
        if len(definition.primitive_actions) > policy.max_expansion_length:
            return self, ADFExpansionResult(
                token,
                (),
                False,
                "expansion_too_long",
                self.usage_counts.get(token, 0),
                macro_id=definition.macro_id,
                expansion_depth=_depth,
                status="blocked_depth",
            )
        actions: list[str] = []
        sources: list[BrainTokenSource] = []
        for index, action in enumerate(definition.primitive_actions):
            if action.startswith("ADF_") and self.get(action) is not None:
                _, nested = self.expand(action, policy, _stack=(*_stack, token), _depth=_depth + 1)
                if not nested.executed:
                    return self, ADFExpansionResult(
                        token,
                        (),
                        False,
                        nested.reason,
                        self.usage_counts.get(token, 0),
                        macro_id=definition.macro_id,
                        expansion_depth=_depth,
                        status=nested.status,
                    )
                actions.extend(nested.expanded_actions)
                sources.extend(nested.expanded_sources)
            else:
                actions.append(action)
                codon = (
                    definition.body_codons[index] if index < len(definition.body_codons) else action
                )
                sources.append(
                    BrainTokenSource(
                        genome_pos=index,
                        codon=codon,
                        macro_id=definition.macro_id,
                        macro_stack=(*_stack, definition.macro_id),
                        expansion_depth=_depth,
                    )
                )
        if len(actions) > policy.max_expansion_length:
            return self, ADFExpansionResult(
                token,
                (),
                False,
                "expansion_too_long",
                self.usage_counts.get(token, 0),
                macro_id=definition.macro_id,
                expansion_depth=_depth,
                status="blocked_depth",
            )
        counts = dict(self.usage_counts)
        if policy.count_usage:
            counts[token] = counts.get(token, 0) + 1
        next_registry = ADFMacroRegistry(self.definitions, counts, dict(self.inherited_generations))
        return next_registry, ADFExpansionResult(
            token,
            tuple(actions),
            True,
            "expanded",
            counts.get(token, 0),
            macro_id=definition.macro_id,
            expanded_sources=tuple(sources),
            expansion_depth=_depth,
            status="expanded",
        )

    def execute(
        self,
        token: str,
        executor: Callable[[str], JsonValue] | None = None,
        policy: ADFExecutionPolicy | None = None,
    ) -> tuple[ADFMacroRegistry, ADFExpansionResult, tuple[JsonValue, ...]]:
        registry, expansion = self.expand(token, policy)
        if not expansion.executed or executor is None:
            return registry, expansion, ()
        return registry, expansion, tuple(executor(action) for action in expansion.expanded_actions)

    def usefulness_report(self, token: str, *, fitness_delta: float = 0.0) -> ADFUsefulnessReport:
        definition = self.get(token)
        usage = self.usage_counts.get(token, 0)
        primitive_len = 0 if definition is None else len(definition.primitive_actions)
        compression_gain = (
            0.0 if primitive_len <= 1 else round((primitive_len - 1) / primitive_len, 10)
        )
        return ADFUsefulnessReport(
            token, usage, compression_gain, fitness_delta, usage > 0 and compression_gain >= 0.0
        )

    def utility_record(
        self,
        token: str,
        *,
        contribution_ledger_digest: str | None = None,
        provisional_mean_reward_delta: float | None = None,
    ) -> MacroUtilityRecord:
        usage = self.usage_counts.get(token, 0)
        status = (
            "ledger_supported"
            if contribution_ledger_digest
            else ("provisional" if usage else "insufficient_data")
        )
        success_rate = 1.0 if usage > 0 else 0.0
        return MacroUtilityRecord(
            token,
            usage,
            success_rate,
            self.inherited_generations.get(token, 0),
            provisional_mean_reward_delta,
            contribution_ledger_digest,
            status,
        )

    def pruning_decision(
        self,
        token: str,
        policy: ADFPruningPolicy | None = None,
        *,
        contribution_ledger_digest: str | None = None,
        mean_fitness_delta: float | None = None,
        mean_novelty_delta: float | None = None,
    ) -> MacroPruningDecision:
        policy = policy or ADFPruningPolicy()
        usage = self.usage_counts.get(token, 0)
        if (
            contribution_ledger_digest is None
            and mean_fitness_delta is not None
            and not policy.allow_fitness_pruning_without_ledger
        ):
            return MacroPruningDecision(
                token,
                "fitness_pruning_requires_contribution_ledger",
                usage,
                "provisional",
                mean_fitness_delta,
                mean_novelty_delta,
                "review",
            )
        if usage < policy.min_usage_count:
            return MacroPruningDecision(
                token,
                "unused_or_underused",
                usage,
                "ledger_supported" if contribution_ledger_digest else "provisional",
                mean_fitness_delta,
                mean_novelty_delta,
                "prune",
            )
        return MacroPruningDecision(
            token,
            "utility_sufficient",
            usage,
            "ledger_supported" if contribution_ledger_digest else "provisional",
            mean_fitness_delta,
            mean_novelty_delta,
            "keep",
        )

    def prune(self, policy: ADFPruningPolicy | None = None) -> ADFMacroRegistry:
        policy = policy or ADFPruningPolicy()
        kept = tuple(
            item
            for item in self.definitions
            if self.pruning_decision(item.name, policy).decision != "prune"
        )
        kept_names = {item.name for item in kept}
        return ADFMacroRegistry(
            kept,
            {name: count for name, count in self.usage_counts.items() if name in kept_names},
            {name: gen for name, gen in self.inherited_generations.items() if name in kept_names},
        )

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "definitions": [item.to_dict() for item in self.definitions],
            "usage_counts": dict(sorted(self.usage_counts.items())),
            "inherited_generations": dict(sorted(self.inherited_generations.items())),
        }

    def digest(self) -> str:
        return _digest(self.to_dict())


def _json_int(value: JsonValue, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ConfigurationError(f"{field} must be an integer")
    return value


def _list(value: object) -> list[object]:
    if value is None:
        return []
    if not isinstance(value, list | tuple):
        raise ConfigurationError("expected list")
    return list(value)

# Phase 3 ADF compression/controls evidence reports.
@dataclass(frozen=True, slots=True)
class ADFCompressionReport:
    macro_id: str
    source_map_digest: str
    reuse_count: int
    compression_ratio: float
    runtime_effect_digest: str
    schema_version: str = "adf_compression_report_v1"
    def __post_init__(self) -> None:
        object.__setattr__(self, "compression_ratio", _require_finite(self.compression_ratio, "compression_ratio"))
        if self.reuse_count < 0 or not self.source_map_digest or not self.runtime_effect_digest:
            raise ConfigurationError("ADFCompressionReport requires reuse, source map, and runtime effect")
    @property
    def claim_eligible(self) -> bool:
        return self.reuse_count >= 2 and self.compression_ratio > 0.0
    def to_dict(self) -> dict[str, JsonValue]:
        return {"schema_version": self.schema_version, "macro_id": self.macro_id, "source_map_digest": self.source_map_digest, "reuse_count": self.reuse_count, "compression_ratio": self.compression_ratio, "runtime_effect_digest": self.runtime_effect_digest, "claim_eligible": self.claim_eligible}
    def digest(self) -> str:
        from codontrace.genesis.canonical import canonical_digest
        return canonical_digest(self.to_dict())

@dataclass(frozen=True, slots=True)
class ADFReuseTrajectory:
    macro_id: str
    reuse_ticks: tuple[int, ...]
    schema_version: str = "adf_reuse_trajectory_v1"
    def to_dict(self) -> dict[str, JsonValue]:
        return {"schema_version": self.schema_version, "macro_id": self.macro_id, "reuse_ticks": list(self.reuse_ticks)}
    def digest(self) -> str:
        from codontrace.genesis.canonical import canonical_digest
        return canonical_digest(self.to_dict())

ADFSourceMapLineage = ADFReuseTrajectory
ADFNullControlReport = ADFCompressionReport
ADFPermutationControlReport = ADFCompressionReport
ADFCostBenefitReport = ADFCompressionReport
