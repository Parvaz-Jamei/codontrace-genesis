"""Phase L Avida ORGANISM_MESSAGING / DEME_GROUP *fidelity* analogs.

Measurement-first follow-on after Phase K: closer (still analog) messaging
semantics, Goldsby 2012-aligned specialist measurement, and optional wiring
so a Phase K coordination ablation can feed evidence objects.

None of this is an Avida C++ port. None of it auto-sets ClaimGate flags.
Smoke never earns flags. ``collective_intelligence`` / ``intelligence`` /
AGI stay blocked. ``is_goldsby_2012_pnas_experiment`` stays False.

Claim ceiling: ``runtime_observation``.
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
    DemeConfig,
    DemeReplicationEvent,
    DemeState,
    DifferentiationRole,
    MessageKind,
    RoleKind,
    maybe_replicate_demes,
    role_for_kind,
    send_message,
)
from codontrace.genesis.phase_h import (
    _CLAIM_CEILING,
    RESEARCH_SEED_COUNT,
    SMOKE_SEED_COUNT,
    CommunicationAblationCampaign,
    CommunicationAblationSeedRecord,
    _assert_ci_blocked,
    _cohens_d,
    _mean,
)
from codontrace.genesis.phase_i import (
    ABLATION_DROP_EPSILON,
    DEFAULT_GROUP_SIZE,
    MLS_KEEP_FRACTION,
    PAIR_BONUS,
    RESEARCH_GENERATION_COUNT,
    SMOKE_GENERATION_COUNT,
    TASK_A,
    TASK_A_YIELD,
    TASK_B,
    TASK_B_YIELD,
    CandidateFlagEarnCriteria,
    EarnedCandidateFlags,
    _DetRng,
    _partition,
    _resolve_group_count,
    _resolve_seeds,
    earn_collective_intelligence_candidate_flags,
    evaluate_phase_i_claim,
    gorelick_normalized_mutual_information,
)
from codontrace.genesis.phase_k import (
    GOLDSBY_LITERATURE_DELAYS,
    GOLDSBY_RESEARCH_REPLICATE_COUNT,
    GOLDSBY_SMOKE_REPLICATE_COUNT,
    ISA_BROADCAST,
    ISA_NOP,
    ISA_RETRIEVE,
    ISA_SEND,
    ISA_WORK_A,
    ISA_WORK_B,
    EvolvedCoordinationCampaign,
    _analog_switch_cpu_cost,
    _eval_instruction_population,
    _mean_coord_nmi,
    _specialist_fraction,
    evolve_instruction_population,
    measure_isolation_competence,
    random_instruction_genome,
)

MEASURED_RUNTIME = "measured_runtime_observation"
ISA_BLOCK = MessageKind.BLOCK_PROPAGATION.value
ISA_ROTATE = "rotate_cw"
FIDELITY_ISA: tuple[str, ...] = (
    ISA_SEND,
    ISA_RETRIEVE,
    ISA_BROADCAST,
    ISA_BLOCK,
    ISA_ROTATE,
    ISA_WORK_A,
    ISA_WORK_B,
    ISA_NOP,
)
FIDELITY_GENOME_LENGTH = 8
FIDELITY_CPU_BUDGET = 10
COORD_BONUS = 4.0
COMPLEMENTARY_COORD_BONUS = 3.0
INSTRUCTION_MUTATION_RATE = 0.25
DEFAULT_COLONY_QUOTA_FRACTION = 0.5
DEFAULT_DEME_REPLICATE_THRESHOLD = 0.5

LITERATURE_CHECKLIST: tuple[tuple[str, str], ...] = (
    (
        "avida_organism_messaging_analog",
        "Avida ORGANISM_MESSAGING (devosoft/avida inst-set / wiki): send-msg "
        "to the faced neighbor, retrieve-msg pops a per-organism FIFO, "
        "broadcast-msg fans out, block_propagation suppresses forwarding. "
        "Phase L is a discrete analog on Phase E DemeState — not Avida C++.",
    ),
    (
        "avida_cfg_deme_group_analog",
        "avida.cfg DEME_GROUP / DEMES_GROUP_REPLICATE / GERMLINE and the "
        "devosoft/avida wiki Deme-introduction: mean-fitness group replicate "
        "exporting a germline/propagule and preserving a target deme. Phase L "
        "calls Phase E maybe_replicate_demes. Analog, not a C++ port.",
    ),
    (
        "goldsby_2012_aligned_specialists",
        "Goldsby et al. PNAS 2012 doi:10.1073/pnas.1202233109: behavioral vs "
        "genotypic specialists, clonal-group DoL, colony resource quota, "
        "ancestral vs evolved isolation, delay dose-response. Phase L records "
        "those *measurements*. is_goldsby_2012_pnas_experiment stays False.",
    ),
    (
        "phase_k_coordination_ablation_evidence_feed",
        "Phase K evolved-coordination ablation may optionally feed an evidence "
        "object. ClaimGate flags are never auto-set; smoke never earns; "
        "research-scale payoff drop may *propose* ablation_result only.",
    ),
)


@dataclass(frozen=True, slots=True)
class OrganismMessage:
    """One per-organism inbox item. Analog of an Avida cOrgMessage."""

    sender_id: str
    label: str
    data: str
    tick: int

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "sender_id": self.sender_id,
            "label": self.label,
            "data": self.data,
            "tick": self.tick,
        }


class _DemeMember:
    """Minimal organism stub for Phase E ``maybe_replicate_demes``."""

    def __init__(self, organism_id: str, role: DifferentiationRole | None = None) -> None:
        self.id = organism_id
        self.phase_e_state = _RoleHolder(role) if role is not None else None


class _RoleHolder:
    def __init__(self, role: DifferentiationRole) -> None:
        self.role = role


def _instruction_at(rng: _DetRng) -> str:
    index = min(len(FIDELITY_ISA) - 1, int(rng.uniform() * len(FIDELITY_ISA)))
    return FIDELITY_ISA[index]


def random_fidelity_genome(
    rng: _DetRng, length: int = FIDELITY_GENOME_LENGTH
) -> tuple[str, ...]:
    if length < 1:
        raise ConfigurationError("fidelity genome length must be >= 1.")
    return tuple(_instruction_at(rng) for _ in range(length))


def mutate_fidelity_genome(
    genome: Sequence[str],
    rng: _DetRng,
    *,
    rate: float = INSTRUCTION_MUTATION_RATE,
) -> tuple[str, ...]:
    items = [str(item) for item in genome]
    if not items:
        raise ConfigurationError("cannot mutate an empty fidelity genome.")
    for index, _item in enumerate(items):
        if rng.uniform() < rate:
            items[index] = _instruction_at(rng)
    if items == list(genome):
        items[int(rng.uniform() * len(items)) % len(items)] = _instruction_at(rng)
    return tuple(items)


def _work_label(last_work: str) -> str:
    if last_work == ISA_WORK_A:
        return "A"
    if last_work == ISA_WORK_B:
        return "B"
    return "cue"


def _facing_target(index: int, facing_offset: int, n: int) -> int | None:
    if n < 2:
        return None
    offset = facing_offset % n
    if offset == 0:
        offset = 1
    return (index + offset) % n


@dataclass(frozen=True, slots=True)
class OrganismMessagingEvaluation:
    """One deme executing the ORGANISM_MESSAGING analog. Not Avida C++."""

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
    n_block: int
    n_rotate: int
    successful_retrieve: int
    complementary_retrieve: int
    blocked_broadcasts: int
    work_a_counts: tuple[int, ...]
    work_b_counts: tuple[int, ...]
    behavioral_specialist_count: int
    messaging_enabled: bool
    uses_per_organism_fifo: bool
    uses_facing_neighbor_send: bool
    nmi: float
    phase_e_message_count: int
    deme_replication_events: tuple[DemeReplicationEvent, ...]
    extra_target_deme_preserved: bool
    germline_parent_ids: tuple[str, ...]
    is_avida_cpp_port: bool
    analog_not_port: bool

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
            "n_block": self.n_block,
            "n_rotate": self.n_rotate,
            "successful_retrieve": self.successful_retrieve,
            "complementary_retrieve": self.complementary_retrieve,
            "blocked_broadcasts": self.blocked_broadcasts,
            "work_a_counts": list(self.work_a_counts),
            "work_b_counts": list(self.work_b_counts),
            "behavioral_specialist_count": self.behavioral_specialist_count,
            "messaging_enabled": self.messaging_enabled,
            "uses_per_organism_fifo": self.uses_per_organism_fifo,
            "uses_facing_neighbor_send": self.uses_facing_neighbor_send,
            "nmi": self.nmi,
            "phase_e_message_count": self.phase_e_message_count,
            "deme_replication_events": [item.to_dict() for item in self.deme_replication_events],
            "extra_target_deme_preserved": self.extra_target_deme_preserved,
            "germline_parent_ids": list(self.germline_parent_ids),
            "is_avida_cpp_port": self.is_avida_cpp_port,
            "analog_not_port": self.analog_not_port,
            "collective_intelligence": False,
        }


def evaluate_organism_messaging_group(
    genomes: Sequence[Sequence[str]],
    *,
    messaging_enabled: bool = True,
    cpu_delay_cycles: int = 0,
    cpu_budget: int = FIDELITY_CPU_BUDGET,
    deme_id: str = "msg0",
    organism_ids: Sequence[str] | None = None,
    deme_replicate_threshold: float | None = None,
    replicate_copy_germline: bool = True,
    germline_member_index: int | None = None,
) -> OrganismMessagingEvaluation:
    """Lockstep Avida-like messaging analog on Phase E ``DemeState``.

    Differences from the Phase K shared-inbox analog (honest, still not C++):

    * each organism has a FIFO inbox; ``retrieve_message`` *pops*
    * ``send_message`` targets the faced neighbor (ring + ``rotate_cw``)
    * ``broadcast_message`` fans out to every other member
    * ``block_propagation`` suppresses that organism's later broadcasts
    * optional ``DEME_GROUP`` analog via ``maybe_replicate_demes``
    """

    resolved = tuple(tuple(str(op) for op in genome) for genome in genomes)
    if not resolved:
        raise ConfigurationError("evaluate_organism_messaging_group requires at least one genome.")
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
    n = len(resolved)
    switch_cost = _analog_switch_cpu_cost(cpu_delay_cycles)
    state = DemeState(demes=(Deme(deme_id=deme_id, member_ids=ids),))
    work_a = [0] * n
    work_b = [0] * n
    last_work = [""] * n
    cpu_left = [int(cpu_budget) for _ in resolved]
    facing = [1 for _ in resolved]
    blocked = [False] * n
    inboxes: list[list[OrganismMessage]] = [[] for _ in resolved]
    retrieved_label: list[str | None] = [None] * n
    n_send = 0
    n_retrieve = 0
    n_broadcast = 0
    n_block = 0
    n_rotate = 0
    successful_retrieve = 0
    complementary_retrieve = 0
    blocked_broadcasts = 0
    tick = 0
    def _deliver(target: int, sender: int, label: str, data: str, now: int) -> None:
        inboxes[target].append(
            OrganismMessage(sender_id=ids[sender], label=label, data=data, tick=now)
        )

    for step in range(length):
        for index, genome in enumerate(resolved):
            op = genome[step]
            cost = 1
            if op in {ISA_WORK_A, ISA_WORK_B} and last_work[index] and last_work[index] != op:
                cost += switch_cost
            if cpu_left[index] < cost:
                continue
            cpu_left[index] -= cost
            label = _work_label(last_work[index])
            data = str(work_a[index] + work_b[index])
            if op == ISA_WORK_A:
                work_a[index] += 1
                last_work[index] = ISA_WORK_A
            elif op == ISA_WORK_B:
                work_b[index] += 1
                last_work[index] = ISA_WORK_B
            elif op == ISA_ROTATE:
                n_rotate += 1
                if n > 1:
                    facing[index] = facing[index] % (n - 1) + 1
            elif op == ISA_BLOCK:
                n_block += 1
                blocked[index] = True
                send_message(
                    state,
                    tick=tick,
                    sender_id=ids[index],
                    deme_id=deme_id,
                    payload=label,
                    kind=MessageKind.BLOCK_PROPAGATION,
                    can_message=messaging_enabled,
                    can_forward=False,
                )
            elif op == ISA_SEND:
                n_send += 1
                target = _facing_target(index, facing[index], n)
                recipients = (ids[target],) if target is not None else ()
                message = send_message(
                    state,
                    tick=tick,
                    sender_id=ids[index],
                    deme_id=deme_id,
                    payload=label,
                    kind=MessageKind.SEND,
                    recipient_ids=recipients,
                    can_message=messaging_enabled,
                    can_forward=True,
                )
                if (
                    messaging_enabled
                    and not message.blocked
                    and target is not None
                    and target != index
                ):
                    _deliver(target, index, label, data, tick)
            elif op == ISA_BROADCAST:
                n_broadcast += 1
                can_forward = messaging_enabled and not blocked[index]
                message = send_message(
                    state,
                    tick=tick,
                    sender_id=ids[index],
                    deme_id=deme_id,
                    payload=label,
                    kind=MessageKind.BROADCAST,
                    can_message=messaging_enabled,
                    can_forward=can_forward,
                )
                if blocked[index] or message.blocked or not messaging_enabled:
                    blocked_broadcasts += 1
                elif messaging_enabled and not message.blocked:
                    for other in range(n):
                        if other != index:
                            _deliver(other, index, label, data, tick)
            elif op == ISA_RETRIEVE:
                n_retrieve += 1
                if messaging_enabled and inboxes[index]:
                    popped = inboxes[index].pop(0)
                    if popped.sender_id != ids[index]:
                        retrieved_label[index] = popped.label
                        successful_retrieve += 1
            tick += 1

    personal: list[float] = []
    tasks: list[str] = []
    coord_pay = 0.0
    behavioral_specialists = 0
    for index in range(n):
        payoff = work_a[index] * TASK_A_YIELD + work_b[index] * TASK_B_YIELD
        token = retrieved_label[index]
        if token is not None:
            coord_pay += COORD_BONUS
            did_a = work_a[index] > 0
            did_b = work_b[index] > 0
            if (token == "A" and did_b) or (token == "B" and did_a):
                coord_pay += COMPLEMENTARY_COORD_BONUS
                complementary_retrieve += 1
        personal.append(round(payoff, 10))
        if work_a[index] > 0 and work_b[index] == 0:
            tasks.append(TASK_A)
            behavioral_specialists += 1
        elif work_b[index] > 0 and work_a[index] == 0:
            tasks.append(TASK_B)
            behavioral_specialists += 1
        elif work_a[index] > work_b[index]:
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

    events: tuple[DemeReplicationEvent, ...] = ()
    extra_target = False
    germline_ids: tuple[str, ...] = ()
    if deme_replicate_threshold is not None:
        fitness_by_id = {oid: personal[index] for index, oid in enumerate(ids)}
        members: list[_DemeMember] = []
        for index, oid in enumerate(ids):
            role = None
            if germline_member_index is not None and index == germline_member_index:
                role = role_for_kind(RoleKind.GERMLINE)
            members.append(_DemeMember(oid, role))
        config = DemeConfig(
            enabled=True,
            deme_size=max(1, n),
            messaging_enabled=messaging_enabled,
            replicate_on_mean_fitness=float(deme_replicate_threshold),
            replicate_copy_germline=replicate_copy_germline,
        )
        state, events = maybe_replicate_demes(
            state, members, fitness_by_id, config, tick=tick
        )
        events = tuple(events)
        germline_ids = tuple(
            item.germline_parent_id for item in events if item.germline_parent_id
        )
        extra_target = any(
            deme.deme_id != deme_id and deme.member_ids for deme in state.demes
        )

    return OrganismMessagingEvaluation(
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
        n_block=n_block,
        n_rotate=n_rotate,
        successful_retrieve=successful_retrieve,
        complementary_retrieve=complementary_retrieve,
        blocked_broadcasts=blocked_broadcasts,
        work_a_counts=tuple(work_a),
        work_b_counts=tuple(work_b),
        behavioral_specialist_count=behavioral_specialists,
        messaging_enabled=bool(messaging_enabled),
        uses_per_organism_fifo=True,
        uses_facing_neighbor_send=True,
        nmi=nmi,
        phase_e_message_count=len(state.inbox),
        deme_replication_events=events,
        extra_target_deme_preserved=extra_target,
        germline_parent_ids=germline_ids,
        is_avida_cpp_port=False,
        analog_not_port=True,
    )


def _eval_fidelity_population(
    genomes: Sequence[tuple[str, ...]],
    *,
    group_size: int,
    messaging_enabled: bool,
    cpu_delay_cycles: int,
    id_prefix: str,
    deme_replicate_threshold: float | None,
) -> tuple[OrganismMessagingEvaluation, ...]:
    groups = _partition(tuple(genomes), group_size)
    rows: list[OrganismMessagingEvaluation] = []
    for index, group in enumerate(groups):
        ids = tuple(f"{id_prefix}:g{index}:o{member}" for member in range(len(group)))
        rows.append(
            evaluate_organism_messaging_group(
                group,
                messaging_enabled=messaging_enabled,
                cpu_delay_cycles=cpu_delay_cycles,
                deme_id=f"{id_prefix}:g{index}",
                organism_ids=ids,
                deme_replicate_threshold=deme_replicate_threshold,
            )
        )
    return tuple(rows)


def _reproduce_fidelity_mls(
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
        children_groups.append(tuple(mutate_fidelity_genome(item, rng) for item in source))
        cursor += 1
    return [genome for group in children_groups for genome in group]


def evolve_fidelity_population(
    *,
    seed: int,
    generations: int,
    n_groups: int,
    group_size: int,
    messaging_enabled: bool = True,
    cpu_delay_cycles: int = 0,
    deme_replicate_threshold: float | None = None,
) -> tuple[tuple[tuple[str, ...], ...], tuple[OrganismMessagingEvaluation, ...]]:
    """MLS-evolve ORGANISM_MESSAGING analog genomes. Not Avida hardware."""

    if generations < 1:
        raise ConfigurationError("generations must be >= 1.")
    rng = _DetRng(seed)
    genomes = [random_fidelity_genome(rng) for _ in range(n_groups * group_size)]
    rows = _eval_fidelity_population(
        genomes,
        group_size=group_size,
        messaging_enabled=messaging_enabled,
        cpu_delay_cycles=cpu_delay_cycles,
        id_prefix=f"fid:{seed}:0",
        deme_replicate_threshold=deme_replicate_threshold,
    )
    for generation in range(1, generations + 1):
        groups = _partition(tuple(genomes), group_size)
        genomes = _reproduce_fidelity_mls(
            groups, tuple(row.group_fitness for row in rows), rng
        )
        rows = _eval_fidelity_population(
            genomes,
            group_size=group_size,
            messaging_enabled=messaging_enabled,
            cpu_delay_cycles=cpu_delay_cycles,
            id_prefix=f"fid:{seed}:{generation}",
            deme_replicate_threshold=deme_replicate_threshold,
        )
    return tuple(genomes), rows


@dataclass(frozen=True, slots=True)
class OrganismMessagingSeedRecord:
    """One seed of the messaging-fidelity analog vs ablation."""

    seed: int
    mean_group_fitness: float
    ablated_group_fitness: float
    ablation_drop: float
    successful_retrieve: int
    n_block: int
    n_rotate: int
    n_deme_replications: int
    extra_target_deme_preserved: bool
    coordination_pays: bool

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "seed": self.seed,
            "mean_group_fitness": self.mean_group_fitness,
            "ablated_group_fitness": self.ablated_group_fitness,
            "ablation_drop": self.ablation_drop,
            "successful_retrieve": self.successful_retrieve,
            "n_block": self.n_block,
            "n_rotate": self.n_rotate,
            "n_deme_replications": self.n_deme_replications,
            "extra_target_deme_preserved": self.extra_target_deme_preserved,
            "coordination_pays": self.coordination_pays,
            "collective_intelligence": False,
        }


@dataclass(frozen=True, slots=True)
class OrganismMessagingFidelityCampaign:
    """ORGANISM_MESSAGING + DEME_GROUP analog campaign. Not a C++ port."""

    seeds: tuple[int, ...]
    generations: int
    n_groups: int
    group_size: int
    seed_records: tuple[OrganismMessagingSeedRecord, ...]
    mean_ablation_drop: float
    uses_phase_e_messaging: bool = True
    uses_per_organism_fifo: bool = True
    uses_facing_neighbor_send: bool = True
    uses_block_propagation: bool = True
    uses_deme_group_analog: bool = True
    is_avida_cpp_port: bool = False
    analog_not_port: bool = True
    evolved_not_assigned: bool = True
    uses_capsules: bool = False
    claim_gate_flags_auto_set: bool = False
    messaging_status: str = MEASURED_RUNTIME
    literature_checklist: tuple[tuple[str, str], ...] = LITERATURE_CHECKLIST
    claim_ceiling: str = _CLAIM_CEILING
    schema_version: str = "organism_messaging_fidelity_campaign_v1"
    digest: str = ""

    def __post_init__(self) -> None:
        if len(self.seeds) < 2:
            raise ConfigurationError(
                "OrganismMessagingFidelityCampaign requires seed_count >= 2."
            )
        object.__setattr__(
            self, "mean_ablation_drop", require_finite_float("mean_ablation_drop", self.mean_ablation_drop)
        )
        if self.claim_gate_flags_auto_set:
            raise ConfigurationError("Phase L must not auto-set ClaimGate flags.")
        if self.is_avida_cpp_port or not self.analog_not_port:
            raise ConfigurationError("Phase L must not claim an Avida C++ port.")
        if self.claim_ceiling != _CLAIM_CEILING:
            raise ConfigurationError("messaging fidelity ceiling must stay runtime_observation.")
        computed = canonical_digest(self._payload())
        if self.digest and self.digest != computed:
            raise ConfigurationError("OrganismMessagingFidelityCampaign digest mismatch.")
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
            "uses_phase_e_messaging": self.uses_phase_e_messaging,
            "uses_per_organism_fifo": self.uses_per_organism_fifo,
            "uses_facing_neighbor_send": self.uses_facing_neighbor_send,
            "uses_block_propagation": self.uses_block_propagation,
            "uses_deme_group_analog": self.uses_deme_group_analog,
            "is_avida_cpp_port": self.is_avida_cpp_port,
            "analog_not_port": self.analog_not_port,
            "evolved_not_assigned": self.evolved_not_assigned,
            "uses_capsules": self.uses_capsules,
            "claim_gate_flags_auto_set": self.claim_gate_flags_auto_set,
            "messaging_status": self.messaging_status,
            "literature_checklist": [[key, text] for key, text in self.literature_checklist],
            "claim_ceiling": self.claim_ceiling,
            "collective_intelligence": False,
            "intelligence": False,
            "limitations": [
                "analog_isa_not_avida_cpp",
                "ring_facing_not_avida_grid_neighborhood",
                "deme_group_analog_not_avida_cfg_hardware",
                "claimgate_flags_not_auto_set",
            ],
        }

    def to_dict(self) -> dict[str, JsonValue]:
        return {**self._payload(), "digest": self.digest}


def run_organism_messaging_fidelity_experiment(
    seeds: Sequence[int] | None = None,
    *,
    seed_count: int | None = None,
    generations: int | None = None,
    n_groups: int | None = None,
    group_size: int = DEFAULT_GROUP_SIZE,
    smoke: bool = False,
    cpu_delay_cycles: int = 0,
    deme_replicate_threshold: float | None = DEFAULT_DEME_REPLICATE_THRESHOLD,
) -> OrganismMessagingFidelityCampaign:
    """MLS-evolve the messaging analog; ablate inboxes. Does not set flags."""

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
    records: list[OrganismMessagingSeedRecord] = []
    for seed in seed_tuple:
        _genomes, rows = evolve_fidelity_population(
            seed=seed,
            generations=gen_count,
            n_groups=groups,
            group_size=group_size,
            messaging_enabled=True,
            cpu_delay_cycles=cpu_delay_cycles,
            deme_replicate_threshold=deme_replicate_threshold,
        )
        baseline = _mean([item.group_fitness for item in rows])
        ablated_rows = _eval_fidelity_population(
            _genomes,
            group_size=group_size,
            messaging_enabled=False,
            cpu_delay_cycles=cpu_delay_cycles,
            id_prefix=f"ablate:{seed}",
            deme_replicate_threshold=None,
        )
        ablated = _mean([item.group_fitness for item in ablated_rows])
        drop = round(baseline - ablated, 10)
        successful = sum(item.successful_retrieve for item in rows)
        records.append(
            OrganismMessagingSeedRecord(
                seed=seed,
                mean_group_fitness=baseline,
                ablated_group_fitness=ablated,
                ablation_drop=drop,
                successful_retrieve=successful,
                n_block=sum(item.n_block for item in rows),
                n_rotate=sum(item.n_rotate for item in rows),
                n_deme_replications=sum(len(item.deme_replication_events) for item in rows),
                extra_target_deme_preserved=any(item.extra_target_deme_preserved for item in rows),
                coordination_pays=drop > ABLATION_DROP_EPSILON and successful > 0,
            )
        )
    campaign = OrganismMessagingFidelityCampaign(
        seeds=seed_tuple,
        generations=gen_count,
        n_groups=groups,
        group_size=group_size,
        seed_records=tuple(records),
        mean_ablation_drop=_mean([item.ablation_drop for item in records]),
        uses_deme_group_analog=deme_replicate_threshold is not None,
        claim_gate_flags_auto_set=False,
        messaging_status=MEASURED_RUNTIME,
    )
    _assert_ci_blocked(campaign.to_dict(), ScientificClaimGate())
    return campaign


def _behavioral_specialist_fraction_from_counts(
    work_a: Sequence[int], work_b: Sequence[int]
) -> float:
    if not work_a:
        return 0.0
    specialists = 0
    for n_a, n_b in zip(work_a, work_b, strict=True):
        if (n_a > 0 and n_b == 0) or (n_b > 0 and n_a == 0):
            specialists += 1
    return round(specialists / len(work_a), 10)


def _generalist_residual_fraction(work_a: Sequence[int], work_b: Sequence[int]) -> float:
    if not work_a:
        return 0.0
    generalists = sum(1 for n_a, n_b in zip(work_a, work_b, strict=True) if n_a > 0 and n_b > 0)
    return round(generalists / len(work_a), 10)


def _colony_quota(group_size: int, *, fraction: float = DEFAULT_COLONY_QUOTA_FRACTION) -> tuple[float, float]:
    quota_a = round(max(1, group_size) * TASK_A_YIELD * fraction, 10)
    quota_b = round(max(1, group_size) * TASK_B_YIELD * fraction, 10)
    return quota_a, quota_b


@dataclass(frozen=True, slots=True)
class GoldsbyAlignedSpecialistRecord:
    """Goldsby 2012-aligned specialist *measurement*. Not the PNAS experiment."""

    literature_delay_cycles: int
    analog_switch_cpu_cost: int
    genotypic_specialist_fraction: float
    behavioral_specialist_fraction: float
    generalist_residual_fraction: float
    gorelick_nmi: float
    colony_quota_a: float
    colony_quota_b: float
    colony_quota_met: bool
    colony_quota_is_analog: bool
    clonal_behavioral_nmi: float
    clonal_behavioral_specialist_fraction: float
    clonal_genomes_identical: bool
    ancestral_isolation_competence: float
    evolved_isolation_competence: float
    isolation_competence_delta: float
    isolation_dual_task_failed: bool
    genomes_missing_complementary_work: int
    instruction_loss_evolved: bool
    isolation_collapse_is_cpu_delay: bool
    isolation_collapse_is_payoff_construction: bool
    isolation_collapse_is_evolved_autonomy_loss: bool
    is_goldsby_2012_pnas_experiment: bool
    uses_avida_hardware: bool
    uses_clonal_groups: bool

    def __post_init__(self) -> None:
        if self.is_goldsby_2012_pnas_experiment:
            raise ConfigurationError(
                "Phase L must not claim it is the Goldsby 2012 PNAS experiment."
            )
        if self.isolation_collapse_is_evolved_autonomy_loss:
            raise ConfigurationError(
                "Phase L must not auto-label isolation collapse as evolved autonomy loss."
            )
        if self.uses_avida_hardware:
            raise ConfigurationError("Phase L specialist measurement does not use Avida hardware.")

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "literature_delay_cycles": self.literature_delay_cycles,
            "analog_switch_cpu_cost": self.analog_switch_cpu_cost,
            "genotypic_specialist_fraction": self.genotypic_specialist_fraction,
            "behavioral_specialist_fraction": self.behavioral_specialist_fraction,
            "generalist_residual_fraction": self.generalist_residual_fraction,
            "gorelick_nmi": self.gorelick_nmi,
            "colony_quota_a": self.colony_quota_a,
            "colony_quota_b": self.colony_quota_b,
            "colony_quota_met": self.colony_quota_met,
            "colony_quota_is_analog": self.colony_quota_is_analog,
            "clonal_behavioral_nmi": self.clonal_behavioral_nmi,
            "clonal_behavioral_specialist_fraction": self.clonal_behavioral_specialist_fraction,
            "clonal_genomes_identical": self.clonal_genomes_identical,
            "ancestral_isolation_competence": self.ancestral_isolation_competence,
            "evolved_isolation_competence": self.evolved_isolation_competence,
            "isolation_competence_delta": self.isolation_competence_delta,
            "isolation_dual_task_failed": self.isolation_dual_task_failed,
            "genomes_missing_complementary_work": self.genomes_missing_complementary_work,
            "instruction_loss_evolved": self.instruction_loss_evolved,
            "isolation_collapse_is_cpu_delay": self.isolation_collapse_is_cpu_delay,
            "isolation_collapse_is_payoff_construction": (
                self.isolation_collapse_is_payoff_construction
            ),
            "isolation_collapse_is_evolved_autonomy_loss": (
                self.isolation_collapse_is_evolved_autonomy_loss
            ),
            "is_goldsby_2012_pnas_experiment": self.is_goldsby_2012_pnas_experiment,
            "uses_avida_hardware": self.uses_avida_hardware,
            "uses_clonal_groups": self.uses_clonal_groups,
            "major_transition_in_individuality": False,
            "collective_intelligence": False,
        }


def measure_goldsby_aligned_specialists(
    genomes: Sequence[tuple[str, ...]],
    *,
    group_size: int,
    cpu_delay_cycles: int,
    ancestral_genomes: Sequence[tuple[str, ...]] | None = None,
    id_prefix: str = "goldsby_l",
    colony_quota_fraction: float = DEFAULT_COLONY_QUOTA_FRACTION,
) -> GoldsbyAlignedSpecialistRecord:
    """Behavioral/genotypic specialists, clonal DoL, quota, isolation delta."""

    resolved = tuple(tuple(item) for item in genomes)
    if not resolved:
        raise ConfigurationError("Goldsby-aligned specialist measurement needs genomes.")
    group_rows = _eval_instruction_population(
        resolved,
        group_size=group_size,
        messaging_enabled=True,
        cpu_delay_cycles=cpu_delay_cycles,
        id_prefix=f"{id_prefix}:group",
    )
    work_a = [count for row in group_rows for count in row.work_a_counts]
    work_b = [count for row in group_rows for count in row.work_b_counts]
    quota_a, quota_b = _colony_quota(group_size, fraction=colony_quota_fraction)
    total_a = sum(work_a) * TASK_A_YIELD
    total_b = sum(work_b) * TASK_B_YIELD
    isolation = measure_isolation_competence(
        resolved,
        group_size=group_size,
        cpu_delay_cycles=cpu_delay_cycles,
        ancestral_genomes=ancestral_genomes,
        id_prefix=f"{id_prefix}:iso",
    )
    ancestral_iso = 0.0
    if ancestral_genomes is not None and ancestral_genomes:
        ancestral_record = measure_isolation_competence(
            tuple(tuple(item) for item in ancestral_genomes),
            group_size=group_size,
            cpu_delay_cycles=cpu_delay_cycles,
            id_prefix=f"{id_prefix}:anc",
        )
        ancestral_iso = ancestral_record.isolation_competence
    clone_source = resolved[0]
    clones = (clone_source,) * max(1, group_size)
    clonal = evaluate_organism_messaging_group(
        clones,
        messaging_enabled=True,
        cpu_delay_cycles=cpu_delay_cycles,
        deme_id=f"{id_prefix}:clonal",
        organism_ids=tuple(f"{id_prefix}:c{index}" for index in range(len(clones))),
    )
    return GoldsbyAlignedSpecialistRecord(
        literature_delay_cycles=int(cpu_delay_cycles),
        analog_switch_cpu_cost=_analog_switch_cpu_cost(cpu_delay_cycles),
        genotypic_specialist_fraction=_specialist_fraction(resolved),
        behavioral_specialist_fraction=_behavioral_specialist_fraction_from_counts(work_a, work_b),
        generalist_residual_fraction=_generalist_residual_fraction(work_a, work_b),
        gorelick_nmi=_mean_coord_nmi(group_rows),
        colony_quota_a=quota_a,
        colony_quota_b=quota_b,
        colony_quota_met=total_a >= quota_a and total_b >= quota_b,
        colony_quota_is_analog=True,
        clonal_behavioral_nmi=clonal.nmi,
        clonal_behavioral_specialist_fraction=round(
            clonal.behavioral_specialist_count / max(1, len(clones)), 10
        ),
        clonal_genomes_identical=len({clone_source}) == 1,
        ancestral_isolation_competence=ancestral_iso,
        evolved_isolation_competence=isolation.isolation_competence,
        isolation_competence_delta=round(isolation.isolation_competence - ancestral_iso, 10),
        isolation_dual_task_failed=isolation.isolation_dual_task_failed,
        genomes_missing_complementary_work=isolation.genomes_missing_complementary_work,
        instruction_loss_evolved=isolation.instruction_loss_evolved,
        isolation_collapse_is_cpu_delay=isolation.isolation_collapse_is_cpu_delay,
        isolation_collapse_is_payoff_construction=False,
        isolation_collapse_is_evolved_autonomy_loss=False,
        is_goldsby_2012_pnas_experiment=False,
        uses_avida_hardware=False,
        uses_clonal_groups=True,
    )


@dataclass(frozen=True, slots=True)
class GoldsbyDoseResponseObservation:
    """Delay × specialist / isolation curve. Observation, not the PNAS result."""

    literature_delays: tuple[int, ...]
    specialist_fractions: tuple[float, ...]
    behavioral_specialist_fractions: tuple[float, ...]
    isolation_collapse_fractions: tuple[float, ...]
    nmi_by_delay: tuple[float, ...]
    specialist_fraction_nondecreasing_with_delay: bool
    literature_prediction: str = (
        "Goldsby 2012: higher switch-cost treatments produced more DoL "
        "(Kruskal-Wallis). This analog records the curve; it is not that test."
    )
    is_goldsby_2012_pnas_experiment: bool = False

    def __post_init__(self) -> None:
        if self.is_goldsby_2012_pnas_experiment:
            raise ConfigurationError("dose-response observation must not claim the PNAS experiment.")

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "literature_delays": list(self.literature_delays),
            "specialist_fractions": list(self.specialist_fractions),
            "behavioral_specialist_fractions": list(self.behavioral_specialist_fractions),
            "isolation_collapse_fractions": list(self.isolation_collapse_fractions),
            "nmi_by_delay": list(self.nmi_by_delay),
            "specialist_fraction_nondecreasing_with_delay": (
                self.specialist_fraction_nondecreasing_with_delay
            ),
            "literature_prediction": self.literature_prediction,
            "is_goldsby_2012_pnas_experiment": self.is_goldsby_2012_pnas_experiment,
            "collective_intelligence": False,
        }


@dataclass(frozen=True, slots=True)
class GoldsbyAlignedSpecialistCampaign:
    """Goldsby-aligned specialist harness. Research default 50; not PNAS 2012."""

    seeds: tuple[int, ...]
    generations: int
    n_groups: int
    group_size: int
    literature_delays: tuple[int, ...]
    treatments: tuple[GoldsbyAlignedSpecialistRecord, ...]
    dose_response: GoldsbyDoseResponseObservation
    research_replicate_default: int = GOLDSBY_RESEARCH_REPLICATE_COUNT
    is_goldsby_2012_pnas_experiment: bool = False
    claim_gate_flags_auto_set: bool = False
    major_transition_in_individuality: bool = False
    goldsby_status: str = MEASURED_RUNTIME
    literature_checklist: tuple[tuple[str, str], ...] = LITERATURE_CHECKLIST
    claim_ceiling: str = _CLAIM_CEILING
    schema_version: str = "goldsby_aligned_specialist_campaign_v1"
    digest: str = ""

    def __post_init__(self) -> None:
        if len(self.seeds) < 2:
            raise ConfigurationError(
                "GoldsbyAlignedSpecialistCampaign requires replicate_count >= 2."
            )
        if self.is_goldsby_2012_pnas_experiment:
            raise ConfigurationError(
                "Phase L must not claim it is the Goldsby 2012 PNAS experiment."
            )
        if self.major_transition_in_individuality:
            raise ConfigurationError(
                "Goldsby-aligned campaign must not set major_transition_in_individuality."
            )
        if self.claim_gate_flags_auto_set:
            raise ConfigurationError("Goldsby-aligned campaign must not auto-set ClaimGate flags.")
        if self.claim_ceiling != _CLAIM_CEILING:
            raise ConfigurationError("Goldsby-aligned ceiling must stay runtime_observation.")
        computed = canonical_digest(self._payload())
        if self.digest and self.digest != computed:
            raise ConfigurationError("GoldsbyAlignedSpecialistCampaign digest mismatch.")
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
            "dose_response": self.dose_response.to_dict(),
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
                "colony_quota_is_analog_not_avida_resource",
                "clonal_assay_is_not_goldsby_spatial_colony",
                "isolation_failure_is_not_automatically_evolved_autonomy_loss",
                "claimgate_flags_not_auto_set",
            ],
        }

    def to_dict(self) -> dict[str, JsonValue]:
        return {**self._payload(), "digest": self.digest}


def _nondecreasing(values: Sequence[float]) -> bool:
    return all(values[index] <= values[index + 1] + 1e-12 for index in range(len(values) - 1))


def run_goldsby_aligned_specialist_campaign(
    seeds: Sequence[int] | None = None,
    *,
    replicate_count: int | None = None,
    generations: int | None = None,
    n_groups: int | None = None,
    group_size: int = DEFAULT_GROUP_SIZE,
    delays: Sequence[int] | None = None,
    smoke: bool = False,
) -> GoldsbyAlignedSpecialistCampaign:
    """0/25/50-cycle analog + Goldsby-aligned specialist metrics. Smoke: 4."""

    default_reps = GOLDSBY_SMOKE_REPLICATE_COUNT if smoke else GOLDSBY_RESEARCH_REPLICATE_COUNT
    seed_tuple = _resolve_seeds(seeds, replicate_count, default_count=default_reps)
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
        raise ConfigurationError("Goldsby-aligned campaign needs at least two delay treatments.")
    treatments: list[GoldsbyAlignedSpecialistRecord] = []
    for delay in delay_tuple:
        records: list[GoldsbyAlignedSpecialistRecord] = []
        for seed in seed_tuple:
            ancestral = [
                random_instruction_genome(_DetRng(seed + 1103 + delay + index))
                for index in range(groups * group_size)
            ]
            genomes, _rows = evolve_instruction_population(
                seed=seed + delay,
                generations=gen_count,
                n_groups=groups,
                group_size=group_size,
                mode="mls",
                messaging_enabled=True,
                cpu_delay_cycles=delay,
            )
            records.append(
                measure_goldsby_aligned_specialists(
                    genomes,
                    group_size=group_size,
                    cpu_delay_cycles=delay,
                    ancestral_genomes=tuple(ancestral),
                    id_prefix=f"goldsby_l:{seed}:{delay}",
                )
            )
        treatments.append(
            GoldsbyAlignedSpecialistRecord(
                literature_delay_cycles=delay,
                analog_switch_cpu_cost=_analog_switch_cpu_cost(delay),
                genotypic_specialist_fraction=_mean(
                    [item.genotypic_specialist_fraction for item in records]
                ),
                behavioral_specialist_fraction=_mean(
                    [item.behavioral_specialist_fraction for item in records]
                ),
                generalist_residual_fraction=_mean(
                    [item.generalist_residual_fraction for item in records]
                ),
                gorelick_nmi=_mean([item.gorelick_nmi for item in records]),
                colony_quota_a=records[0].colony_quota_a,
                colony_quota_b=records[0].colony_quota_b,
                colony_quota_met=sum(1 for item in records if item.colony_quota_met) * 2
                >= len(records),
                colony_quota_is_analog=True,
                clonal_behavioral_nmi=_mean([item.clonal_behavioral_nmi for item in records]),
                clonal_behavioral_specialist_fraction=_mean(
                    [item.clonal_behavioral_specialist_fraction for item in records]
                ),
                clonal_genomes_identical=True,
                ancestral_isolation_competence=_mean(
                    [item.ancestral_isolation_competence for item in records]
                ),
                evolved_isolation_competence=_mean(
                    [item.evolved_isolation_competence for item in records]
                ),
                isolation_competence_delta=_mean(
                    [item.isolation_competence_delta for item in records]
                ),
                isolation_dual_task_failed=_mean(
                    [1.0 if item.isolation_dual_task_failed else 0.0 for item in records]
                )
                >= 0.5,
                genomes_missing_complementary_work=int(
                    round(_mean([float(item.genomes_missing_complementary_work) for item in records]))
                ),
                instruction_loss_evolved=any(item.instruction_loss_evolved for item in records),
                isolation_collapse_is_cpu_delay=any(
                    item.isolation_collapse_is_cpu_delay for item in records
                ),
                isolation_collapse_is_payoff_construction=False,
                isolation_collapse_is_evolved_autonomy_loss=False,
                is_goldsby_2012_pnas_experiment=False,
                uses_avida_hardware=False,
                uses_clonal_groups=True,
            )
        )
    geno = tuple(item.genotypic_specialist_fraction for item in treatments)
    dose = GoldsbyDoseResponseObservation(
        literature_delays=delay_tuple,
        specialist_fractions=geno,
        behavioral_specialist_fractions=tuple(
            item.behavioral_specialist_fraction for item in treatments
        ),
        isolation_collapse_fractions=tuple(
            1.0 if item.isolation_dual_task_failed else 0.0 for item in treatments
        ),
        nmi_by_delay=tuple(item.gorelick_nmi for item in treatments),
        specialist_fraction_nondecreasing_with_delay=_nondecreasing(geno),
        is_goldsby_2012_pnas_experiment=False,
    )
    campaign = GoldsbyAlignedSpecialistCampaign(
        seeds=seed_tuple,
        generations=gen_count,
        n_groups=groups,
        group_size=group_size,
        literature_delays=delay_tuple,
        treatments=tuple(treatments),
        dose_response=dose,
        research_replicate_default=GOLDSBY_RESEARCH_REPLICATE_COUNT,
        is_goldsby_2012_pnas_experiment=False,
        claim_gate_flags_auto_set=False,
        major_transition_in_individuality=False,
        goldsby_status=MEASURED_RUNTIME,
    )
    _assert_ci_blocked(campaign.to_dict(), ScientificClaimGate())
    return campaign


def phase_k_coordination_to_communication_ablation(
    campaign: EvolvedCoordinationCampaign,
) -> CommunicationAblationCampaign:
    """Package Phase K ablation numbers as a Phase H-shaped evidence object.

    Does **not** set ``claim_gate_ablation_result_set``. Digests are new.
    """

    records = tuple(
        CommunicationAblationSeedRecord(
            seed=item.seed,
            messaging_on_mean_fitness=item.mean_group_fitness,
            messaging_off_mean_fitness=item.ablated_group_fitness,
            delta=item.ablation_drop,
            messages_on=max(0, item.successful_retrieve),
            messages_off=0,
        )
        for item in campaign.seed_records
    )
    on_fits = [item.messaging_on_mean_fitness for item in records]
    off_fits = [item.messaging_off_mean_fitness for item in records]
    cohens, status = _cohens_d(on_fits, off_fits)
    packed = CommunicationAblationCampaign(
        seeds=campaign.seeds,
        seed_records=records,
        mean_delta=campaign.mean_ablation_drop,
        cohens_d=cohens,
        effect_size_status=status,
        communication_ablation_status=MEASURED_RUNTIME,
        claim_gate_ablation_result_set=False,
    )
    _assert_ci_blocked(packed.to_dict(), ScientificClaimGate())
    return packed


@dataclass(frozen=True, slots=True)
class CoordinationAblationEvidence:
    """Optional Phase K → evidence feed. Never mutates ClaimGate."""

    source_schema: str
    source_digest: str
    seeds: tuple[int, ...]
    generations: int
    mean_ablation_drop: float
    successful_retrieve_total: int
    coordination_pays: bool
    uses_phase_e_messaging: bool
    proposed_flags: EarnedCandidateFlags
    propose_candidate_flags: bool
    claim_gate_flags_auto_set: bool = False
    claim_gate_ablation_result_set: bool = False
    evidence_status: str = MEASURED_RUNTIME
    claim_ceiling: str = _CLAIM_CEILING
    schema_version: str = "coordination_ablation_evidence_v1"
    digest: str = ""

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "mean_ablation_drop",
            require_finite_float("mean_ablation_drop", self.mean_ablation_drop),
        )
        if self.claim_gate_flags_auto_set or self.claim_gate_ablation_result_set:
            raise ConfigurationError(
                "CoordinationAblationEvidence must not auto-set ClaimGate flags."
            )
        if self.claim_ceiling != _CLAIM_CEILING:
            raise ConfigurationError("coordination ablation evidence ceiling must stay runtime_observation.")
        if self.proposed_flags.auto_set:
            raise ConfigurationError("proposed flags must not auto-set ClaimGate.")
        computed = canonical_digest(self._payload())
        if self.digest and self.digest != computed:
            raise ConfigurationError("CoordinationAblationEvidence digest mismatch.")
        object.__setattr__(self, "digest", computed)

    def as_mapping(self) -> dict[str, bool]:
        return self.proposed_flags.as_mapping()

    def _payload(self) -> dict[str, JsonValue]:
        return {
            "schema_version": self.schema_version,
            "source_schema": self.source_schema,
            "source_digest": self.source_digest,
            "seeds": list(self.seeds),
            "generations": self.generations,
            "mean_ablation_drop": self.mean_ablation_drop,
            "successful_retrieve_total": self.successful_retrieve_total,
            "coordination_pays": self.coordination_pays,
            "uses_phase_e_messaging": self.uses_phase_e_messaging,
            "proposed_flags": self.proposed_flags.to_dict(),
            "propose_candidate_flags": self.propose_candidate_flags,
            "claim_gate_flags_auto_set": self.claim_gate_flags_auto_set,
            "claim_gate_ablation_result_set": self.claim_gate_ablation_result_set,
            "evidence_status": self.evidence_status,
            "claim_ceiling": self.claim_ceiling,
            "collective_intelligence": False,
            "intelligence": False,
            "limitations": [
                "feed_does_not_mutate_claimgate",
                "smoke_never_earns",
                "research_scale_and_payoff_drop_required_to_propose_ablation_result",
            ],
        }

    def to_dict(self) -> dict[str, JsonValue]:
        return {**self._payload(), "digest": self.digest}


def feed_phase_k_coordination_ablation_evidence(
    campaign: EvolvedCoordinationCampaign,
    *,
    propose_candidate_flags: bool = False,
    smoke: bool = True,
    criteria: CandidateFlagEarnCriteria | None = None,
) -> CoordinationAblationEvidence:
    """Optionally feed Phase K coordination ablation into an evidence object.

    Default ``propose_candidate_flags=False`` (and ``smoke=True``) packages
    numbers only. Flags are proposed only when the caller opts in *and*
    ``earn_collective_intelligence_candidate_flags`` accepts research scale
    plus a measured payoff drop. ClaimGate is never mutated.
    """

    if campaign.claim_gate_flags_auto_set:
        raise ConfigurationError("source coordination campaign must not auto-set flags.")
    inferred_smoke = True if not propose_candidate_flags else bool(smoke)
    earned = earn_collective_intelligence_candidate_flags(
        coordination=campaign,
        smoke=inferred_smoke,
        criteria=criteria,
    )
    evidence = CoordinationAblationEvidence(
        source_schema=campaign.schema_version,
        source_digest=campaign.digest,
        seeds=campaign.seeds,
        generations=campaign.generations,
        mean_ablation_drop=campaign.mean_ablation_drop,
        successful_retrieve_total=sum(item.successful_retrieve for item in campaign.seed_records),
        coordination_pays=any(item.coordination_pays for item in campaign.seed_records),
        uses_phase_e_messaging=campaign.uses_phase_e_messaging,
        proposed_flags=earned,
        propose_candidate_flags=bool(propose_candidate_flags),
        claim_gate_flags_auto_set=False,
        claim_gate_ablation_result_set=False,
        evidence_status=MEASURED_RUNTIME,
    )
    _assert_ci_blocked(evidence.to_dict(), ScientificClaimGate())
    return evidence


def evaluate_phase_l_claim(payload: Mapping[str, JsonValue] | object) -> ClaimDecision:
    """Runtime observation only. Intelligence claims stay blocked."""

    return evaluate_phase_i_claim(payload)
