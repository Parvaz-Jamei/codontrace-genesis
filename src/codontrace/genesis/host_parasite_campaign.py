"""Multi-seed host–parasite ClaimGate campaign runner (outside engine.py).

Deterministic arms for digital coevolution audit:

- intact, content-null, structure-null, dual-null
- abiotic-only (hosts without parasites)
- freeze/replay parasites (Zaman 2014 analogy: frozen parasite task/payload
  list reused while hosts update)

Canonical digests are emitted per arm and for the whole campaign. This module
does not modify ``engine.py``, does not prove Red Queen dynamics, and does not
certify clinical, CRISPR-identity, phage-therapy, vaccine, epidemic, or BSL
claims. Scores are digital scope only for ClaimGate labeling.
"""

from __future__ import annotations

import hashlib
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from codontrace.errors import ConfigurationError
from codontrace.genesis.canonical import canonical_digest, canonical_payload
from codontrace.genesis.host_parasite_env import (
    DEFAULT_STEAL_FRACTION,
    HostParasiteEnv,
    dual_null_template,
)

CAMPAIGN_ARMS = frozenset(
    {
        "intact",
        "content_null",
        "structure_null",
        "dual_null",
        "abiotic_only",
        "freeze_replay_parasites",
    }
)

_NULL_ARM_TO_KIND = {
    "intact": "none",
    "content_null": "content_null",
    "structure_null": "structure_null",
    "dual_null": "dual_null",
}

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


def _digest_body(body: Mapping[str, object]) -> str:
    return canonical_digest(canonical_payload(dict(body)))


def _seed_bytes(seed: int, salt: str) -> bytes:
    raw = f"{int(seed)}|{salt}".encode()
    return hashlib.sha256(raw).digest()


def _tasks_for_seed(seed: int, role: str, count: int) -> tuple[str, ...]:
    if count < 1:
        raise ConfigurationError(f"{role} task count must be >= 1.")
    digest = _seed_bytes(seed, role)
    chosen: list[str] = []
    seen: set[str] = set()
    idx = 0
    while len(chosen) < count:
        pick = _TASK_CATALOG[digest[idx % len(digest)] % len(_TASK_CATALOG)]
        idx += 1
        if pick in seen:
            # Advance deterministically through catalog for uniqueness.
            pick = _TASK_CATALOG[(idx + seed) % len(_TASK_CATALOG)]
            if pick in seen:
                continue
        seen.add(pick)
        chosen.append(pick)
        if len(seen) == len(_TASK_CATALOG) and len(chosen) < count:
            break
    if not chosen:
        raise ConfigurationError("could not derive tasks for seed.")
    return tuple(chosen)


def _payload_for_seed(seed: int, length: int = 3) -> tuple[int, ...]:
    digest = _seed_bytes(seed, "payload")
    return tuple(int(digest[i]) for i in range(length))


def _require_seeds(seeds: Sequence[int]) -> tuple[int, ...]:
    if not seeds:
        raise ConfigurationError("campaign requires at least one seed.")
    out: list[int] = []
    seen: set[int] = set()
    for index, seed in enumerate(seeds):
        if isinstance(seed, bool) or not isinstance(seed, int):
            raise ConfigurationError(f"seeds[{index}] must be an int.")
        if seed < 0:
            raise ConfigurationError(f"seeds[{index}] must be non-negative.")
        if seed in seen:
            raise ConfigurationError(f"duplicate seed {seed}.")
        seen.add(seed)
        out.append(seed)
    return tuple(out)


def _require_arms(arms: Sequence[str] | None) -> tuple[str, ...]:
    if arms is None:
        return tuple(sorted(CAMPAIGN_ARMS))
    if not arms:
        raise ConfigurationError("campaign arms must be non-empty when provided.")
    out: list[str] = []
    seen: set[str] = set()
    for index, raw in enumerate(arms):
        if not isinstance(raw, str) or not raw.strip():
            raise ConfigurationError(f"arms[{index}] must be a non-empty string.")
        key = raw.strip().lower()
        if key not in CAMPAIGN_ARMS:
            raise ConfigurationError(
                f"arms[{index}] must be one of {sorted(CAMPAIGN_ARMS)}; got {raw!r}."
            )
        if key in seen:
            raise ConfigurationError(f"duplicate arm {key!r}.")
        seen.add(key)
        out.append(key)
    return tuple(out)


@dataclass(frozen=True, slots=True)
class SeedArmOutcome:
    """One seed × arm digital outcome with a canonical digest."""

    seed: int
    arm: str
    mean_retained_cpu: float
    injected_hosts: int
    host_count: int
    host_tasks: tuple[str, ...]
    parasite_tasks: tuple[str, ...]
    parasite_payload: tuple[int, ...]
    notes: tuple[str, ...]

    def to_dict(self) -> dict[str, object]:
        body: dict[str, object] = {
            "seed": self.seed,
            "arm": self.arm,
            "mean_retained_cpu": self.mean_retained_cpu,
            "injected_hosts": self.injected_hosts,
            "host_count": self.host_count,
            "host_tasks": list(self.host_tasks),
            "parasite_tasks": list(self.parasite_tasks),
            "parasite_payload": list(self.parasite_payload),
            "notes": list(self.notes),
        }
        body["digest"] = _digest_body({k: body[k] for k in body if k != "digest"})
        return body


@dataclass(frozen=True, slots=True)
class ArmCampaignResult:
    """Aggregated multi-seed result for one campaign arm."""

    arm: str
    seed_outcomes: tuple[SeedArmOutcome, ...]
    mean_score: float
    score_stdev: float
    injected_fraction: float

    def to_dict(self) -> dict[str, object]:
        outcomes = [item.to_dict() for item in self.seed_outcomes]
        body: dict[str, object] = {
            "arm": self.arm,
            "seed_count": len(self.seed_outcomes),
            "mean_score": self.mean_score,
            "score_stdev": self.score_stdev,
            "injected_fraction": self.injected_fraction,
            "seed_outcomes": outcomes,
            "seed_digests": [str(item["digest"]) for item in outcomes],
        }
        body["digest"] = _digest_body({k: body[k] for k in body if k != "digest"})
        return body


@dataclass(frozen=True, slots=True)
class HostParasiteCampaignResult:
    """Full multi-arm campaign with per-arm and whole-campaign digests."""

    schema: str
    seeds: tuple[int, ...]
    arms: tuple[str, ...]
    steal_fraction: float
    host_count: int
    arm_results: tuple[ArmCampaignResult, ...]
    falsification_rules_passed: bool
    claim_ceiling: str
    red_queen_proved: bool

    def to_dict(self) -> dict[str, object]:
        arm_dicts = [item.to_dict() for item in self.arm_results]
        body: dict[str, object] = {
            "schema": self.schema,
            "seeds": list(self.seeds),
            "arms": list(self.arms),
            "steal_fraction": self.steal_fraction,
            "host_count": self.host_count,
            "arm_results": arm_dicts,
            "arm_digests": {str(item["arm"]): str(item["digest"]) for item in arm_dicts},
            "falsification_rules_passed": self.falsification_rules_passed,
            "claim_ceiling": self.claim_ceiling,
            "red_queen_proved": self.red_queen_proved,
            "raises_claim_ladder": False,
            "engine_infection_physics": "not_in_engine_core",
            "zaman_freeze_replay_analogy": "freeze_replay_parasites" in self.arms,
        }
        body["campaign_digest"] = _digest_body(
            {k: body[k] for k in body if k not in {"campaign_digest", "digest"}}
        )
        body["digest"] = body["campaign_digest"]
        return body


def _mean(values: Sequence[float]) -> float:
    if not values:
        return 0.0
    return round(sum(values) / len(values), 10)


def _stdev(values: Sequence[float]) -> float:
    if len(values) < 2:
        return 0.0
    mean = sum(values) / len(values)
    var = sum((value - mean) ** 2 for value in values) / (len(values) - 1)
    return float(round(var**0.5, 10))


def _ensure_overlap(host_tasks: Sequence[str], parasite_tasks: Sequence[str]) -> tuple[str, ...]:
    """Guarantee at least one shared task so intact/freeze arms can infect."""

    host = list(host_tasks)
    parasite = list(parasite_tasks)
    if set(host) & set(parasite):
        return tuple(parasite)
    # Force overlap by grafting the first host task onto the parasite set.
    return tuple(dict.fromkeys([*parasite, host[0]]))


def _run_standard_arm(
    *,
    arm: str,
    seed: int,
    host_count: int,
    steal_fraction: float,
) -> SeedArmOutcome:
    host_tasks = _tasks_for_seed(seed, "host", min(3, len(_TASK_CATALOG)))
    parasite_tasks = _ensure_overlap(
        host_tasks, _tasks_for_seed(seed, "parasite", min(2, len(_TASK_CATALOG)))
    )
    payload = _payload_for_seed(seed)
    notes: list[str] = []

    if arm == "abiotic_only":
        env = HostParasiteEnv(steal_fraction=steal_fraction)
        for index in range(host_count):
            env.add_host(f"H{index}", host_tasks)
        notes.append("no_parasite_inject")
        return SeedArmOutcome(
            seed=seed,
            arm=arm,
            mean_retained_cpu=env.population_outcome_score(),
            injected_hosts=0,
            host_count=host_count,
            host_tasks=host_tasks,
            parasite_tasks=parasite_tasks,
            parasite_payload=(),
            notes=tuple(notes),
        )

    null_kind = _NULL_ARM_TO_KIND[arm]
    env = HostParasiteEnv(
        steal_fraction=steal_fraction,
        null_template=dual_null_template(null_kind),
    )
    injected = 0
    for index in range(host_count):
        env.add_host(f"H{index}", host_tasks)
        attempt = env.try_horizontal_inject(
            host_id=f"H{index}",
            parasite_id=f"P{index}",
            parasite_tasks=parasite_tasks,
            payload=payload,
        )
        if attempt.injected:
            injected += 1
        notes.append(attempt.reason)
    return SeedArmOutcome(
        seed=seed,
        arm=arm,
        mean_retained_cpu=env.population_outcome_score(),
        injected_hosts=injected,
        host_count=host_count,
        host_tasks=host_tasks,
        parasite_tasks=parasite_tasks,
        parasite_payload=payload if null_kind != "content_null" else (),
        notes=tuple(notes),
    )


def _run_freeze_replay_arm(
    *,
    seed: int,
    host_count: int,
    steal_fraction: float,
) -> SeedArmOutcome:
    """Freeze parasite tasks/payload, then replay against updated host tasks.

    Zaman-style analogy: parasite history is held fixed while hosts update.
    Digital scope only; does not prove parasite-driven evolvability.
    """

    host_tasks_t0 = _tasks_for_seed(seed, "host_t0", min(3, len(_TASK_CATALOG)))
    parasite_tasks = _ensure_overlap(
        host_tasks_t0, _tasks_for_seed(seed, "parasite_freeze", min(2, len(_TASK_CATALOG)))
    )
    frozen_payload = _payload_for_seed(seed, length=4)
    # Hosts update to a new repertoire that still overlaps the frozen parasite.
    host_tasks_t1 = _tasks_for_seed(seed, "host_t1", min(3, len(_TASK_CATALOG)))
    if not (set(host_tasks_t1) & set(parasite_tasks)):
        host_tasks_t1 = tuple(dict.fromkeys([*host_tasks_t1, parasite_tasks[0]]))

    env = HostParasiteEnv(steal_fraction=steal_fraction)
    injected = 0
    notes = ["parasite_frozen_from_t0", "replay_on_updated_hosts"]
    for index in range(host_count):
        env.add_host(f"H{index}", host_tasks_t1)
        attempt = env.try_horizontal_inject(
            host_id=f"H{index}",
            parasite_id=f"P_frozen_{index}",
            parasite_tasks=parasite_tasks,
            payload=frozen_payload,
        )
        if attempt.injected:
            injected += 1
        notes.append(attempt.reason)
    return SeedArmOutcome(
        seed=seed,
        arm="freeze_replay_parasites",
        mean_retained_cpu=env.population_outcome_score(),
        injected_hosts=injected,
        host_count=host_count,
        host_tasks=host_tasks_t1,
        parasite_tasks=parasite_tasks,
        parasite_payload=frozen_payload,
        notes=tuple(notes),
    )


def _evaluate_falsification(arm_results: Sequence[ArmCampaignResult]) -> bool:
    """Falsification rules for candidate_evidence ceiling.

    Require intact vs at least one null/abiotic arm with a mean-score *or*
    injected-fraction difference (steal_fraction=0 can tie scores while nulls
    still change injection). When freeze/replay and abiotic-only both exist,
    their arm digests must differ.
    """

    by_arm = {item.arm: item for item in arm_results}
    if "intact" not in by_arm:
        return False
    intact = by_arm["intact"]
    contrast_arms = (
        "content_null",
        "structure_null",
        "dual_null",
        "abiotic_only",
    )
    differed = False
    for name in contrast_arms:
        other = by_arm.get(name)
        if other is None:
            continue
        if other.mean_score != intact.mean_score:
            differed = True
            break
        if other.injected_fraction != intact.injected_fraction:
            differed = True
            break
    if not differed:
        return False
    if "freeze_replay_parasites" in by_arm and "abiotic_only" in by_arm:
        freeze_digest = by_arm["freeze_replay_parasites"].to_dict()["digest"]
        abiotic_digest = by_arm["abiotic_only"].to_dict()["digest"]
        if freeze_digest == abiotic_digest:
            return False
    return True


def run_host_parasite_campaign(
    *,
    seeds: Sequence[int],
    arms: Sequence[str] | None = None,
    steal_fraction: float = DEFAULT_STEAL_FRACTION,
    host_count: int = 3,
    request_claim_ceiling: str = "runtime_observation",
) -> HostParasiteCampaignResult:
    """Run a deterministic multi-seed multi-arm campaign outside engine.py.

    ``request_claim_ceiling`` may be ``runtime_observation`` or
    ``candidate_evidence``. Higher ceilings are refused. ``candidate_evidence``
    is granted only when falsification rules pass (intact differs from at least
    one null/abiotic arm; digests are distinct where required).
    """

    seed_tuple = _require_seeds(seeds)
    arm_tuple = _require_arms(arms)
    if isinstance(host_count, bool) or not isinstance(host_count, int) or host_count < 1:
        raise ConfigurationError("host_count must be a positive int.")
    if host_count > 64:
        raise ConfigurationError("host_count must be <= 64 for the digital campaign.")
    steal = float(steal_fraction)
    if steal != steal or steal < 0.0 or steal > 1.0:
        raise ConfigurationError("steal_fraction must be in [0, 1].")
    if not isinstance(request_claim_ceiling, str) or not request_claim_ceiling.strip():
        raise ConfigurationError("request_claim_ceiling is required.")
    ceiling_req = request_claim_ceiling.strip().lower()
    allowed_ceilings = frozenset({"runtime_observation", "candidate_evidence"})
    if ceiling_req not in allowed_ceilings:
        raise ConfigurationError(
            f"request_claim_ceiling must be one of {sorted(allowed_ceilings)}; "
            f"ceilings above candidate_evidence are refused (got {request_claim_ceiling!r})."
        )

    arm_results: list[ArmCampaignResult] = []
    for arm in arm_tuple:
        outcomes: list[SeedArmOutcome] = []
        for seed in seed_tuple:
            if arm == "freeze_replay_parasites":
                outcomes.append(
                    _run_freeze_replay_arm(
                        seed=seed,
                        host_count=host_count,
                        steal_fraction=steal,
                    )
                )
            else:
                outcomes.append(
                    _run_standard_arm(
                        arm=arm,
                        seed=seed,
                        host_count=host_count,
                        steal_fraction=steal,
                    )
                )
        scores = [item.mean_retained_cpu for item in outcomes]
        injected_total = sum(item.injected_hosts for item in outcomes)
        host_total = sum(item.host_count for item in outcomes)
        arm_results.append(
            ArmCampaignResult(
                arm=arm,
                seed_outcomes=tuple(outcomes),
                mean_score=_mean(scores),
                score_stdev=_stdev(scores),
                injected_fraction=round(injected_total / host_total, 10) if host_total else 0.0,
            )
        )

    falsification_ok = _evaluate_falsification(arm_results)
    if ceiling_req == "candidate_evidence" and not falsification_ok:
        raise ConfigurationError(
            "candidate_evidence refused: falsification rules did not pass "
            "(intact must differ from a null/abiotic arm; arm digests must be distinct)."
        )
    claim_ceiling = ceiling_req if (
        ceiling_req == "runtime_observation" or falsification_ok
    ) else "runtime_observation"

    return HostParasiteCampaignResult(
        schema="host_parasite_campaign_v1",
        seeds=seed_tuple,
        arms=arm_tuple,
        steal_fraction=steal,
        host_count=host_count,
        arm_results=tuple(arm_results),
        falsification_rules_passed=falsification_ok,
        claim_ceiling=claim_ceiling,
        red_queen_proved=False,
    )


__all__ = [
    "CAMPAIGN_ARMS",
    "ArmCampaignResult",
    "HostParasiteCampaignResult",
    "SeedArmOutcome",
    "run_host_parasite_campaign",
]
