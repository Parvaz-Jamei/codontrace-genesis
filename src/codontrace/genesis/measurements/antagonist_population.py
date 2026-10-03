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

import math
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field, replace

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

#: Live accounting. Archived RQ-3 tables were produced before this contract and are
#: kept as results of the defective model: offspring used to receive a copy of the
#: parent's energy without a debit. Those files are not recomputed here.
ACCOUNTING_VERSION = "split_v2"


def _finite(name: str, value: float) -> float:
    number = float(value)
    if not math.isfinite(number):
        raise ConfigurationError(f"{name} must be finite")
    return number


@dataclass(frozen=True, slots=True)
class ContactEvent:
    """One realised contact. Income is credited to ``unit_id``, never to a window."""

    contact_id: str
    host_id: str
    unit_id: str
    atp_paid: float
    window: str = ""


@dataclass(frozen=True, slots=True)
class EnergyAccount:
    """Closed antagonist energy balance for one generation.

    ``opening + contact_income - maintenance_loss - death_loss - eviction_loss
    - reproduction_cost = closing``. Reproduction under ``split_v2`` has cost 0
    because the parent's energy is divided, not copied.
    """

    generation: int
    mode: str
    opening: float
    contact_income: float
    maintenance_loss: float
    death_loss: float
    eviction_loss: float
    reproduction_cost: float
    closing: float

    def residual(self) -> float:
        return (
            float(self.opening)
            + float(self.contact_income)
            - float(self.maintenance_loss)
            - float(self.death_loss)
            - float(self.eviction_loss)
            - float(self.reproduction_cost)
            - float(self.closing)
        )


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
    #   IF the two 6-bit windows are independent and each bit is uniform, the number
    #   of matching bits is Binomial(6, 0.5) and affinity (that count / 6) has mean 0.5.
    #   Mean 0.5 is not guaranteed for an evolved population unless it is measured.
    #   The historical derivation used that assumption:
    #   mean ATP per contact = 1.2 * 0.5 = 0.6 ATP
    #   the arm realises one contact seat per host, so the ATP throughput per seat per
    #   generation is also 0.6 ATP under the same assumption
    #   assimilated income per unit per generation = (EARNED_YIELD - PAIRING_COST) * 0.6
    #   = 0.3 ATP
    #   maintenance = half the assimilated income = 0.15 ATP per generation, so strict
    #   starvation death stays real (an uncontacted unit loses 0.15 per generation and
    #   dies) while a unit earning the standing income keeps a surplus.
    # The numeric value is NOT retuned. The same value is used in every arm, is never
    # re-chosen after an arm result, and its derivation is hashed into the run manifest.
    maintenance_cost: float = 0.15
    ledgers: list[PassageLedger] = None  # type: ignore[assignment]
    #: Pre-selection energy checkpoint per generation (controlled quantity, asserted
    #: equal across arms by the harness; see the comment inside ``advance``).
    pre_selection_signatures: list[dict[str, float | str]] = field(default_factory=list)
    energy_accounts: list[EnergyAccount] = field(default_factory=list)
    known_unit_ids: set[str] = field(default_factory=set)
    accounting_version: str = ACCOUNTING_VERSION
    # Birth counter for short ids. The previous id embedded the entire ancestor
    # chain (``a{gen}-{parent_unit_id}-{seat}``), so a living id was hundreds of
    # characters by generation 200 and still growing. parent_id already points at
    # the immediate parent. The id text is not an RNG input.
    child_serial: int = 0

    def __post_init__(self) -> None:
        if self.ledgers is None:
            self.ledgers = []
        if self.seat_cap < 1:
            raise ConfigurationError("antagonist seat cap must be >= 1")
        if not self.ancestral_windows:
            raise ConfigurationError("antagonist population requires ancestral windows")
        if not 0.0 <= float(self.keep_fraction) <= 1.0:
            raise ConfigurationError("keep fraction must be in [0, 1]")
        maintenance = _finite("maintenance cost", self.maintenance_cost)
        if maintenance <= 0.0:
            raise ConfigurationError("maintenance cost must be positive")
        mutation = _finite("mutation rate", self.mutation_rate)
        if not 0.0 <= mutation <= 1.0:
            raise ConfigurationError("mutation rate must be in [0, 1]")
        fecundity = _finite("fecundity", self.fecundity)
        if fecundity < 0.0:
            raise ConfigurationError("fecundity must be >= 0")
        seen: set[str] = set()
        for unit in self.units:
            if unit.unit_id in seen:
                raise ConfigurationError(f"duplicate antagonist unit id {unit.unit_id}")
            seen.add(unit.unit_id)
            energy = _finite(f"energy of {unit.unit_id}", unit.energy)
            if energy < 0.0:
                raise ConfigurationError(f"energy of {unit.unit_id} must be >= 0")
        historical = set(self.known_unit_ids) | seen
        for unit in self.units:
            if unit.parent_id == unit.unit_id:
                raise ConfigurationError(f"unit {unit.unit_id} cannot be its own parent")
            if unit.parent_id is not None and unit.parent_id not in historical:
                raise ConfigurationError(f"parent {unit.parent_id} has no history")
        self.known_unit_ids.update(seen)

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
        contact_events: Sequence[ContactEvent] | None = None,
    ) -> PassageLedger:
        """Mortality, reproduction, selection and truncation for one generation.

        Reproduction contract (``split_v2``): the parent remains. Its
        post-maintenance energy ``E`` is the only source for itself and its
        offspring. ``n`` offspring means ``n + 1`` equal shares, so the parent
        is debited and no energy is created. Reproduction cost is 0.

        ``contact_events``, when given, credit ``unit_id``. The legacy
        ``(window, atp_paid)`` pairs are used only when ``contact_events`` is
        omitted; they cannot tell same-window individuals apart.
        """

        # Contract note (reviewer finding, 2026-09-29): the frozen and shuffled-label
        # controls deliberately do NOT take an early return. They run the same contact
        # credit, maintenance, reproduction and seat-cap selection as the coevolving arm,
        # so the non-heritable energy budget is identical across arms and only the
        # information path is cut. An earlier revision reset control energy to
        # ``ENERGY_PER_SEAT`` every generation, which removed the energy accounting too and
        # confounded the primary contrast.
        gen = int(generation)
        roster = list(self.units)
        opening = float(sum(float(unit.energy) for unit in roster))
        if mode == "absent":
            energies = [float(unit.energy) for unit in roster]
            signature = {
                "generation": gen,
                "mode": mode,
                "roster": float(len(roster)),
                "maintenance_charged": 0.0,
                "energy_total": opening,
                "energy_mean": (opening / len(roster)) if roster else 0.0,
                "energy_min": min(energies) if energies else 0.0,
                "energy_max": max(energies) if energies else 0.0,
                "seats_offered": 0.0,
            }
            ledger = PassageLedger(
                gen, mode, (), (), tuple(u.unit_id for u in roster), 0, 0, 0.0, 0
            )
            self.units = []
            self.energy_accounts.append(
                EnergyAccount(gen, mode, opening, 0.0, 0.0, opening, 0.0, 0.0, 0.0)
            )
            self.pre_selection_signatures.append(signature)
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
        # A corpse still sitting in the roster is not credited. Its energy leaves
        # as death, so it cannot disappear from the balance.
        prior_dead = [unit for unit in roster if not unit.alive]
        death_loss = float(sum(float(unit.energy) for unit in prior_dead))
        dead_ids = [unit.unit_id for unit in prior_dead]
        roster = [unit for unit in roster if unit.alive]
        roster, contact_income = self._credit(
            roster, served_contacts=served_contacts, contact_events=contact_events
        )

        # PRE-SELECTION PARITY CHECKPOINT (reviewer requirement, 2026-09-29).
        #
        # Controlled quantity: the pre-selection energy budget of this generation. The
        # contact budget offered per seat, the per-seat payment rule and the maintenance
        # charged per unit are identical in every arm by construction, and the energy
        # distribution recorded here is the one the identical pipeline produced before any
        # reproduction or seat-cap selection acts.
        #
        # Outcome, not confound: after this point the arms may and should diverge. The
        # heritable cut changes which windows the roster carries, hence which contacts are
        # realised in the next generation and hence the realised income. Post-selection
        # divergence is part of the treatment effect and is logged as such; it is not a
        # parity failure.
        #
        # The checkpoint exists so the claim "the arms differ only in the information path"
        # can be asserted and audited rather than assumed.
        signature = {
                "generation": gen,
                "mode": mode,
                "roster": float(len(roster)),
                "maintenance_charged": float(len(roster))
                * float(self.maintenance_cost),
                "energy_total": float(sum(float(u.energy) for u in roster)),
                "energy_mean": (
                    float(sum(float(u.energy) for u in roster)) / len(roster)
                    if roster
                    else 0.0
                ),
                "energy_min": (
                    float(min(float(u.energy) for u in roster)) if roster else 0.0
                ),
                "energy_max": (
                    float(max(float(u.energy) for u in roster)) if roster else 0.0
                ),
                "seats_offered": float(
                    len(contact_events) if contact_events is not None else len(served_contacts)
                ),
        }

        # 1. Maintenance and mortality. Every living unit pays a fixed maintenance cost
        #    per generation, so energy earned by contact decays and a unit that has run
        #    its reserve down dies. Extinction is a real outcome of this mechanism, not
        #    a failure mode to be papered over: persistence comes from the substrate
        #    opt-in (`ecology=persistence_safe`), which keeps the pool populated while
        #    selection stays entirely inside this object. No top-up and no safety rule is
        #    applied here, because a rule introduced to restore persistence would also
        #    re-mix unsampled windows into the roster and dilute the energy ranking that
        #    the negative control has to separate.
        maintenance_loss = 0.0
        survivors: list[AntagonistUnit] = []
        for unit in roster:
            energy = float(unit.energy)
            cost = float(self.maintenance_cost)
            # The charge removes min(energy, cost). A unit that cannot pay the
            # whole charge dies, and no energy is left to book a second time.
            paid = energy if energy <= cost else cost
            maintenance_loss += paid
            if energy <= cost:
                dead_ids.append(unit.unit_id)
            else:
                survivors.append(replace(unit, energy=energy - paid))
        deaths = tuple(dead_ids)

        # 2. Reproduction, split_v2. The parent remains and is debited. n offspring
        #    divide the parent's energy into n + 1 equal shares. The sum is unchanged.
        newborns: list[AntagonistUnit] = []
        parents: list[AntagonistUnit] = []
        mutation_events = 0
        born_ids: list[str] = []
        effective_mutation = 0.0 if mode == "frozen" else float(self.mutation_rate)
        for unit in survivors:
            expected = float(self.fecundity) * float(unit.energy)
            fractional = expected - math.floor(expected)
            draws = int(math.floor(expected)) + (1 if rng.random() < fractional else 0)
            if draws <= 0:
                parents.append(unit)
                continue
            if unit.unit_id not in self.known_unit_ids:
                raise ConfigurationError(f"parent {unit.unit_id} has no history")
            share = float(unit.energy) / float(draws + 1)
            parent_energy = float(unit.energy) - share * float(draws)
            parents.append(replace(unit, energy=parent_energy))
            for _child_seat in range(draws):
                window = unit.window
                mutated = False
                if effective_mutation > 0.0 and rng.random() < effective_mutation:
                    window = mutate_window(window, rng)
                    mutation_events += 1
                    mutated = True
                child_id = f"a{gen}-n{self.child_serial}"
                self.child_serial += 1
                if child_id in self.known_unit_ids or child_id in born_ids:
                    raise ConfigurationError(f"duplicate antagonist unit id {child_id}")
                newborns.append(
                    AntagonistUnit(
                        unit_id=child_id,
                        window=str(window),
                        parent_id=unit.unit_id,
                        born_generation=gen,
                        energy=share,
                        inherited_mutation=mutated,
                    )
                )
                born_ids.append(child_id)

        if mode == ANTAGONIST_PASSAGE_SHUFFLED_LABELS:
            newborns = [
                replace(
                    unit,
                    window=str(
                        self.ancestral_windows[
                            rng.randrange(0, len(self.ancestral_windows))
                        ]
                    ),
                    inherited_mutation=False,
                )
                for unit in newborns
            ]

        pool = parents + newborns
        rng_by_unit = {unit.unit_id: rng.random() for unit in pool}
        if len(rng_by_unit) != len(pool):
            raise ConfigurationError("antagonist pool contains a repeated unit id")
        pool.sort(key=lambda unit: (-float(unit.energy), rng_by_unit[unit.unit_id]))
        selected = pool[: self.seat_cap]
        evicted = pool[self.seat_cap :]
        eviction_loss = float(sum(float(unit.energy) for unit in evicted))
        dropped = tuple(unit.unit_id for unit in evicted)
        if mode == "frozen":
            selected = self._reseat_frozen(selected, roster)
        self._reject_duplicate_ids(selected)
        closing = float(sum(float(unit.energy) for unit in selected))
        account = EnergyAccount(
            gen,
            mode,
            opening,
            contact_income,
            maintenance_loss,
            death_loss,
            eviction_loss,
            0.0,
            closing,
        )
        if abs(account.residual()) > 1e-9:
            raise ConfigurationError(
                f"antagonist energy account did not close: residual {account.residual()}"
            )
        self.known_unit_ids.update(born_ids)
        self.energy_accounts.append(account)
        self.pre_selection_signatures.append(signature)
        self.units = [replace(unit, alive=True) for unit in selected]
        newborn_ids = {unit.unit_id for unit in newborns}
        selected_newborns = tuple(unit for unit in selected if unit.unit_id in newborn_ids)
        kept = tuple(unit.unit_id for unit in selected if unit.unit_id not in newborn_ids)
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

    def _credit(
        self,
        roster: list[AntagonistUnit],
        *,
        served_contacts: Sequence[tuple[str, float]],
        contact_events: Sequence[ContactEvent] | None,
    ) -> tuple[list[AntagonistUnit], float]:
        net = EARNED_YIELD - PAIRING_COST
        credits = {unit.unit_id: 0.0 for unit in roster}
        counts = {unit.unit_id: 0 for unit in roster}
        income = 0.0
        if contact_events is not None:
            seen: set[str] = set()
            for event in contact_events:
                paid = _finite("contact payment", event.atp_paid)
                if paid < 0.0:
                    raise ConfigurationError("contact payment must be >= 0")
                if not event.contact_id or event.contact_id in seen:
                    raise ConfigurationError("contact id must be unique and non-empty")
                if not event.host_id:
                    raise ConfigurationError("contact host id must be non-empty")
                if event.unit_id not in credits:
                    raise ConfigurationError(f"contact names unknown unit {event.unit_id}")
                seen.add(event.contact_id)
                gain = net * paid
                credits[event.unit_id] += gain
                income += gain
                if paid > 0.0:
                    counts[event.unit_id] += 1
        else:
            queues: dict[str, list[float]] = {}
            for window, paid_raw in served_contacts:
                paid = _finite("contact payment", paid_raw)
                if paid < 0.0:
                    raise ConfigurationError("contact payment must be >= 0")
                queues.setdefault(str(window), []).append(paid)
            for unit in roster:
                queue = queues.get(unit.window) or []
                personal = float(queue.pop(0)) if queue else 0.0
                gain = net * personal
                credits[unit.unit_id] += gain
                income += gain
                if personal > 0.0:
                    counts[unit.unit_id] += 1
            leftover = sum(len(queue) for queue in queues.values())
            if leftover:
                raise ConfigurationError(
                    f"{leftover} contact payments matched no antagonist unit"
                )
        credited = [
            replace(
                unit,
                energy=float(unit.energy) + credits[unit.unit_id],
                contacts_served=int(unit.contacts_served) + counts[unit.unit_id],
            )
            for unit in roster
        ]
        return credited, income

    def _reseat_frozen(
        self, selected: list[AntagonistUnit], roster: list[AntagonistUnit]
    ) -> list[AntagonistUnit]:
        """Assign founder windows one-to-one. A unit is never seated twice."""

        by_window: dict[str, list[AntagonistUnit]] = {}
        for unit in selected:
            by_window.setdefault(unit.window, []).append(unit)
        used: set[str] = set()
        reseated: list[AntagonistUnit] = []
        for seat, _unit in enumerate(selected):
            founder_window = roster[seat].window if seat < len(roster) else selected[seat].window
            picked: AntagonistUnit | None = None
            bucket = by_window.get(founder_window, [])
            while bucket:
                cand = bucket.pop(0)
                if cand.unit_id not in used:
                    picked = cand
                    break
            if picked is None:
                for cand in selected:
                    if cand.unit_id not in used:
                        picked = cand
                        break
            if picked is None:
                raise ConfigurationError("frozen reseat ran out of unique units")
            used.add(picked.unit_id)
            reseated.append(
                replace(picked, window=str(founder_window), inherited_mutation=False)
            )
        if len(used) != len(selected):
            raise ConfigurationError("frozen reseat was not one-to-one")
        return reseated

    @staticmethod
    def _reject_duplicate_ids(units: Sequence[AntagonistUnit]) -> None:
        seen: set[str] = set()
        for unit in units:
            if unit.unit_id in seen:
                raise ConfigurationError(f"duplicate living unit id {unit.unit_id}")
            seen.add(unit.unit_id)

    def windows(self) -> list[str]:
        return [unit.window for unit in self.units]

    def mean_energy(self) -> float:
        return (
            sum(float(u.energy) for u in self.units) / len(self.units)
            if self.units
            else 0.0
        )

    def energy_signature(self) -> dict[str, float]:
        """Logged, asserted quantity: the post-contact energy budget of one generation.

        The RQ-3 claim is that the arms differ only in the heritable information path, so
        the non-heritable energy budget must be identical across the arms of a seed. This
        signature is the ledger's own account of that budget: roster size, total and mean
        energy, the energy floor, and the number of units at or below zero. A comparison
        that differs here is confounded and must not be reported as a mechanism result.
        """

        energies = sorted(float(u.energy) for u in self.units)
        return {
            "roster": float(len(energies)),
            "energy_total": float(sum(energies)),
            "energy_mean": float(sum(energies) / len(energies)) if energies else 0.0,
            "energy_min": float(energies[0]) if energies else 0.0,
            "energy_max": float(energies[-1]) if energies else 0.0,
            "at_or_below_zero": float(sum(1 for e in energies if e <= 0.0)),
        }

    @staticmethod
    def energy_budget_equal(
        signature_a: dict[str, float],
        signature_b: dict[str, float],
        *,
        tolerance: float = 1e-9,
    ) -> dict[str, object]:
        """Compare two arms' energy signatures; report every field that differs."""

        fields = (
            "roster",
            "energy_total",
            "energy_mean",
            "energy_min",
            "energy_max",
            "at_or_below_zero",
        )
        differences = {
            field: float(signature_a.get(field, 0.0)) - float(signature_b.get(field, 0.0))
            for field in fields
            if abs(
                float(signature_a.get(field, 0.0)) - float(signature_b.get(field, 0.0))
            )
            > tolerance
        }
        return {"equal": not differences, "differences": differences}

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
