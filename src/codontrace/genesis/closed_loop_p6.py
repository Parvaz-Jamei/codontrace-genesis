"""Closed-loop P6: matching-allele contact on the existing ATP clock.

The open problem is not "does a Red Queen story sound true". Otto and Nuismer
(Science 2004, doi:10.1126/science.1094072) showed that species interactions
usually select against sex. Morran et al. (Science 2011,
doi:10.1126/science.1206360) found the opposite sign in one host-pathogen
passage. Agrawal (PLoS Biol 2006, doi:10.1371/journal.pbio.0040265) showed the
sign can flip when offspring meet the same antagonist their parent did.

This module asks that question on GenesisOrganism, not on the type-II Euler
stepper in ``host_parasite_type2_rq.py``. Exact window equality is the
individual limit of that stepper's diagonal specificity (match α = 1, else 0).
A hit debits the host's own ``atp_state``. There is no second energy bag and
no separate world clock.

Passage modes
- ``coevolve``: after the hit, the antagonist window becomes the modal living
  host window (passage on survivors).
- ``frozen``: the antagonist window stays at the ancestral modal host window.
- ``absent``: no debit.

Outcross births use ``apply_positional_segment_exchange`` on the first codon
of the recognition window, then the existing mating-effort fee. Selfing copies
the tape and pays no fee. A hit debits Holling type II,
``virulence * H / (1 + H)``, from that host's own account. A density-free flat
α is not used.

``pattern_holds`` is the storm rule in
``docs/handoff/CLOSED_LOOP_P6_STORM_20260925.md``. It is not copied into
``red_queen_proved``. A name-set that returns with no match debit inside the
repeat is not that rule's cycle. ``biological_red_queen_proved`` stays false.
The host_parasite claim profile still blocks the biological claim.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass

from codontrace.errors import ConfigurationError
from codontrace.genesis.birth import apply_positional_segment_exchange
from codontrace.genesis.host_parasite_life_plugin import (
    MATCH_BIT_START,
    MATCH_BIT_WIDTH,
    OUTCROSS_OUT_BITS,
    OUTCROSS_SELFING_BITS,
    ROLE_PRIMARY,
    ROLE_SECONDARY,
    ClosedLoopHPLifeConfig,
    assert_single_atp_owner,
    decode_recognition,
    outcross_runtime_cost,
    silence_outcross_locus,
)
from codontrace.genesis.organism import GenesisOrganism
from codontrace.genesis.population import (
    MetabolicConfig,
    MutationConfig,
    PopulationConfigs,
    PopulationState,
    ReproductionConfig,
)
from codontrace.genesis.population_runner import PopulationRunner
from codontrace.genesis.runtime_profiles import LIFE_LOOP_EATER_GENOME
from codontrace.genome import SemanticGenome
from codontrace.world import World2D

P6_PREDICATE = (
    "coevolve gap, absent under freeze and under a zero debit, "
    "frequencies cycle only while types update, and the gap needs a high debit"
)
_VIRULENCE_GRID = (0.0, 1.0, 4.0, 8.0, 16.0, 32.0, 64.0)
_FEE_CONFIG = ClosedLoopHPLifeConfig(
    enabled=True,
    outcross_enabled=True,
    outcross_runtime_atp=1.0,
)
P6_OPEN_PROBLEM = (
    "otto_nuismer_2004_sign_of_selection_on_sex_under_matching_allele_contact"
)
MATCH_LEDGER_REASON = "p6_match_cost"
_KAPPA_QUIET = "100000"
_BIRTH_ATP = 10.0
_PROGRAM = f"{LIFE_LOOP_EATER_GENOME}{_KAPPA_QUIET}"
# Three copies of the common haplotype, one of the complement.
# Exchange of the first recognition codon makes two windows the ancestor misses.
_FOUNDER_WINDOWS = ("000111", "000111", "000111", "111000")


def strict_match_alpha(host_window: str, antagonist_window: str) -> float:
    """Exact-window α. 1 on equality, else 0. Not an Euler step."""

    if not host_window or not antagonist_window:
        return 0.0
    if len(host_window) != len(antagonist_window):
        return 0.0
    return 1.0 if host_window == antagonist_window else 0.0


def holling_type2_cost(virulence: float, type_count: int) -> float:
    """Saturating per-host debit. A flat α, independent of density, is refused."""

    if virulence < 0.0:
        raise ConfigurationError("virulence must be >= 0")
    if type_count <= 0 or virulence == 0.0:
        return 0.0
    count = float(type_count)
    return float(virulence) * (count / (1.0 + count))


def frequency_cycles(history: tuple[tuple[str, ...], ...] | list[tuple[str, ...]]) -> bool:
    """True when a type-set returns after a different set. A fixed point is not a cycle."""

    seen: dict[tuple[str, ...], int] = {}
    for index, state in enumerate(history):
        previous = seen.get(state)
        if previous is not None and any(history[cursor] != state for cursor in range(previous + 1, index)):
            return True
        seen.setdefault(state, index)
    return False


def debit_backed_cycle(
    history: tuple[tuple[str, ...], ...] | list[tuple[str, ...]],
    match_debits: tuple[int, ...] | list[int],
) -> bool:
    """Name-set return counts only when a match debit lands inside the repeat.

    The square of a forced exchange alternates two names and pays nothing on
    the return. That orbit is not the cycle clause.
    """

    if len(match_debits) != len(history):
        raise ConfigurationError("match debits must align with the type history")
    seen: dict[tuple[str, ...], int] = {}
    for index, state in enumerate(history):
        previous = seen.get(state)
        interior = range(previous + 1, index + 1) if previous is not None else ()
        names_changed = previous is not None and any(history[cursor] != state for cursor in range(previous + 1, index))
        paid = any(match_debits[cursor] > 0 for cursor in interior)
        if names_changed and paid:
            return True
        seen.setdefault(state, index)
    return False


def _match_debit_count(organisms: list[GenesisOrganism], tick: int) -> int:
    total = 0
    for organism in organisms:
        ledger = organism.atp_state.runtime.to_dict().get("ledger", [])
        total += sum(
            1
            for entry in ledger
            if isinstance(entry, dict)
            and entry.get("reason") == MATCH_LEDGER_REASON
            and entry.get("tick") == tick
        )
    return total


def digital_red_queen_pattern(
    *,
    coevo_outcross_extinct: bool,
    coevo_selfing_extinct: bool,
    frozen_outcross_extinct: bool,
    frozen_selfing_extinct: bool,
    zero_outcross_extinct: bool,
    zero_selfing_extinct: bool,
    coevo_cycles: bool,
    frozen_cycles: bool,
    low_debit_gap: bool,
    debit_threshold: float | None,
) -> bool:
    """Storm rule. The extinct/persist gap alone is not enough."""

    gap_coevo = (not coevo_outcross_extinct) and coevo_selfing_extinct
    gap_frozen = (not frozen_outcross_extinct) and frozen_selfing_extinct
    gap_zero = (not zero_outcross_extinct) and zero_selfing_extinct
    return bool(
        gap_coevo
        and not gap_frozen
        and not gap_zero
        and coevo_cycles
        and not frozen_cycles
        and not low_debit_gap
        and debit_threshold is not None
        and debit_threshold > 0.0
    )


def _tape(mating_bits: str, window: str) -> str:
    if len(window) != MATCH_BIT_WIDTH:
        raise ConfigurationError("recognition window must be 6 bits")
    if mating_bits not in {OUTCROSS_SELFING_BITS, OUTCROSS_OUT_BITS}:
        raise ConfigurationError("mating locus must be selfing 000 or outcross 001")
    return f"{_PROGRAM}{mating_bits}{window}"


def _window(organism: GenesisOrganism) -> str:
    return decode_recognition(organism.genome.to_compact())


def _set_window(organism: GenesisOrganism, window: str) -> None:
    bits = organism.genome.to_compact()
    if len(bits) < MATCH_BIT_START + MATCH_BIT_WIDTH:
        raise ConfigurationError("tape is shorter than the recognition window")
    rewritten = bits[:MATCH_BIT_START] + window + bits[MATCH_BIT_START + MATCH_BIT_WIDTH :]
    organism.genome = SemanticGenome.from_compact(rewritten)


def _modal(organisms: list[GenesisOrganism]) -> str:
    counts = Counter(_window(org) for org in organisms)
    if not counts:
        raise ConfigurationError("modal window requires a living host")
    best = max(counts.values())
    winners = sorted(window for window, count in counts.items() if count == best)
    return winners[0]


def _spawn(organism_id: str, bits: str, atp: float) -> GenesisOrganism:
    return GenesisOrganism.from_bits(
        organism_id,
        bits,
        initial_runtime_atp=atp,
        position=(0, 0),
    )


def _charge_mating_fee(organism: GenesisOrganism, *, tick: int) -> None:
    """Existing mating-effort fee. Selfing tapes pay nothing."""

    cost = outcross_runtime_cost(organism.genome.to_compact(), _FEE_CONFIG)
    if cost <= 0.0:
        return
    payable = min(cost, organism.atp_state.runtime_available)
    if payable <= 0.0:
        return
    organism.atp_state.debit_runtime(
        payable,
        tick=tick,
        organism_id=organism.id,
        codon=organism.genome.to_compact()[15:18] or "000",
        action="mate_fee",
        reason="outcross_runtime_cost",
    )


def _infect(
    hosts: list[GenesisOrganism],
    antagonist_window: str,
    *,
    tick: int,
    virulence: float,
) -> list[GenesisOrganism]:
    counts = Counter(_window(host) for host in hosts)
    living: list[GenesisOrganism] = []
    for host in hosts:
        window = _window(host)
        if strict_match_alpha(window, antagonist_window) != 1.0:
            living.append(host)
            continue
        cost = holling_type2_cost(virulence, counts[window])
        if cost <= 0.0:
            living.append(host)
            continue
        payable = min(cost, host.atp_state.runtime_available)
        if payable > 0.0:
            host.atp_state.debit_runtime(
                payable,
                tick=tick,
                organism_id=host.id,
                codon=window[:3] or "000",
                action="match_hit",
                reason=MATCH_LEDGER_REASON,
            )
        if host.atp_state.runtime_available > 0.0:
            living.append(host)
    return living


def _selfing_children(
    parents: list[GenesisOrganism], *, generation: int, atp: float
) -> list[GenesisOrganism]:
    children: list[GenesisOrganism] = []
    for index, parent in enumerate(sorted(parents, key=lambda org: org.id)):
        children.append(
            _spawn(f"s{generation}-{index}", parent.genome.to_compact(), atp)
        )
    return children


def _outcross_children(
    parents: list[GenesisOrganism], *, generation: int, atp: float
) -> list[GenesisOrganism]:
    pool = sorted(parents, key=lambda org: (_window(org), org.id))
    pairs: list[tuple[GenesisOrganism, GenesisOrganism]] = []
    while len(pool) >= 2:
        left = pool.pop(0)
        different = next(
            (i for i, other in enumerate(pool) if _window(other) != _window(left)),
            None,
        )
        if different is None:
            right = pool.pop(0)
        else:
            right = pool.pop(different)
        pairs.append((left, right))
    if pool:
        pairs.append((pool[0], pool[0]))
    children: list[GenesisOrganism] = []
    serial = 0
    for left, right in pairs:
        first, second = apply_positional_segment_exchange(
            left.genome.to_compact(),
            right.genome.to_compact(),
            MATCH_BIT_START,
            MATCH_BIT_START + 3,
        )
        children.append(_spawn(f"x{generation}-{serial}", first, atp))
        serial += 1
        children.append(_spawn(f"x{generation}-{serial}", second, atp))
        serial += 1
    return children


@dataclass(frozen=True, slots=True)
class MatchArmRecord:
    """One mating system under one antagonist passage. No digest field."""

    mating: str
    passage: str
    generations: int
    virulence: float
    final_hosts: int
    extinct: bool
    cycles: bool
    mating_fee_debits: int
    match_debits_by_generation: tuple[int, ...]
    parasite_window: str
    final_windows: tuple[str, ...]
    window_history: tuple[tuple[str, ...], ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "mating": self.mating,
            "passage": self.passage,
            "generations": self.generations,
            "virulence": self.virulence,
            "final_hosts": self.final_hosts,
            "extinct": self.extinct,
            "cycles": self.cycles,
            "mating_fee_debits": self.mating_fee_debits,
            "match_debits_by_generation": list(self.match_debits_by_generation),
            "parasite_window": self.parasite_window,
            "final_windows": list(self.final_windows),
            "window_history": [list(state) for state in self.window_history],
        }


@dataclass(frozen=True, slots=True)
class MatchingAlleleFactorial:
    """Digital answer. The extinct/persist gap alone does not set the flag."""

    arms: tuple[MatchArmRecord, ...]
    pattern_holds: bool
    red_queen_proved: bool
    biological_red_queen_proved: bool
    claim_ceiling: str
    predicate: str
    open_problem: str
    debit_threshold: float | None
    coevo_cycles: bool
    frozen_cycles: bool
    low_debit_gap: bool
    zero_debit_gap: bool

    def to_dict(self) -> dict[str, object]:
        return {
            "arms": [arm.to_dict() for arm in self.arms],
            "pattern_holds": self.pattern_holds,
            "red_queen_proved": self.red_queen_proved,
            "biological_red_queen_proved": self.biological_red_queen_proved,
            "claim_ceiling": self.claim_ceiling,
            "predicate": self.predicate,
            "open_problem": self.open_problem,
            "debit_threshold": self.debit_threshold,
            "coevo_cycles": self.coevo_cycles,
            "frozen_cycles": self.frozen_cycles,
            "low_debit_gap": self.low_debit_gap,
            "zero_debit_gap": self.zero_debit_gap,
            "euler_stepper_used": False,
            "holling": "type_ii",
            "atp_owner": "GenesisOrganism.atp_state",
        }


def _type_state(hosts: list[GenesisOrganism]) -> tuple[str, ...]:
    return tuple(sorted({_window(host) for host in hosts}))


def _survival_gap(arms: tuple[MatchArmRecord, ...] | list[MatchArmRecord], passage: str) -> bool:
    by_key = {(arm.mating, arm.passage): arm for arm in arms}
    return (not by_key[("outcross", passage)].extinct) and by_key[("selfing", passage)].extinct


def run_match_arm(
    *,
    mating: str,
    passage: str,
    generations: int = 4,
    birth_atp: float = _BIRTH_ATP,
    virulence: float = 0.0,
) -> MatchArmRecord:
    """Semelparous generations. Each debit's tick is the generation index."""

    if mating not in {"outcross", "selfing"}:
        raise ConfigurationError("mating must be outcross or selfing")
    if passage not in {"coevolve", "frozen", "absent"}:
        raise ConfigurationError("passage must be coevolve, frozen, or absent")
    if generations < 1:
        raise ConfigurationError("generations must be >= 1")
    if virulence < 0.0:
        raise ConfigurationError("virulence must be >= 0")
    mating_bits = OUTCROSS_OUT_BITS if mating == "outcross" else OUTCROSS_SELFING_BITS
    hosts = [
        _spawn(f"f{index}", _tape(mating_bits, window), birth_atp)
        for index, window in enumerate(_FOUNDER_WINDOWS)
    ]
    antagonist = _spawn("antagonist", _tape(OUTCROSS_SELFING_BITS, _modal(hosts)), birth_atp)
    ancestral = _window(antagonist)
    history: list[tuple[str, ...]] = []
    match_debits: list[int] = []
    fee_debits = 0
    for generation in range(generations):
        assert_single_atp_owner([*hosts, antagonist])
        if not hosts:
            history.append(())
            match_debits.append(0)
            continue
        if mating == "outcross":
            children = _outcross_children(hosts, generation=generation, atp=birth_atp)
        else:
            children = _selfing_children(hosts, generation=generation, atp=birth_atp)
        for child in children:
            before = child.atp_state.runtime_available
            _charge_mating_fee(child, tick=generation)
            if child.atp_state.runtime_available < before:
                fee_debits += 1
        if passage == "absent" or virulence == 0.0:
            hosts = [child for child in children if child.atp_state.runtime_available > 0.0]
            history.append(_type_state(hosts))
            match_debits.append(0)
            continue
        hosts = _infect(children, _window(antagonist), tick=generation, virulence=virulence)
        history.append(_type_state(hosts))
        match_debits.append(_match_debit_count(children, generation))
        if passage == "coevolve" and hosts:
            _set_window(antagonist, _modal(hosts))
        elif passage == "frozen":
            _set_window(antagonist, ancestral)
    return MatchArmRecord(
        mating=mating,
        passage=passage,
        generations=generations,
        virulence=virulence,
        final_hosts=len(hosts),
        extinct=len(hosts) == 0,
        cycles=debit_backed_cycle(history, match_debits),
        mating_fee_debits=fee_debits,
        match_debits_by_generation=tuple(match_debits),
        parasite_window=_window(antagonist),
        final_windows=tuple(sorted(_window(host) for host in hosts)),
        window_history=tuple(history),
    )


def _arms_at(virulence: float, *, generations: int) -> tuple[MatchArmRecord, ...]:
    return tuple(
        run_match_arm(
            mating=mating,
            passage=passage,
            generations=generations,
            virulence=virulence,
        )
        for passage in ("coevolve", "frozen", "absent")
        for mating in ("outcross", "selfing")
    )


def run_matching_allele_factorial(*, generations: int = 4) -> MatchingAlleleFactorial:
    """Score the storm rule across a declared virulence grid. Do not fit one cell."""

    rows = [(virulence, _arms_at(virulence, generations=generations)) for virulence in _VIRULENCE_GRID]
    zero_arms = rows[0][1]
    zero_gap = _survival_gap(zero_arms, "absent")

    def _full(arms: tuple[MatchArmRecord, ...]) -> bool:
        by_key = {(arm.mating, arm.passage): arm for arm in arms}
        return digital_red_queen_pattern(
            coevo_outcross_extinct=by_key[("outcross", "coevolve")].extinct,
            coevo_selfing_extinct=by_key[("selfing", "coevolve")].extinct,
            frozen_outcross_extinct=by_key[("outcross", "frozen")].extinct,
            frozen_selfing_extinct=by_key[("selfing", "frozen")].extinct,
            zero_outcross_extinct=by_key[("outcross", "absent")].extinct,
            zero_selfing_extinct=by_key[("selfing", "absent")].extinct,
            coevo_cycles=by_key[("outcross", "coevolve")].cycles,
            frozen_cycles=by_key[("outcross", "frozen")].cycles,
            low_debit_gap=False,
            debit_threshold=1.0,
        )

    threshold: float | None = None
    chosen = rows[-1][1]
    for virulence, arms in rows:
        if virulence <= 0.0:
            continue
        if _survival_gap(arms, "coevolve") and _full(arms):
            threshold = virulence
            chosen = arms
            break
    low_gap = False
    if threshold is None:
        low_gap = any(
            virulence > 0.0 and _survival_gap(arms, "coevolve") for virulence, arms in rows
        )
        # No virulence cleared the full rule. Keep the strongest coevo gap, if any.
        for _virulence, arms in rows:
            if _survival_gap(arms, "coevolve"):
                chosen = arms
    else:
        low_gap = any(
            0.0 < virulence < threshold and _survival_gap(arms, "coevolve")
            for virulence, arms in rows
        )
    by_key = {(arm.mating, arm.passage): arm for arm in chosen}
    pattern = digital_red_queen_pattern(
        coevo_outcross_extinct=by_key[("outcross", "coevolve")].extinct,
        coevo_selfing_extinct=by_key[("selfing", "coevolve")].extinct,
        frozen_outcross_extinct=by_key[("outcross", "frozen")].extinct,
        frozen_selfing_extinct=by_key[("selfing", "frozen")].extinct,
        zero_outcross_extinct=by_key[("outcross", "absent")].extinct,
        zero_selfing_extinct=by_key[("selfing", "absent")].extinct,
        coevo_cycles=by_key[("outcross", "coevolve")].cycles,
        frozen_cycles=by_key[("outcross", "frozen")].cycles,
        low_debit_gap=low_gap,
        debit_threshold=threshold,
    )
    # A threshold that still has a cheaper gap is not "only above".
    if low_gap:
        pattern = False
    return MatchingAlleleFactorial(
        arms=chosen,
        pattern_holds=pattern,
        red_queen_proved=False,
        biological_red_queen_proved=False,
        claim_ceiling="runtime_observation",
        predicate=P6_PREDICATE,
        open_problem=P6_OPEN_PROBLEM,
        debit_threshold=threshold,
        coevo_cycles=by_key[("outcross", "coevolve")].cycles,
        frozen_cycles=by_key[("outcross", "frozen")].cycles,
        low_debit_gap=low_gap,
        zero_debit_gap=zero_gap,
    )


class ClosedLoopP6Clock:
    """One PopulationRunner generation, then the same match debit on its organisms.

    Reproduction stays off so the eater program cannot confound the hit test.
    The runner is the clock. The debit lands on ``atp_state``.
    """

    def __init__(self, runner: PopulationRunner, roles: dict[str, str], passage: str) -> None:
        self.runner = runner
        self.roles = roles
        self.passage = passage
        self.tick_index = 0

    @classmethod
    def boot(cls, *, passage: str = "coevolve", initial_atp: float = 100.0) -> ClosedLoopP6Clock:
        if passage not in {"coevolve", "frozen"}:
            raise ConfigurationError("clock passage must be coevolve or frozen")
        specs = (
            ("h0", ROLE_PRIMARY, "000111"),
            ("h1", ROLE_PRIMARY, "111000"),
            ("h2", ROLE_PRIMARY, "111000"),
            ("p0", ROLE_SECONDARY, "000111"),
        )
        organisms: list[GenesisOrganism] = []
        roles: dict[str, str] = {}
        for index, (oid, role, window) in enumerate(specs):
            mating = OUTCROSS_SELFING_BITS if role == ROLE_SECONDARY else OUTCROSS_OUT_BITS
            organisms.append(
                GenesisOrganism.from_bits(
                    oid,
                    _tape(mating, window),
                    initial_runtime_atp=initial_atp,
                    position=(index % 4, 0 if role == ROLE_PRIMARY else 1),
                )
            )
            roles[oid] = role
        life = ClosedLoopHPLifeConfig(
            enabled=True,
            role_by_id=tuple(sorted(roles.items())),
            kappa_enabled=False,
            outcross_enabled=True,
            match_locus_enabled=True,
            mutation_stream_lock_roles=(ROLE_SECONDARY,) if passage == "frozen" else (),
        )
        for org in organisms:
            silence_outcross_locus(org, life)
        configs = PopulationConfigs(
            reproduction=ReproductionConfig(enabled=False),
            mutation=MutationConfig(bit_flip_rate=0.0),
            metabolism=MetabolicConfig(enabled=False),
            ticks_per_generation=1,
            closed_loop_hp_life=life,
        )
        runner = PopulationRunner(
            population=PopulationState(
                generation=0,
                tick=0,
                organisms=tuple(organisms),
                lineage=(),
                fitness=(),
            ),
            world=World2D(width=4, height=4),
            configs=configs,
        )
        assert_single_atp_owner(organisms)
        return cls(runner, roles, passage)

    def _split(self) -> tuple[list[GenesisOrganism], GenesisOrganism]:
        hosts = [
            org
            for org in self.runner.population.organisms
            if self.roles.get(org.id) == ROLE_PRIMARY
        ]
        antagonists = [
            org
            for org in self.runner.population.organisms
            if self.roles.get(org.id) == ROLE_SECONDARY
        ]
        if len(antagonists) != 1:
            raise ConfigurationError("P6 clock expects one antagonist organism")
        return hosts, antagonists[0]

    def run_ticks(self, ticks: int, *, match_cost: float = 1.0) -> dict[str, object]:
        if ticks < 0:
            raise ConfigurationError("ticks must be non-negative")
        for _ in range(ticks):
            self.runner.step_generation(seed=self.tick_index + 1)
            hosts, antagonist = self._split()
            ancestral = _window(antagonist)
            _infect(hosts, ancestral, tick=self.tick_index, virulence=match_cost)
            if self.passage == "coevolve":
                living = [host for host in hosts if host.atp_state.runtime_available > 0.0]
                if living:
                    _set_window(antagonist, _modal(living))
            self.tick_index += 1
            assert_single_atp_owner(self.runner.population.organisms)
        hosts, antagonist = self._split()
        return {
            "generation": self.runner.population.generation,
            "tick_index": self.tick_index,
            "antagonist_window": _window(antagonist),
            "host_windows": {host.id: _window(host) for host in hosts},
            "matched_ids": [
                host.id
                for host in hosts
                if any(
                    entry.get("reason") == MATCH_LEDGER_REASON
                    for entry in host.atp_state.runtime.to_dict().get("ledger", [])
                    if isinstance(entry, dict)
                )
            ],
            "red_queen_proved": False,
            "biological_red_queen_proved": False,
            "clock_api": "PopulationRunner.step_generation",
        }
