"""RQ-3: per-unit antagonist identity, ancestry, and the label-shuffled control.

Why this module exists
----------------------

The RQ-3 arms require the delayed adaptation route to be logged on *both* sides and
to be cut by a negative control while contact and energy costs are kept real. In the
tree at the discovery-program tip the antagonist is an anonymous ``list[str]`` of
recognition windows held on ``StructuralRQArm.parasite_windows``: units are kept by
shuffled index, replaced by sampling the realised contact set, and mutated, but no
unit carries an id, a parent or a death record. ``test-runs/rq3/`` recorded
``antagonist_ancestry_rows = 0`` on every live run for that reason, and there is no
label-shuffled passage mode at all, so the RQ-3 negative control cannot be run.

This module is additive and engine-free. It holds:

* :data:`ANTAGONIST_PASSAGE_SHUFFLED_LABELS` -- the negative-control passage mode;
* :class:`AntagonistUnit` and :func:`initial_units` -- a roster with stable ids;
* :func:`passage_update` -- the existing copassaged keep/mutate law, re-expressed on
  the roster, plus the shuffled-label variant;
* :func:`ancestry_rows` -- the JSONL rows the campaign schema requires on the
  antagonist side (``side="antagonist"``, with ``parent_id`` and ``mutation``).

Integration points (manager wiring, all inside ``closed_loop_hp_arm01_structural_rq``)
-------------------------------------------------------------------------------------

1. ``boot_structural``: ``self.antagonist_units = initial_units(parasite_windows)``.
2. ``_apply_hp_env_contact``: when ``collect_realised_host_pressure`` is true, also
   append one row per real pair ``(host_class, antagonist_class, affinity,
   intended_debit, realised_debit)`` to ``self.contact_pair_records``, and use
   ``self.antagonist_units[p_index].window`` as the paired antagonist window so the
   contact carries the unit id.
3. ``_passage_update``: delegate to :func:`passage_update`; keep the existing
   ``turnover_*`` bookkeeping by reading the returned ledger entry, and store
   ``self.passage_ledger.append(entry)``.
4. ``window_snapshot``: add ``"antagonist_units"`` (id, window, class, parent_id) and
   ``"antagonist_ancestry"`` (kept, newborn, deaths, mutation events) for the window.

Nothing here changes the debit rule, the affinity rule, the ATP ledger, any
threshold, or any pre-registered decision branch.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Sequence

from codontrace.errors import ConfigurationError
from codontrace.genesis.measurements.rq_frequency_clocks import (
    reference_graded_affinity,
)
from codontrace.rng import RNGManager

#: Negative-control passage mode: the antagonist is replenished from the realised
#: contact set with the *labels* permuted against the host classes. Real contact and
#: real ATP cost are untouched; only the frequency-to-composition route is cut.
ANTAGONIST_PASSAGE_SHUFFLED_LABELS = "shuffled_labels"


@dataclass(frozen=True, slots=True)
class AntagonistUnit:
    """One antagonist individual: stable identity plus its recognition window."""

    unit_id: str
    window: str
    parent_id: str | None
    born_generation: int

    def with_window(self, window: str) -> "AntagonistUnit":
        return replace(self, window=window)


@dataclass(frozen=True, slots=True)
class PassageLedger:
    """Per-generation antagonist ancestry record."""

    generation: int
    mode: str
    kept: tuple[str, ...]
    newborns: tuple[AntagonistUnit, ...]
    deaths: tuple[str, ...]
    mutation_events: int


def initial_units(windows: Sequence[str], *, generation: int = 0) -> list[AntagonistUnit]:
    """Founder roster: one unit per seat, id ``a{generation}-{seat}``."""

    if not windows:
        raise ConfigurationError("antagonist roster requires at least one window")
    return [
        AntagonistUnit(
            unit_id=f"a{int(generation)}-{seat}",
            window=str(window),
            parent_id=None,
            born_generation=int(generation),
        )
        for seat, window in enumerate(windows)
    ]


def passage_update(
    units: Sequence[AntagonistUnit],
    matched_windows: Sequence[str],
    *,
    mode: str,
    keep_fraction: float,
    mutation_rate: float,
    generation: int,
    rng: RNGManager,
    mutate_window,
) -> tuple[list[AntagonistUnit], PassageLedger]:
    """Advance the antagonist roster one generation.

    ``mode`` is the Pearl passage mode (``coevolve`` / ``frozen`` / ``absent``) or
    :data:`ANTAGONIST_PASSAGE_SHUFFLED_LABELS`. ``mutate_window`` is the existing
    window mutation helper, injected so this module does not duplicate the rule.

    The copassaged branch reproduces the recorded law exactly: keep ``int(kappa*n)``
    units chosen at random, replenish the rest by sampling the realised contact set
    with per-draw mutation. The shuffled-label branch keeps nothing and replenishes
    from a permuted view of the realised contact set, so which host class was common
    carries no information into the antagonist composition.
    """

    roster = list(units)
    n = len(roster)
    if mode == "absent":
        return [], PassageLedger(int(generation), mode, (), (), tuple(u.unit_id for u in roster), 0)
    if mode == "frozen":
        # Same units, same windows; identity persists and no birth or death occurs.
        return roster, PassageLedger(
            int(generation), mode, tuple(u.unit_id for u in roster), (), (), 0
        )

    keep_n = max(0, min(n, int(float(keep_fraction) * n)))
    if mode == ANTAGONIST_PASSAGE_SHUFFLED_LABELS:
        keep_n = 0
    replace_n = n - keep_n

    order = list(range(n))
    for i in range(len(order) - 1, 0, -1):
        j = rng.randrange(0, i + 1)
        order[i], order[j] = order[j], order[i]
    kept = [roster[order[i]] for i in range(keep_n)]
    kept_ids = {unit.unit_id for unit in kept}

    source = list(matched_windows) if matched_windows else [u.window for u in roster]
    if mode == ANTAGONIST_PASSAGE_SHUFFLED_LABELS:
        perm = list(range(len(source)))
        for i in range(len(perm) - 1, 0, -1):
            j = rng.randrange(0, i + 1)
            perm[i], perm[j] = perm[j], perm[i]
        source = [source[i] for i in perm]

    newborns: list[AntagonistUnit] = []
    mut_events = 0
    for seat in range(replace_n):
        source_seat = rng.randrange(0, len(source))
        parent = roster[source_seat] if source_seat < n else None
        parent_id = (
            parent.unit_id
            if parent is not None
            else f"contact-window:{str(source[source_seat])}"
        )
        window = source[source_seat]
        if float(mutation_rate) > 0.0 and rng.random() < float(mutation_rate):
            window = mutate_window(window, rng)
            mut_events += 1
        newborns.append(
            AntagonistUnit(
                unit_id=f"a{int(generation)}-{n + seat}",
                window=str(window),
                parent_id=parent_id,
                born_generation=int(generation),
            )
        )
    nxt = kept + newborns
    while len(nxt) < n:
        source_seat = rng.randrange(0, len(source))
        parent = roster[source_seat] if source_seat < n else None
        nxt.append(
            AntagonistUnit(
                unit_id=f"a{int(generation)}-pad{n - len(nxt)}",
                window=str(source[source_seat]),
                parent_id=(
                    parent.unit_id
                    if parent is not None
                    else f"contact-window:{str(source[source_seat])}"
                ),
                born_generation=int(generation),
            )
        )
    nxt = nxt[:n]
    after_ids = {unit.unit_id for unit in nxt}
    deaths = tuple(u.unit_id for u in roster if u.unit_id not in after_ids)
    ledger = PassageLedger(
        int(generation),
        mode,
        tuple(u.unit_id for u in kept),
        tuple(newborns),
        deaths,
        int(mut_events),
    )
    return nxt, ledger


def ancestry_rows(
    ledger: PassageLedger,
    *,
    run_id: str,
    seed: int,
    arm: str,
) -> list[dict[str, object]]:
    """Rows for the campaign's ancestry channel, antagonist side."""

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
                "mutation": int(ledger.mutation_events > 0),
                "intervention_id": (
                    "RQ3-CUT-ADAPTATION-ROUTE-V1"
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


def contact_pair_rows(
    pairs: Sequence[tuple[str, str, float, float, float]],
    *,
    run_id: str,
    seed: int,
    arm: str,
    generation: int,
) -> list[dict[str, object]]:
    """One row per realised contact pair, so pressure is reconstructible from raw."""

    rows = []
    for index, (host_class, ant_class, affinity, intended, realised) in enumerate(pairs):
        rows.append(
            {
                "run_id": run_id,
                "seed": int(seed),
                "arm": str(arm),
                "generation": int(generation),
                "event_id": f"pair-{arm}-{seed}-{generation}-{index}",
                "contact_edge_id": f"seat-{index}",
                "host_class": host_class,
                "antagonist_class": ant_class,
                "affinity": float(affinity),
                "intended_debit": float(intended),
                "realised_debit": float(realised),
                "matched": bool(affinity > 0.0),
                "opportunity": 1,
            }
        )
    return rows
