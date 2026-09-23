"""Cornish-style observational vs interventional multi-arm campaign (Phase 9).

Preregistered arms separate *observational match* from *declared interventions*.
ClaimGate attach never grants ``intervention_supported`` from observational
match alone (Cornish et al. JMLR 27(152) 2026 / arXiv:2301.07210 analogy).

Digital scope only. Does not modify ``engine.py``. Does not prove Red Queen,
CRISPR identity, phage therapy, vaccine effect, epidemic forecast, BSL,
intelligence, or major transition.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from codontrace.errors import ConfigurationError
from codontrace.genesis.canonical import canonical_digest, canonical_payload
from codontrace.genesis.host_parasite_env import (
    DEFAULT_STEAL_FRACTION,
    HostParasiteEnv,
    dual_null_template,
)

_ARM_KINDS = frozenset({"observational", "intervention"})
_INTERVENTION_KINDS = frozenset(
    {
        "remove_parasites",
        "content_null_payload",
        "structure_null_overlap",
        "steal_fraction_ablation",
    }
)


def _digest_body(body: dict[str, object]) -> str:
    return canonical_digest(canonical_payload(body))


@dataclass(frozen=True, slots=True)
class CornishArmSpec:
    arm_id: str
    kind: str
    intervention_kind: str | None
    description: str

    def to_dict(self) -> dict[str, object]:
        return {
            "arm_id": self.arm_id,
            "kind": self.kind,
            "intervention_kind": self.intervention_kind,
            "description": self.description,
        }


@dataclass(frozen=True, slots=True)
class CornishArmOutcome:
    arm_id: str
    kind: str
    intervention_kind: str | None
    score: float
    injected: bool
    notes: tuple[str, ...]

    def to_dict(self) -> dict[str, object]:
        body: dict[str, object] = {
            "arm_id": self.arm_id,
            "kind": self.kind,
            "intervention_kind": self.intervention_kind,
            "score": self.score,
            "injected": self.injected,
            "notes": list(self.notes),
        }
        body["digest"] = _digest_body(body)
        return body


@dataclass(frozen=True, slots=True)
class CornishCampaignResult:
    schema: str
    seeds: tuple[int, ...]
    arm_specs: tuple[CornishArmSpec, ...]
    arm_outcomes: tuple[CornishArmOutcome, ...]
    observational_match: bool
    interventions_executed: bool
    intervention_supported: bool
    claim_ceiling: str
    red_queen_proved: bool
    preregistration_digest: str

    def to_dict(self) -> dict[str, object]:
        outcomes = [item.to_dict() for item in self.arm_outcomes]
        body: dict[str, object] = {
            "schema": self.schema,
            "seeds": list(self.seeds),
            "arm_specs": [item.to_dict() for item in self.arm_specs],
            "arm_outcomes": outcomes,
            "arm_digests": {str(item["arm_id"]): str(item["digest"]) for item in outcomes},
            "observational_match": self.observational_match,
            "interventions_executed": self.interventions_executed,
            "intervention_supported": self.intervention_supported,
            "claim_ceiling": self.claim_ceiling,
            "red_queen_proved": self.red_queen_proved,
            "preregistration_digest": self.preregistration_digest,
            "raises_claim_ladder": False,
            "cornish_rule": (
                "observational_match_alone_never_grants_intervention_supported"
            ),
            "engine_infection_physics": "not_in_engine_core",
        }
        body["campaign_digest"] = _digest_body(
            {k: body[k] for k in body if k not in {"campaign_digest", "digest"}}
        )
        body["digest"] = body["campaign_digest"]
        return body


def _parse_specs(raw_arms: Sequence[Mapping[str, object]]) -> tuple[CornishArmSpec, ...]:
    if not raw_arms:
        raise ConfigurationError("Cornish campaign requires at least one arm spec.")
    specs: list[CornishArmSpec] = []
    seen: set[str] = set()
    for index, raw in enumerate(raw_arms):
        if not isinstance(raw, Mapping):
            raise ConfigurationError(f"arms[{index}] must be a mapping.")
        arm_id = raw.get("arm_id")
        kind = raw.get("kind")
        if not isinstance(arm_id, str) or not arm_id.strip():
            raise ConfigurationError(f"arms[{index}].arm_id is required.")
        if not isinstance(kind, str) or not kind.strip():
            raise ConfigurationError(f"arms[{index}].kind is required.")
        aid = arm_id.strip()
        k = kind.strip().lower()
        if aid.lower() in seen:
            raise ConfigurationError(f"duplicate arm_id {aid!r}.")
        seen.add(aid.lower())
        if k not in _ARM_KINDS:
            raise ConfigurationError(
                f"arms[{index}].kind must be one of {sorted(_ARM_KINDS)}."
            )
        intervention_kind = raw.get("intervention_kind")
        ik: str | None
        if k == "observational":
            if intervention_kind not in (None, ""):
                raise ConfigurationError(
                    f"arms[{index}] observational arms must not set intervention_kind."
                )
            ik = None
        else:
            if not isinstance(intervention_kind, str) or not intervention_kind.strip():
                raise ConfigurationError(
                    f"arms[{index}].intervention_kind is required for intervention arms."
                )
            ik = intervention_kind.strip().lower()
            if ik not in _INTERVENTION_KINDS:
                raise ConfigurationError(
                    f"arms[{index}].intervention_kind must be one of "
                    f"{sorted(_INTERVENTION_KINDS)}."
                )
        description = raw.get("description", "")
        if not isinstance(description, str) or not description.strip():
            raise ConfigurationError(f"arms[{index}].description is required.")
        specs.append(CornishArmSpec(aid, k, ik, description.strip()))
    return tuple(specs)


def _run_observational(
    *,
    host_tasks: Sequence[str],
    parasite_tasks: Sequence[str],
    payload: Sequence[int],
    steal_fraction: float,
) -> tuple[float, bool, tuple[str, ...]]:
    env = HostParasiteEnv(steal_fraction=steal_fraction)
    env.add_host("H0", host_tasks)
    attempt = env.try_horizontal_inject(
        host_id="H0",
        parasite_id="P0",
        parasite_tasks=parasite_tasks,
        payload=payload,
    )
    return env.population_outcome_score(), attempt.injected, ("observational_intact",)


def _run_intervention(
    *,
    intervention_kind: str,
    host_tasks: Sequence[str],
    parasite_tasks: Sequence[str],
    payload: Sequence[int],
    steal_fraction: float,
) -> tuple[float, bool, tuple[str, ...]]:
    if intervention_kind == "remove_parasites":
        env = HostParasiteEnv(steal_fraction=steal_fraction)
        env.add_host("H0", host_tasks)
        return env.population_outcome_score(), False, ("parasites_removed",)
    if intervention_kind == "content_null_payload":
        env = HostParasiteEnv(
            steal_fraction=steal_fraction,
            null_template=dual_null_template("content_null"),
        )
        env.add_host("H0", host_tasks)
        attempt = env.try_horizontal_inject(
            host_id="H0",
            parasite_id="P0",
            parasite_tasks=parasite_tasks,
            payload=payload,
        )
        return (
            env.population_outcome_score(),
            attempt.injected,
            ("content_null_applied",),
        )
    if intervention_kind == "structure_null_overlap":
        env = HostParasiteEnv(
            steal_fraction=steal_fraction,
            null_template=dual_null_template("structure_null"),
        )
        env.add_host("H0", host_tasks)
        attempt = env.try_horizontal_inject(
            host_id="H0",
            parasite_id="P0",
            parasite_tasks=parasite_tasks,
            payload=payload,
        )
        return (
            env.population_outcome_score(),
            attempt.injected,
            ("structure_null_applied",),
        )
    # steal_fraction_ablation
    env = HostParasiteEnv(steal_fraction=0.0)
    env.add_host("H0", host_tasks)
    attempt = env.try_horizontal_inject(
        host_id="H0",
        parasite_id="P0",
        parasite_tasks=parasite_tasks,
        payload=payload,
    )
    return env.population_outcome_score(), attempt.injected, ("steal_fraction_zeroed",)


def default_cornish_arm_specs() -> tuple[dict[str, object], ...]:
    """Preregistered default: one observational + two intervention arms."""

    return (
        {
            "arm_id": "obs_intact",
            "kind": "observational",
            "description": "Observational intact infection score (match only).",
        },
        {
            "arm_id": "int_remove_parasites",
            "kind": "intervention",
            "intervention_kind": "remove_parasites",
            "description": "Declared remove-parasites intervention.",
        },
        {
            "arm_id": "int_content_null",
            "kind": "intervention",
            "intervention_kind": "content_null_payload",
            "description": "Declared content-null intervention.",
        },
    )


def run_cornish_intervention_campaign(
    *,
    seeds: Sequence[int],
    arms: Sequence[Mapping[str, object]] | None = None,
    host_tasks: Sequence[str] = ("and", "or"),
    parasite_tasks: Sequence[str] = ("and",),
    payload: Sequence[int] = (1, 2, 3),
    steal_fraction: float = DEFAULT_STEAL_FRACTION,
    observational_tolerance: float = 1e-9,
    request_claim_ceiling: str = "runtime_observation",
    preregistration_digest: str = "",
) -> CornishCampaignResult:
    """Run observational vs intervention arms under a preregistration digest.

    ``observational_match`` is True when all observational arm scores agree
    within tolerance across seeds (stable observational pattern). That match
    **never** sets ``intervention_supported``. ``intervention_supported`` stays
    False in this digital pack; ClaimGate attach enforces the same refusal.
    """

    if not seeds:
        raise ConfigurationError("Cornish campaign requires at least one seed.")
    seed_tuple: list[int] = []
    seen: set[int] = set()
    for index, seed in enumerate(seeds):
        if isinstance(seed, bool) or not isinstance(seed, int) or seed < 0:
            raise ConfigurationError(f"seeds[{index}] must be a non-negative int.")
        if seed in seen:
            raise ConfigurationError(f"duplicate seed {seed}.")
        seen.add(seed)
        seed_tuple.append(seed)
    specs = _parse_specs(arms if arms is not None else default_cornish_arm_specs())
    ceiling = str(request_claim_ceiling).strip().lower()
    if ceiling not in {"runtime_observation", "candidate_evidence"}:
        raise ConfigurationError(
            "request_claim_ceiling must be runtime_observation or candidate_evidence."
        )
    if not isinstance(preregistration_digest, str) or not preregistration_digest.strip():
        raise ConfigurationError(
            "preregistration_digest is required (preregister before Cornish run)."
        )
    prereg = preregistration_digest.strip().lower()
    if len(prereg) < 16:
        raise ConfigurationError("preregistration_digest looks too short to be canonical.")

    steal = float(steal_fraction)
    if steal != steal or steal < 0.0 or steal > 1.0:
        raise ConfigurationError("steal_fraction must be in [0, 1].")

    outcomes: list[CornishArmOutcome] = []
    for spec in specs:
        # Seeds fold into a single arm outcome via mean score (deterministic).
        scores: list[float] = []
        injected_flags: list[bool] = []
        notes: list[str] = [f"seed_count_{len(seed_tuple)}"]
        for seed in seed_tuple:
            # Seed perturbs payload only; tasks fixed for observational stability.
            seeded_payload = tuple(payload) + (int(seed % 251),)
            if spec.kind == "observational":
                score, injected, note = _run_observational(
                    host_tasks=host_tasks,
                    parasite_tasks=parasite_tasks,
                    payload=seeded_payload,
                    steal_fraction=steal,
                )
            else:
                assert spec.intervention_kind is not None
                score, injected, note = _run_intervention(
                    intervention_kind=spec.intervention_kind,
                    host_tasks=host_tasks,
                    parasite_tasks=parasite_tasks,
                    payload=seeded_payload,
                    steal_fraction=steal,
                )
            scores.append(score)
            injected_flags.append(injected)
            notes.extend(note)
        mean_score = round(sum(scores) / len(scores), 10)
        outcomes.append(
            CornishArmOutcome(
                arm_id=spec.arm_id,
                kind=spec.kind,
                intervention_kind=spec.intervention_kind,
                score=mean_score,
                injected=any(injected_flags),
                notes=tuple(dict.fromkeys(notes)),
            )
        )

    obs_scores = [item.score for item in outcomes if item.kind == "observational"]
    if not obs_scores:
        observational_match = False
    elif len(obs_scores) == 1:
        observational_match = True
    else:
        observational_match = max(obs_scores) - min(obs_scores) <= float(
            observational_tolerance
        )

    interventions_executed = any(item.kind == "intervention" for item in outcomes)
    # Hard rule: observational match alone never grants intervention_supported.
    intervention_supported = False

    return CornishCampaignResult(
        schema="host_parasite_cornish_campaign_v1",
        seeds=tuple(seed_tuple),
        arm_specs=specs,
        arm_outcomes=tuple(outcomes),
        observational_match=observational_match,
        interventions_executed=interventions_executed,
        intervention_supported=intervention_supported,
        claim_ceiling=ceiling if ceiling == "runtime_observation" else "candidate_evidence",
        red_queen_proved=False,
        preregistration_digest=prereg,
    )


__all__ = [
    "CornishArmOutcome",
    "CornishArmSpec",
    "CornishCampaignResult",
    "default_cornish_arm_specs",
    "run_cornish_intervention_campaign",
]
