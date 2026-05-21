"""Pure string claim-audit scaffolds for GENESIS documentation.

This module performs deterministic keyword scanning only. It uses no LLM, no
network access, no file reading, and no report generation. Matching is local:
safe-negation wording can neutralize only the specific claim phrase it scopes,
not a different unsafe phrase elsewhere in the same sentence.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping
from dataclasses import dataclass
from enum import Enum

from codontrace._types import JsonValue
from codontrace.errors import ConfigurationError


class ClaimType(str, Enum):
    AGI = "agi"
    ARTIFICIAL_LIFE_PROOF = "artificial_life_proof"
    OPEN_ENDED_DISCOVERY_PROOF = "open_ended_discovery_proof"
    CAUSAL_PROOF = "causal_proof"
    KNOWLEDGE_TRANSFER_PROOF = "knowledge_transfer_proof"
    BENCHMARK_SUPERIORITY = "benchmark_superiority"
    LIBRARY_FEATURE = "library_feature"
    CONSCIOUSNESS = "consciousness"
    AUTONOMOUS_INTELLIGENCE = "autonomous_intelligence"
    OPEN_ENDED_DISCOVERY_CLAIM = "open_ended_discovery_claim"
    ARTIFICIAL_LIFE_CLAIM = "artificial_life_claim"
    STATE_OF_THE_ART = "state_of_the_art"
    PRODUCTION_AUTONOMY = "production_autonomy"
    SCIENTIFIC_PROOF_OVERCLAIM = "scientific_proof_overclaim"
    OPEN_ENDEDNESS_ACHIEVEMENT = "open_endedness_achievement"
    CAUSAL_LEARNING_PROOF = "causal_learning_proof"
    KNOWLEDGE_TRANSFER_CLAIM = "knowledge_transfer_claim"
    BENCHMARK_LEADERSHIP = "benchmark_leadership"
    PERFORMANCE_SUPERIORITY = "performance_superiority"
    EMERGENCE_PROOF = "emergence_proof"
    SUPERINTELLIGENCE = "superintelligence"
    EMERGENT_LIFE_CLAIM = "emergent_life_claim"
    LIFE_LIKE_INTELLIGENCE_CLAIM = "life_like_intelligence_claim"
    BREAKTHROUGH_AUTONOMY = "breakthrough_autonomy"
    BEST_FRAMEWORK_SUPERIORITY = "best_framework_superiority"
    OPEN_ENDED_AI_CLAIM = "open_ended_ai_claim"


@dataclass(frozen=True, slots=True)
class ClaimAuditContext:
    """Document-level context for claim auditing.

    Context only downgrades clearly negated/non-goal/example wording. It never
    suppresses a separate positive claim in the same document.
    """

    document_name: str
    section_type: str = "current_docs"
    allow_safe_negations: bool = True
    allow_historical_claim_terms_when_negated: bool = True

    def __post_init__(self) -> None:
        allowed = {
            "current_docs",
            "non_goals",
            "changelog",
            "release_evidence",
            "historical",
            "example",
        }
        if self.section_type not in allowed:
            msg = "ClaimAuditContext.section_type is invalid."
            raise ConfigurationError(msg)

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "document_name": self.document_name,
            "section_type": self.section_type,
            "allow_safe_negations": self.allow_safe_negations,
            "allow_historical_claim_terms_when_negated": (
                self.allow_historical_claim_terms_when_negated
            ),
        }

    def digest(self) -> str:
        return _digest(self.to_dict())


@dataclass(frozen=True, slots=True)
class ClaimAuditFinding:
    claim_type: ClaimType
    severity: str
    text: str
    reason: str
    suggested_replacement: str = ""

    def __post_init__(self) -> None:
        if not isinstance(self.claim_type, ClaimType):
            object.__setattr__(self, "claim_type", ClaimType(str(self.claim_type)))
        if self.severity not in {"info", "warning", "blocker"}:
            msg = "ClaimAuditFinding.severity must be info, warning, or blocker."
            raise ConfigurationError(msg)

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "claim_type": self.claim_type.value,
            "severity": self.severity,
            "text": self.text,
            "reason": self.reason,
            "suggested_replacement": self.suggested_replacement,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, JsonValue]) -> ClaimAuditFinding:
        return cls(
            claim_type=ClaimType(_str(data, "claim_type")),
            severity=_str(data, "severity"),
            text=_str(data, "text"),
            reason=_str(data, "reason"),
            suggested_replacement=_str(data, "suggested_replacement", ""),
        )

    def digest(self) -> str:
        return _digest(self.to_dict())


@dataclass(frozen=True, slots=True)
class ClaimAuditResult:
    attempted: bool
    succeeded: bool
    findings: tuple[ClaimAuditFinding, ...]

    @property
    def blocked_claims(self) -> tuple[ClaimAuditFinding, ...]:
        return tuple(item for item in self.findings if item.severity == "blocker")

    @property
    def warnings(self) -> tuple[ClaimAuditFinding, ...]:
        return tuple(item for item in self.findings if item.severity == "warning")

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "attempted": self.attempted,
            "succeeded": self.succeeded,
            "findings": [item.to_dict() for item in self.findings],
            "blocked_claims": [item.to_dict() for item in self.blocked_claims],
            "warnings": [item.to_dict() for item in self.warnings],
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, JsonValue]) -> ClaimAuditResult:
        raw = data.get("findings", [])
        if not isinstance(raw, list):
            msg = "ClaimAuditResult.findings must be a list."
            raise ConfigurationError(msg)
        return cls(
            attempted=_bool(data, "attempted", False),
            succeeded=_bool(data, "succeeded", False),
            findings=tuple(ClaimAuditFinding.from_dict(_mapping(item, "finding")) for item in raw),
        )

    def digest(self) -> str:
        return _digest(self.to_dict())


_BLOCKED_PATTERNS: tuple[tuple[ClaimType, tuple[str, ...], str, str], ...] = (
    (
        ClaimType.AGI,
        (r"\bagi\b", r"artificial general intelligence"),
        "CodonTrace is a research library, not AGI.",
        "library-first research scaffold",
    ),
    (
        ClaimType.SUPERINTELLIGENCE,
        (r"superintelligence",),
        "Superintelligence claims are out of scope.",
        "controlled research-alpha library",
    ),
    (
        ClaimType.CONSCIOUSNESS,
        (r"proves? consciousness", r"consciousness", r"sentience", r"self-aware"),
        "No consciousness, sentience, or self-awareness claim is allowed.",
        "does not model or prove consciousness",
    ),
    (
        ClaimType.ARTIFICIAL_LIFE_PROOF,
        (
            r"proves? artificial life",
            r"artificial life proof",
            r"proof of artificial life",
            r"artificial life achieved",
        ),
        "Use scaffold/evidence wording instead of proof.",
        "research scaffold for artificial-life-adjacent experiments",
    ),
    (
        ClaimType.ARTIFICIAL_LIFE_CLAIM,
        (
            r"demonstrates artificial life",
            r"achieves artificial life",
            r"artificial life system",
        ),
        "Artificial-life demonstration/system language overclaims current evidence.",
        "controlled primitives for artificial-life-adjacent experiments",
    ),
    (
        ClaimType.EMERGENT_LIFE_CLAIM,
        (r"emergent life", r"creates emergent life"),
        "Emergent-life language is not supported by this alpha.",
        "controlled emergence-adjacent research scaffold",
    ),
    (
        ClaimType.LIFE_LIKE_INTELLIGENCE_CLAIM,
        (r"life[- ]like intelligence", r"proves? life[- ]like intelligence"),
        "Life-like intelligence claims are out of scope.",
        "agent-behavior evidence scaffold",
    ),
    (
        ClaimType.OPEN_ENDED_DISCOVERY_PROOF,
        (r"proves? open[- ]ended", r"open[- ]ended discovery proof", r"proof of open[- ]ended"),
        "Open-endedness is not claimed as proof.",
        "evidence scaffold for open-endedness research",
    ),
    (
        ClaimType.OPEN_ENDED_DISCOVERY_CLAIM,
        (
            r"achieves open[- ]ended discovery",
            r"demonstrates open[- ]ended discovery",
            r"open[- ]ended discovery achieved",
            r"achieves open[- ]endedness",
            r"open[- ]endedness achieved",
            r"achieves open[- ]ended evolution",
            r"demonstrates open[- ]ended evolution",
        ),
        "Open-ended discovery achievement language is not supported.",
        "auditable open-ended-discovery experiment scaffold",
    ),
    (
        ClaimType.OPEN_ENDED_AI_CLAIM,
        (r"open[- ]ended ai",),
        "Open-ended AI claims are too broad for this research alpha.",
        "GENESIS-aligned research toolkit",
    ),
    (
        ClaimType.AUTONOMOUS_INTELLIGENCE,
        (r"autonomous intelligence", r"production autonomous intelligence"),
        "Autonomous intelligence claims are out of scope.",
        "controlled agent experiments",
    ),
    (
        ClaimType.BREAKTHROUGH_AUTONOMY,
        (r"breakthrough autonomous agent", r"autonomous agent breakthrough"),
        "Breakthrough autonomy language is not supported.",
        "controlled agent research scaffold",
    ),
    (
        ClaimType.PRODUCTION_AUTONOMY,
        (r"production autonomous", r"production-ready autonomous"),
        "Production autonomy is not claimed.",
        "pre-public research alpha",
    ),
    (
        ClaimType.CAUSAL_PROOF,
        (
            r"causal proof",
            r"proves? causality",
            r"causal discovery proof",
            r"proof of causal learning",
            r"causal learning proof",
            r"proves? causal learning",
            r"proves? emergence",
        ),
        "Causal graph objects are evidence scaffolds only.",
        "local causal-evidence scaffold",
    ),
    (
        ClaimType.KNOWLEDGE_TRANSFER_PROOF,
        (
            r"proves? knowledge transfer",
            r"knowledge transfer proof",
            r"knowledge transfer proven",
            r"knowledge transfer is demonstrated",
            r"demonstrates knowledge transfer",
        ),
        "Capsules are controlled exchange scaffolds only.",
        "controlled capsule-transfer evidence scaffold",
    ),
    (
        ClaimType.BENCHMARK_SUPERIORITY,
        (
            r"beats benchmarks",
            r"benchmark superiority",
            r"superior to benchmarks",
            r"benchmark[- ]leading",
            r"best[- ]in[- ]class",
            r"outperforms all",
            r"superior performance",
        ),
        "No benchmark superiority is claimed.",
        "no benchmark-superiority claim",
    ),
    (
        ClaimType.BEST_FRAMEWORK_SUPERIORITY,
        (r"best framework", r"best library"),
        "Best-framework/library language is unsupported superiority wording.",
        "professional research toolkit",
    ),
    (
        ClaimType.STATE_OF_THE_ART,
        (r"state of the art", r"state-of-the-art", r"\bsota\b"),
        "State-of-the-art language is not supported by this alpha.",
        "research-oriented alpha library",
    ),
    (
        ClaimType.SCIENTIFIC_PROOF_OVERCLAIM,
        (r"scientifically proves", r"proof-grade", r"proves emergence", r"emergence achieved"),
        "Proof-grade language requires external scientific validation.",
        "auditable evidence scaffold",
    ),
)

_ALLOWED_SCAFFOLD_PATTERNS: tuple[str, ...] = (
    r"library-first research scaffold",
    r"research scaffold for artificial[- ]life",
    r"artificial[- ]life[- ]adjacent experiments",
    r"controlled agent experiments",
    r"evidence infrastructure only",
    r"evidence scaffold only",
    r"no proof of artificial life",
    r"no superintelligence claim",
    r"does not prove open[- ]ended discovery",
)

_NEGATION_PREFIX_RE = re.compile(
    r"(?:does\s+not|do\s+not|did\s+not|not|no|without|never)\s+"
    r"(?:a\s+|an\s+|the\s+)?"
    r"(?:claim\s+of\s+|proof\s+of\s+|evidence\s+of\s+proof\s+of\s+|"
    r"prove\s+|proves\s+|proving\s+|demonstrate\s+|demonstrates\s+|"
    r"demonstration\s+of\s+|achieve\s+|achieves\s+|achievement\s+of\s+|"
    r"benchmark\s+claim\s+)?$"
)


def audit_claim_text(text: str) -> ClaimAuditResult:
    """Audit one string for blocked claim language with local safe-negation handling."""

    findings: list[ClaimAuditFinding] = []
    lowered = text.lower()
    seen: set[tuple[ClaimType, int, int]] = set()
    for claim_type, patterns, reason, replacement in _BLOCKED_PATTERNS:
        for pattern in patterns:
            for match in re.finditer(pattern, lowered):
                key = (claim_type, match.start(), match.end())
                if key in seen:
                    continue
                seen.add(key)
                snippet = _snippet(lowered, match.start(), match.end())
                if _is_safe_match_context(lowered, match.start()):
                    findings.append(
                        ClaimAuditFinding(
                            claim_type=claim_type,
                            severity="info",
                            text=snippet,
                            reason="Safe local negation/non-goal context detected for this phrase.",
                            suggested_replacement="",
                        )
                    )
                else:
                    findings.append(
                        ClaimAuditFinding(
                            claim_type=claim_type,
                            severity="blocker",
                            text=snippet,
                            reason=reason,
                            suggested_replacement=replacement,
                        )
                    )
    if any(re.search(pattern, lowered) for pattern in _ALLOWED_SCAFFOLD_PATTERNS) and not any(
        f.severity == "blocker" for f in findings
    ):
        findings.append(
            ClaimAuditFinding(
                claim_type=ClaimType.LIBRARY_FEATURE,
                severity="info",
                text="research scaffold",
                reason="Library/scaffold wording is acceptable.",
                suggested_replacement="",
            )
        )
    elif "library" in lowered and not findings:
        findings.append(
            ClaimAuditFinding(
                claim_type=ClaimType.LIBRARY_FEATURE,
                severity="info",
                text="library",
                reason="Library-feature wording is acceptable.",
                suggested_replacement="",
            )
        )
    return ClaimAuditResult(
        attempted=True,
        succeeded=not any(f.severity == "blocker" for f in findings),
        findings=tuple(findings),
    )


def audit_docs_claims(
    docs: Mapping[str, str],
    contexts: Mapping[str, ClaimAuditContext] | None = None,
) -> ClaimAuditResult:
    """Audit caller-provided document text mapping without reading files.

    Document context is used only to downgrade clearly safe non-goal/history or
    claim-audit example text. Positive overclaims remain blockers everywhere.
    """

    findings: list[ClaimAuditFinding] = []
    for name, text in sorted(docs.items()):
        context = None if contexts is None else contexts.get(name)
        if context is None:
            context = _infer_claim_context(name, text)
        result = audit_claim_text(text)
        for finding in result.findings:
            severity = finding.severity
            reason = finding.reason
            if severity == "blocker" and _docs_finding_is_safe(finding, context, text):
                severity = (
                    "info"
                    if context.section_type
                    in {"non_goals", "changelog", "historical", "release_evidence"}
                    else "warning"
                )
                reason = f"Context-scoped non-goal/history/example wording: {finding.reason}"
            findings.append(
                ClaimAuditFinding(
                    claim_type=finding.claim_type,
                    severity=severity,
                    text=f"{name}[{context.section_type}]:{finding.text}",
                    reason=reason,
                    suggested_replacement=finding.suggested_replacement,
                )
            )
    return ClaimAuditResult(
        attempted=True,
        succeeded=not any(f.severity == "blocker" for f in findings),
        findings=tuple(findings),
    )


def _infer_claim_context(name: str, text: str) -> ClaimAuditContext:
    lowered_name = name.lower()
    lowered_text = text.lower()
    section_type = "current_docs"
    if "non_goal" in lowered_name or "non-goal" in lowered_text or "non-goals" in lowered_text:
        section_type = "non_goals"
    elif "changelog" in lowered_name:
        section_type = "changelog"
    elif "release_evidence" in lowered_name or "release evidence" in lowered_text:
        section_type = "release_evidence"
    elif "history" in lowered_name or "roadmap" in lowered_name:
        section_type = "historical"
    elif "example" in lowered_name or "claim audit" in lowered_text:
        section_type = "example"
    return ClaimAuditContext(document_name=name, section_type=section_type)


def _docs_finding_is_safe(
    finding: ClaimAuditFinding, context: ClaimAuditContext, full_text: str
) -> bool:
    if not context.allow_safe_negations:
        return False
    lowered = full_text.lower()
    snippet = finding.text.lower()
    # Positive superiority phrases are release blockers unless the local snippet
    # itself is an explicit non-claim/example.
    positive_claim = finding.claim_type in {
        ClaimType.STATE_OF_THE_ART,
        ClaimType.BEST_FRAMEWORK_SUPERIORITY,
        ClaimType.BENCHMARK_SUPERIORITY,
        ClaimType.BENCHMARK_LEADERSHIP,
        ClaimType.PERFORMANCE_SUPERIORITY,
    }
    safe_markers = (
        "does not",
        "do not",
        "not proof",
        "not a proof",
        "never a proof",
        "no proof",
        "not evidence",
        "does not establish",
        "no claim",
        "no ",
        "non-claim",
        "non-goal",
        "non-goals",
        "must not claim",
        "forbidden",
        "blocked claim",
        "claim audit",
        "example of unsafe",
        "prohibited claims",
    )
    snippet_safe = any(marker in snippet for marker in safe_markers)
    idx = lowered.find(snippet[: min(len(snippet), 48)].strip())
    window = lowered[max(0, idx - 220) : min(len(lowered), idx + 260)] if idx >= 0 else lowered
    window_safe = any(marker in window for marker in safe_markers) or any(
        marker in window
        for marker in (
            "claim pattern",
            "claim-audit",
            "blocked pattern",
            "blocked claim",
            "prohibited claims",
        )
    )
    contextual_safe_doc = context.section_type in {
        "non_goals",
        "changelog",
        "historical",
        "release_evidence",
        "example",
    }
    if positive_claim and not (snippet_safe or (contextual_safe_doc and window_safe)):
        return False
    if snippet_safe:
        return True
    if contextual_safe_doc:
        # Only safe when nearby wording clearly frames the phrase as a rejected
        # claim, limitation, or example, not as a positive capability statement.
        return window_safe
    return False


def _is_safe_match_context(text: str, match_start: int) -> bool:
    prefix = text[max(0, match_start - 160) : match_start]
    # Stop a broad sentence-level negation from hiding a separate claim after a
    # contrastive conjunction or punctuation break. Within one clause, allow
    # list-style non-goals such as "No AGI, consciousness, or proof is claimed"
    # and "does not prove X, Y, or Z".
    tail = re.split(r"[.;!?]|\bbut\b|\bhowever\b|\balthough\b", prefix)[-1]
    if _NEGATION_PREFIX_RE.search(tail):
        return True
    if re.search(
        r"(?:does\s+not|do\s+not|did\s+not|not|no|without|never)\s+"
        r"(?:a\s+|an\s+|the\s+)?"
        r"(?:claim|claims|prove|proves|proof|evidence|demonstrate|demonstrates|"
        r"establish|establishes|achieve|achieves|benchmark\s+claim)"
        r"(?:\s+of)?",
        tail,
    ):
        return True
    return _is_safe_negated_list_tail(tail)


def _is_safe_negated_list_tail(tail: str) -> bool:
    """Return whether a local clause is still inside a negated non-claim list."""

    normalized = " ".join(tail.split())
    if not normalized:
        return False
    if not re.search(r"(?:^|\s)(?:no|without)\s+", normalized):
        return False
    # Keep this local and conservative: the caller already split away
    # contrastive conjunctions and sentence punctuation. Require either a list
    # separator or explicit non-claim/proof vocabulary so a bare unrelated
    # occurrence after "no" is not automatically hidden.
    if "," not in normalized and " or " not in normalized and " and " not in normalized:
        return bool(re.search(r"(?:claim|proof|prove|demonstrat|achiev)", normalized))
    return not re.search(r"\b(?:proves?|demonstrates?|achieves?)\b", normalized)


def _snippet(text: str, start: int, end: int) -> str:
    left = max(0, start - 70)
    right = min(len(text), end + 70)
    return " ".join(text[left:right].split())


def _digest(payload: Mapping[str, JsonValue]) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _mapping(value: object, name: str) -> Mapping[str, JsonValue]:
    if not isinstance(value, Mapping):
        msg = f"{name} must be an object."
        raise ConfigurationError(msg)
    return value


def _str(data: Mapping[str, JsonValue], key: str, default: str | None = None) -> str:
    value = data.get(key, default)
    if not isinstance(value, str):
        msg = f"{key} must be a string."
        raise ConfigurationError(msg)
    return value


def _bool(data: Mapping[str, JsonValue], key: str, default: bool) -> bool:
    value = data.get(key, default)
    if not isinstance(value, bool):
        msg = f"{key} must be a boolean."
        raise ConfigurationError(msg)
    return value
