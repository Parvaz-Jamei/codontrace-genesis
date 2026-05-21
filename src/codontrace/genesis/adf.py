"""ADF / Dynamic Vocabulary foundation for GENESIS-style experiments.

This module provides deterministic, dependency-free detection of repeated
trace patterns and creates auditable vocabulary proposals. It does not prove
endogenous language emergence, perform unrestricted program synthesis, or mutate
public codon tables automatically.
"""

from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field, replace
from enum import Enum

from codontrace._types import JsonValue
from codontrace.codon import Codon, CodonTable
from codontrace.errors import ConfigurationError
from codontrace.genesis.atp import GenesisATPState
from codontrace.specs import GenomeSpec
from codontrace.trace import Trace, TraceEvent


class ADFCostPolicy(str, Enum):
    """Cost policy for traceable ADF macro proposals."""

    SUM_PRIMITIVE_COSTS = "sum_primitive_costs"
    DISCOUNTED_SUM = "discounted_sum"
    MAX_PRIMITIVE_COST = "max_primitive_cost"
    EXPLICIT = "explicit"


class ADFProposalCostMode(str, Enum):
    """ATP_learning accounting mode for vocabulary proposal passes."""

    PER_RUN = "per_run"
    PER_PATTERN = "per_pattern"
    PER_PROPOSAL = "per_proposal"


@dataclass(frozen=True, slots=True)
class ADFPattern:
    """Repeated action/codon pattern detected from trace evidence."""

    pattern_id: str
    tokens: tuple[str, ...]
    codons: tuple[str, ...]
    length: int
    support_count: int
    first_seen_tick: int
    last_seen_tick: int
    organism_ids: tuple[str, ...]
    trace_refs: tuple[str, ...]
    occurrence_refs: tuple[str, ...] = ()
    occurrence_count: int = 0
    first_event_refs: tuple[str, ...] = ()
    metadata: dict[str, JsonValue] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.pattern_id or self.length <= 0 or len(self.tokens) != self.length:
            msg = "ADFPattern requires a non-empty id and consistent positive length."
            raise ConfigurationError(msg)
        if len(self.codons) != self.length:
            msg = "ADFPattern.codons must have the same length as tokens."
            raise ConfigurationError(msg)
        if self.support_count <= 0:
            msg = "ADFPattern.support_count must be > 0."
            raise ConfigurationError(msg)
        if self.occurrence_count < 0:
            msg = "ADFPattern.occurrence_count must be >= 0."
            raise ConfigurationError(msg)
        if self.occurrence_count == 0:
            object.__setattr__(self, "occurrence_count", self.support_count)
        if not self.occurrence_refs:
            object.__setattr__(self, "occurrence_refs", self.trace_refs)
        if not self.first_event_refs:
            object.__setattr__(self, "first_event_refs", self.trace_refs)
        # occurrence_refs may be deduplicated in older hand-built tests;
        # occurrence_count remains the authoritative count of windows.

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "pattern_id": self.pattern_id,
            "tokens": list(self.tokens),
            "codons": list(self.codons),
            "length": self.length,
            "support_count": self.support_count,
            "first_seen_tick": self.first_seen_tick,
            "last_seen_tick": self.last_seen_tick,
            "organism_ids": list(self.organism_ids),
            "trace_refs": list(self.trace_refs),
            "occurrence_refs": list(self.occurrence_refs),
            "occurrence_count": self.occurrence_count,
            "first_event_refs": list(self.first_event_refs),
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, JsonValue]) -> ADFPattern:
        metadata = data.get("metadata", {})
        if not isinstance(metadata, dict):
            msg = "ADFPattern.metadata must be an object."
            raise ConfigurationError(msg)
        trace_refs = _str_tuple(data, "trace_refs")
        return cls(
            pattern_id=_str(data, "pattern_id"),
            tokens=_str_tuple(data, "tokens"),
            codons=_str_tuple(data, "codons"),
            length=_int(data, "length", 0),
            support_count=_int(data, "support_count", 0),
            first_seen_tick=_int(data, "first_seen_tick", 0),
            last_seen_tick=_int(data, "last_seen_tick", 0),
            organism_ids=_str_tuple(data, "organism_ids"),
            trace_refs=trace_refs,
            occurrence_refs=_str_tuple(data, "occurrence_refs") or trace_refs,
            occurrence_count=_int(data, "occurrence_count", 0),
            first_event_refs=_str_tuple(data, "first_event_refs") or trace_refs,
            metadata={str(k): v for k, v in metadata.items()},
        )

    def digest(self) -> str:
        return _digest(self.to_dict())


@dataclass(frozen=True, slots=True)
class ADFCompressionScore:
    """Compression/reuse score for one ADF candidate."""

    pattern_id: str
    raw_token_count: int
    compressed_token_count: int
    compression_gain: float
    reuse_count: int
    fitness_delta: float | None
    atp_pressure_score: float
    accepted: bool
    reasons: tuple[str, ...]

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "pattern_id": self.pattern_id,
            "raw_token_count": self.raw_token_count,
            "compressed_token_count": self.compressed_token_count,
            "compression_gain": self.compression_gain,
            "reuse_count": self.reuse_count,
            "fitness_delta": self.fitness_delta,
            "atp_pressure_score": self.atp_pressure_score,
            "accepted": self.accepted,
            "reasons": list(self.reasons),
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, JsonValue]) -> ADFCompressionScore:
        raw_delta = data.get("fitness_delta")
        return cls(
            pattern_id=_str(data, "pattern_id"),
            raw_token_count=_int(data, "raw_token_count", 0),
            compressed_token_count=_int(data, "compressed_token_count", 0),
            compression_gain=_float(data, "compression_gain", 0.0),
            reuse_count=_int(data, "reuse_count", 0),
            fitness_delta=None if raw_delta is None else _float(data, "fitness_delta", 0.0),
            atp_pressure_score=_float(data, "atp_pressure_score", 0.0),
            accepted=_bool(data, "accepted", False),
            reasons=_str_tuple(data, "reasons"),
        )

    def digest(self) -> str:
        return _digest(self.to_dict())


@dataclass(frozen=True, slots=True)
class ADFProposal:
    """Auditable dynamic vocabulary proposal; never executable Python code."""

    proposal_id: str
    pattern: ADFPattern
    score: ADFCompressionScore
    proposed_bits: str
    proposed_action: str
    proposed_cost: float
    source: str = "adf_detector"
    status: str = "proposed"
    metadata: dict[str, JsonValue] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.proposal_id or not self.proposed_action:
            msg = "ADFProposal requires non-empty ids/actions."
            raise ConfigurationError(msg)
        if not self.proposed_bits or any(symbol.isspace() for symbol in self.proposed_bits):
            msg = (
                "ADFProposal.proposed_bits/proposed_codon must be non-empty "
                "and contain no whitespace."
            )
            raise ConfigurationError(msg)
        if self.proposed_cost < 0:
            msg = "ADFProposal.proposed_cost must be >= 0."
            raise ConfigurationError(msg)
        if self.status not in {"proposed", "accepted", "rejected"}:
            msg = "ADFProposal.status must be proposed, accepted, or rejected."
            raise ConfigurationError(msg)

    @property
    def proposed_codon(self) -> str:
        """Canonical non-binary-safe codon sequence alias."""

        return self.proposed_bits

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "proposal_id": self.proposal_id,
            "pattern": self.pattern.to_dict(),
            "score": self.score.to_dict(),
            "proposed_bits": self.proposed_bits,
            "proposed_codon": self.proposed_codon,
            "proposed_action": self.proposed_action,
            "proposed_cost": self.proposed_cost,
            "source": self.source,
            "status": self.status,
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, JsonValue]) -> ADFProposal:
        pattern = data.get("pattern")
        score = data.get("score")
        metadata = data.get("metadata", {})
        if not isinstance(pattern, Mapping) or not isinstance(score, Mapping):
            msg = "ADFProposal requires pattern and score objects."
            raise ConfigurationError(msg)
        if not isinstance(metadata, dict):
            msg = "ADFProposal.metadata must be an object."
            raise ConfigurationError(msg)
        return cls(
            proposal_id=_str(data, "proposal_id"),
            pattern=ADFPattern.from_dict(pattern),
            score=ADFCompressionScore.from_dict(score),
            proposed_bits=_str(data, "proposed_bits", _str(data, "proposed_codon", "")),
            proposed_action=_str(data, "proposed_action"),
            proposed_cost=_float(data, "proposed_cost", 0.0),
            source=_str(data, "source", "adf_detector"),
            status=_str(data, "status", "proposed"),
            metadata={str(k): v for k, v in metadata.items()},
        )

    def digest(self) -> str:
        return _digest(self.to_dict())


@dataclass(frozen=True, slots=True)
class DynamicVocabularyConfig:
    """Thresholds for controlled ADF proposal creation."""

    enabled: bool = True
    min_pattern_length: int = 2
    max_pattern_length: int = 8
    min_support_count: int = 3
    min_compression_gain: float = 1.0
    min_reuse_count: int = 2
    max_new_codons: int = 16
    extended_codon_width: int = 4
    require_fitness_non_decrease: bool = True
    require_multi_organism_support: bool = False
    proposal_cost_learning_atp: float = 1.0
    allow_auto_accept: bool = False
    include_blocked_only_patterns: bool = False
    include_blocked_events: bool = False
    include_failed_events: bool = False
    cost_policy: ADFCostPolicy = ADFCostPolicy.SUM_PRIMITIVE_COSTS
    cost_discount: float = 1.0
    min_adf_cost: float = 0.0
    max_adf_cost: float | None = None
    proposal_cost_mode: ADFProposalCostMode = ADFProposalCostMode.PER_PROPOSAL
    genome_spec: GenomeSpec | None = None

    def __post_init__(self) -> None:
        if self.min_pattern_length <= 0 or self.max_pattern_length < self.min_pattern_length:
            msg = "DynamicVocabularyConfig pattern lengths are invalid."
            raise ConfigurationError(msg)
        if self.min_support_count <= 0 or self.min_reuse_count <= 0:
            msg = "DynamicVocabularyConfig support/reuse thresholds must be > 0."
            raise ConfigurationError(msg)
        min_width = 1 if self.genome_spec is not None else 4
        if self.max_new_codons <= 0 or self.extended_codon_width < min_width:
            msg = "DynamicVocabularyConfig max_new_codons must be > 0 and width valid for its spec."
            raise ConfigurationError(msg)
        if self.min_compression_gain < 0 or self.proposal_cost_learning_atp < 0:
            msg = "DynamicVocabularyConfig gains/costs must be >= 0."
            raise ConfigurationError(msg)
        if self.cost_discount < 0 or self.min_adf_cost < 0:
            msg = "ADF cost policy values must be >= 0."
            raise ConfigurationError(msg)
        if self.max_adf_cost is not None and self.max_adf_cost < self.min_adf_cost:
            msg = "max_adf_cost must be >= min_adf_cost when provided."
            raise ConfigurationError(msg)
        if (
            self.genome_spec is not None
            and self.genome_spec.codon_width != self.extended_codon_width
        ):
            msg = "DynamicVocabularyConfig.genome_spec codon_width must match extended_codon_width."
            raise ConfigurationError(msg)
        if not isinstance(self.cost_policy, ADFCostPolicy):
            object.__setattr__(self, "cost_policy", ADFCostPolicy(str(self.cost_policy)))
        if not isinstance(self.proposal_cost_mode, ADFProposalCostMode):
            object.__setattr__(
                self, "proposal_cost_mode", ADFProposalCostMode(str(self.proposal_cost_mode))
            )

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "enabled": self.enabled,
            "min_pattern_length": self.min_pattern_length,
            "max_pattern_length": self.max_pattern_length,
            "min_support_count": self.min_support_count,
            "min_compression_gain": self.min_compression_gain,
            "min_reuse_count": self.min_reuse_count,
            "max_new_codons": self.max_new_codons,
            "extended_codon_width": self.extended_codon_width,
            "require_fitness_non_decrease": self.require_fitness_non_decrease,
            "require_multi_organism_support": self.require_multi_organism_support,
            "proposal_cost_learning_atp": self.proposal_cost_learning_atp,
            "allow_auto_accept": self.allow_auto_accept,
            "include_blocked_only_patterns": self.include_blocked_only_patterns,
            "include_blocked_events": self.include_blocked_events,
            "include_failed_events": self.include_failed_events,
            "cost_policy": self.cost_policy.value,
            "cost_discount": self.cost_discount,
            "min_adf_cost": self.min_adf_cost,
            "max_adf_cost": self.max_adf_cost,
            "proposal_cost_mode": self.proposal_cost_mode.value,
            "genome_spec": None if self.genome_spec is None else self.genome_spec.to_dict(),
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, JsonValue]) -> DynamicVocabularyConfig:
        return cls(
            enabled=_bool(data, "enabled", True),
            min_pattern_length=_int(data, "min_pattern_length", 2),
            max_pattern_length=_int(data, "max_pattern_length", 8),
            min_support_count=_int(data, "min_support_count", 3),
            min_compression_gain=_float(data, "min_compression_gain", 1.0),
            min_reuse_count=_int(data, "min_reuse_count", 2),
            max_new_codons=_int(data, "max_new_codons", 16),
            extended_codon_width=_int(data, "extended_codon_width", 4),
            require_fitness_non_decrease=_bool(data, "require_fitness_non_decrease", True),
            require_multi_organism_support=_bool(data, "require_multi_organism_support", False),
            proposal_cost_learning_atp=_float(data, "proposal_cost_learning_atp", 1.0),
            allow_auto_accept=_bool(data, "allow_auto_accept", False),
            include_blocked_only_patterns=_bool(data, "include_blocked_only_patterns", False),
            include_blocked_events=_bool(data, "include_blocked_events", False),
            include_failed_events=_bool(data, "include_failed_events", False),
            cost_policy=ADFCostPolicy(
                _str(data, "cost_policy", ADFCostPolicy.SUM_PRIMITIVE_COSTS.value)
            ),
            cost_discount=_float(data, "cost_discount", 1.0),
            min_adf_cost=_float(data, "min_adf_cost", 0.0),
            max_adf_cost=None
            if data.get("max_adf_cost") is None
            else _float(data, "max_adf_cost", 0.0),
            proposal_cost_mode=ADFProposalCostMode(
                _str(data, "proposal_cost_mode", ADFProposalCostMode.PER_PROPOSAL.value)
            ),
            genome_spec=(
                GenomeSpec.from_dict(raw_genome_spec)
                if isinstance((raw_genome_spec := data.get("genome_spec")), dict)
                else None
            ),
        )


@dataclass(frozen=True, slots=True)
class DynamicVocabularyState:
    """Immutable dynamic vocabulary proposal state."""

    base_table_version: str
    proposals: tuple[ADFProposal, ...] = ()
    accepted_proposals: tuple[ADFProposal, ...] = ()
    rejected_proposals: tuple[ADFProposal, ...] = ()
    next_available_bits: tuple[str, ...] = field(default_factory=lambda: _binary_codes(4))
    codon_width: int = 4
    alphabet: tuple[str, ...] = ("0", "1")

    def __post_init__(self) -> None:
        if self.codon_width < 1:
            msg = "DynamicVocabularyState.codon_width must be >= 1."
            raise ConfigurationError(msg)
        if any(len(bits) != self.codon_width for bits in self.next_available_bits):
            msg = "DynamicVocabularyState.next_available_bits width mismatch."
            raise ConfigurationError(msg)
        if not self.alphabet or any(len(symbol) != 1 for symbol in self.alphabet):
            msg = "DynamicVocabularyState.alphabet must contain one-character symbols."
            raise ConfigurationError(msg)
        for codon in self.next_available_bits:
            if any(symbol not in self.alphabet for symbol in codon):
                msg = (
                    "DynamicVocabularyState.next_available_bits contains a symbol outside alphabet."
                )
                raise ConfigurationError(msg)

    @classmethod
    def for_config(
        cls, base_table_version: str, config: DynamicVocabularyConfig
    ) -> DynamicVocabularyState:
        """Create state with next_available_bits matching ``config.extended_codon_width``."""

        spec = config.genome_spec or GenomeSpec(
            codon_width=config.extended_codon_width,
            alphabet=("0", "1"),
            name=f"binary{config.extended_codon_width}",
        )
        return cls(
            base_table_version=base_table_version,
            next_available_bits=_codon_codes(spec),
            codon_width=spec.codon_width,
            alphabet=spec.alphabet,
        )

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "base_table_version": self.base_table_version,
            "proposals": [item.to_dict() for item in self.proposals],
            "accepted_proposals": [item.to_dict() for item in self.accepted_proposals],
            "rejected_proposals": [item.to_dict() for item in self.rejected_proposals],
            "next_available_bits": list(self.next_available_bits),
            "codon_width": self.codon_width,
            "alphabet": list(self.alphabet),
            "digest": self.digest(),
        }

    @classmethod
    def from_dict(
        cls, data: Mapping[str, JsonValue], *, validate_digest: bool = False
    ) -> DynamicVocabularyState:
        width = _int(data, "codon_width", 4)
        alphabet_raw = data.get("alphabet", ["0", "1"])
        if not isinstance(alphabet_raw, list) or not all(
            isinstance(item, str) for item in alphabet_raw
        ):
            msg = "DynamicVocabularyState.alphabet must be a list of strings."
            raise ConfigurationError(msg)
        alphabet = tuple(str(item) for item in alphabet_raw)
        state = cls(
            base_table_version=_str(data, "base_table_version"),
            proposals=_proposal_tuple(data, "proposals"),
            accepted_proposals=_proposal_tuple(data, "accepted_proposals"),
            rejected_proposals=_proposal_tuple(data, "rejected_proposals"),
            next_available_bits=_str_tuple(data, "next_available_bits")
            or _codon_codes(GenomeSpec(codon_width=width, alphabet=alphabet, name="dynamic")),
            codon_width=width,
            alphabet=alphabet,
        )
        expected = data.get("digest")
        if validate_digest and expected is not None and expected != state.digest():
            msg = "DynamicVocabularyState digest validation failed."
            raise ConfigurationError(msg)
        return state

    def digest(self) -> str:
        payload = {
            "base_table_version": self.base_table_version,
            "proposals": [item.to_dict() for item in self.proposals],
            "accepted_proposals": [item.to_dict() for item in self.accepted_proposals],
            "rejected_proposals": [item.to_dict() for item in self.rejected_proposals],
            "next_available_bits": list(self.next_available_bits),
            "codon_width": self.codon_width,
            "alphabet": list(self.alphabet),
        }
        encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()


@dataclass(frozen=True, slots=True)
class ADFDetectionResult:
    """Audit result for an ATP_learning-gated vocabulary proposal pass."""

    attempted: bool
    succeeded: bool
    blocked_reason: str | None
    patterns_found: int
    proposals_created: int
    proposals_accepted: int
    consumed_learning_atp: float
    learning_ledger_entry_id: int | None
    vocabulary_digest_before: str
    vocabulary_digest_after: str
    trace_refs_used: tuple[str, ...]
    vocabulary_state: DynamicVocabularyState
    proposals_rejected: int = 0
    rejection_reasons: tuple[str, ...] = ()
    accepted_proposal_ids: tuple[str, ...] = ()
    rejected_proposal_ids: tuple[str, ...] = ()
    proposed_proposal_ids: tuple[str, ...] = ()
    truncated: bool = False

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "attempted": self.attempted,
            "succeeded": self.succeeded,
            "blocked_reason": self.blocked_reason,
            "patterns_found": self.patterns_found,
            "proposals_created": self.proposals_created,
            "proposals_accepted": self.proposals_accepted,
            "proposals_rejected": self.proposals_rejected,
            "rejection_reasons": list(self.rejection_reasons),
            "accepted_proposal_ids": list(self.accepted_proposal_ids),
            "rejected_proposal_ids": list(self.rejected_proposal_ids),
            "proposed_proposal_ids": list(self.proposed_proposal_ids),
            "truncated": self.truncated,
            "consumed_learning_atp": self.consumed_learning_atp,
            "learning_ledger_entry_id": self.learning_ledger_entry_id,
            "vocabulary_digest_before": self.vocabulary_digest_before,
            "vocabulary_digest_after": self.vocabulary_digest_after,
            "trace_refs_used": list(self.trace_refs_used),
            "vocabulary_state": self.vocabulary_state.to_dict(),
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, JsonValue]) -> ADFDetectionResult:
        state_raw = data.get("vocabulary_state")
        if not isinstance(state_raw, Mapping):
            msg = "ADFDetectionResult requires vocabulary_state."
            raise ConfigurationError(msg)
        ledger = data.get("learning_ledger_entry_id")
        blocked = data.get("blocked_reason")
        if ledger is not None and (isinstance(ledger, bool) or not isinstance(ledger, int)):
            msg = "learning_ledger_entry_id must be an integer or null."
            raise ConfigurationError(msg)
        if blocked is not None and not isinstance(blocked, str):
            msg = "blocked_reason must be a string or null."
            raise ConfigurationError(msg)
        return cls(
            attempted=_bool(data, "attempted", False),
            succeeded=_bool(data, "succeeded", False),
            blocked_reason=blocked,
            patterns_found=_int(data, "patterns_found", 0),
            proposals_created=_int(data, "proposals_created", 0),
            proposals_accepted=_int(data, "proposals_accepted", 0),
            consumed_learning_atp=_float(data, "consumed_learning_atp", 0.0),
            learning_ledger_entry_id=ledger,
            vocabulary_digest_before=_str(data, "vocabulary_digest_before"),
            vocabulary_digest_after=_str(data, "vocabulary_digest_after"),
            trace_refs_used=_str_tuple(data, "trace_refs_used"),
            vocabulary_state=DynamicVocabularyState.from_dict(state_raw),
            proposals_rejected=_int(data, "proposals_rejected", 0),
            rejection_reasons=_str_tuple(data, "rejection_reasons"),
            accepted_proposal_ids=_str_tuple(data, "accepted_proposal_ids"),
            rejected_proposal_ids=_str_tuple(data, "rejected_proposal_ids"),
            proposed_proposal_ids=_str_tuple(data, "proposed_proposal_ids"),
            truncated=_bool(data, "truncated", False),
        )


@dataclass(frozen=True, slots=True)
class ADFMacro:
    """Safe macro expansion metadata; no dynamic Python execution."""

    macro_id: str
    action_name: str
    expanded_actions: tuple[str, ...]
    expanded_codons: tuple[str, ...]
    cost: float
    source_proposal_id: str

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "macro_id": self.macro_id,
            "action_name": self.action_name,
            "expanded_actions": list(self.expanded_actions),
            "expanded_codons": list(self.expanded_codons),
            "cost": self.cost,
            "source_proposal_id": self.source_proposal_id,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, JsonValue]) -> ADFMacro:
        return cls(
            macro_id=_str(data, "macro_id"),
            action_name=_str(data, "action_name"),
            expanded_actions=_str_tuple(data, "expanded_actions"),
            expanded_codons=_str_tuple(data, "expanded_codons"),
            cost=_float(data, "cost", 0.0),
            source_proposal_id=_str(data, "source_proposal_id"),
        )

    def digest(self) -> str:
        return _digest(self.to_dict())


@dataclass(frozen=True, slots=True)
class ADFExpansionResult:
    """Result of resolving an ADF macro to traceable primitive actions."""

    expanded: bool
    macro_id: str | None
    expanded_actions: tuple[str, ...]
    expanded_codons: tuple[str, ...]
    blocked_reason: str | None

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "expanded": self.expanded,
            "macro_id": self.macro_id,
            "expanded_actions": list(self.expanded_actions),
            "expanded_codons": list(self.expanded_codons),
            "blocked_reason": self.blocked_reason,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, JsonValue]) -> ADFExpansionResult:
        return cls(
            expanded=_bool(data, "expanded", False),
            macro_id=_optional_str(data, "macro_id"),
            expanded_actions=_str_tuple(data, "expanded_actions"),
            expanded_codons=_str_tuple(data, "expanded_codons"),
            blocked_reason=_optional_str(data, "blocked_reason"),
        )


def detect_adf_patterns(
    traces: Sequence[Trace] | Sequence[Sequence[TraceEvent]],
    config: DynamicVocabularyConfig,
) -> tuple[ADFPattern, ...]:
    """Detect repeated contiguous action/codon patterns deterministically."""

    if not config.enabled:
        return ()
    buckets: dict[tuple[tuple[str, ...], tuple[str, ...]], list[tuple[TraceEvent, ...]]] = (
        defaultdict(list)
    )
    first_refs: dict[tuple[tuple[str, ...], tuple[str, ...]], list[str]] = defaultdict(list)
    occurrence_refs: dict[tuple[tuple[str, ...], tuple[str, ...]], list[str]] = defaultdict(list)
    organism_buckets: dict[tuple[tuple[str, ...], tuple[str, ...]], set[str]] = defaultdict(set)
    for events in _event_sequences(traces):
        if not events:
            continue
        for length in range(config.min_pattern_length, config.max_pattern_length + 1):
            if len(events) < length:
                continue
            for start in range(0, len(events) - length + 1):
                window = events[start : start + length]
                if not _window_allowed(window, config):
                    continue
                tokens = tuple(event.action for event in window)
                codons = tuple(event.codon for event in window)
                key = (tokens, codons)
                buckets[key].append(window)
                first_refs[key].append(_event_digest(window[0]))
                occurrence_refs[key].append(_window_digest(window))
                organism_buckets[key].update(event.agent_id for event in window)
    patterns: list[ADFPattern] = []
    for (tokens, codons), windows in buckets.items():
        support_count = len(windows)
        organisms = tuple(sorted(organism_buckets[(tokens, codons)]))
        if support_count < config.min_support_count:
            continue
        if config.require_multi_organism_support and len(organisms) < 2:
            continue
        events_for_pattern = [event for window in windows for event in window]
        first_seen = min(event.step for event in events_for_pattern)
        last_seen = max(event.step for event in events_for_pattern)
        pattern_id = _stable_id("adf_pattern", list(tokens), list(codons))
        refs = tuple(occurrence_refs[(tokens, codons)])
        patterns.append(
            ADFPattern(
                pattern_id=pattern_id,
                tokens=tokens,
                codons=codons,
                length=len(tokens),
                support_count=support_count,
                first_seen_tick=first_seen,
                last_seen_tick=last_seen,
                organism_ids=organisms,
                trace_refs=refs,
                occurrence_refs=refs,
                occurrence_count=support_count,
                first_event_refs=tuple(sorted(set(first_refs[(tokens, codons)]))),
                metadata={
                    "includes_blocked_or_failed": any(
                        event.status != "executed" for event in events_for_pattern
                    )
                },
            )
        )
    return tuple(
        sorted(patterns, key=lambda item: (-item.support_count, -item.length, item.pattern_id))
    )


def score_adf_pattern(
    pattern: ADFPattern,
    *,
    fitness_before: float | None = None,
    fitness_after: float | None = None,
    atp_pressure: float = 0.0,
    config: DynamicVocabularyConfig,
) -> ADFCompressionScore:
    """Score an ADF pattern using explicit support/compression thresholds."""

    raw_token_count = pattern.support_count * pattern.length
    compressed_token_count = pattern.support_count
    compression_gain = float(pattern.support_count * (pattern.length - 1))
    fitness_delta = None
    if fitness_before is not None and fitness_after is not None:
        fitness_delta = round(float(fitness_after - fitness_before), 10)
    atp_pressure_score = max(0.0, min(1.0, float(atp_pressure)))
    reasons: list[str] = []
    if pattern.support_count < config.min_support_count:
        reasons.append("support_below_threshold")
    if pattern.support_count < config.min_reuse_count:
        reasons.append("reuse_below_threshold")
    if compression_gain < config.min_compression_gain:
        reasons.append("compression_gain_below_threshold")
    if config.require_fitness_non_decrease and fitness_delta is not None and fitness_delta < 0:
        reasons.append("negative_fitness_delta")
    accepted = not reasons
    if accepted:
        reasons.append("thresholds_passed")
    return ADFCompressionScore(
        pattern_id=pattern.pattern_id,
        raw_token_count=raw_token_count,
        compressed_token_count=compressed_token_count,
        compression_gain=round(compression_gain, 10),
        reuse_count=pattern.support_count,
        fitness_delta=fitness_delta,
        atp_pressure_score=round(atp_pressure_score, 10),
        accepted=accepted,
        reasons=tuple(reasons),
    )


def propose_dynamic_vocabulary(
    traces: Sequence[Trace] | Sequence[Sequence[TraceEvent]],
    state: DynamicVocabularyState,
    atp_state: GenesisATPState,
    config: DynamicVocabularyConfig,
    *,
    tick: int,
    organism_id: str,
) -> ADFDetectionResult:
    """Create ATP_learning-gated ADF proposals without mutating codon tables."""

    before_digest = state.digest()
    if state.codon_width != config.extended_codon_width:
        msg = "DynamicVocabularyState codon_width does not match config.extended_codon_width."
        raise ConfigurationError(msg)
    expected_alphabet = (
        config.genome_spec.alphabet if config.genome_spec is not None else ("0", "1")
    )
    if state.alphabet != expected_alphabet:
        msg = "DynamicVocabularyState alphabet does not match DynamicVocabularyConfig genome_spec."
        raise ConfigurationError(msg)
    if not config.enabled:
        return _adf_blocked("dynamic_vocabulary_disabled", state, before_digest)
    patterns = detect_adf_patterns(traces, config)
    if not patterns:
        return ADFDetectionResult(
            attempted=True,
            succeeded=False,
            blocked_reason="no_patterns",
            patterns_found=0,
            proposals_created=0,
            proposals_accepted=0,
            consumed_learning_atp=0.0,
            learning_ledger_entry_id=None,
            vocabulary_digest_before=before_digest,
            vocabulary_digest_after=before_digest,
            trace_refs_used=(),
            vocabulary_state=state,
        )
    available_bits = list(state.next_available_bits)
    proposals: list[ADFProposal] = []
    accepted: list[ADFProposal] = []
    rejected: list[ADFProposal] = []
    rejected_reasons: list[str] = []
    base_table = _base_table_for_version(state.base_table_version)
    for pattern in patterns[: config.max_new_codons]:
        if not available_bits:
            break
        bits = available_bits.pop(0)
        score = score_adf_pattern(pattern, config=config)
        cost, cost_reason = _proposal_cost(pattern, base_table, config)
        status = (
            "accepted"
            if config.allow_auto_accept and score.accepted and cost_reason is None
            else "proposed"
        )
        reasons = list(score.reasons)
        metadata: dict[str, JsonValue] = {"cost_policy": config.cost_policy.value}
        if cost_reason is not None:
            status = "rejected"
            reasons.append(cost_reason)
            metadata["blocked_reason"] = cost_reason
        elif not score.accepted:
            status = "rejected"
        proposal_score = replace(
            score, accepted=status in {"accepted", "proposed"}, reasons=tuple(reasons)
        )
        proposal = ADFProposal(
            proposal_id=_stable_id("adf_proposal", pattern.pattern_id, bits),
            pattern=pattern,
            score=proposal_score,
            proposed_bits=bits,
            proposed_action=f"ADF_{bits}",
            proposed_cost=cost,
            status=status,
            metadata=metadata,
        )
        proposals.append(proposal)
        if status == "accepted":
            accepted.append(proposal)
        elif status == "rejected":
            rejected.append(proposal)
            rejected_reasons.extend(reason for reason in reasons if reason != "thresholds_passed")
    if not proposals:
        return _adf_blocked("no_available_extended_codons", state, before_digest)
    learning_cost = _proposal_learning_cost(config, len(patterns), len(proposals))
    if not atp_state.can_learn(learning_cost):
        return ADFDetectionResult(
            attempted=True,
            succeeded=False,
            blocked_reason="insufficient_learning_atp",
            patterns_found=len(patterns),
            proposals_created=0,
            proposals_accepted=0,
            consumed_learning_atp=0.0,
            learning_ledger_entry_id=None,
            vocabulary_digest_before=before_digest,
            vocabulary_digest_after=before_digest,
            trace_refs_used=tuple(
                sorted({ref for pattern in patterns for ref in pattern.occurrence_refs})
            ),
            vocabulary_state=state,
            proposals_rejected=0,
            rejection_reasons=(),
            truncated=False,
        )
    ledger_id = atp_state.debit_learning(
        learning_cost,
        tick=tick,
        organism_id=organism_id,
        reason=f"dynamic_vocabulary_proposal:{config.proposal_cost_mode.value}",
        event_ref=before_digest,
    )
    if ledger_id is None and learning_cost > 0:
        return _adf_blocked("insufficient_learning_atp", state, before_digest)
    new_state = replace(
        state,
        proposals=state.proposals + tuple(proposals),
        accepted_proposals=state.accepted_proposals + tuple(accepted),
        rejected_proposals=state.rejected_proposals + tuple(rejected),
        next_available_bits=tuple(available_bits),
    )
    return ADFDetectionResult(
        attempted=True,
        succeeded=True,
        blocked_reason=None,
        patterns_found=len(patterns),
        proposals_created=len(proposals),
        proposals_accepted=len(accepted),
        proposals_rejected=len(rejected),
        rejection_reasons=tuple(sorted(set(rejected_reasons))),
        accepted_proposal_ids=tuple(proposal.proposal_id for proposal in accepted),
        rejected_proposal_ids=tuple(proposal.proposal_id for proposal in rejected),
        proposed_proposal_ids=tuple(proposal.proposal_id for proposal in proposals),
        consumed_learning_atp=learning_cost,
        learning_ledger_entry_id=ledger_id,
        vocabulary_digest_before=before_digest,
        vocabulary_digest_after=new_state.digest(),
        trace_refs_used=tuple(
            sorted({ref for proposal in proposals for ref in proposal.pattern.occurrence_refs})
        ),
        vocabulary_state=new_state,
        truncated=len(patterns) > len(proposals),
    )


def extend_codon_table_with_adfs(
    base_table: CodonTable,
    proposals: Sequence[ADFProposal],
    *,
    codon_width: int = 4,
) -> CodonTable:
    """Return an additive codon table containing accepted ADF proposals only."""

    table = base_table
    existing = {codon.bits for codon in base_table.actions()}
    for proposal in proposals:
        if proposal.status != "accepted":
            continue
        if len(proposal.proposed_bits) != codon_width:
            msg = "Accepted ADF proposal width does not match codon_width."
            raise ConfigurationError(msg)
        if proposal.proposed_bits in existing:
            msg = f"ADF codon collision for {proposal.proposed_bits!r}."
            raise ConfigurationError(msg)
        table = table.extend(
            Codon(
                proposal.proposed_bits,
                proposal.proposed_action,
                proposal.proposed_cost,
                "Traceable ADF macro proposal.",
            )
        )
        existing.add(proposal.proposed_bits)
    return table


def macro_from_proposal(proposal: ADFProposal) -> ADFMacro:
    """Create a safe macro representation from an accepted or proposed ADF."""

    return ADFMacro(
        macro_id=_stable_id("adf_macro", proposal.proposal_id),
        action_name=proposal.proposed_action,
        expanded_actions=proposal.pattern.tokens,
        expanded_codons=proposal.pattern.codons,
        cost=proposal.proposed_cost,
        source_proposal_id=proposal.proposal_id,
    )


def expand_adf_macro(action_name: str, macros: Sequence[ADFMacro]) -> ADFExpansionResult:
    """Resolve an ADF action name into deterministic primitive expansion metadata."""

    for macro in macros:
        if macro.action_name == action_name:
            return ADFExpansionResult(
                expanded=True,
                macro_id=macro.macro_id,
                expanded_actions=macro.expanded_actions,
                expanded_codons=macro.expanded_codons,
                blocked_reason=None,
            )
    return ADFExpansionResult(
        expanded=False,
        macro_id=None,
        expanded_actions=(),
        expanded_codons=(),
        blocked_reason="unknown_adf_macro",
    )


def _event_sequences(
    traces: Sequence[Trace] | Sequence[Sequence[TraceEvent]],
) -> tuple[tuple[TraceEvent, ...], ...]:
    sequences: list[tuple[TraceEvent, ...]] = []
    for item in traces:
        if isinstance(item, Trace):
            sequences.append(tuple(item.events))
        else:
            sequences.append(tuple(item))
    return tuple(sequences)


def _window_allowed(window: tuple[TraceEvent, ...], config: DynamicVocabularyConfig) -> bool:
    statuses = {event.status for event in window}
    if "failed" in statuses and not config.include_failed_events:
        return False
    if "blocked" in statuses and not config.include_blocked_events:
        return False
    return not (statuses <= {"blocked", "failed"} and not config.include_blocked_only_patterns)


def _proposal_tuple(data: Mapping[str, JsonValue], key: str) -> tuple[ADFProposal, ...]:
    raw = data.get(key, [])
    if not isinstance(raw, list):
        msg = f"{key} must be a list."
        raise ConfigurationError(msg)
    return tuple(ADFProposal.from_dict(item) for item in raw if isinstance(item, Mapping))


def _adf_blocked(
    reason: str,
    state: DynamicVocabularyState,
    before_digest: str,
) -> ADFDetectionResult:
    return ADFDetectionResult(
        attempted=True,
        succeeded=False,
        blocked_reason=reason,
        patterns_found=0,
        proposals_created=0,
        proposals_accepted=0,
        consumed_learning_atp=0.0,
        learning_ledger_entry_id=None,
        vocabulary_digest_before=before_digest,
        vocabulary_digest_after=before_digest,
        trace_refs_used=(),
        vocabulary_state=state,
    )


def _binary_codes(width: int) -> tuple[str, ...]:
    return tuple(format(value, f"0{width}b") for value in range(2**width))


def _codon_codes(spec: GenomeSpec) -> tuple[str, ...]:
    return spec.all_codons()


def _event_digest(event: TraceEvent) -> str:
    return _digest(event.to_dict())


def _window_digest(window: tuple[TraceEvent, ...]) -> str:
    payload: dict[str, JsonValue] = {
        "events": [event.to_dict() for event in window],
        "actions": [event.action for event in window],
        "codons": [event.codon for event in window],
        "statuses": [event.status for event in window],
        "organism_id": window[0].agent_id if window else "",
        "start_tick": window[0].step if window else 0,
        "end_tick": window[-1].step if window else 0,
    }
    return _digest(payload)


def _base_table_for_version(version: str) -> CodonTable:
    if version in {"genesis_v0", "GenesisCodonTable.default_v0"}:
        return CodonTable.genesis_v0()
    if version in {"default_minimal", "core_minimal"}:
        return CodonTable.default_minimal()
    return CodonTable.genesis_v0()


def _proposal_cost(
    pattern: ADFPattern, base_table: CodonTable, config: DynamicVocabularyConfig
) -> tuple[float, str | None]:
    costs: list[float] = []
    for bits in pattern.codons:
        try:
            costs.append(base_table.decode(bits).cost)
        except KeyError:
            return (0.0, "unknown_primitive_cost")
    if not costs:
        return (0.0, "unknown_primitive_cost")
    if config.cost_policy is ADFCostPolicy.SUM_PRIMITIVE_COSTS:
        cost = sum(costs)
    elif config.cost_policy is ADFCostPolicy.DISCOUNTED_SUM:
        cost = sum(costs) * config.cost_discount
    elif config.cost_policy is ADFCostPolicy.MAX_PRIMITIVE_COST:
        cost = max(costs)
    elif config.cost_policy is ADFCostPolicy.EXPLICIT:
        cost = config.min_adf_cost
    else:
        return (0.0, "unsupported_cost_policy")
    cost = max(config.min_adf_cost, cost)
    if config.max_adf_cost is not None:
        cost = min(cost, config.max_adf_cost)
    return (round(cost, 10), None)


def _proposal_learning_cost(
    config: DynamicVocabularyConfig, pattern_count: int, proposal_count: int
) -> float:
    if config.proposal_cost_mode is ADFProposalCostMode.PER_RUN:
        multiplier = 1 if proposal_count > 0 else 0
    elif config.proposal_cost_mode is ADFProposalCostMode.PER_PATTERN:
        multiplier = pattern_count
    else:
        multiplier = proposal_count
    return round(config.proposal_cost_learning_atp * multiplier, 10)


def _stable_id(prefix: str, *parts: object) -> str:
    encoded = json.dumps(parts, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return f"{prefix}_{hashlib.sha256(encoded).hexdigest()[:16]}"


def _digest(payload: Mapping[str, JsonValue]) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _str(data: Mapping[str, JsonValue], key: str, default: str | None = None) -> str:
    value = data.get(key, default)
    if not isinstance(value, str):
        msg = f"{key} must be a string."
        raise ConfigurationError(msg)
    return value


def _optional_str(data: Mapping[str, JsonValue], key: str) -> str | None:
    value = data.get(key)
    if value is None:
        return None
    if not isinstance(value, str):
        msg = f"{key} must be a string or null."
        raise ConfigurationError(msg)
    return value


def _bool(data: Mapping[str, JsonValue], key: str, default: bool) -> bool:
    value = data.get(key, default)
    if not isinstance(value, bool):
        msg = f"{key} must be a boolean."
        raise ConfigurationError(msg)
    return value


def _int(data: Mapping[str, JsonValue], key: str, default: int) -> int:
    value = data.get(key, default)
    if isinstance(value, bool) or not isinstance(value, int):
        msg = f"{key} must be an integer."
        raise ConfigurationError(msg)
    return value


def _float(data: Mapping[str, JsonValue], key: str, default: float) -> float:
    value = data.get(key, default)
    if isinstance(value, bool) or not isinstance(value, int | float):
        msg = f"{key} must be numeric."
        raise ConfigurationError(msg)
    return float(value)


def _str_tuple(data: Mapping[str, JsonValue], key: str) -> tuple[str, ...]:
    raw = data.get(key, [])
    if not isinstance(raw, list) or not all(isinstance(item, str) for item in raw):
        msg = f"{key} must be a list of strings."
        raise ConfigurationError(msg)
    return tuple(str(item) for item in raw)
