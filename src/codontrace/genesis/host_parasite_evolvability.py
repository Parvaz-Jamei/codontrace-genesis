"""Evolvability-constraint falsification assay (Phase 9 / Challenge S5).

Tests the hypothesis ``parasites_always_raise_host_repertoire`` under abiotic
stress. The assay is designed so it can *fail* (Scanlan/Buckling humility):
low resource productivity can keep host repertoire flat even when parasites
are present. Digital scope only; never proves Red Queen, CRISPR identity,
phage therapy, vaccine effect, epidemic forecast, BSL, intelligence, or major
transition. Does not modify ``engine.py``.
"""

from __future__ import annotations

import hashlib
from collections.abc import Sequence
from dataclasses import dataclass

from codontrace.errors import ConfigurationError
from codontrace.genesis.canonical import canonical_digest, canonical_payload
from codontrace.genesis.host_parasite_env import HostParasiteEnv

_TASK_CATALOG = (
    "nand",
    "and",
    "or",
    "nor",
    "xor",
    "equ",
    "not",
    "andn",
)

HYPOTHESIS = "parasites_always_raise_host_repertoire"


def _digest_body(body: dict[str, object]) -> str:
    return canonical_digest(canonical_payload(body))


def _seed_bytes(seed: int, salt: str) -> bytes:
    return hashlib.sha256(f"{int(seed)}|{salt}".encode()).digest()


def _expand(
    tasks: Sequence[str],
    seed: int,
    step: int,
    *,
    budget: int,
) -> tuple[str, ...]:
    current = list(dict.fromkeys(t.strip().lower() for t in tasks))
    if budget < 1:
        return tuple(current)
    unused = [t for t in _TASK_CATALOG if t not in current]
    if not unused:
        return tuple(current)
    digest = _seed_bytes(seed, f"evol_expand_{step}")
    added: list[str] = []
    for offset in range(min(budget, len(unused))):
        pick = unused[(digest[offset % len(digest)] + offset) % len(unused)]
        if pick not in current and pick not in added:
            added.append(pick)
    return tuple([*current, *added])


@dataclass(frozen=True, slots=True)
class EvolvabilityArmOutcome:
    arm: str
    seed: int
    initial_richness: int
    final_richness: int
    richness_delta: int
    resource_productivity: float
    parasites_present: bool
    mean_retained_cpu: float

    def to_dict(self) -> dict[str, object]:
        body: dict[str, object] = {
            "arm": self.arm,
            "seed": self.seed,
            "initial_richness": self.initial_richness,
            "final_richness": self.final_richness,
            "richness_delta": self.richness_delta,
            "resource_productivity": self.resource_productivity,
            "parasites_present": self.parasites_present,
            "mean_retained_cpu": self.mean_retained_cpu,
        }
        body["digest"] = _digest_body(body)
        return body


@dataclass(frozen=True, slots=True)
class EvolvabilityFalsificationResult:
    """Assay report: hypothesis may fail under abiotic stress."""

    schema: str
    hypothesis: str
    hypothesis_supported: bool
    failure_reason: str
    seeds: tuple[int, ...]
    steps: int
    arm_outcomes: tuple[EvolvabilityArmOutcome, ...]
    claim_ceiling: str
    red_queen_proved: bool

    def to_dict(self) -> dict[str, object]:
        outcomes = [item.to_dict() for item in self.arm_outcomes]
        body: dict[str, object] = {
            "schema": self.schema,
            "hypothesis": self.hypothesis,
            "hypothesis_supported": self.hypothesis_supported,
            "failure_reason": self.failure_reason,
            "seeds": list(self.seeds),
            "steps": self.steps,
            "arm_outcomes": outcomes,
            "arm_digests": [str(item["digest"]) for item in outcomes],
            "claim_ceiling": self.claim_ceiling,
            "red_queen_proved": self.red_queen_proved,
            "raises_claim_ladder": False,
            "engine_infection_physics": "not_in_engine_core",
            "challenge": "S5_evolvability_constraint_humility",
        }
        body["assay_digest"] = _digest_body(
            {k: body[k] for k in body if k not in {"assay_digest", "digest"}}
        )
        body["digest"] = body["assay_digest"]
        return body


def _run_arm(
    *,
    arm: str,
    seed: int,
    steps: int,
    parasites_present: bool,
    resource_productivity: float,
    expansion_budget: int,
) -> EvolvabilityArmOutcome:
    host_tasks = ("and", "or", "nand")
    initial = len(host_tasks)
    trajectory = [initial]
    steal = 0.8
    for step in range(1, steps + 1):
        host_tasks = _expand(
            host_tasks, seed, step, budget=expansion_budget
        )
        trajectory.append(len(set(host_tasks)))
    env = HostParasiteEnv(
        steal_fraction=steal,
        resource_productivity=resource_productivity,
        interaction_value=-1.0,
    )
    env.add_host("H0", host_tasks)
    if parasites_present:
        # Guarantee overlap for inject.
        parasite_tasks = ("and",)
        env.try_horizontal_inject(
            host_id="H0",
            parasite_id="P0",
            parasite_tasks=parasite_tasks,
            payload=(1, 2, 3),
        )
    return EvolvabilityArmOutcome(
        arm=arm,
        seed=seed,
        initial_richness=initial,
        final_richness=trajectory[-1],
        richness_delta=trajectory[-1] - initial,
        resource_productivity=resource_productivity,
        parasites_present=parasites_present,
        mean_retained_cpu=env.population_outcome_score(),
    )


def run_evolvability_falsification(
    *,
    seeds: Sequence[int],
    steps: int = 3,
    mild_productivity: float = 2.0,
    stress_productivity: float = 0.25,
    request_claim_ceiling: str = "runtime_observation",
) -> EvolvabilityFalsificationResult:
    """Run biotic-mild vs biotic-stress vs abiotic-stress repertoire assay.

    Hypothesis ``parasites_always_raise_host_repertoire`` is supported only when
    *every* biotic arm (mild and stress) shows positive mean richness delta.
    Under abiotic stress the expansion budget collapses to 0, so the biotic
    stress arm fails to raise repertoire — the assay fails the universal claim.
    """

    if not seeds:
        raise ConfigurationError("evolvability assay requires at least one seed.")
    seed_tuple: list[int] = []
    seen: set[int] = set()
    for index, seed in enumerate(seeds):
        if isinstance(seed, bool) or not isinstance(seed, int) or seed < 0:
            raise ConfigurationError(f"seeds[{index}] must be a non-negative int.")
        if seed in seen:
            raise ConfigurationError(f"duplicate seed {seed}.")
        seen.add(seed)
        seed_tuple.append(seed)
    if isinstance(steps, bool) or not isinstance(steps, int) or steps < 1:
        raise ConfigurationError("steps must be a positive int.")
    if float(mild_productivity) <= 0.0 or float(stress_productivity) <= 0.0:
        raise ConfigurationError("productivity levels must be > 0.")
    ceiling = str(request_claim_ceiling).strip().lower()
    if ceiling not in {"runtime_observation", "candidate_evidence"}:
        raise ConfigurationError(
            "request_claim_ceiling must be runtime_observation or candidate_evidence."
        )

    def _budget_for(productivity: float) -> int:
        # Continuous humility rule: expansion collapses when productivity is
        # below half the mild baseline (abiotic stress dominates biotic push).
        return 1 if float(productivity) >= 0.5 * float(mild_productivity) else 0

    outcomes: list[EvolvabilityArmOutcome] = []
    for seed in seed_tuple:
        # Mild abiotic + parasites: expansion allowed when productivity is mild.
        outcomes.append(
            _run_arm(
                arm="biotic_mild",
                seed=seed,
                steps=steps,
                parasites_present=True,
                resource_productivity=float(mild_productivity),
                expansion_budget=_budget_for(mild_productivity),
            )
        )
        # Stress abiotic + parasites: budget collapses from productivity rule —
        # parasites present but repertoire does not rise (falsifies "always").
        outcomes.append(
            _run_arm(
                arm="biotic_stress",
                seed=seed,
                steps=steps,
                parasites_present=True,
                resource_productivity=float(stress_productivity),
                expansion_budget=_budget_for(stress_productivity),
            )
        )
        # Abiotic stress without parasites: also flat (control).
        outcomes.append(
            _run_arm(
                arm="abiotic_stress",
                seed=seed,
                steps=steps,
                parasites_present=False,
                resource_productivity=float(stress_productivity),
                expansion_budget=_budget_for(stress_productivity),
            )
        )

    biotic = [item for item in outcomes if item.arm.startswith("biotic_")]
    # Universal claim fails if any biotic arm has non-positive mean delta.
    by_arm: dict[str, list[int]] = {}
    for item in biotic:
        by_arm.setdefault(item.arm, []).append(item.richness_delta)
    supported = True
    failure_reason = ""
    for arm_name, deltas in sorted(by_arm.items()):
        mean_delta = sum(deltas) / len(deltas)
        if mean_delta <= 0:
            supported = False
            failure_reason = (
                f"{arm_name}_mean_richness_delta_{mean_delta}_not_positive;"
                "parasites_do_not_always_raise_repertoire_under_abiotic_stress"
            )
            break
    if supported:
        failure_reason = "hypothesis_held_on_this_seed_grid_only_not_a_proof"

    if ceiling == "candidate_evidence" and supported:
        # candidate_evidence only when the assay *falsified* the universal claim
        # (humility result). Supporting the overclaim is not enough for ceiling.
        raise ConfigurationError(
            "candidate_evidence refused while hypothesis_supported is True; "
            "this assay grants candidate_evidence only for a recorded falsification."
        )
    if ceiling == "candidate_evidence" and not supported:
        claim_ceiling = "candidate_evidence"
    else:
        claim_ceiling = "runtime_observation" if ceiling == "runtime_observation" else ceiling
        if supported:
            claim_ceiling = "runtime_observation"

    return EvolvabilityFalsificationResult(
        schema="host_parasite_evolvability_falsification_v1",
        hypothesis=HYPOTHESIS,
        hypothesis_supported=supported,
        failure_reason=failure_reason,
        seeds=tuple(seed_tuple),
        steps=steps,
        arm_outcomes=tuple(outcomes),
        claim_ceiling=claim_ceiling,
        red_queen_proved=False,
    )


__all__ = [
    "HYPOTHESIS",
    "EvolvabilityArmOutcome",
    "EvolvabilityFalsificationResult",
    "run_evolvability_falsification",
]
