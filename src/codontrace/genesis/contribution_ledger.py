"""Contribution ledger and bounded attribution estimates for GENESIS runs."""

from __future__ import annotations

import hashlib
import json
import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import cast

from codontrace._types import JsonValue
from codontrace.errors import ConfigurationError
from codontrace.genesis.ribosome import CodonExecutionRecord


def _digest(payload: Mapping[str, JsonValue]) -> str:
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    ).hexdigest()


def _require_finite(value: float, name: str) -> float:
    value = float(value)
    if not math.isfinite(value):
        raise ConfigurationError(f"{name} must be finite.")
    return value


@dataclass(frozen=True, slots=True)
class CodonContributionRecord:
    execution_ref: str
    organism_id: str
    generation: int
    genome_pos: int
    codon: str
    action: str
    macro_id: str | None
    local_reward_delta: float
    novelty_delta: float
    reproduction_progress_delta: float
    causal_accuracy_delta: float | None
    descendant_success_discounted: float
    method: str
    confidence: float
    caveat: str = "attribution_estimate_not_causal_proof"

    def __post_init__(self) -> None:
        for attr in (
            "local_reward_delta",
            "novelty_delta",
            "reproduction_progress_delta",
            "descendant_success_discounted",
            "confidence",
        ):
            object.__setattr__(self, attr, round(_require_finite(getattr(self, attr), attr), 10))
        if self.causal_accuracy_delta is not None:
            object.__setattr__(self, "causal_accuracy_delta", round(_require_finite(self.causal_accuracy_delta, "causal_accuracy_delta"), 10))
        if self.generation < 0 or self.genome_pos < 0:
            raise ConfigurationError("generation/genome_pos must be non-negative.")

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "execution_ref": self.execution_ref,
            "organism_id": self.organism_id,
            "generation": self.generation,
            "genome_pos": self.genome_pos,
            "codon": self.codon,
            "action": self.action,
            "macro_id": self.macro_id,
            "local_reward_delta": self.local_reward_delta,
            "novelty_delta": self.novelty_delta,
            "reproduction_progress_delta": self.reproduction_progress_delta,
            "causal_accuracy_delta": self.causal_accuracy_delta,
            "descendant_success_discounted": self.descendant_success_discounted,
            "method": self.method,
            "confidence": self.confidence,
            "caveat": self.caveat,
        }

    @property
    def total_estimate(self) -> float:
        return round(
            self.local_reward_delta
            + self.novelty_delta
            + self.reproduction_progress_delta
            + (self.causal_accuracy_delta or 0.0)
            + self.descendant_success_discounted,
            10,
        )


@dataclass(frozen=True, slots=True)
class ContributionLedger:
    organism_id: str
    generation: int
    records: tuple[CodonContributionRecord, ...]
    aggregate_by_codon: tuple[tuple[str, float], ...]
    aggregate_by_macro: tuple[tuple[str, float], ...]
    aggregate_by_mutation: tuple[tuple[str, float], ...]
    confidence_mean: float
    digest: str

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "organism_id": self.organism_id,
            "generation": self.generation,
            "records": [record.to_dict() for record in self.records],
            "aggregate_by_codon": [[k, v] for k, v in self.aggregate_by_codon],
            "aggregate_by_macro": [[k, v] for k, v in self.aggregate_by_macro],
            "aggregate_by_mutation": [[k, v] for k, v in self.aggregate_by_mutation],
            "confidence_mean": self.confidence_mean,
            "digest": self.digest,
        }


def build_contribution_ledger(
    organism_id: str,
    generation: int,
    records: Sequence[CodonContributionRecord],
    *,
    mutation_scores: Mapping[str, float] | None = None,
) -> ContributionLedger:
    ordered = tuple(sorted(records, key=lambda item: (item.genome_pos, item.execution_ref)))
    codon_scores: dict[str, float] = {}
    macro_scores: dict[str, float] = {}
    for record in ordered:
        codon_scores[record.codon] = codon_scores.get(record.codon, 0.0) + record.total_estimate
        if record.macro_id is not None:
            macro_scores[record.macro_id] = (
                macro_scores.get(record.macro_id, 0.0) + record.total_estimate
            )
    confidence = round(sum(r.confidence for r in ordered) / len(ordered), 10) if ordered else 0.0
    aggregate_by_codon = tuple((k, round(v, 10)) for k, v in sorted(codon_scores.items()))
    aggregate_by_macro = tuple((k, round(v, 10)) for k, v in sorted(macro_scores.items()))
    aggregate_by_mutation = tuple(
        (k, round(float(v), 10)) for k, v in sorted((mutation_scores or {}).items())
    )
    payload: dict[str, JsonValue] = {
        "organism_id": organism_id,
        "generation": generation,
        "records": [r.to_dict() for r in ordered],
        "aggregate_by_codon": cast(JsonValue, [[k, v] for k, v in aggregate_by_codon]),
        "aggregate_by_macro": cast(JsonValue, [[k, v] for k, v in aggregate_by_macro]),
        "aggregate_by_mutation": cast(JsonValue, [[k, v] for k, v in aggregate_by_mutation]),
        "confidence_mean": confidence,
    }
    return ContributionLedger(
        organism_id=organism_id,
        generation=generation,
        records=ordered,
        aggregate_by_codon=aggregate_by_codon,
        aggregate_by_macro=aggregate_by_macro,
        aggregate_by_mutation=aggregate_by_mutation,
        confidence_mean=confidence,
        digest=_digest(payload),
    )


def contribution_ledger_from_dict(data: Mapping[str, JsonValue]) -> ContributionLedger:
    records_raw = data.get("records", [])
    if not isinstance(records_raw, list):
        raise ConfigurationError("ContributionLedger.records must be a list.")
    records = tuple(_record_from_dict(item) for item in records_raw if isinstance(item, Mapping))
    ledger = build_contribution_ledger(
        _str(data, "organism_id"), _int(data, "generation", 0), records
    )
    if ledger.digest != data.get("digest"):
        raise ConfigurationError("ContributionLedger digest mismatch.")
    return ledger


def contribution_from_execution_record(
    execution: CodonExecutionRecord,
    *,
    generation: int = 0,
    novelty_delta: float = 0.0,
    reproduction_progress_delta: float = 0.0,
    causal_accuracy_delta: float | None = None,
    descendant_success_discounted: float = 0.0,
    method: str = "local_delta",
    confidence: float = 0.5,
) -> CodonContributionRecord:
    reward_delta = round(execution.atp_after - execution.atp_before, 10)
    if execution.action_status not in {"executed", "ok", "success"}:
        reward_delta -= 1.0
    return CodonContributionRecord(
        execution_ref=execution.trace_event_ref,
        organism_id=execution.organism_id,
        generation=generation,
        genome_pos=execution.source.genome_pos,
        codon=execution.source.codon,
        action=execution.resolved_action,
        macro_id=execution.source.macro_id,
        local_reward_delta=reward_delta,
        novelty_delta=novelty_delta,
        reproduction_progress_delta=reproduction_progress_delta,
        causal_accuracy_delta=causal_accuracy_delta,
        descendant_success_discounted=descendant_success_discounted,
        method=method,
        confidence=confidence,
    )


def eligibility_trace_credit(
    records: Sequence[CodonContributionRecord], future_reward: float, gamma: float = 0.9
) -> tuple[CodonContributionRecord, ...]:
    result = []
    n = len(records)
    for index, record in enumerate(records):
        discounted = round(float(future_reward) * (gamma ** (n - index - 1)), 10)
        result.append(
            CodonContributionRecord(
                execution_ref=record.execution_ref,
                organism_id=record.organism_id,
                generation=record.generation,
                genome_pos=record.genome_pos,
                codon=record.codon,
                action=record.action,
                macro_id=record.macro_id,
                local_reward_delta=record.local_reward_delta,
                novelty_delta=record.novelty_delta,
                reproduction_progress_delta=record.reproduction_progress_delta,
                causal_accuracy_delta=record.causal_accuracy_delta,
                descendant_success_discounted=record.descendant_success_discounted + discounted,
                method=record.method,
                confidence=record.confidence,
                caveat=record.caveat,
            )
        )
    return tuple(result)


@dataclass(frozen=True, slots=True)
class MicroAblationAttributionRecord:
    """Digestable Phase 2 attribution record for paired micro-ablation.

    The record is evidence for attribution support, not causal proof by itself;
    causal levels still require intervention/ablation protocols in ClaimGate.
    """

    target_ref: str
    target_type: str
    original_metric: float
    ablated_metric: float
    micro_ablation_delta: float
    paired_seed_policy: str
    contribution_ledger_digest: str | None
    status: str
    confidence_status: str
    schema_version: str = "micro_ablation_attribution_v1"
    digest: str = ""

    def __post_init__(self) -> None:
        if self.status not in {"measured", "not_run", "provisional"}:
            raise ConfigurationError("Unsupported MicroAblationAttributionRecord.status.")
        if self.confidence_status not in {"ablation_supported", "estimate_only", "not_run"}:
            raise ConfigurationError("Unsupported MicroAblationAttributionRecord.confidence_status.")
        for attr in ("original_metric", "ablated_metric", "micro_ablation_delta"):
            object.__setattr__(self, attr, round(_require_finite(getattr(self, attr), attr), 10))
        computed = _digest(self._payload())
        if self.digest and self.digest != computed:
            raise ConfigurationError("MicroAblationAttributionRecord digest mismatch.")
        object.__setattr__(self, "digest", computed)

    def _payload(self) -> dict[str, JsonValue]:
        return {
            "schema_version": self.schema_version,
            "target_ref": self.target_ref,
            "target_type": self.target_type,
            "original_metric": self.original_metric,
            "ablated_metric": self.ablated_metric,
            "micro_ablation_delta": self.micro_ablation_delta,
            "paired_seed_policy": self.paired_seed_policy,
            "contribution_ledger_digest": self.contribution_ledger_digest,
            "status": self.status,
            "confidence_status": self.confidence_status,
        }

    def to_dict(self) -> dict[str, JsonValue]:
        return {**self._payload(), "digest": self.digest}


def build_micro_ablation_attribution_record(
    target_ref: str,
    target_type: str,
    *,
    original_metric: float | None = None,
    ablated_metric: float | None = None,
    paired_seed_policy: str = "single_seed_pair",
    contribution_ledger_digest: str | None = None,
) -> MicroAblationAttributionRecord:
    if original_metric is None or ablated_metric is None:
        return MicroAblationAttributionRecord(
            target_ref=target_ref,
            target_type=target_type,
            original_metric=0.0,
            ablated_metric=0.0,
            micro_ablation_delta=0.0,
            paired_seed_policy=paired_seed_policy,
            contribution_ledger_digest=contribution_ledger_digest,
            status="not_run",
            confidence_status="not_run",
        )
    delta = paired_micro_ablation_score(original_metric, ablated_metric)
    return MicroAblationAttributionRecord(
        target_ref=target_ref,
        target_type=target_type,
        original_metric=round(float(original_metric), 10),
        ablated_metric=round(float(ablated_metric), 10),
        micro_ablation_delta=delta,
        paired_seed_policy=paired_seed_policy,
        contribution_ledger_digest=contribution_ledger_digest,
        status="measured",
        confidence_status="ablation_supported" if contribution_ledger_digest and delta != 0 else "estimate_only",
    )


def paired_micro_ablation_score(original_metric: float, ablated_metric: float) -> float:
    return round(_require_finite(original_metric, "original_metric") - _require_finite(ablated_metric, "ablated_metric"), 10)


def _record_from_dict(data: Mapping[str, JsonValue]) -> CodonContributionRecord:
    return CodonContributionRecord(
        execution_ref=_str(data, "execution_ref"),
        organism_id=_str(data, "organism_id"),
        generation=_int(data, "generation", 0),
        genome_pos=_int(data, "genome_pos", 0),
        codon=_str(data, "codon"),
        action=_str(data, "action"),
        macro_id=None if data.get("macro_id") is None else _str(data, "macro_id"),
        local_reward_delta=_float(data, "local_reward_delta", 0.0),
        novelty_delta=_float(data, "novelty_delta", 0.0),
        reproduction_progress_delta=_float(data, "reproduction_progress_delta", 0.0),
        causal_accuracy_delta=None
        if data.get("causal_accuracy_delta") is None
        else _float(data, "causal_accuracy_delta", 0.0),
        descendant_success_discounted=_float(data, "descendant_success_discounted", 0.0),
        method=_str(data, "method"),
        confidence=_float(data, "confidence", 0.0),
        caveat=_str(data, "caveat", "attribution_estimate_not_causal_proof"),
    )


def _str(data: Mapping[str, JsonValue], key: str, default: str | None = None) -> str:
    value = data.get(key, default)
    if not isinstance(value, str):
        raise ConfigurationError(f"{key} must be a string.")
    return value


def _int(data: Mapping[str, JsonValue], key: str, default: int) -> int:
    value = data.get(key, default)
    if isinstance(value, bool) or not isinstance(value, int):
        raise ConfigurationError(f"{key} must be an integer.")
    return value


def _float(data: Mapping[str, JsonValue], key: str, default: float) -> float:
    value = data.get(key, default)
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise ConfigurationError(f"{key} must be numeric.")
    return _require_finite(value, key)

# ---------------------------------------------------------------------------
# Multi-agent credit attribution ledger (P2)
# ---------------------------------------------------------------------------
from dataclasses import field as _ledger_field
from codontrace.genesis.canonical import canonical_digest as _ledger_canonical_digest, require_finite_float as _ledger_require_finite_float


@dataclass(frozen=True, slots=True)
class MultiAgentContributionRecord:
    organism_id: str
    tick: int
    direct_reward: float = 0.0
    indirect_reward: float = 0.0
    packet_credit: float = 0.0
    guard_credit: float = 0.0
    memory_credit: float = 0.0
    evidence_digest: str | None = None
    schema_version: str = "multi_agent_contribution_record_v1"

    def __post_init__(self) -> None:
        if not self.organism_id:
            raise ConfigurationError("organism_id is required")
        if self.tick < 0:
            raise ConfigurationError("tick must be non-negative")
        for attr in ("direct_reward", "indirect_reward", "packet_credit", "guard_credit", "memory_credit"):
            object.__setattr__(self, attr, round(_ledger_require_finite_float(attr, getattr(self, attr)), 10))

    @property
    def total_credit(self) -> float:
        return round(self.direct_reward + self.indirect_reward + self.packet_credit + self.guard_credit + self.memory_credit, 10)

    def to_dict(self) -> dict[str, JsonValue]:
        return {"schema_version": self.schema_version, "organism_id": self.organism_id, "tick": self.tick, "direct_reward": self.direct_reward, "indirect_reward": self.indirect_reward, "packet_credit": self.packet_credit, "guard_credit": self.guard_credit, "memory_credit": self.memory_credit, "total_credit": self.total_credit, "evidence_digest": self.evidence_digest}

    def digest(self) -> str:
        return _ledger_canonical_digest(self.to_dict(), prefix="multi_agent_contribution")


@dataclass(frozen=True, slots=True)
class MultiAgentContributionLedger:
    records: tuple[MultiAgentContributionRecord, ...]
    track_direct_reward: bool = True
    track_indirect_reward: bool = True
    track_packet_credit: bool = True
    track_guard_credit: bool = True
    track_memory_credit: bool = True
    schema_version: str = "multi_agent_contribution_ledger_v1"
    digest_value: str = ""

    def __post_init__(self) -> None:
        object.__setattr__(self, "records", tuple(sorted(self.records, key=lambda r: (r.tick, r.organism_id, r.digest()))))
        if not self.digest_value:
            object.__setattr__(self, "digest_value", _ledger_canonical_digest(self._payload(), prefix="multi_agent_ledger"))

    @property
    def aggregate_by_agent(self) -> tuple[tuple[str, float], ...]:
        scores: dict[str, float] = {}
        for record in self.records:
            scores[record.organism_id] = scores.get(record.organism_id, 0.0) + record.total_credit
        return tuple(sorted((agent, round(score, 10)) for agent, score in scores.items()))

    def _payload(self) -> dict[str, JsonValue]:
        return {"schema_version": self.schema_version, "records": [record.to_dict() for record in self.records], "track_direct_reward": self.track_direct_reward, "track_indirect_reward": self.track_indirect_reward, "track_packet_credit": self.track_packet_credit, "track_guard_credit": self.track_guard_credit, "track_memory_credit": self.track_memory_credit, "aggregate_by_agent": [[agent, score] for agent, score in self.aggregate_by_agent]}

    def to_dict(self) -> dict[str, JsonValue]:
        return {**self._payload(), "digest": self.digest_value}

    def digest(self) -> str:
        return self.digest_value


MultiAgentCreditLedger = MultiAgentContributionLedger
