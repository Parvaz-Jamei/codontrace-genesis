"""Phase I collective-intelligence *evidence* harnesses for CodonTrace Genesis.

Measurement-first engineering after Phase H: heldout unfamiliar-partner
generalization, evolved (not assigned) division of labor, multilevel selection
that can change evolutionary *outcome*, and an export-of-fitness scaffold.

None of this auto-sets ClaimGate flags. Smoke runs never earn flags.
``collective_intelligence`` / ``intelligence`` / AGI stay blocked.
``major_transition_in_individuality`` stays False unless every Michod-style
criterion is actually met (the scaffold does not meet them).

Claim ceiling: ``runtime_observation``. Group fitness is not intelligence.
This is a heritable two-task analog (Goldsby / Gorelick / Okasha / Michod),
not Avida C++ and not a 50-replicate PNAS experiment.
"""

from __future__ import annotations

import hashlib
import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Protocol

from codontrace._types import JsonValue
from codontrace.errors import ConfigurationError
from codontrace.genesis.canonical import canonical_digest, require_finite_float
from codontrace.genesis.claim_gate import (
    ClaimDecision,
    ClaimRequest,
    ScientificClaimGate,
)
from codontrace.genesis.generalization import (
    HeldoutPartnerEvaluationProtocol,
    HeldoutPartnerEvaluationRecord,
)
from codontrace.genesis.phase_h import (
    _CANDIDATE_FLAGS,
    _CLAIM_CEILING,
    _FORBIDDEN,
    RESEARCH_SEED_COUNT,
    SMOKE_SEED_COUNT,
    CollectiveIntelligenceCandidateChecklist,
    CommunicationAblationCampaign,
    _assert_ci_blocked,
    _cohens_d,
    _mean,
    collective_intelligence_candidate_checklist,
)

RESEARCH_GENERATION_COUNT = 20
SMOKE_GENERATION_COUNT = 6
MEASURED_RUNTIME = "measured_runtime_observation"
GAP_NOT_RUN = "not_run"
TASK_A = "A"
TASK_B = "B"
SPECIALIST_A_CUTOFF = 0.35
SPECIALIST_B_CUTOFF = 0.65
TASK_A_YIELD = 1.0
TASK_B_YIELD = 0.65
SWITCH_COST = 0.5
PAIR_BONUS = 3.0
DEFAULT_GROUP_SIZE = 4
DEFAULT_N_GROUPS = 8
SMOKE_N_GROUPS = 4
MUTATION_SIGMA = 0.15
MLS_KEEP_FRACTION = 0.5
NMI_SPECIALIZATION_THRESHOLD = 0.2
ABLATION_DROP_EPSILON = 1e-9
LIFETIME_TASK_SAMPLES = 4
MONOCULTURE_A_FRACTION = 0.75
MIXED_ROLE_FRACTION = 0.25

LITERATURE_CHECKLIST: tuple[tuple[str, str], ...] = (
    (
        "goldsby_2012_heldout_and_isolation",
        "Goldsby et al. PNAS 2012 doi:10.1073/pnas.1202233109: task-switching "
        "costs promote evolved DoL and isolation failure. Phase I evolves a "
        "heritable preference, not CPU-cycle specialists at 50 replicates.",
    ),
    (
        "gorelick_2004_nmi_dol",
        "Gorelick et al. 2004 Integr Comp Biol doi:10.1093/icb/44.5.345: "
        "normalized mutual information as a DoL statistic. Phase I computes "
        "an analog on evolved task choices.",
    ),
    (
        "okasha_2006_mls1_mls2",
        "Okasha 2006 Evolution and the Levels of Selection: MLS1 fitness "
        "accounting vs MLS2 evolutionary outcome (which strategy/lineage "
        "wins). Phase I compares majority strategy under group vs organism "
        "selection — not a rank table.",
    ),
    (
        "michod_2007_export_of_fitness",
        "Michod et al. PNAS 2007 doi:10.1073/pnas.0701482104: export-of-fitness "
        "and conflict suppression. Phase I records a scaffold; "
        "major_transition_in_individuality stays False.",
    ),
    (
        "chaturvedi_2026_mls_roles",
        "arXiv 2604.00810: MLS can maintain role mix. This two-task analog is "
        "not that coupled-channel ecology.",
    ),
)

EARNABLE_FLAG_SOURCES: tuple[tuple[str, str], ...] = (
    (
        "heldout_protocol",
        "HeldoutUnfamiliarPartnerCampaign at research seed/generation scale "
        "with distinct familiar vs unfamiliar partner digests and clean leakage",
    ),
    (
        "familiar_partner_protocol",
        "HeldoutUnfamiliarPartnerCampaign familiar-partner evaluation records",
    ),
    (
        "unfamiliar_partner_protocol",
        "HeldoutUnfamiliarPartnerCampaign unfamiliar-partner evaluation records",
    ),
    (
        "real_partner_event",
        "HeldoutUnfamiliarPartnerCampaign non-empty partner interaction records",
    ),
    (
        "role_complementarity",
        "EvolvedDivisionOfLaborCampaign: evolved (not assigned) roles, NMI, "
        "ablation payoff drop, research scale",
    ),
    (
        "collective_coordination",
        "EvolvedDivisionOfLaborCampaign: coordination/complementarity pays "
        "under ablation, research scale",
    ),
    (
        "non_capsule_cooperation",
        "EvolvedDivisionOfLaborCampaign: no capsules; joint group payoff with "
        "ablation drop, research scale",
    ),
    (
        "ablation_result",
        "EvolvedDivisionOfLaborCampaign, research-scale "
        "CommunicationAblationCampaign, or research-scale Phase K "
        "EvolvedCoordinationCampaign (Phase L evidence feed) with a measured "
        "payoff drop; never from smoke; never auto-set",
    ),
    (
        "collective_report_digest",
        "Any Phase I campaign digest at research scale (not smoke)",
    ),
    (
        "replay_verification",
        "Independent digest re-execution (Phase J DigestReplayVerification) at "
        "research scale when captured vs replayed campaign digests match. Never "
        "from Phase I harnesses alone, never from smoke, never faked.",
    ),
)


class ReplayVerificationLike(Protocol):
    """Duck type for Phase J ``DigestReplayVerification``. Avoids a circular import."""

    def earns_replay_verification(self) -> bool: ...


class CoordinationAblationLike(Protocol):
    """Duck type for Phase K ``EvolvedCoordinationCampaign``. Avoids a circular import."""

    seeds: Sequence[int]
    generations: int
    mean_ablation_drop: float


def _resolve_group_count(n_groups: int | None, *, smoke: bool) -> int:
    if n_groups is not None:
        return int(n_groups)
    return SMOKE_N_GROUPS if smoke else DEFAULT_N_GROUPS


def default_research_seeds(seed_count: int = RESEARCH_SEED_COUNT) -> tuple[int, ...]:
    """Deterministic seed tuple. Research default is 12; smoke may pass 2."""

    count = int(seed_count)
    if count < 2:
        raise ConfigurationError("Phase I seed_count must be >= 2.")
    return tuple(range(11, 11 + count))


def _resolve_seeds(
    seeds: Sequence[int] | None,
    seed_count: int | None,
    *,
    default_count: int,
) -> tuple[int, ...]:
    if seeds is not None:
        resolved = tuple(int(item) for item in seeds)
        if len(resolved) < 2:
            raise ConfigurationError("Phase I campaigns require at least two seeds.")
        return resolved
    return default_research_seeds(default_count if seed_count is None else seed_count)


class _DetRng:
    """Replay-stable stream. Does not touch the process-global RNG."""

    def __init__(self, seed: int) -> None:
        self._seed = int(seed)
        self._n = 0

    def uniform(self) -> float:
        self._n += 1
        digest = hashlib.sha256(f"{self._seed}:{self._n}".encode()).digest()
        return int.from_bytes(digest[:8], "big") / float(2**64)

    def gauss(self, mu: float, sigma: float) -> float:
        u1 = max(1e-12, self.uniform())
        u2 = self.uniform()
        z = math.sqrt(-2.0 * math.log(u1)) * math.cos(2.0 * math.pi * u2)
        return mu + sigma * z


def _clip01(value: float) -> float:
    return 0.0 if value < 0.0 else 1.0 if value > 1.0 else value


def gorelick_normalized_mutual_information(
    organism_tasks: Sequence[tuple[str, str]],
) -> float:
    """Gorelick et al. 2004 analog: NMI of (organism identity, task).

    ``I(id; task) / H(task)`` when H(task)>0, else 0. Not bit-identical to the
    paper; a measurement statistic, not a Goldsby 50-replicate result.
    """

    if not organism_tasks:
        return 0.0
    n = float(len(organism_tasks))
    joint: dict[tuple[str, str], int] = {}
    id_counts: dict[str, int] = {}
    task_counts: dict[str, int] = {}
    for oid, task in organism_tasks:
        joint[(oid, task)] = joint.get((oid, task), 0) + 1
        id_counts[oid] = id_counts.get(oid, 0) + 1
        task_counts[task] = task_counts.get(task, 0) + 1

    def _h(counts: Mapping[str, int]) -> float:
        ent = 0.0
        for count in counts.values():
            p = count / n
            if p > 0.0:
                ent -= p * math.log2(p)
        return ent

    h_task = _h(task_counts)
    if h_task <= 0.0:
        return 0.0
    h_id = _h(id_counts)
    h_joint = 0.0
    for count in joint.values():
        p = count / n
        if p > 0.0:
            h_joint -= p * math.log2(p)
    mutual = h_id + h_task - h_joint
    if mutual < 0.0:
        mutual = 0.0
    return round(min(1.0, mutual / h_task), 10)


def _choose_task(preference: float, rng: _DetRng) -> str:
    if preference <= SPECIALIST_A_CUTOFF:
        return TASK_A
    if preference >= SPECIALIST_B_CUTOFF:
        return TASK_B
    return TASK_A if rng.uniform() < 0.5 else TASK_B


def _is_generalist(preference: float) -> bool:
    return SPECIALIST_A_CUTOFF < preference < SPECIALIST_B_CUTOFF


def _task_yield(task: str) -> float:
    return TASK_A_YIELD if task == TASK_A else TASK_B_YIELD


@dataclass(frozen=True, slots=True)
class TaskGroupEvaluation:
    """One group: complementary tasks A/B. Not collective intelligence."""

    preferences: tuple[float, ...]
    tasks: tuple[str, ...]
    personal_fitness: tuple[float, ...]
    group_fitness: float
    n_task_a: int
    n_task_b: int
    nmi: float

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "preferences": [round(item, 10) for item in self.preferences],
            "tasks": list(self.tasks),
            "personal_fitness": [round(item, 10) for item in self.personal_fitness],
            "group_fitness": self.group_fitness,
            "n_task_a": self.n_task_a,
            "n_task_b": self.n_task_b,
            "nmi": self.nmi,
            "collective_intelligence": False,
        }


def evaluate_task_group(
    preferences: Sequence[float],
    *,
    rng: _DetRng,
    organism_ids: Sequence[str] | None = None,
) -> TaskGroupEvaluation:
    """Binary task choice with complementary group payoff (min A, B)."""

    prefs = tuple(_clip01(float(item)) for item in preferences)
    if not prefs:
        raise ConfigurationError("evaluate_task_group requires at least one organism.")
    tasks = tuple(_choose_task(pref, rng) for pref in prefs)
    personal: list[float] = []
    for pref, task in zip(prefs, tasks, strict=True):
        payoff = _task_yield(task)
        if _is_generalist(pref):
            payoff = round(payoff - SWITCH_COST, 10)
        personal.append(round(payoff, 10))
    n_a = sum(1 for task in tasks if task == TASK_A)
    n_b = len(tasks) - n_a
    total_a = n_a * TASK_A_YIELD
    total_b = n_b * TASK_B_YIELD
    group = round(PAIR_BONUS * min(total_a, total_b), 10)
    ids = (
        tuple(organism_ids)
        if organism_ids is not None
        else tuple(f"org{index}" for index in range(len(prefs)))
    )
    if len(ids) != len(tasks):
        raise ConfigurationError("organism_ids must match preferences.")
    lifetime: list[tuple[str, str]] = []
    for oid, pref in zip(ids, prefs, strict=True):
        for _ in range(LIFETIME_TASK_SAMPLES):
            lifetime.append((oid, _choose_task(pref, rng)))
    nmi = gorelick_normalized_mutual_information(tuple(lifetime))
    return TaskGroupEvaluation(
        preferences=tuple(round(item, 10) for item in prefs),
        tasks=tasks,
        personal_fitness=tuple(personal),
        group_fitness=group,
        n_task_a=n_a,
        n_task_b=n_b,
        nmi=nmi,
    )


def _partition(preferences: Sequence[float], group_size: int) -> tuple[tuple[float, ...], ...]:
    items = tuple(preferences)
    if group_size < 2:
        raise ConfigurationError("group_size must be >= 2.")
    if len(items) % group_size:
        raise ConfigurationError("population size must divide group_size.")
    return tuple(items[index : index + group_size] for index in range(0, len(items), group_size))


def _eval_population(
    preferences: Sequence[float],
    *,
    group_size: int,
    rng: _DetRng,
    id_prefix: str,
) -> tuple[TaskGroupEvaluation, ...]:
    groups = _partition(preferences, group_size)
    rows: list[TaskGroupEvaluation] = []
    for index, group in enumerate(groups):
        ids = tuple(f"{id_prefix}:g{index}:o{member}" for member in range(len(group)))
        rows.append(evaluate_task_group(group, rng=rng, organism_ids=ids))
    return tuple(rows)


def _mean_group_fitness(rows: Sequence[TaskGroupEvaluation]) -> float:
    return _mean([item.group_fitness for item in rows])


def _mean_personal_fitness(rows: Sequence[TaskGroupEvaluation]) -> float:
    values = [fit for item in rows for fit in item.personal_fitness]
    return _mean(values)


def _mean_nmi(rows: Sequence[TaskGroupEvaluation]) -> float:
    return _mean([item.nmi for item in rows])


def _mean_preference(preferences: Sequence[float]) -> float:
    return _mean([float(item) for item in preferences])


def _within_group_preference_std(preferences: Sequence[float], group_size: int) -> float:
    groups = _partition(preferences, group_size)
    stds: list[float] = []
    for group in groups:
        mean = sum(group) / len(group)
        var = sum((item - mean) ** 2 for item in group) / max(1, len(group) - 1)
        stds.append(math.sqrt(var))
    return _mean(stds)


def classify_evolutionary_strategy(
    *,
    preferences: Sequence[float],
    mean_preference: float,
    within_group_std: float,
    nmi: float,
) -> str:
    """Label the evolved population by genotype mix. Outcome, not intelligence."""

    prefs = tuple(float(item) for item in preferences)
    if not prefs:
        return "empty"
    frac_a = sum(1 for item in prefs if item <= SPECIALIST_A_CUTOFF) / len(prefs)
    frac_b = sum(1 for item in prefs if item >= SPECIALIST_B_CUTOFF) / len(prefs)
    if frac_a >= MONOCULTURE_A_FRACTION and frac_b < MIXED_ROLE_FRACTION:
        return "a_specialist_monoculture"
    if frac_b >= MONOCULTURE_A_FRACTION and frac_a < MIXED_ROLE_FRACTION:
        return "b_specialist_monoculture"
    if frac_a >= MIXED_ROLE_FRACTION and frac_b >= MIXED_ROLE_FRACTION:
        return "mixed_specialists"
    if nmi >= NMI_SPECIALIZATION_THRESHOLD and within_group_std >= 0.12:
        return "mixed_specialists"
    if mean_preference <= 0.22:
        return "a_specialist_monoculture"
    if mean_preference >= 0.78:
        return "b_specialist_monoculture"
    return "generalist_or_mixed_weak"


def _mutate(preference: float, rng: _DetRng, sigma: float = MUTATION_SIGMA) -> float:
    return round(_clip01(preference + rng.gauss(0.0, sigma)), 10)


def _init_preferences(count: int, rng: _DetRng) -> list[float]:
    return [_clip01(rng.uniform()) for _ in range(count)]


def _reproduce_organism_only(
    preferences: Sequence[float],
    personal: Sequence[float],
    rng: _DetRng,
) -> list[float]:
    paired = sorted(
        zip(personal, range(len(preferences)), strict=True),
        key=lambda item: (-item[0], item[1]),
    )
    keep = max(1, int(len(preferences) * MLS_KEEP_FRACTION))
    parents = [preferences[index] for _, index in paired[:keep]]
    children: list[float] = []
    cursor = 0
    while len(children) < len(preferences):
        children.append(_mutate(parents[cursor % len(parents)], rng))
        cursor += 1
    rng_order = sorted(((rng.uniform(), item) for item in children), key=lambda row: row[0])
    return [item for _, item in rng_order]


def _reproduce_mls(
    groups: Sequence[tuple[float, ...]],
    group_fitness: Sequence[float],
    rng: _DetRng,
) -> list[float]:
    ranked = sorted(
        zip(group_fitness, range(len(groups)), strict=True),
        key=lambda item: (-item[0], item[1]),
    )
    keep = max(1, int(len(groups) * MLS_KEEP_FRACTION))
    parents = [groups[index] for _, index in ranked[:keep]]
    children_groups: list[tuple[float, ...]] = []
    cursor = 0
    while len(children_groups) < len(groups):
        source = parents[cursor % len(parents)]
        children_groups.append(tuple(_mutate(item, rng) for item in source))
        cursor += 1
    return [pref for group in children_groups for pref in group]


def evolve_two_task_population(
    *,
    seed: int,
    generations: int,
    n_groups: int,
    group_size: int,
    mode: str,
) -> tuple[tuple[float, ...], tuple[TaskGroupEvaluation, ...]]:
    """Evolve heritable task preference under organism-only or MLS2-style group replacement."""

    if mode not in {"organism_only", "mls"}:
        raise ConfigurationError("evolve mode must be organism_only or mls.")
    if generations < 1:
        raise ConfigurationError("generations must be >= 1.")
    rng = _DetRng(seed)
    prefs = _init_preferences(n_groups * group_size, rng)
    rows = _eval_population(prefs, group_size=group_size, rng=rng, id_prefix=f"{mode}:{seed}:0")
    for generation in range(1, generations + 1):
        if mode == "organism_only":
            personal = [fit for row in rows for fit in row.personal_fitness]
            prefs = _reproduce_organism_only(prefs, personal, rng)
        else:
            groups = _partition(prefs, group_size)
            prefs = _reproduce_mls(groups, tuple(row.group_fitness for row in rows), rng)
        rows = _eval_population(
            prefs, group_size=group_size, rng=rng, id_prefix=f"{mode}:{seed}:{generation}"
        )
    return tuple(round(item, 10) for item in prefs), rows


def _partner_digest(preferences: Sequence[float], label: str) -> str:
    payload: dict[str, JsonValue] = {
        "label": label,
        "preferences": [round(float(item), 8) for item in preferences],
    }
    return canonical_digest(payload)


def _mix_unfamiliar(
    familiar: Sequence[float],
    heldout: Sequence[float],
    group_size: int,
) -> list[float]:
    fam_groups = _partition(familiar, group_size)
    hold_groups = _partition(heldout, group_size)
    mixed: list[float] = []
    half = group_size // 2
    for left, right in zip(fam_groups, hold_groups, strict=False):
        mixed.extend(list(left[:half]) + list(right[half:]))
    if len(mixed) != len(familiar):
        # Unequal group counts: pair as many as possible, pad from familiar.
        mixed = list(familiar[:half]) + list(heldout[: len(familiar) - half])
        if len(mixed) < len(familiar):
            mixed.extend(list(familiar[len(mixed) :]))
    return mixed[: len(familiar)]


@dataclass(frozen=True, slots=True)
class HeldoutUnfamiliarPartnerSeedRecord:
    """One seed: familiar vs heldout-unfamiliar partners."""

    seed: int
    familiar_mean_group_fitness: float
    unfamiliar_mean_group_fitness: float
    delta: float
    familiar_digest: str
    unfamiliar_digest: str
    leakage_status: str
    distinct_partners: bool

    def __post_init__(self) -> None:
        for name in (
            "familiar_mean_group_fitness",
            "unfamiliar_mean_group_fitness",
            "delta",
        ):
            object.__setattr__(self, name, require_finite_float(name, getattr(self, name)))
        if self.leakage_status not in {"clean", "leaked", "not_run"}:
            raise ConfigurationError("invalid leakage_status.")

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "seed": self.seed,
            "familiar_mean_group_fitness": self.familiar_mean_group_fitness,
            "unfamiliar_mean_group_fitness": self.unfamiliar_mean_group_fitness,
            "delta": self.delta,
            "familiar_digest": self.familiar_digest,
            "unfamiliar_digest": self.unfamiliar_digest,
            "leakage_status": self.leakage_status,
            "distinct_partners": self.distinct_partners,
            "collective_intelligence": False,
        }


@dataclass(frozen=True, slots=True)
class HeldoutUnfamiliarPartnerCampaign:
    """Familiar vs unfamiliar partner generalization. Does not set ClaimGate flags."""

    seeds: tuple[int, ...]
    generations: int
    seed_records: tuple[HeldoutUnfamiliarPartnerSeedRecord, ...]
    protocol: HeldoutPartnerEvaluationProtocol
    evaluation_records: tuple[HeldoutPartnerEvaluationRecord, ...]
    mean_delta: float
    cohens_d: float | None
    effect_size_status: str
    heldout_partner_status: str = MEASURED_RUNTIME
    claim_gate_flags_auto_set: bool = False
    literature_checklist: tuple[tuple[str, str], ...] = LITERATURE_CHECKLIST
    claim_ceiling: str = _CLAIM_CEILING
    schema_version: str = "heldout_unfamiliar_partner_campaign_v1"
    digest: str = ""

    def __post_init__(self) -> None:
        if len(self.seeds) < 2:
            raise ConfigurationError("HeldoutUnfamiliarPartnerCampaign requires seed_count >= 2.")
        if self.generations < 1:
            raise ConfigurationError("generations must be >= 1.")
        object.__setattr__(self, "mean_delta", require_finite_float("mean_delta", self.mean_delta))
        if self.cohens_d is not None:
            object.__setattr__(self, "cohens_d", require_finite_float("cohens_d", self.cohens_d))
        if self.claim_gate_flags_auto_set:
            raise ConfigurationError("Phase I must not auto-set ClaimGate flags.")
        if self.claim_ceiling in _FORBIDDEN or self.claim_ceiling != _CLAIM_CEILING:
            raise ConfigurationError(
                "HeldoutUnfamiliarPartnerCampaign ceiling must stay runtime_observation."
            )
        computed = canonical_digest(self._payload())
        if self.digest and self.digest != computed:
            raise ConfigurationError("HeldoutUnfamiliarPartnerCampaign digest mismatch.")
        object.__setattr__(self, "digest", computed)

    def _payload(self) -> dict[str, JsonValue]:
        return {
            "schema_version": self.schema_version,
            "seeds": list(self.seeds),
            "generations": self.generations,
            "seed_records": [item.to_dict() for item in self.seed_records],
            "protocol": self.protocol.to_dict(),
            "evaluation_records": [item.to_dict() for item in self.evaluation_records],
            "mean_delta": self.mean_delta,
            "cohens_d": self.cohens_d,
            "effect_size_status": self.effect_size_status,
            "heldout_partner_status": self.heldout_partner_status,
            "claim_gate_flags_auto_set": self.claim_gate_flags_auto_set,
            "literature_checklist": [[key, text] for key, text in self.literature_checklist],
            "claim_ceiling": self.claim_ceiling,
            "collective_intelligence": False,
            "intelligence": False,
            "limitations": [
                "two_task_analog_not_avida_heldout_partners",
                "not_literature_scale_unless_research_seed_and_generation_counts",
                "claimgate_flags_not_auto_set",
            ],
        }

    def to_dict(self) -> dict[str, JsonValue]:
        return {**self._payload(), "digest": self.digest}


def run_heldout_unfamiliar_partner_experiment(
    seeds: Sequence[int] | None = None,
    *,
    seed_count: int | None = None,
    generations: int | None = None,
    n_groups: int | None = None,
    group_size: int = DEFAULT_GROUP_SIZE,
    smoke: bool = False,
) -> HeldoutUnfamiliarPartnerCampaign:
    """Train/evolve with familiar partners; evaluate with a heldout lineage.

    Smoke never earns ClaimGate flags. Status is measured_runtime_observation
    when the protocol actually ran.
    """

    seed_tuple = _resolve_seeds(
        seeds, seed_count, default_count=SMOKE_SEED_COUNT if smoke else RESEARCH_SEED_COUNT
    )
    gen_count = int(
        SMOKE_GENERATION_COUNT
        if generations is None and smoke
        else RESEARCH_GENERATION_COUNT
        if generations is None
        else generations
    )
    groups = _resolve_group_count(n_groups, smoke=smoke)
    records: list[HeldoutUnfamiliarPartnerSeedRecord] = []
    evals: list[HeldoutPartnerEvaluationRecord] = []
    fam_fits: list[float] = []
    unfam_fits: list[float] = []
    protocol = HeldoutPartnerEvaluationProtocol(
        train_partner_pool="familiar_lineage",
        test_partner_pool="heldout_unfamiliar_lineage",
        prevent_lineage_overlap=True,
        compare_familiar_vs_unfamiliar=True,
    )
    for seed in seed_tuple:
        fam_prefs, fam_rows = evolve_two_task_population(
            seed=seed,
            generations=gen_count,
            n_groups=groups,
            group_size=group_size,
            mode="mls",
        )
        hold_prefs, _hold_rows = evolve_two_task_population(
            seed=seed + 10_000,
            generations=gen_count,
            n_groups=groups,
            group_size=group_size,
            mode="mls",
        )
        mixed = _mix_unfamiliar(fam_prefs, hold_prefs, group_size)
        rng_u = _DetRng(seed + 19)
        unfam_eval = _eval_population(
            mixed, group_size=group_size, rng=rng_u, id_prefix=f"unfam:{seed}"
        )
        fam_fit = _mean_group_fitness(fam_rows)
        unfam_fit = _mean_group_fitness(unfam_eval)
        fam_digest = _partner_digest(fam_prefs, f"familiar:{seed}")
        unfam_digest = _partner_digest(mixed, f"unfamiliar:{seed}")
        distinct = fam_digest != unfam_digest
        leakage = "clean" if distinct else "leaked"
        fam_fits.append(fam_fit)
        unfam_fits.append(unfam_fit)
        records.append(
            HeldoutUnfamiliarPartnerSeedRecord(
                seed=seed,
                familiar_mean_group_fitness=fam_fit,
                unfamiliar_mean_group_fitness=unfam_fit,
                delta=round(unfam_fit - fam_fit, 10),
                familiar_digest=fam_digest,
                unfamiliar_digest=unfam_digest,
                leakage_status=leakage,
                distinct_partners=distinct,
            )
        )
        evals.append(
            HeldoutPartnerEvaluationRecord(
                protocol_digest=protocol.digest(),
                familiar_partner_digest=fam_digest,
                unfamiliar_partner_digest=unfam_digest,
                familiar_score=fam_fit,
                unfamiliar_score=unfam_fit,
                leakage_status=leakage,
            )
        )
    cohens, status = _cohens_d(unfam_fits, fam_fits)
    campaign = HeldoutUnfamiliarPartnerCampaign(
        seeds=seed_tuple,
        generations=gen_count,
        seed_records=tuple(records),
        protocol=protocol,
        evaluation_records=tuple(evals),
        mean_delta=_mean([item.delta for item in records]),
        cohens_d=cohens,
        effect_size_status=status,
        heldout_partner_status=MEASURED_RUNTIME,
        claim_gate_flags_auto_set=False,
    )
    _assert_ci_blocked(campaign.to_dict(), ScientificClaimGate())
    return campaign


@dataclass(frozen=True, slots=True)
class EvolvedDivisionOfLaborSeedRecord:
    """One seed of evolved (not assigned) two-task specialization."""

    seed: int
    nmi: float
    mean_group_fitness: float
    ablated_group_fitness: float
    ablation_drop: float
    assigned_roles: bool
    evolved_division_of_labor_pays: bool
    strategy: str

    def __post_init__(self) -> None:
        for name in ("nmi", "mean_group_fitness", "ablated_group_fitness", "ablation_drop"):
            object.__setattr__(self, name, require_finite_float(name, getattr(self, name)))
        if self.assigned_roles:
            raise ConfigurationError("Evolved DoL records must not mark roles as assigned.")

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "seed": self.seed,
            "nmi": self.nmi,
            "mean_group_fitness": self.mean_group_fitness,
            "ablated_group_fitness": self.ablated_group_fitness,
            "ablation_drop": self.ablation_drop,
            "assigned_roles": self.assigned_roles,
            "evolved_division_of_labor_pays": self.evolved_division_of_labor_pays,
            "strategy": self.strategy,
            "collective_intelligence": False,
        }


@dataclass(frozen=True, slots=True)
class EvolvedDivisionOfLaborCampaign:
    """Evolved preference DoL + ablation. Not Goldsby 50-replicate PNAS."""

    seeds: tuple[int, ...]
    generations: int
    seed_records: tuple[EvolvedDivisionOfLaborSeedRecord, ...]
    mean_nmi: float
    mean_ablation_drop: float
    cohens_d: float | None
    effect_size_status: str
    evolved_not_assigned: bool = True
    communication_ablation_status: str = GAP_NOT_RUN
    claim_gate_ablation_result_set: bool = False
    claim_gate_flags_auto_set: bool = False
    literature_checklist: tuple[tuple[str, str], ...] = LITERATURE_CHECKLIST
    claim_ceiling: str = _CLAIM_CEILING
    schema_version: str = "evolved_division_of_labor_campaign_v1"
    digest: str = ""

    def __post_init__(self) -> None:
        if len(self.seeds) < 2:
            raise ConfigurationError("EvolvedDivisionOfLaborCampaign requires seed_count >= 2.")
        object.__setattr__(self, "mean_nmi", require_finite_float("mean_nmi", self.mean_nmi))
        object.__setattr__(
            self,
            "mean_ablation_drop",
            require_finite_float("mean_ablation_drop", self.mean_ablation_drop),
        )
        if self.cohens_d is not None:
            object.__setattr__(self, "cohens_d", require_finite_float("cohens_d", self.cohens_d))
        if self.claim_gate_ablation_result_set or self.claim_gate_flags_auto_set:
            raise ConfigurationError("Phase I evolved-DoL must not auto-set ClaimGate flags.")
        if not self.evolved_not_assigned:
            raise ConfigurationError("EvolvedDivisionOfLaborCampaign cannot claim assigned roles.")
        if self.claim_ceiling != _CLAIM_CEILING:
            raise ConfigurationError("DoL campaign ceiling must stay runtime_observation.")
        computed = canonical_digest(self._payload())
        if self.digest and self.digest != computed:
            raise ConfigurationError("EvolvedDivisionOfLaborCampaign digest mismatch.")
        object.__setattr__(self, "digest", computed)

    def _payload(self) -> dict[str, JsonValue]:
        return {
            "schema_version": self.schema_version,
            "seeds": list(self.seeds),
            "generations": self.generations,
            "seed_records": [item.to_dict() for item in self.seed_records],
            "mean_nmi": self.mean_nmi,
            "mean_ablation_drop": self.mean_ablation_drop,
            "cohens_d": self.cohens_d,
            "effect_size_status": self.effect_size_status,
            "evolved_not_assigned": self.evolved_not_assigned,
            "communication_ablation_status": self.communication_ablation_status,
            "claim_gate_ablation_result_set": self.claim_gate_ablation_result_set,
            "claim_gate_flags_auto_set": self.claim_gate_flags_auto_set,
            "literature_checklist": [[key, text] for key, text in self.literature_checklist],
            "claim_ceiling": self.claim_ceiling,
            "collective_intelligence": False,
            "evolved_division_of_labor_is_not_goldsby_2012": True,
            "limitations": [
                "two_task_preference_gene_not_avida_instructions",
                "not_50_replicate_pnas_experiment",
                "claimgate_ablation_result_not_auto_set",
            ],
        }

    def to_dict(self) -> dict[str, JsonValue]:
        return {**self._payload(), "digest": self.digest}


def _ablate_to_monoculture_a(preferences: Sequence[float]) -> tuple[float, ...]:
    return tuple(0.0 for _ in preferences)


def run_evolved_division_of_labor_experiment(
    seeds: Sequence[int] | None = None,
    *,
    seed_count: int | None = None,
    generations: int | None = None,
    n_groups: int | None = None,
    group_size: int = DEFAULT_GROUP_SIZE,
    smoke: bool = False,
) -> EvolvedDivisionOfLaborCampaign:
    """MLS-evolved task preference vs all-A ablation. Roles are not assigned tags."""

    seed_tuple = _resolve_seeds(
        seeds, seed_count, default_count=SMOKE_SEED_COUNT if smoke else RESEARCH_SEED_COUNT
    )
    gen_count = int(
        SMOKE_GENERATION_COUNT
        if generations is None and smoke
        else RESEARCH_GENERATION_COUNT
        if generations is None
        else generations
    )
    groups = _resolve_group_count(n_groups, smoke=smoke)
    records: list[EvolvedDivisionOfLaborSeedRecord] = []
    baseline_fits: list[float] = []
    ablated_fits: list[float] = []
    for seed in seed_tuple:
        prefs, rows = evolve_two_task_population(
            seed=seed,
            generations=gen_count,
            n_groups=groups,
            group_size=group_size,
            mode="mls",
        )
        baseline = _mean_group_fitness(rows)
        nmi = _mean_nmi(rows)
        ablated_prefs = _ablate_to_monoculture_a(prefs)
        ablated_rows = _eval_population(
            ablated_prefs,
            group_size=group_size,
            rng=_DetRng(seed + 99),
            id_prefix=f"ablate:{seed}",
        )
        ablated = _mean_group_fitness(ablated_rows)
        drop = round(baseline - ablated, 10)
        strategy = classify_evolutionary_strategy(
            preferences=prefs,
            mean_preference=_mean_preference(prefs),
            within_group_std=_within_group_preference_std(prefs, group_size),
            nmi=nmi,
        )
        pays = drop > ABLATION_DROP_EPSILON and nmi >= NMI_SPECIALIZATION_THRESHOLD
        baseline_fits.append(baseline)
        ablated_fits.append(ablated)
        records.append(
            EvolvedDivisionOfLaborSeedRecord(
                seed=seed,
                nmi=nmi,
                mean_group_fitness=baseline,
                ablated_group_fitness=ablated,
                ablation_drop=drop,
                assigned_roles=False,
                evolved_division_of_labor_pays=pays,
                strategy=strategy,
            )
        )
    cohens, status = _cohens_d(baseline_fits, ablated_fits)
    campaign = EvolvedDivisionOfLaborCampaign(
        seeds=seed_tuple,
        generations=gen_count,
        seed_records=tuple(records),
        mean_nmi=_mean([item.nmi for item in records]),
        mean_ablation_drop=_mean([item.ablation_drop for item in records]),
        cohens_d=cohens,
        effect_size_status=status,
        evolved_not_assigned=True,
        claim_gate_ablation_result_set=False,
        claim_gate_flags_auto_set=False,
    )
    _assert_ci_blocked(campaign.to_dict(), ScientificClaimGate())
    return campaign


@dataclass(frozen=True, slots=True)
class MlsOutcomeSeedRecord:
    """Paired MLS vs organism-only evolutionary outcome for one seed."""

    seed: int
    mls_strategy: str
    organism_strategy: str
    mls_mean_preference: float
    organism_mean_preference: float
    mls_nmi: float
    organism_nmi: float
    mls_mean_group_fitness: float
    organism_mean_group_fitness: float
    outcome_changed: bool

    def __post_init__(self) -> None:
        for name in (
            "mls_mean_preference",
            "organism_mean_preference",
            "mls_nmi",
            "organism_nmi",
            "mls_mean_group_fitness",
            "organism_mean_group_fitness",
        ):
            object.__setattr__(self, name, require_finite_float(name, getattr(self, name)))

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "seed": self.seed,
            "mls_strategy": self.mls_strategy,
            "organism_strategy": self.organism_strategy,
            "mls_mean_preference": self.mls_mean_preference,
            "organism_mean_preference": self.organism_mean_preference,
            "mls_nmi": self.mls_nmi,
            "organism_nmi": self.organism_nmi,
            "mls_mean_group_fitness": self.mls_mean_group_fitness,
            "organism_mean_group_fitness": self.organism_mean_group_fitness,
            "outcome_changed": self.outcome_changed,
            "collective_intelligence": False,
        }


@dataclass(frozen=True, slots=True)
class MlsEvolutionaryOutcomeCampaign:
    """MLS2-style group replacement vs organism-only. Outcome, not a rank table."""

    seeds: tuple[int, ...]
    generations: int
    seed_records: tuple[MlsOutcomeSeedRecord, ...]
    outcome_changed_fraction: float
    mean_group_fitness_delta: float
    cohens_d: float | None
    effect_size_status: str
    multilevel_selection_experiment: str = MEASURED_RUNTIME
    claim_gate_flags_auto_set: bool = False
    major_transition_in_individuality: bool = False
    literature_checklist: tuple[tuple[str, str], ...] = LITERATURE_CHECKLIST
    claim_ceiling: str = _CLAIM_CEILING
    schema_version: str = "mls_evolutionary_outcome_campaign_v1"
    digest: str = ""

    def __post_init__(self) -> None:
        if len(self.seeds) < 2:
            raise ConfigurationError("MlsEvolutionaryOutcomeCampaign requires seed_count >= 2.")
        object.__setattr__(
            self,
            "outcome_changed_fraction",
            require_finite_float("outcome_changed_fraction", self.outcome_changed_fraction),
        )
        object.__setattr__(
            self,
            "mean_group_fitness_delta",
            require_finite_float("mean_group_fitness_delta", self.mean_group_fitness_delta),
        )
        if self.cohens_d is not None:
            object.__setattr__(self, "cohens_d", require_finite_float("cohens_d", self.cohens_d))
        if self.claim_gate_flags_auto_set:
            raise ConfigurationError("Phase I MLS campaign must not auto-set ClaimGate flags.")
        if self.major_transition_in_individuality:
            raise ConfigurationError(
                "MLS outcome campaign must not set major_transition_in_individuality True."
            )
        if self.claim_ceiling != _CLAIM_CEILING:
            raise ConfigurationError("MLS campaign ceiling must stay runtime_observation.")
        computed = canonical_digest(self._payload())
        if self.digest and self.digest != computed:
            raise ConfigurationError("MlsEvolutionaryOutcomeCampaign digest mismatch.")
        object.__setattr__(self, "digest", computed)

    def _payload(self) -> dict[str, JsonValue]:
        return {
            "schema_version": self.schema_version,
            "seeds": list(self.seeds),
            "generations": self.generations,
            "seed_records": [item.to_dict() for item in self.seed_records],
            "outcome_changed_fraction": self.outcome_changed_fraction,
            "mean_group_fitness_delta": self.mean_group_fitness_delta,
            "cohens_d": self.cohens_d,
            "effect_size_status": self.effect_size_status,
            "multilevel_selection_experiment": self.multilevel_selection_experiment,
            "claim_gate_flags_auto_set": self.claim_gate_flags_auto_set,
            "major_transition_in_individuality": self.major_transition_in_individuality,
            "literature_checklist": [[key, text] for key, text in self.literature_checklist],
            "claim_ceiling": self.claim_ceiling,
            "collective_intelligence": False,
            "ranking_is_not_this_experiment": True,
            "limitations": [
                "two_task_analog_not_avida_deme_group",
                "not_okasha_full_price_equation_paper",
                "major_transition_in_individuality_false",
            ],
        }

    def to_dict(self) -> dict[str, JsonValue]:
        return {**self._payload(), "digest": self.digest}


def run_mls_evolutionary_outcome_experiment(
    seeds: Sequence[int] | None = None,
    *,
    seed_count: int | None = None,
    generations: int | None = None,
    n_groups: int | None = None,
    group_size: int = DEFAULT_GROUP_SIZE,
    smoke: bool = False,
) -> MlsEvolutionaryOutcomeCampaign:
    """Compare which strategy wins under MLS vs organism-only selection."""

    seed_tuple = _resolve_seeds(
        seeds, seed_count, default_count=SMOKE_SEED_COUNT if smoke else RESEARCH_SEED_COUNT
    )
    gen_count = int(
        SMOKE_GENERATION_COUNT
        if generations is None and smoke
        else RESEARCH_GENERATION_COUNT
        if generations is None
        else generations
    )
    groups = _resolve_group_count(n_groups, smoke=smoke)
    records: list[MlsOutcomeSeedRecord] = []
    mls_fits: list[float] = []
    org_fits: list[float] = []
    for seed in seed_tuple:
        mls_prefs, mls_rows = evolve_two_task_population(
            seed=seed,
            generations=gen_count,
            n_groups=groups,
            group_size=group_size,
            mode="mls",
        )
        org_prefs, org_rows = evolve_two_task_population(
            seed=seed,
            generations=gen_count,
            n_groups=groups,
            group_size=group_size,
            mode="organism_only",
        )
        mls_nmi = _mean_nmi(mls_rows)
        org_nmi = _mean_nmi(org_rows)
        mls_strategy = classify_evolutionary_strategy(
            preferences=mls_prefs,
            mean_preference=_mean_preference(mls_prefs),
            within_group_std=_within_group_preference_std(mls_prefs, group_size),
            nmi=mls_nmi,
        )
        org_strategy = classify_evolutionary_strategy(
            preferences=org_prefs,
            mean_preference=_mean_preference(org_prefs),
            within_group_std=_within_group_preference_std(org_prefs, group_size),
            nmi=org_nmi,
        )
        mls_fit = _mean_group_fitness(mls_rows)
        org_fit = _mean_group_fitness(org_rows)
        mls_fits.append(mls_fit)
        org_fits.append(org_fit)
        records.append(
            MlsOutcomeSeedRecord(
                seed=seed,
                mls_strategy=mls_strategy,
                organism_strategy=org_strategy,
                mls_mean_preference=_mean_preference(mls_prefs),
                organism_mean_preference=_mean_preference(org_prefs),
                mls_nmi=mls_nmi,
                organism_nmi=org_nmi,
                mls_mean_group_fitness=mls_fit,
                organism_mean_group_fitness=org_fit,
                outcome_changed=mls_strategy != org_strategy,
            )
        )
    cohens, status = _cohens_d(mls_fits, org_fits)
    changed = sum(1 for item in records if item.outcome_changed)
    campaign = MlsEvolutionaryOutcomeCampaign(
        seeds=seed_tuple,
        generations=gen_count,
        seed_records=tuple(records),
        outcome_changed_fraction=round(changed / len(records), 10),
        mean_group_fitness_delta=_mean(
            [item.mls_mean_group_fitness - item.organism_mean_group_fitness for item in records]
        ),
        cohens_d=cohens,
        effect_size_status=status,
        multilevel_selection_experiment=MEASURED_RUNTIME,
        claim_gate_flags_auto_set=False,
        major_transition_in_individuality=False,
    )
    _assert_ci_blocked(campaign.to_dict(), ScientificClaimGate())
    return campaign


@dataclass(frozen=True, slots=True)
class ExportOfFitnessObservation:
    """Michod-style measurement scaffold. Defaults keep the transition false.

    Isolation collapse in this two-task payoff is partly *by construction*
    (a singleton cannot supply both complementary tasks). That is not evolved
    loss of lower-level autonomy (Goldsby 2012 / Conlin 2023). Conflict
    suppression and germline sequestration stay non-endogenous.
    """

    mls: MlsEvolutionaryOutcomeCampaign | None
    between_group_fitness_mean: float
    within_group_personal_mean: float
    isolation_competence: float
    group_competence: float
    isolation_collapse_ratio: float
    isolation_collapse_is_payoff_construction: bool = True
    conflict_suppression_endogenous: bool = False
    germline_sequestration_endogenous: bool = False
    export_of_fitness_detected: bool = False
    major_transition_in_individuality: bool = False
    literature_gap: str = "measurement_scaffold_not_michod_transition"
    claim_ceiling: str = _CLAIM_CEILING
    schema_version: str = "export_of_fitness_observation_v1"
    digest: str = ""

    def __post_init__(self) -> None:
        for name in (
            "between_group_fitness_mean",
            "within_group_personal_mean",
            "isolation_competence",
            "group_competence",
            "isolation_collapse_ratio",
        ):
            object.__setattr__(self, name, require_finite_float(name, getattr(self, name)))
        if self.major_transition_in_individuality and not (
            self.conflict_suppression_endogenous
            and self.germline_sequestration_endogenous
            and self.export_of_fitness_detected
            and not self.isolation_collapse_is_payoff_construction
        ):
            raise ConfigurationError(
                "major_transition_in_individuality cannot be True on this scaffold."
            )
        if self.claim_ceiling != _CLAIM_CEILING:
            raise ConfigurationError("export-of-fitness ceiling must stay runtime_observation.")
        computed = canonical_digest(self._payload())
        if self.digest and self.digest != computed:
            raise ConfigurationError("ExportOfFitnessObservation digest mismatch.")
        object.__setattr__(self, "digest", computed)

    def _payload(self) -> dict[str, JsonValue]:
        mls_payload: JsonValue = None if self.mls is None else self.mls.to_dict()
        return {
            "schema_version": self.schema_version,
            "mls": mls_payload,
            "between_group_fitness_mean": self.between_group_fitness_mean,
            "within_group_personal_mean": self.within_group_personal_mean,
            "isolation_competence": self.isolation_competence,
            "group_competence": self.group_competence,
            "isolation_collapse_ratio": self.isolation_collapse_ratio,
            "isolation_collapse_is_payoff_construction": (
                self.isolation_collapse_is_payoff_construction
            ),
            "conflict_suppression_endogenous": self.conflict_suppression_endogenous,
            "germline_sequestration_endogenous": self.germline_sequestration_endogenous,
            "export_of_fitness_detected": self.export_of_fitness_detected,
            "major_transition_in_individuality": self.major_transition_in_individuality,
            "literature_gap": self.literature_gap,
            "claim_ceiling": self.claim_ceiling,
            "collective_intelligence": False,
        }

    def to_dict(self) -> dict[str, JsonValue]:
        return {**self._payload(), "digest": self.digest}


def build_export_of_fitness_observation(
    mls: MlsEvolutionaryOutcomeCampaign | None = None,
    *,
    seed: int = 11,
    generations: int = SMOKE_GENERATION_COUNT,
    n_groups: int = SMOKE_N_GROUPS,
    group_size: int = DEFAULT_GROUP_SIZE,
) -> ExportOfFitnessObservation:
    """Record export-of-fitness *hooks*. Transition flag stays false."""

    campaign = mls
    if campaign is None:
        campaign = run_mls_evolutionary_outcome_experiment(
            seeds=(seed, seed + 1),
            generations=generations,
            n_groups=n_groups,
            group_size=group_size,
            smoke=True,
        )
    prefs, rows = evolve_two_task_population(
        seed=seed,
        generations=max(1, campaign.generations),
        n_groups=n_groups,
        group_size=group_size,
        mode="mls",
    )
    group_competence = _mean_group_fitness(rows)
    isolation_rows: list[float] = []
    rng = _DetRng(seed + 123)
    for index, pref in enumerate(prefs):
        solo = evaluate_task_group((pref,), rng=rng, organism_ids=(f"iso:{index}",))
        isolation_rows.append(solo.group_fitness)
    isolation = _mean(isolation_rows)
    ratio = 0.0 if group_competence <= 0.0 else round(isolation / group_competence, 10)
    observation = ExportOfFitnessObservation(
        mls=campaign,
        between_group_fitness_mean=group_competence,
        within_group_personal_mean=_mean_personal_fitness(rows),
        isolation_competence=isolation,
        group_competence=group_competence,
        isolation_collapse_ratio=ratio,
        isolation_collapse_is_payoff_construction=True,
        conflict_suppression_endogenous=False,
        germline_sequestration_endogenous=False,
        export_of_fitness_detected=False,
        major_transition_in_individuality=False,
    )
    _assert_ci_blocked(observation.to_dict(), ScientificClaimGate())
    return observation


@dataclass(frozen=True, slots=True)
class CandidateFlagEarnCriteria:
    """Research-scale bars. Smoke is never enough."""

    min_seed_count: int = RESEARCH_SEED_COUNT
    min_generations: int = RESEARCH_GENERATION_COUNT
    require_distinct_partners: bool = True
    require_evolved_not_assigned: bool = True
    require_ablation_payoff_drop: bool = True
    smoke_never_earns: bool = True
    schema_version: str = "candidate_flag_earn_criteria_v1"

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "schema_version": self.schema_version,
            "min_seed_count": self.min_seed_count,
            "min_generations": self.min_generations,
            "require_distinct_partners": self.require_distinct_partners,
            "require_evolved_not_assigned": self.require_evolved_not_assigned,
            "require_ablation_payoff_drop": self.require_ablation_payoff_drop,
            "smoke_never_earns": self.smoke_never_earns,
            "replay_verification_earnable_from_phase_i": False,
        }


@dataclass(frozen=True, slots=True)
class EarnedCandidateFlags:
    """Flags earned from evidence objects. Printing/constructing does not set ClaimGate."""

    flags: tuple[tuple[str, bool], ...]
    reasons: tuple[tuple[str, str], ...]
    earnable_sources: tuple[tuple[str, str], ...] = EARNABLE_FLAG_SOURCES
    auto_set: bool = False
    smoke: bool = False
    research_scale: bool = False
    claim_ceiling: str = "collective_intelligence_candidate"
    schema_version: str = "earned_candidate_flags_v1"
    digest: str = ""

    def __post_init__(self) -> None:
        if self.auto_set:
            raise ConfigurationError("EarnedCandidateFlags must not auto-set ClaimGate state.")
        computed = canonical_digest(self._payload())
        if self.digest and self.digest != computed:
            raise ConfigurationError("EarnedCandidateFlags digest mismatch.")
        object.__setattr__(self, "digest", computed)

    def as_mapping(self) -> dict[str, bool]:
        return {name: value for name, value in self.flags}

    def _payload(self) -> dict[str, JsonValue]:
        return {
            "schema_version": self.schema_version,
            "flags": [[name, value] for name, value in self.flags],
            "reasons": [[name, text] for name, text in self.reasons],
            "earnable_sources": [[name, text] for name, text in self.earnable_sources],
            "auto_set": self.auto_set,
            "smoke": self.smoke,
            "research_scale": self.research_scale,
            "claim_ceiling": self.claim_ceiling,
            "collective_intelligence": False,
            "intelligence": False,
            "note": "earning_returns_a_mapping_claimgate_is_not_mutated",
        }

    def to_dict(self) -> dict[str, JsonValue]:
        return {**self._payload(), "digest": self.digest}


def _scale_ok(
    *,
    seed_count: int,
    generations: int,
    smoke: bool,
    criteria: CandidateFlagEarnCriteria,
) -> tuple[bool, str]:
    if smoke and criteria.smoke_never_earns:
        return False, "smoke_never_earns_claimgate_flags"
    if seed_count < criteria.min_seed_count:
        return False, "seed_count_below_research_minimum"
    if generations < criteria.min_generations:
        return False, "generations_below_research_minimum"
    return True, "research_scale"


def _earn_replay_verification(
    replay: ReplayVerificationLike | None,
    *,
    smoke: bool,
    criteria: CandidateFlagEarnCriteria,
) -> tuple[bool, str]:
    """Honest replay flag: independent digest match at research scale, never smoke."""

    if replay is None:
        return False, "not_earnable_without_independent_digest_replay"
    earns_fn = getattr(replay, "earns_replay_verification", None)
    if not callable(earns_fn) or not bool(earns_fn()):
        issues = tuple(getattr(replay, "issues", ()) or ())
        if issues:
            return False, str(issues[0])
        if not bool(getattr(replay, "re_executed", False)):
            return False, "replay_was_not_independently_re_executed"
        if not bool(getattr(replay, "matched", False)):
            return False, "replay_digests_did_not_match"
        return False, "replay_verification_object_did_not_pass"
    captures = tuple(getattr(replay, "captures", ()) or ())
    if not captures:
        return False, "replay_verification_missing_captures"
    for capture in captures:
        spec = getattr(capture, "spec", None)
        if spec is None:
            return False, "replay_capture_missing_spec"
        seeds = tuple(getattr(spec, "seeds", ()) or ())
        generations = int(getattr(spec, "generations", 0) or 0)
        capture_smoke = bool(getattr(spec, "smoke", False))
        ok, why = _scale_ok(
            seed_count=len(seeds),
            generations=generations,
            smoke=smoke or capture_smoke,
            criteria=criteria,
        )
        if not ok:
            return False, why
    return True, "earned_from_independent_digest_replay"


def earn_collective_intelligence_candidate_flags(
    *,
    heldout: HeldoutUnfamiliarPartnerCampaign | None = None,
    evolved_dol: EvolvedDivisionOfLaborCampaign | None = None,
    mls: MlsEvolutionaryOutcomeCampaign | None = None,
    export_of_fitness: ExportOfFitnessObservation | None = None,
    communication_ablation: CommunicationAblationCampaign | None = None,
    coordination: CoordinationAblationLike | None = None,
    replay: ReplayVerificationLike | None = None,
    smoke: bool = False,
    criteria: CandidateFlagEarnCriteria | None = None,
) -> EarnedCandidateFlags:
    """Return flags that *may* be passed into ClaimGate. Never mutates the gate.

    Smoke and sub-research scale return all False. ``replay_verification`` is
    earned only from an independent digest re-execution object whose captured
    and replayed campaign digests match at research scale. Phase I harnesses
    alone never set it. ``collective_intelligence`` stays forbidden even if
    every candidate flag is later supplied by a researcher.
    """

    resolved = criteria or CandidateFlagEarnCriteria()
    flags = {name: False for name in _CANDIDATE_FLAGS}
    reasons = {name: "not_earned" for name in _CANDIDATE_FLAGS}
    replay_ok, replay_why = _earn_replay_verification(replay, smoke=smoke, criteria=resolved)
    reasons["replay_verification"] = replay_why
    if replay_ok:
        flags["replay_verification"] = True

    def _consider(seed_count: int, generations: int) -> tuple[bool, str]:
        return _scale_ok(
            seed_count=seed_count, generations=generations, smoke=smoke, criteria=resolved
        )

    research_scale = False
    if heldout is not None:
        ok, why = _consider(len(heldout.seeds), heldout.generations)
        research_scale = research_scale or ok
        distinct = all(item.distinct_partners for item in heldout.seed_records)
        clean = all(item.leakage_status == "clean" for item in heldout.seed_records)
        if not ok:
            for name in (
                "heldout_protocol",
                "familiar_partner_protocol",
                "unfamiliar_partner_protocol",
                "real_partner_event",
                "collective_report_digest",
            ):
                reasons[name] = why
        elif resolved.require_distinct_partners and not (distinct and clean):
            for name in (
                "heldout_protocol",
                "familiar_partner_protocol",
                "unfamiliar_partner_protocol",
                "real_partner_event",
            ):
                reasons[name] = "partners_not_distinct_or_leakage"
        else:
            flags["heldout_protocol"] = True
            flags["familiar_partner_protocol"] = True
            flags["unfamiliar_partner_protocol"] = True
            flags["real_partner_event"] = True
            flags["collective_report_digest"] = True
            for name in (
                "heldout_protocol",
                "familiar_partner_protocol",
                "unfamiliar_partner_protocol",
                "real_partner_event",
                "collective_report_digest",
            ):
                reasons[name] = "earned_from_heldout_unfamiliar_partner_campaign"

    if evolved_dol is not None:
        ok, why = _consider(len(evolved_dol.seeds), evolved_dol.generations)
        research_scale = research_scale or ok
        pays = evolved_dol.mean_ablation_drop > ABLATION_DROP_EPSILON
        nmi_ok = evolved_dol.mean_nmi >= NMI_SPECIALIZATION_THRESHOLD
        if not ok:
            for name in (
                "role_complementarity",
                "collective_coordination",
                "non_capsule_cooperation",
                "ablation_result",
            ):
                if reasons[name] == "not_earned":
                    reasons[name] = why
        elif resolved.require_evolved_not_assigned and not evolved_dol.evolved_not_assigned:
            for name in ("role_complementarity", "collective_coordination"):
                reasons[name] = "roles_were_assigned"
        elif resolved.require_ablation_payoff_drop and not (pays and nmi_ok):
            for name in (
                "role_complementarity",
                "collective_coordination",
                "non_capsule_cooperation",
                "ablation_result",
            ):
                reasons[name] = "ablation_did_not_drop_payoff_or_nmi_too_low"
        else:
            flags["role_complementarity"] = True
            flags["collective_coordination"] = True
            flags["non_capsule_cooperation"] = True
            flags["ablation_result"] = True
            flags["collective_report_digest"] = True
            for name in (
                "role_complementarity",
                "collective_coordination",
                "non_capsule_cooperation",
                "ablation_result",
                "collective_report_digest",
            ):
                reasons[name] = "earned_from_evolved_division_of_labor_campaign"

    if communication_ablation is not None and not flags["ablation_result"]:
        ok, why = _consider(len(communication_ablation.seeds), RESEARCH_GENERATION_COUNT)
        pays = communication_ablation.mean_delta > ABLATION_DROP_EPSILON
        if ok and pays:
            flags["ablation_result"] = True
            reasons["ablation_result"] = "earned_from_research_scale_communication_ablation"
        elif not ok:
            reasons["ablation_result"] = why
        else:
            reasons["ablation_result"] = "communication_ablation_did_not_show_payoff_drop"

    if coordination is not None and not flags["ablation_result"]:
        ok, why = _consider(len(tuple(coordination.seeds)), int(coordination.generations))
        pays = float(coordination.mean_ablation_drop) > ABLATION_DROP_EPSILON
        successful = sum(
            int(getattr(item, "successful_retrieve", 0) or 0)
            for item in tuple(getattr(coordination, "seed_records", ()) or ())
        )
        if ok and pays and successful > 0:
            flags["ablation_result"] = True
            reasons["ablation_result"] = (
                "earned_from_research_scale_phase_k_coordination_ablation"
            )
        elif not ok:
            if reasons["ablation_result"] == "not_earned":
                reasons["ablation_result"] = why
        else:
            reasons["ablation_result"] = "coordination_ablation_did_not_show_payoff_drop"

    if mls is not None:
        ok, why = _consider(len(mls.seeds), mls.generations)
        research_scale = research_scale or ok
        if ok:
            flags["collective_report_digest"] = True
            digest_reason = reasons["collective_report_digest"]
            if digest_reason in {"not_earned", "seed_count_below_research_minimum"}:
                reasons["collective_report_digest"] = (
                    "earned_from_mls_evolutionary_outcome_campaign"
                )
        elif reasons["collective_report_digest"] == "not_earned":
            reasons["collective_report_digest"] = why

    if export_of_fitness is not None and export_of_fitness.major_transition_in_individuality:
        raise ConfigurationError("export-of-fitness scaffold must not unlock a major transition.")

    earned = EarnedCandidateFlags(
        flags=tuple((name, flags[name]) for name in _CANDIDATE_FLAGS),
        reasons=tuple((name, reasons[name]) for name in _CANDIDATE_FLAGS),
        auto_set=False,
        smoke=smoke,
        research_scale=research_scale and not smoke,
    )
    mapping = earned.as_mapping()
    gate = ScientificClaimGate()
    blocked = gate.decide(ClaimRequest("collective_intelligence", mapping))
    if blocked.allowed:
        raise ConfigurationError("collective_intelligence must remain blocked.")
    intelligence = gate.decide(ClaimRequest("intelligence", mapping))
    if intelligence.allowed:
        raise ConfigurationError("intelligence must remain blocked.")
    return earned


def phase_i_candidate_checklist(
    *,
    heldout: HeldoutUnfamiliarPartnerCampaign | None = None,
    evolved_dol: EvolvedDivisionOfLaborCampaign | None = None,
    mls: MlsEvolutionaryOutcomeCampaign | None = None,
    export_of_fitness: ExportOfFitnessObservation | None = None,
    communication_ablation: CommunicationAblationCampaign | None = None,
    coordination: CoordinationAblationLike | None = None,
    replay: ReplayVerificationLike | None = None,
    smoke: bool = False,
) -> CollectiveIntelligenceCandidateChecklist:
    """Checklist over earned flags. Does not set ClaimGate state."""

    earned = earn_collective_intelligence_candidate_flags(
        heldout=heldout,
        evolved_dol=evolved_dol,
        mls=mls,
        export_of_fitness=export_of_fitness,
        communication_ablation=communication_ablation,
        coordination=coordination,
        replay=replay,
        smoke=smoke,
    )
    checklist = collective_intelligence_candidate_checklist(earned.as_mapping())
    return checklist


def evaluate_phase_i_claim(payload: Mapping[str, JsonValue] | object) -> ClaimDecision:
    """Runtime observation only. Intelligence claims stay blocked."""

    gate = ScientificClaimGate()
    to_dict = getattr(payload, "to_dict", None)
    data: Mapping[str, JsonValue]
    if callable(to_dict):
        raw = to_dict()
        data = raw if isinstance(raw, Mapping) else {}
    elif isinstance(payload, Mapping):
        data = payload
    else:
        data = {}
    digest = str(data.get("digest", "") or "")
    decision = gate.decide(
        ClaimRequest(_CLAIM_CEILING, {}, evidence_digests=(digest,) if digest else ())
    )
    _assert_ci_blocked(data, gate)
    return decision
