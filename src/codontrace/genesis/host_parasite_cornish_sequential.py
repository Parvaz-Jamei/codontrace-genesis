"""Phase 22 — sequential Cornish multi-intervention deepening.

Ordered intervention schedule with a required observational baseline. A twin
that matches observational history can still fail a later intervention in the
schedule. Observational match alone never grants ``intervention_supported``
(Cornish et al. JMLR 27(152) 2026 / arXiv:2301.07210). Digital ClaimGate only;
no clinical decision-support claim.
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

SCHEMA = "host_parasite_cornish_sequential_v1"
_INTERVENTION_KINDS = frozenset(
    {
        "remove_parasites",
        "content_null_payload",
        "structure_null_overlap",
        "steal_fraction_ablation",
        "break_spatial_structure",
    }
)
_ALLOWED_CEILINGS = frozenset({"runtime_observation", "candidate_evidence"})


def _digest_body(body: Mapping[str, object]) -> str:
    return canonical_digest(canonical_payload(dict(body)))


def _require_seeds(seeds: Sequence[int]) -> tuple[int, ...]:
    if not seeds:
        raise ConfigurationError("seeds must be non-empty.")
    out: list[int] = []
    seen: set[int] = set()
    for index, seed in enumerate(seeds):
        if isinstance(seed, bool) or not isinstance(seed, int) or seed < 0:
            raise ConfigurationError(f"seeds[{index}] must be a non-negative int.")
        if seed in seen:
            raise ConfigurationError(f"duplicate seed {seed}.")
        seen.add(seed)
        out.append(seed)
    return tuple(out)


def default_sequential_schedule() -> tuple[dict[str, object], ...]:
    """Preregistered ordered schedule: observational baseline then interventions."""

    return (
        {
            "step_id": "obs_baseline",
            "kind": "observational",
            "description": "Observational history baseline (match only).",
        },
        {
            "step_id": "int_remove_parasites",
            "kind": "intervention",
            "intervention_kind": "remove_parasites",
            "description": "First declared intervention: remove parasites.",
        },
        {
            "step_id": "int_content_null",
            "kind": "intervention",
            "intervention_kind": "content_null_payload",
            "description": "Second declared intervention: content-null payload.",
        },
        {
            "step_id": "int_steal_ablation",
            "kind": "intervention",
            "intervention_kind": "steal_fraction_ablation",
            "description": "Third declared intervention: zero steal fraction.",
        },
    )


def _run_step(
    *,
    kind: str,
    intervention_kind: str | None,
    host_tasks: Sequence[str],
    parasite_tasks: Sequence[str],
    payload: Sequence[int],
    steal_fraction: float,
) -> tuple[float, bool, tuple[str, ...]]:
    if kind == "observational":
        env = HostParasiteEnv(steal_fraction=steal_fraction)
        env.add_host("H0", host_tasks)
        attempt = env.try_horizontal_inject(
            host_id="H0",
            parasite_id="P0",
            parasite_tasks=parasite_tasks,
            payload=payload,
        )
        return env.population_outcome_score(), attempt.injected, ("observational_intact",)

    assert intervention_kind is not None
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
        return env.population_outcome_score(), attempt.injected, ("content_null_applied",)
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
    if intervention_kind == "steal_fraction_ablation":
        env = HostParasiteEnv(steal_fraction=0.0)
        env.add_host("H0", host_tasks)
        attempt = env.try_horizontal_inject(
            host_id="H0",
            parasite_id="P0",
            parasite_tasks=parasite_tasks,
            payload=payload,
        )
        return env.population_outcome_score(), attempt.injected, ("steal_fraction_zeroed",)
    # break_spatial_structure
    env = HostParasiteEnv(
        steal_fraction=steal_fraction,
        spatial_mode="well_mixed",
    )
    env.add_host("H0", host_tasks)
    attempt = env.try_horizontal_inject(
        host_id="H0",
        parasite_id="P0",
        parasite_tasks=parasite_tasks,
        payload=payload,
    )
    return env.population_outcome_score(), attempt.injected, ("spatial_structure_broken",)


def _parse_schedule(
    raw_steps: Sequence[Mapping[str, object]],
) -> tuple[tuple[str, str, str | None, str], ...]:
    if not raw_steps:
        raise ConfigurationError("sequential Cornish schedule requires at least one step.")
    parsed: list[tuple[str, str, str | None, str]] = []
    seen: set[str] = set()
    has_obs = False
    for index, raw in enumerate(raw_steps):
        if not isinstance(raw, Mapping):
            raise ConfigurationError(f"schedule[{index}] must be a mapping.")
        step_id = raw.get("step_id")
        kind = raw.get("kind")
        if not isinstance(step_id, str) or not step_id.strip():
            raise ConfigurationError(f"schedule[{index}].step_id is required.")
        if not isinstance(kind, str) or not kind.strip():
            raise ConfigurationError(f"schedule[{index}].kind is required.")
        sid = step_id.strip()
        k = kind.strip().lower()
        if sid.lower() in seen:
            raise ConfigurationError(f"duplicate step_id {sid!r}.")
        seen.add(sid.lower())
        if k not in {"observational", "intervention"}:
            raise ConfigurationError(
                f"schedule[{index}].kind must be observational or intervention."
            )
        intervention_kind = raw.get("intervention_kind")
        ik: str | None
        if k == "observational":
            has_obs = True
            if intervention_kind not in (None, ""):
                raise ConfigurationError(
                    f"schedule[{index}] observational steps must not set intervention_kind."
                )
            ik = None
        else:
            if not isinstance(intervention_kind, str) or not intervention_kind.strip():
                raise ConfigurationError(
                    f"schedule[{index}].intervention_kind is required for intervention steps."
                )
            ik = intervention_kind.strip().lower()
            if ik not in _INTERVENTION_KINDS:
                raise ConfigurationError(
                    f"schedule[{index}].intervention_kind must be one of "
                    f"{sorted(_INTERVENTION_KINDS)}."
                )
        description = raw.get("description", "")
        if not isinstance(description, str) or not description.strip():
            raise ConfigurationError(f"schedule[{index}].description is required.")
        parsed.append((sid, k, ik, description.strip()))
    if not has_obs:
        raise ConfigurationError(
            "sequential Cornish schedule requires an observational baseline step."
        )
    if not any(k == "intervention" for _, k, _, _ in parsed):
        raise ConfigurationError(
            "sequential Cornish schedule requires at least one intervention step."
        )
    # Observational baseline must be first (ordered schedule deepening).
    if parsed[0][1] != "observational":
        raise ConfigurationError(
            "observational baseline must be the first step in the ordered schedule."
        )
    return tuple(parsed)


@dataclass(frozen=True, slots=True)
class SequentialStepOutcome:
    step_id: str
    order: int
    kind: str
    intervention_kind: str | None
    score: float
    injected: bool
    matches_observational_baseline: bool
    intervention_effect_distinct: bool
    step_digest: str
    notes: tuple[str, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "step_id": self.step_id,
            "order": self.order,
            "kind": self.kind,
            "intervention_kind": self.intervention_kind,
            "score": self.score,
            "injected": self.injected,
            "matches_observational_baseline": self.matches_observational_baseline,
            "intervention_effect_distinct": self.intervention_effect_distinct,
            "step_digest": self.step_digest,
            "notes": list(self.notes),
            "intervention_supported": False,
        }


@dataclass(frozen=True, slots=True)
class SequentialCornishResult:
    schema: str
    seeds: tuple[int, ...]
    schedule: tuple[dict[str, object], ...]
    step_outcomes: tuple[SequentialStepOutcome, ...]
    observational_match: bool
    later_intervention_failed: bool
    interventions_executed: bool
    intervention_supported: bool
    claim_ceiling: str
    red_queen_proved: bool
    preregistration_digest: str

    def to_dict(self) -> dict[str, object]:
        outcomes = [item.to_dict() for item in self.step_outcomes]
        body: dict[str, object] = {
            "schema": self.schema,
            "seeds": list(self.seeds),
            "schedule": list(self.schedule),
            "step_outcomes": outcomes,
            "step_digests": {o["step_id"]: o["step_digest"] for o in outcomes},
            "observational_match": self.observational_match,
            "later_intervention_failed": self.later_intervention_failed,
            "interventions_executed": self.interventions_executed,
            "intervention_supported": False,
            "claim_ceiling": self.claim_ceiling,
            "red_queen_proved": False,
            "preregistration_digest": self.preregistration_digest,
            "raises_claim_ladder": False,
            "cornish_rule": (
                "observational_match_alone_never_grants_intervention_supported"
            ),
            "clinical_decision_support": False,
            "domain_profile": "host_parasite",
            "note": (
                "Sequential multi-intervention Cornish deepening; observational "
                "accuracy alone never grants intervention_supported."
            ),
        }
        body["campaign_digest"] = _digest_body(
            {k: body[k] for k in body if k not in {"campaign_digest", "digest"}}
        )
        body["digest"] = body["campaign_digest"]
        return body


def run_sequential_cornish_campaign(
    *,
    seeds: Sequence[int],
    schedule: Sequence[Mapping[str, object]] | None = None,
    host_tasks: Sequence[str] = ("and", "or"),
    parasite_tasks: Sequence[str] = ("and",),
    payload: Sequence[int] = (1, 2, 3),
    steal_fraction: float = DEFAULT_STEAL_FRACTION,
    observational_tolerance: float = 1e-9,
    request_claim_ceiling: str = "runtime_observation",
    preregistration_digest: str = "",
) -> SequentialCornishResult:
    """Run ordered observational→intervention schedule under Cornish refusal."""

    seed_tuple = _require_seeds(seeds)
    steps = _parse_schedule(schedule if schedule is not None else default_sequential_schedule())
    ceiling = str(request_claim_ceiling).strip().lower()
    if ceiling not in _ALLOWED_CEILINGS:
        raise ConfigurationError(
            "request_claim_ceiling must be runtime_observation or candidate_evidence."
        )
    if not isinstance(preregistration_digest, str) or not preregistration_digest.strip():
        raise ConfigurationError(
            "preregistration_digest is required (preregister before sequential Cornish)."
        )
    prereg = preregistration_digest.strip().lower()
    if len(prereg) < 16:
        raise ConfigurationError("preregistration_digest looks too short to be canonical.")

    steal = float(steal_fraction)
    if steal != steal or steal < 0.0 or steal > 1.0:
        raise ConfigurationError("steal_fraction must be in [0, 1].")

    schedule_dicts = tuple(
        {
            "step_id": sid,
            "kind": kind,
            "intervention_kind": ik,
            "description": desc,
            "order": order,
        }
        for order, (sid, kind, ik, desc) in enumerate(steps)
    )

    outcomes: list[SequentialStepOutcome] = []
    baseline_score: float | None = None
    for order, (sid, kind, ik, desc) in enumerate(steps):
        scores: list[float] = []
        injected_flags: list[bool] = []
        notes: list[str] = [f"seed_count_{len(seed_tuple)}", f"order_{order}", desc]
        for seed in seed_tuple:
            seeded_payload = tuple(payload) + (int(seed % 251),)
            score, injected, note = _run_step(
                kind=kind,
                intervention_kind=ik,
                host_tasks=host_tasks,
                parasite_tasks=parasite_tasks,
                payload=seeded_payload,
                steal_fraction=steal,
            )
            scores.append(score)
            injected_flags.append(injected)
            notes.extend(note)
        mean_score = round(sum(scores) / len(scores), 10)
        if kind == "observational":
            baseline_score = mean_score
            matches = True
            distinct_effect = False
        else:
            assert baseline_score is not None
            matches = abs(mean_score - baseline_score) <= float(observational_tolerance)
            # Intervention "fails" (falsifies twin) when it does NOT move score
            # away from observational baseline — twin matched history but later
            # intervention has no distinct effect.
            distinct_effect = not matches
        step_digest = _digest_body(
            {
                "step_id": sid,
                "order": order,
                "kind": kind,
                "intervention_kind": ik,
                "score": mean_score,
                "matches_observational_baseline": matches if kind == "observational" else matches,
                "intervention_effect_distinct": distinct_effect,
            }
        )
        outcomes.append(
            SequentialStepOutcome(
                step_id=sid,
                order=order,
                kind=kind,
                intervention_kind=ik,
                score=mean_score,
                injected=any(injected_flags),
                matches_observational_baseline=matches if kind != "observational" else True,
                intervention_effect_distinct=distinct_effect,
                step_digest=step_digest,
                notes=tuple(dict.fromkeys(notes)),
            )
        )

    obs_scores = [o.score for o in outcomes if o.kind == "observational"]
    observational_match = bool(obs_scores)  # baseline present and scored
    # Later intervention failed = at least one intervention lacks distinct effect
    # OR we explicitly record that match≠support (always true for support flag).
    intervention_steps = [o for o in outcomes if o.kind == "intervention"]
    later_intervention_failed = any(
        not o.intervention_effect_distinct for o in intervention_steps
    ) or any(o.matches_observational_baseline for o in intervention_steps)
    # If all interventions moved scores, still refuse support from obs match alone;
    # mark later_intervention_failed False but intervention_supported stays False.
    if all(o.intervention_effect_distinct for o in intervention_steps):
        later_intervention_failed = False

    interventions_executed = bool(intervention_steps)
    # Hard Cornish rule.
    intervention_supported = False

    digests = [o.step_digest for o in outcomes]
    distinct = len(set(digests)) == len(digests)
    if ceiling == "candidate_evidence" and not distinct:
        raise ConfigurationError(
            "candidate_evidence refused: sequential steps must produce distinct digests."
        )

    return SequentialCornishResult(
        schema=SCHEMA,
        seeds=seed_tuple,
        schedule=schedule_dicts,
        step_outcomes=tuple(outcomes),
        observational_match=observational_match,
        later_intervention_failed=later_intervention_failed,
        interventions_executed=interventions_executed,
        intervention_supported=intervention_supported,
        claim_ceiling=ceiling,
        red_queen_proved=False,
        preregistration_digest=prereg,
    )


__all__ = [
    "SCHEMA",
    "SequentialCornishResult",
    "SequentialStepOutcome",
    "default_sequential_schedule",
    "run_sequential_cornish_campaign",
]
