"""Opt-in Avida Logic-9 / NAND-style reaction → resource → merit/ATP coupling.

Ofria & Wilke 2004 and live ``avida.cfg`` 2.14.0 treat logic tasks as
*reactions* that consume named resources and award merit. The classic Logic-9
tasks are NOT, NAND, AND, ORN, OR, ANDN, NOR, XOR, and EQU. BMC Evol Biol 2021
metabolic-signaling work treats resource × population × mutation as interacting
experimental axes.

CodonTrace uses a different ISA than Avida's NAND CPU. This module is a
**semantic analog**: genome even/odd bits are treated as IO channels A/B; a
task completes when the remaining genome contains the boolean function of A
and B; completion consumes ``res{TASK}`` and awards runtime ATP/merit. Default
off so Phase A–E pins stay stable. Claim ceiling: ``runtime_observation``.
Not an Avida replacement and not metabolic intelligence.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from codontrace._types import JsonValue
from codontrace.errors import ConfigurationError
from codontrace.genesis.canonical import canonical_digest, require_finite_float
from codontrace.genesis.claim_gate import ClaimDecision, ClaimRequest, ScientificClaimGate
from codontrace.genesis.environment import ResourceSpec

_PACK_SCHEMA = "logic9_reaction_pack_v1"
_CLAIM_CEILING = "runtime_observation"
_FORBIDDEN = frozenset(
    {
        "avida_replacement",
        "agi",
        "open_ended_intelligence",
        "associative_learning_proved",
        "tokyo_type1_passed",
    }
)

LOGIC9_TASKS: tuple[str, ...] = (
    "NOT",
    "NAND",
    "AND",
    "ORN",
    "OR",
    "ANDN",
    "NOR",
    "XOR",
    "EQU",
)

LITERATURE_CHECKLIST: tuple[tuple[str, str], ...] = (
    (
        "ofria_wilke_2004_avida",
        "Ofria & Wilke 2004 Artificial Life: environment = resources + reactions; "
        "tasks consume resources and award merit.",
    ),
    (
        "avida_cfg_2_14_0_logic_tasks",
        "Live avida.cfg VERSION_ID 2.14.0 RESOURCE / reaction / LOGIC task group: "
        "NOT NAND AND ORN OR ANDN NOR XOR EQU (Logic-9).",
    ),
    (
        "bmc_evol_biol_2021_metabolic_signaling",
        "BMC Evol Biol 2021 metabolic signaling in Avida: resource × population × "
        "mutation as interacting experimental axes. Recorded here as design axes, "
        "not a replication of that paper.",
    ),
)


def logic9_resource_name(task: str) -> str:
    return f"res{task}"


def logic9_resource_specs(*, initial: float = 8.0, inflow: float = 0.25, outflow: float = 0.01) -> tuple[ResourceSpec, ...]:
    """Avida-parity named resources for Logic-9 reactions (opt-in)."""

    return tuple(
        ResourceSpec(name=logic9_resource_name(task), initial=initial, inflow=inflow, outflow=outflow)
        for task in LOGIC9_TASKS
    )


def _invert_bits(bits: str) -> str:
    return "".join("0" if bit == "1" else "1" for bit in bits)


def _zip_op(left: str, right: str, fn) -> str:  # noqa: ANN001
    n = min(len(left), len(right))
    return "".join("1" if fn(left[i] == "1", right[i] == "1") else "0" for i in range(n))


def logic9_outputs(channel_a: str, channel_b: str) -> dict[str, str]:
    """Boolean Logic-9 functions over bitstring IO channels."""

    n = min(len(channel_a), len(channel_b))
    if n <= 0:
        return {task: "" for task in LOGIC9_TASKS}
    a = channel_a[:n]
    b = channel_b[:n]
    return {
        "NOT": _invert_bits(a),
        "NAND": _zip_op(a, b, lambda x, y: not (x and y)),
        "AND": _zip_op(a, b, lambda x, y: x and y),
        "ORN": _zip_op(a, b, lambda x, y: x or (not y)),
        "OR": _zip_op(a, b, lambda x, y: x or y),
        "ANDN": _zip_op(a, b, lambda x, y: x and (not y)),
        "NOR": _zip_op(a, b, lambda x, y: not (x or y)),
        "XOR": _zip_op(a, b, lambda x, y: x != y),
        "EQU": _zip_op(a, b, lambda x, y: x == y),
    }


def split_io_channels(bits: str, io_width: int = 8) -> tuple[str, str, str]:
    """First ``2 * io_width`` bits are interleaved IO (A even, B odd); rest is output motif."""

    take = min(len(bits), max(0, io_width) * 2)
    head = bits[:take]
    remainder = bits[take:]
    even = head[0::2]
    odd = head[1::2]
    n = min(len(even), len(odd))
    return even[:n], odd[:n], remainder


def detect_logic9_tasks(genome_bits: str, *, io_width: int = 8) -> tuple[str, ...]:
    """Return Logic-9 tasks whose output motif appears in the genome remainder."""

    channel_a, channel_b, remainder = split_io_channels(genome_bits, io_width=io_width)
    if not channel_a or not remainder:
        return ()
    outputs = logic9_outputs(channel_a, channel_b)
    found: list[str] = []
    for task in LOGIC9_TASKS:
        motif = outputs[task]
        if motif and motif in remainder:
            found.append(task)
    return tuple(found)


@dataclass(frozen=True, slots=True)
class Logic9ReactionConfig:
    """Opt-in reaction coupling. Defaults off so A–E pins stay stable."""

    enabled: bool = False
    consume_amount: float = 1.0
    atp_bonus: float = 0.5
    population_size: int = 0
    mutation_bit_flip_rate: float = 0.0

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "consume_amount",
            require_finite_float("consume_amount", self.consume_amount, non_negative=True),
        )
        object.__setattr__(
            self, "atp_bonus", require_finite_float("atp_bonus", self.atp_bonus, non_negative=True)
        )
        if self.population_size < 0:
            raise ConfigurationError("population_size must be >= 0.")
        object.__setattr__(
            self,
            "mutation_bit_flip_rate",
            require_finite_float(
                "mutation_bit_flip_rate", self.mutation_bit_flip_rate, non_negative=True, probability=True
            ),
        )

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "enabled": self.enabled,
            "consume_amount": self.consume_amount,
            "atp_bonus": self.atp_bonus,
            "population_size": self.population_size,
            "mutation_bit_flip_rate": self.mutation_bit_flip_rate,
            "resource_population_mutation_axes": True,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, JsonValue]) -> Logic9ReactionConfig:
        return cls(
            enabled=bool(data.get("enabled", False)),
            consume_amount=float(data.get("consume_amount", 1.0) or 1.0),
            atp_bonus=float(data.get("atp_bonus", 0.5) or 0.5),
            population_size=int(data.get("population_size", 0) or 0),
            mutation_bit_flip_rate=float(data.get("mutation_bit_flip_rate", 0.0) or 0.0),
        )

    def digest(self) -> str:
        return canonical_digest(self.to_dict())


@dataclass(frozen=True, slots=True)
class Logic9ReactionEvent:
    """One reaction firing: task → resource consumption → ATP/merit bonus."""

    tick: int
    organism_id: str
    task: str
    resource_name: str
    consumed: float
    atp_bonus: float
    blocked_reason: str = ""
    genome_digest: str = ""

    def __post_init__(self) -> None:
        if self.task not in LOGIC9_TASKS:
            raise ConfigurationError(f"Unknown Logic-9 task {self.task!r}.")
        object.__setattr__(
            self, "consumed", require_finite_float("consumed", self.consumed, non_negative=True)
        )
        object.__setattr__(
            self, "atp_bonus", require_finite_float("atp_bonus", self.atp_bonus, non_negative=True)
        )

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "tick": self.tick,
            "organism_id": self.organism_id,
            "task": self.task,
            "resource_name": self.resource_name,
            "consumed": self.consumed,
            "atp_bonus": self.atp_bonus,
            "blocked_reason": self.blocked_reason,
            "genome_digest": self.genome_digest,
        }

    def digest(self) -> str:
        return canonical_digest(self.to_dict())


@dataclass(frozen=True, slots=True)
class Logic9ReactionPack:
    """Digest-backed Logic-9 coupling observation. Claim ceiling runtime_observation."""

    config: Logic9ReactionConfig
    events: tuple[Logic9ReactionEvent, ...]
    completed_tasks: tuple[str, ...]
    total_consumed: float
    total_atp_bonus: float
    resource_population_mutation: tuple[float, int, float]
    literature_checklist: tuple[tuple[str, str], ...] = LITERATURE_CHECKLIST
    claim_ceiling: str = _CLAIM_CEILING
    schema_version: str = _PACK_SCHEMA
    digest: str = ""

    def __post_init__(self) -> None:
        if self.claim_ceiling in _FORBIDDEN or self.claim_ceiling != _CLAIM_CEILING:
            raise ConfigurationError("Logic9ReactionPack claim_ceiling must stay runtime_observation.")
        object.__setattr__(
            self,
            "total_consumed",
            require_finite_float("total_consumed", self.total_consumed, non_negative=True),
        )
        object.__setattr__(
            self,
            "total_atp_bonus",
            require_finite_float("total_atp_bonus", self.total_atp_bonus, non_negative=True),
        )
        computed = canonical_digest(self._payload())
        if self.digest and self.digest != computed:
            raise ConfigurationError("Logic9ReactionPack digest mismatch.")
        object.__setattr__(self, "digest", computed)

    def _payload(self) -> dict[str, JsonValue]:
        return {
            "schema_version": self.schema_version,
            "config": self.config.to_dict(),
            "events": [item.to_dict() for item in self.events],
            "completed_tasks": list(self.completed_tasks),
            "total_consumed": self.total_consumed,
            "total_atp_bonus": self.total_atp_bonus,
            "resource_population_mutation": [
                self.resource_population_mutation[0],
                self.resource_population_mutation[1],
                self.resource_population_mutation[2],
            ],
            "literature_checklist": [[key, text] for key, text in self.literature_checklist],
            "claim_ceiling": self.claim_ceiling,
            "avida_replacement": False,
            "limitations": [
                "semantic_analog_not_avida_nand_cpu",
                "not_metabolic_intelligence",
                "bmc_2021_axes_recorded_not_paper_replication",
            ],
        }

    def to_dict(self) -> dict[str, JsonValue]:
        return {**self._payload(), "digest": self.digest}


def _organism_bits_from_run(result: object) -> tuple[tuple[int, str, str, str], ...]:
    rows: list[tuple[int, str, str, str]] = []
    ticks = getattr(result, "ticks", ()) or ()
    for tick in ticks:
        generation = getattr(tick, "generation_result", None)
        if generation is None:
            continue
        index = int(getattr(tick, "index", 0) or 0)
        population = getattr(generation, "population", None)
        organisms = getattr(population, "organisms", ()) if population is not None else ()
        for organism in organisms:
            bits = organism.genome.to_compact()
            rows.append((index, str(organism.id), bits, organism.genome.digest()))
    return tuple(rows)


def build_logic9_reaction_pack(
    result: object,
    config: Logic9ReactionConfig | None = None,
    *,
    pool: Mapping[str, float] | None = None,
) -> Logic9ReactionPack:
    """Score Logic-9 reactions from a run. Default config is disabled (empty pack)."""

    cfg = config or Logic9ReactionConfig()
    events: list[Logic9ReactionEvent] = []
    completed: list[str] = []
    totals_consumed = 0.0
    totals_atp = 0.0
    stocks = {logic9_resource_name(task): float((pool or {}).get(logic9_resource_name(task), 8.0)) for task in LOGIC9_TASKS}
    if cfg.enabled:
        seen: set[tuple[str, str]] = set()
        for tick, organism_id, bits, genome_digest in _organism_bits_from_run(result):
            for task in detect_logic9_tasks(bits):
                key = (organism_id, task)
                if key in seen:
                    continue
                seen.add(key)
                resource = logic9_resource_name(task)
                available = stocks.get(resource, 0.0)
                if available >= cfg.consume_amount:
                    stocks[resource] = round(available - cfg.consume_amount, 10)
                    consumed = cfg.consume_amount
                    bonus = cfg.atp_bonus
                    blocked = ""
                else:
                    consumed = 0.0
                    bonus = 0.0
                    blocked = "insufficient_resource"
                events.append(
                    Logic9ReactionEvent(
                        tick=tick,
                        organism_id=organism_id,
                        task=task,
                        resource_name=resource,
                        consumed=consumed,
                        atp_bonus=bonus,
                        blocked_reason=blocked,
                        genome_digest=genome_digest,
                    )
                )
                if consumed > 0:
                    completed.append(task)
                    totals_consumed = round(totals_consumed + consumed, 10)
                    totals_atp = round(totals_atp + bonus, 10)
    unique_tasks = tuple(dict.fromkeys(completed))
    pop = cfg.population_size
    if pop <= 0 and result is not None:
        spec_pop = getattr(getattr(result, "spec", None), "genome_bits", ())
        pop = len(tuple(spec_pop or ()))
    return Logic9ReactionPack(
        config=cfg,
        events=tuple(events),
        completed_tasks=unique_tasks,
        total_consumed=totals_consumed,
        total_atp_bonus=totals_atp,
        resource_population_mutation=(
            round(sum(stocks.values()), 10),
            pop,
            cfg.mutation_bit_flip_rate,
        ),
    )


def apply_logic9_runtime_bonus(
    organism: object,
    *,
    tick: int,
    config: Logic9ReactionConfig,
    pool: dict[str, float],
) -> tuple[Logic9ReactionEvent, ...]:
    """Runtime hook: consume Logic-9 resources and credit ATP when a task matches.

    Callers must pass ``config.enabled is True``. Default life-loop does not.
    """

    if not config.enabled:
        return ()
    bits = organism.genome.to_compact()
    events: list[Logic9ReactionEvent] = []
    for task in detect_logic9_tasks(bits):
        resource = logic9_resource_name(task)
        available = float(pool.get(resource, 0.0))
        if available < config.consume_amount:
            events.append(
                Logic9ReactionEvent(
                    tick=tick,
                    organism_id=str(organism.id),
                    task=task,
                    resource_name=resource,
                    consumed=0.0,
                    atp_bonus=0.0,
                    blocked_reason="insufficient_resource",
                    genome_digest=organism.genome.digest(),
                )
            )
            continue
        pool[resource] = round(available - config.consume_amount, 10)
        organism.atp_state.credit_runtime(
            config.atp_bonus,
            tick=tick,
            organism_id=str(organism.id),
            codon="",
            action=f"LOGIC9_{task}",
            reason="logic9_reaction_merit",
        )
        events.append(
            Logic9ReactionEvent(
                tick=tick,
                organism_id=str(organism.id),
                task=task,
                resource_name=resource,
                consumed=config.consume_amount,
                atp_bonus=config.atp_bonus,
                genome_digest=organism.genome.digest(),
            )
        )
    return tuple(events)


def evaluate_logic9_reaction_claim(
    pack: Logic9ReactionPack,
    gate: ScientificClaimGate | None = None,
) -> ClaimDecision:
    """Runtime observation only. Avida-replacement remains blocked."""

    resolved = gate or ScientificClaimGate()
    decision = resolved.decide(
        ClaimRequest(_CLAIM_CEILING, {}, evidence_digests=(pack.digest,))
    )
    blocked = resolved.decide(ClaimRequest("avida_replacement", {}))
    if blocked.allowed:
        raise ConfigurationError("avida_replacement must remain blocked.")
    return decision
