"""RQ-BIDIRECTIONAL-TIMESHIFT-01, phase 1.

Engine for a bidirectional time-shift on the structural host-parasite arm.
The antagonist is the heritable population (contact income, death,
reproduction), not the standing window pool. Archived host and parasite
states are replayed with evolution, reproduction and mutation off. The
archive is not written by the replay.

This module does not score Red Queen and does not set ``red_queen_proved``.

Literature actually opened while choosing the assay, not a parameter search
---------------------------------------------------------------------------
Gandon, S. 2002. Local adaptation and the geometry of host-parasite
coevolution. Ecology Letters 5:246-256.
https://evolepid.cefe.cnrs.fr/pub/Gandon2002.pdf
Opened in full. Matching-allele specificity; local adaptation is performance
at home minus performance away. Frank's result, cited there, equates the
pattern of genotype frequencies across populations at one time with the
pattern across generations in one population. A time-shift is that temporal
transplant: archived generation t scored against a partner from t+k, with
no further evolution during the score.

Gandon, S. and Y. Michalakis. 2002. Local adaptation, evolutionary potential
and host-parasite coevolution. Journal of Evolutionary Biology.
Search extract of https://www.thereadgroup.net/wp-content/uploads/Gandon02_JEB.pdf
Relative mutation, population size and generation time change which side is
ahead. Phase 1 does not retune those quantities; they stay on the locked
structural design.

Dybdahl, M. F. and C. M. Lively. 1998. Host-parasite coevolution: evidence
for rare advantage and time-lagged selection. Evolution 52:1057-1066.
Search extract of the authors' summary page
https://public.archive.wsu.edu/dybdahl/public_html/evol98.html
Parasites tracked common host clones with a lag. The assay therefore keeps
the whole archived population, not a single modal window.

Lively, C. M. and M. F. Dybdahl. 2000. Parasite adaptation to locally common
host genotypes. Nature 405:679-681. Abstract opened via search. Sympatric
parasites infected locally common hosts more than rare ones; allopatric
parasites did not. Phase 1 only checks that the debit instrument and the
replay can tell populations apart. It does not claim that result.

The graded 6-bit window already in ``graded_affinity`` is the contact rule
(three bit-disjoint sub-loci). It is not replaced here.
"""

from __future__ import annotations

import hashlib
import json
import os
import time
from collections import Counter
from collections.abc import Mapping
from pathlib import Path

from codontrace.errors import ConfigurationError
from codontrace.genesis.closed_loop_hp_arm01 import (
    ARM_COPASSAGED,
    _tape,
    _window,
)
from codontrace.genesis.closed_loop_hp_arm01_structural_rq import (
    STRUCT_BIRTH_ATP,
    STRUCT_STEAL_FRACTION,
    STRUCT_VIRULENCE,
    StructuralRQArm,
    assert_pilot_seed_policy,
    graded_affinity,
    locked_design_dict,
)
from codontrace.genesis.closed_loop_pearl_spc import PASSAGE_COEVOLVE
from codontrace.genesis.host_parasite_life_plugin import (
    OUTCROSS_OUT_BITS,
    ROLE_PRIMARY,
    ROLE_SECONDARY,
)
from codontrace.genesis.measurements.antagonist_population import (
    ANTAGONIST_ECOLOGY_POPULATION,
    ANTAGONIST_PASSAGE_SHUFFLED_LABELS,
    EARNED_YIELD,
    PAIRING_COST,
    AntagonistPopulation,
    AntagonistUnit,
)
from codontrace.genesis.organism import GenesisOrganism
from codontrace.genesis.population import PopulationState

EXPERIMENT_ID = "RQ-BIDIRECTIONAL-TIMESHIFT-01"
PHASE = 1
# Pilot only. A later confirmatory must not reuse these seeds.
PHASE1_PILOT_SEEDS: tuple[int, ...] = (9101, 9102, 9103, 9104)
SMOKE_SEED = 9099
PHASE1_GENERATIONS = 200
SNAPSHOT_STRIDE = 20
SMOKE_GENERATIONS = 4

# Arm A: both inheritance paths open.
# Arm B: parasite offspring windows are redrawn from the ancestral pool
#         (shuffled labels). Host inheritance stays open. Contact and cost stay.
# Arm C: host reproduction and bit flips are off. This is not a pure evolution control.
#         Parasite population still coevolves. Host population, contact and cost stay.
# Arm D: both cuts at once.
ARM_A = "A"
ARM_B = "B"
ARM_C = "C"
ARM_D = "D"
ARM_PILOT = "pilot"
ARMS: tuple[str, ...] = (ARM_A, ARM_B, ARM_C, ARM_D)

# Instrument pairs. Affinities differ by the locked graded rule, so debits
# must differ. This is an instrument check, not a coevolution result.
INSTRUMENT_PAIR_HIGH = ("000000", "000000")
INSTRUMENT_PAIR_LOW = ("000000", "111000")

RED_QUEEN_PROVED = False
SNAPSHOT_SCHEMA = "rq-timeshift-snapshot/1"
ARCHIVE_SCHEMA = "rq-timeshift-archive/1"
RQ_CODE_VERSION = "rq-mechanism-v2/0.3.0b12"
RQ_DESIGN_VERSION = "hp-arm01-structural/timeshift-phase1"


def control_statement(arm_name: str) -> str:
    """What an arm actually cuts. Names that over-claim are refused."""

    key = str(arm_name)
    if key == ARM_A:
        return (
            "Both genotypes can be transmitted. Host reproduction stays on and "
            "parasite offspring keep inherited windows, subject to mutation. "
            "Contact and cost stay on."
        )
    if key == ARM_B:
        return (
            "Parasite offspring windows are redrawn from the ancestral pool "
            "(shuffled_labels). This is not a frozen genotype. Host inheritance "
            "stays on. Contact and cost stay on."
        )
    if key == ARM_C:
        return (
            "Host reproduction is off and host bit flips are off, so living host "
            "windows stay put and host births stop. This is not a pure evolution "
            "control: host demography is stopped, not only an evolutionary "
            "operator. Contact and cost remain. The parasite population still "
            "reproduces."
        )
    if key == ARM_D:
        return (
            "Both cuts at once: host reproduction is off, and parasite offspring "
            "windows are shuffled_labels. shuffled_labels is not a frozen "
            "genotype, and reproduction off is not a pure evolution control. "
            "Contact and cost remain."
        )
    if key == ARM_PILOT:
        return "Pilot ecology: both inheritance paths open. Not a control label."
    raise ConfigurationError(f"unknown timeshift arm {arm_name!r}")


def config_digest() -> str:
    """Digest of the locked structural design. Not a content digest of one snapshot."""

    return _canonical({"design": locked_design_dict(), "experiment": EXPERIMENT_ID})


def _canonical(body: Mapping[str, object]) -> str:
    encoded = json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(encoded.encode()).hexdigest()


def _assert_phase1_seeds(seeds: tuple[int, ...]) -> None:
    assert_pilot_seed_policy(seeds)
    if len(set(seeds)) != len(seeds):
        raise ConfigurationError("phase-1 seeds must be unique")
    # Structural RQ's own pilot seeds are a different experiment.
    from codontrace.genesis.closed_loop_hp_arm01_structural_rq import PILOT_SEEDS

    shared = sorted(set(seeds) & set(PILOT_SEEDS))
    if shared:
        raise ConfigurationError(
            f"structural RQ pilot seeds must not be reused here; overlap={shared}"
        )


def build_arm(arm_name: str, seed: int) -> StructuralRQArm:
    """Population ecology. Standing passage is not used."""

    key = str(arm_name)
    if key not in {ARM_A, ARM_B, ARM_C, ARM_D, ARM_PILOT}:
        raise ConfigurationError(f"unknown timeshift arm {arm_name!r}")
    arm = StructuralRQArm.boot_structural(
        arm=ARM_COPASSAGED,
        seed=int(seed),
        antagonist_ecology=ANTAGONIST_ECOLOGY_POPULATION,
    )
    if arm.antagonist_pop is None:
        raise ConfigurationError("population ecology did not build an antagonist population")
    if key in {ARM_C, ARM_D}:
        arm.freeze_host_genotypic_inheritance()
    if key in {ARM_B, ARM_D}:
        arm.passage = ANTAGONIST_PASSAGE_SHUFFLED_LABELS
    else:
        arm.passage = PASSAGE_COEVOLVE
    # Timeshift histories do not use seed+generation. Legacy structural arms,
    # which never set these fields, keep that older mixer.
    arm.stream_root = EXPERIMENT_ID
    arm.stream_history = str(int(seed))
    return arm


def _hosts_payload(arm: StructuralRQArm) -> list[dict[str, object]]:
    parents = {
        rec.organism_id: rec.parent_id for rec in arm.runner.population.lineage
    }
    rows: list[dict[str, object]] = []
    for org in arm._hosts():
        rows.append(
            {
                "id": str(org.id),
                "window": _window(org),
                "runtime_atp": float(org.atp_state.runtime_available),
                "parent_id": parents.get(org.id),
            }
        )
    rows.sort(key=lambda row: str(row["id"]))
    return rows


def _parasite_payload(arm: StructuralRQArm) -> list[dict[str, object]]:
    pop = arm.antagonist_pop
    if pop is None:
        raise ConfigurationError("parasite archive requires the population ecology")
    rows = [
        {
            "unit_id": unit.unit_id,
            "window": unit.window,
            "energy": float(unit.energy),
            "parent_id": unit.parent_id,
            "born_generation": int(unit.born_generation),
        }
        for unit in pop.units
    ]
    rows.sort(key=lambda row: str(row["unit_id"]))
    return rows


def snapshot_body(arm: StructuralRQArm, *, seed: int, arm_name: str, generation: int) -> dict[str, object]:
    body: dict[str, object] = {
        "experiment": EXPERIMENT_ID,
        "phase": PHASE,
        "seed": int(seed),
        "arm": str(arm_name),
        "generation": int(generation),
        "host_inheritance": arm.host_inheritance,
        "passage": arm.passage,
        "hosts": _hosts_payload(arm),
        "parasites": _parasite_payload(arm),
        "red_queen_proved": RED_QUEEN_PROVED,
    }
    body["digest"] = _canonical({k: v for k, v in body.items() if k != "digest"})
    return body


def write_snapshot(path: Path, body: Mapping[str, object]) -> str:
    """Create an immutable snapshot. A second write to the same path fails."""

    payload = {k: v for k, v in dict(body).items() if k != "digest"}
    digest = _canonical(payload)
    payload["digest"] = digest
    path.parent.mkdir(parents=True, exist_ok=True)
    flags = os.O_CREAT | os.O_EXCL | os.O_WRONLY
    fd = os.open(path, flags, 0o644)
    with os.fdopen(fd, "w", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, sort_keys=True, separators=(",", ":")))
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())
    return digest


def read_snapshot(path: Path) -> dict[str, object]:
    raw = path.read_text(encoding="utf-8")
    body = json.loads(raw)
    if not isinstance(body, dict):
        raise ConfigurationError("snapshot must be a JSON object")
    digest = str(body.get("digest") or "")
    payload = {k: v for k, v in body.items() if k != "digest"}
    computed = _canonical(payload)
    if digest != computed:
        raise ConfigurationError("snapshot digest does not match its body")
    body["digest"] = computed
    return body


def read_bound_snapshot(path: Path, *, expected: Mapping[str, object]) -> dict[str, object]:
    """Reject a healthy content digest whose identity is not the requested run.

    The content digest is necessary and not sufficient. Experiment, schema,
    history, seed, arm, generation, run id, config digest and code/design
    version must all match ``expected``.
    """

    body = read_snapshot(path)
    required = (
        "arm",
        "code_version",
        "config_digest",
        "design_version",
        "experiment",
        "generation",
        "history_id",
        "run_id",
        "schema",
        "seed",
    )
    for key in required:
        if key not in body or body[key] in (None, ""):
            raise ConfigurationError(f"snapshot missing schema field {key}")
    for key, value in expected.items():
        if body.get(key) != value:
            raise ConfigurationError(f"snapshot identity rejected: {key}")
    return body


def replay_archived_contact(
    hosts: list[dict[str, object]],
    parasites: list[dict[str, object]],
    *,
    virulence: float = STRUCT_VIRULENCE,
    steal_fraction: float = STRUCT_STEAL_FRACTION,
    seed: int = 0,
    atp_override: float | None = None,
    tick_index: int = 0,
) -> dict[str, object]:
    """Score one contact round on copies through the engine debit path.

    Evolution, reproduction and mutation stay off. Turning reproduction off
    here is a measurement freeze so the archived individuals are not replaced
    during the score. It is not a pure evolution control. The input lists and
    the dicts inside them are not modified. Parasite ``advance`` is not
    called, so parasite reproduction does not run. Host ``step_generation``
    is not called. Debit, host ATP loss and antagonist credit are read from
    the engine objects, not from a second formula.
    """

    host_token = json.dumps(hosts, sort_keys=True, separators=(",", ":"))
    parasite_token = json.dumps(parasites, sort_keys=True, separators=(",", ":"))
    host_copy = json.loads(host_token)
    parasite_copy = json.loads(parasite_token)
    if not host_copy or not parasite_copy:
        raise ConfigurationError("replay requires both populations")
    for index, row in enumerate(host_copy):
        if row.get("id") in (None, ""):
            row["id"] = f"assay-host-{index}"
        if atp_override is not None:
            row["runtime_atp"] = float(atp_override)
        elif "runtime_atp" not in row:
            row["runtime_atp"] = float(STRUCT_BIRTH_ATP)
    for index, row in enumerate(parasite_copy):
        if row.get("unit_id") in (None, ""):
            row["unit_id"] = f"assay-parasite-{index}"
        if "energy" not in row:
            row["energy"] = 1.0
        if "born_generation" not in row:
            row["born_generation"] = 0

    arm = build_arm(ARM_C, seed)
    # Reproduction is already off on this scratch arm. That is only so the
    # score cannot evolve. Do not describe it as an evolution control.
    pop = arm.antagonist_pop
    if not isinstance(pop, AntagonistPopulation):
        raise ConfigurationError("replay requires the antagonist population")
    pop.mutation_rate = 0.0
    arm.parasite_mutation = 0.0
    arm.virulence = float(virulence)
    arm.hp_env.steal_fraction = float(steal_fraction)
    arm.tick_index = int(tick_index)
    arm.passage = PASSAGE_COEVOLVE

    organisms: list[GenesisOrganism] = []
    seen_hosts: set[str] = set()
    before_atp: dict[str, float] = {}
    for row in host_copy:
        oid = str(row["id"])
        if oid in seen_hosts:
            raise ConfigurationError(f"duplicate archived host id {oid}")
        seen_hosts.add(oid)
        window = str(row["window"])
        before_atp[oid] = float(row["runtime_atp"])
        organisms.append(
            GenesisOrganism.from_bits(
                oid,
                _tape(OUTCROSS_OUT_BITS, window),
                initial_runtime_atp=before_atp[oid],
                position=(0, 0),
            )
        )
    units: list[AntagonistUnit] = []
    seen_units: set[str] = set()
    for row in parasite_copy:
        uid = str(row["unit_id"])
        if uid in seen_units:
            raise ConfigurationError(f"duplicate archived parasite id {uid}")
        seen_units.add(uid)
        parent = row.get("parent_id")
        units.append(
            AntagonistUnit(
                unit_id=uid,
                window=str(row["window"]),
                parent_id=None if parent in (None, "") else str(parent),
                born_generation=int(row.get("born_generation") or 0),
                energy=float(row["energy"]),
            )
        )
    pop.units = units
    pop.known_unit_ids.update(seen_units)
    arm.parasite_windows = [unit.window for unit in units]
    arm.runner.population = PopulationState(
        generation=0,
        tick=0,
        organisms=tuple(organisms),
        lineage=(),
        fitness=(),
    )
    arm.roles = {org.id: ROLE_PRIMARY for org in organisms}
    arm.roles["parasite_stock"] = ROLE_SECONDARY
    ledgers_before = len(pop.ledgers)
    if arm.runner.configs.reproduction.enabled:
        raise ConfigurationError("replay left host reproduction enabled")
    if float(arm.runner.configs.mutation.bit_flip_rate) != 0.0:
        raise ConfigurationError("replay left host mutation enabled")
    arm._apply_hp_env_contact()
    if len(pop.ledgers) != ledgers_before:
        raise ConfigurationError("replay advanced parasite reproduction")
    if arm.runner.population.generation != 0:
        raise ConfigurationError("replay stepped the host population")
    records = arm.contact_pair_records[-1] if arm.contact_pair_records else ()
    total_debit = float(sum(row[4] for row in records))
    contacts = len(records)
    mean_affinity = (
        float(sum(row[2] for row in records) / contacts) if contacts else 0.0
    )
    events = arm.antagonist_contact_events[-1] if arm.antagonist_contact_events else ()
    event_debit = float(sum(float(event.atp_paid) for event in events))
    loss = float(
        sum(before_atp[org.id] - float(org.atp_state.runtime_available) for org in organisms)
    )
    _roster, credit = pop._credit(
        list(pop.units),
        served_contacts=(),
        contact_events=events,
    )
    scale = float(virulence) * float(steal_fraction)
    infectivity = None if contacts == 0 else (event_debit / float(contacts)) / scale
    archive_mutated = (
        json.dumps(hosts, sort_keys=True, separators=(",", ":")) != host_token
        or json.dumps(parasites, sort_keys=True, separators=(",", ":")) != parasite_token
    )
    if archive_mutated:
        raise ConfigurationError("replay mutated the archived populations")
    return {
        "contacts": contacts,
        "total_debit": total_debit,
        "debit": event_debit,
        "credit": float(credit),
        "loss": loss,
        "infectivity": infectivity,
        "mean_affinity": mean_affinity,
        "evolution": False,
        "reproduction": False,
        "mutation": False,
        "measurement_freeze_is_evolution_control": False,
        "archive_mutated": False,
        "red_queen_proved": RED_QUEEN_PROVED,
    }


def instrument_two_pair_debit() -> dict[str, object]:
    """Two window pairs with different affinity must produce different debit."""

    high_aff = graded_affinity(*INSTRUMENT_PAIR_HIGH)
    low_aff = graded_affinity(*INSTRUMENT_PAIR_LOW)
    if high_aff == low_aff:
        raise ConfigurationError("instrument pairs do not differ in affinity")
    atp = float(STRUCT_BIRTH_ATP)

    def _one(host_window: str, parasite_window: str) -> dict[str, object]:
        hosts = [
            {
                "id": "instrument-host",
                "window": host_window,
                "runtime_atp": atp,
                "parent_id": None,
            }
        ]
        parasites = [
            {
                "unit_id": "instrument-parasite",
                "window": parasite_window,
                "energy": 1.0,
                "parent_id": None,
                "born_generation": 0,
            }
        ]
        scored = replay_archived_contact(
            hosts,
            parasites,
            virulence=STRUCT_VIRULENCE,
            steal_fraction=STRUCT_STEAL_FRACTION,
        )
        return scored

    high = _one(*INSTRUMENT_PAIR_HIGH)
    low = _one(*INSTRUMENT_PAIR_LOW)
    valid = float(high["total_debit"]) != float(low["total_debit"])
    return {
        "valid": valid,
        "pair_high": {
            "windows": list(INSTRUMENT_PAIR_HIGH),
            "affinity": high_aff,
            "total_debit": high["total_debit"],
        },
        "pair_low": {
            "windows": list(INSTRUMENT_PAIR_LOW),
            "affinity": low_aff,
            "total_debit": low["total_debit"],
        },
        "virulence": STRUCT_VIRULENCE,
        "steal_fraction": STRUCT_STEAL_FRACTION,
        "available_atp": atp,
        "red_queen_proved": RED_QUEEN_PROVED,
        "note": "instrument only; not Red Queen evidence",
    }


def invariant_status(arm: StructuralRQArm, *, generation: int, founder_ids: set[str]) -> str:
    pop = arm.antagonist_pop
    if pop is None:
        return "missing-population"
    if len(pop.energy_accounts) != int(generation):
        return "energy-checkpoint-length"
    if len(pop.pre_selection_signatures) != int(generation):
        return "preselection-checkpoint-length"
    if len(pop.ledgers) != int(generation):
        return "ledger-length"
    if len(arm.antagonist_ledger) != int(generation):
        return "arm-ledger-length"
    if len(arm.antagonist_unit_series) != int(generation):
        return "unit-snapshot-length"
    residual = abs(pop.energy_accounts[-1].residual())
    if residual > 1e-6:
        return "energy-residual"
    ids = [unit.unit_id for unit in pop.units]
    if len(ids) != len(set(ids)):
        return "duplicate-parasite-id"
    for unit in pop.units:
        if unit.parent_id == unit.unit_id:
            return "self-parent"
        if unit.parent_id is not None and unit.parent_id not in pop.known_unit_ids:
            return "parasite-parent-missing"
    known_hosts = set(founder_ids)
    host_ids = [org.id for org in arm._hosts()]
    if len(host_ids) != len(set(host_ids)):
        return "duplicate-host-id"
    for rec in arm.runner.population.lineage:
        # The population stepper records generation-0 founders with no parent.
        # Those are not births. A later record without a parent is an orphan birth.
        if not rec.parent_id:
            if int(rec.generation) != 0:
                return "host-birth-without-parent"
            known_hosts.add(rec.organism_id)
            continue
        if rec.parent_id not in known_hosts:
            return "host-parent-missing"
        known_hosts.add(rec.organism_id)
    try:
        snap = arm.window_snapshot(int(generation))
    except ConfigurationError as exc:
        return f"snapshot:{exc}"
    if snap["generation"] != int(generation):
        return "snapshot-generation"
    if arm.antagonist_pop is not None and not snap["antagonist_units"] and pop.units:
        return "snapshot-empty-units"
    return "ok"


class LiveLog:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)
        self.log_path = root / "live.log"
        self.data_path = root / "trajectory.jsonl"
        self._log = self.log_path.open("a", encoding="utf-8", buffering=1)
        self._data = self.data_path.open("a", encoding="utf-8", buffering=1)

    def line(self, text: str) -> None:
        self._log.write(text.rstrip("\n") + "\n")
        self._log.flush()
        os.fsync(self._log.fileno())

    def generation(self, row: Mapping[str, object]) -> None:
        text = (
            f"seed={row['seed']} arm={row['arm']} generation={row['generation']} "
            f"host_census={row['host_census']} parasite_census={row['parasite_census']} "
            f"host_energy={row['host_energy']:.6f} parasite_energy={row['parasite_energy']:.6f} "
            f"host_births={row['host_births']} host_deaths={row['host_deaths']} "
            f"parasite_births={row['parasite_births']} parasite_deaths={row['parasite_deaths']} "
            f"contacts={row['contacts']} invariant={row['invariant']}"
        )
        self.line(text)
        self._data.write(json.dumps(dict(row), sort_keys=True, separators=(",", ":")))
        self._data.write("\n")
        self._data.flush()
        os.fsync(self._data.fileno())

    def close(self) -> None:
        self._log.close()
        self._data.close()


def _generation_row(
    arm: StructuralRQArm,
    *,
    seed: int,
    arm_name: str,
    generation: int,
    founder_ids: set[str],
    prev_host_census: int,
    prev_lineage: int,
) -> dict[str, object]:
    hosts = arm._hosts()
    host_census = len(hosts)
    births_total = sum(1 for rec in arm.runner.population.lineage if rec.parent_id)
    host_births = births_total - prev_lineage
    host_deaths = prev_host_census + host_births - host_census
    pop = arm.antagonist_pop
    assert pop is not None
    ledger = pop.ledgers[-1]
    status = invariant_status(arm, generation=generation, founder_ids=founder_ids)
    if host_deaths < 0:
        status = "host-census"
    return {
        "experiment": EXPERIMENT_ID,
        "phase": PHASE,
        "seed": int(seed),
        "arm": arm_name,
        "generation": int(generation),
        "host_census": host_census,
        "parasite_census": len(pop.units),
        "host_energy": float(sum(org.atp_state.runtime_available for org in hosts)),
        "parasite_energy": float(sum(unit.energy for unit in pop.units)),
        "host_births": int(host_births),
        "host_deaths": int(host_deaths),
        "parasite_births": len(ledger.newborns),
        "parasite_deaths": len(ledger.deaths),
        "contacts": int(arm.graded_contact_count[-1]) if arm.graded_contact_count else 0,
        "debits": int(arm.match_debits_by_generation[-1]) if arm.match_debits_by_generation else 0,
        "invariant": status,
        "host_inheritance": arm.host_inheritance,
        "passage": arm.passage,
        "red_queen_proved": RED_QUEEN_PROVED,
    }


def _income_association(arm: StructuralRQArm) -> tuple[float, float, int, int]:
    """Mean contact income of parents of newborns versus everyone else paired."""

    pop = arm.antagonist_pop
    assert pop is not None
    events = arm.antagonist_contact_events[-1] if arm.antagonist_contact_events else ()
    net = float(EARNED_YIELD) - float(PAIRING_COST)
    income: dict[str, float] = {}
    for event in events:
        income[event.unit_id] = income.get(event.unit_id, 0.0) + net * float(event.atp_paid)
    parents = {
        unit.parent_id
        for unit in pop.ledgers[-1].newborns
        if unit.parent_id
    }
    universe = set(income) | parents
    if not parents or not (universe - parents):
        return 0.0, 0.0, 0, 0
    parent_vals = [income.get(uid, 0.0) for uid in parents]
    other_vals = [income.get(uid, 0.0) for uid in universe - parents]
    return (
        sum(parent_vals) / len(parent_vals),
        sum(other_vals) / len(other_vals),
        len(parent_vals),
        len(other_vals),
    )


def run_logged_generations(
    arm: StructuralRQArm,
    *,
    seed: int,
    arm_name: str,
    generations: int,
    live: LiveLog,
    snapshot_dir: Path | None,
    snapshot_stride: int | None,
) -> dict[str, object]:
    founder_ids = {org.id for org in arm._hosts()}
    founder_windows = {org.id: _window(org) for org in arm._hosts()}
    prev_census = len(founder_ids)
    prev_lineage = 0
    parent_income = 0.0
    other_income = 0.0
    parent_n = 0
    other_n = 0
    failed: str | None = None
    for generation in range(1, int(generations) + 1):
        arm.run_generations(1)
        row = _generation_row(
            arm,
            seed=seed,
            arm_name=arm_name,
            generation=generation,
            founder_ids=founder_ids,
            prev_host_census=prev_census,
            prev_lineage=prev_lineage,
        )
        p_mean, o_mean, p_n, o_n = _income_association(arm)
        parent_income += p_mean * p_n
        other_income += o_mean * o_n
        parent_n += p_n
        other_n += o_n
        row["parent_mean_income"] = p_mean
        row["other_mean_income"] = o_mean
        live.generation(row)
        if row["invariant"] != "ok":
            failed = str(row["invariant"])
            break
        if (
            snapshot_dir is not None
            and snapshot_stride
            and generation % int(snapshot_stride) == 0
        ):
            body = snapshot_body(arm, seed=seed, arm_name=arm_name, generation=generation)
            path = snapshot_dir / f"seed{seed}_{arm_name}_g{generation:04d}.json"
            write_snapshot(path, body)
            loaded = read_snapshot(path)
            if loaded["digest"] != body["digest"]:
                failed = "snapshot-reread"
                live.line(
                    f"seed={seed} arm={arm_name} generation={generation} invariant=snapshot-reread"
                )
                break
        prev_census = int(row["host_census"])
        prev_lineage += int(row["host_births"])
    windows_now = {org.id: _window(org) for org in arm._hosts()}
    # Death of a founder is not a genotype change. A new id or a changed
    # window on a survivor is.
    host_window_changed = any(
        oid in windows_now and windows_now[oid] != window
        for oid, window in founder_windows.items()
    ) or any(oid not in founder_windows for oid in windows_now)
    start_hist = arm.parasite_class_hist_series[0] if arm.parasite_class_hist_series else ()
    end_hist = arm.parasite_class_hist_series[-1] if arm.parasite_class_hist_series else ()
    parasite_changed = start_hist != end_hist
    frozen_held = all(windows_now.get(oid) == window for oid, window in founder_windows.items() if oid in windows_now)
    pop = arm.antagonist_pop
    assert pop is not None
    newborn_parents = sum(1 for ledger in pop.ledgers for unit in ledger.newborns if unit.parent_id)
    return {
        "generations_completed": len(arm.host_joint_class_series),
        "failed": failed,
        "host_births": sum(
            1 for rec in arm.runner.population.lineage if rec.parent_id
        ),
        "host_window_changed": host_window_changed,
        "parasite_window_changed": parasite_changed,
        "frozen_windows_held": frozen_held,
        "parasite_births_with_parents": newborn_parents,
        "parasite_mutation_events": sum(ledger.mutation_events for ledger in pop.ledgers),
        "contacts": sum(arm.graded_contact_count),
        "debits": sum(arm.match_debits_by_generation),
        "final_host_census": len(arm._hosts()),
        "final_parasite_census": len(pop.units),
        "parent_income_sum": parent_income,
        "other_income_sum": other_income,
        "parent_n": parent_n,
        "other_n": other_n,
        "red_queen_proved": RED_QUEEN_PROVED,
    }


def _window_counter(rows: list[dict[str, object]], key: str) -> tuple[tuple[str, int], ...]:
    return tuple(sorted(Counter(str(row[key]) for row in rows).items()))


def assay_separates_populations(sample: dict[str, object]) -> dict[str, object]:
    """Same hosts, two parasite populations, replayed with evolution off."""

    hosts = list(sample["hosts"])  # type: ignore[arg-type]
    # Guarantee a difference that does not depend on the evolved mix:
    # all-matching 000000 versus the partial-match window used by the instrument.
    left = []
    right = []
    for index in range(len(hosts)):
        left.append(
            {
                "unit_id": f"sep-l-{index}",
                "window": "000000",
                "energy": 1.0,
                "parent_id": None,
                "born_generation": 0,
            }
        )
        right.append(
            {
                "unit_id": f"sep-r-{index}",
                "window": "111000",
                "energy": 1.0,
                "parent_id": None,
                "born_generation": 0,
            }
        )
    # Give every host the locked birth reserve so residual starvation cannot
    # hide a genotypic difference. The windows themselves are copies.
    hosts_ref = []
    for row in hosts:
        copied = dict(row)
        copied["runtime_atp"] = float(STRUCT_BIRTH_ATP)
        hosts_ref.append(copied)
    token = json.dumps(sample, sort_keys=True, separators=(",", ":"))
    score_left = replay_archived_contact(hosts_ref, left)
    score_right = replay_archived_contact(hosts_ref, right)
    separated = float(score_left["total_debit"]) != float(score_right["total_debit"])
    mutated = json.dumps(sample, sort_keys=True, separators=(",", ":")) != token
    return {
        "separated": separated and not mutated,
        "debit_all_000000": score_left["total_debit"],
        "debit_all_111000": score_right["total_debit"],
        "archive_mutated": mutated,
        "red_queen_proved": RED_QUEEN_PROVED,
    }


def _dir_size(path: Path) -> int:
    total = 0
    if not path.exists():
        return 0
    for item in path.rglob("*"):
        if item.is_file():
            total += item.stat().st_size
    return total


def run_phase1(root: Path | None = None) -> dict[str, object]:
    """Instrument, arm smoke, then the 4-seed x 200-generation pilot.

    Stops before the pilot if the instrument is not valid. Stops the pilot
    on the first accounting failure and does not continue that run.
    """

    out = Path(root) if root is not None else Path(__file__).resolve().parents[3] / "runs" / "rq-bidirectional-timeshift-01"
    if out.exists() and any(out.iterdir()):
        raise ConfigurationError(f"refusing to append to a non-empty run directory: {out}")
    out.mkdir(parents=True, exist_ok=True)
    _assert_phase1_seeds(PHASE1_PILOT_SEEDS)
    _assert_phase1_seeds((SMOKE_SEED,))
    live = LiveLog(out)
    started = time.perf_counter()
    design = locked_design_dict()
    live.line(
        f"experiment={EXPERIMENT_ID} phase={PHASE} event=start "
        f"seeds={','.join(str(s) for s in PHASE1_PILOT_SEEDS)} "
        f"generations={PHASE1_GENERATIONS} ecology=population red_queen_proved=false"
    )
    instrument = instrument_two_pair_debit()
    (out / "instrument.json").write_text(
        json.dumps(instrument, sort_keys=True, indent=2) + "\n", encoding="utf-8"
    )
    live.line(
        "event=instrument "
        f"valid={instrument['valid']} "
        f"debit_high={instrument['pair_high']['total_debit']} "
        f"debit_low={instrument['pair_low']['total_debit']} "
        f"affinity_high={instrument['pair_high']['affinity']} "
        f"affinity_low={instrument['pair_low']['affinity']}"
    )
    if not instrument["valid"]:
        live.line("event=stop reason=instrument-invalid confirmatory=not-started")
        live.close()
        return {"instrument": instrument, "pilot": None, "red_queen_proved": False}

    smoke: dict[str, object] = {}
    smoke_ok = True
    for arm_name in ARMS:
        arm = build_arm(arm_name, SMOKE_SEED)
        summary = run_logged_generations(
            arm,
            seed=SMOKE_SEED,
            arm_name=f"{arm_name}-smoke",
            generations=SMOKE_GENERATIONS,
            live=live,
            snapshot_dir=None,
            snapshot_stride=None,
        )
        smoke[arm_name] = summary
        if summary["failed"]:
            smoke_ok = False
            break
        if int(summary["contacts"]) <= 0 or int(summary["final_host_census"]) <= 0:
            summary["failed"] = "smoke-population-or-contact"
            smoke_ok = False
            break
        if arm_name == ARM_C:
            if not summary["frozen_windows_held"] or int(summary["host_births"]) != 0:
                summary["failed"] = "arm-c-did-not-freeze-inheritance"
                smoke_ok = False
                break
            if int(summary["debits"]) <= 0 or int(summary["parasite_births_with_parents"]) <= 0:
                summary["failed"] = "arm-c-lost-cost-or-parasite-reproduction"
                smoke_ok = False
                break
        if arm_name in {ARM_B, ARM_D}:
            if arm.passage != ANTAGONIST_PASSAGE_SHUFFLED_LABELS:
                summary["failed"] = "shuffled-passage-missing"
                smoke_ok = False
                break
    if not smoke_ok:
        live.line("event=stop reason=arm-smoke-failed confirmatory=not-started pilot=not-started")
        live.close()
        report = {
            "instrument": instrument,
            "smoke": smoke,
            "pilot": None,
            "red_queen_proved": False,
        }
        (out / "pilot_summary.json").write_text(
            json.dumps(report, sort_keys=True, indent=2) + "\n", encoding="utf-8"
        )
        return report

    snap_dir = out / "snapshots"
    pilot_rows: list[dict[str, object]] = []
    pilot_failed = False
    for seed in PHASE1_PILOT_SEEDS:
        arm = build_arm(ARM_PILOT, seed)
        t0 = time.perf_counter()
        summary = run_logged_generations(
            arm,
            seed=seed,
            arm_name=ARM_PILOT,
            generations=PHASE1_GENERATIONS,
            live=live,
            snapshot_dir=snap_dir,
            snapshot_stride=SNAPSHOT_STRIDE,
        )
        summary["seed"] = seed
        summary["wall_seconds"] = time.perf_counter() - t0
        pilot_rows.append(summary)
        if summary["failed"] or int(summary["generations_completed"]) != PHASE1_GENERATIONS:
            pilot_failed = True
            live.line(
                f"event=stop seed={seed} reason={summary['failed'] or 'short-run'} "
                "confirmatory=not-started"
            )
            break

    separation = None
    empirical = None
    if not pilot_failed:
        sample_path = snap_dir / f"seed{PHASE1_PILOT_SEEDS[0]}_{ARM_PILOT}_g{SNAPSHOT_STRIDE:04d}.json"
        sample = read_snapshot(sample_path)
        file_hash = hashlib.sha256(sample_path.read_bytes()).hexdigest()
        separation = assay_separates_populations(sample)
        if hashlib.sha256(sample_path.read_bytes()).hexdigest() != file_hash:
            separation["archive_file_mutated"] = True
            separation["separated"] = False
        else:
            separation["archive_file_mutated"] = False
        # Empirical cross of two archived generations, same hosts, if both exist.
        early = sample
        late_path = snap_dir / f"seed{PHASE1_PILOT_SEEDS[0]}_{ARM_PILOT}_g{PHASE1_GENERATIONS:04d}.json"
        late = read_snapshot(late_path)
        early_score = replay_archived_contact(
            list(early["hosts"]),  # type: ignore[arg-type]
            list(early["parasites"]),  # type: ignore[arg-type]
        )
        cross_score = replay_archived_contact(
            list(early["hosts"]),  # type: ignore[arg-type]
            list(late["parasites"]),  # type: ignore[arg-type]
        )
        empirical = {
            "early_generation": SNAPSHOT_STRIDE,
            "late_generation": PHASE1_GENERATIONS,
            "debit_contemporary": early_score["total_debit"],
            "debit_late_parasites_on_early_hosts": cross_score["total_debit"],
            "parasite_windows_differ": _window_counter(list(early["parasites"]), "window")  # type: ignore[arg-type]
            != _window_counter(list(late["parasites"]), "window"),  # type: ignore[arg-type]
            "red_queen_proved": False,
            "note": "descriptive cross only; not a Red Queen verdict",
        }
        if hashlib.sha256(sample_path.read_bytes()).hexdigest() != file_hash:
            empirical["archive_file_mutated"] = True

    parent_n = sum(int(row["parent_n"]) for row in pilot_rows)
    other_n = sum(int(row["other_n"]) for row in pilot_rows)
    parent_sum = sum(float(row["parent_income_sum"]) for row in pilot_rows)
    other_sum = sum(float(row["other_income_sum"]) for row in pilot_rows)
    parent_mean = parent_sum / parent_n if parent_n else None
    other_mean = other_sum / other_n if other_n else None
    income_depends = (
        parent_mean is not None
        and other_mean is not None
        and parent_mean > other_mean
    )
    both_inherit = all(
        int(row["host_births"]) > 0
        and bool(row["host_window_changed"])
        and int(row["parasite_births_with_parents"]) > 0
        and bool(row["parasite_window_changed"])
        for row in pilot_rows
    ) and not pilot_failed and len(pilot_rows) == len(PHASE1_PILOT_SEEDS)
    checks = {
        "both_sides_inherit_and_change": both_inherit,
        "parasite_change_depends_on_contact_income": income_depends,
        "parent_mean_contact_income": parent_mean,
        "other_mean_contact_income": other_mean,
        "energy_ids_parents_checkpoints_valid": (not pilot_failed)
        and all(row["failed"] is None for row in pilot_rows),
        "assay_separates_populations": bool(separation and separation.get("separated")),
        "instrument_valid": bool(instrument["valid"]),
    }
    elapsed = time.perf_counter() - started
    sizes = {
        "live_log_bytes": (out / "live.log").stat().st_size,
        "trajectory_bytes": (out / "trajectory.jsonl").stat().st_size,
        "snapshot_bytes": _dir_size(snap_dir),
        "run_dir_bytes": _dir_size(out),
    }
    code_commit = _git_head(Path(__file__).resolve().parents[3])
    lock = {
        "experiment": EXPERIMENT_ID,
        "phase": PHASE,
        "red_queen_proved": False,
        "biological_red_queen_proved": False,
        "confirmatory_started": False,
        "code_commit": code_commit,
        "antagonist_ecology": ANTAGONIST_ECOLOGY_POPULATION,
        "pilot_seeds": list(PHASE1_PILOT_SEEDS),
        "pilot_seeds_not_for_confirmatory": True,
        "smoke_seed": SMOKE_SEED,
        "generations": PHASE1_GENERATIONS,
        "snapshot_stride": SNAPSHOT_STRIDE,
        "initial_host_n": design["host_n"],
        "initial_parasite_n": design["parasite_n"],
        "locked_design": design,
        "phase1_protocol_overrides": {
            "generations": PHASE1_GENERATIONS,
            "snapshot_stride": SNAPSHOT_STRIDE,
            "antagonist_ecology": ANTAGONIST_ECOLOGY_POPULATION,
            "seeds": list(PHASE1_PILOT_SEEDS),
            "note": "overrides are the phase-1 protocol, not a fit to the outcome",
        },
        "arms": {
            ARM_A: "host inheritance on, parasite population coevolves",
            ARM_B: control_statement(ARM_B),
            ARM_C: control_statement(ARM_C),
            ARM_D: control_statement(ARM_D),
        },
        "instrument": instrument,
        "literature": [
            "Gandon 2002 Ecology Letters 5:246-256 (PDF opened)",
            "Gandon and Michalakis 2002 J Evol Biol (search extract)",
            "Dybdahl and Lively 1998 Evolution 52:1057-1066 (author summary opened via search)",
            "Lively and Dybdahl 2000 Nature 405:679-681 (abstract via search)",
        ],
    }
    summary = {
        "experiment": EXPERIMENT_ID,
        "phase": PHASE,
        "red_queen_proved": False,
        "instrument": instrument,
        "smoke": smoke,
        "pilot": pilot_rows,
        "checks": checks,
        "separation": separation,
        "empirical_cross": empirical,
        "wall_seconds": elapsed,
        "file_sizes": sizes,
        "code_commit": code_commit,
        "confirmatory_started": False,
    }
    (out / "pilot_summary.json").write_text(
        json.dumps(summary, sort_keys=True, indent=2) + "\n", encoding="utf-8"
    )
    (out / "prereg_lock.json").write_text(
        json.dumps(lock, sort_keys=True, indent=2) + "\n", encoding="utf-8"
    )
    live.line(
        f"event=phase1-done wall_seconds={elapsed:.3f} "
        f"checks={json.dumps(checks, sort_keys=True)} confirmatory=not-started "
        "red_queen_proved=false"
    )
    live.close()
    return summary


def _git_head(repo: Path) -> str:
    head = repo / ".git" / "HEAD"
    if not head.is_file():
        return "unknown"
    text = head.read_text(encoding="utf-8").strip()
    if text.startswith("ref:"):
        ref = text.split(" ", 1)[1].strip()
        ref_path = repo / ".git" / ref
        if ref_path.is_file():
            return ref_path.read_text(encoding="utf-8").strip()
    return text


def main() -> None:
    run_phase1()


if __name__ == "__main__":
    main()
