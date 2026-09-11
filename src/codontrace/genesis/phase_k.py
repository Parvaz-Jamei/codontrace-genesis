"""Phase K literature-grade CI *depth* measurements for CodonTrace Genesis.

Measurement-first follow-on after Phase J: evolved coordination *instructions*
(send/retrieve/broadcast that pay), a Goldsby-scale CPU-delay specialist
campaign harness, multi-generation Price analysis with a transmission term,
and Michod/Conlin conflict-suppression *hooks*.

None of this auto-sets ClaimGate flags. Smoke never earns flags.
``collective_intelligence`` / ``intelligence`` / AGI stay blocked.
``major_transition_in_individuality`` stays False.

Claim ceiling: ``runtime_observation``. This is not Avida C++, not a PNAS
50-replicate paper, and not a Price 1970/1972 empirical study.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from codontrace._types import JsonValue
from codontrace.errors import ConfigurationError
from codontrace.genesis.canonical import canonical_digest, require_finite_float
from codontrace.genesis.claim_gate import ClaimDecision, ScientificClaimGate
from codontrace.genesis.phase_e import (
    Deme,
    DemeState,
    MessageKind,
    retrieve_message,
    send_message,
)
from codontrace.genesis.phase_h import (
    _CLAIM_CEILING,
    _FORBIDDEN,
    RESEARCH_SEED_COUNT,
    SMOKE_SEED_COUNT,
    _assert_ci_blocked,
    _mean,
)
from codontrace.genesis.phase_i import (
    ABLATION_DROP_EPSILON,
    DEFAULT_GROUP_SIZE,
    MLS_KEEP_FRACTION,
    MUTATION_SIGMA,
    PAIR_BONUS,
    RESEARCH_GENERATION_COUNT,
    SMOKE_GENERATION_COUNT,
    SMOKE_N_GROUPS,
    TASK_A,
    TASK_A_YIELD,
    TASK_B,
    TASK_B_YIELD,
    TaskGroupEvaluation,
    _clip01,
    _DetRng,
    _partition,
    _resolve_group_count,
    _resolve_seeds,
    evaluate_phase_i_claim,
    gorelick_normalized_mutual_information,
)
from codontrace.genesis.phase_j import (
    PRICE_PARTITION_TOLERANCE,
    population_covariance,
    price_partition_from_groups,
)

MEASURED_RUNTIME = "measured_runtime_observation"
ISA_SEND = MessageKind.SEND.value
ISA_RETRIEVE = MessageKind.RETRIEVE.value
ISA_BROADCAST = MessageKind.BROADCAST.value
ISA_WORK_A = "work_a"
ISA_WORK_B = "work_b"
ISA_NOP = "nop"
COORDINATION_ISA: tuple[str, ...] = (
    ISA_SEND,
    ISA_RETRIEVE,
    ISA_BROADCAST,
    ISA_WORK_A,
    ISA_WORK_B,
    ISA_NOP,
)
GENOME_LENGTH = 6
CPU_BUDGET = 8
COORD_BONUS = 4.0
COMPLEMENTARY_COORD_BONUS = 3.0
GOLDSBY_RESEARCH_REPLICATE_COUNT = 50
GOLDSBY_SMOKE_REPLICATE_COUNT = 4
GOLDSBY_LITERATURE_DELAYS: tuple[int, ...] = (0, 25, 50)
INSTRUCTION_MUTATION_RATE = 0.25

LITERATURE_CHECKLIST: tuple[tuple[str, str], ...] = (
    (
        "goldsby_ofria_evolved_coordination_instructions",
        "Goldsby/Ofria Avida ORGANISM_MESSAGING: send/retrieve/broadcast must "
        "pay. Phase K evolves a discrete instruction analog on the Phase E "
        "buffer — not Avida C++ and not evolved language.",
    ),
    (
        "goldsby_2012_cpu_delay_fifty_replicates",
        "Goldsby et al. PNAS 2012 doi:10.1073/pnas.1202233109: 0/25/50-cycle "
        "switch delay, ~50 replicates, isolation vs group. Phase K is a "
        "harness with that scale as the research default; smoke uses 4.",
    ),
    (
        "price_1970_1972_transmission",
        "Price 1970/1972: Δz̄ = Cov(w,z)/w̄ + E[w Δz]/w̄. Phase K estimates "
        "the transmission term from parent–offspring mutation. Still not a "
        "published Price paper; price_equation_complete stays False.",
    ),
    (
        "michod_conlin_conflict_hooks",
        "Michod PNAS 2007 conflict suppression; Conlin et al. 2023 revertant "
        "entrenchment. Phase K records hooks. endogenous flags stay False; "
        "major_transition_in_individuality stays False.",
    ),
)


def _analog_switch_cpu_cost(literature_cycles: int) -> int:
    """Map Goldsby 0/25/50 CPU-cycle delays onto this analog's tiny budget."""

    cycles = int(literature_cycles)
    if cycles <= 0:
        return 0
    if cycles <= 25:
        return 2
    return 4


def _instruction_at(rng: _DetRng) -> str:
    index = min(len(COORDINATION_ISA) - 1, int(rng.uniform() * len(COORDINATION_ISA)))
    return COORDINATION_ISA[index]


def random_instruction_genome(rng: _DetRng, length: int = GENOME_LENGTH) -> tuple[str, ...]:
    if length < 1:
        raise ConfigurationError("instruction genome length must be >= 1.")
    return tuple(_instruction_at(rng) for _ in range(length))


def mutate_instruction_genome(
    genome: Sequence[str],
    rng: _DetRng,
    *,
    rate: float = INSTRUCTION_MUTATION_RATE,
) -> tuple[str, ...]:
    items = [str(item) for item in genome]
    if not items:
        raise ConfigurationError("cannot mutate an empty instruction genome.")
    for index, _item in enumerate(items):
        if rng.uniform() < rate:
            items[index] = _instruction_at(rng)
    if items == list(genome):
        items[int(rng.uniform() * len(items)) % len(items)] = _instruction_at(rng)
    return tuple(items)


def _instruction_counts(genome: Sequence[str]) -> dict[str, int]:
    counts = {name: 0 for name in COORDINATION_ISA}
    for item in genome:
        if item in counts:
            counts[item] += 1
    return counts


@dataclass(frozen=True, slots=True)
class CoordinationGroupEvaluation:
    """One group executing instruction genomes on the Phase E buffer."""

    genomes: tuple[tuple[str, ...], ...]
    tasks: tuple[str, ...]
    personal_fitness: tuple[float, ...]
    group_fitness: float
    complementary_payoff: float
    coordination_payoff: float
    n_task_a: int
    n_task_b: int
    n_send: int
    n_retrieve: int
    n_broadcast: int
    successful_retrieve: int
    complementary_retrieve: int
    work_a_counts: tuple[int, ...]
    work_b_counts: tuple[int, ...]
    messaging_enabled: bool
    nmi: float
    phase_e_message_count: int

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "genomes": [list(item) for item in self.genomes],
            "tasks": list(self.tasks),
            "personal_fitness": [round(item, 10) for item in self.personal_fitness],
            "group_fitness": self.group_fitness,
            "complementary_payoff": self.complementary_payoff,
            "coordination_payoff": self.coordination_payoff,
            "n_task_a": self.n_task_a,
            "n_task_b": self.n_task_b,
            "n_send": self.n_send,
            "n_retrieve": self.n_retrieve,
            "n_broadcast": self.n_broadcast,
            "successful_retrieve": self.successful_retrieve,
            "complementary_retrieve": self.complementary_retrieve,
            "work_a_counts": list(self.work_a_counts),
            "work_b_counts": list(self.work_b_counts),
            "messaging_enabled": self.messaging_enabled,
            "nmi": self.nmi,
            "phase_e_message_count": self.phase_e_message_count,
            "collective_intelligence": False,
        }


def evaluate_coordination_group(
    genomes: Sequence[Sequence[str]],
    *,
    messaging_enabled: bool = True,
    cpu_delay_cycles: int = 0,
    cpu_budget: int = CPU_BUDGET,
    deme_id: str = "coord0",
    organism_ids: Sequence[str] | None = None,
) -> CoordinationGroupEvaluation:
    """Lockstep instruction execution. Messaging uses Phase E send/retrieve.

    Coordination pays only when a retrieve reads a peer send/broadcast.
    Complementary retrieve (A-token then work B, or the reverse) pays extra.
    CPU-delay analog: switching work_a↔work_b costs extra analog CPU.
    """

    resolved = tuple(tuple(str(op) for op in genome) for genome in genomes)
    if not resolved:
        raise ConfigurationError("evaluate_coordination_group requires at least one genome.")
    length = len(resolved[0])
    if any(len(item) != length for item in resolved):
        raise ConfigurationError("instruction genomes in a group must be the same length.")
    ids = (
        tuple(str(item) for item in organism_ids)
        if organism_ids is not None
        else tuple(f"org{index}" for index in range(len(resolved)))
    )
    if len(ids) != len(resolved):
        raise ConfigurationError("organism_ids must match genomes.")
    switch_cost = _analog_switch_cpu_cost(cpu_delay_cycles)
    state = DemeState(demes=(Deme(deme_id=deme_id, member_ids=ids),))
    work_a = [0] * len(resolved)
    work_b = [0] * len(resolved)
    last_work = [""] * len(resolved)
    cpu_left = [int(cpu_budget) for _ in resolved]
    retrieved_payload: list[str | None] = [None] * len(resolved)
    n_send = 0
    n_retrieve = 0
    n_broadcast = 0
    successful_retrieve = 0
    complementary_retrieve = 0
    tick = 0
    for step in range(length):
        for index, genome in enumerate(resolved):
            op = genome[step]
            cost = 1
            if op in {ISA_WORK_A, ISA_WORK_B} and last_work[index] and last_work[index] != op:
                cost += switch_cost
            if cpu_left[index] < cost:
                continue
            cpu_left[index] -= cost
            if op == ISA_WORK_A:
                work_a[index] += 1
                last_work[index] = ISA_WORK_A
            elif op == ISA_WORK_B:
                work_b[index] += 1
                last_work[index] = ISA_WORK_B
            elif op == ISA_SEND:
                n_send += 1
                payload = "A" if last_work[index] == ISA_WORK_A else (
                    "B" if last_work[index] == ISA_WORK_B else "cue"
                )
                send_message(
                    state,
                    tick=tick,
                    sender_id=ids[index],
                    deme_id=deme_id,
                    payload=payload,
                    kind=MessageKind.SEND,
                    recipient_ids=(),
                    can_message=messaging_enabled,
                    can_forward=True,
                )
            elif op == ISA_BROADCAST:
                n_broadcast += 1
                payload = "A" if last_work[index] == ISA_WORK_A else (
                    "B" if last_work[index] == ISA_WORK_B else "cue"
                )
                send_message(
                    state,
                    tick=tick,
                    sender_id=ids[index],
                    deme_id=deme_id,
                    payload=payload,
                    kind=MessageKind.BROADCAST,
                    can_message=messaging_enabled,
                    can_forward=messaging_enabled,
                )
            elif op == ISA_RETRIEVE:
                n_retrieve += 1
                if messaging_enabled:
                    message = retrieve_message(state, deme_id=deme_id)
                    if (
                        message is not None
                        and not message.blocked
                        and message.sender_id != ids[index]
                    ):
                        retrieved_payload[index] = str(message.payload)
                        successful_retrieve += 1
            tick += 1
    personal: list[float] = []
    tasks: list[str] = []
    coord_pay = 0.0
    for index in range(len(resolved)):
        payoff = work_a[index] * TASK_A_YIELD + work_b[index] * TASK_B_YIELD
        token = retrieved_payload[index]
        if token is not None:
            coord_pay += COORD_BONUS
            did_a = work_a[index] > 0 or last_work[index] == ISA_WORK_A
            did_b = work_b[index] > 0 or last_work[index] == ISA_WORK_B
            if (token == "A" and did_b) or (token == "B" and did_a):
                coord_pay += COMPLEMENTARY_COORD_BONUS
                complementary_retrieve += 1
        personal.append(round(payoff, 10))
        if work_a[index] > work_b[index]:
            tasks.append(TASK_A)
        elif work_b[index] > work_a[index]:
            tasks.append(TASK_B)
        elif work_a[index] > 0:
            tasks.append(TASK_A)
        else:
            tasks.append(TASK_B if work_b[index] > 0 else TASK_A)
    n_a = sum(1 for task in tasks if task == TASK_A)
    n_b = len(tasks) - n_a
    total_a = sum(work_a) * TASK_A_YIELD
    total_b = sum(work_b) * TASK_B_YIELD
    complementary = round(PAIR_BONUS * min(total_a, total_b), 10)
    coord_pay = round(coord_pay, 10)
    lifetime: list[tuple[str, str]] = []
    for oid, n_a_i, n_b_i in zip(ids, work_a, work_b, strict=True):
        for _ in range(max(1, n_a_i)):
            lifetime.append((oid, TASK_A))
        for _ in range(max(0, n_b_i)):
            lifetime.append((oid, TASK_B))
        if n_a_i == 0 and n_b_i == 0:
            lifetime.append((oid, TASK_A))
    nmi = gorelick_normalized_mutual_information(tuple(lifetime))
    return CoordinationGroupEvaluation(
        genomes=resolved,
        tasks=tuple(tasks),
        personal_fitness=tuple(personal),
        group_fitness=round(complementary + coord_pay, 10),
        complementary_payoff=complementary,
        coordination_payoff=coord_pay,
        n_task_a=n_a,
        n_task_b=n_b,
        n_send=n_send,
        n_retrieve=n_retrieve,
        n_broadcast=n_broadcast,
        successful_retrieve=successful_retrieve,
        complementary_retrieve=complementary_retrieve,
        work_a_counts=tuple(work_a),
        work_b_counts=tuple(work_b),
        messaging_enabled=bool(messaging_enabled),
        nmi=nmi,
        phase_e_message_count=len(state.inbox),
    )


def _eval_instruction_population(
    genomes: Sequence[tuple[str, ...]],
    *,
    group_size: int,
    messaging_enabled: bool,
    cpu_delay_cycles: int,
    id_prefix: str,
) -> tuple[CoordinationGroupEvaluation, ...]:
    groups = _partition(tuple(genomes), group_size)
    rows: list[CoordinationGroupEvaluation] = []
    for index, group in enumerate(groups):
        ids = tuple(f"{id_prefix}:g{index}:o{member}" for member in range(len(group)))
        rows.append(
            evaluate_coordination_group(
                group,
                messaging_enabled=messaging_enabled,
                cpu_delay_cycles=cpu_delay_cycles,
                deme_id=f"{id_prefix}:g{index}",
                organism_ids=ids,
            )
        )
    return tuple(rows)


def _reproduce_instruction_mls(
    groups: Sequence[tuple[tuple[str, ...], ...]],
    group_fitness: Sequence[float],
    rng: _DetRng,
) -> list[tuple[str, ...]]:
    ranked = sorted(
        zip(group_fitness, range(len(groups)), strict=True),
        key=lambda item: (-item[0], item[1]),
    )
    keep = max(1, int(len(groups) * MLS_KEEP_FRACTION))
    parents = [groups[index] for _, index in ranked[:keep]]
    children_groups: list[tuple[tuple[str, ...], ...]] = []
    cursor = 0
    while len(children_groups) < len(groups):
        source = parents[cursor % len(parents)]
        children_groups.append(tuple(mutate_instruction_genome(item, rng) for item in source))
        cursor += 1
    return [genome for group in children_groups for genome in group]


def _reproduce_instruction_organism_only(
    genomes: Sequence[tuple[str, ...]],
    personal: Sequence[float],
    rng: _DetRng,
) -> list[tuple[str, ...]]:
    paired = sorted(
        zip(personal, range(len(genomes)), strict=True),
        key=lambda item: (-item[0], item[1]),
    )
    keep = max(1, int(len(genomes) * MLS_KEEP_FRACTION))
    parents = [genomes[index] for _, index in paired[:keep]]
    children: list[tuple[str, ...]] = []
    cursor = 0
    while len(children) < len(genomes):
        children.append(mutate_instruction_genome(parents[cursor % len(parents)], rng))
        cursor += 1
    rng_order = sorted(((rng.uniform(), item) for item in children), key=lambda row: row[0])
    return [item for _, item in rng_order]


def evolve_instruction_population(
    *,
    seed: int,
    generations: int,
    n_groups: int,
    group_size: int,
    mode: str,
    messaging_enabled: bool = True,
    cpu_delay_cycles: int = 0,
) -> tuple[tuple[tuple[str, ...], ...], tuple[CoordinationGroupEvaluation, ...]]:
    """Evolve discrete send/retrieve/broadcast/work genomes under MLS or organism-only."""

    if mode not in {"organism_only", "mls"}:
        raise ConfigurationError("evolve mode must be organism_only or mls.")
    if generations < 1:
        raise ConfigurationError("generations must be >= 1.")
    rng = _DetRng(seed)
    genomes = [random_instruction_genome(rng) for _ in range(n_groups * group_size)]
    rows = _eval_instruction_population(
        genomes,
        group_size=group_size,
        messaging_enabled=messaging_enabled,
        cpu_delay_cycles=cpu_delay_cycles,
        id_prefix=f"{mode}:{seed}:0",
    )
    for generation in range(1, generations + 1):
        if mode == "organism_only":
            personal = [fit for row in rows for fit in row.personal_fitness]
            genomes = _reproduce_instruction_organism_only(genomes, personal, rng)
        else:
            groups = _partition(tuple(genomes), group_size)
            genomes = _reproduce_instruction_mls(
                groups, tuple(row.group_fitness for row in rows), rng
            )
        rows = _eval_instruction_population(
            genomes,
            group_size=group_size,
            messaging_enabled=messaging_enabled,
            cpu_delay_cycles=cpu_delay_cycles,
            id_prefix=f"{mode}:{seed}:{generation}",
        )
    return tuple(genomes), rows


def _mean_coord_group_fitness(rows: Sequence[CoordinationGroupEvaluation]) -> float:
    return _mean([item.group_fitness for item in rows])


def _mean_coord_nmi(rows: Sequence[CoordinationGroupEvaluation]) -> float:
    return _mean([item.nmi for item in rows])


def _instruction_frequency(
    genomes: Sequence[tuple[str, ...]], instruction: str
) -> float:
    if not genomes:
        return 0.0
    total = sum(sum(1 for op in genome if op == instruction) for genome in genomes)
    slots = sum(len(genome) for genome in genomes)
    return 0.0 if slots <= 0 else round(total / slots, 10)


@dataclass(frozen=True, slots=True)
class EvolvedCoordinationSeedRecord:
    """One seed: evolved instruction genomes vs messaging ablation."""

    seed: int
    mean_group_fitness: float
    ablated_group_fitness: float
    ablation_drop: float
    coordination_payoff: float
    send_frequency: float
    retrieve_frequency: float
    broadcast_frequency: float
    successful_retrieve: int
    evolved_not_assigned: bool
    coordination_pays: bool
    nmi: float

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "seed": self.seed,
            "mean_group_fitness": self.mean_group_fitness,
            "ablated_group_fitness": self.ablated_group_fitness,
            "ablation_drop": self.ablation_drop,
            "coordination_payoff": self.coordination_payoff,
            "send_frequency": self.send_frequency,
            "retrieve_frequency": self.retrieve_frequency,
            "broadcast_frequency": self.broadcast_frequency,
            "successful_retrieve": self.successful_retrieve,
            "evolved_not_assigned": self.evolved_not_assigned,
            "coordination_pays": self.coordination_pays,
            "nmi": self.nmi,
            "collective_intelligence": False,
        }


@dataclass(frozen=True, slots=True)
class EvolvedCoordinationCampaign:
    """Evolved send/retrieve/broadcast analog. Does not set ClaimGate flags."""

    seeds: tuple[int, ...]
    generations: int
    n_groups: int
    group_size: int
    seed_records: tuple[EvolvedCoordinationSeedRecord, ...]
    mean_ablation_drop: float
    mean_coordination_payoff: float
    mean_send_frequency: float
    mean_retrieve_frequency: float
    uses_phase_e_messaging: bool = True
    evolved_not_assigned: bool = True
    uses_capsules: bool = False
    claim_gate_flags_auto_set: bool = False
    coordination_status: str = MEASURED_RUNTIME
    literature_checklist: tuple[tuple[str, str], ...] = LITERATURE_CHECKLIST
    claim_ceiling: str = _CLAIM_CEILING
    schema_version: str = "evolved_coordination_campaign_v1"
    digest: str = ""

    def __post_init__(self) -> None:
        if len(self.seeds) < 2:
            raise ConfigurationError("EvolvedCoordinationCampaign requires seed_count >= 2.")
        if self.generations < 1:
            raise ConfigurationError("generations must be >= 1.")
        for name in (
            "mean_ablation_drop",
            "mean_coordination_payoff",
            "mean_send_frequency",
            "mean_retrieve_frequency",
        ):
            object.__setattr__(self, name, require_finite_float(name, getattr(self, name)))
        if self.claim_gate_flags_auto_set:
            raise ConfigurationError("Phase K must not auto-set ClaimGate flags.")
        if self.claim_ceiling in _FORBIDDEN or self.claim_ceiling != _CLAIM_CEILING:
            raise ConfigurationError("coordination campaign ceiling must stay runtime_observation.")
        computed = canonical_digest(self._payload())
        if self.digest and self.digest != computed:
            raise ConfigurationError("EvolvedCoordinationCampaign digest mismatch.")
        object.__setattr__(self, "digest", computed)

    def _payload(self) -> dict[str, JsonValue]:
        return {
            "schema_version": self.schema_version,
            "seeds": list(self.seeds),
            "generations": self.generations,
            "n_groups": self.n_groups,
            "group_size": self.group_size,
            "seed_records": [item.to_dict() for item in self.seed_records],
            "mean_ablation_drop": self.mean_ablation_drop,
            "mean_coordination_payoff": self.mean_coordination_payoff,
            "mean_send_frequency": self.mean_send_frequency,
            "mean_retrieve_frequency": self.mean_retrieve_frequency,
            "uses_phase_e_messaging": self.uses_phase_e_messaging,
            "evolved_not_assigned": self.evolved_not_assigned,
            "uses_capsules": self.uses_capsules,
            "claim_gate_flags_auto_set": self.claim_gate_flags_auto_set,
            "coordination_status": self.coordination_status,
            "literature_checklist": [[key, text] for key, text in self.literature_checklist],
            "claim_ceiling": self.claim_ceiling,
            "collective_intelligence": False,
            "intelligence": False,
            "limitations": [
                "analog_isa_not_avida_cpp",
                "not_evolved_language",
                "claimgate_flags_not_auto_set",
            ],
        }

    def to_dict(self) -> dict[str, JsonValue]:
        return {**self._payload(), "digest": self.digest}


def run_evolved_coordination_instruction_experiment(
    seeds: Sequence[int] | None = None,
    *,
    seed_count: int | None = None,
    generations: int | None = None,
    n_groups: int | None = None,
    group_size: int = DEFAULT_GROUP_SIZE,
    smoke: bool = False,
    cpu_delay_cycles: int = 0,
) -> EvolvedCoordinationCampaign:
    """MLS-evolve instruction genomes; ablate Phase E messaging. Does not set flags."""

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
    records: list[EvolvedCoordinationSeedRecord] = []
    for seed in seed_tuple:
        genomes, rows = evolve_instruction_population(
            seed=seed,
            generations=gen_count,
            n_groups=groups,
            group_size=group_size,
            mode="mls",
            messaging_enabled=True,
            cpu_delay_cycles=cpu_delay_cycles,
        )
        baseline = _mean_coord_group_fitness(rows)
        ablated_rows = _eval_instruction_population(
            genomes,
            group_size=group_size,
            messaging_enabled=False,
            cpu_delay_cycles=cpu_delay_cycles,
            id_prefix=f"ablate:{seed}",
        )
        ablated = _mean_coord_group_fitness(ablated_rows)
        drop = round(baseline - ablated, 10)
        coord_pay = _mean([item.coordination_payoff for item in rows])
        nmi = _mean_coord_nmi(rows)
        successful = sum(item.successful_retrieve for item in rows)
        pays = drop > ABLATION_DROP_EPSILON and successful > 0
        records.append(
            EvolvedCoordinationSeedRecord(
                seed=seed,
                mean_group_fitness=baseline,
                ablated_group_fitness=ablated,
                ablation_drop=drop,
                coordination_payoff=coord_pay,
                send_frequency=_instruction_frequency(genomes, ISA_SEND),
                retrieve_frequency=_instruction_frequency(genomes, ISA_RETRIEVE),
                broadcast_frequency=_instruction_frequency(genomes, ISA_BROADCAST),
                successful_retrieve=successful,
                evolved_not_assigned=True,
                coordination_pays=pays,
                nmi=nmi,
            )
        )
    campaign = EvolvedCoordinationCampaign(
        seeds=seed_tuple,
        generations=gen_count,
        n_groups=groups,
        group_size=group_size,
        seed_records=tuple(records),
        mean_ablation_drop=_mean([item.ablation_drop for item in records]),
        mean_coordination_payoff=_mean([item.coordination_payoff for item in records]),
        mean_send_frequency=_mean([item.send_frequency for item in records]),
        mean_retrieve_frequency=_mean([item.retrieve_frequency for item in records]),
        uses_phase_e_messaging=True,
        evolved_not_assigned=True,
        uses_capsules=False,
        claim_gate_flags_auto_set=False,
        coordination_status=MEASURED_RUNTIME,
    )
    _assert_ci_blocked(campaign.to_dict(), ScientificClaimGate())
    return campaign


@dataclass(frozen=True, slots=True)
class IsolationCompetenceRecord:
    """Isolation vs group dual-task competence. Not a major transition."""

    group_competence: float
    isolation_competence: float
    isolation_collapse_ratio: float
    isolation_dual_task_failed: bool
    genomes_missing_complementary_work: int
    isolation_collapse_is_cpu_delay: bool
    isolation_collapse_is_payoff_construction: bool
    isolation_collapse_is_evolved_autonomy_loss: bool
    instruction_loss_evolved: bool = False

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "group_competence": self.group_competence,
            "isolation_competence": self.isolation_competence,
            "isolation_collapse_ratio": self.isolation_collapse_ratio,
            "isolation_dual_task_failed": self.isolation_dual_task_failed,
            "genomes_missing_complementary_work": self.genomes_missing_complementary_work,
            "isolation_collapse_is_cpu_delay": self.isolation_collapse_is_cpu_delay,
            "isolation_collapse_is_payoff_construction": (
                self.isolation_collapse_is_payoff_construction
            ),
            "isolation_collapse_is_evolved_autonomy_loss": (
                self.isolation_collapse_is_evolved_autonomy_loss
            ),
            "instruction_loss_evolved": self.instruction_loss_evolved,
            "major_transition_in_individuality": False,
            "collective_intelligence": False,
        }


def measure_isolation_competence(
    genomes: Sequence[tuple[str, ...]],
    *,
    group_size: int,
    cpu_delay_cycles: int,
    ancestral_genomes: Sequence[tuple[str, ...]] | None = None,
    id_prefix: str = "iso",
) -> IsolationCompetenceRecord:
    """Dual-task isolation vs complementary group competence."""

    resolved = tuple(tuple(item) for item in genomes)
    if not resolved:
        raise ConfigurationError("isolation competence needs at least one genome.")
    group_rows = _eval_instruction_population(
        resolved,
        group_size=group_size,
        messaging_enabled=True,
        cpu_delay_cycles=cpu_delay_cycles,
        id_prefix=f"{id_prefix}:group",
    )
    group_competence = _mean_coord_group_fitness(group_rows)
    isolation_scores: list[float] = []
    missing = 0
    delay_blocked = 0
    for index, genome in enumerate(resolved):
        if ISA_WORK_A not in genome or ISA_WORK_B not in genome:
            missing += 1
        solo = evaluate_coordination_group(
            (genome,),
            messaging_enabled=False,
            cpu_delay_cycles=cpu_delay_cycles,
            deme_id=f"{id_prefix}:solo{index}",
            organism_ids=(f"{id_prefix}:o{index}",),
        )
        zero_delay = evaluate_coordination_group(
            (genome,),
            messaging_enabled=False,
            cpu_delay_cycles=0,
            deme_id=f"{id_prefix}:zd{index}",
            organism_ids=(f"{id_prefix}:zd{index}",),
        )
        delay_has_both = solo.work_a_counts[0] > 0 and solo.work_b_counts[0] > 0
        zero_has_both = zero_delay.work_a_counts[0] > 0 and zero_delay.work_b_counts[0] > 0
        if zero_has_both and not delay_has_both:
            delay_blocked += 1
        isolation_scores.append(1.0 if delay_has_both else 0.0)
    isolation = _mean(isolation_scores)
    ratio = 0.0 if group_competence <= 0.0 else round(isolation / group_competence, 10)
    ancestral_missing = 0
    if ancestral_genomes is not None:
        for genome in ancestral_genomes:
            if ISA_WORK_A not in genome or ISA_WORK_B not in genome:
                ancestral_missing += 1
    instruction_loss = missing > ancestral_missing
    return IsolationCompetenceRecord(
        group_competence=group_competence,
        isolation_competence=isolation,
        isolation_collapse_ratio=ratio,
        isolation_dual_task_failed=isolation <= 0.0 < group_competence,
        genomes_missing_complementary_work=missing,
        isolation_collapse_is_cpu_delay=delay_blocked > 0,
        isolation_collapse_is_payoff_construction=False,
        isolation_collapse_is_evolved_autonomy_loss=False,
        instruction_loss_evolved=instruction_loss,
    )


@dataclass(frozen=True, slots=True)
class GoldsbyTreatmentRecord:
    """One delay treatment across replicates. Not the PNAS experiment."""

    literature_delay_cycles: int
    analog_switch_cpu_cost: int
    replicate_count: int
    mean_nmi: float
    mean_group_competence: float
    mean_isolation_competence: float
    mean_isolation_collapse_ratio: float
    specialist_fraction: float
    isolation_dual_task_failed_fraction: float

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "literature_delay_cycles": self.literature_delay_cycles,
            "analog_switch_cpu_cost": self.analog_switch_cpu_cost,
            "replicate_count": self.replicate_count,
            "mean_nmi": self.mean_nmi,
            "mean_group_competence": self.mean_group_competence,
            "mean_isolation_competence": self.mean_isolation_competence,
            "mean_isolation_collapse_ratio": self.mean_isolation_collapse_ratio,
            "specialist_fraction": self.specialist_fraction,
            "isolation_dual_task_failed_fraction": self.isolation_dual_task_failed_fraction,
            "collective_intelligence": False,
        }


@dataclass(frozen=True, slots=True)
class GoldsbyCpuDelayCampaign:
    """Goldsby-scale CPU-delay specialist harness. Research default 50 replicates."""

    seeds: tuple[int, ...]
    generations: int
    n_groups: int
    group_size: int
    literature_delays: tuple[int, ...]
    treatments: tuple[GoldsbyTreatmentRecord, ...]
    research_replicate_default: int = GOLDSBY_RESEARCH_REPLICATE_COUNT
    is_goldsby_2012_pnas_experiment: bool = False
    claim_gate_flags_auto_set: bool = False
    major_transition_in_individuality: bool = False
    goldsby_status: str = MEASURED_RUNTIME
    literature_checklist: tuple[tuple[str, str], ...] = LITERATURE_CHECKLIST
    claim_ceiling: str = _CLAIM_CEILING
    schema_version: str = "goldsby_cpu_delay_campaign_v1"
    digest: str = ""

    def __post_init__(self) -> None:
        if len(self.seeds) < 2:
            raise ConfigurationError("GoldsbyCpuDelayCampaign requires replicate_count >= 2.")
        if self.is_goldsby_2012_pnas_experiment:
            raise ConfigurationError(
                "Phase K must not claim it is the Goldsby 2012 PNAS experiment."
            )
        if self.major_transition_in_individuality:
            raise ConfigurationError(
                "Goldsby campaign must not set major_transition_in_individuality."
            )
        if self.claim_gate_flags_auto_set:
            raise ConfigurationError("Goldsby campaign must not auto-set ClaimGate flags.")
        if self.claim_ceiling != _CLAIM_CEILING:
            raise ConfigurationError("Goldsby campaign ceiling must stay runtime_observation.")
        for name_holder in self.treatments:
            for name in (
                "mean_nmi",
                "mean_group_competence",
                "mean_isolation_competence",
                "mean_isolation_collapse_ratio",
                "specialist_fraction",
                "isolation_dual_task_failed_fraction",
            ):
                require_finite_float(name, getattr(name_holder, name))
        computed = canonical_digest(self._payload())
        if self.digest and self.digest != computed:
            raise ConfigurationError("GoldsbyCpuDelayCampaign digest mismatch.")
        object.__setattr__(self, "digest", computed)

    def _payload(self) -> dict[str, JsonValue]:
        return {
            "schema_version": self.schema_version,
            "seeds": list(self.seeds),
            "generations": self.generations,
            "n_groups": self.n_groups,
            "group_size": self.group_size,
            "literature_delays": list(self.literature_delays),
            "treatments": [item.to_dict() for item in self.treatments],
            "research_replicate_default": self.research_replicate_default,
            "is_goldsby_2012_pnas_experiment": self.is_goldsby_2012_pnas_experiment,
            "claim_gate_flags_auto_set": self.claim_gate_flags_auto_set,
            "major_transition_in_individuality": self.major_transition_in_individuality,
            "goldsby_status": self.goldsby_status,
            "literature_checklist": [[key, text] for key, text in self.literature_checklist],
            "claim_ceiling": self.claim_ceiling,
            "collective_intelligence": False,
            "intelligence": False,
            "limitations": [
                "analog_cpu_delay_not_avida_hardware",
                "not_pnas_2012_fifty_replicate_paper",
                "isolation_failure_is_not_automatically_evolved_autonomy_loss",
                "claimgate_flags_not_auto_set",
            ],
        }

    def to_dict(self) -> dict[str, JsonValue]:
        return {**self._payload(), "digest": self.digest}


def _specialist_fraction(genomes: Sequence[tuple[str, ...]]) -> float:
    if not genomes:
        return 0.0
    specialists = 0
    for genome in genomes:
        has_a = ISA_WORK_A in genome
        has_b = ISA_WORK_B in genome
        if has_a ^ has_b:
            specialists += 1
    return round(specialists / len(genomes), 10)


def run_goldsby_cpu_delay_specialist_campaign(
    seeds: Sequence[int] | None = None,
    *,
    replicate_count: int | None = None,
    generations: int | None = None,
    n_groups: int | None = None,
    group_size: int = DEFAULT_GROUP_SIZE,
    delays: Sequence[int] | None = None,
    smoke: bool = False,
) -> GoldsbyCpuDelayCampaign:
    """0/25/50-cycle analog treatments. Research default 50 replicates; smoke 4."""

    default_reps = GOLDSBY_SMOKE_REPLICATE_COUNT if smoke else GOLDSBY_RESEARCH_REPLICATE_COUNT
    seed_tuple = _resolve_seeds(
        seeds, replicate_count, default_count=default_reps
    )
    gen_count = int(
        SMOKE_GENERATION_COUNT
        if generations is None and smoke
        else RESEARCH_GENERATION_COUNT
        if generations is None
        else generations
    )
    groups = _resolve_group_count(n_groups, smoke=smoke)
    delay_tuple = tuple(int(item) for item in (delays or GOLDSBY_LITERATURE_DELAYS))
    if len(delay_tuple) < 2:
        raise ConfigurationError("Goldsby campaign needs at least two delay treatments.")
    treatments: list[GoldsbyTreatmentRecord] = []
    for delay in delay_tuple:
        nmis: list[float] = []
        groups_c: list[float] = []
        isos: list[float] = []
        ratios: list[float] = []
        specialists: list[float] = []
        failed: list[float] = []
        for seed in seed_tuple:
            ancestral = [
                random_instruction_genome(_DetRng(seed + 901 + delay + index))
                for index in range(groups * group_size)
            ]
            genomes, rows = evolve_instruction_population(
                seed=seed + delay,
                generations=gen_count,
                n_groups=groups,
                group_size=group_size,
                mode="mls",
                messaging_enabled=True,
                cpu_delay_cycles=delay,
            )
            isolation = measure_isolation_competence(
                genomes,
                group_size=group_size,
                cpu_delay_cycles=delay,
                ancestral_genomes=tuple(ancestral),
                id_prefix=f"goldsby:{seed}:{delay}",
            )
            nmis.append(_mean_coord_nmi(rows))
            groups_c.append(isolation.group_competence)
            isos.append(isolation.isolation_competence)
            ratios.append(isolation.isolation_collapse_ratio)
            specialists.append(_specialist_fraction(genomes))
            failed.append(1.0 if isolation.isolation_dual_task_failed else 0.0)
        treatments.append(
            GoldsbyTreatmentRecord(
                literature_delay_cycles=delay,
                analog_switch_cpu_cost=_analog_switch_cpu_cost(delay),
                replicate_count=len(seed_tuple),
                mean_nmi=_mean(nmis),
                mean_group_competence=_mean(groups_c),
                mean_isolation_competence=_mean(isos),
                mean_isolation_collapse_ratio=_mean(ratios),
                specialist_fraction=_mean(specialists),
                isolation_dual_task_failed_fraction=_mean(failed),
            )
        )
    campaign = GoldsbyCpuDelayCampaign(
        seeds=seed_tuple,
        generations=gen_count,
        n_groups=groups,
        group_size=group_size,
        literature_delays=delay_tuple,
        treatments=tuple(treatments),
        research_replicate_default=GOLDSBY_RESEARCH_REPLICATE_COUNT,
        is_goldsby_2012_pnas_experiment=False,
        claim_gate_flags_auto_set=False,
        major_transition_in_individuality=False,
        goldsby_status=MEASURED_RUNTIME,
    )
    _assert_ci_blocked(campaign.to_dict(), ScientificClaimGate())
    return campaign


def _reproduce_organism_only_traced(
    preferences: Sequence[float],
    personal: Sequence[float],
    rng: _DetRng,
) -> tuple[list[float], list[int]]:
    paired = sorted(
        zip(personal, range(len(preferences)), strict=True),
        key=lambda item: (-item[0], item[1]),
    )
    keep = max(1, int(len(preferences) * MLS_KEEP_FRACTION))
    parent_indices = [index for _, index in paired[:keep]]
    children: list[float] = []
    child_parents: list[int] = []
    cursor = 0
    while len(children) < len(preferences):
        parent = parent_indices[cursor % len(parent_indices)]
        children.append(round(_clip01(preferences[parent] + rng.gauss(0.0, MUTATION_SIGMA)), 10))
        child_parents.append(parent)
        cursor += 1
    return children, child_parents


def _reproduce_mls_traced(
    groups: Sequence[tuple[float, ...]],
    group_fitness: Sequence[float],
    rng: _DetRng,
) -> tuple[list[float], list[int]]:
    ranked = sorted(
        zip(group_fitness, range(len(groups)), strict=True),
        key=lambda item: (-item[0], item[1]),
    )
    keep = max(1, int(len(groups) * MLS_KEEP_FRACTION))
    parent_groups = [index for _, index in ranked[:keep]]
    children: list[float] = []
    child_parents: list[int] = []
    cursor = 0
    group_size = len(groups[0]) if groups else 0
    while len(children) < len(groups) * max(1, group_size):
        source_index = parent_groups[cursor % len(parent_groups)]
        source = groups[source_index]
        base = source_index * group_size
        for offset, item in enumerate(source):
            children.append(round(_clip01(item + rng.gauss(0.0, MUTATION_SIGMA)), 10))
            child_parents.append(base + offset)
        cursor += 1
        if group_size <= 0:
            break
    return children[: len(groups) * group_size], child_parents[: len(groups) * group_size]


def _eval_pref_population(
    preferences: Sequence[float],
    *,
    group_size: int,
    rng: _DetRng,
    id_prefix: str,
) -> tuple[TaskGroupEvaluation, ...]:
    from codontrace.genesis.phase_i import evaluate_task_group

    groups = _partition(preferences, group_size)
    rows: list[TaskGroupEvaluation] = []
    for index, group in enumerate(groups):
        ids = tuple(f"{id_prefix}:g{index}:o{member}" for member in range(len(group)))
        rows.append(evaluate_task_group(group, rng=rng, organism_ids=ids))
    return tuple(rows)


@dataclass(frozen=True, slots=True)
class MultiGenerationPriceStep:
    """One generation of Price bookkeeping, including a transmission term."""

    generation: int
    n_organisms: int
    mean_trait_before: float
    mean_trait_after: float
    observed_delta_z: float
    mean_fitness: float
    selection_term: float
    transmission_term: float
    predicted_delta_z: float
    residual: float

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "generation": self.generation,
            "n_organisms": self.n_organisms,
            "mean_trait_before": self.mean_trait_before,
            "mean_trait_after": self.mean_trait_after,
            "observed_delta_z": self.observed_delta_z,
            "mean_fitness": self.mean_fitness,
            "selection_term": self.selection_term,
            "transmission_term": self.transmission_term,
            "predicted_delta_z": self.predicted_delta_z,
            "residual": self.residual,
            "collective_intelligence": False,
        }


@dataclass(frozen=True, slots=True)
class MultiGenerationPricePartition:
    """Multi-generation Price scaffold with an estimated transmission term.

    ``transmission_term_estimated`` is True because parent–offspring Δz is
    recorded after mutation. ``price_equation_complete`` stays False: this is
    analog bookkeeping, not a Price 1970/1972 empirical paper.
    """

    n_generations: int
    n_groups: int
    n_organisms: int
    steps: tuple[MultiGenerationPriceStep, ...]
    mean_selection_term: float
    mean_transmission_term: float
    mean_observed_delta_z: float
    mean_residual: float
    transmission_identity_holds: bool
    last_generation_mls1: Mapping[str, JsonValue]
    transmission_term_estimated: bool = True
    price_equation_complete: bool = False
    major_transition_in_individuality: bool = False
    schema_version: str = "multi_generation_price_partition_v1"
    digest: str = ""

    def __post_init__(self) -> None:
        if self.n_generations < 1 or self.n_organisms < 1:
            raise ConfigurationError("multi-generation Price needs generations and organisms.")
        if self.price_equation_complete:
            raise ConfigurationError("Phase K must not claim a complete Price equation paper.")
        if not self.transmission_term_estimated:
            raise ConfigurationError(
                "Phase K multi-gen Price must record that transmission was estimated."
            )
        if self.major_transition_in_individuality:
            raise ConfigurationError(
                "Price analysis must not set major_transition_in_individuality."
            )
        for name in (
            "mean_selection_term",
            "mean_transmission_term",
            "mean_observed_delta_z",
            "mean_residual",
        ):
            object.__setattr__(self, name, require_finite_float(name, getattr(self, name)))
        computed = canonical_digest(self._payload())
        if self.digest and self.digest != computed:
            raise ConfigurationError("MultiGenerationPricePartition digest mismatch.")
        object.__setattr__(self, "digest", computed)

    def _payload(self) -> dict[str, JsonValue]:
        return {
            "schema_version": self.schema_version,
            "n_generations": self.n_generations,
            "n_groups": self.n_groups,
            "n_organisms": self.n_organisms,
            "steps": [item.to_dict() for item in self.steps],
            "mean_selection_term": self.mean_selection_term,
            "mean_transmission_term": self.mean_transmission_term,
            "mean_observed_delta_z": self.mean_observed_delta_z,
            "mean_residual": self.mean_residual,
            "transmission_identity_holds": self.transmission_identity_holds,
            "last_generation_mls1": dict(self.last_generation_mls1),
            "transmission_term_estimated": self.transmission_term_estimated,
            "price_equation_complete": self.price_equation_complete,
            "major_transition_in_individuality": self.major_transition_in_individuality,
            "collective_intelligence": False,
            "limitations": [
                "transmission_is_mutation_parent_offspring_delta",
                "truncation_selection_not_price_1970_empirical_protocol",
                "not_a_published_price_paper",
            ],
        }

    def to_dict(self) -> dict[str, JsonValue]:
        return {**self._payload(), "digest": self.digest}


def _price_step_from_parent_child(
    *,
    generation: int,
    parent_z: Sequence[float],
    parent_w: Sequence[float],
    child_z: Sequence[float],
    child_parents: Sequence[int],
) -> MultiGenerationPriceStep:
    if len(parent_z) != len(parent_w) or not parent_z:
        raise ConfigurationError("parent trait and fitness must align.")
    if len(child_z) != len(child_parents):
        raise ConfigurationError("child traits must have parent indices.")
    z = [require_finite_float("z", float(item)) for item in parent_z]
    w = [require_finite_float("w", float(item)) for item in parent_w]
    mean_z = sum(z) / len(z)
    mean_w = sum(w) / len(w)
    mean_child = sum(float(item) for item in child_z) / len(child_z)
    observed = round(mean_child - mean_z, 10)
    realized = [0.0] * len(z)
    delta_sum = [0.0] * len(z)
    for child, parent_index in zip(child_z, child_parents, strict=True):
        idx = int(parent_index)
        realized[idx] += 1.0
        delta_sum[idx] += float(child) - z[idx]
    # Realized offspring count is the fitness that makes the Price identity hold
    # under truncation selection. Personal task yield is recorded as mean_fitness.
    selection = 0.0 if len(z) == 0 else population_covariance(realized, z) / (
        sum(realized) / len(realized)
    )
    weighted = 0.0
    weight = 0.0
    for idx, count in enumerate(realized):
        if count <= 0.0:
            continue
        weighted += count * (delta_sum[idx] / count)
        weight += count
    transmission = 0.0 if weight == 0.0 else weighted / weight
    predicted = round(selection + transmission, 10)
    residual = round(observed - predicted, 10)
    return MultiGenerationPriceStep(
        generation=generation,
        n_organisms=len(z),
        mean_trait_before=round(mean_z, 10),
        mean_trait_after=round(mean_child, 10),
        observed_delta_z=observed,
        mean_fitness=round(mean_w, 10),
        selection_term=round(selection, 10),
        transmission_term=round(transmission, 10),
        predicted_delta_z=predicted,
        residual=residual,
    )


def evolve_two_task_population_traced(
    *,
    seed: int,
    generations: int,
    n_groups: int,
    group_size: int,
    mode: str,
) -> tuple[tuple[MultiGenerationPriceStep, ...], tuple[TaskGroupEvaluation, ...]]:
    """Preference analog with parent–offspring pairing for the transmission term."""

    if mode not in {"organism_only", "mls"}:
        raise ConfigurationError("evolve mode must be organism_only or mls.")
    rng = _DetRng(seed)
    prefs = [_clip01(rng.uniform()) for _ in range(n_groups * group_size)]
    rows = _eval_pref_population(
        prefs, group_size=group_size, rng=rng, id_prefix=f"{mode}:{seed}:0"
    )
    steps: list[MultiGenerationPriceStep] = []
    for generation in range(1, generations + 1):
        if mode == "organism_only":
            personal = [fit for row in rows for fit in row.personal_fitness]
            children, parents = _reproduce_organism_only_traced(prefs, personal, rng)
            parent_w = personal
        else:
            grouped = _partition(prefs, group_size)
            children, parents = _reproduce_mls_traced(
                grouped, tuple(row.group_fitness for row in rows), rng
            )
            parent_w = [fit for row in rows for fit in row.personal_fitness]
        steps.append(
            _price_step_from_parent_child(
                generation=generation,
                parent_z=prefs,
                parent_w=parent_w,
                child_z=children,
                child_parents=parents,
            )
        )
        prefs = children
        rows = _eval_pref_population(
            prefs, group_size=group_size, rng=rng, id_prefix=f"{mode}:{seed}:{generation}"
        )
    return tuple(steps), rows


def multi_generation_price_from_steps(
    steps: Sequence[MultiGenerationPriceStep],
    *,
    last_rows: Sequence[TaskGroupEvaluation],
    n_groups: int,
) -> MultiGenerationPricePartition:
    if not steps:
        raise ConfigurationError("multi-generation Price needs at least one step.")
    snapshot = price_partition_from_groups(last_rows)
    residuals = [abs(item.residual) for item in steps]
    partition = MultiGenerationPricePartition(
        n_generations=len(steps),
        n_groups=n_groups,
        n_organisms=steps[-1].n_organisms,
        steps=tuple(steps),
        mean_selection_term=_mean([item.selection_term for item in steps]),
        mean_transmission_term=_mean([item.transmission_term for item in steps]),
        mean_observed_delta_z=_mean([item.observed_delta_z for item in steps]),
        mean_residual=_mean([item.residual for item in steps]),
        transmission_identity_holds=all(value <= PRICE_PARTITION_TOLERANCE for value in residuals),
        last_generation_mls1=snapshot.to_dict(),
        transmission_term_estimated=True,
        price_equation_complete=False,
        major_transition_in_individuality=False,
    )
    _assert_ci_blocked(partition.to_dict(), ScientificClaimGate())
    return partition


@dataclass(frozen=True, slots=True)
class MultiGenerationPriceSeedRecord:
    """One seed: MLS vs organism-only multi-generation Price traces."""

    seed: int
    mls: MultiGenerationPricePartition
    organism_only: MultiGenerationPricePartition

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "seed": self.seed,
            "mls": self.mls.to_dict(),
            "organism_only": self.organism_only.to_dict(),
            "collective_intelligence": False,
        }


@dataclass(frozen=True, slots=True)
class MultiGenerationPriceCampaign:
    """Multi-seed Price analysis with a transmission term. Does not set flags."""

    seeds: tuple[int, ...]
    generations: int
    n_groups: int
    group_size: int
    seed_records: tuple[MultiGenerationPriceSeedRecord, ...]
    mean_mls_selection_term: float
    mean_mls_transmission_term: float
    mean_mls_residual: float
    transmission_identity_holds: bool
    transmission_term_estimated: bool = True
    price_equation_complete: bool = False
    claim_gate_flags_auto_set: bool = False
    major_transition_in_individuality: bool = False
    price_equation_status: str = MEASURED_RUNTIME
    literature_checklist: tuple[tuple[str, str], ...] = LITERATURE_CHECKLIST
    claim_ceiling: str = _CLAIM_CEILING
    schema_version: str = "multi_generation_price_campaign_v1"
    digest: str = ""

    def __post_init__(self) -> None:
        if len(self.seeds) < 2:
            raise ConfigurationError("MultiGenerationPriceCampaign requires seed_count >= 2.")
        if self.generations < 1:
            raise ConfigurationError("generations must be >= 1.")
        if self.price_equation_complete:
            raise ConfigurationError("Phase K must not claim a complete Price equation paper.")
        if not self.transmission_term_estimated:
            raise ConfigurationError("multi-generation Price must mark transmission estimated.")
        if self.major_transition_in_individuality or self.claim_gate_flags_auto_set:
            raise ConfigurationError(
                "Price campaign must not unlock a transition or auto-set flags."
            )
        if self.claim_ceiling != _CLAIM_CEILING:
            raise ConfigurationError("Price campaign ceiling must stay runtime_observation.")
        for name in (
            "mean_mls_selection_term",
            "mean_mls_transmission_term",
            "mean_mls_residual",
        ):
            object.__setattr__(self, name, require_finite_float(name, getattr(self, name)))
        computed = canonical_digest(self._payload())
        if self.digest and self.digest != computed:
            raise ConfigurationError("MultiGenerationPriceCampaign digest mismatch.")
        object.__setattr__(self, "digest", computed)

    def _payload(self) -> dict[str, JsonValue]:
        return {
            "schema_version": self.schema_version,
            "seeds": list(self.seeds),
            "generations": self.generations,
            "n_groups": self.n_groups,
            "group_size": self.group_size,
            "seed_records": [item.to_dict() for item in self.seed_records],
            "mean_mls_selection_term": self.mean_mls_selection_term,
            "mean_mls_transmission_term": self.mean_mls_transmission_term,
            "mean_mls_residual": self.mean_mls_residual,
            "transmission_identity_holds": self.transmission_identity_holds,
            "transmission_term_estimated": self.transmission_term_estimated,
            "price_equation_complete": self.price_equation_complete,
            "claim_gate_flags_auto_set": self.claim_gate_flags_auto_set,
            "major_transition_in_individuality": self.major_transition_in_individuality,
            "price_equation_status": self.price_equation_status,
            "literature_checklist": [[key, text] for key, text in self.literature_checklist],
            "claim_ceiling": self.claim_ceiling,
            "collective_intelligence": False,
            "intelligence": False,
            "limitations": [
                "transmission_is_realized_parent_offspring_delta",
                "not_a_published_price_paper",
                "major_transition_in_individuality_false",
            ],
        }

    def to_dict(self) -> dict[str, JsonValue]:
        return {**self._payload(), "digest": self.digest}


def run_multi_generation_price_analysis(
    seeds: Sequence[int] | None = None,
    *,
    seed_count: int | None = None,
    generations: int | None = None,
    n_groups: int | None = None,
    group_size: int = DEFAULT_GROUP_SIZE,
    smoke: bool = False,
) -> MultiGenerationPriceCampaign:
    """Multi-generation Price with an estimated transmission term. Snapshot MLS1 retained."""

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
    records: list[MultiGenerationPriceSeedRecord] = []
    for seed in seed_tuple:
        mls_steps, mls_rows = evolve_two_task_population_traced(
            seed=seed,
            generations=gen_count,
            n_groups=groups,
            group_size=group_size,
            mode="mls",
        )
        org_steps, org_rows = evolve_two_task_population_traced(
            seed=seed,
            generations=gen_count,
            n_groups=groups,
            group_size=group_size,
            mode="organism_only",
        )
        records.append(
            MultiGenerationPriceSeedRecord(
                seed=seed,
                mls=multi_generation_price_from_steps(
                    mls_steps, last_rows=mls_rows, n_groups=groups
                ),
                organism_only=multi_generation_price_from_steps(
                    org_steps, last_rows=org_rows, n_groups=groups
                ),
            )
        )
    campaign = MultiGenerationPriceCampaign(
        seeds=seed_tuple,
        generations=gen_count,
        n_groups=groups,
        group_size=group_size,
        seed_records=tuple(records),
        mean_mls_selection_term=_mean(
            [item.mls.mean_selection_term for item in records]
        ),
        mean_mls_transmission_term=_mean(
            [item.mls.mean_transmission_term for item in records]
        ),
        mean_mls_residual=_mean([item.mls.mean_residual for item in records]),
        transmission_identity_holds=all(
            item.mls.transmission_identity_holds
            and item.organism_only.transmission_identity_holds
            for item in records
        ),
        transmission_term_estimated=True,
        price_equation_complete=False,
        claim_gate_flags_auto_set=False,
        major_transition_in_individuality=False,
        price_equation_status=MEASURED_RUNTIME,
    )
    _assert_ci_blocked(campaign.to_dict(), ScientificClaimGate())
    return campaign


def _within_group_personal_variance(rows: Sequence[TaskGroupEvaluation]) -> float:
    variances: list[float] = []
    for row in rows:
        values = [float(item) for item in row.personal_fitness]
        if len(values) < 2:
            variances.append(0.0)
            continue
        mean = sum(values) / len(values)
        variances.append(sum((item - mean) ** 2 for item in values) / len(values))
    return _mean(variances)


@dataclass(frozen=True, slots=True)
class CheaterInvasionAssay:
    """Insert a high-personal A specialist. Group replacement is not endogenous suppression."""

    baseline_group_fitness: float
    invaded_group_fitness: float
    group_fitness_drop: float
    cheater_personal_fitness: float
    resident_mean_personal_fitness: float
    suppressed_by_group_selection: bool
    suppression_mechanism: str = "group_replacement_bookkeeping"
    conflict_suppression_endogenous: bool = False

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "baseline_group_fitness": self.baseline_group_fitness,
            "invaded_group_fitness": self.invaded_group_fitness,
            "group_fitness_drop": self.group_fitness_drop,
            "cheater_personal_fitness": self.cheater_personal_fitness,
            "resident_mean_personal_fitness": self.resident_mean_personal_fitness,
            "suppressed_by_group_selection": self.suppressed_by_group_selection,
            "suppression_mechanism": self.suppression_mechanism,
            "conflict_suppression_endogenous": self.conflict_suppression_endogenous,
            "collective_intelligence": False,
        }


def run_cheater_invasion_assay(
    preferences: Sequence[float],
    *,
    seed: int = 11,
    group_size: int | None = None,
) -> CheaterInvasionAssay:
    """Replace one member with an A-only cheater. Endogenous suppression stays False."""

    prefs = tuple(_clip01(float(item)) for item in preferences)
    if len(prefs) < 2:
        raise ConfigurationError("cheater assay needs at least two organisms.")
    size = int(group_size or min(DEFAULT_GROUP_SIZE, len(prefs)))
    if len(prefs) % size:
        prefs = prefs[: len(prefs) - (len(prefs) % size)]
    if len(prefs) < size:
        raise ConfigurationError("cheater assay population must fill at least one group.")
    rng = _DetRng(seed)
    baseline_rows = _eval_pref_population(
        prefs, group_size=size, rng=rng, id_prefix="cheat:base"
    )
    invaded = (0.0,) + prefs[1:]
    invaded_rows = _eval_pref_population(
        invaded, group_size=size, rng=_DetRng(seed + 1), id_prefix="cheat:inv"
    )
    baseline = _mean([item.group_fitness for item in baseline_rows])
    invaded_fit = _mean([item.group_fitness for item in invaded_rows])
    drop = round(baseline - invaded_fit, 10)
    first = invaded_rows[0]
    assay = CheaterInvasionAssay(
        baseline_group_fitness=baseline,
        invaded_group_fitness=invaded_fit,
        group_fitness_drop=drop,
        cheater_personal_fitness=first.personal_fitness[0],
        resident_mean_personal_fitness=_mean(first.personal_fitness[1:])
        if len(first.personal_fitness) > 1
        else 0.0,
        suppressed_by_group_selection=drop > ABLATION_DROP_EPSILON,
        suppression_mechanism="group_replacement_bookkeeping",
        conflict_suppression_endogenous=False,
    )
    _assert_ci_blocked(assay.to_dict(), ScientificClaimGate())
    return assay


@dataclass(frozen=True, slots=True)
class RevertantIsolationAssay:
    """Conlin-style unicell revertant hook. Collapse may still be payoff construction."""

    group_competence: float
    revertant_mean_isolation_fitness: float
    revertant_collapse_ratio: float
    revertant_fitness_collapse: bool
    isolation_collapse_is_payoff_construction: bool = True
    entrenchment_of_multicellularity: bool = False
    revertant_assay_status: str = MEASURED_RUNTIME

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "group_competence": self.group_competence,
            "revertant_mean_isolation_fitness": self.revertant_mean_isolation_fitness,
            "revertant_collapse_ratio": self.revertant_collapse_ratio,
            "revertant_fitness_collapse": self.revertant_fitness_collapse,
            "isolation_collapse_is_payoff_construction": (
                self.isolation_collapse_is_payoff_construction
            ),
            "entrenchment_of_multicellularity": self.entrenchment_of_multicellularity,
            "revertant_assay_status": self.revertant_assay_status,
            "major_transition_in_individuality": False,
            "collective_intelligence": False,
        }


def run_revertant_isolation_assay(
    preferences: Sequence[float],
    *,
    seed: int = 11,
    group_size: int | None = None,
) -> RevertantIsolationAssay:
    """Force isolation (unicell analog) after group evolution. Entrenchment stays False."""

    from codontrace.genesis.phase_i import evaluate_task_group

    prefs = tuple(_clip01(float(item)) for item in preferences)
    if not prefs:
        raise ConfigurationError("revertant assay needs at least one preference.")
    size = int(group_size or min(DEFAULT_GROUP_SIZE, max(2, len(prefs))))
    usable = prefs[: len(prefs) - (len(prefs) % size)] if len(prefs) >= size else prefs
    rng = _DetRng(seed)
    if len(usable) >= size:
        group_rows = _eval_pref_population(
            usable, group_size=size, rng=rng, id_prefix="rev:group"
        )
        group_competence = _mean([item.group_fitness for item in group_rows])
    else:
        group_competence = 0.0
    isolation_rows = [
        evaluate_task_group((pref,), rng=_DetRng(seed + 17 + index), organism_ids=(f"rev:{index}",))
        for index, pref in enumerate(prefs)
    ]
    isolation = _mean([item.group_fitness for item in isolation_rows])
    ratio = 0.0 if group_competence <= 0.0 else round(isolation / group_competence, 10)
    assay = RevertantIsolationAssay(
        group_competence=group_competence,
        revertant_mean_isolation_fitness=isolation,
        revertant_collapse_ratio=ratio,
        revertant_fitness_collapse=isolation < group_competence,
        isolation_collapse_is_payoff_construction=True,
        entrenchment_of_multicellularity=False,
        revertant_assay_status=MEASURED_RUNTIME,
    )
    _assert_ci_blocked(assay.to_dict(), ScientificClaimGate())
    return assay


@dataclass(frozen=True, slots=True)
class ConflictSuppressionObservation:
    """Michod/Conlin measurement hooks. Endogenous flags stay False."""

    mls_within_group_personal_variance: float
    organism_within_group_personal_variance: float
    conflict_index_mls: float
    conflict_index_organism: float
    variance_reduction_under_mls: float
    cheater: CheaterInvasionAssay
    revertant: RevertantIsolationAssay
    conflict_suppression_measured: bool = True
    conflict_suppression_endogenous: bool = False
    germline_sequestration_endogenous: bool = False
    export_of_fitness_detected: bool = False
    major_transition_in_individuality: bool = False
    literature_gap: str = "hooks_not_endogenous_michod_conlin_transition"
    claim_ceiling: str = _CLAIM_CEILING
    schema_version: str = "conflict_suppression_observation_v1"
    digest: str = ""

    def __post_init__(self) -> None:
        for name in (
            "mls_within_group_personal_variance",
            "organism_within_group_personal_variance",
            "conflict_index_mls",
            "conflict_index_organism",
            "variance_reduction_under_mls",
        ):
            object.__setattr__(self, name, require_finite_float(name, getattr(self, name)))
        if self.conflict_suppression_endogenous or self.germline_sequestration_endogenous:
            raise ConfigurationError("Phase K hooks must not claim endogenous suppression.")
        if self.major_transition_in_individuality or self.export_of_fitness_detected:
            raise ConfigurationError("Phase K hooks must not claim a major transition.")
        if self.claim_ceiling != _CLAIM_CEILING:
            raise ConfigurationError("conflict-suppression ceiling must stay runtime_observation.")
        computed = canonical_digest(self._payload())
        if self.digest and self.digest != computed:
            raise ConfigurationError("ConflictSuppressionObservation digest mismatch.")
        object.__setattr__(self, "digest", computed)

    def _payload(self) -> dict[str, JsonValue]:
        return {
            "schema_version": self.schema_version,
            "mls_within_group_personal_variance": self.mls_within_group_personal_variance,
            "organism_within_group_personal_variance": (
                self.organism_within_group_personal_variance
            ),
            "conflict_index_mls": self.conflict_index_mls,
            "conflict_index_organism": self.conflict_index_organism,
            "variance_reduction_under_mls": self.variance_reduction_under_mls,
            "cheater": self.cheater.to_dict(),
            "revertant": self.revertant.to_dict(),
            "conflict_suppression_measured": self.conflict_suppression_measured,
            "conflict_suppression_endogenous": self.conflict_suppression_endogenous,
            "germline_sequestration_endogenous": self.germline_sequestration_endogenous,
            "export_of_fitness_detected": self.export_of_fitness_detected,
            "major_transition_in_individuality": self.major_transition_in_individuality,
            "literature_gap": self.literature_gap,
            "claim_ceiling": self.claim_ceiling,
            "collective_intelligence": False,
            "intelligence": False,
        }

    def to_dict(self) -> dict[str, JsonValue]:
        return {**self._payload(), "digest": self.digest}


def build_conflict_suppression_observation(
    *,
    seed: int = 11,
    generations: int = SMOKE_GENERATION_COUNT,
    n_groups: int = SMOKE_N_GROUPS,
    group_size: int = DEFAULT_GROUP_SIZE,
) -> ConflictSuppressionObservation:
    """Record Michod/Conlin *hooks*. Endogenous and transition flags stay false."""

    from codontrace.genesis.phase_i import evolve_two_task_population

    mls_prefs, mls_rows = evolve_two_task_population(
        seed=seed,
        generations=generations,
        n_groups=n_groups,
        group_size=group_size,
        mode="mls",
    )
    _org_prefs, org_rows = evolve_two_task_population(
        seed=seed,
        generations=generations,
        n_groups=n_groups,
        group_size=group_size,
        mode="organism_only",
    )
    mls_var = _within_group_personal_variance(mls_rows)
    org_var = _within_group_personal_variance(org_rows)
    mls_between = _mean([item.group_fitness for item in mls_rows])
    org_between = _mean([item.group_fitness for item in org_rows])
    mls_index = (
        0.0 if (mls_var + mls_between) <= 0.0 else round(mls_var / (mls_var + mls_between), 10)
    )
    org_index = (
        0.0 if (org_var + org_between) <= 0.0 else round(org_var / (org_var + org_between), 10)
    )
    reduction = 0.0 if org_var <= 0.0 else round((org_var - mls_var) / org_var, 10)
    observation = ConflictSuppressionObservation(
        mls_within_group_personal_variance=mls_var,
        organism_within_group_personal_variance=org_var,
        conflict_index_mls=mls_index,
        conflict_index_organism=org_index,
        variance_reduction_under_mls=reduction,
        cheater=run_cheater_invasion_assay(mls_prefs, seed=seed, group_size=group_size),
        revertant=run_revertant_isolation_assay(mls_prefs, seed=seed, group_size=group_size),
        conflict_suppression_measured=True,
        conflict_suppression_endogenous=False,
        germline_sequestration_endogenous=False,
        export_of_fitness_detected=False,
        major_transition_in_individuality=False,
    )
    _assert_ci_blocked(observation.to_dict(), ScientificClaimGate())
    return observation


def evaluate_phase_k_claim(payload: Mapping[str, JsonValue] | object) -> ClaimDecision:
    """Runtime observation only. Intelligence claims stay blocked."""

    return evaluate_phase_i_claim(payload)
