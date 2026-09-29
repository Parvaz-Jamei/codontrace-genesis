"""CausalTape-1 harness.

Deterministic mutation-accumulation "tape" built on the CodonTrace engine
primitives (``RNGManager`` forks, ``Mutation`` point operator and
``SemanticGenome``). Every proposed mutation is drawn from a per-tape RNG
stream that advances identically for every counterfactual, so a do()
intervention on one event leaves the rest of the tape bit-identical.

Two substrates are provided:

* ``synthetic`` -- an 18-bit genotype (6 codons x 3 bits) scored by a fully
  specified quadratic fitness map ``F(x) = sum w_i x_i + eps * sum J_ij x_i x_j``.
  Because the map is analytic, exact interventional effects can be validated
  against closed-form values, and epistasis strength ``eps`` can be swept.
* ``agent`` -- the engine-native substrate: the genome is executed by
  ``WhiteBoxAgent`` in a fixed ``World2D`` and the outcome is the closed ATP
  ledger value read from ``ATPAccount`` after a fixed number of steps.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass, field
from pathlib import Path

REPO_SRC = Path(__file__).resolve().parents[1] / "codontrace-genesis" / "src"
if str(REPO_SRC) not in sys.path:
    sys.path.insert(0, str(REPO_SRC))

import numpy as np  # noqa: E402

from codontrace.agent import WhiteBoxAgent  # noqa: E402
from codontrace.codon import CodonTable  # noqa: E402
from codontrace.energy import ATPAccount  # noqa: E402
from codontrace.genome import SemanticGenome  # noqa: E402
from codontrace.mutation import Mutation  # noqa: E402
from codontrace.rng import RNGManager  # noqa: E402

CODON_TABLE = CodonTable.default_minimal()
CODONS = 6
WIDTH = 3
BITS = CODONS * WIDTH
ENV_SEED = 20260927

AGENT_WORLD = """
.......
.*.....
.......
...*...
.......
.....*.
.......
"""

AGENT_STEPS = 24


# --------------------------------------------------------------------------
# environment
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class Env:
    """Fully specified synthetic fitness map over the 18-bit genotype."""

    weights: tuple[float, ...]
    couplings: tuple[tuple[float, ...], ...]
    eps: float
    theta: float

    def fitness(self, bits: np.ndarray) -> float:
        linear = float(np.dot(np.asarray(self.weights), bits))
        pair = 0.0
        coupling = np.asarray(self.couplings)
        pair = float(0.5 * bits @ coupling @ bits)
        return linear + self.eps * pair

    def analytic_clear_delta(self, bits: np.ndarray, bit: int) -> float:
        """Exact change in F when ``bit`` is forced to 0, other bits held fixed."""

        if bits[bit] == 0:
            return 0.0
        cleared = bits.copy()
        cleared[bit] = 0
        return float(self.fitness(cleared) - self.fitness(bits))


def build_env(eps: float, *, theta_scale: float = 0.72, env_seed: int = ENV_SEED) -> Env:
    """Build a fixed environment; weights/couplings depend on ``env_seed`` only.

    The coupling matrix is symmetric with a zero diagonal, so the quadratic
    term equals ``sum_{i<j} J_ij x_i x_j`` and the isolated effect of flipping
    bit ``i`` on the ancestor background ``x = 0`` is exactly ``w_i``.
    """

    stream = RNGManager(seed=env_seed).fork("env")
    weights = tuple(0.5 + stream.random() for _ in range(BITS))
    grid = [[0.0] * BITS for _ in range(BITS)]
    for i in range(BITS):
        for j in range(i + 1, BITS):
            value = 1.0 if stream.randrange(2) == 0 else -1.0
            grid[i][j] = value
            grid[j][i] = value
    couplings = tuple(tuple(row) for row in grid)
    theta = theta_scale * float(sum(weights))
    return Env(weights=weights, couplings=couplings, eps=eps, theta=theta)


# --------------------------------------------------------------------------
# substrates
# --------------------------------------------------------------------------


def bits_of(genome: SemanticGenome) -> np.ndarray:
    return np.array([int(sym) for codon in genome.to_codons() for sym in codon], dtype=float)


def agent_outcome(genome: SemanticGenome, *, steps: int = AGENT_STEPS) -> float:
    """Engine-native outcome: resource credit actually banked by the agent.

    The first version of this port used remaining ATP, which is monotonically
    decreasing in activity, so selection never accepted any mutation and every
    seed returned the same value. The outcome is therefore the closed-ledger
    resource credit read out of the trace (``resource_credit`` in
    ``world_delta``), with remaining ATP as a tiny tie-breaker.
    """

    from codontrace.world import World2D

    world = World2D.from_ascii(AGENT_WORLD)
    agent = WhiteBoxAgent(
        id="tape-agent",
        genome=genome,
        codon_table=CODON_TABLE,
        atp_account=ATPAccount(initial_atp=20.0),
        position=(1, 1),
    )
    trace = agent.run(world, steps=steps)
    credit = 0.0
    visited: set[tuple[int, int]] = {(1, 1)}
    for event in trace:
        value = event.world_delta.get("resource_credit", 0.0)
        credit += float(value) if isinstance(value, (int, float)) else 0.0
        position = tuple(event.position_after)
        if len(position) == 2:
            visited.add((int(position[0]), int(position[1])))
    # A pure resource-credit outcome leaves the all-wait ancestor in a neutral
    # valley: no single point mutation reaches a COLLECT codon, so selection
    # accepts nothing and the tape is frozen. Exploration credit keeps the
    # landscape responsive while remaining a deterministic function of the trace.
    return len(visited) + 5.0 * credit + 1e-6 * float(agent.atp_account.current_atp)


# --------------------------------------------------------------------------
# tape
# --------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class TapeEvent:
    generation: int
    mutation_id: str
    bit: int
    old: str
    new: str
    accepted: bool
    delta_fitness: float
    suppressed: bool


@dataclass(slots=True)
class TapeResult:
    seed: int
    final_bits: tuple[int, ...]
    fitness: float
    genome_digest: str
    rng_digest: str
    events: list[TapeEvent] = field(default_factory=list)
    suppressed_hits: int = 0
    schedule_digest: str = ""

    def mutation_ids(self) -> set[str]:
        return {ev.mutation_id for ev in self.events if ev.accepted and not ev.suppressed}

    def present(self, mutation_id: str) -> bool:
        return mutation_id in self.mutation_ids()

    def digest(self) -> str:
        return f"{self.rng_digest}:{self.genome_digest}:{self.fitness!r}"


def _diff_mutation(before: str, after: str) -> tuple[int, str, str]:
    for index, (old, new) in enumerate(zip(before, after, strict=True)):
        if old != new:
            return index, old, new
    msg = "mutation log did not change the genome"
    raise RuntimeError(msg)


def _fast_point(genome: SemanticGenome, stream: RNGManager) -> tuple[SemanticGenome, int, str, str]:
    """Draw and apply a point mutation using exactly the draws ``Mutation.point`` makes.

    ``Mutation.apply`` additionally runs a behavioural-validity mini-trial per
    call, which is ~3 ms per generation. This path keeps the identical draw
    order (index, bit, replacement) and is proven equivalent in gate C.
    """

    spec = genome.spec
    codons = list(genome.to_codons())
    codon_index = stream.randrange(len(codons))
    bit_index = stream.randrange(spec.codon_width)
    original = codons[codon_index]
    choices = tuple(symbol for symbol in spec.alphabet if symbol != original[bit_index])
    replacement = stream.choice(choices)
    codons[codon_index] = original[:bit_index] + replacement + original[bit_index + 1 :]
    child = SemanticGenome.from_codons(codons, spec=spec)
    before = genome.to_compact()
    after = child.to_compact()
    flat, old, new = _diff_mutation(before, after)
    return child, flat, old, new


def run_tape(
    *,
    seed: int,
    generations: int,
    env: Env | None = None,
    substrate: str = "synthetic",
    suppress: frozenset[str] = frozenset(),
    accept_all: bool = False,
    founder: SemanticGenome | None = None,
    agent_steps: int = 8,
    proposal: str = "fast",
) -> TapeResult:
    """Run one deterministic tape.

    ``suppress`` holds mutation ids of the form ``"<bit>:<old>><new>"``. When a
    drawn proposal matches a suppressed id it is *not applied*, but the RNG
    stream still advances exactly as it would have, so suppressing one event is
    a minimal do() intervention on that event only.
    """

    stream = RNGManager(seed=seed).fork("tape")
    genome = founder if founder is not None else SemanticGenome.from_codons(["000"] * CODONS)
    bits = bits_of(genome)

    def score(candidate: SemanticGenome, candidate_bits: np.ndarray) -> float:
        if substrate == "synthetic":
            if env is None:
                msg = "synthetic substrate requires an Env"
                raise ValueError(msg)
            return env.fitness(candidate_bits)
        if substrate == "agent":
            return agent_outcome(candidate, steps=agent_steps)
        msg = f"unknown substrate {substrate!r}"
        raise ValueError(msg)

    current_fitness = score(genome, bits)
    events: list[TapeEvent] = []
    hits = 0

    for generation in range(1, generations + 1):
        if proposal == "engine":
            mutation = Mutation(operation="point", rng=stream)
            candidate = mutation.apply(
                genome, parent_id="tape", generation=generation, codon_table=CODON_TABLE
            )
            log = mutation.last_log[0]
            bit, old, new = _diff_mutation(log.before_genome, log.after_genome)
        elif proposal == "fast":
            candidate, bit, old, new = _fast_point(genome, stream)
        else:
            msg = f"unknown proposal mode {proposal!r}"
            raise ValueError(msg)
        mutation_id = f"{bit}:{old}>{new}"
        candidate_bits = bits_of(candidate)
        candidate_fitness = score(candidate, candidate_bits)

        if mutation_id in suppress:
            hits += 1
            events.append(
                TapeEvent(
                    generation=generation,
                    mutation_id=mutation_id,
                    bit=bit,
                    old=old,
                    new=new,
                    accepted=False,
                    delta_fitness=float(candidate_fitness - current_fitness),
                    suppressed=True,
                )
            )
            continue

        accept = True if accept_all else candidate_fitness > current_fitness
        events.append(
            TapeEvent(
                generation=generation,
                mutation_id=mutation_id,
                bit=bit,
                old=old,
                new=new,
                accepted=accept,
                delta_fitness=float(candidate_fitness - current_fitness),
                suppressed=False,
            )
        )
        if accept:
            genome = candidate
            bits = candidate_bits
            current_fitness = candidate_fitness

    return TapeResult(
        seed=seed,
        final_bits=tuple(int(value) for value in bits),
        fitness=float(current_fitness),
        genome_digest=genome.digest(),
        rng_digest=stream.state_digest(),
        events=events,
        suppressed_hits=hits,
    )


# --------------------------------------------------------------------------
# scheduled tapes: the order intervention
# --------------------------------------------------------------------------


def record_schedule(tape: TapeResult) -> tuple[tuple[int, str], ...]:
    """Return the proposal sequence as ``(bit, target_symbol)`` pairs.

    A drawn point mutation always targets a symbol different from the current
    one, so the schedule fully determines what the tape proposed, independent of
    the order in which those proposals are later applied.
    """

    return tuple((event.bit, event.new) for event in tape.events)


def schedule_digest(schedule: tuple[tuple[int, str], ...]) -> str:
    import hashlib

    payload = ";".join(f"{bit}>{target}" for bit, target in schedule)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def run_scheduled_tape(
    *,
    seed: int,
    schedule: tuple[tuple[int, str], ...],
    env: Env | None = None,
    substrate: str = "synthetic",
    accept_all: bool = False,
    founder: SemanticGenome | None = None,
    agent_steps: int = AGENT_STEPS,
    proposal: str = "fast",
) -> TapeResult:
    """Apply an explicit proposal sequence in the given order.

    The schedule is applied to the same founder with the same selection rule as
    :func:`run_tape`, so replaying a recorded schedule in its recorded order
    reproduces the draw-driven tape exactly (gate E), while replaying a
    permutation of it is the order intervention.
    """

    if substrate == "synthetic" and env is None:
        msg = "synthetic substrate requires an Env"
        raise ValueError(msg)

    genome = founder if founder is not None else SemanticGenome.from_codons(["000"] * CODONS)

    def score(candidate: SemanticGenome) -> float:
        if substrate == "synthetic":
            assert env is not None
            return env.fitness(bits_of(candidate))
        return agent_outcome(candidate, steps=agent_steps)

    bits = bits_of(genome)
    current_fitness = score(genome)
    events: list[TapeEvent] = []

    for generation, (bit, target) in enumerate(schedule, start=1):
        current_symbol = str(int(bits[bit]))
        if current_symbol == target:
            events.append(
                TapeEvent(
                    generation=generation,
                    mutation_id=f"{bit}:{current_symbol}>{target}",
                    bit=bit,
                    old=current_symbol,
                    new=target,
                    accepted=False,
                    delta_fitness=0.0,
                    suppressed=True,
                )
            )
            continue

        codons = list(genome.to_codons())
        codon_index, offset = divmod(bit, WIDTH)
        codons[codon_index] = codons[codon_index][:offset] + target + codons[codon_index][offset + 1 :]
        candidate = SemanticGenome.from_codons(codons, spec=genome.spec)
        candidate_fitness = score(candidate)

        accept = True if accept_all else candidate_fitness > current_fitness
        events.append(
            TapeEvent(
                generation=generation,
                mutation_id=f"{bit}:{current_symbol}>{target}",
                bit=bit,
                old=current_symbol,
                new=target,
                accepted=accept,
                delta_fitness=float(candidate_fitness - current_fitness),
                suppressed=False,
            )
        )
        if accept:
            genome = candidate
            bits = bits_of(genome)
            current_fitness = candidate_fitness

    return TapeResult(
        seed=seed,
        final_bits=tuple(int(value) for value in bits),
        fitness=float(current_fitness),
        genome_digest=genome.digest(),
        rng_digest="",
        events=events,
        suppressed_hits=sum(1 for event in events if event.suppressed),
        schedule_digest=schedule_digest(schedule),
    )
