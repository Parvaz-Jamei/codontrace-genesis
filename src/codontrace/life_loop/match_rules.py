"""Domain-free MatchRule specs and phenotype comparators for the life-loop.

Builds contact-compatible MatchRule callables from PhenotypeMap + MatchRuleSpec.
Graded feature-overlap (Jaccard), optional allele-match mode, threshold gate, and
score_scale modifier. No discipline vocabulary, no contagion-engine types, no claim-ladder
imports, no tick physics.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, Literal

from codontrace._types import JsonValue
from codontrace.contracts.banned import BANNED_DOMAIN_TOKENS
from codontrace.errors import ConfigurationError
from codontrace.genesis.canonical import canonical_digest, require_finite_float
from codontrace.life_loop.contact import MatchRule
from codontrace.life_loop.phenotype import PhenotypeMap, PhenotypeRecord

SCHEMA_VERSION = "life_loop_match_rules_v1"

MatchMode = Literal["always", "never", "feature_overlap", "allele_match"]

MATCH_MODES: frozenset[str] = frozenset(
    {"always", "never", "feature_overlap", "allele_match"}
)

MatchFailReason = Literal[
    "passed",
    "no_overlap",
    "below_threshold",
    "missing_phenotype",
    "allele_mismatch",
    "mode_disabled",
    "scaled_out",
]

MATCH_FAIL_REASONS: frozenset[str] = frozenset(
    {
        "passed",
        "no_overlap",
        "below_threshold",
        "missing_phenotype",
        "allele_mismatch",
        "mode_disabled",
        "scaled_out",
    }
)


def _as_str(value: object, name: str, *, allow_empty: bool = False) -> str:
    if not isinstance(value, str):
        raise ConfigurationError(f"{name} must be a string.")
    text = value.strip()
    if not text and not allow_empty:
        raise ConfigurationError(f"{name} must be a non-empty string.")
    return text


def _refuse_banned_fragment(text: str, name: str) -> str:
    lowered = text.casefold()
    for token in BANNED_DOMAIN_TOKENS:
        if token.casefold() in lowered:
            raise ConfigurationError(f"{name} contains a banned fragment.")
    return text


def _check_digest(existing: str, computed: str, label: str) -> str:
    if existing and existing != computed:
        raise ConfigurationError(f"{label} digest mismatch.")
    return computed


def _unit_interval(value: object, name: str) -> float:
    number = float(require_finite_float(name, value))
    if number < 0.0 or number > 1.0:
        raise ConfigurationError(f"{name} must be in [0, 1].")
    return number


def _score_scale(value: object, name: str) -> float:
    number = float(require_finite_float(name, value))
    if number <= 0.0 or number > 1.0:
        raise ConfigurationError(f"{name} must be in (0, 1].")
    return number


def jaccard_overlap(a_tags: frozenset[str], b_tags: frozenset[str]) -> float:
    """Jaccard similarity; empty∪empty → 0.0 (vacuous match refused)."""

    if not a_tags and not b_tags:
        return 0.0
    union = a_tags | b_tags
    if not union:
        return 0.0
    return float(len(a_tags & b_tags) / len(union))


@dataclass(frozen=True, slots=True)
class MatchRuleSpec:
    """Immutable digest-stable match configuration."""

    spec_id: str
    mode: str = "feature_overlap"
    threshold: float = 0.0
    score_scale: float = 1.0
    allele_mode_enabled: bool = False
    digest: str = ""

    def __post_init__(self) -> None:
        sid = _refuse_banned_fragment(_as_str(self.spec_id, "spec_id"), "spec_id")
        object.__setattr__(self, "spec_id", sid)
        mode = _as_str(self.mode, "mode").casefold()
        if mode not in MATCH_MODES:
            raise ConfigurationError(f"unknown match mode {self.mode!r}.")
        object.__setattr__(self, "mode", mode)
        object.__setattr__(
            self, "threshold", _unit_interval(self.threshold, "threshold")
        )
        object.__setattr__(
            self, "score_scale", _score_scale(self.score_scale, "score_scale")
        )
        if not isinstance(self.allele_mode_enabled, bool):
            raise ConfigurationError("allele_mode_enabled must be a bool.")
        if mode == "allele_match" and not self.allele_mode_enabled:
            raise ConfigurationError(
                "allele_match requires allele_mode_enabled=True."
            )
        computed = canonical_digest(self._body(), prefix="match_spec")
        object.__setattr__(
            self, "digest", _check_digest(self.digest, computed, "MatchRuleSpec")
        )

    def _body(self) -> dict[str, JsonValue]:
        return {
            "schema_version": SCHEMA_VERSION,
            "spec_id": self.spec_id,
            "mode": self.mode,
            "threshold": self.threshold,
            "score_scale": self.score_scale,
            "allele_mode_enabled": self.allele_mode_enabled,
        }

    def to_dict(self) -> dict[str, JsonValue]:
        return {**self._body(), "digest": self.digest}

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> MatchRuleSpec:
        return cls(
            spec_id=_as_str(data.get("spec_id"), "spec_id"),
            mode=_as_str(data.get("mode", "feature_overlap"), "mode"),
            threshold=float(
                require_finite_float("threshold", data.get("threshold", 0.0))
            ),
            score_scale=float(
                require_finite_float("score_scale", data.get("score_scale", 1.0))
            ),
            allele_mode_enabled=bool(data.get("allele_mode_enabled", False)),
            digest=_as_str(data.get("digest", ""), "digest", allow_empty=True),
        )


@dataclass(frozen=True, slots=True)
class MatchOutcome:
    """Observation-only match result (not a claim grade)."""

    score: float
    passed: bool
    reason: str
    raw_overlap: float = 0.0

    def __post_init__(self) -> None:
        score = float(require_finite_float("score", self.score))
        if score < 0.0 or score > 1.0:
            raise ConfigurationError("score must be in [0, 1].")
        object.__setattr__(self, "score", score)
        if not isinstance(self.passed, bool):
            raise ConfigurationError("passed must be a bool.")
        reason = _as_str(self.reason, "reason").casefold()
        if reason not in MATCH_FAIL_REASONS:
            raise ConfigurationError(f"unknown match reason {self.reason!r}.")
        object.__setattr__(self, "reason", reason)
        raw = float(require_finite_float("raw_overlap", self.raw_overlap))
        if raw < 0.0 or raw > 1.0:
            raise ConfigurationError("raw_overlap must be in [0, 1].")
        object.__setattr__(self, "raw_overlap", raw)

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "score": self.score,
            "passed": self.passed,
            "reason": self.reason,
            "raw_overlap": self.raw_overlap,
        }


def score_phenotypes(
    left: PhenotypeRecord | None,
    right: PhenotypeRecord | None,
    spec: MatchRuleSpec,
) -> MatchOutcome:
    """Compare two phenotype records under a MatchRuleSpec."""

    if not isinstance(spec, MatchRuleSpec):
        raise ConfigurationError("spec must be a MatchRuleSpec.")

    if spec.mode == "always":
        return MatchOutcome(score=1.0, passed=True, reason="passed", raw_overlap=1.0)
    if spec.mode == "never":
        return MatchOutcome(score=0.0, passed=False, reason="no_overlap", raw_overlap=0.0)

    if left is None or right is None:
        return MatchOutcome(
            score=0.0, passed=False, reason="missing_phenotype", raw_overlap=0.0
        )

    if spec.mode == "allele_match":
        if not spec.allele_mode_enabled:
            return MatchOutcome(
                score=0.0, passed=False, reason="mode_disabled", raw_overlap=0.0
            )
        if left.feature_tags == right.feature_tags and left.feature_tags:
            alpha = float(spec.score_scale)
            if alpha <= 0.0:
                return MatchOutcome(
                    score=0.0, passed=False, reason="scaled_out", raw_overlap=1.0
                )
            if alpha < spec.threshold:
                return MatchOutcome(
                    score=0.0,
                    passed=False,
                    reason="below_threshold",
                    raw_overlap=1.0,
                )
            return MatchOutcome(
                score=alpha, passed=True, reason="passed", raw_overlap=1.0
            )
        return MatchOutcome(
            score=0.0, passed=False, reason="allele_mismatch", raw_overlap=0.0
        )

    # feature_overlap (Jaccard)
    raw = jaccard_overlap(left.tag_set, right.tag_set)
    if raw <= 0.0:
        return MatchOutcome(
            score=0.0, passed=False, reason="no_overlap", raw_overlap=0.0
        )
    scaled = min(1.0, max(0.0, raw * float(spec.score_scale)))
    if scaled <= 0.0:
        return MatchOutcome(
            score=0.0, passed=False, reason="scaled_out", raw_overlap=raw
        )
    if scaled < spec.threshold:
        return MatchOutcome(
            score=0.0, passed=False, reason="below_threshold", raw_overlap=raw
        )
    return MatchOutcome(score=scaled, passed=True, reason="passed", raw_overlap=raw)


def evaluate_match(
    spec: MatchRuleSpec,
    phenotype_map: PhenotypeMap,
    left_id: str,
    right_id: str,
) -> MatchOutcome:
    """Look up phenotypes by id and score them."""

    if not isinstance(phenotype_map, PhenotypeMap):
        raise ConfigurationError("phenotype_map must be a PhenotypeMap.")
    return score_phenotypes(
        phenotype_map.get(left_id),
        phenotype_map.get(right_id),
        spec,
    )


def bind_match_rule(
    spec: MatchRuleSpec,
    phenotype_map: PhenotypeMap | None = None,
) -> MatchRule:
    """Return a contact-compatible MatchRule.

    Failed gates return 0.0 so apply_contact records match_failed.
    Passed gates return the graded α in (0, 1].
    always/never ignore the phenotype map.
    """

    if not isinstance(spec, MatchRuleSpec):
        raise ConfigurationError("spec must be a MatchRuleSpec.")
    if spec.mode in {"feature_overlap", "allele_match"}:
        if phenotype_map is None:
            raise ConfigurationError(
                f"mode {spec.mode!r} requires a PhenotypeMap."
            )
        if not isinstance(phenotype_map, PhenotypeMap):
            raise ConfigurationError("phenotype_map must be a PhenotypeMap.")

    empty = PhenotypeMap(map_id="empty_map", records=())
    book = phenotype_map if phenotype_map is not None else empty

    def _rule(left_id: str, right_id: str) -> float:
        outcome = evaluate_match(spec, book, left_id, right_id)
        return float(outcome.score) if outcome.passed else 0.0

    return _rule


def spec_for_mode(
    mode: str,
    *,
    spec_id: str | None = None,
    threshold: float = 0.0,
    score_scale: float = 1.0,
    allele_mode_enabled: bool = False,
) -> MatchRuleSpec:
    """Convenience constructor with default spec_id derived from mode."""

    mid = _as_str(mode, "mode").casefold()
    sid = spec_id or f"spec_{mid}"
    enabled = allele_mode_enabled or mid == "allele_match"
    return MatchRuleSpec(
        spec_id=sid,
        mode=mid,
        threshold=threshold,
        score_scale=score_scale,
        allele_mode_enabled=enabled if mid == "allele_match" else allele_mode_enabled,
    )


__all__ = [
    "MATCH_FAIL_REASONS",
    "MATCH_MODES",
    "SCHEMA_VERSION",
    "MatchFailReason",
    "MatchMode",
    "MatchOutcome",
    "MatchRuleSpec",
    "bind_match_rule",
    "evaluate_match",
    "jaccard_overlap",
    "score_phenotypes",
    "spec_for_mode",
]
