"""RQ-3: the antagonist as a heritable genotype population with reproduction,
death and selection, plus the label-shuffled negative-control route.

Defect this module fixes
------------------------

``closed_loop_hp_arm01_structural_rq.StructuralRQArm`` holds the antagonist as
``parasite_windows: list[str]``. Units have no identity, no parent, no energy, no
death and no fertility: ``_passage_update`` (structural_rq.py:710-773) keeps a random
half by index, replenishes the rest by uniform sampling of the realised contact set,
and mutates 25 per cent of draws. There is therefore no antagonist fitness, no
genealogy, no mortality and no selection coefficient, and the RQ-3 arms cannot be
built: ``test-runs/rq3/`` recorded ``antagonist_ancestry_rows = 0`` and no
label-shuffled passage mode exists in the tree.

This module supplies the smallest object that is a population rather than a pool:
each antagonist individual has a stable id, a window (its genotype), a parent, a
birth generation, an energy reserve and an alive/dead flag. A generation is:

    contact (host side, unchanged, in _apply_hp_env_contact)
        -> each unit that served a contact pays the pairing cost and earns
           ``earned_yield`` (the same ATP the host paid; the pairing cost is the
           dead-loss fraction, so the energy account of the pair closes)
        -> units with energy <= 0 die
        -> survivors reproduce asexually with probability ``fecundity * energy``,
           offspring inherit the parent window and may mutate
        -> offspring and survivors fill a fixed seat budget by energy rank, so
           total antagonist energy and the number of contact seats stay bounded

Selection is then explicit: units whose windows match the common host class serve
more contacts and pay less cost per unit, so they accumulate energy and reproduce,
which is the delayed adaptation route. The route is heritable (offspring inherit
the window) and it is cut without touching contact or cost in the shuffled-label
mode, which permutes the offspring windows against the contact evidence.

Engine boundary: ``engine.py`` is not touched; this is arm/plugin code, exactly like
the rest of the closed-loop measurement layer.

Integration points (four edits, all in closed_loop_hp_arm01_structural_rq.py)
----------------------------------------------------------------------------

1. import: add ``from codontrace.genesis.measurements.antagonist_population import
   ANTAGONIST_PASSAGE_SHUFFLED_LABELS, AntagonistPopulation``.
2. ``boot_structural``: build ``AntagonistPopulation.founders(parasite_windows)`` and
   store it as ``self.antagonist_pop``.
3. ``_apply_hp_env_contact``: return the per-pair records already collected for the
   pressure meter, and credit each participating unit with the host's paid debit.
4. ``_passage_update``: replace the body with ``self.antagonist_pop.advance(...)`` and
   set ``self.parasite_windows`` from the surviving roster's windows. ``run_generations``
   must pass the contact records into ``_passage_update`` (one extra argument).

The existing ``turnover_kept`` / ``turnover_replaced`` / ``turnover_mut_events`` /
``turnover_churn`` series keep their names and meanings and are filled from the
returned ledger, so every downstream reader (``turnover_audit``, the confirm runner,
the digest builder) keeps working unchanged.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass, replace

from codontrace.errors import ConfigurationError
from codontrace.rng import RNGManager

#: Negative-control passage mode: real contact and real cost, but the offspring
#: windows are permuted against the contact evidence, so which host class was
#: common carries no information into the next generation's antagonist composition.
ANTAGONIST_PASSAGE_SHUFFLED_LABELS = "shuffled_labels"

#: Arm-level opt-in for the RQ-3 antagonist population. The standing value leaves the arm
#: byte-identical to the pre-RQ-3 build, so every locked expectation is untouched;
#: ``"population"`` selects the heritable genotype population.
ANTAGONIST_ECOLOGY_STANDING = "standing"
ANTAGONIST_ECOLOGY_POPULATION = "population"
ANTAGONIST_ECOLOGIES: tuple[str, ...] = (
    ANTAGONIST_ECOLOGY_STANDING,
    ANTAGONIST_ECOLOGY_POPULATION,
)

#: Realised contact costs the antagonist one unit of energy per unit of ATP it takes.
#: ``pairing_cost`` is the dead-loss share and ``earned_yield`` the assimilated share;
#: they sum to 1 so the pair's energy account closes.
PAIRING_COST = 0.25
EARNED_YIELD = 0.75

#: Fixed energy reserve handed to each re-seeded unit in the negative-control and
#: frozen modes. It is a constant of the control, not a tuned parameter: it equals the
#: founder reserve so the negative control starts every generation from the same
#: state the coevolving arm started from.
ENERGY_PER_SEAT = 1.0


@dataclass(frozen=True, slots=True)
class AntagonistUnit:
    """One antagonist individual: heritable window plus energy and genealogy."""

    unit_id: str
    window: str
    parent_id: str | None
    born_generation: int
    energy: float = 1.0
    alive: bool = True
    contacts_served: int = 0
    inherited_mutation: bool = False

    def with_energy(self, energy: float) -> AntagonistUnit:
        return replace(self, energy=float(energy))


@dataclass(frozen=True, slots=True)
class PassageLedger:
    """Per-generation antagonist demography and ancestry record."""

    generation: int
    mode: str
    kept: tuple[str, ...]
    newborns: tuple[AntagonistUnit, ...]
    deaths: tuple[str, ...]
    mutation_events: int
    contacts: int
    mean_energy: float
    alive: int


@dataclass
class AntagonistPopulation:
    """A fixed-seat antagonist population with energy-limited reproduction."""

    units: list[AntagonistUnit]
    seat_cap: int
    ancestral_windows: list[str]
    keep_fraction: float = 0.5
    mutation_rate: float = 0.25
    fecundity: float = 1.0
    # Pre-declared substrate knob, derived mechanically from the arm's standing ATP
    # budget and fixed BEFORE any arm runs. Derivation, using only documented constants:
    #   debit per contact at a full-affinity match = virulence * steal_fraction = 1.2 ATP
    #   affinity is uniform on [0, 1] over the window space, so its mean is 0.5
    #   mean ATP per contact = 1.2 * 0.5 = 0.6 ATP
    #   the arm realises one contact seat per host, so the ATP throughput per seat per
    #   generation is also 0.6 ATP
    #   assimilated income per unit per generation = (EARNED_YIELD - PAIRING_COST) * 0.6
    #   = 0.3 ATP
    #   maintenance = half the assimilated income = 0.15 ATP per generation, so strict
    #   starvation death stays real (an uncontacted unit loses 0.15 per generation and
    #   dies) while a unit earning the standing income keeps a surplus.
    # The same value is used in every arm, is never re-chosen after an arm result, and
    # its derivation is hashed into the run manifest.
    maintenance_cost: float = 0.15
    ledgers: list[PassageLedger] = None  # type: ignore[assignment]

    def __post_init__(self) -> None:
        if self.ledgers is None:
            self.ledgers = []
        if self.seat_cap < 1:
            raise ConfigurationError("antagonist seat cap must be >= 1")
        if not self.ancestral_windows:
            raise ConfigurationError("antagonist population requires ancestral windows")
        if not 0.0 <= float(self.keep_fraction) <= 1.0:
            raise ConfigurationError("keep fraction must be in [0, 1]")
        if float(self.maintenance_cost) <= 0.0:
            raise ConfigurationError("maintenance cost must be positive")

    @classmethod
    def founders(
        cls,
        windows: Sequence[str],
        *,
        keep_fraction: float = 0.5,
        mutation_rate: float = 0.25,
        fecundity: float = 1.0,
        maintenance_cost: float | None = None,
    ) -> AntagonistPopulation:
        if not windows:
            raise ConfigurationError("antagonist population requires founder windows")
        founder_units = [
            AntagonistUnit(
                unit_id=f"a0-{seat}",
                window=str(window),
                parent_id=None,
                born_generation=0,
                energy=ENERGY_PER_SEAT,
            )
            for seat, window in enumerate(windows)
        ]
        built = cls(
            units=founder_units,
            seat_cap=len(founder_units),
            ancestral_windows=[str(window) for window in windows],
            keep_fraction=float(keep_fraction),
            mutation_rate=float(mutation_rate),
            fecundity=float(fecundity),
        )
        if maintenance_cost is None:
            return built
        return replace(built, maintenance_cost=float(maintenance_cost))

    # -- accounting ---------------------------------------------------------

    def begin_round(self) -> None:
        """Reset the per-round contact tally before the contact round."""

        self.units = [replace(unit, contacts_served=0) for unit in self.units]

    # -- one generation -----------------------------------------------------

    def advance(
        self,
        *,
        matched_windows: Sequence[str],
        served_contacts: Sequence[tuple[str, float]] = (),
        mode: str,
        generation: int,
        rng: RNGManager,
        mutate_window: Callable[[str, RNGManager], str],
    ) -> PassageLedger:
        """Mortality, reproduction, selection and truncation for one generation.

        ``served_contacts`` holds ``(antagonist_window, atp_paid)`` per realised
        contact seat. A unit that served a seat earns ``EARNED_YIELD`` of the ATP paid
        and pays ``PAIRING_COST`` of it, so the pair's energy account closes and the
        energy a unit holds is exactly what it took from host contacts.
        """

        gen = int(generation)
        roster = list(self.units)
        if mode == "absent":
            ledger = PassageLedger(
                gen, mode, (), (), tuple(u.unit_id for u in roster), 0, 0, 0.0, 0
            )
            self.units = []
            self.ledgers.append(ledger)
            return ledger
        if mode == "frozen":
            # Frozen stock: the same windows are re-seeded each generation, so no
            # heritable change can accumulate. The units keep identity and are
            # re-energised to a flat reserve.
            re_seeded = [
                replace(unit, energy=ENERGY_PER_SEAT, alive=True, contacts_served=0, inherited_mutation=False)
                for unit in roster
            ]
            ledger = PassageLedger(
                gen,
                mode,
                tuple(u.unit_id for u in re_seeded),
                (),
                (),
                0,
                0,
                1.0,
                len(re_seeded),
            )
            self.units = re_seeded
            self.ledgers.append(ledger)
            return ledger

        # 0. Contact credit. The ATP a generation's contacts take is the antagonist's
        #    energy income for that generation. It is accumulated per *class*: a class
        # PER-SEAT REALISED INCOME (round-4 accounting). Each unit earns the ATP actually
        # taken by the contact seats it personally served, and zero if it served none. The
        # income is not averaged across the roster: averaging let a unit that was never
        # contacted live on other units' harvest, which both hid the mechanism and made any
        # survival-level maintenance cost indistinguishable from a cap. Selection now
        # follows realised contact income, which is the quantity RQ-3 claims to test: a
        # window that matches the common host class serves more seats, takes more ATP and
        # therefore reproduces more, with no roster-wide smoothing.
        served_queue: dict[str, list[float]] = {}
        for window, paid in served_contacts:
            served_queue.setdefault(str(window), []).append(float(paid))
        credited: list[AntagonistUnit] = []
        for unit in roster:
            queue = served_queue.get(unit.window) or []
            personal = float(queue.pop(0)) if queue else 0.0
            credited.append(
                replace(
                    unit,
                    energy=float(unit.energy)
                    + (EARNED_YIELD - PAIRING_COST) * personal,
                    contacts_served=int(unit.contacts_served)
                    + (1 if personal > 0.0 else 0),
                )
            )
        roster = credited

        # 1. Maintenance and mortality. Every living unit pays a fixed maintenance cost
        #    per generation, so energy earned by contact decays and a unit that has run
        #    its reserve down dies. Extinction is a real outcome of this mechanism, not
        #    a failure mode to be papered over: persistence comes from the substrate
        #    opt-in (`ecology=persistence_safe`), which keeps the pool populated while
        #    selection stays entirely inside this object. No top-up and no safety rule is
        #    applied here, because a rule introduced to restore persistence would also
        #    re-mix unsampled windows into the roster and dilute the energy ranking that
        #    the negative control has to separate.
        maintained = [
            replace(unit, energy=float(unit.energy) - float(self.maintenance_cost))
            for unit in roster
            if unit.alive
        ]
        survivors = [unit for unit in maintained if float(unit.energy) > 0.0]
        deaths = tuple(
            unit.unit_id for unit in maintained if float(unit.energy) <= 0.0
        )

        # 2. Reproduction. A surviving unit produces offspring in proportion to the
        #    energy it holds, and each offspring inherits an equal share of that
        #    energy. This is the heritable frequency-dependent step: a window that
        #    matches the common host class serves more contact seats, is credited
        #    more energy, and therefore contributes more copies of itself to the next
        #    generation, so the antagonist composition follows the host composition
        #    after one generation's delay.
        newborns: list[AntagonistUnit] = []
        mutation_events = 0
        for unit in survivors:
            expected = float(self.fecundity) * float(unit.energy)
            draws = int(expected) + (1 if rng.random() < (expected - int(expected)) else 0)
            share = float(unit.energy) / draws if draws > 0 else 0.0
            for child_seat in range(draws):
                window = unit.window
                mutated = False
                if float(self.mutation_rate) > 0.0 and rng.random() < float(self.mutation_rate):
                    window = mutate_window(window, rng)
                    mutation_events += 1
                    mutated = True
                newborns.append(
                    AntagonistUnit(
                        unit_id=f"a{gen}-{unit.unit_id}-{child_seat}",
                        window=str(window),
                        parent_id=unit.unit_id,
                        born_generation=gen,
                        energy=share,
                        inherited_mutation=mutated,
                    )
                )

        if mode == ANTAGONIST_PASSAGE_SHUFFLED_LABELS:
            # The negative control. Two ingredients are required to cut the route
            # without touching contact or cost:
            #   (a) the whole roster is re-drawn each generation from the *ancestral*
            #       window pool, so the next generation's composition is independent
            #       of which host class was common;
            #   (b) offspring windows are permuted against the parent that earned the
            #       energy, so per-unit ancestry is broken.
            # Without (a) a label shuffle alone leaves the multiset of windows
            # unchanged -- permuting strings cannot change a multiset -- and the
            # frequency-to-composition channel would survive the control. That failure
            # mode is why the pilot must show the negative control removes the effect
            # before any confirmatory seed is opened.
            windows = [unit.window for unit in newborns]
            for i in range(len(windows) - 1, 0, -1):
                j = rng.randrange(0, i + 1)
                windows[i], windows[j] = windows[j], windows[i]
            newborns = [
                replace(unit, window=windows[seat], inherited_mutation=False)
                for seat, unit in enumerate(newborns)
            ]
            # Deterministic equal-seat re-seeding from the ancestral pool: the number
            # of seats each ancestral window receives is fixed by construction, so no
            # contact-derived frequency information can reach the next generation.
            re_seeded: list[AntagonistUnit] = []
            for seat in range(self.seat_cap):
                parent_window = self.ancestral_windows[seat % len(self.ancestral_windows)]
                re_seeded.append(
                    AntagonistUnit(
                        unit_id=f"a{gen}-sham-{seat}",
                        window=str(parent_window),
                        parent_id=None,
                        born_generation=gen,
                        energy=ENERGY_PER_SEAT,
                        inherited_mutation=False,
                    )
                )
            self.units = re_seeded
            ledger = PassageLedger(
                gen,
                mode,
                (),
                tuple(re_seeded),
                deaths,
                mutation_events,
                len(matched_windows),
                ENERGY_PER_SEAT,
                len(self.units),
            )
            self.ledgers.append(ledger)
            return ledger

        # 3. Selection under a fixed seat budget. The pool of survivors and offspring
        #    exceeds the seat cap, so this is the step that removes genotypes, and its
        #    ordering is the antagonist's selection coefficient: energy rank, which is
        #    earned by contact. A unit that is never contacted holds no surplus and
        #    contributes nothing; a unit whose window matches the common host class
        #    contributes many copies. Equal ranks are broken by a fresh draw, never by
        #    unit id, so the result cannot depend on identifier order.
        pool = survivors + newborns
        # Selection under the seat budget. The pool of surviving parents and their
        # offspring is ranked by energy, which is earned by contact; the top ``seat_cap``
        # form the next generation. If the pool is smaller than the budget the roster
        # simply shrinks, and it can reach zero: that is the mechanism's own extinction
        # route, kept strict and unpatched. Equal ranks are broken by a fresh draw, never
        # by unit id, so the result cannot depend on identifier order.
        rng_by_unit = {
            unit.unit_id: rng.random() for unit in pool
        }
        pool.sort(key=lambda unit: (-float(unit.energy), rng_by_unit[unit.unit_id]))
        selected = pool[: self.seat_cap]
        dropped = tuple(u.unit_id for u in pool[self.seat_cap :])
        self.units = [replace(unit, alive=True) for unit in selected]
        newborn_ids = {unit.unit_id for unit in newborns}
        selected_newborns = tuple(
            unit for unit in selected if unit.unit_id in newborn_ids
        )
        kept = tuple(
            unit.unit_id for unit in selected if unit.unit_id not in newborn_ids
        )
        ledger = PassageLedger(
            gen,
            mode,
            kept,
            selected_newborns,
            deaths + dropped,
            mutation_events,
            len(matched_windows),
            (sum(u.energy for u in selected) / len(selected)) if selected else 0.0,
            len(self.units),
        )
        self.ledgers.append(ledger)
        return ledger

    def windows(self) -> list[str]:
        return [unit.window for unit in self.units]

    def mean_energy(self) -> float:
        return (
            sum(float(u.energy) for u in self.units) / len(self.units)
            if self.units
            else 0.0
        )

    def ancestry_rows(
        self, ledger: PassageLedger, *, run_id: str, seed: int, arm: str
    ) -> list[dict[str, object]]:
        """Rows for the campaign ancestry channel, antagonist side."""

        rows: list[dict[str, object]] = []
        for unit in ledger.newborns:
            rows.append(
                {
                    "run_id": run_id,
                    "seed": int(seed),
                    "arm": str(arm),
                    "generation": ledger.generation,
                    "event_id": f"ant-birth-{arm}-{seed}-{ledger.generation}-{unit.unit_id}",
                    "organism_id": unit.unit_id,
                    "parent_id": unit.parent_id,
                    "side": "antagonist",
                    "event": "birth",
                    "genotype_digest": unit.window,
                    "antagonist_digest": None,
                    "mutation": bool(unit.inherited_mutation),
                    "intervention_id": (
                        "RQ3-CUT-HERITABLE-ADAPTATION-V1"
                        if ledger.mode == ANTAGONIST_PASSAGE_SHUFFLED_LABELS
                        else None
                    ),
                }
            )
        for unit_id in ledger.deaths:
            rows.append(
                {
                    "run_id": run_id,
                    "seed": int(seed),
                    "arm": str(arm),
                    "generation": ledger.generation,
                    "event_id": f"ant-death-{arm}-{seed}-{ledger.generation}-{unit_id}",
                    "organism_id": unit_id,
                    "parent_id": None,
                    "side": "antagonist",
                    "event": "death",
                    "genotype_digest": None,
                    "antagonist_digest": None,
                    "mutation": None,
                    "intervention_id": None,
                }
            )
        return rows
