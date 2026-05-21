"""Structured rule/config proposal validation for GENESIS workflows.

The rule API accepts data, not code. It never evals, imports, or executes LLM
output. Accepted proposals still require a human approval record before a rule
set can be used by a future run.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from dataclasses import dataclass, field, is_dataclass, replace
from enum import Enum
from types import MappingProxyType
from typing import Any, cast

from codontrace._types import JsonValue
from codontrace.errors import ConfigurationError


class RuleProposalSource(str, Enum):
    HUMAN = "human"
    LLM = "llm"
    TOOL = "tool"
    TEST = "test"


class ApprovalStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


FrozenJson = JsonValue | Mapping[str, "FrozenJson"] | tuple["FrozenJson", ...]
FrozenJsonObject = Mapping[str, FrozenJson]


def _freeze_json_value(value: JsonValue) -> FrozenJson:
    if isinstance(value, dict):
        return MappingProxyType(
            dict(sorted((str(k), _freeze_json_value(v)) for k, v in value.items()))
        )
    if isinstance(value, list):
        return tuple(_freeze_json_value(item) for item in value)
    return value


def _thaw_json_value(value: FrozenJson) -> JsonValue:
    if isinstance(value, Mapping):
        return {str(k): _thaw_json_value(v) for k, v in value.items()}
    if isinstance(value, tuple):
        return [_thaw_json_value(item) for item in value]
    return value


def _freeze_mapping(value: Mapping[str, JsonValue]) -> FrozenJsonObject:
    return MappingProxyType(dict(sorted((str(k), _freeze_json_value(v)) for k, v in value.items())))


def _thaw_mapping(value: Mapping[str, JsonValue] | FrozenJsonObject) -> dict[str, JsonValue]:
    return {str(k): _thaw_json_value(v) for k, v in value.items()}


@dataclass(frozen=True, slots=True)
class RuleSetDiff:
    """Pure-data config/rule diff with deep-immutable nested metadata."""

    add: tuple[Mapping[str, JsonValue] | FrozenJsonObject, ...] = ()
    modify: tuple[Mapping[str, JsonValue] | FrozenJsonObject, ...] = ()
    remove: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "add", tuple(_freeze_mapping(_thaw_mapping(item)) for item in self.add)
        )
        object.__setattr__(
            self,
            "modify",
            tuple(_freeze_mapping(_thaw_mapping(item)) for item in self.modify),
        )
        object.__setattr__(self, "remove", tuple(str(item) for item in self.remove))

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "add": [_thaw_mapping(item) for item in self.add],
            "modify": [_thaw_mapping(item) for item in self.modify],
            "remove": list(self.remove),
        }

    def digest(self) -> str:
        return _digest(self.to_dict())


@dataclass(frozen=True, slots=True)
class RuleProposal:
    proposal_id: str
    source: RuleProposalSource
    diff: RuleSetDiff
    rationale: str = ""
    metadata: Mapping[str, JsonValue] | FrozenJsonObject = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "metadata", _freeze_mapping(_thaw_mapping(self.metadata)))

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "proposal_id": self.proposal_id,
            "source": self.source.value,
            "diff": self.diff.to_dict(),
            "rationale": self.rationale,
            "metadata": _thaw_mapping(self.metadata),
        }

    def digest(self) -> str:
        return _digest(self.to_dict())


@dataclass(frozen=True, slots=True)
class RuleRiskReport:
    severity: str
    issues: tuple[str, ...]

    def to_dict(self) -> dict[str, JsonValue]:
        return {"severity": self.severity, "issues": list(self.issues)}


@dataclass(frozen=True, slots=True)
class RuleValidationResult:
    proposal_digest: str
    passed: bool
    issues: tuple[str, ...]
    risk_report: RuleRiskReport
    requires_human_approval: bool = True

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "proposal_digest": self.proposal_digest,
            "passed": self.passed,
            "issues": list(self.issues),
            "risk_report": self.risk_report.to_dict(),
            "requires_human_approval": self.requires_human_approval,
        }

    def digest(self) -> str:
        return _digest(self.to_dict())


class ConservationCheck:
    """Check resource/element conservation in strict mode."""

    def validate(self, proposal: RuleProposal, *, strict: bool) -> tuple[str, ...]:
        issues: list[str] = []
        for item in proposal.diff.add + proposal.diff.modify:
            conservative = item.get("conservative", True)
            if strict and conservative is False:
                issues.append("non_conservative_rule")
        return tuple(issues)


class LocalityCheck:
    """Check that rules declare local radius."""

    def validate(self, proposal: RuleProposal, *, max_radius: int) -> tuple[str, ...]:
        issues: list[str] = []
        for item in proposal.diff.add + proposal.diff.modify:
            radius = item.get("radius", 1)
            if isinstance(radius, bool) or not isinstance(radius, int) or radius < 0:
                issues.append("invalid_locality_radius")
            elif radius > max_radius:
                issues.append("locality_radius_exceeds_limit")
        return tuple(issues)


class DeterminismCheck:
    """Block nondeterministic proposals without seed/replay control."""

    def validate(self, proposal: RuleProposal) -> tuple[str, ...]:
        issues: list[str] = []
        for item in proposal.diff.add + proposal.diff.modify:
            if item.get("nondeterministic") is True and item.get("seed_controlled") is not True:
                issues.append("nondeterministic_without_seed_control")
        return tuple(issues)


class NamespaceCheck:
    """Block unknown or unsafe namespaces."""

    def validate(
        self, proposal: RuleProposal, *, allowed_namespaces: tuple[str, ...]
    ) -> tuple[str, ...]:
        issues: list[str] = []
        for item in proposal.diff.add + proposal.diff.modify:
            namespace = item.get("namespace", "genesis")
            if not isinstance(namespace, str) or namespace not in allowed_namespaces:
                issues.append("namespace_not_allowed")
        return tuple(issues)


class ReactionCycleCheck:
    """Simple cycle metadata check."""

    def validate(self, proposal: RuleProposal) -> tuple[str, ...]:
        return tuple(
            "unbounded_reaction_cycle"
            for item in proposal.diff.add + proposal.diff.modify
            if item.get("cycle") == "unbounded"
        )


class CodonActionCompatibilityCheck:
    """Check that proposed codon/action pairs are structured."""

    def validate(self, proposal: RuleProposal) -> tuple[str, ...]:
        issues: list[str] = []
        for item in proposal.diff.add + proposal.diff.modify:
            if "codon" in item and not isinstance(item.get("codon"), str):
                issues.append("codon_must_be_string")
            if "action" in item and not isinstance(item.get("action"), str):
                issues.append("action_must_be_string")
        return tuple(issues)


class FitnessExploitCheck:
    """Flag obvious reward-hacking metadata."""

    def validate(self, proposal: RuleProposal) -> tuple[str, ...]:
        return tuple(
            "fitness_exploit_risk"
            for item in proposal.diff.add + proposal.diff.modify
            if item.get("fitness_direct_write") is True
        )


@dataclass(frozen=True, slots=True)
class RuleValidator:
    strict_conservation: bool = True
    allowed_output_elements: tuple[str, ...] = ("Lumen", "Nexus", "Vitae", "Heat", "Signal")
    allowed_namespaces: tuple[str, ...] = ("genesis", "codontrace")
    max_locality_radius: int = 2

    def validate(self, proposal: RuleProposal) -> RuleValidationResult:
        issues: list[str] = []
        issues.extend(ConservationCheck().validate(proposal, strict=self.strict_conservation))
        issues.extend(LocalityCheck().validate(proposal, max_radius=self.max_locality_radius))
        issues.extend(DeterminismCheck().validate(proposal))
        issues.extend(
            NamespaceCheck().validate(proposal, allowed_namespaces=self.allowed_namespaces)
        )
        issues.extend(ReactionCycleCheck().validate(proposal))
        issues.extend(CodonActionCompatibilityCheck().validate(proposal))
        issues.extend(FitnessExploitCheck().validate(proposal))
        for item in proposal.diff.add + proposal.diff.modify:
            output = item.get("output_element")
            if output is not None and output not in self.allowed_output_elements:
                issues.append("unknown_output_element")
            if any(key in item for key in ("code", "python", "eval", "exec", "import")):
                issues.append("executable_code_not_allowed")
        severity = (
            "none"
            if not issues
            else (
                "high"
                if any("not_allowed" in item or "executable" in item for item in issues)
                else "medium"
            )
        )
        risk = RuleRiskReport(severity=severity, issues=tuple(sorted(issues)))
        return RuleValidationResult(
            proposal_digest=proposal.digest(),
            passed=not issues,
            issues=tuple(sorted(issues)),
            risk_report=risk,
            requires_human_approval=True,
        )


@dataclass(frozen=True, slots=True)
class HumanApprovalRecord:
    proposal_digest: str
    approver: str
    status: ApprovalStatus
    reason: str
    validation_digest: str

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "proposal_digest": self.proposal_digest,
            "approver": self.approver,
            "status": self.status.value,
            "reason": self.reason,
            "validation_digest": self.validation_digest,
        }

    def digest(self) -> str:
        return _digest(self.to_dict())


@dataclass(frozen=True, slots=True)
class ApprovedRuleSet:
    proposal: RuleProposal
    validation: RuleValidationResult
    approval: HumanApprovalRecord

    def __post_init__(self) -> None:
        if not self.validation.passed:
            msg = "Cannot approve a proposal that failed validation."
            raise ConfigurationError(msg)
        if self.approval.status is not ApprovalStatus.APPROVED:
            msg = "Rule proposal requires explicit human approval."
            raise ConfigurationError(msg)
        if self.validation.proposal_digest != self.proposal.digest():
            msg = "Validation proposal digest mismatch."
            raise ConfigurationError(msg)
        if self.approval.proposal_digest != self.proposal.digest():
            msg = "Approval proposal digest mismatch."
            raise ConfigurationError(msg)
        if self.approval.validation_digest != self.validation.digest():
            msg = "Approval validation digest mismatch."
            raise ConfigurationError(msg)

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "proposal": self.proposal.to_dict(),
            "validation": self.validation.to_dict(),
            "approval": self.approval.to_dict(),
            "rule_set_digest": self.digest(),
        }

    def digest(self) -> str:
        return _digest(
            {
                "proposal_digest": self.proposal.digest(),
                "validation_digest": self.validation.digest(),
                "approval_digest": self.approval.digest(),
                "policy_version": "approved_rule_set_v2",
            }
        )


def apply_approved_rule_set(spec: object, approved_rule_set: ApprovedRuleSet) -> object:
    """Return a new experiment spec with an approved rule set attached.

    This is intentionally conservative: the rule proposal remains structured
    data, is never executed as code, and only a small whitelist of declarative
    config updates is applied. Unsupported diff entries are preserved in
    metadata for audit but do not mutate runtime state.
    """

    if not isinstance(approved_rule_set, ApprovedRuleSet):
        msg = "approved_rule_set must be an ApprovedRuleSet."
        raise ConfigurationError(msg)
    if not is_dataclass(spec):
        msg = "apply_approved_rule_set expects a dataclass experiment spec."
        raise ConfigurationError(msg)
    metadata = dict(getattr(spec, "metadata", {}) or {})
    applied: list[dict[str, JsonValue]] = []
    unsupported: list[dict[str, JsonValue]] = []
    updates: dict[str, object] = {"approved_rule_set": approved_rule_set}

    for frozen_item in approved_rule_set.proposal.diff.add + approved_rule_set.proposal.diff.modify:
        item = _thaw_mapping(frozen_item)
        target = item.get("target", "metadata")
        if target == "metadata":
            key = item.get("key") or item.get("name")
            if isinstance(key, str) and key:
                metadata[key] = item.get("value", True)
                applied.append(item)
            else:
                unsupported.append(item)
        elif target == "engine_config":
            _apply_nested_dataclass_update(
                spec, updates, "engine_config", item, applied, unsupported
            )
        elif target == "capsule_transfer_config":
            _apply_nested_dataclass_update(
                spec, updates, "capsule_transfer_config", item, applied, unsupported
            )
        elif target == "causal_graph_config":
            _apply_nested_dataclass_update(
                spec, updates, "causal_graph_config", item, applied, unsupported
            )
        elif target == "population":
            field = item.get("field")
            if field in {
                "population_max",
                "tick_count",
                "initial_runtime_atp",
                "initial_learning_atp",
            }:
                updates[str(field)] = item.get("value")
                applied.append(item)
            else:
                unsupported.append(item)
        else:
            unsupported.append(item)

    metadata["approved_rule_set_digest"] = approved_rule_set.digest()
    metadata["approved_rule_set_applied_entries"] = len(applied)
    metadata["approved_rule_set_unsupported_entries"] = len(unsupported)
    if unsupported:
        metadata["approved_rule_set_unsupported"] = unsupported
    updates["metadata"] = metadata
    return replace(cast(Any, spec), **updates)


def _apply_nested_dataclass_update(
    spec: object,
    updates: dict[str, object],
    attr: str,
    item: Mapping[str, JsonValue],
    applied: list[dict[str, JsonValue]],
    unsupported: list[dict[str, JsonValue]],
) -> None:
    current = updates.get(attr, getattr(spec, attr, None))
    field_name = item.get("field")
    if current is None or not isinstance(field_name, str) or not hasattr(current, field_name):
        unsupported.append(dict(item))
        return
    updates[attr] = replace(cast(Any, current), **{field_name: item.get("value")})
    applied.append(dict(item))


def _digest(payload: Mapping[str, JsonValue]) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


@dataclass(frozen=True, slots=True)
class RuleCompatibilityReport:
    """Compatibility checks against runtime registries without executing proposal code."""

    passed: bool
    issues: tuple[str, ...]
    checked_registries: tuple[str, ...]

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "passed": self.passed,
            "issues": list(self.issues),
            "checked_registries": list(self.checked_registries),
        }

    def digest(self) -> str:
        return _digest(self.to_dict())


@dataclass(frozen=True, slots=True)
class RuleSafetyReport:
    """Safety report for LLM/human rule proposals."""

    schema_valid: bool
    no_code_execution: bool
    deterministic: bool
    human_approval_required: bool = True

    @property
    def passed(self) -> bool:
        return (
            self.schema_valid
            and self.no_code_execution
            and self.deterministic
            and self.human_approval_required
        )

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "schema_valid": self.schema_valid,
            "no_code_execution": self.no_code_execution,
            "deterministic": self.deterministic,
            "human_approval_required": self.human_approval_required,
            "passed": self.passed,
        }


@dataclass(frozen=True, slots=True)
class ApprovedRuleApplicationResult:
    spec_digest_before: str
    spec_digest_after: str
    approved_rule_set_digest: str
    applied: bool

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "spec_digest_before": self.spec_digest_before,
            "spec_digest_after": self.spec_digest_after,
            "approved_rule_set_digest": self.approved_rule_set_digest,
            "applied": self.applied,
        }


def validate_rule_compatibility(
    proposal: RuleProposal,
    *,
    element_registry: object | None = None,
    action_registry: object | None = None,
    codon_table: object | None = None,
    genome_spec: object | None = None,
) -> RuleCompatibilityReport:
    """Check declarative proposal compatibility with supplied registries."""

    issues: list[str] = []
    checked: list[str] = []
    element_symbols = (
        set(element_registry.symbols())
        if element_registry is not None and hasattr(element_registry, "symbols")
        else None
    )
    action_names = (
        set(action_registry.names())
        if action_registry is not None and hasattr(action_registry, "names")
        else None
    )
    codon_bits = (
        {codon.bits for codon in codon_table.actions()}
        if codon_table is not None and hasattr(codon_table, "actions")
        else None
    )
    if element_symbols is not None:
        checked.append("element_registry")
    if action_names is not None:
        checked.append("action_registry")
    if codon_bits is not None:
        checked.append("codon_table")
    if genome_spec is not None:
        checked.append("genome_spec")

    for item in proposal.diff.add + proposal.diff.modify:
        output = item.get("output_element") or item.get("element")
        if (
            element_symbols is not None
            and isinstance(output, str)
            and output not in element_symbols
            and output not in {"Lumen", "Nexus", "Vitae", "Heat", "Signal"}
        ):
            issues.append("element_registry_incompatible")
        action = item.get("action")
        if action_names is not None and isinstance(action, str) and action not in action_names:
            issues.append("action_registry_incompatible")
        codon = item.get("codon")
        if (
            codon_bits is not None
            and isinstance(codon, str)
            and codon in codon_bits
            and item.get("allow_replace") is not True
        ):
            issues.append("codon_table_conflict")
        if genome_spec is not None and isinstance(codon, str):
            width = getattr(genome_spec, "codon_width", None)
            if (
                isinstance(width, int)
                and width > 0
                and len(codon) != width
                and item.get("variable_width") is not True
            ):
                issues.append("genome_spec_width_incompatible")
    return RuleCompatibilityReport(not issues, tuple(sorted(set(issues))), tuple(sorted(checked)))


def build_rule_safety_report(validation: RuleValidationResult) -> RuleSafetyReport:
    issues = set(validation.issues)
    return RuleSafetyReport(
        schema_valid=validation.passed,
        no_code_execution="executable_code_not_allowed" not in issues,
        deterministic="nondeterministic_without_seed_control" not in issues,
        human_approval_required=validation.requires_human_approval,
    )


def apply_approved_rule_set_with_report(
    spec: object, approved_rule_set: ApprovedRuleSet
) -> tuple[object, ApprovedRuleApplicationResult]:
    before = spec.digest() if hasattr(spec, "digest") else _digest({"repr": repr(spec)})
    updated = apply_approved_rule_set(spec, approved_rule_set)
    after = updated.digest() if hasattr(updated, "digest") else _digest({"repr": repr(updated)})
    return updated, ApprovedRuleApplicationResult(
        before, after, approved_rule_set.digest(), before != after
    )
