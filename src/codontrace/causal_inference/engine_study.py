"""Section 7: causal diagrams over engine variables, validated by reruns.

Variables are named by layer:

* ``env:<name>``: an exogenous setting of the run (here the founding
  population size of :meth:`GenesisRuntimeProfile.life_loop_world`),
* ``bit:<i>``: bit ``i`` of the founder genome (bit level),
* ``genome:<name>``: a genome-level summary,
* ``event:<name>``: a count of engine events (here ``birth_event_records``).

``do(bit:i = b)`` is a real engine intervention: the founders that carry the
preset's primary genome get bit ``i`` set to ``b`` in
``GenesisExperimentSpec.genome_bits`` and the engine is rerun with the same
seed (common random numbers; the rest of the spec is unchanged). The engine
is not modified.

:class:`EngineBitStudy` draws an *observational* sample in which the focal
bit is assigned with probabilities that depend on the environment and on the
background bit (confounding by design, drawn from ``RNGManager``), runs the
engine for every unit, identifies ``E[Y | do(focal)]`` from the diagram with
ID, estimates it on the observational sample, and compares it with the ground
truth from interventional reruns of the *same* units (each unit's seed,
environment and background, with the focal bit forced to 0 and to 1).
"""

from __future__ import annotations

import dataclasses
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from functools import lru_cache

from codontrace.errors import ConfigurationError
from codontrace.rng import RNGManager

from .expressions import DiscreteJoint, Expression
from .graph import CausalDiagram
from .identification import NotIdentifiable, identify

__all__ = [
    "EngineBitStudy",
    "EngineUnit",
    "EngineValidationReport",
    "life_loop_births",
    "set_founder_bits",
    "DIRECTED_EVIDENCE_RELATIONS",
    "diagram_from_evidence_graph",
]


def set_founder_bits(genome_bits: Sequence[str], bits: Mapping[int, int]) -> tuple[str, ...]:
    """Apply ``do(bit:i = v)`` to every founder that carries the primary genome."""
    primary = genome_bits[0]
    for i, v in bits.items():
        if not 0 <= i < len(primary) or v not in (0, 1):
            raise ConfigurationError(f"invalid bit intervention {i}={v} for {primary!r}")

    def edit(g: str) -> str:
        chars = list(g)
        for i, v in bits.items():
            chars[i] = str(v)
        return "".join(chars)

    return tuple(edit(g) if g == primary else g for g in genome_bits)


@lru_cache(maxsize=4096)
def _births(seed: int, population: int, bits: tuple[tuple[int, int], ...], ticks: int) -> int:
    from codontrace.genesis import GenesisEngine, GenesisRuntimeProfile

    spec = GenesisRuntimeProfile.life_loop_world(seed=seed, tick_count=ticks, population=population)
    spec = dataclasses.replace(spec, genome_bits=set_founder_bits(spec.genome_bits, dict(bits)))
    return len(GenesisEngine.from_spec(spec).run_ticks().birth_event_records)


def life_loop_births(seed: int, population: int, bits: Mapping[int, int], ticks: int) -> int:
    """Number of birth events in one engine run of the life-loop preset."""
    return _births(int(seed), int(population), tuple(sorted(bits.items())), int(ticks))


@dataclass(frozen=True)
class EngineUnit:
    seed: int
    env: int  # index into EngineBitStudy.populations
    background: int
    focal: int
    outcome: int


@dataclass(frozen=True)
class EngineValidationReport:
    expression: str
    adjustment: tuple[str, ...]
    identified: dict[int, float]
    truth: dict[int, float]
    naive: dict[int, float]
    n_units: int
    bootstrap_ci: tuple[float, float]

    @property
    def identified_ate(self) -> float:
        return self.identified[1] - self.identified[0]

    @property
    def true_ate(self) -> float:
        return self.truth[1] - self.truth[0]

    @property
    def naive_ate(self) -> float:
        return self.naive[1] - self.naive[0]

    def to_dict(self) -> dict[str, object]:
        return {
            "expression": self.expression,
            "adjustment": list(self.adjustment),
            "identified": self.identified,
            "truth": self.truth,
            "naive": self.naive,
            "identified_ate": self.identified_ate,
            "true_ate": self.true_ate,
            "naive_ate": self.naive_ate,
            "bootstrap_ci_identified_ate": list(self.bootstrap_ci),
            "n_units": self.n_units,
        }


Runner = Callable[[int, int, Mapping[int, int], int], int]


@dataclass(frozen=True)
class EngineBitStudy:
    focal_bit: int = 1
    background_bit: int = 2
    populations: tuple[int, int] = (4, 8)
    ticks: int = 12
    seeds: tuple[int, ...] = (0, 1, 2)
    # P(focal = 1 | env, background): confounded assignment
    assignment: Mapping[tuple[int, int], float] = field(
        default_factory=lambda: {(0, 0): 0.2, (0, 1): 0.3, (1, 0): 0.6, (1, 1): 0.85}
    )
    runner: Runner = life_loop_births

    # names
    @property
    def env_var(self) -> str:
        return "env:population"

    @property
    def focal_var(self) -> str:
        return f"bit:{self.focal_bit}"

    @property
    def background_var(self) -> str:
        return f"bit:{self.background_bit}"

    outcome_var = "event:births"

    def diagram(self, *, env_observed: bool = True) -> CausalDiagram:
        """The assumed diagram. With the environment hidden it becomes a bidirected edge."""
        e, f, b, y = self.env_var, self.focal_var, self.background_var, self.outcome_var
        directed = [(b, f), (b, y), (f, y)]
        if env_observed:
            return CausalDiagram.build(directed + [(e, f), (e, y)])
        return CausalDiagram.build(directed, [(f, y)])

    def run(self, seed: int, env: int, background: int, focal: int) -> int:
        bits = {self.focal_bit: focal, self.background_bit: background}
        return self.runner(seed, self.populations[env], bits, self.ticks)

    def observational_sample(self, n_units: int, seed: int) -> tuple[EngineUnit, ...]:
        rng = RNGManager(seed=seed, namespace="causal_inference/engine_study")
        units = []
        for _ in range(n_units):
            s = rng.choice(self.seeds)
            env = rng.randrange(2)
            bg = rng.randrange(2)
            focal = 1 if rng.random() < self.assignment[(env, bg)] else 0
            units.append(EngineUnit(s, env, bg, focal, self.run(s, env, bg, focal)))
        return tuple(units)

    def empirical_joint(self, units: Sequence[EngineUnit]) -> DiscreteJoint:
        counts: dict[tuple[int, int, int, int], int] = {}
        for u in units:
            key = (u.env, u.background, u.focal, u.outcome)
            counts[key] = counts.get(key, 0) + 1
        n = len(units)
        ys = tuple(sorted({u.outcome for u in units}))
        names = (self.env_var, self.background_var, self.focal_var, self.outcome_var)
        domains = {names[0]: (0, 1), names[1]: (0, 1), names[2]: (0, 1), names[3]: ys}
        return DiscreteJoint(names, domains, {k: c / n for k, c in counts.items()})

    def identified_mean(self, expr: Expression, joint: DiscreteJoint, focal: int) -> float:
        total = 0.0
        for y in joint.domains[self.outcome_var]:
            a = {self.focal_var: focal, self.outcome_var: y}
            total += float(y) * joint.evaluate(expr, a, fill_unbound=True)
        return total

    def ground_truth(self, units: Sequence[EngineUnit]) -> dict[int, float]:
        """Mean outcome of the same units rerun under do(focal = 0) and do(focal = 1)."""
        return {
            b: sum(self.run(u.seed, u.env, u.background, b) for u in units) / len(units)
            for b in (0, 1)
        }

    def validate(
        self, n_units: int = 200, seed: int = 0, n_bootstrap: int = 200
    ) -> EngineValidationReport:
        g = self.diagram(env_observed=True)
        expr = identify(g, {self.outcome_var}, {self.focal_var})
        units = self.observational_sample(n_units, seed)
        joint = self.empirical_joint(units)
        ident = {b: self.identified_mean(expr, joint, b) for b in (0, 1)}
        naive = {}
        for b in (0, 1):
            sel = [u.outcome for u in units if u.focal == b]
            if not sel:
                raise ConfigurationError("no unit received focal value {b}; enlarge the sample")
            naive[b] = sum(sel) / len(sel)
        rng = RNGManager(seed=seed, namespace="causal_inference/engine_study/bootstrap")
        ates = []
        for _ in range(n_bootstrap):
            boot = [units[rng.randrange(len(units))] for _ in units]
            try:
                j = self.empirical_joint(boot)
                ates.append(self.identified_mean(expr, j, 1) - self.identified_mean(expr, j, 0))
            except ConfigurationError:
                continue
        ates.sort()
        lo = ates[int(0.025 * (len(ates) - 1))]
        hi = ates[int(0.975 * (len(ates) - 1))]
        from .adjustment import backdoor_adjustment_sets

        adj = backdoor_adjustment_sets(g, {self.focal_var}, {self.outcome_var})
        return EngineValidationReport(
            expression=str(expr),
            adjustment=tuple(sorted(adj[0])) if adj else (),
            identified=ident,
            truth=self.ground_truth(units),
            naive=naive,
            n_units=n_units,
            bootstrap_ci=(lo, hi),
        )

    def hidden_environment_is_not_identifiable(self) -> bool:
        try:
            identify(self.diagram(env_observed=False), {self.outcome_var}, {self.focal_var})
        except NotIdentifiable:
            return True
        return False


# Relations of genesis.causal_graph that state a direction of influence. The
# others (``precedes`` is temporal order, ``co_occurs`` is association) are
# not causal assumptions and are not turned into arrows.
DIRECTED_EVIDENCE_RELATIONS = frozenset(
    {
        "predicts_local",
        "consumes_runtime_atp",
        "consumes_learning_atp",
        "leads_to_block",
        "leads_to_resource_gain",
        "leads_to_memory_write",
        "leads_to_reproduction_attempt",
        "leads_to_reproduction_success",
        "has_outcome_detail",
    }
)


def diagram_from_evidence_graph(
    graph: object,
    *,
    relations: frozenset[str] = DIRECTED_EVIDENCE_RELATIONS,
    min_evidence: int = 1,
    confounded: Sequence[tuple[str, str]] = (),
) -> CausalDiagram:
    """Turn the engine's event evidence graph into a *hypothesised* causal diagram.

    Nodes become ``event:<node_id>``. Edges with a directed relation and at
    least ``min_evidence`` observations become arrows. ``confounded`` adds
    bidirected edges (by node id) for suspected hidden common causes. The
    evidence graph is a co-occurrence scaffold, so the result is an
    assumption to be tested with interventions, not a discovered structure;
    a directed cycle raises ``ConfigurationError``.
    """
    from codontrace.genesis.causal_graph import CausalGraph

    if not isinstance(graph, CausalGraph):
        raise ConfigurationError("graph must be a genesis CausalGraph")
    directed = [
        (f"event:{e.source}", f"event:{e.target}")
        for e in graph.edges
        if e.relation in relations and e.evidence_count >= min_evidence and e.source != e.target
    ]
    return CausalDiagram.build(
        directed,
        [(f"event:{a}", f"event:{b}") for a, b in confounded],
        nodes=[f"event:{n.node_id}" for n in graph.nodes],
    )
