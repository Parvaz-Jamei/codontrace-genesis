"""Zaman-style freeze / replay / reciprocal coevolution contrast (Phase 7).

Three *distinct* digital campaign arms (Zaman et al. 2014
doi:10.1371/journal.pbio.1002023 analogy):

- ``freeze_parasites`` — parasite tasks/payload frozen at t0; hosts update;
  frozen parasites inject against updated hosts.
- ``replay_parasite_schedule`` — a predetermined schedule of historical
  parasite snapshots is replayed; parasites do not adapt to contemporaneous
  hosts (schedule ≠ freeze, schedule ≠ reciprocal).
- ``reciprocal_coevolution`` — hosts and parasites both update each step
  from the other's repertoire (digital analogue only).

Host repertoire-richness analogue = task-set cardinality trajectory plus a
summary digest per arm. This module never claims proved complexity
emergence, Red Queen dynamics, CRISPR identity, phage therapy, vaccine
effect, epidemic forecast, BSL, intelligence, or major transition.
Does not modify ``engine.py``.
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
)

ZAMAN_ARMS = frozenset(
    {
        "freeze_parasites",
        "replay_parasite_schedule",
        "reciprocal_coevolution",
    }
)


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


def _mean(values: Sequence[float]) -> float:
    if not values:
        return 0.0
    return round(sum(values) / len(values), 10)


def _stdev(values: Sequence[float]) -> float:
    if len(values) < 2:
        return 0.0
    mean = sum(values) / len(values)
    var = sum((value - mean) ** 2 for value in values) / (len(values) - 1)
    return round(var**0.5, 10)


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


def _ensure_overlap(host_tasks: Sequence[str], parasite_tasks: Sequence[str]) -> tuple[str, ...]:
    host = list(host_tasks)
    parasite = list(parasite_tasks)
    if set(host) & set(parasite):
        return tuple(parasite)
    return tuple(dict.fromkeys([*parasite, host[0]]))


def _digest_body(body: Mapping[str, object]) -> str:
    return canonical_digest(canonical_payload(dict(body)))


def _require_zaman_arms(arms: Sequence[str] | None) -> tuple[str, ...]:
    if arms is None:
        return ("freeze_parasites", "replay_parasite_schedule", "reciprocal_coevolution")
    if not arms:
        raise ConfigurationError("zaman arms must be non-empty when provided.")
    out: list[str] = []
    seen: set[str] = set()
    for index, raw in enumerate(arms):
        if not isinstance(raw, str) or not raw.strip():
            raise ConfigurationError(f"arms[{index}] must be a non-empty string.")
        key = raw.strip().lower()
        if key not in ZAMAN_ARMS:
            raise ConfigurationError(
                f"arms[{index}] must be one of {sorted(ZAMAN_ARMS)}; got {raw!r}."
            )
        if key in seen:
            raise ConfigurationError(f"duplicate arm {key!r}.")
        seen.add(key)
        out.append(key)
    return tuple(out)


def _seed_bytes(seed: int, salt: str) -> bytes:
    return hashlib.sha256(f"{int(seed)}|{salt}".encode()).digest()


def _schedule_for_seed(seed: int, steps: int) -> tuple[tuple[tuple[str, ...], tuple[int, ...]], ...]:
    """Predetermined parasite (tasks, payload) schedule — not reciprocal."""

    if steps < 2:
        raise ConfigurationError("replay schedule needs at least 2 steps.")
    rows: list[tuple[tuple[str, ...], tuple[int, ...]]] = []
    for step in range(steps):
        tasks = _tasks_for_seed(seed + step * 17, f"parasite_sched_{step}", min(2, len(_TASK_CATALOG)))
        payload = tuple(int(b) for b in _seed_bytes(seed, f"sched_payload_{step}")[:3])
        rows.append((tasks, payload))
    return tuple(rows)


def _host_expand(
    current: Sequence[str],
    seed: int,
    step: int,
    *,
    under_parasite_pressure: bool,
    expansion_budget: int = 1,
) -> tuple[str, ...]:
    """Digital repertoire update: add up to ``expansion_budget`` tasks under pressure.

    Freeze arms use budget 1 (hosts evolve against a fixed parasite). Reciprocal
    arms use budget 2 when parasites co-adapt (digital Zaman analogue). Replay
    schedule uses pressure=False so cardinality stays flat. Never proves
    complexity emergence.
    """

    current_set = list(dict.fromkeys(t.strip().lower() for t in current))
    if not under_parasite_pressure:
        # Abiotic-like drift: permute order only; cardinality unchanged.
        if len(current_set) < 2:
            return tuple(current_set)
        digest = _seed_bytes(seed, f"host_drift_{step}")
        shift = digest[0] % len(current_set)
        return tuple(current_set[shift:] + current_set[:shift])
    budget = int(expansion_budget)
    if budget < 1:
        raise ConfigurationError("expansion_budget must be >= 1 under parasite pressure.")
    unused = [t for t in _TASK_CATALOG if t not in current_set]
    if not unused:
        return tuple(current_set)
    digest = _seed_bytes(seed, f"host_expand_{step}")
    added: list[str] = []
    for offset in range(min(budget, len(unused))):
        pick = unused[(digest[offset % len(digest)] + offset) % len(unused)]
        if pick not in current_set and pick not in added:
            added.append(pick)
    return tuple([*current_set, *added])


def _parasite_adapt(host_tasks: Sequence[str], seed: int, step: int) -> tuple[str, ...]:
    """Parasite repertoire tracks a subset of current host tasks (reciprocal)."""

    hosts = list(dict.fromkeys(t.strip().lower() for t in host_tasks))
    if not hosts:
        raise ConfigurationError("parasite adapt needs host tasks.")
    digest = _seed_bytes(seed, f"parasite_adapt_{step}")
    count = 1 + (digest[0] % min(2, len(hosts)))
    chosen: list[str] = []
    idx = 0
    while len(chosen) < count:
        pick = hosts[digest[idx % len(digest)] % len(hosts)]
        idx += 1
        if pick not in chosen:
            chosen.append(pick)
        if idx > 32:
            break
    if not chosen:
        chosen = [hosts[0]]
    return tuple(chosen)


@dataclass(frozen=True, slots=True)
class RepertoireSummary:
    """Host repertoire-richness analogue (task-set cardinality trajectory)."""

    final_richness: int
    mean_richness: float
    richness_trajectory: tuple[int, ...]
    mean_retained_cpu: float
    complexity_emergence_proved: bool

    def to_dict(self) -> dict[str, object]:
        body: dict[str, object] = {
            "final_richness": self.final_richness,
            "mean_richness": self.mean_richness,
            "richness_trajectory": list(self.richness_trajectory),
            "mean_retained_cpu": self.mean_retained_cpu,
            "complexity_emergence_proved": self.complexity_emergence_proved,
        }
        body["digest"] = _digest_body(body)
        return body


@dataclass(frozen=True, slots=True)
class ZamanSeedOutcome:
    seed: int
    arm: str
    repertoire: RepertoireSummary
    injected_hosts: int
    host_count: int
    final_host_tasks: tuple[str, ...]
    final_parasite_tasks: tuple[str, ...]
    notes: tuple[str, ...]

    def to_dict(self) -> dict[str, object]:
        body: dict[str, object] = {
            "seed": self.seed,
            "arm": self.arm,
            "repertoire": self.repertoire.to_dict(),
            "injected_hosts": self.injected_hosts,
            "host_count": self.host_count,
            "final_host_tasks": list(self.final_host_tasks),
            "final_parasite_tasks": list(self.final_parasite_tasks),
            "notes": list(self.notes),
        }
        body["digest"] = _digest_body(
            {k: body[k] for k in body if k != "digest"}
        )
        return body


@dataclass(frozen=True, slots=True)
class ZamanArmResult:
    arm: str
    seed_outcomes: tuple[ZamanSeedOutcome, ...]
    mean_final_richness: float
    mean_retained_cpu: float
    richness_stdev: float

    def to_dict(self) -> dict[str, object]:
        outcomes = [item.to_dict() for item in self.seed_outcomes]
        body: dict[str, object] = {
            "arm": self.arm,
            "seed_count": len(self.seed_outcomes),
            "mean_final_richness": self.mean_final_richness,
            "mean_retained_cpu": self.mean_retained_cpu,
            "richness_stdev": self.richness_stdev,
            "seed_outcomes": outcomes,
            "seed_digests": [str(item["digest"]) for item in outcomes],
            "complexity_emergence_proved": False,
        }
        body["digest"] = _digest_body({k: body[k] for k in body if k != "digest"})
        return body


@dataclass(frozen=True, slots=True)
class ZamanCampaignResult:
    """Three-arm Zaman contrast with per-arm digests; complexity unproved."""

    schema: str
    seeds: tuple[int, ...]
    arms: tuple[str, ...]
    steps: int
    steal_fraction: float
    host_count: int
    arm_results: tuple[ZamanArmResult, ...]
    claim_ceiling: str
    complexity_emergence_proved: bool
    red_queen_proved: bool
    arms_are_distinct: bool

    def to_dict(self) -> dict[str, object]:
        arm_dicts = [item.to_dict() for item in self.arm_results]
        body: dict[str, object] = {
            "schema": self.schema,
            "seeds": list(self.seeds),
            "arms": list(self.arms),
            "steps": self.steps,
            "steal_fraction": self.steal_fraction,
            "host_count": self.host_count,
            "arm_results": arm_dicts,
            "arm_digests": {str(item["arm"]): str(item["digest"]) for item in arm_dicts},
            "claim_ceiling": self.claim_ceiling,
            "complexity_emergence_proved": self.complexity_emergence_proved,
            "red_queen_proved": self.red_queen_proved,
            "arms_are_distinct": self.arms_are_distinct,
            "raises_claim_ladder": False,
            "engine_infection_physics": "not_in_engine_core",
            "zaman_citation": "doi:10.1371/journal.pbio.1002023",
            "zaman_scope": "digital_analogue_only",
        }
        body["campaign_digest"] = _digest_body(
            {k: body[k] for k in body if k not in {"campaign_digest", "digest"}}
        )
        body["digest"] = body["campaign_digest"]
        return body


def _run_freeze_parasites(
    *,
    seed: int,
    host_count: int,
    steal_fraction: float,
    steps: int,
) -> ZamanSeedOutcome:
    """Freeze parasite at t0; hosts update across steps; replay frozen inject."""

    host_tasks = _tasks_for_seed(seed, "host_t0", min(3, len(_TASK_CATALOG)))
    parasite_tasks = _ensure_overlap(
        host_tasks, _tasks_for_seed(seed, "parasite_freeze", min(2, len(_TASK_CATALOG)))
    )
    frozen_payload = _payload_for_seed(seed, length=4)
    trajectory: list[int] = [len(host_tasks)]
    notes = ["parasite_frozen_at_t0"]
    cpu_samples: list[float] = []

    for step in range(1, steps + 1):
        host_tasks = _host_expand(
            host_tasks, seed, step, under_parasite_pressure=True
        )
        # Keep overlap with frozen parasite so inject remains possible.
        if not (set(host_tasks) & set(parasite_tasks)):
            host_tasks = tuple(dict.fromkeys([*host_tasks, parasite_tasks[0]]))
        trajectory.append(len(set(host_tasks)))
        env = HostParasiteEnv(steal_fraction=steal_fraction)
        injected = 0
        for index in range(host_count):
            env.add_host(f"H{index}", host_tasks)
            attempt = env.try_horizontal_inject(
                host_id=f"H{index}",
                parasite_id=f"P_frozen_{index}",
                parasite_tasks=parasite_tasks,
                payload=frozen_payload,
            )
            if attempt.injected:
                injected += 1
        cpu_samples.append(env.population_outcome_score())
        notes.append(f"step_{step}_injected_{injected}")

    repertoire = RepertoireSummary(
        final_richness=trajectory[-1],
        mean_richness=_mean([float(v) for v in trajectory]),
        richness_trajectory=tuple(trajectory),
        mean_retained_cpu=_mean(cpu_samples),
        complexity_emergence_proved=False,
    )
    return ZamanSeedOutcome(
        seed=seed,
        arm="freeze_parasites",
        repertoire=repertoire,
        injected_hosts=injected,
        host_count=host_count,
        final_host_tasks=tuple(host_tasks),
        final_parasite_tasks=tuple(parasite_tasks),
        notes=tuple(notes),
    )


def _run_replay_parasite_schedule(
    *,
    seed: int,
    host_count: int,
    steal_fraction: float,
    steps: int,
) -> ZamanSeedOutcome:
    """Replay a fixed parasite history schedule; parasites do not co-adapt."""

    schedule = _schedule_for_seed(seed, steps)
    host_tasks = _tasks_for_seed(seed, "host_replay_t0", min(3, len(_TASK_CATALOG)))
    trajectory: list[int] = [len(host_tasks)]
    notes = ["parasite_schedule_predetermined", f"schedule_steps_{len(schedule)}"]
    cpu_samples: list[float] = []
    last_parasite = schedule[0][0]
    injected = 0

    for step_index, (parasite_tasks, payload) in enumerate(schedule):
        # Hosts update without reciprocal parasite pressure (schedule is fixed).
        host_tasks = _host_expand(
            host_tasks, seed, step_index + 1, under_parasite_pressure=False
        )
        parasite_tasks = _ensure_overlap(host_tasks, parasite_tasks)
        last_parasite = parasite_tasks
        trajectory.append(len(set(host_tasks)))
        env = HostParasiteEnv(steal_fraction=steal_fraction)
        injected = 0
        for index in range(host_count):
            env.add_host(f"H{index}", host_tasks)
            attempt = env.try_horizontal_inject(
                host_id=f"H{index}",
                parasite_id=f"P_sched_{step_index}_{index}",
                parasite_tasks=parasite_tasks,
                payload=payload,
            )
            if attempt.injected:
                injected += 1
        cpu_samples.append(env.population_outcome_score())
        notes.append(f"sched_step_{step_index}_injected_{injected}")

    repertoire = RepertoireSummary(
        final_richness=trajectory[-1],
        mean_richness=_mean([float(v) for v in trajectory]),
        richness_trajectory=tuple(trajectory),
        mean_retained_cpu=_mean(cpu_samples),
        complexity_emergence_proved=False,
    )
    return ZamanSeedOutcome(
        seed=seed,
        arm="replay_parasite_schedule",
        repertoire=repertoire,
        injected_hosts=injected,
        host_count=host_count,
        final_host_tasks=tuple(host_tasks),
        final_parasite_tasks=tuple(last_parasite),
        notes=tuple(notes),
    )


def _run_reciprocal_coevolution(
    *,
    seed: int,
    host_count: int,
    steal_fraction: float,
    steps: int,
) -> ZamanSeedOutcome:
    """Both sides update each step from the other's repertoire (digital only)."""

    host_tasks = _tasks_for_seed(seed, "host_recip_t0", min(3, len(_TASK_CATALOG)))
    parasite_tasks = _parasite_adapt(host_tasks, seed, 0)
    trajectory: list[int] = [len(host_tasks)]
    notes = ["reciprocal_host_and_parasite_update"]
    cpu_samples: list[float] = []
    injected = 0

    for step in range(1, steps + 1):
        host_tasks = _host_expand(
            host_tasks,
            seed,
            step,
            under_parasite_pressure=True,
            expansion_budget=2,
        )
        parasite_tasks = _parasite_adapt(host_tasks, seed, step)
        trajectory.append(len(set(host_tasks)))
        env = HostParasiteEnv(steal_fraction=steal_fraction)
        injected = 0
        for index in range(host_count):
            env.add_host(f"H{index}", host_tasks)
            attempt = env.try_horizontal_inject(
                host_id=f"H{index}",
                parasite_id=f"P_recip_{step}_{index}",
                parasite_tasks=parasite_tasks,
                payload=_payload_for_seed(seed + step, length=3),
            )
            if attempt.injected:
                injected += 1
        cpu_samples.append(env.population_outcome_score())
        notes.append(f"recip_step_{step}_richness_{trajectory[-1]}")

    repertoire = RepertoireSummary(
        final_richness=trajectory[-1],
        mean_richness=_mean([float(v) for v in trajectory]),
        richness_trajectory=tuple(trajectory),
        mean_retained_cpu=_mean(cpu_samples),
        complexity_emergence_proved=False,
    )
    return ZamanSeedOutcome(
        seed=seed,
        arm="reciprocal_coevolution",
        repertoire=repertoire,
        injected_hosts=injected,
        host_count=host_count,
        final_host_tasks=tuple(host_tasks),
        final_parasite_tasks=tuple(parasite_tasks),
        notes=tuple(notes),
    )


_ARM_RUNNERS = {
    "freeze_parasites": _run_freeze_parasites,
    "replay_parasite_schedule": _run_replay_parasite_schedule,
    "reciprocal_coevolution": _run_reciprocal_coevolution,
}


def run_zaman_three_arm_campaign(
    *,
    seeds: Sequence[int],
    arms: Sequence[str] | None = None,
    steps: int = 3,
    steal_fraction: float = DEFAULT_STEAL_FRACTION,
    host_count: int = 3,
    request_claim_ceiling: str = "runtime_observation",
) -> ZamanCampaignResult:
    """Run freeze ≠ replay ≠ reciprocal contrast with repertoire digests.

    Ceiling max is ``candidate_evidence`` when the three arms produce distinct
    digests. Never sets ``complexity_emergence_proved`` or ``red_queen_proved``.
    """

    seed_tuple = _require_seeds(seeds)
    arm_tuple = _require_zaman_arms(arms)
    if isinstance(steps, bool) or not isinstance(steps, int) or steps < 2:
        raise ConfigurationError("steps must be an int >= 2.")
    if steps > 16:
        raise ConfigurationError("steps must be <= 16 for the digital Zaman assay.")
    if isinstance(host_count, bool) or not isinstance(host_count, int) or host_count < 1:
        raise ConfigurationError("host_count must be a positive int.")
    if host_count > 64:
        raise ConfigurationError("host_count must be <= 64.")
    steal = float(steal_fraction)
    if steal != steal or steal < 0.0 or steal > 1.0:
        raise ConfigurationError("steal_fraction must be in [0, 1].")
    if not isinstance(request_claim_ceiling, str) or not request_claim_ceiling.strip():
        raise ConfigurationError("request_claim_ceiling is required.")
    ceiling_req = request_claim_ceiling.strip().lower()
    allowed = frozenset({"runtime_observation", "candidate_evidence"})
    if ceiling_req not in allowed:
        raise ConfigurationError(
            f"request_claim_ceiling must be one of {sorted(allowed)}; "
            f"ceilings above candidate_evidence are refused (got {request_claim_ceiling!r})."
        )

    arm_results: list[ZamanArmResult] = []
    for arm in arm_tuple:
        runner = _ARM_RUNNERS[arm]
        outcomes = [
            runner(
                seed=seed,
                host_count=host_count,
                steal_fraction=steal,
                steps=steps,
            )
            for seed in seed_tuple
        ]
        richness = [float(item.repertoire.final_richness) for item in outcomes]
        cpu = [item.repertoire.mean_retained_cpu for item in outcomes]
        arm_results.append(
            ZamanArmResult(
                arm=arm,
                seed_outcomes=tuple(outcomes),
                mean_final_richness=_mean(richness),
                mean_retained_cpu=_mean(cpu),
                richness_stdev=_stdev(richness),
            )
        )

    digests = [item.to_dict()["digest"] for item in arm_results]
    arms_distinct = len(set(digests)) == len(digests) and len(digests) >= 2
    if ceiling_req == "candidate_evidence" and not arms_distinct:
        raise ConfigurationError(
            "candidate_evidence refused: Zaman arms must produce distinct digests "
            "(freeze ≠ replay ≠ reciprocal)."
        )
    claim_ceiling = (
        ceiling_req
        if ceiling_req == "runtime_observation" or arms_distinct
        else "runtime_observation"
    )
    return ZamanCampaignResult(
        schema="host_parasite_zaman_three_arm_v1",
        seeds=seed_tuple,
        arms=arm_tuple,
        steps=steps,
        steal_fraction=steal,
        host_count=host_count,
        arm_results=tuple(arm_results),
        claim_ceiling=claim_ceiling,
        complexity_emergence_proved=False,
        red_queen_proved=False,
        arms_are_distinct=arms_distinct,
    )


__all__ = [
    "ZAMAN_ARMS",
    "RepertoireSummary",
    "ZamanArmResult",
    "ZamanCampaignResult",
    "ZamanSeedOutcome",
    "run_zaman_three_arm_campaign",
]
