"""Phase 16 — virulence / resistance quality proxies (Challenge S7, digital only).

Qualitative resistance: seat/overlap gate (infect or not).
Quantitative resistance: graded steal_fraction drain.
Dual-null contrast can falsify 'any parasite always raises host cost'.
``virulence_optimized_for_humans`` stays blocked forever.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from codontrace.errors import ConfigurationError
from codontrace.genesis.canonical import canonical_digest, canonical_payload
from codontrace.genesis.host_parasite_env import HostParasiteEnv

SCHEMA = "host_parasite_virulence_resistance_quality_v1"
HYPOTHESIS = "any_parasite_always_raises_host_cost"
ARMS = (
    "qualitative_resistance_gate",
    "quantitative_steal_gradient",
    "content_null_control",
    "structure_null_control",
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


@dataclass(frozen=True, slots=True)
class VirulenceArmOutcome:
    seed: int
    arm: str
    host_cost: float
    infected: bool
    resistance_quality: str
    arm_digest: str
    notes: tuple[str, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "seed": self.seed,
            "arm": self.arm,
            "host_cost": self.host_cost,
            "infected": self.infected,
            "resistance_quality": self.resistance_quality,
            "arm_digest": self.arm_digest,
            "notes": list(self.notes),
            "virulence_optimized_for_humans": False,
        }


@dataclass(frozen=True, slots=True)
class VirulenceQualityResult:
    schema: str
    seeds: tuple[int, ...]
    arms: tuple[str, ...]
    arm_outcomes: tuple[VirulenceArmOutcome, ...]
    hypothesis: str
    hypothesis_supported: bool
    failure_reason: str
    claim_ceiling: str
    arms_are_distinct: bool
    red_queen_proved: bool
    virulence_optimized_for_humans: bool

    def to_dict(self) -> dict[str, object]:
        outcomes = [item.to_dict() for item in self.arm_outcomes]
        arm_digests = {
            arm: _digest_body({"arm": arm, "outcomes": [o for o in outcomes if o["arm"] == arm]})
            for arm in self.arms
        }
        body: dict[str, object] = {
            "schema": self.schema,
            "seeds": list(self.seeds),
            "arms": list(self.arms),
            "arm_outcomes": outcomes,
            "arm_digests": arm_digests,
            "hypothesis": self.hypothesis,
            "hypothesis_supported": self.hypothesis_supported,
            "failure_reason": self.failure_reason,
            "claim_ceiling": self.claim_ceiling,
            "arms_are_distinct": self.arms_are_distinct,
            "red_queen_proved": False,
            "virulence_optimized_for_humans": False,
            "raises_claim_ladder": False,
            "challenge": "S7_gandon_resistance_quality_digital_proxy",
            "domain_profile": "host_parasite",
            "engine_infection_physics": "not_in_engine_core",
        }
        body["campaign_digest"] = _digest_body(
            {k: body[k] for k in body if k not in {"campaign_digest", "digest"}}
        )
        body["digest"] = body["campaign_digest"]
        return body


def _run_arm(*, seed: int, arm: str) -> VirulenceArmOutcome:
    notes = [f"arm_{arm}", "digital_proxy_only"]
    if arm == "qualitative_resistance_gate":
        # Overlap absent → seat refuses infection (qualitative resistance).
        env = HostParasiteEnv(steal_fraction=0.8, transmission_mode="horizontal")
        env.add_host("H0", ("nand", "xor"))
        attempt = env.try_horizontal_inject(
            host_id="H0",
            parasite_id="P0",
            parasite_tasks=("and",),  # no overlap
            payload=(seed % 13, 1),
        )
        infected = bool(attempt.injected)
        host_cost = 0.0 if not infected else 0.8
        quality = "qualitative_gate"
        notes.append("no_overlap_blocks_seat")
    elif arm == "quantitative_steal_gradient":
        env = HostParasiteEnv(steal_fraction=0.8, transmission_mode="horizontal")
        env.add_host("H0", ("and", "nand"))
        attempt = env.try_horizontal_inject(
            host_id="H0",
            parasite_id="P0",
            parasite_tasks=("and",),
            payload=(seed % 13, 2),
        )
        infected = bool(attempt.injected)
        # Graded cost from steal_fraction when infected.
        host_cost = float(env.steal_fraction) if infected else 0.0
        quality = "quantitative_steal"
        notes.append("graded_steal_fraction_cost")
    elif arm == "content_null_control":
        env = HostParasiteEnv(
            steal_fraction=0.8,
            transmission_mode="horizontal",
            null_template=__import__(
                "codontrace.genesis.host_parasite_env", fromlist=["dual_null_template"]
            ).dual_null_template("content_null"),
        )
        env.add_host("H0", ("and", "nand"))
        attempt = env.try_horizontal_inject(
            host_id="H0",
            parasite_id="P0",
            parasite_tasks=("and",),
            payload=(seed % 13, 3),
        )
        infected = bool(attempt.injected)
        # Content null: seat may occupy but cost proxy collapses.
        host_cost = 0.0
        quality = "content_null"
        notes.append("content_null_zero_cost_proxy")
    else:  # structure_null_control
        env = HostParasiteEnv(
            steal_fraction=0.8,
            transmission_mode="horizontal",
            null_template=__import__(
                "codontrace.genesis.host_parasite_env", fromlist=["dual_null_template"]
            ).dual_null_template("structure_null"),
        )
        env.add_host("H0", ("and", "nand"))
        attempt = env.try_horizontal_inject(
            host_id="H0",
            parasite_id="P0",
            parasite_tasks=("and",),
            payload=(seed % 13, 4),
        )
        infected = bool(attempt.injected)
        host_cost = 0.0
        quality = "structure_null"
        notes.append("structure_null_blocks_or_zeros_cost")

    body = {
        "seed": seed,
        "arm": arm,
        "host_cost": host_cost,
        "infected": infected,
        "resistance_quality": quality,
        "notes": notes,
        "virulence_optimized_for_humans": False,
    }
    return VirulenceArmOutcome(
        seed=seed,
        arm=arm,
        host_cost=host_cost,
        infected=infected,
        resistance_quality=quality,
        arm_digest=_digest_body(body),
        notes=tuple(notes),
    )


def run_virulence_resistance_quality_campaign(
    *,
    seeds: Sequence[int],
    request_claim_ceiling: str = "runtime_observation",
) -> VirulenceQualityResult:
    """Run qualitative vs quantitative resistance proxies with dual-null controls."""

    seed_tuple = _require_seeds(seeds)
    ceiling = str(request_claim_ceiling).strip().lower()
    if ceiling not in _ALLOWED_CEILINGS:
        raise ConfigurationError(
            "request_claim_ceiling must be runtime_observation or candidate_evidence."
        )

    outcomes = tuple(
        _run_arm(seed=seed, arm=arm) for seed in seed_tuple for arm in ARMS
    )
    by_arm: dict[str, list[float]] = {arm: [] for arm in ARMS}
    for item in outcomes:
        by_arm[item.arm].append(item.host_cost)

    def _mean(vals: list[float]) -> float:
        return sum(vals) / len(vals) if vals else 0.0

    qualitative = _mean(by_arm["qualitative_resistance_gate"])
    quantitative = _mean(by_arm["quantitative_steal_gradient"])
    content_null = _mean(by_arm["content_null_control"])
    structure_null = _mean(by_arm["structure_null_control"])

    # Hypothesis fails when nulls do not raise cost while quantitative does,
    # or qualitative gate blocks infection (cost ~ 0).
    hypothesis_supported = (
        quantitative > 0
        and qualitative > 0
        and content_null > 0
        and structure_null > 0
    )
    failure_parts: list[str] = []
    if qualitative <= 0:
        failure_parts.append("qualitative_gate")
    if content_null <= 0:
        failure_parts.append("content_null")
    if structure_null <= 0:
        failure_parts.append("structure_null")
    failure_reason = (
        ""
        if hypothesis_supported
        else "any_parasite_does_not_always_raise_host_cost_under_" + "_".join(failure_parts or ["controls"])
    )

    digests = {
        arm: _digest_body(
            {
                "arm": arm,
                "outcomes": [o.to_dict() for o in outcomes if o.arm == arm],
            }
        )
        for arm in ARMS
    }
    distinct = len(set(digests.values())) == len(ARMS)
    if ceiling == "candidate_evidence" and not distinct:
        raise ConfigurationError(
            "candidate_evidence refused: virulence-quality arms must produce distinct digests."
        )

    return VirulenceQualityResult(
        schema=SCHEMA,
        seeds=seed_tuple,
        arms=ARMS,
        arm_outcomes=outcomes,
        hypothesis=HYPOTHESIS,
        hypothesis_supported=hypothesis_supported,
        failure_reason=failure_reason,
        claim_ceiling=ceiling if distinct or ceiling == "runtime_observation" else "runtime_observation",
        arms_are_distinct=distinct,
        red_queen_proved=False,
        virulence_optimized_for_humans=False,
    )


__all__ = [
    "ARMS",
    "HYPOTHESIS",
    "SCHEMA",
    "VirulenceArmOutcome",
    "VirulenceQualityResult",
    "run_virulence_resistance_quality_campaign",
]
