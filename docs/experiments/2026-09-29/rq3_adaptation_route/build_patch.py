"""Builds test-runs/rq3/PROPOSED_CHANGE.patch against the repository working tree.

Reads codontrace-genesis/src/codontrace/genesis/closed_loop_hp_arm01_structural_rq.py,
applies the RQ-3 transformations in memory, and writes a unified diff plus the new
module file. Nothing inside the repository is written: the transformed copy lives in
memory and under test-runs/rq3/.

Usage: python build_patch.py
"""

from __future__ import annotations

import difflib
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = Path(r"E:\مقاله پزشکی شبیه سازی ویروس\codontrace-genesis")
TARGET_REL = "src/codontrace/genesis/closed_loop_hp_arm01_structural_rq.py"
TARGET = REPO / TARGET_REL
NEW_REL = "src/codontrace/genesis/measurements/antagonist_population.py"
NEW_MODULE = HERE / "antagonist_population.py"
OUT = HERE / "PROPOSED_CHANGE.patch"


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"anchor {label!r} matched {count} times, expected 1")
    return text.replace(old, new, 1)


# ---------------------------------------------------------------- transformations

ELIGIBILITY_COMMENT = '''SLICE_NAME = "HP-ARM01-STRUCTURAL-RQ-REGIME"'''

RUNTIME_FIELD_ANCHOR = """    # Domain-free diagnostics (WAVE8 P3): no HP args on the observer.
    generation_boundary_observer: Callable[..., None] | None = None"""

RUNTIME_FIELD_NEW = """    # RQ-3 opt-in: the arm-level switch for the heritable antagonist population.
    # The standing value leaves this arm byte-identical to the pre-patch build.
    antagonist_ecology: str = ANTAGONIST_ECOLOGY_STANDING
    # RQ-3: antagonist population with identity, reproduction and death. ``None`` on
    # the standing path, so ``parasite_windows`` and every recorded series are unchanged.
    antagonist_pop: object | None = None
    # ``(kept, replaced, mut_events, churn)`` per generation for the ancestry log.
    antagonist_ledger: list[tuple[int, int, int, int]] = field(default_factory=list)
    # RQ-3: one row per realised contact pair (host class, antagonist class, affinity,
    # intended debit, realised debit) when pressure collection is enabled, so realised
    # pressure is reconstructable from raw events for every class that was contacted.
    contact_pair_records: list[tuple[tuple[str, str, float, float, float], ...]] = field(
        default_factory=list
    )
    # Domain-free diagnostics (WAVE8 P3): no HP args on the observer.
    generation_boundary_observer: Callable[..., None] | None = None"""

IMPORT_ANCHOR = """from codontrace.genesis.measurements.rq_frequency_clocks import (
    host_realised_pressure_from_contacts,
)"""

IMPORT_NEW = """from codontrace.genesis.measurements.antagonist_population import (
    ANTAGONIST_ECOLOGY_POPULATION,
    ANTAGONIST_ECOLOGY_STANDING,
    ANTAGONIST_ECOLOGIES,
    ANTAGONIST_PASSAGE_SHUFFLED_LABELS,
    AntagonistPopulation,
)
from codontrace.genesis.measurements.rq_frequency_clocks import (
    host_realised_pressure_from_contacts,
)"""

BOOT_SIG_ANCHOR = """    @classmethod
    def boot_structural(
        cls,
        *,
        arm: str,
        seed: int,
    ) -> StructuralRQArm:"""

BOOT_SIG_NEW = """    @classmethod
    def boot_structural(
        cls,
        *,
        arm: str,
        seed: int,
        antagonist_ecology: str = ANTAGONIST_ECOLOGY_STANDING,
        antagonist_maintenance_cost: float | None = None,
    ) -> StructuralRQArm:
        \"\"\"Build a structural arm.

        ``antagonist_ecology`` is the arm-level opt-in for the RQ-3 antagonist
        population. The standing value leaves the arm byte-identical to the
        pre-patch build: the antagonist stays the anonymous window list and
        ``_passage_update`` keeps its recorded keep/replace/mutate behaviour, so
        every locked expectation is untouched. ``"population"`` selects the
        heritable genotype population. ``antagonist_maintenance_cost`` is the
        pre-declared substrate knob inside that opt-in; it is fixed before the runs,
        must be the same in every compared arm, and is never chosen, raised or
        lowered after seeing an arm result.
        \"\"\""""

BOOT_ANCHOR = """            host_bit_flip_rate=float(STRUCT_HOST_BIT_FLIP),
            parasite_keep_fraction=float(STRUCT_KEEP_FRACTION),
        )
        return structural"""

BOOT_NEW = """            host_bit_flip_rate=float(STRUCT_HOST_BIT_FLIP),
            parasite_keep_fraction=float(STRUCT_KEEP_FRACTION),
        )
        structural.antagonist_ecology = str(antagonist_ecology)
        if structural.antagonist_ecology not in ANTAGONIST_ECOLOGIES:
            raise ConfigurationError(
                f"unknown antagonist ecology {antagonist_ecology!r}"
            )
        if structural.antagonist_ecology == ANTAGONIST_ECOLOGY_POPULATION:
            if antagonist_maintenance_cost is None:
                structural.antagonist_pop = AntagonistPopulation.founders(
                    parasite_windows,
                    keep_fraction=float(STRUCT_KEEP_FRACTION),
                    mutation_rate=float(STRUCT_PARASITE_MUTATION),
                )
            else:
                structural.antagonist_pop = AntagonistPopulation.founders(
                    parasite_windows,
                    keep_fraction=float(STRUCT_KEEP_FRACTION),
                    mutation_rate=float(STRUCT_PARASITE_MUTATION),
                    maintenance_cost=float(antagonist_maintenance_cost),
                )
        else:
            structural.antagonist_pop = None
        return structural"""

RUN_ANCHOR = """                debit_count, matched = self._apply_hp_env_contact()
                self.match_debits_by_generation.append(int(debit_count))
                self._passage_update(matched, rng.fork(f"passage/{self.tick_index}"))"""

RUN_NEW = """                debit_count, matched = self._apply_hp_env_contact()
                self.match_debits_by_generation.append(int(debit_count))
                served: tuple[tuple[str, float], ...] = ()
                if self.antagonist_pop is not None:
                    # The record list grows only on paths that append one for the current
                    # generation, so it is empty on the first generation of an arm that
                    # does not collect pressure. Reading it defensively keeps the
                    # population path independent of a flag the boot path does not set.
                    records = (
                        self.contact_pair_records[-1]
                        if self.contact_pair_records
                        else ()
                    )
                    served = tuple((record[1], record[4]) for record in records)
                self._passage_update(
                    matched,
                    served_contacts=served,
                    rng=rng.fork(f"passage/{self.tick_index}"),
                )
                if self.antagonist_pop is not None:
                    ledger = self.antagonist_pop.ledgers[-1]
                    self.antagonist_ledger = [
                        (
                            len(ledger.kept),
                            len(ledger.newborns),
                            int(ledger.mutation_events),
                            len(ledger.deaths),
                        )
                    ]
                    self.parasite_windows = self.antagonist_pop.windows()"""

CONTACT_DOC_ANCHOR = """        The realised conditional pressure is derived from that evidence by
        ``host_realised_pressure_from_contacts`` — never from the parasite class
        histogram. Recording is additive and changes no debit, survival,
        threshold, or digest input.
        \"\"\""""

CONTACT_DOC_NEW = """        The realised conditional pressure is derived from that evidence by
        ``host_realised_pressure_from_contacts`` — never from the parasite class
        histogram. Recording is additive and changes no debit, survival,
        threshold, or digest input.

        RQ-3 additionally credits each participating antagonist unit with the ATP its
        contact actually took through the passage ledger (``served_contacts``) and,
        when pressure collection is enabled, keeps the per-pair records in
        ``contact_pair_records`` so pressure can be recomputed from raw events.
        \"\"\""""

CONTACT_ABSENT_ANCHOR = """        if self.passage == PASSAGE_ABSENT:
            self.graded_affinity_sum.append(0.0)
            self.graded_contact_count.append(0)
            return 0, []
        hosts = self._hosts()"""

CONTACT_ABSENT_NEW = """        if self.antagonist_pop is not None:
            self.antagonist_pop.begin_round()
        if self.passage == PASSAGE_ABSENT:
            self.graded_affinity_sum.append(0.0)
            self.graded_contact_count.append(0)
            if self.collect_realised_host_pressure:
                self.contact_pair_records.append(())
            return 0, []
        hosts = self._hosts()"""

CONTACT_NO_HOST_ANCHOR = """        if not hosts or not self.parasite_windows:
            self.graded_affinity_sum.append(0.0)
            self.graded_contact_count.append(0)
            return 0, []"""

CONTACT_NO_HOST_NEW = """        if not hosts or not self.parasite_windows:
            self.graded_affinity_sum.append(0.0)
            self.graded_contact_count.append(0)
            if self.collect_realised_host_pressure:
                self.contact_pair_records.append(())
            return 0, []"""

CONTACT_EMPTY_ANCHOR = """        # One parasite–host pair per seat per generation (no multi-hit pile-on).
        pair_n = min(len(hosts), len(self.parasite_windows))
        host_order = list(range(len(hosts)))
        # Deterministic rotate by tick so pairing is not always index-0 biased.
        rot = int(self.tick_index) % max(1, len(host_order))
        host_order = host_order[rot:] + host_order[:rot]
        for p_index in range(pair_n):
            host = hosts[host_order[p_index]]
            p_window = self.parasite_windows[p_index]
            host_window = _window(host)
            affinity = graded_affinity(host_window, p_window)
            contacts += 1
            aff_sum += affinity
            if self.collect_realised_host_pressure:
                h_class = joint_match_class(host_window)
                pressure_aff_sum[h_class] = pressure_aff_sum.get(h_class, 0.0) + float(
                    affinity
                )
                pressure_contacts[h_class] = pressure_contacts.get(h_class, 0) + 1
                pressure_available.setdefault(h_class, []).append(
                    float(host.atp_state.runtime_available)
                )
            if affinity <= 0.0:
                continue"""

CONTACT_EMPTY_NEW = """        # One parasite–host pair per seat per generation (no multi-hit pile-on).
        pair_n = min(len(hosts), len(self.parasite_windows))
        host_order = list(range(len(hosts)))
        # Deterministic rotate by tick so pairing is not always index-0 biased.
        rot = int(self.tick_index) % max(1, len(host_order))
        host_order = host_order[rot:] + host_order[:rot]
        pair_records: list[tuple[str, str, float, float, float]] = []
        for p_index in range(pair_n):
            host = hosts[host_order[p_index]]
            p_window = self.parasite_windows[p_index]
            host_window = _window(host)
            affinity = graded_affinity(host_window, p_window)
            contacts += 1
            aff_sum += affinity
            intended = float(self.virulence) * float(self.hp_env.steal_fraction) * float(
                affinity
            )
            pair_records.append(
                (
                    joint_match_class(host_window),
                    str(p_window),
                    float(affinity),
                    float(intended),
                    float(min(host.atp_state.runtime_available, intended)),
                )
            )
            if self.collect_realised_host_pressure:
                h_class = joint_match_class(host_window)
                pressure_aff_sum[h_class] = pressure_aff_sum.get(h_class, 0.0) + float(
                    affinity
                )
                pressure_contacts[h_class] = pressure_contacts.get(h_class, 0) + 1
                pressure_available.setdefault(h_class, []).append(
                    float(host.atp_state.runtime_available)
                )
            if affinity <= 0.0:
                continue"""

CONTACT_TAIL_ANCHOR = """        if self.collect_realised_host_pressure:
            self._record_realised_host_pressure(
                pressure_aff_sum, pressure_contacts, pressure_available
            )
        return debit_count, matched_windows"""

CONTACT_TAIL_NEW = """        if self.collect_realised_host_pressure:
            self._record_realised_host_pressure(
                pressure_aff_sum, pressure_contacts, pressure_available
            )
        if self.antagonist_pop is not None:
            # The antagonist income record must not depend on the pressure-collection
            # flag: the population path needs the realised seats to credit units, and a
            # default-booted arm does not set that flag. This list is a separate field
            # from ``host_realised_pressure_series``, so turning the flag off still
            # leaves every recorded pressure series empty and byte-identical.
            self.contact_pair_records.append(tuple(pair_records))
        return debit_count, matched_windows"""


def build_passage_update() -> str:
    """The exact replacement body for ``_passage_update`` (docstring included)."""

    return '''    def _passage_update(
        self,
        matched_windows: Sequence[str],
        *,
        served_contacts: Sequence[tuple[str, float]] = (),
        rng: RNGManager,
    ) -> None:
        """Advance the antagonist one generation.

        Two paths, selected by the arm-level opt-in ``antagonist_ecology``:

        * the standing path (default) is the recorded behaviour, unchanged: keep a
          random ``int(kappa * n)`` by index, replenish the rest by uniform sampling of
          the realised contact set with per-draw mutation, and keep the four
          ``turnover_*`` series;
        * ``"population"`` delegates to :class:`AntagonistPopulation`, where the
          antagonist is a heritable genotype population with per-unit identity, contact
          income, maintenance, starvation death, energy-proportional reproduction and
          selection under a fixed seat budget.

        The ``turnover_*`` series keep their names and meanings on both paths.
        """

        if self.antagonist_pop is None:
            self._passage_update_standing(matched_windows, rng)
            return
        if self.passage == PASSAGE_ABSENT:
            matched_windows = []
            served_contacts = ()
        mode = self.passage
        if mode not in (PASSAGE_COEVOLVE, PASSAGE_FROZEN, PASSAGE_ABSENT):
            mode = ANTAGONIST_PASSAGE_SHUFFLED_LABELS
        ledger = self.antagonist_pop.advance(
            matched_windows=matched_windows,
            served_contacts=served_contacts,
            mode=mode,
            generation=int(self.tick_index) + 1,
            rng=rng,
            mutate_window=_mutate_window,
        )
        self.parasite_windows = self.antagonist_pop.windows()
        self.turnover_kept.append(len(ledger.kept))
        self.turnover_replaced.append(len(ledger.newborns))
        self.turnover_mut_events.append(int(ledger.mutation_events))
        self.turnover_churn.append(len(ledger.deaths))

    def _passage_update_standing(
        self, matched_windows: Sequence[str], rng: RNGManager
    ) -> None:
        """The recorded passage behaviour, byte-identical to the pre-RQ-3 build."""

        if self.passage == PASSAGE_ABSENT:
            self.parasite_windows = []
            self.turnover_kept.append(0)
            self.turnover_replaced.append(0)
            self.turnover_mut_events.append(0)
            self.turnover_churn.append(0)
            return
        n = len(self.parasite_windows) or STRUCT_PARASITE_N
        if self.passage == PASSAGE_FROZEN:
            self.parasite_windows = [
                _DISTINCT_WINDOWS[i % len(_DISTINCT_WINDOWS)] for i in range(n)
            ]
            self.turnover_kept.append(n)
            self.turnover_replaced.append(0)
            self.turnover_mut_events.append(0)
            self.turnover_churn.append(0)
            return
        if self.passage != PASSAGE_COEVOLVE:
            self.turnover_kept.append(n)
            self.turnover_replaced.append(0)
            self.turnover_mut_events.append(0)
            self.turnover_churn.append(0)
            return
        kappa = float(self.parasite_keep_fraction)
        keep_n = int(kappa * n)
        if keep_n < 0:
            keep_n = 0
        if keep_n > n:
            keep_n = n
        replace_n = n - keep_n
        current = list(self.parasite_windows)
        before_unique = len(set(current))
        order = list(range(len(current)))
        for i in range(len(order) - 1, 0, -1):
            j = rng.randrange(0, i + 1)
            order[i], order[j] = order[j], order[i]
        kept = [current[order[i]] for i in range(keep_n)]
        source = list(matched_windows) if matched_windows else list(current)
        if not source:
            source = list(_DISTINCT_WINDOWS)
        nxt = list(kept)
        mut_events = 0
        for _ in range(replace_n):
            parent = source[rng.randrange(0, len(source))]
            window = parent
            if self.parasite_mutation > 0.0 and rng.random() < self.parasite_mutation:
                window = _mutate_window(window, rng)
                mut_events += 1
            nxt.append(window)
        while len(nxt) < n:
            nxt.append(source[rng.randrange(0, len(source))])
        self.parasite_windows = nxt[:n]
        after_unique = len(set(self.parasite_windows))
        self.turnover_kept.append(keep_n)
        self.turnover_replaced.append(replace_n)
        self.turnover_mut_events.append(mut_events)
        self.turnover_churn.append(abs(after_unique - before_unique))
'''


def transform(text: str) -> str:
    text = replace_once(text, IMPORT_ANCHOR, IMPORT_NEW, "import")
    text = replace_once(
        text, RUNTIME_FIELD_ANCHOR, RUNTIME_FIELD_NEW, "runtime fields"
    )
    text = replace_once(text, BOOT_SIG_ANCHOR, BOOT_SIG_NEW, "boot_structural signature")
    text = replace_once(text, BOOT_ANCHOR, BOOT_NEW, "boot_structural")
    text = replace_once(text, RUN_ANCHOR, RUN_NEW, "run_generations")
    text = replace_once(text, CONTACT_DOC_ANCHOR, CONTACT_DOC_NEW, "contact docstring")
    text = replace_once(text, CONTACT_ABSENT_ANCHOR, CONTACT_ABSENT_NEW, "contact absent")
    text = replace_once(
        text, CONTACT_NO_HOST_ANCHOR, CONTACT_NO_HOST_NEW, "contact no hosts"
    )
    text = replace_once(text, CONTACT_EMPTY_ANCHOR, CONTACT_EMPTY_NEW, "contact pairing")
    text = replace_once(text, CONTACT_TAIL_ANCHOR, CONTACT_TAIL_NEW, "contact tail")

    # _passage_update: replace from its def line through the end of turnover_churn.
    start = text.index("    def _passage_update(self, matched_windows: Sequence[str], rng: RNGManager) -> None:")
    marker = "        self.turnover_churn.append(abs(after_unique - before_unique))\n"
    end = text.index(marker) + len(marker)
    text = text[:start] + build_passage_update() + text[end:]

    # window_snapshot: empty snapshot keys, then the populated return.
    empty_anchor = """            "host_realised_pressure": {},
            "host_realised_pressure_lag": [],
            "parasite_class_hist_is_class_frequency_not_host_pressure": True,
        }"""
    empty_new = """            "host_realised_pressure": {},
            "host_realised_pressure_lag": [],
            "parasite_class_hist_is_class_frequency_not_host_pressure": True,
            "antagonist_units": [],
            "antagonist_ledger": None,
        }"""
    text = replace_once(text, empty_anchor, empty_new, "empty snapshot")

    ret_anchor = """            "host_realised_pressure": host_realised_pressure,
            "host_realised_pressure_lag": host_realised_pressure_lag,"""
    ret_new = """            "host_realised_pressure": host_realised_pressure,
            "host_realised_pressure_lag": host_realised_pressure_lag,
            "antagonist_units": [
                {
                    "unit_id": unit.unit_id,
                    "window": unit.window,
                    "class": joint_match_class(unit.window),
                    "parent_id": unit.parent_id,
                    "energy": round(float(unit.energy), 9),
                }
                for unit in (
                    self.antagonist_pop.units if self.antagonist_pop is not None else []
                )
            ],
            "antagonist_ledger": (
                None if not self.antagonist_pop or not self.antagonist_pop.ledgers
                else {
                    "mode": self.antagonist_pop.ledgers[-1].mode,
                    "kept": len(self.antagonist_pop.ledgers[-1].kept),
                    "newborns": len(self.antagonist_pop.ledgers[-1].newborns),
                    "deaths": len(self.antagonist_pop.ledgers[-1].deaths),
                    "mutation_events": int(
                        self.antagonist_pop.ledgers[-1].mutation_events
                    ),
                    "contacts": int(self.antagonist_pop.ledgers[-1].contacts),
                    "mean_energy": round(
                        float(self.antagonist_pop.ledgers[-1].mean_energy), 9
                    ),
                }
            ),"""
    text = replace_once(text, ret_anchor, ret_new, "populated snapshot")
    return text


def main() -> int:
    original = TARGET.read_text(encoding="utf-8")
    modified = transform(original)
    module = NEW_MODULE.read_text(encoding="utf-8")

    diff = difflib.unified_diff(
        original.splitlines(keepends=True),
        modified.splitlines(keepends=True),
        fromfile=f"a/{TARGET_REL}",
        tofile=f"b/{TARGET_REL}",
        n=3,
    )
    hunks = "".join(diff)
    header = (
        f"diff --git a/{TARGET_REL} b/{TARGET_REL}\n"
        f"--- a/{TARGET_REL}\n"
        f"+++ b/{TARGET_REL}\n"
    )
    # Strip the two diff-generated header lines and re-add the git header.
    lines = hunks.splitlines(keepends=True)
    body = "".join(lines[2:])

    module_lines = module.splitlines(keepends=True)
    module_header = (
        f"diff --git a/{NEW_REL} b/{NEW_REL}\n"
        "new file mode 100644\n"
        f"--- /dev/null\n"
        f"+++ b/{NEW_REL}\n"
        f"@@ -0,0 +1,{len(module_lines)} @@\n"
    )
    module_body = "".join(
        ("+" + line) if line.endswith("\n") else ("+" + line + "\n")
        for line in module.splitlines(keepends=True)
    )

    OUT.write_text(
        header + body + module_header + module_body, encoding="utf-8", newline="\n"
    )
    total = len((header + body + module_header + module_body).splitlines())
    try:
        print(f"wrote {OUT} ({total} lines)")
    except UnicodeEncodeError:
        print(f"wrote patch ({total} lines)")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
