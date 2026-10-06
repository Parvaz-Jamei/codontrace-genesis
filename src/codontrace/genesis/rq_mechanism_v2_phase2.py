"""Phase-2 short mechanism run. Not the 9201-9224 confirmatory.

Arms B and D freeze parasite genotypic inheritance with PASSAGE_FROZEN.
They do not use shuffled_labels. Host freeze stops host reproduction and
bit flips and does not delete the host population. red_queen_proved stays
false. This module does not start a frequency panel, a fitness link, or a
confirmatory.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import time
from collections.abc import Mapping, Sequence
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path
from typing import IO, cast

from codontrace.dynvalues import same_float, same_int
from codontrace.errors import ConfigurationError
from codontrace.genesis.closed_loop_hp_arm01 import ARM_COPASSAGED, _window
from codontrace.genesis.closed_loop_hp_arm01_structural_rq import (
    PILOT_SEEDS,
    StructuralRQArm,
)
from codontrace.genesis.closed_loop_pearl_spc import PASSAGE_COEVOLVE, PASSAGE_FROZEN
from codontrace.genesis.measurements.antagonist_population import (
    ANTAGONIST_PASSAGE_SHUFFLED_LABELS,
)
from codontrace.genesis.rq_bidirectional_timeshift import (
    ARM_A,
    ARM_B,
    ARM_C,
    ARM_D,
    ARMS,
    EXPERIMENT_ID,
    PHASE1_GENERATIONS,
    RQ_CODE_VERSION,
    RQ_DESIGN_VERSION,
    _generation_row,
    _git_head,
    build_phase2_arm,
    config_digest,
    control_statement,
    replay_archived_contact,
)
from codontrace.genesis.rq_stream import ARM_STREAM_POLICY, derive_stream_seed

PHASE2_SEEDS: tuple[int, ...] = (9301, 9302, 9303, 9304)
PHASE2_GENERATIONS = PHASE1_GENERATIONS
PHASE2_FORBIDDEN_SEEDS: frozenset[int] = frozenset(
    {9099, 9101, 9102, 9103, 9104, *range(9201, 9225), 601, 602, 603}
)
PHASE2_ARCHIVE_SCHEMA = "rq-mechanism-v2-phase2/1"
MAX_WORKERS = 4
OUTPUT_DIRNAME = "phase2-short"
REPLAY_ABS_TOL = 1e-6

_ARCHIVE_FIELDS: tuple[str, ...] = (
    "arm",
    "contact_credit",
    "contact_debit",
    "contact_hosts",
    "contact_parasites",
    "contact_tick",
    "contacts",
    "generation",
    "host_births",
    "host_deaths",
    "host_energy",
    "hosts",
    "invariant",
    "parasite_births",
    "parasite_deaths",
    "parasite_energy",
    "parasites",
    "passage",
    "seed",
)


def assert_phase2_seeds(seeds: Sequence[int]) -> None:
    """Refuse every seed the lock names as already used."""

    chosen = tuple(int(seed) for seed in seeds)
    banned = sorted((set(chosen) & PHASE2_FORBIDDEN_SEEDS) | (set(chosen) & set(PILOT_SEEDS)))
    if banned:
        raise ConfigurationError(f"phase-2 seed is forbidden; overlap={banned}")
    if chosen != PHASE2_SEEDS:
        raise ConfigurationError("phase-2 seeds are locked to 9301, 9302, 9303, 9304")


def archive_field_status(record: Mapping[str, object]) -> str:
    """A required archive field that is absent is a bug. It is not imputed."""

    for key in _ARCHIVE_FIELDS:
        if key not in record:
            return f"archive-missing:{key}"
    if not isinstance(record["contacts"], list):
        return "archive-contacts-type"
    if not isinstance(record["host_births"], list) or not isinstance(record["host_deaths"], list):
        return "archive-host-birth-death"
    if not isinstance(record["parasite_births"], list) or not isinstance(record["parasite_deaths"], list):
        return "archive-parasite-birth-death"
    if not isinstance(record["hosts"], list) or not isinstance(record["parasites"], list):
        return "archive-population-type"
    if not isinstance(record["contact_hosts"], list) or not isinstance(record["contact_parasites"], list):
        return "archive-contact-population-type"
    for row in record["hosts"]:
        if not isinstance(row, dict) or "id" not in row or "parent_id" not in row:
            return "archive-host-id-parent"
        if "runtime_atp" not in row:
            return "archive-host-energy"
    for row in record["parasites"]:
        if not isinstance(row, dict) or "unit_id" not in row or "parent_id" not in row:
            return "archive-parasite-id-parent"
        if "energy" not in row:
            return "archive-parasite-energy"
    for row in record["contacts"]:
        if not isinstance(row, dict):
            return "archive-contact-row"
        for key in ("atp", "host_id", "unit_id"):
            if key not in row:
                return f"archive-missing:contact-{key}"
    return "ok"


def founder_identity(arm: StructuralRQArm) -> dict[str, object]:
    """Ids, windows and energy only. Treatment flags are not part of the founder state."""

    hosts = [
        {
            "id": str(org.id),
            "runtime_atp": float(org.atp_state.runtime_available),
            "window": _window(org),
        }
        for org in arm._hosts()
    ]
    hosts.sort(key=lambda row: str(row["id"]))
    pop = arm.antagonist_pop
    if pop is None:
        raise ConfigurationError("phase-2 founder identity requires the parasite population")
    parasites = [
        {"energy": float(unit.energy), "unit_id": unit.unit_id, "window": unit.window}
        for unit in pop.units
    ]
    parasites.sort(key=lambda row: str(row["unit_id"]))
    return {"hosts": hosts, "parasites": parasites}


def scientific_body(arm: StructuralRQArm) -> dict[str, object]:
    """Fields a one-shot run and a resumed run must share. No wall clock."""

    pop = arm.antagonist_pop
    if pop is None:
        raise ConfigurationError("scientific body requires the parasite population")
    hosts = [
        {
            "id": str(org.id),
            "runtime_atp": round(float(org.atp_state.runtime_available), 9),
            "window": _window(org),
        }
        for org in arm._hosts()
    ]
    parasites = [
        {
            "energy": round(float(unit.energy), 9),
            "parent_id": unit.parent_id,
            "unit_id": unit.unit_id,
            "window": unit.window,
        }
        for unit in pop.units
    ]
    parasites.sort(key=lambda row: str(row["unit_id"]))
    paid = [
        round(float(sum(record[4] for record in records)), 9) for records in arm.contact_pair_records
    ]
    return {
        "contacts": list(arm.graded_contact_count),
        "debits": list(arm.match_debits_by_generation),
        "host_ids": [str(org.id) for org in arm._hosts()],
        "hosts": hosts,
        "incomes": [round(float(account.contact_income), 9) for account in pop.energy_accounts],
        "paid": paid,
        "parasite_births": [[unit.unit_id for unit in ledger.newborns] for ledger in pop.ledgers],
        "parasite_deaths": [list(ledger.deaths) for ledger in pop.ledgers],
        "parasite_windows": list(pop.windows()),
        "parasites": parasites,
        "tick_index": int(arm.tick_index),
    }


def _first_diff(left: object, right: object, prefix: str = "") -> str | None:
    if type(left) is not type(right):
        return prefix or "type"
    if isinstance(left, dict) and isinstance(right, dict):
        for key in sorted(set(left) | set(right)):
            if key not in left or key not in right:
                return f"{prefix}.{key}" if prefix else str(key)
            found = _first_diff(left[key], right[key], f"{prefix}.{key}" if prefix else str(key))
            if found:
                return found
        return None
    if isinstance(left, list) and isinstance(right, list):
        if len(left) != len(right):
            return f"{prefix}.len" if prefix else "len"
        for index, (item, other) in enumerate(zip(left, right, strict=True)):
            found = _first_diff(item, other, f"{prefix}[{index}]")
            if found:
                return found
        return None
    if left != right:
        return prefix or "value"
    return None


class _Append:
    def __init__(self, path: Path) -> None:
        self._has_flock: bool = False
        try:
            import fcntl

            self._flock = fcntl.flock
            self._lock_ex = fcntl.LOCK_EX
            self._lock_un = fcntl.LOCK_UN
            self._has_flock = True
        except ImportError:
            pass

        path.parent.mkdir(parents=True, exist_ok=True)
        self._fh = path.open("a", encoding="utf-8", buffering=1)

    def line(self, text: str) -> None:
        payload = text if text.endswith("\n") else text + "\n"
        if self._has_flock:
            self._flock(self._fh.fileno(), self._lock_ex)
        try:
            self._fh.write(payload)
            self._fh.flush()
            os.fsync(self._fh.fileno())
        finally:
            if self._has_flock:
                self._flock(self._fh.fileno(), self._lock_un)

    def close(self) -> None:
        self._fh.flush()
        os.fsync(self._fh.fileno())
        self._fh.close()


def _contact_snapshot(arm: StructuralRQArm) -> dict[str, object]:
    parents = {rec.organism_id: rec.parent_id for rec in arm.runner.population.lineage}
    hosts = [
        {
            "id": str(org.id),
            "parent_id": parents.get(org.id),
            "runtime_atp": float(org.atp_state.runtime_available),
            "window": _window(org),
        }
        for org in arm._hosts()
    ]
    pop = arm.antagonist_pop
    if pop is None:
        raise ConfigurationError("contact snapshot requires the parasite population")
    parasites = [
        {
            "born_generation": int(unit.born_generation),
            "energy": float(unit.energy),
            "parent_id": unit.parent_id,
            "unit_id": unit.unit_id,
            "window": unit.window,
        }
        for unit in pop.units
    ]
    return {"hosts": hosts, "parasites": parasites, "tick": int(arm.tick_index)}


def _install_contact_tap(arm: StructuralRQArm) -> list[dict[str, object]]:
    snaps: list[dict[str, object]] = []
    original = arm._apply_hp_env_contact

    def wrapped() -> tuple[int, list[str]]:
        snaps.append(_contact_snapshot(arm))
        return original()

    arm._apply_hp_env_contact = wrapped  # type: ignore[method-assign]
    return snaps


def _end_population(arm: StructuralRQArm) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    parents = {rec.organism_id: rec.parent_id for rec in arm.runner.population.lineage}
    hosts = [
        {
            "id": str(org.id),
            "parent_id": parents.get(org.id),
            "runtime_atp": float(org.atp_state.runtime_available),
            "window": _window(org),
        }
        for org in arm._hosts()
    ]
    hosts.sort(key=lambda row: str(row["id"]))
    pop = arm.antagonist_pop
    if pop is None:
        raise ConfigurationError("end population requires the parasite population")
    parasites = [
        {
            "born_generation": int(unit.born_generation),
            "energy": float(unit.energy),
            "parent_id": unit.parent_id,
            "unit_id": unit.unit_id,
            "window": unit.window,
        }
        for unit in pop.units
    ]
    parasites.sort(key=lambda row: str(row["unit_id"]))
    return cast(
        tuple[list[dict[str, object]], list[dict[str, object]]],
        (hosts, parasites),
    )


def _write_json(path: Path, body: Mapping[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(body, sort_keys=True, indent=2) + "\n"
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(payload, encoding="utf-8")
    os.replace(temporary, path)


def _run_logged_arm(
    arm: StructuralRQArm,
    *,
    seed: int,
    arm_name: str,
    generations: int,
    archive: IO[str],
    live: _Append,
    dataset: _Append,
    stop: Path,
) -> dict[str, object]:
    snaps = _install_contact_tap(arm)
    founder_ids = {org.id for org in arm._hosts()}
    prev_census = len(founder_ids)
    prev_lineage = 0
    failed: str | None = None
    completed = 0
    for generation in range(1, int(generations) + 1):
        if stop.exists():
            failed = "stopped"
            break
        before_hosts = [str(org.id) for org in arm._hosts()]
        before_lineage = {rec.organism_id for rec in arm.runner.population.lineage}
        try:
            arm.run_generations(1)
        except Exception as exc:
            failed = f"exception:{type(exc).__name__}:{exc}"[:500]
            live.line(
                f"phase=2 seed={seed} arm={arm_name} generation={generation} "
                f"invariant={failed} red_queen_proved=false"
            )
            break
        if len(snaps) != generation:
            failed = "contact-snapshot-missing"
            break
        row = _generation_row(
            arm,
            seed=seed,
            arm_name=arm_name,
            generation=generation,
            founder_ids=founder_ids,
            prev_host_census=prev_census,
            prev_lineage=prev_lineage,
        )
        new_lineage = [
            rec
            for rec in arm.runner.population.lineage
            if rec.organism_id not in before_lineage and rec.parent_id and int(rec.generation) != 0
        ]
        pop = arm.antagonist_pop
        if pop is None:
            failed = "missing-population"
            break
        ledger = pop.ledgers[-1]
        account = pop.energy_accounts[-1]
        contact = snaps[-1]
        events = arm.antagonist_contact_events[-1] if arm.antagonist_contact_events else ()
        after_hosts = {str(org.id) for org in arm._hosts()}
        birth_ids = {rec.organism_id for rec in new_lineage}
        deaths = sorted((set(before_hosts) - after_hosts) | (birth_ids - after_hosts))
        hosts, parasites = _end_population(arm)
        paid = float(sum(float(event.atp_paid) for event in events))
        record: dict[str, object] = {
            "arm": arm_name,
            "code_version": RQ_CODE_VERSION,
            "config_digest": config_digest(),
            "contact_credit": float(account.contact_income),
            "contact_debit": paid,
            "contact_hosts": contact["hosts"],
            "contact_parasites": contact["parasites"],
            "contact_tick": same_int(contact["tick"]),
            "contacts": [
                {
                    "atp": float(event.atp_paid),
                    "host_id": str(event.host_id),
                    "unit_id": str(event.unit_id),
                    "window": str(event.window),
                }
                for event in events
            ],
            "design_version": RQ_DESIGN_VERSION,
            "experiment": EXPERIMENT_ID,
            "generation": int(generation),
            "history_id": str(seed),
            "host_births": [
                {"generation": int(rec.generation), "id": rec.organism_id, "parent_id": rec.parent_id}
                for rec in new_lineage
            ],
            "host_deaths": deaths,
            "host_energy": same_float(row["host_energy"]),
            "host_inheritance": arm.host_inheritance,
            "hosts": hosts,
            "invariant": row["invariant"],
            "parasite_births": [
                {
                    "energy": float(unit.energy),
                    "parent_id": unit.parent_id,
                    "unit_id": unit.unit_id,
                    "window": unit.window,
                }
                for unit in ledger.newborns
            ],
            "parasite_deaths": [str(unit_id) for unit_id in ledger.deaths],
            "parasite_energy": same_float(row["parasite_energy"]),
            "parasites": parasites,
            "passage": arm.passage,
            "phase": 2,
            "red_queen_proved": False,
            "schema": PHASE2_ARCHIVE_SCHEMA,
            "seed": int(seed),
        }
        field_status = archive_field_status(record)
        if field_status != "ok":
            record["invariant"] = field_status
            failed = field_status
        elif row["invariant"] != "ok":
            failed = str(row["invariant"])
        archive.write(json.dumps(record, sort_keys=True, separators=(",", ":")) + "\n")
        archive.flush()
        if generation % 20 == 0:
            os.fsync(archive.fileno())
        public = {
            "arm": arm_name,
            "contacts": row["contacts"],
            "generation": int(generation),
            "host_births": row["host_births"],
            "host_census": row["host_census"],
            "host_deaths": row["host_deaths"],
            "host_energy": row["host_energy"],
            "invariant": record["invariant"],
            "parasite_births": row["parasite_births"],
            "parasite_census": row["parasite_census"],
            "parasite_deaths": row["parasite_deaths"],
            "parasite_energy": row["parasite_energy"],
            "passage": arm.passage,
            "red_queen_proved": False,
            "seed": int(seed),
        }
        dataset.line(json.dumps(public, sort_keys=True, separators=(",", ":")))
        live.line(
            f"phase=2 seed={seed} arm={arm_name} generation={generation} "
            f"host_census={row['host_census']} parasite_census={row['parasite_census']} "
            f"contacts={row['contacts']} invariant={record['invariant']} red_queen_proved=false"
        )
        completed = generation
        prev_census = same_int(row["host_census"])
        prev_lineage += same_int(row["host_births"])
        if failed:
            break
    return {
        "failed": failed,
        "generations_completed": completed,
        "red_queen_proved": False,
    }


def _compare_one_shot(arm: StructuralRQArm, *, seed: int, arm_name: str, generations: int) -> str | None:
    one_shot = build_phase2_arm(arm_name, seed)
    one_shot.run_generations(int(generations))
    left = scientific_body(arm)
    right = scientific_body(one_shot)
    if left == right:
        return None
    diff = _first_diff(left, right) or "scientific-body"
    return f"one-shot-resume-mismatch:{arm_name}:{diff}"


def run_phase2_history(seed: int, root_text: str, generations: int) -> dict[str, object]:
    """Four arms, one seed. Stops on an invariant bug or a resume mismatch.

    The archived path is ``run_generations(1)`` repeated. The one-shot path is
    one ``run_generations(generations)`` call on a second arm. They must match.
    A partial archive is kept. The seed is not replaced.
    """

    if int(generations) != PHASE2_GENERATIONS:
        raise ConfigurationError("phase-2 horizon is locked at 200")
    if int(seed) not in PHASE2_SEEDS:
        raise ConfigurationError(f"phase-2 history seed {seed} is not locked")
    root = Path(root_text)
    stop = root / "STOP"
    seed_dir = root / "by_seed" / f"seed{seed}"
    seed_dir.mkdir(parents=True, exist_ok=True)
    arms = {name: build_phase2_arm(name, seed) for name in ARMS}
    identities = {name: founder_identity(arms[name]) for name in ARMS}
    encoded = {
        name: json.dumps(identities[name], sort_keys=True, separators=(",", ":")) for name in ARMS
    }
    if len(set(encoded.values())) != 1:
        _write_json(
            seed_dir / "FAIL.json",
            {"failed": "initial-state-diverged", "red_queen_proved": False, "seed": int(seed)},
        )
        return {"failed": "initial-state-diverged", "red_queen_proved": False, "seed": int(seed)}
    for name, arm in arms.items():
        if arm.passage == ANTAGONIST_PASSAGE_SHUFFLED_LABELS:
            return {"failed": "shuffled-labels-used", "red_queen_proved": False, "seed": int(seed)}
        if name in {ARM_B, ARM_D} and arm.passage != PASSAGE_FROZEN:
            return {"failed": "parasite-freeze-missing", "red_queen_proved": False, "seed": int(seed)}
        if name in {ARM_A, ARM_C} and arm.passage != PASSAGE_COEVOLVE:
            return {"failed": "parasite-coevolve-missing", "red_queen_proved": False, "seed": int(seed)}
        if arm.arm != ARM_COPASSAGED:
            return {"failed": "rng-namespace-diverged", "red_queen_proved": False, "seed": int(seed)}
        if not arm._hosts() or arm.antagonist_pop is None or not arm.antagonist_pop.units:
            return {"failed": "population-deleted", "red_queen_proved": False, "seed": int(seed)}
    direct = StructuralRQArm.boot_structural(
        arm=ARM_COPASSAGED,
        seed=int(seed),
        antagonist_ecology=arms[ARM_A].antagonist_ecology,
    )
    if founder_identity(direct) != identities[ARM_A]:
        _write_json(
            seed_dir / "FAIL.json",
            {"failed": "boot-founder-mismatch", "red_queen_proved": False, "seed": int(seed)},
        )
        return {"failed": "boot-founder-mismatch", "red_queen_proved": False, "seed": int(seed)}
    initial = {
        "arms": {
            name: {
                "host_inheritance": arms[name].host_inheritance,
                "passage": arms[name].passage,
                "statement": control_statement(name, phase=2),
            }
            for name in ARMS
        },
        "code_version": RQ_CODE_VERSION,
        "config_digest": config_digest(),
        "design_version": RQ_DESIGN_VERSION,
        "experiment": EXPERIMENT_ID,
        "founder": identities[ARM_A],
        "generations": int(generations),
        "history_id": str(seed),
        "red_queen_proved": False,
        "rng": {
            "arm_name_in_hash": False,
            "history_id": str(seed),
            "host_step_g1": derive_stream_seed(EXPERIMENT_ID, str(seed), "host-step", 1),
            "passage_g1": derive_stream_seed(EXPERIMENT_ID, str(seed), "passage", 1),
            "root": EXPERIMENT_ID,
            "sharing_policy": dict(ARM_STREAM_POLICY),
            "subsystems": ["host-step", "passage"],
        },
        "schema": PHASE2_ARCHIVE_SCHEMA,
        "seed": int(seed),
    }
    _write_json(seed_dir / "initial.json", initial)
    live = _Append(root / "live.log")
    dataset = _Append(root / "trajectory.jsonl")
    archive_path = seed_dir / "archive.jsonl"
    summaries: dict[str, object] = {}
    failed: str | None = None
    try:
        with archive_path.open("w", encoding="utf-8", buffering=1) as archive:
            for arm_name in ARMS:
                if stop.exists():
                    failed = "stopped"
                    summaries[arm_name] = {"failed": "stopped", "generations_completed": 0}
                    break
                outcome = _run_logged_arm(
                    arms[arm_name],
                    seed=int(seed),
                    arm_name=arm_name,
                    generations=int(generations),
                    archive=archive,
                    live=live,
                    dataset=dataset,
                    stop=stop,
                )
                summaries[arm_name] = outcome
                if outcome["failed"]:
                    failed = str(outcome["failed"])
                    break
                mismatch = _compare_one_shot(
                    arms[arm_name],
                    seed=int(seed),
                    arm_name=arm_name,
                    generations=int(generations),
                )
                if mismatch:
                    failed = mismatch
                    _write_json(
                        seed_dir / "mismatch.json",
                        {
                            "arm": arm_name,
                            "failed": mismatch,
                            "red_queen_proved": False,
                            "seed": int(seed),
                        },
                    )
                    live.line(
                        f"phase=2 seed={seed} arm={arm_name} invariant={mismatch} "
                        "red_queen_proved=false"
                    )
                    break
    finally:
        live.close()
        dataset.close()
    if failed:
        _write_json(
            seed_dir / "FAIL.json",
            {
                "arms": summaries,
                "failed": failed,
                "red_queen_proved": False,
                "seed": int(seed),
            },
        )
        stop.write_text(f"seed={seed} failed={failed}\n", encoding="utf-8")
    else:
        (seed_dir / "COMPLETE").write_text("generations=200 red_queen_proved=false\n", encoding="utf-8")
    return {
        "arms": summaries,
        "failed": failed,
        "red_queen_proved": False,
        "seed": int(seed),
    }


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def compare_history_archives(left: Path, right: Path) -> dict[str, object]:
    """Byte compare of the scientific archives. Live logs are not scientific output."""

    mismatches: list[str] = []
    hashes: dict[str, dict[str, str]] = {}
    for seed in PHASE2_SEEDS:
        for name in ("archive.jsonl", "initial.json"):
            left_path = left / "by_seed" / f"seed{seed}" / name
            right_path = right / "by_seed" / f"seed{seed}" / name
            if not left_path.is_file() or not right_path.is_file():
                mismatches.append(f"missing:{seed}:{name}")
                continue
            left_hash = _sha256(left_path)
            right_hash = _sha256(right_path)
            hashes[f"seed{seed}/{name}"] = {"workers_1": left_hash, "workers_4": right_hash}
            if left_path.read_bytes() != right_path.read_bytes():
                mismatches.append(f"bytes:{seed}:{name}")
    return {
        "compared": "archive.jsonl and initial.json bytes",
        "hashes": hashes,
        "matched": not mismatches,
        "mismatches": mismatches,
        "red_queen_proved": False,
    }


def replay_phase2_archive(path: Path) -> dict[str, object]:
    """Re-score archived contact-time populations with evolution off.

    Comparison is named engine fields from ``replay_archived_contact``
    (total_debit, credit, evolution, reproduction, mutation), not a second
    formula and not a byte copy of the archive. An empty side is unmeasurable
    and stays missing. It is not written as zero.
    """

    mismatches: list[dict[str, object]] = []
    compared = 0
    unmeasurable = 0
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        row = json.loads(line)
        hosts = row.get("contact_hosts")
        parasites = row.get("contact_parasites")
        if not isinstance(hosts, list) or not isinstance(parasites, list):
            mismatches.append({"generation": row.get("generation"), "reason": "contact-population-missing"})
            continue
        recorded_contacts = row.get("contacts")
        if not isinstance(recorded_contacts, list):
            mismatches.append({"generation": row.get("generation"), "reason": "contacts-missing"})
            continue
        if not hosts or not parasites:
            unmeasurable += 1
            if recorded_contacts:
                mismatches.append(
                    {
                        "arm": row.get("arm"),
                        "generation": row.get("generation"),
                        "reason": "empty-population-had-contacts",
                    }
                )
            elif row.get("contact_debit") not in (0, 0.0):
                mismatches.append(
                    {
                        "arm": row.get("arm"),
                        "generation": row.get("generation"),
                        "reason": "empty-population-nonzero-debit",
                    }
                )
            continue
        host_copy = json.loads(json.dumps(hosts))
        parasite_copy = json.loads(json.dumps(parasites))
        scored = replay_archived_contact(
            host_copy,
            parasite_copy,
            tick_index=int(row["contact_tick"]),
            seed=0,
        )
        compared += 1
        debit_gap = abs(same_float(scored["total_debit"]) - same_float(row["contact_debit"]))
        credit_gap = abs(same_float(scored["credit"]) - same_float(row["contact_credit"]))
        recorded_paid = float(sum(float(item["atp"]) for item in recorded_contacts))
        paid_gap = abs(same_float(scored["total_debit"]) - recorded_paid)
        flags_off = (
            scored["evolution"] is False
            and scored["reproduction"] is False
            and scored["mutation"] is False
        )
        if debit_gap > REPLAY_ABS_TOL or credit_gap > REPLAY_ABS_TOL or paid_gap > REPLAY_ABS_TOL or not flags_off:
            mismatches.append(
                {
                    "arm": row.get("arm"),
                    "credit_gap": credit_gap,
                    "debit_gap": debit_gap,
                    "generation": row.get("generation"),
                    "line": line_number,
                    "paid_gap": paid_gap,
                    "reason": "replay-field-mismatch",
                }
            )
            if len(mismatches) >= 5:
                break
    return {
        "compared_generations": compared,
        "comparison": "named fields total_debit, credit, evolution, reproduction, mutation; not archive bytes",
        "matched": not mismatches,
        "mismatches": mismatches,
        "red_queen_proved": False,
        "unmeasurable_generations": unmeasurable,
    }


def _run_pool(root: Path, *, workers: int) -> dict[str, object]:
    if workers < 1 or workers > MAX_WORKERS:
        raise ConfigurationError("CPU workers must be between 1 and 4")
    assert_phase2_seeds(PHASE2_SEEDS)
    root.mkdir(parents=True, exist_ok=True)
    if any(root.iterdir()):
        raise ConfigurationError(f"refusing to append to a non-empty phase-2 directory: {root}")
    started = time.perf_counter()
    outcomes: list[dict[str, object]] = []
    if workers == 1:
        for seed in PHASE2_SEEDS:
            if (root / "STOP").exists():
                break
            try:
                outcomes.append(run_phase2_history(seed, str(root), PHASE2_GENERATIONS))
            except Exception as exc:
                outcomes.append(
                    {"failed": f"exception:{type(exc).__name__}:{exc}"[:500], "red_queen_proved": False, "seed": seed}
                )
                (root / "STOP").write_text(f"seed={seed} exception={exc}\n", encoding="utf-8")
    else:
        with ProcessPoolExecutor(max_workers=workers) as pool:
            futures = {
                pool.submit(run_phase2_history, seed, str(root), PHASE2_GENERATIONS): seed
                for seed in PHASE2_SEEDS
            }
            for future in as_completed(futures):
                seed = futures[future]
                try:
                    outcomes.append(future.result())
                except Exception as exc:
                    outcomes.append(
                        {
                            "failed": f"exception:{type(exc).__name__}:{exc}"[:500],
                            "red_queen_proved": False,
                            "seed": seed,
                        }
                    )
                    (root / "STOP").write_text(f"seed={seed} exception={exc}\n", encoding="utf-8")
    failed = [item for item in outcomes if item.get("failed")]
    return {
        "failed": bool(failed),
        "outcomes": outcomes,
        "red_queen_proved": False,
        "wall_seconds": time.perf_counter() - started,
        "workers": workers,
    }


def execute_phase2_short(root: Path) -> dict[str, object]:
    """Four workers, then one process, then archive replay. Stop on disagreement.

    Does not retune seeds, horizon, lag, thresholds, or maintenance cost.
    """

    root = Path(root)
    if root.exists() and any(root.iterdir()):
        raise ConfigurationError(f"refusing to append to a non-empty phase-2 directory: {root}")
    root.mkdir(parents=True, exist_ok=True)
    parallel_root = root / "workers4"
    serial_root = root / "workers1"
    parallel = _run_pool(parallel_root, workers=4)
    summary: dict[str, object] = {
        "experiment": EXPERIMENT_ID,
        "frequency_panel": False,
        "fitness_link": False,
        "generations": PHASE2_GENERATIONS,
        "not_run": ["frequency panel", "fitness link", "confirmatory", "Red Queen claim"],
        "phase": 2,
        "red_queen_proved": False,
        "seeds": list(PHASE2_SEEDS),
        "workers4": {
            "failed": parallel["failed"],
            "wall_seconds": parallel["wall_seconds"],
        },
    }
    if parallel["failed"]:
        summary["stopped"] = "invariant-or-resume"
        summary["outcomes"] = parallel["outcomes"]
        _write_json(root / "summary.json", summary)
        return summary
    serial = _run_pool(serial_root, workers=1)
    summary["workers1"] = {"failed": serial["failed"], "wall_seconds": serial["wall_seconds"]}
    if serial["failed"]:
        summary["stopped"] = "serial-invariant-or-resume"
        summary["outcomes"] = serial["outcomes"]
        _write_json(root / "summary.json", summary)
        return summary
    worker_compare = compare_history_archives(serial_root, parallel_root)
    summary["worker_compare"] = worker_compare
    if not worker_compare["matched"]:
        summary["stopped"] = "one-process-vs-four-workers"
        _write_json(root / "summary.json", summary)
        return summary
    replays = []
    for seed in PHASE2_SEEDS:
        replays.append(
            {
                "replay": replay_phase2_archive(parallel_root / "by_seed" / f"seed{seed}" / "archive.jsonl"),
                "seed": seed,
            }
        )
    summary["replay"] = replays
    summary["replay_matched"] = all(bool(item["replay"]["matched"]) for item in replays)  # type: ignore[index]
    if not summary["replay_matched"]:
        summary["stopped"] = "replay-mismatch"
        _write_json(root / "summary.json", summary)
        return summary
    summary["stopped"] = None
    summary["one_shot_vs_resume"] = "matched on scientific_body inside each history before COMPLETE"
    summary["serial_archives"] = "removed after byte match; hashes remain in worker_compare"
    summary["code_commit"] = _git_head(Path(__file__).resolve().parents[3])
    _write_json(root / "summary.json", summary)
    shutil.rmtree(serial_root)
    return summary
