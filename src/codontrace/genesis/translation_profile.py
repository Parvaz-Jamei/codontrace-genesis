"""Adaptive genotype-phenotype map proxy through immutable translation profiles."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from codontrace._types import JsonValue
from codontrace.errors import ConfigurationError
from codontrace.genesis.canonical import require_finite_float
from codontrace.rng import RNGManager, RNGProtocol


def _digest(payload: Mapping[str, JsonValue]) -> str:
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def _round(value: float) -> float:
    return round(require_finite_float("translation_float", value), 12)


@dataclass(frozen=True, slots=True)
class TranslationWeight:
    codon: str
    action: str
    weight: float
    evidence_count: int
    last_updated_tick: int

    def __post_init__(self) -> None:
        if not self.codon or not self.action:
            raise ConfigurationError("TranslationWeight codon/action must not be empty.")
        object.__setattr__(self, "weight", require_finite_float("weight", self.weight))
        if self.evidence_count < 0 or self.last_updated_tick < 0:
            raise ConfigurationError("TranslationWeight counts/ticks must be non-negative.")

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "codon": self.codon,
            "action": self.action,
            "weight": _round(self.weight),
            "evidence_count": self.evidence_count,
            "last_updated_tick": self.last_updated_tick,
        }


@dataclass(frozen=True, slots=True)
class TranslationProfile:
    profile_id: str
    genome_spec_digest: str
    weights: tuple[TranslationWeight, ...]
    version: str
    digest: str = ""

    def __post_init__(self) -> None:
        ordered = tuple(sorted(self.weights, key=lambda item: (item.codon, item.action)))
        object.__setattr__(self, "weights", ordered)
        computed = _digest(self._payload())
        if self.digest and self.digest != computed:
            raise ConfigurationError("TranslationProfile digest mismatch.")
        object.__setattr__(self, "digest", computed)

    def _payload(self) -> dict[str, JsonValue]:
        return {
            "profile_id": self.profile_id,
            "genome_spec_digest": self.genome_spec_digest,
            "weights": [w.to_dict() for w in self.weights],
            "version": self.version,
        }

    def to_dict(self) -> dict[str, JsonValue]:
        return {**self._payload(), "digest": self.digest}


def build_translation_profile(
    profile_id: str,
    genome_spec_digest: str,
    weights: Sequence[TranslationWeight],
    *,
    version: str = "translation_profile_v1",
) -> TranslationProfile:
    ordered = tuple(sorted(weights, key=lambda item: (item.codon, item.action)))
    payload: dict[str, JsonValue] = {
        "profile_id": profile_id,
        "genome_spec_digest": genome_spec_digest,
        "weights": [w.to_dict() for w in ordered],
        "version": version,
    }
    return TranslationProfile(profile_id, genome_spec_digest, ordered, version, _digest(payload))


def translation_profile_from_dict(data: Mapping[str, JsonValue]) -> TranslationProfile:
    raw = data.get("weights", [])
    if not isinstance(raw, list):
        raise ConfigurationError("TranslationProfile.weights must be a list.")
    profile = build_translation_profile(
        _str(data, "profile_id"),
        _str(data, "genome_spec_digest"),
        tuple(_weight_from_dict(item) for item in raw if isinstance(item, Mapping)),
        version=_str(data, "version", "translation_profile_v1"),
    )
    if data.get("digest") is not None and profile.digest != data.get("digest"):
        raise ConfigurationError("TranslationProfile digest mismatch.")
    return profile


@dataclass(frozen=True, slots=True)
class TranslationPolicy:
    mode: str = "argmax"
    min_weight: float = 0.0
    allow_unknown_codons: bool = False
    fallback_to_base_table: bool = True
    approved_actions: tuple[str, ...] = ()
    weight_lower_bound: float = 0.0
    weight_upper_bound: float = 1.0e12
    max_translation_entropy: float = 16.0
    min_compile_success_rate: float = 0.0

    def __post_init__(self) -> None:
        if self.mode not in {"argmax", "seeded_sample", "conservative_base_fallback"}:
            raise ConfigurationError("Unsupported TranslationPolicy.mode.")
        if self.weight_upper_bound < self.weight_lower_bound:
            raise ConfigurationError("TranslationPolicy weight bounds are invalid.")
        object.__setattr__(self, "approved_actions", tuple(sorted(set(self.approved_actions))))

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "mode": self.mode,
            "min_weight": self.min_weight,
            "allow_unknown_codons": self.allow_unknown_codons,
            "fallback_to_base_table": self.fallback_to_base_table,
            "approved_actions": list(self.approved_actions),
            "weight_lower_bound": self.weight_lower_bound,
            "weight_upper_bound": self.weight_upper_bound,
            "max_translation_entropy": self.max_translation_entropy,
            "min_compile_success_rate": self.min_compile_success_rate,
        }


@dataclass(frozen=True, slots=True)
class TranslationUpdateRecord:
    organism_id: str
    tick: int
    codon: str
    old_action: str | None
    new_action: str
    old_weight: float
    new_weight: float
    reason: str
    atp_learning_cost: float
    digest: str = ""

    def __post_init__(self) -> None:
        computed = _digest(self._payload())
        if self.digest and self.digest != computed:
            raise ConfigurationError("TranslationUpdateRecord digest mismatch.")
        object.__setattr__(self, "digest", computed)

    def _payload(self) -> dict[str, JsonValue]:
        return {
            "organism_id": self.organism_id,
            "tick": self.tick,
            "codon": self.codon,
            "old_action": self.old_action,
            "new_action": self.new_action,
            "old_weight": _round(self.old_weight),
            "new_weight": _round(self.new_weight),
            "reason": self.reason,
            "atp_learning_cost": _round(self.atp_learning_cost),
        }

    def to_dict(self) -> dict[str, JsonValue]:
        return {**self._payload(), "digest": self.digest}


@dataclass(frozen=True, slots=True)
class SemanticProxyReport:
    profile_id: str
    compile_success_rate: float
    affected_codons: int
    behavior_delta_digest: str
    lineage_persistence: int
    translation_entropy: float
    translation_stability: float
    replay_captured: bool
    claim_level: str = "adaptive_gp_map_proxy"
    digest: str = ""

    def __post_init__(self) -> None:
        if self.claim_level == "semantic_closure":
            raise ConfigurationError("SemanticProxyReport must not claim semantic_closure.")
        computed = _digest(self._payload())
        if self.digest and self.digest != computed:
            raise ConfigurationError("SemanticProxyReport digest mismatch.")
        object.__setattr__(self, "digest", computed)

    def _payload(self) -> dict[str, JsonValue]:
        return {
            "profile_id": self.profile_id,
            "compile_success_rate": _round(self.compile_success_rate),
            "affected_codons": self.affected_codons,
            "behavior_delta_digest": self.behavior_delta_digest,
            "lineage_persistence": self.lineage_persistence,
            "translation_entropy": _round(self.translation_entropy),
            "translation_stability": _round(self.translation_stability),
            "replay_captured": self.replay_captured,
            "claim_level": self.claim_level,
        }

    def to_dict(self) -> dict[str, JsonValue]:
        return {**self._payload(), "digest": self.digest}


def resolve_translation_action(
    codon: str,
    base_action: str | None,
    profile: TranslationProfile | None,
    policy: TranslationPolicy | None = None,
    rng: RNGProtocol | None = None,
) -> str | None:
    pol = policy or TranslationPolicy()
    if profile is None:
        return base_action
    for weight in profile.weights:
        if weight.weight < pol.weight_lower_bound or weight.weight > pol.weight_upper_bound:
            raise ConfigurationError("TranslationProfile weight outside policy bounds.")
        if pol.approved_actions and weight.action not in pol.approved_actions:
            raise ConfigurationError("TranslationProfile references unapproved action.")
    candidates = [w for w in profile.weights if w.codon == codon and w.weight >= pol.min_weight]
    if not candidates:
        if base_action is not None and pol.fallback_to_base_table:
            return base_action
        return codon if pol.allow_unknown_codons else None
    if pol.mode in {"argmax", "conservative_base_fallback"}:
        return sorted(candidates, key=lambda w: (-w.weight, w.action))[0].action
    stream = rng or RNGManager(seed=0, namespace="translation_profile")
    ordered = sorted(candidates, key=lambda w: w.action)
    return stream.choice(ordered).action


def update_translation_profile(
    profile: TranslationProfile,
    *,
    organism_id: str,
    tick: int,
    codon: str,
    new_action: str,
    delta: float,
    reason: str,
    atp_learning_available: float,
    atp_learning_cost: float = 1.0,
) -> tuple[TranslationProfile, TranslationUpdateRecord, float]:
    if atp_learning_available < atp_learning_cost:
        raise ConfigurationError("insufficient_atp_learning_for_translation_update")
    weights = list(profile.weights)
    old_action = None
    old_weight = 0.0
    updated = False
    for index, weight in enumerate(weights):
        if weight.codon == codon and weight.action == new_action:
            old_action = weight.action
            old_weight = weight.weight
            weights[index] = TranslationWeight(
                codon, new_action, weight.weight + delta, weight.evidence_count + 1, tick
            )
            updated = True
            break
    if not updated:
        weights.append(TranslationWeight(codon, new_action, delta, 1, tick))
    new_profile = build_translation_profile(
        profile.profile_id, profile.genome_spec_digest, weights, version=profile.version
    )
    record = TranslationUpdateRecord(
        organism_id,
        tick,
        codon,
        old_action,
        new_action,
        old_weight,
        old_weight + delta,
        reason,
        atp_learning_cost,
    )
    return new_profile, record, round(atp_learning_available - atp_learning_cost, 10)


def inherit_translation_profile(
    profile: TranslationProfile, *, child_profile_id: str, mutation_delta: float = 0.0
) -> TranslationProfile:
    weights = tuple(
        TranslationWeight(
            w.codon, w.action, w.weight + mutation_delta, w.evidence_count, w.last_updated_tick
        )
        for w in profile.weights
    )
    return build_translation_profile(
        child_profile_id, profile.genome_spec_digest, weights, version=profile.version
    )


def build_semantic_proxy_report(
    profile: TranslationProfile,
    *,
    behavior_delta_digest: str = "none",
    lineage_persistence: int = 0,
    replay_captured: bool = True,
) -> SemanticProxyReport:
    affected = len({w.codon for w in profile.weights})
    total = sum(max(w.weight, 0.0) for w in profile.weights)
    entropy = 0.0
    if total > 0:
        import math

        for w in profile.weights:
            p = max(w.weight, 0.0) / total
            if p > 0:
                entropy -= p * math.log(p, 2)
    return SemanticProxyReport(
        profile.profile_id,
        1.0 if profile.weights else 0.0,
        affected,
        behavior_delta_digest,
        lineage_persistence,
        round(entropy, 10),
        1.0 / max(1, affected),
        replay_captured,
    )


def _weight_from_dict(data: Mapping[str, JsonValue]) -> TranslationWeight:
    return TranslationWeight(
        _str(data, "codon"),
        _str(data, "action"),
        _float(data, "weight", 0.0),
        _int(data, "evidence_count", 0),
        _int(data, "last_updated_tick", 0),
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
    return float(value)
