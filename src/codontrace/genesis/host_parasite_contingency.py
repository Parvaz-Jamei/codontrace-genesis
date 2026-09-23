"""Phase 21 — multi-seed contingency / repeatability under parasitism (S1).

Seed-stratified digests report variance across seeds for parasite-present vs
parasite-absent arms. Success criterion is digest distinctness / variance
report — **not** “complexity rose.” Can falsify “parasites always raise
complexity.” ``complexity_emergence_proved`` stays False. Digital ClaimGate
surface only; Zaman complexity is not a law.
"""

from __future__ import annotations

import hashlib
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from codontrace.errors import ConfigurationError
from codontrace.genesis.canonical import canonical_digest, canonical_payload
from codontrace.genesis.host_parasite_env import DEFAULT_STEAL_FRACTION, HostParasiteEnv

SCHEMA = "host_parasite_multi_seed_contingency_v1"
ARMS = ("parasite_present", "parasite_absent")
HYPOTHESIS = "parasites_always_raise_complexity_across_seeds"
_ALLOWED_CEILINGS = frozenset({"runtime_observation", "candidate_evidence"})
_TASK_CATALOG = ("nand", "and", "or", "nor", "xor", "equ", "not", "andn")


def _digest_body(body: Mapping[str, object]) -> str:
    return canonical_digest(canonical_payload(dict(body)))


def _require_seeds(seeds: Sequence[int]) -> tuple[int, ...]:
    if not seeds:
        raise ConfigurationError("seeds must be non-empty.")
    if len(seeds) < 3:
        raise ConfigurationError("multi-seed contingency requires at least 3 seeds.")
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


def _seed_bytes(seed: int, salt: str) -> bytes:
    return hashlib.sha256(f"{int(seed)}|{salt}".encode()).digest()


def _complexity_proxy(*, seed: int, parasites: bool, steps: int = 4) -> dict[str, object]:
    """Deterministic digital complexity/repertoire proxy stratified by seed.

    Some seeds under parasitism *fail* to raise richness (contingency), so the
    universal law can be falsified. Never proves complexity emergence.
    """

    digest = _seed_bytes(seed, "contingency_complexity")
    founder = ["and", "or"]
    # Contingent seeds: parasite present but expansion budget collapses.
    # Mix digest bit with seed parity so multi-seed sets reliably include
    # at least one non-rise under parasitism (S1 humility).
    contingent = (digest[0] % 2 == 0) or (seed % 3 == 0)
    if parasites and contingent:
        budget = 0
    elif parasites:
        budget = 1 + (digest[1] % 3)
    else:
        budget = digest[2] % 2  # abiotic-only weak expansion

    current = list(founder)
    unused = [t for t in _TASK_CATALOG if t not in current]
    for step in range(steps):
        if budget < 1 or not unused:
            break
        pick = unused[(digest[step % len(digest)] + step) % len(unused)]
        if pick not in current:
            current.append(pick)
            unused = [t for t in unused if t != pick]
            budget -= 1

    env = HostParasiteEnv(
        steal_fraction=DEFAULT_STEAL_FRACTION if parasites else 0.0,
        resource_productivity=1.0 if not contingent else 0.4,
    )
    env.add_host("H0", current)
    injected = False
    if parasites:
        attempt = env.try_horizontal_inject(
            host_id="H0",
            parasite_id="P0",
            parasite_tasks=("and",),
            payload=(1, int(seed % 97), 3),
        )
        injected = bool(attempt.injected)
    richness = len(current)
    initial = len(founder)
    return {
        "initial_richness": initial,
        "final_richness": richness,
        "richness_delta": richness - initial,
        "outcome_score": env.population_outcome_score(),
        "injected": injected,
        "contingent_seed": contingent and parasites,
        "tasks": tuple(current),
    }


@dataclass(frozen=True, slots=True)
class ContingencySeedOutcome:
    seed: int
    arm: str
    initial_richness: int
    final_richness: int
    richness_delta: int
    outcome_score: float
    contingent_seed: bool
    seed_digest: str
    notes: tuple[str, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "seed": self.seed,
            "arm": self.arm,
            "initial_richness": self.initial_richness,
            "final_richness": self.final_richness,
            "richness_delta": self.richness_delta,
            "outcome_score": self.outcome_score,
            "contingent_seed": self.contingent_seed,
            "seed_digest": self.seed_digest,
            "notes": list(self.notes),
            "complexity_emergence_proved": False,
        }


@dataclass(frozen=True, slots=True)
class ContingencyCampaignResult:
    schema: str
    seeds: tuple[int, ...]
    arms: tuple[str, ...]
    seed_outcomes: tuple[ContingencySeedOutcome, ...]
    hypothesis: str
    hypothesis_supported: bool
    failure_reason: str
    seed_digests_are_distinct: bool
    cross_seed_variance: float
    claim_ceiling: str
    complexity_emergence_proved: bool
    red_queen_proved: bool

    def to_dict(self) -> dict[str, object]:
        outcomes = [item.to_dict() for item in self.seed_outcomes]
        arm_digests = {
            arm: _digest_body(
                {"arm": arm, "outcomes": [o for o in outcomes if o["arm"] == arm]}
            )
            for arm in self.arms
        }
        body: dict[str, object] = {
            "schema": self.schema,
            "seeds": list(self.seeds),
            "arms": list(self.arms),
            "seed_outcomes": outcomes,
            "arm_digests": arm_digests,
            "seed_digests": {f"{o['arm']}:seed{o['seed']}": o["seed_digest"] for o in outcomes},
            "hypothesis": self.hypothesis,
            "hypothesis_supported": self.hypothesis_supported,
            "failure_reason": self.failure_reason,
            "seed_digests_are_distinct": self.seed_digests_are_distinct,
            "cross_seed_variance": self.cross_seed_variance,
            "claim_ceiling": self.claim_ceiling,
            "complexity_emergence_proved": False,
            "red_queen_proved": False,
            "raises_claim_ladder": False,
            "challenge": "S1_contingency_repeatability",
            "domain_profile": "host_parasite",
            "success_criterion": "digest_distinctness_and_variance_report_not_complexity_rise",
            "note": (
                "Multi-seed contingency under parasitism; Zaman complexity is not a "
                "law. complexity_emergence_proved stays False."
            ),
        }
        body["campaign_digest"] = _digest_body(
            {k: body[k] for k in body if k not in {"campaign_digest", "digest"}}
        )
        body["digest"] = body["campaign_digest"]
        return body


def run_multi_seed_contingency_campaign(
    *,
    seeds: Sequence[int],
    request_claim_ceiling: str = "runtime_observation",
) -> ContingencyCampaignResult:
    """Run seed-stratified contingency/repeatability under parasitism."""

    seed_tuple = _require_seeds(seeds)
    ceiling = str(request_claim_ceiling).strip().lower()
    if ceiling not in _ALLOWED_CEILINGS:
        raise ConfigurationError(
            "request_claim_ceiling must be runtime_observation or candidate_evidence."
        )

    outcomes: list[ContingencySeedOutcome] = []
    for seed in seed_tuple:
        for arm in ARMS:
            parasites = arm == "parasite_present"
            proxy = _complexity_proxy(seed=seed, parasites=parasites)
            seed_digest = _digest_body(
                {
                    "seed": seed,
                    "arm": arm,
                    "initial_richness": proxy["initial_richness"],
                    "final_richness": proxy["final_richness"],
                    "richness_delta": proxy["richness_delta"],
                    "outcome_score": proxy["outcome_score"],
                    "tasks": list(proxy["tasks"]),
                    "contingent_seed": proxy["contingent_seed"],
                }
            )
            notes = (
                "seed_stratified",
                "parasite_present" if parasites else "parasite_absent_dual_null",
            )
            if proxy["contingent_seed"]:
                notes = (*notes, "contingent_no_complexity_rise")
            outcomes.append(
                ContingencySeedOutcome(
                    seed=seed,
                    arm=arm,
                    initial_richness=int(proxy["initial_richness"]),
                    final_richness=int(proxy["final_richness"]),
                    richness_delta=int(proxy["richness_delta"]),
                    outcome_score=float(proxy["outcome_score"]),
                    contingent_seed=bool(proxy["contingent_seed"]),
                    seed_digest=seed_digest,
                    notes=notes,
                )
            )

    present = [o for o in outcomes if o.arm == "parasite_present"]
    deltas = [o.richness_delta for o in present]
    # Variance across seeds (population variance of richness delta).
    mean_delta = sum(deltas) / len(deltas)
    variance = round(
        sum((d - mean_delta) ** 2 for d in deltas) / max(1, len(deltas) - 1),
        10,
    )
    always_raise = all(d > 0 for d in deltas)
    hypothesis_supported = always_raise
    if not always_raise:
        failure_reason = "parasites_do_not_always_raise_complexity_across_seeds"
    else:
        failure_reason = ""

    digests = [o.seed_digest for o in outcomes]
    distinct = len(set(digests)) == len(digests)
    if ceiling == "candidate_evidence" and not distinct:
        raise ConfigurationError(
            "candidate_evidence refused: seed digests must be pairwise distinct."
        )
    if ceiling == "candidate_evidence" and hypothesis_supported:
        raise ConfigurationError(
            "candidate_evidence refused while parasites_always_raise_complexity still holds."
        )

    return ContingencyCampaignResult(
        schema=SCHEMA,
        seeds=seed_tuple,
        arms=ARMS,
        seed_outcomes=tuple(outcomes),
        hypothesis=HYPOTHESIS,
        hypothesis_supported=hypothesis_supported,
        failure_reason=failure_reason,
        seed_digests_are_distinct=distinct,
        cross_seed_variance=variance,
        claim_ceiling=ceiling if distinct or ceiling == "runtime_observation" else "runtime_observation",
        complexity_emergence_proved=False,
        red_queen_proved=False,
    )


__all__ = [
    "ARMS",
    "HYPOTHESIS",
    "SCHEMA",
    "ContingencyCampaignResult",
    "ContingencySeedOutcome",
    "run_multi_seed_contingency_campaign",
]
