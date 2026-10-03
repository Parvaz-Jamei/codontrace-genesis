"""Phase-4 fitness link. Not a Red Queen claim.

Prediction. A parasite conditioned while host A was common reduces A's
relative advantage against the parasite conditioned while host B was common,
and the converse. The contrast is who is alive at the horizon, classed by
lineage parent ids. An ATP drop is not that score.

Engine path. Each branch boots ``build_arm(ARM_A)``, installs equal counts of
the locked genomes, and steps ``StructuralRQArm.run_generations``. Contact is
``_apply_hp_env_contact``. Parasite update is ``AntagonistPopulation.advance``.
Host births are ``PopulationRunner.step_generation`` with reproduction left
enabled. Recognition mutation is off: host ``bit_flip_rate`` is 0 and the
parasite ``mutation_rate`` is 0. The adapted branches stay on passage
``coevolve`` so the frozen reseat does not replace the conditioned windows.

Control. Passage ``absent`` (``PASSAGE_ABSENT``). ``_apply_hp_env_contact``
returns no contacts and no debit before any host ATP move. Host reproduction
and ``parent_atp_cost`` stay on. This is antagonist removal, not a pure
evolution control, and not ``freeze_host_genotypic_inheritance``.
``shuffled_labels`` is not used and is not a frozen genotype.

Source. The seat, debit, birth, and absent passage are the structural engine.
``runs/rq-mechanism-v2/PHASE1.md`` records Zaman et al. 2014 (PMC4267771) as
the reason a static antagonist is not reciprocal coevolution, and
Decaestecker et al. 2007 as the reason the score itself does not evolve.
Hall et al. 2011 full text was not read. No sentence here is a new quotation.
The replacement time 60/26 and the multiple 3 are the phase-3 record, not a
new probe.

Limit. Importance for this estimand is undeclared, so SUPPORTED is forbidden.
``MEASUREMENT_FLOOR`` stays 12. n = 4 is not support. Generation-1 births
happen before contact, so the estimand is the terminal census, not that first
birth share. Contact removal does not write ``death_tick``; a death is an id
that was alive or born and is absent afterwards. ``red_queen_proved`` stays
false. A fitness link is not Red Queen.

Estimand. ``L_A`` is the founder-class A fraction of hosts alive after the
horizon. ``R = L_A - L_B``. ``F = R(common_a parasite) - R(common_b parasite)``.
The absent branch is reported beside F and is not substituted into F. Empty
or unresolved lineage is null, not zero.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
from collections.abc import Mapping, Sequence
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import replace
from pathlib import Path

from codontrace.errors import ConfigurationError
from codontrace.genesis.birth import SexualRecombinationConfig
from codontrace.genesis.closed_loop_hp_arm01 import _window
from codontrace.genesis.closed_loop_hp_arm01_structural_rq import (
    STRUCT_BIRTH_ATP,
    STRUCT_KEEP_FRACTION,
    StructuralRQArm,
)
from codontrace.genesis.closed_loop_pearl_spc import PASSAGE_ABSENT, PASSAGE_COEVOLVE
from codontrace.genesis.host_parasite_life_plugin import (
    ROLE_PRIMARY,
    ROLE_SECONDARY,
    silence_outcross_locus,
)
from codontrace.genesis.measurements.antagonist_population import (
    AntagonistPopulation,
    AntagonistUnit,
)
from codontrace.genesis.organism import GenesisOrganism
from codontrace.genesis.rq_bidirectional_timeshift import ARM_A, build_arm
from codontrace.genesis.rq_bidirectional_timeshift_confirm import (
    MEASUREMENT_FLOOR,
    VERDICT_BLOCKED,
)
from codontrace.genesis.rq_mechanism_v2_phase3 import (
    horizon_from_turnover,
    host_genome,
)

PHASE4_SEEDS: tuple[int, ...] = (9501, 9502, 9503, 9504)
# Unit tests only. Not a measurement history.
TEST_SEED = 9491
PHASE4_FORBIDDEN_SEEDS: frozenset[int] = frozenset(
    {
        9099,
        9101,
        9102,
        9103,
        9104,
        *range(9201, 9225),
        *range(9301, 9305),
        9401,
        9500,
        601,
        602,
        603,
    }
)
# Already recorded in PHASE3_LOCK.md from the seed-9500 probe. Not remeasured
# and not taken from the sign of F.
RECORDED_REPLACEMENT_CENSUS = 60
RECORDED_MEAN_SEATED_NEWBORNS = 26.0
PHASE4_CENSUS = 60
PHASE4_PER_CLASS = 30
MAX_WORKERS = 7
STREAM_ROOT = "RQ-MECHANISM-V2-PHASE4"
BRANCH_COMMON_A = "common_a"
BRANCH_COMMON_B = "common_b"
BRANCH_ABSENT = "absent"
BRANCHES: tuple[str, ...] = (BRANCH_COMMON_A, BRANCH_COMMON_B, BRANCH_ABSENT)
WINDOW_A = "000000"
WINDOW_B = "111111"
GENOME_A = "101111000100000001000000"
GENOME_B = "101111000100000001111111"
EXEMPLAR_A = "host-A-001"
EXEMPLAR_B = "host-B-001"
ARCHIVE_SCHEMA = "rq-mechanism-v2-phase4/1"
VERDICT_NOT_DECLARED = "NOT_DECLARED"
NO_FITNESS_SENTENCE = "No fitness number has been computed."
IMPORTANCE_RULE = (
    "Importance for this estimand is undeclared. SUPPORTED is forbidden. "
    "The minimum detectable effect is not the importance bound."
)
PHASE3_FREQUENCY_ROOT = Path("runs/rq-mechanism-v2/phase3-frequency")
_BANNED_OUTPUT_PARTS = (
    Path("runs/rq-bidirectional-timeshift-01"),
    Path("runs/rq-mechanism-v2/phase2-short"),
    Path("runs/rq-mechanism-v2/phase3-frequency"),
    Path("runs/rq-mechanism-v2/phase3-selection"),
)


def _horizon_record() -> dict[str, object]:
    """Horizon from the recorded replacement time. Does not read F."""

    record = horizon_from_turnover(
        mean_newborns=RECORDED_MEAN_SEATED_NEWBORNS,
        census=RECORDED_REPLACEMENT_CENSUS,
        measurable=True,
    )
    record["why_not_one"] = (
        "generation-1 host births are inside step_generation, which runs "
        "before contact, so a one-generation horizon cannot be a post-contact census"
    )
    record["chosen_from_fitness_sign"] = False
    return record


_HORIZON = _horizon_record()
PHASE4_HORIZON = int(_HORIZON["conditioning_generations"])
# Death on the no-food maximum-debit account. Not ceil(3 * 60/26).
# The assay bolus stays on. This constant is the lock, not a fitness sign.
PHASE4B_HORIZON = 9
STREAM_ROOT_B = "RQ-MECHANISM-V2-PHASE4B"
ARCHIVE_SCHEMA_B = "rq-mechanism-v2-phase4b/1"
PHASE4B_OUTPUT = Path("runs/rq-mechanism-v2/phase4b-fitness")
_PHASE4_ARCHIVE = Path("runs/rq-mechanism-v2/phase4-fitness")


def assert_phase4_seeds(seeds: Sequence[int]) -> None:
    """Measurement histories are exactly 9501-9504. A shorter list is refused."""

    chosen = tuple(int(seed) for seed in seeds)
    if chosen != PHASE4_SEEDS:
        raise ConfigurationError(
            "phase-4 measurement histories are exactly 9501, 9502, 9503, 9504"
        )
    banned = sorted(set(chosen) & PHASE4_FORBIDDEN_SEEDS)
    if banned:
        raise ConfigurationError(f"phase-4 seed is forbidden; overlap={banned}")


def assert_branch_seed(seed: int) -> None:
    """A branch may be a locked history or the single test seed 9491."""

    chosen = int(seed)
    if chosen in PHASE4_SEEDS:
        return
    if chosen == TEST_SEED:
        return
    raise ConfigurationError(f"phase-4 seed {chosen} is not a locked history or the test seed")


def resolve_workers(requested: int | None) -> int:
    """Cap at 7. Reject 8. Do not read cpu_count."""

    if requested is None:
        requested = MAX_WORKERS
    workers = int(requested)
    if workers < 1 or workers > MAX_WORKERS:
        raise ConfigurationError(
            f"phase-4 workers must be in 1..{MAX_WORKERS}, got {workers}"
        )
    return workers


def assert_output_dir(root: Path, *, forbid_rejected_archive: bool = False) -> None:
    """Refuse the confirmatory tree, phase 2, and the phase-3 archives."""

    resolved = root.resolve()
    banned_parts = list(_BANNED_OUTPUT_PARTS)
    if forbid_rejected_archive:
        banned_parts.append(_PHASE4_ARCHIVE)
    for banned in banned_parts:
        banned_resolved = banned.resolve()
        if resolved == banned_resolved or banned_resolved in resolved.parents:
            raise ConfigurationError(f"phase-4 output must not be inside {banned}")


def locked_genomes() -> dict[str, str]:
    """The phase-3 genomes. Not re-chosen from a fitness sign."""

    built_a = host_genome(WINDOW_A)
    built_b = host_genome(WINDOW_B)
    if built_a != GENOME_A or built_b != GENOME_B:
        raise ConfigurationError("engine tape does not match the locked genomes")
    if not GENOME_A.endswith(WINDOW_A) or not GENOME_B.endswith(WINDOW_B):
        raise ConfigurationError("locked genome does not end in its window")
    if GENOME_A == GENOME_B:
        raise ConfigurationError("locked host genomes must differ")
    return {
        "exemplar_a": EXEMPLAR_A,
        "exemplar_b": EXEMPLAR_B,
        "genome_a": GENOME_A,
        "genome_b": GENOME_B,
        "window_a": WINDOW_A,
        "window_b": WINDOW_B,
    }


def equal_host_seats(census: int = PHASE4_CENSUS) -> list[dict[str, str]]:
    """Equal A and B. Index % 2 == 0 is A. Shared genomes, not class labels."""

    if int(census) != PHASE4_CENSUS or PHASE4_CENSUS != 2 * PHASE4_PER_CLASS:
        raise ConfigurationError("phase-4 census is the locked equal 30/30")
    genomes = locked_genomes()
    seats: list[dict[str, str]] = []
    counts = {"A": 0, "B": 0}
    for index in range(int(census)):
        letter = "A" if index % 2 == 0 else "B"
        counts[letter] += 1
        window = WINDOW_A if letter == "A" else WINDOW_B
        genome = GENOME_A if letter == "A" else GENOME_B
        seats.append(
            {
                "genome": genome,
                "host_id": f"host-{letter}-{counts[letter]:03d}",
                "role_letter": letter,
                "window": window,
            }
        )
    if counts["A"] != PHASE4_PER_CLASS or counts["B"] != PHASE4_PER_CLASS:
        raise ConfigurationError("equal mix did not hit 30 and 30")
    if seats[0]["host_id"] != EXEMPLAR_A or seats[1]["host_id"] != EXEMPLAR_B:
        raise ConfigurationError("exemplar ids are not in the equal mix")
    if seats[0]["genome"] != genomes["genome_a"]:
        raise ConfigurationError("exemplar A genome drifted")
    return seats


def resolve_founder_class(
    unit_id: str,
    parents: Mapping[str, str | None],
    founders: Mapping[str, str],
) -> str | None:
    """Walk parent_id to an installed founder. A cycle or a gap is null."""

    current: str | None = str(unit_id)
    seen: set[str] = set()
    while current is not None:
        if current in seen:
            return None
        seen.add(current)
        if current in founders:
            label = founders[current]
            if label not in {"A", "B"}:
                return None
            return label
        if current not in parents:
            return None
        current = parents[current]
    return None


def lineage_share(
    living_ids: Sequence[str],
    parents: Mapping[str, str | None],
    founders: Mapping[str, str],
) -> dict[str, object]:
    """Founder-class share of the living census. ATP is not an argument.

    Empty census or any unresolved id yields null shares. Null is not zero.
    A measured share of 0 is returned only when the other class is present
    and every living id resolved.
    """

    labels: list[str | None] = []
    unresolved = 0
    for unit_id in living_ids:
        label = resolve_founder_class(str(unit_id), parents, founders)
        labels.append(label)
        if label is None:
            unresolved += 1
    n_living = len(list(living_ids))
    n_a = sum(1 for label in labels if label == "A")
    n_b = sum(1 for label in labels if label == "B")
    if n_living == 0 or unresolved:
        return {
            "n_A": n_a,
            "n_B": n_b,
            "n_living": n_living,
            "n_unresolved": unresolved,
            "share_A": None,
            "share_B": None,
        }
    return {
        "n_A": n_a,
        "n_B": n_b,
        "n_living": n_living,
        "n_unresolved": 0,
        "share_A": n_a / float(n_living),
        "share_B": n_b / float(n_living),
    }


def fitness_from_lineage(
    living_ids: Sequence[str],
    parents: Mapping[str, str | None],
    founders: Mapping[str, str],
    atp_loss: Mapping[str, float] | None = None,
) -> dict[str, object]:
    """Lineage share. ``atp_loss`` is ignored so an ATP drop cannot be the score."""

    del atp_loss
    return lineage_share(living_ids, parents, founders)


def relative_advantage(share_a: float | None, share_b: float | None) -> float | None:
    """``L_A - L_B``. Either null input stays null, not zero."""

    if share_a is None or share_b is None:
        return None
    if not _finite_number(share_a) or not _finite_number(share_b):
        return None
    return float(share_a) - float(share_b)


def fitness_contrast(
    share_a_common_a: float | None,
    share_b_common_a: float | None,
    share_a_common_b: float | None,
    share_b_common_b: float | None,
) -> float | None:
    """``F = R(parasite common A) - R(parasite common B)``.

    The absent-passage advantage is not an argument. Any null stays null.
    """

    left = relative_advantage(share_a_common_a, share_b_common_a)
    right = relative_advantage(share_a_common_b, share_b_common_b)
    if left is None or right is None:
        return None
    return left - right


def contact_without_demography(
    *,
    contacts_a: int,
    contacts_b: int,
    paid_a: float,
    paid_b: float,
    births_a: Mapping[str, int],
    births_b: Mapping[str, int],
    deaths_a: Mapping[str, int],
    deaths_b: Mapping[str, int],
) -> dict[str, bool]:
    """Whether contact moved while birth and death counts did not.

    This is a report, not F, and not a support call.
    """

    contact_changed = int(contacts_a) != int(contacts_b) or abs(float(paid_a) - float(paid_b)) > 1e-9
    reproduction_changed = int(births_a["A"]) != int(births_b["A"]) or int(births_a["B"]) != int(
        births_b["B"]
    )
    survival_changed = int(deaths_a["A"]) != int(deaths_b["A"]) or int(deaths_a["B"]) != int(
        deaths_b["B"]
    )
    return {
        "contact_changed": contact_changed,
        "contact_without_demographic_change": (
            contact_changed and not reproduction_changed and not survival_changed
        ),
        "reproduction_changed": reproduction_changed,
        "survival_changed": survival_changed,
    }


def _finite_number(value: object) -> bool:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return False
    number = float(value)
    return number == number and number not in (float("inf"), float("-inf"))


def _next_serial(unit_ids: Sequence[str]) -> int:
    best = 0
    for unit_id in unit_ids:
        if "-n" not in unit_id:
            continue
        tail = unit_id.rsplit("-n", 1)[-1]
        if tail.isdigit():
            best = max(best, int(tail) + 1)
    return best


def population_from_parasite_rows(rows: Sequence[Mapping[str, object]]) -> AntagonistPopulation:
    """Rebuild the conditioned roster. Mutation rate is 0. Not a frozen reseat."""

    if not rows:
        raise ConfigurationError("conditioned parasite archive has no parasites")
    units: list[AntagonistUnit] = []
    ids: list[str] = []
    parents: set[str] = set()
    windows: list[str] = []
    for row in rows:
        unit_id = str(row["unit_id"])
        raw_parent = row.get("parent_id")
        parent_id = None if raw_parent in (None, "") else str(raw_parent)
        if parent_id is not None:
            parents.add(parent_id)
        window = str(row["window"])
        units.append(
            AntagonistUnit(
                unit_id=unit_id,
                window=window,
                parent_id=parent_id,
                born_generation=int(row["born_generation"]),  # type: ignore[arg-type]
                energy=float(row["energy"]),  # type: ignore[arg-type]
                alive=True,
            )
        )
        ids.append(unit_id)
        windows.append(window)
    known = set(ids) | parents
    return AntagonistPopulation(
        units=units,
        seat_cap=len(units),
        ancestral_windows=sorted(set(windows)),
        keep_fraction=float(STRUCT_KEEP_FRACTION),
        mutation_rate=0.0,
        known_unit_ids=known,
        child_serial=_next_serial(sorted(known)),
    )


def install_equal_hosts(arm: StructuralRQArm, seats: Sequence[Mapping[str, str]]) -> None:
    """Put equal A and B on the shared patches. Does not install a hold."""

    if len(seats) != PHASE4_CENSUS:
        raise ConfigurationError("equal host mix is not the locked census")
    patches = list(arm.food_patches)
    if not patches:
        raise ConfigurationError("equal hosts require the shared food patches")
    organisms: list[GenesisOrganism] = []
    roles: dict[str, str] = {"parasite_stock": ROLE_SECONDARY}
    seen: set[str] = set()
    for index, seat in enumerate(seats):
        host_id = str(seat["host_id"])
        if host_id in seen:
            raise ConfigurationError(f"duplicate host id {host_id}")
        seen.add(host_id)
        genome = str(seat["genome"])
        organism = GenesisOrganism.from_bits(
            host_id,
            genome,
            initial_runtime_atp=float(STRUCT_BIRTH_ATP),
            position=patches[index % len(patches)],
        )
        if _window(organism) != str(seat["window"]):
            raise ConfigurationError("installed genome does not decode to its window")
        silence_outcross_locus(organism, arm.runner.configs.closed_loop_hp_life)
        organisms.append(organism)
        roles[host_id] = ROLE_PRIMARY
    arm.runner.population = replace(arm.runner.population, organisms=tuple(organisms))
    arm.roles = roles
    arm.host_composition_hold = None


def _clone_parasites(pop: AntagonistPopulation) -> AntagonistPopulation:
    units = [replace(unit) for unit in pop.units]
    return AntagonistPopulation(
        units=units,
        seat_cap=int(pop.seat_cap),
        ancestral_windows=list(pop.ancestral_windows),
        keep_fraction=float(pop.keep_fraction),
        mutation_rate=0.0,
        fecundity=float(pop.fecundity),
        maintenance_cost=float(pop.maintenance_cost),
        known_unit_ids=set(pop.known_unit_ids),
        child_serial=int(pop.child_serial),
    )


def build_phase4_arm(
    seed: int,
    branch: str,
    seats: Sequence[Mapping[str, str]],
    parasites: AntagonistPopulation,
    *,
    stream_root: str = STREAM_ROOT,
) -> StructuralRQArm:
    """One fitness branch. Host reproduction stays on. Recognition mutation is off."""

    assert_branch_seed(int(seed))
    key = str(branch)
    if key not in BRANCHES:
        raise ConfigurationError(f"unknown phase-4 branch {branch!r}")
    arm = build_arm(ARM_A, int(seed))
    arm.stream_root = str(stream_root)
    arm.stream_history = str(int(seed))
    arm.host_composition_hold = None
    configs = arm.runner.configs
    if not configs.reproduction.enabled:
        raise ConfigurationError("host reproduction was off at boot")
    if float(configs.reproduction.parent_atp_cost) <= 0.0:
        raise ConfigurationError("host reproduction cost was off at boot")
    arm.runner.configs = replace(
        configs,
        mutation=replace(configs.mutation, bit_flip_rate=0.0),
    )
    if arm.runner.configs.reproduction.enabled is not True:
        raise ConfigurationError("setting bit_flip_rate turned reproduction off")
    if float(arm.runner.configs.reproduction.parent_atp_cost) <= 0.0:
        raise ConfigurationError("host reproduction cost must stay on")
    if float(arm.runner.configs.mutation.bit_flip_rate) != 0.0:
        raise ConfigurationError("host recognition mutation is not off")
    if key == BRANCH_ABSENT:
        # Existing zero-contact path. Host step_generation still runs first.
        arm.passage = PASSAGE_ABSENT
    else:
        # coevolve with mutation_rate 0 keeps the conditioned windows.
        # frozen would reseat founder windows and destroy the conditioning.
        arm.passage = PASSAGE_COEVOLVE
    if arm.passage in {"shuffled_labels", "frozen"}:
        raise ConfigurationError("phase-4 passage must not be shuffled_labels or frozen")
    if arm.host_inheritance != "transmit":
        raise ConfigurationError("host inheritance must stay on")
    pop = _clone_parasites(parasites)
    if float(pop.mutation_rate) != 0.0:
        raise ConfigurationError("parasite recognition mutation is not off")
    arm.antagonist_pop = pop
    arm.parasite_windows = pop.windows()
    install_equal_hosts(arm, seats)
    enable_outcross_birth_chamber(arm)
    return arm


def enable_outcross_birth_chamber(arm: StructuralRQArm) -> None:
    """Admit a child on the engine path the outcross locus already requires.

    Prediction. ``reproduction.enabled`` does not build a child. The locked
    tape has a nonzero outcross locus, so ``resolve_copy_self_mode`` returns
    ``chamber``. Structural boot sets ``SexualRecombinationConfig(enabled=False)``,
    so ``uses_birth_chamber`` is false. ``COPY_SELF`` is refused with
    ``outcross_chamber_required`` and no organism id is added.

    Engine path. The life-loop chamber is turned back on:
    ``enabled=True`` and ``pairing_policy='birth_chamber'``. ``COPY_SELF``
    then enters ``_handle_chamber_copy_self``. Installed host ids are written
    into ``closed_loop_hp_life.role_by_id`` so ``outcross_same_role_only`` can
    pair them. ``parent_atp_cost`` and ``bit_flip_rate`` are not arguments of
    this call.

    Control. Leaving sexual recombination disabled on the same organisms
    still refuses. That is the test, not a second measurement.

    Source. The chamber is ``SexualRecombinationConfig.uses_birth_chamber``
    and ``copy_self_chamber_refusal`` in the existing motor. No new paper
    quotation. Hall et al. 2011 full text was not read.

    Limit. Virulence, steal fraction, maintenance, birth ATP, bolus,
    ``max_population``, mutation rate, and ``MEASUREMENT_FLOOR`` stay as
    booted. This does not aim F at a nonzero sign.

    Estimand. A child id can enter the living census that ``L_A`` and ``L_B``
    read. ATP loss is still not the score.
    """

    configs = arm.runner.configs
    parent_cost = float(configs.reproduction.parent_atp_cost)
    bit_flip = float(configs.mutation.bit_flip_rate)
    if not configs.reproduction.enabled or parent_cost <= 0.0:
        raise ConfigurationError("birth acceptance must keep the reproduction cost")
    if bit_flip != 0.0:
        raise ConfigurationError("birth acceptance must leave recognition mutation off")
    chamber = SexualRecombinationConfig(
        enabled=True,
        same_length_only=True,
        recombination_prob=1.0,
        two_fold_cost_sex=False,
        diploid_meiosis=False,
        timeout_policy="asexual_fallback",
    )
    if not chamber.uses_birth_chamber:
        raise ConfigurationError("outcross birth requires the birth chamber")
    life = replace(
        configs.closed_loop_hp_life,
        role_by_id=tuple(sorted(arm.roles.items())),
    )
    if "host-A-001" not in life.role_map():
        raise ConfigurationError("installed hosts are missing from the life role map")
    arm.runner.configs = replace(
        configs,
        sexual_recombination=chamber,
        closed_loop_hp_life=life,
    )
    after = arm.runner.configs
    if float(after.reproduction.parent_atp_cost) != parent_cost:
        raise ConfigurationError("birth chamber changed the reproduction cost")
    if float(after.mutation.bit_flip_rate) != bit_flip:
        raise ConfigurationError("birth chamber changed the recognition mutation rate")
    if not after.reproduction.enabled:
        raise ConfigurationError("birth chamber turned reproduction off")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def branch_archive_hash(branch: str, file_sha256: str, file_bytes: bytes) -> str:
    """Hash label stored on one branch. Not an alias of another branch's bytes.

    Prediction. The rejected writer passed the common_a digest into every
    branch, including common_b, whose file bytes differ.

    Engine path. common_a and common_b keep the sha256 of the file they
    read. The absent branch reads those common_a bytes only as a roster to
    remove, and its label is sha256 of those bytes plus a branch tag so the
    stored label is not the common_a label.

    Control. Three different byte strings must produce three different
    labels. Hashing every branch as the first string is the failure.

    Limit. This does not rewrite an archive that already exists.
    """

    key = str(branch)
    if key not in BRANCHES:
        raise ConfigurationError(f"unknown phase-4 branch {branch!r}")
    digest = str(file_sha256)
    if len(digest) != 64 or any(ch not in "0123456789abcdef" for ch in digest):
        raise ConfigurationError("branch file hash must be a sha256 hex digest")
    if key == BRANCH_ABSENT:
        return hashlib.sha256(bytes(file_bytes) + b"\nbranch:absent\n").hexdigest()
    return digest


def _read_only_bytes(path: Path) -> bytes:
    """Read a phase-3 archive. Does not open it for write."""

    with path.open("rb") as handle:
        return handle.read()


def phase3_archive_path(phase3_root: Path, seed: int, branch: str) -> Path:
    if branch not in {BRANCH_COMMON_A, BRANCH_COMMON_B}:
        raise ConfigurationError("phase-3 source branch must be common_a or common_b")
    return phase3_root / "by_seed" / f"seed{int(seed)}" / branch / "archive.jsonl"


def load_conditioned_parasites(path: Path) -> tuple[list[dict[str, object]], str, int]:
    """Last parasite list. The file bytes are only read."""

    before = _read_only_bytes(path)
    digest = hashlib.sha256(before).hexdigest()
    last: dict[str, object] | None = None
    for line in before.decode("utf-8").splitlines():
        if line.strip():
            parsed = json.loads(line)
            if isinstance(parsed, dict):
                last = parsed
    if last is None:
        raise ConfigurationError(f"phase-3 archive is empty: {path}")
    parasites = last.get("parasites")
    if not isinstance(parasites, list) or not parasites:
        raise ConfigurationError(f"phase-3 archive has no parasites: {path}")
    generation = int(last["generation"])  # type: ignore[arg-type]
    after = _read_only_bytes(path)
    if after != before:
        raise ConfigurationError("reading the phase-3 archive changed its bytes")
    rows = [dict(row) for row in parasites if isinstance(row, dict)]
    return rows, digest, generation


def _genealogy_lists(
    parents: Mapping[str, str | None],
    founders: Mapping[str, str],
    living_ids: Sequence[str],
) -> dict[str, object]:
    parent_rows = [
        {"id": unit_id, "parent_id": parents[unit_id]}
        for unit_id in sorted(parents)
    ]
    founder_rows = [
        {"founder_class": founders[unit_id], "id": unit_id}
        for unit_id in sorted(founders)
    ]
    return {
        "founders": founder_rows,
        "living_ids": sorted(str(unit_id) for unit_id in living_ids),
        "parents": parent_rows,
    }


def _absorb_lineage(
    arm: StructuralRQArm,
    parents: dict[str, str | None],
    founders: Mapping[str, str],
) -> None:
    """Add births whose parent is already in the map. Repeat for grandchildren."""

    records = list(arm.runner.population.lineage)
    changed = True
    guard = 0
    while changed:
        changed = False
        guard += 1
        if guard > len(records) + 2:
            break
        for rec in records:
            unit_id = str(rec.organism_id)
            if unit_id in founders or unit_id in parents:
                continue
            parent_id = rec.parent_id
            if parent_id and (parent_id in founders or parent_id in parents):
                parents[unit_id] = str(parent_id)
                changed = True


def _count_class(
    unit_ids: Sequence[str],
    parents: Mapping[str, str | None],
    founders: Mapping[str, str],
) -> tuple[dict[str, int], int]:
    counts = {"A": 0, "B": 0}
    unresolved = 0
    for unit_id in unit_ids:
        label = resolve_founder_class(str(unit_id), parents, founders)
        if label is None:
            unresolved += 1
        else:
            counts[label] += 1
    return counts, unresolved


def run_fitness_branch(
    *,
    seed: int,
    branch: str,
    seats: Sequence[Mapping[str, str]],
    parasites: AntagonistPopulation,
    generations: int,
    archive_path: Path,
    source_sha256: str,
    archive_schema: str = ARCHIVE_SCHEMA,
    stream_root: str = STREAM_ROOT,
    forbid_rejected_archive: bool = False,
) -> dict[str, object]:
    """One branch. Stops on a lineage or mutation bug and keeps the file."""

    assert_branch_seed(int(seed))
    locked_horizons = {PHASE4_HORIZON, PHASE4B_HORIZON}
    if int(seed) in PHASE4_SEEDS and int(generations) not in locked_horizons:
        raise ConfigurationError("measurement horizon is locked")
    if int(generations) < 1:
        raise ConfigurationError("generations must be >= 1")
    assert_output_dir(archive_path.parent, forbid_rejected_archive=forbid_rejected_archive)
    arm = build_phase4_arm(seed, branch, seats, parasites, stream_root=stream_root)
    founders = {str(seat["host_id"]): str(seat["role_letter"]) for seat in seats}
    parents: dict[str, str | None] = {unit_id: None for unit_id in founders}
    archive_path.parent.mkdir(parents=True, exist_ok=True)
    handle = archive_path.open("a", encoding="utf-8")
    completed = 0
    reason: str | None = None
    try:
        for generation in range(1, int(generations) + 1):
            try:
                before_living = {str(org.id) for org in arm._hosts()}
                before_known = set(parents)
                arm.run_generations(1)
                _absorb_lineage(arm, parents, founders)
                after_hosts = list(arm._hosts())
                after_living = {str(org.id) for org in after_hosts}
                born = sorted(set(parents) - before_known)
                deaths = sorted((before_living | set(born)) - after_living)
                birth_counts, birth_unresolved = _count_class(born, parents, founders)
                death_counts, death_unresolved = _count_class(deaths, parents, founders)
                windows_ok = True
                for org in after_hosts:
                    label = resolve_founder_class(str(org.id), parents, founders)
                    expected = WINDOW_A if label == "A" else WINDOW_B if label == "B" else None
                    if expected is None or _window(org) != expected:
                        windows_ok = False
                        break
                pop = arm.antagonist_pop
                mutation_events = 0
                if isinstance(pop, AntagonistPopulation) and pop.ledgers:
                    mutation_events = int(pop.ledgers[-1].mutation_events)
                contacts = int(arm.graded_contact_count[-1]) if arm.graded_contact_count else 0
                events = arm.antagonist_contact_events[-1] if arm.antagonist_contact_events else ()
                host_atp_paid = float(sum(float(event.atp_paid) for event in events))
                reproduction_on = bool(arm.runner.configs.reproduction.enabled)
                bit_flip = float(arm.runner.configs.mutation.bit_flip_rate)
                parent_cost = float(arm.runner.configs.reproduction.parent_atp_cost)
                if not reproduction_on or parent_cost <= 0.0 or bit_flip != 0.0:
                    reason = f"reproduction or recognition flag drifted at generation {generation}"
                elif mutation_events != 0:
                    reason = f"recognition mutation fired at generation {generation}"
                elif not windows_ok:
                    reason = f"host recognition window changed at generation {generation}"
                elif birth_unresolved or death_unresolved:
                    reason = f"unresolved lineage id at generation {generation}"
                alive_counts, alive_unresolved = _count_class(sorted(after_living), parents, founders)
                if alive_unresolved and reason is None:
                    reason = f"unresolved living host at generation {generation}"
                row = {
                    "alive_end_A": int(alive_counts["A"]),
                    "alive_end_B": int(alive_counts["B"]),
                    "births_A": int(birth_counts["A"]),
                    "births_B": int(birth_counts["B"]),
                    "branch": str(branch),
                    "contacts": contacts,
                    "deaths_A": int(death_counts["A"]),
                    "deaths_B": int(death_counts["B"]),
                    "extinct_A": int(alive_counts["A"]) == 0,
                    "extinct_B": int(alive_counts["B"]) == 0,
                    "generation": int(generation),
                    "host_atp_paid": host_atp_paid,
                    "host_bit_flip_rate": bit_flip,
                    "host_inheritance": arm.host_inheritance,
                    "lineage_ok": reason is None,
                    "parasite_mutation_events": mutation_events,
                    "parasite_mutation_rate": 0.0,
                    "parent_atp_cost": parent_cost,
                    "passage": arm.passage,
                    "recognition_ok": windows_ok and mutation_events == 0 and bit_flip == 0.0,
                    "red_queen_proved": False,
                    "reproduction_enabled": reproduction_on,
                    "schema": str(archive_schema),
                    "seed": int(seed),
                    "source_sha256": source_sha256,
                }
                row.update(_genealogy_lists(parents, founders, sorted(after_living)))
            except Exception as exc:
                reason = f"{type(exc).__name__}: {exc}"
                break
            handle.write(json.dumps(row, sort_keys=True, separators=(",", ":")))
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
            completed = generation
            if reason is not None:
                break
    finally:
        handle.close()
    return {
        "branch": str(branch),
        "completed": completed,
        "failed": reason,
        "passage": arm.passage,
        "red_queen_proved": False,
        "reproduction_enabled": bool(arm.runner.configs.reproduction.enabled),
    }


def _write_json(path: Path, body: Mapping[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(body, sort_keys=True, indent=2) + "\n", encoding="utf-8")


def _parent_map(rows: Sequence[Mapping[str, object]]) -> dict[str, str | None]:
    mapped: dict[str, str | None] = {}
    for row in rows:
        unit_id = str(row["id"])
        raw = row.get("parent_id")
        mapped[unit_id] = None if raw in (None, "") else str(raw)
    return mapped


def _founder_map(rows: Sequence[Mapping[str, object]]) -> dict[str, str]:
    return {str(row["id"]): str(row["founder_class"]) for row in rows}


def _sum_counts(rows: Sequence[Mapping[str, object]], key_a: str, key_b: str) -> dict[str, int]:
    return {
        "A": int(sum(int(row[key_a]) for row in rows)),  # type: ignore[arg-type]
        "B": int(sum(int(row[key_b]) for row in rows)),  # type: ignore[arg-type]
    }


def _load_jsonl(path: Path) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    if not path.is_file():
        return rows
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            parsed = json.loads(line)
            if isinstance(parsed, dict):
                rows.append(parsed)
    return rows


def branch_measurement(rows: Sequence[Mapping[str, object]], *, generations: int) -> dict[str, object]:
    """Recompute the terminal share from archived parent ids. Ignore ATP."""

    if len(rows) != int(generations):
        return {
            "share_A": None,
            "share_B": None,
            "status": "incomplete",
        }
    if any(row.get("lineage_ok") is False or row.get("recognition_ok") is False for row in rows):
        return {
            "share_A": None,
            "share_B": None,
            "status": "unmeasurable",
        }
    last = rows[-1]
    living = last.get("living_ids")
    parent_rows = last.get("parents")
    founder_rows = last.get("founders")
    if not isinstance(living, list) or not isinstance(parent_rows, list) or not isinstance(founder_rows, list):
        return {"share_A": None, "share_B": None, "status": "unmeasurable"}
    scored = lineage_share(
        [str(unit_id) for unit_id in living],
        _parent_map(parent_rows),  # type: ignore[arg-type]
        _founder_map(founder_rows),  # type: ignore[arg-type]
    )
    births = _sum_counts(rows, "births_A", "births_B")
    deaths = _sum_counts(rows, "deaths_A", "deaths_B")
    contacts = int(sum(int(row["contacts"]) for row in rows))  # type: ignore[arg-type]
    paid = float(sum(float(row["host_atp_paid"]) for row in rows))  # type: ignore[arg-type]
    status = "measured" if scored["share_A"] is not None else "unmeasurable"
    return {
        "alive_end_A": int(last["alive_end_A"]),  # type: ignore[arg-type]
        "alive_end_B": int(last["alive_end_B"]),  # type: ignore[arg-type]
        "births": births,
        "contacts": contacts,
        "deaths": deaths,
        "extinct_A": bool(last["extinct_A"]),
        "extinct_B": bool(last["extinct_B"]),
        "host_atp_paid": paid,
        "passage": last.get("passage"),
        "share_A": scored["share_A"],
        "share_B": scored["share_B"],
        "status": status,
    }


def assess_phase4(
    by_seed: Mapping[int, Mapping[str, object]],
    locked_seeds: Sequence[int] = PHASE4_SEEDS,
) -> dict[str, object]:
    """Incomplete locked seeds are BLOCKED_MEASUREMENT, not a negative.

    Importance is undeclared. A complete sample is NOT_DECLARED, never SUPPORTED.
    ``MEASUREMENT_FLOOR`` is not lowered and is not the importance bound.
    """

    if int(MEASUREMENT_FLOOR) < 12:
        raise ConfigurationError("MEASUREMENT_FLOOR must not be lowered")
    locked = [int(seed) for seed in locked_seeds]
    if tuple(locked) != PHASE4_SEEDS:
        raise ConfigurationError("phase-4 locked seeds must be the full list")
    dropped: list[int] = []
    used: list[int] = []
    per_seed: list[dict[str, object]] = []
    for seed in locked:
        row = by_seed.get(int(seed))
        if row is None or row.get("F") is None:
            dropped.append(int(seed))
            per_seed.append(
                {
                    "F": None,
                    "seed": int(seed),
                    "status": "missing" if row is None else "unmeasurable",
                }
            )
            continue
        raw_f = row.get("F")
        if not _finite_number(raw_f):
            dropped.append(int(seed))
            per_seed.append({"F": None, "seed": int(seed), "status": "unmeasurable"})
            continue
        used.append(int(seed))
        per_seed.append({"F": float(raw_f), "seed": int(seed), "status": "measured"})  # type: ignore[arg-type]
    n_locked = len(locked)
    n_used = len(used)
    blocked = n_used != n_locked or bool(dropped)
    mean: float | None = None
    if not blocked and used:
        total = 0.0
        for seed in used:
            total += float(by_seed[seed]["F"])  # type: ignore[arg-type]
        mean = total / float(n_used)
    return {
        "F_mean": mean,
        "dropped_seeds": dropped,
        "importance_bound": None,
        "importance_rule": IMPORTANCE_RULE,
        "mde_is_importance_bound": False,
        "measurement_floor": int(MEASUREMENT_FLOOR),
        "measurement_floor_lowered": False,
        "n_locked": n_locked,
        "n_used": n_used,
        "per_seed_status": per_seed,
        "red_queen_declared": False,
        "red_queen_proved": False,
        "supported_forbidden": True,
        "verdict": VERDICT_BLOCKED if blocked else VERDICT_NOT_DECLARED,
    }


def _seed_estimand(seed_dir: Path, *, generations: int) -> dict[str, object]:
    branches: dict[str, dict[str, object]] = {}
    for branch in BRANCHES:
        rows = _load_jsonl(seed_dir / branch / "archive.jsonl")
        branches[branch] = branch_measurement(rows, generations=int(generations))
    common_a = branches[BRANCH_COMMON_A]
    common_b = branches[BRANCH_COMMON_B]
    absent = branches[BRANCH_ABSENT]
    contrast = fitness_contrast(
        common_a.get("share_A"),  # type: ignore[arg-type]
        common_a.get("share_B"),  # type: ignore[arg-type]
        common_b.get("share_A"),  # type: ignore[arg-type]
        common_b.get("share_B"),  # type: ignore[arg-type]
    )
    control = relative_advantage(absent.get("share_A"), absent.get("share_B"))  # type: ignore[arg-type]
    demography = None
    if common_a.get("status") == "measured" and common_b.get("status") == "measured":
        demography = contact_without_demography(
            contacts_a=int(common_a["contacts"]),  # type: ignore[arg-type]
            contacts_b=int(common_b["contacts"]),  # type: ignore[arg-type]
            paid_a=float(common_a["host_atp_paid"]),  # type: ignore[arg-type]
            paid_b=float(common_b["host_atp_paid"]),  # type: ignore[arg-type]
            births_a=common_a["births"],  # type: ignore[arg-type]
            births_b=common_b["births"],  # type: ignore[arg-type]
            deaths_a=common_a["deaths"],  # type: ignore[arg-type]
            deaths_b=common_b["deaths"],  # type: ignore[arg-type]
        )
    return {
        "F": contrast,
        "advantage_absent": control,
        "advantage_common_a": relative_advantage(
            common_a.get("share_A"),  # type: ignore[arg-type]
            common_a.get("share_B"),  # type: ignore[arg-type]
        ),
        "advantage_common_b": relative_advantage(
            common_b.get("share_A"),  # type: ignore[arg-type]
            common_b.get("share_B"),  # type: ignore[arg-type]
        ),
        "branches": branches,
        "contact_report": demography,
        "red_queen_proved": False,
    }


def analyze_phase4(
    root: Path,
    locked_seeds: Sequence[int] = PHASE4_SEEDS,
    *,
    generations: int | None = None,
) -> dict[str, object]:
    """Read archives. A missing history is dropped, not filled with zero."""

    assert_phase4_seeds(locked_seeds)
    horizon = PHASE4_HORIZON if generations is None else int(generations)
    by_seed: dict[int, dict[str, object]] = {}
    present: list[int] = []
    for seed in locked_seeds:
        seed_dir = root / "by_seed" / f"seed{int(seed)}"
        if not (seed_dir / "COMPLETE").is_file():
            continue
        present.append(int(seed))
        by_seed[int(seed)] = _seed_estimand(seed_dir, generations=horizon)
    report = assess_phase4(by_seed, locked_seeds)
    report["by_seed"] = {str(seed): by_seed[seed] for seed in present}
    report["horizon"] = dict(_HORIZON) if horizon == PHASE4_HORIZON else {"generations": horizon, "source": "host_energy_account"}
    report["horizon_generations"] = horizon
    report["no_fitness_sentence_was_the_lock"] = NO_FITNESS_SENTENCE
    report["red_queen_declared"] = False
    report["red_queen_proved"] = False
    report["workers_cap"] = MAX_WORKERS
    _write_json(root / "summary.json", report)
    return report


def run_phase4_seed(
    seed: int,
    root: Path,
    *,
    phase3_root: Path = PHASE3_FREQUENCY_ROOT,
    generations: int = PHASE4_HORIZON,
    stream_root: str | None = None,
    archive_schema: str | None = None,
    forbid_rejected_archive: bool = False,
) -> dict[str, object]:
    """Three branches from one seed's phase-3 parasites. Does not write phase 3."""

    if int(seed) not in PHASE4_SEEDS:
        raise ConfigurationError("run_phase4_seed is only for the locked histories")
    if int(generations) not in {PHASE4_HORIZON, PHASE4B_HORIZON}:
        raise ConfigurationError("measurement horizon is locked")
    assert_output_dir(root, forbid_rejected_archive=forbid_rejected_archive)
    if stream_root is None:
        stream_root = STREAM_ROOT_B if int(generations) == PHASE4B_HORIZON else STREAM_ROOT
    if archive_schema is None:
        archive_schema = ARCHIVE_SCHEMA_B if int(generations) == PHASE4B_HORIZON else ARCHIVE_SCHEMA
    seed_dir = root / "by_seed" / f"seed{int(seed)}"
    seed_dir.mkdir(parents=True, exist_ok=True)
    seats = equal_host_seats()
    sources: dict[str, dict[str, object]] = {}
    loaded: dict[str, AntagonistPopulation] = {}
    file_bytes: dict[str, bytes] = {}
    for branch in (BRANCH_COMMON_A, BRANCH_COMMON_B):
        path = phase3_archive_path(phase3_root, int(seed), branch)
        before = _read_only_bytes(path)
        file_bytes[branch] = before
        rows, digest, generation = load_conditioned_parasites(path)
        if _read_only_bytes(path) != before:
            raise ConfigurationError("phase-3 archive changed while loading")
        if generation != 7:
            reason = f"{path} last generation is {generation}, not 7"
            (seed_dir / "REASON.txt").write_text(reason + "\n", encoding="utf-8")
            return {"failed": reason, "red_queen_proved": False, "seed": int(seed)}
        sources[branch] = {
            "generation": generation,
            "n_parasites": len(rows),
            "path": str(path),
            "sha256": digest,
        }
        loaded[branch] = population_from_parasite_rows(rows)
    # The absent branch loads the common_a roster only so advance has a
    # population to remove. Contact is skipped because passage is absent.
    # The roster is not a genotype treatment.
    loaded[BRANCH_ABSENT] = population_from_parasite_rows(
        [
            {
                "born_generation": unit.born_generation,
                "energy": unit.energy,
                "parent_id": unit.parent_id,
                "unit_id": unit.unit_id,
                "window": unit.window,
            }
            for unit in loaded[BRANCH_COMMON_A].units
        ]
    )
    sources[BRANCH_ABSENT] = {
        "note": "passage absent; roster is removed before contact and is not a genotype treatment",
        "path": sources[BRANCH_COMMON_A]["path"],
        "sha256": sources[BRANCH_COMMON_A]["sha256"],
    }
    file_bytes[BRANCH_ABSENT] = file_bytes[BRANCH_COMMON_A]
    for branch in BRANCHES:
        label = branch_archive_hash(
            branch,
            str(sources[branch]["sha256"]),
            file_bytes[branch],
        )
        sources[branch]["archive_sha256"] = label
    labels = [str(sources[branch]["archive_sha256"]) for branch in BRANCHES]
    if len(set(labels)) != len(labels) and file_bytes[BRANCH_COMMON_A] != file_bytes[BRANCH_COMMON_B]:
        raise ConfigurationError("branch archive hashes aliased")
    _write_json(
        seed_dir / "initial.json",
        {
            "genomes": locked_genomes(),
            "horizon_generations": int(generations),
            "per_class": PHASE4_PER_CLASS,
            "red_queen_proved": False,
            "seed": int(seed),
            "sources": sources,
        },
    )
    summaries: dict[str, object] = {}
    failed: str | None = None
    for branch in BRANCHES:
        archive = seed_dir / branch / "archive.jsonl"
        if archive.exists() and archive.stat().st_size > 0:
            failed = f"archive already exists: {archive}"
            break
        summary = run_fitness_branch(
            seed=int(seed),
            branch=branch,
            seats=seats,
            parasites=loaded[branch],
            generations=int(generations),
            archive_path=archive,
            source_sha256=str(sources[branch]["archive_sha256"]),
            archive_schema=str(archive_schema),
            stream_root=str(stream_root),
            forbid_rejected_archive=forbid_rejected_archive,
        )
        summaries[branch] = summary
        if summary["failed"] or int(summary["completed"]) != int(generations):
            failed = str(summary["failed"] or "incomplete")
            (seed_dir / "REASON.txt").write_text(
                f"seed={seed} branch={branch} completed={summary['completed']} reason={failed}\n",
                encoding="utf-8",
            )
            break
    for branch in (BRANCH_COMMON_A, BRANCH_COMMON_B):
        path = phase3_archive_path(phase3_root, int(seed), branch)
        if _sha256(path) != str(sources[branch]["sha256"]):
            failed = f"phase-3 archive bytes changed: {path}"
            (seed_dir / "REASON.txt").write_text(failed + "\n", encoding="utf-8")
            break
    if failed:
        return {
            "branches": summaries,
            "failed": failed,
            "red_queen_proved": False,
            "seed": int(seed),
        }
    (seed_dir / "COMPLETE").write_text(
        f"generations={int(generations)} red_queen_proved=false\n",
        encoding="utf-8",
    )
    return {
        "branches": summaries,
        "failed": None,
        "red_queen_proved": False,
        "seed": int(seed),
    }


def _worker(payload: dict[str, object]) -> dict[str, object]:
    return run_phase4_seed(
        int(payload["seed"]),
        Path(str(payload["root"])),
        phase3_root=Path(str(payload["phase3_root"])),
        generations=int(payload["generations"]),
        stream_root=None if payload.get("stream_root") is None else str(payload["stream_root"]),
        archive_schema=None if payload.get("archive_schema") is None else str(payload["archive_schema"]),
        forbid_rejected_archive=bool(payload.get("forbid_rejected_archive", False)),
    )


def execute_phase4(
    root: Path,
    *,
    workers: int | None = None,
    phase3_root: Path = PHASE3_FREQUENCY_ROOT,
    seeds: Sequence[int] = PHASE4_SEEDS,
    generations: int = PHASE4_HORIZON,
    stream_root: str | None = None,
    archive_schema: str | None = None,
    forbid_rejected_archive: bool = False,
) -> dict[str, object]:
    """Run the locked histories. Workers at most 7. Does not prove Red Queen."""

    assert_phase4_seeds(seeds)
    assert_output_dir(root, forbid_rejected_archive=forbid_rejected_archive)
    if int(generations) not in {PHASE4_HORIZON, PHASE4B_HORIZON}:
        raise ConfigurationError("measurement horizon is locked")
    n_workers = resolve_workers(workers)
    root.mkdir(parents=True, exist_ok=True)
    payloads = [
        {
            "archive_schema": archive_schema,
            "forbid_rejected_archive": forbid_rejected_archive,
            "generations": int(generations),
            "phase3_root": str(phase3_root),
            "root": str(root),
            "seed": int(seed),
            "stream_root": stream_root,
        }
        for seed in seeds
    ]
    results: list[dict[str, object]] = []
    if n_workers == 1:
        for payload in payloads:
            results.append(_worker(payload))
    else:
        with ProcessPoolExecutor(max_workers=n_workers) as pool:
            futures = [pool.submit(_worker, payload) for payload in payloads]
            for future in as_completed(futures):
                results.append(future.result())
    report = analyze_phase4(root, seeds, generations=int(generations))
    report["results"] = results
    report["workers"] = n_workers
    report["red_queen_proved"] = False
    _write_json(root / "summary.json", {key: value for key, value in report.items() if key != "results"})
    if any(item.get("failed") for item in results):
        report["stopped"] = True
    return report


def render_phase4_lock(*, code_commit: str) -> str:
    """Lock text. Refuses to embed a fitness number. Call before the run."""

    if not code_commit or code_commit.strip() != code_commit or len(code_commit) < 7:
        raise ConfigurationError("code commit must be a full hash")
    genomes = locked_genomes()
    horizon = _horizon_record()
    lines = [
        "# Phase-4 lock",
        "",
        NO_FITNESS_SENTENCE,
        "No generation of seeds 9501, 9502, 9503, or 9504 has been run for this fitness assay.",
        "This file is the lock, written before any phase-4 fitness history.",
        "`red_queen_proved` is false. This is not a Red Queen claim.",
        "A positive fitness link is not Red Queen. A negative fitness link is not Red Queen.",
        "",
        f"Code commit: `{code_commit}` on branch `rq/mechanism-v2`.",
        "Nothing has been pushed, merged, or rebased.",
        "`runs/rq-bidirectional-timeshift-01` is untouched and is not part of this commit.",
        "",
        "## Fitness definition",
        "",
        "ATP loss is not host success and is not this score.",
        "Each branch starts with equal counts of host A and host B on the shared food patches,",
        "the shared resource bolus, the shared birth ATP, and the shared reproduction cost.",
        "`L_A` is the fraction of hosts alive after the horizon whose founder class is A.",
        "Founder class is the class installed on that id, or the class reached by walking `parent_id`.",
        "Founders are not counted as births. `L_B` is the fraction whose founder class is B.",
        "The walk uses births' parent ids. It does not use ATP.",
        "If nobody is alive, or any living id cannot be walked to A or B, `L_A` and `L_B` are null.",
        "Null is not zero.",
        "If one class is absent and the other is present, the shares are the measured 0 and 1.",
        "That zero is a counted absence in the living census, not a missing seed.",
        "Relative advantage `R = L_A - L_B`.",
        "`F = R(parasite from that seed's phase-3 common_a archive) - R(parasite from that seed's phase-3 common_b archive)`.",
        "The absent-passage advantage is reported beside F and is not written into F.",
        "Prediction, not a support bound: F below zero would mean the parasite conditioned while A was common",
        "reduced A's relative advantage compared with the parasite conditioned while B was common, and the converse.",
        "The sign is not an importance bound.",
        "Survival is the count of deaths of each class: an id that was alive at the start of the generation",
        "or born during it, and is not alive after the generation. Contact removal does not write `death_tick`;",
        "the id difference is the death record. Reproduction is the count of lineage births of each class.",
        "Those counts are not an ATP drop.",
        "",
        "## Extinction",
        "",
        "A class is extinct in a generation when its living count after that generation is 0.",
        "The archive line is still written. The history is not deleted. The seed is not replaced.",
        "The run keeps stepping through the locked horizon while the engine accepts the step.",
        "An empty terminal census makes the share null, not zero.",
        "If a locked seed is missing or its F is null, the verdict is BLOCKED_MEASUREMENT,",
        "not a negative on the reduced sample.",
        "Unmeasurable is missing, not zero.",
        "`n_locked`, `n_used`, and `dropped_seeds` are reported.",
        "",
        "## Horizon",
        "",
        f"Fitness generations: {horizon['conditioning_generations']}",
        f"Recorded replacement generations: {horizon['replacement_generations']}",
        f"Recorded mean seated newborns: {horizon['mean_seated_newborns']}",
        f"Recorded census: {horizon['census']}",
        f"Turnover multiple, pre-declared: {horizon['turnover_multiple']}",
        "The replacement time 60/26 and the multiple 3 are the phase-3 record.",
        "They were not remeasured for this contrast and were not chosen from the sign of F.",
        "One engine generation is one `run_generations` step: the host life-loop, then contact, then one parasite advance.",
        str(horizon["why_not_one"]) + ".",
        "The horizon was not chosen from the sign of F.",
        "",
        "## Seeds and genomes",
        "",
        "Measurement histories: 9501, 9502, 9503, 9504.",
        "Hosts were not re-selected from a fitness sign. They are the phase-3 lock.",
        f"Exemplar id A: `{genomes['exemplar_a']}`",
        f"Exemplar id B: `{genomes['exemplar_b']}`",
        f"Genome A: `{genomes['genome_a']}`",
        f"Genome B: `{genomes['genome_b']}`",
        f"Window A: `{genomes['window_a']}`",
        f"Window B: `{genomes['window_b']}`",
        "Equal counts: 30 of A and 30 of B. Census 60, so every parasite seat from the phase-3 census can be paired.",
        "Index modulo 2 equal to 0 is A. The first two ids are the exemplars.",
        "Virulence, steal fraction, maintenance, birth ATP, bolus, and `MEASUREMENT_FLOOR` are not retuned.",
        "",
        "## Control and mutation",
        "",
        "Three branches, each from that seed's own phase-3 parasites:",
        "- `common_a`: parasite list from `common_a/archive.jsonl`, passage `coevolve`, parasite mutation rate 0.",
        "- `common_b`: parasite list from `common_b/archive.jsonl`, passage `coevolve`, parasite mutation rate 0.",
        "- `absent`: passage `absent` (`PASSAGE_ABSENT`). `_apply_hp_env_contact` returns no contacts and no debit.",
        "Host `reproduction.enabled` stays true. Host `parent_atp_cost` stays the booted cost.",
        "Host `bit_flip_rate` is 0. That is recognition mutation off, not reproduction off.",
        "`freeze_host_genotypic_inheritance` is not used. The absent branch is not a pure evolution control.",
        "`shuffled_labels` is not used. `shuffled_labels` is not a frozen genotype.",
        "Passage `frozen` is not used. The frozen reseat would replace conditioned windows with founders.",
        "The absent roster is loaded only so `advance` has a population to remove. It is not a third genotype treatment.",
        "",
        "## Rules",
        "",
        IMPORTANCE_RULE,
        "SUPPORTED is forbidden.",
        f"`MEASUREMENT_FLOOR` stays {MEASUREMENT_FLOOR} and is not lowered. It is not the importance bound.",
        "CPU workers at most 7.",
        "Source archives are read-only. They are not modified, deleted, or rewritten:",
        "- `runs/rq-mechanism-v2/phase3-frequency/by_seed/seed9501/common_a/archive.jsonl`",
        "- `runs/rq-mechanism-v2/phase3-frequency/by_seed/seed9501/common_b/archive.jsonl`",
        "- `runs/rq-mechanism-v2/phase3-frequency/by_seed/seed9502/common_a/archive.jsonl`",
        "- `runs/rq-mechanism-v2/phase3-frequency/by_seed/seed9502/common_b/archive.jsonl`",
        "- `runs/rq-mechanism-v2/phase3-frequency/by_seed/seed9503/common_a/archive.jsonl`",
        "- `runs/rq-mechanism-v2/phase3-frequency/by_seed/seed9503/common_b/archive.jsonl`",
        "- `runs/rq-mechanism-v2/phase3-frequency/by_seed/seed9504/common_a/archive.jsonl`",
        "- `runs/rq-mechanism-v2/phase3-frequency/by_seed/seed9504/common_b/archive.jsonl`",
        "Output: `runs/rq-mechanism-v2/phase4-fitness/`.",
        "Raw archives are kept. A partial run is kept. The seed is not replaced.",
        "`red_queen_proved` stays false.",
        "",
        NO_FITNESS_SENTENCE,
        "",
    ]
    text = "\n".join(lines)
    if re.search(r"F\s*=\s*-?\d", text):
        raise ConfigurationError("lock text must not contain a fitness result")
    return text


def execute_phase4b(
    root: Path | None = None,
    *,
    workers: int | None = None,
    phase3_root: Path = PHASE3_FREQUENCY_ROOT,
    seeds: Sequence[int] = PHASE4_SEEDS,
) -> dict[str, object]:
    """Phase-4b histories. Does not write the rejected phase4-fitness tree."""

    target = PHASE4B_OUTPUT if root is None else root
    report = execute_phase4(
        target,
        workers=workers,
        phase3_root=phase3_root,
        seeds=seeds,
        generations=PHASE4B_HORIZON,
        stream_root=STREAM_ROOT_B,
        archive_schema=ARCHIVE_SCHEMA_B,
        forbid_rejected_archive=True,
    )
    report["red_queen_declared"] = False
    report["red_queen_proved"] = False
    return report


def render_phase4b_lock(*, code_commit: str) -> str:
    """Lock text for the rerun. Refuses to embed a fitness number."""

    if not code_commit or code_commit.strip() != code_commit or len(code_commit) < 7:
        raise ConfigurationError("code commit must be a full hash")
    genomes = locked_genomes()
    lines = [
        "# Phase-4b lock",
        "",
        NO_FITNESS_SENTENCE,
        "No generation of seeds 9501, 9502, 9503, or 9504 has been run for this phase-4b fitness assay.",
        "This file is the lock, written before any phase-4b fitness history.",
        "`red_queen_proved` is false. This is not a Red Queen claim.",
        "A positive fitness link is not Red Queen. A negative fitness link is not Red Queen.",
        "A nonzero F is not Red Queen.",
        "",
        f"Code commit: `{code_commit}` on branch `rq/mechanism-v2`.",
        "Nothing has been pushed, merged, or rebased.",
        "`runs/rq-bidirectional-timeshift-01` is untouched and is not part of this commit.",
        "The rejected run stays at `runs/rq-mechanism-v2/phase4-fitness/`. It is not deleted and its seeds are not changed.",
        "",
        "## Fitness definition",
        "",
        "ATP loss is not host success and is not this score.",
        "Each branch starts with equal counts of host A and host B on the shared food patches,",
        "the shared resource bolus, the shared birth ATP, and the shared reproduction cost.",
        "`L_A` is the fraction of hosts alive after the horizon whose founder class is A.",
        "Founder class is the class installed on that id, or the class reached by walking `parent_id`.",
        "Founders are not counted as births. `L_B` is the fraction whose founder class is B.",
        "The walk uses births' parent ids. It does not use ATP.",
        "If nobody is alive, or any living id cannot be walked to A or B, `L_A` and `L_B` are null.",
        "Null is not zero.",
        "If one class is absent and the other is present, the shares are the measured 0 and 1.",
        "That zero is a counted absence in the living census, not a missing seed.",
        "Relative advantage `R = L_A - L_B`.",
        "`F = R(parasite from that seed's phase-3 common_a archive) - R(parasite from that seed's phase-3 common_b archive)`.",
        "The absent-passage advantage is reported beside F and is not written into F.",
        "The absent control is passage absent, not a pure evolution control. Host reproduction stays enabled.",
        "Prediction, not a support bound: F below zero would mean the parasite conditioned while A was common",
        "reduced A's relative advantage compared with the parasite conditioned while B was common, and the converse.",
        "The sign is not an importance bound.",
        "Survival is the count of deaths of each class. Reproduction is the count of lineage births of each class.",
        "Those counts are not an ATP drop.",
        "",
        "## Extinction",
        "",
        "A class is extinct in a generation when its living count after that generation is 0.",
        "The archive line is still written. The history is not deleted. The seed is not replaced.",
        "An empty terminal census makes the share null, not zero.",
        "If a locked seed is missing or its F is null, the verdict is BLOCKED_MEASUREMENT,",
        "not a negative on the reduced sample.",
        "Unmeasurable is missing, not zero.",
        "`n_locked`, `n_used`, and `dropped_seeds` are reported.",
        "",
        "## Horizon",
        "",
        "Fitness generations: 9",
        "The horizon is not the parasite replacement time 60/26 and not the ceiling of 3 times that time.",
        "It was not chosen from the sign of F. No fitness number has been computed.",
        "Opening runtime ATP is the structural birth ATP, 48.",
        "One contact debit is virulence 8.0 times steal fraction 0.15 times graded affinity.",
        "Affinity is at most 1, so the per-generation debit cap is 1.2.",
        "The life-loop applies basal maintenance 0.05 at each of 2 ticks, when that amount is payable.",
        "After the outcross and recognition windows are silenced, the program is EAT_LUMEN 0.8, COPY_SELF 8.0, WAIT 0.1.",
        "The cursor starts at 0 and advances 2 codons per generation, including a codon whose full cost is not payable.",
        "The death account credits no food. The resource bolus is not placed on that account.",
        "Evaluated on that account, balance after the life-loop and then after a 1.2 debit:",
        "- generation 1: 48 - 8.9 = 39.1, then 37.9",
        "- generation 2: 37.9 - 1.0 = 36.9, then 35.7",
        "- generation 3: 35.7 - 8.2 = 27.5, then 26.3",
        "- generation 4: 26.3 - 8.9 = 17.4, then 16.2",
        "- generation 5: 16.2 - 1.0 = 15.2, then 14.0",
        "- generation 6: 14.0 - 8.2 = 5.8, then 4.6",
        "- generation 7: COPY_SELF 8.0 is not payable; 4.6 - 0.9 = 3.7, then 2.5. Still alive.",
        "- generation 8: 2.5 - 1.0 = 1.5, then 0.3. Still alive.",
        "- generation 9: COPY_SELF 8.0 is not payable; 0.3 - 0.2 = 0.1, then the debit takes the last 0.1 and the balance is 0.",
        "Death is first reachable at generation 9. Generation 7 leaves 2.5.",
        "The life-loop on the assay path does place a 20.0 bolus on each food patch before the step.",
        "When EAT_LUMEN collects that bolus the balance rises, so the fed path is not the death bound.",
        "The bolus is not turned off to create a death or to make F nonzero.",
        "The locked horizon is 9 because that is the first generation of the no-food maximum-debit account at which death is reachable.",
        "An accepted birth is a separate way for the census to move. The horizon was not shortened to the first birth.",
        "",
        "## Seeds and genomes",
        "",
        "Measurement histories: 9501, 9502, 9503, 9504.",
        "Hosts were not re-selected from a fitness sign. They are the phase-3 lock.",
        "Parasites stay the phase-3 frequency-panel archives for those seeds. Those archives are read only.",
        f"Exemplar id A: `{genomes['exemplar_a']}`",
        f"Exemplar id B: `{genomes['exemplar_b']}`",
        f"Genome A: `{genomes['genome_a']}`",
        f"Genome B: `{genomes['genome_b']}`",
        f"Window A: `{genomes['window_a']}`",
        f"Window B: `{genomes['window_b']}`",
        "Equal counts: 30 of A and 30 of B. Census 60.",
        "Index modulo 2 equal to 0 is A. The first two ids are the exemplars.",
        "Virulence, steal fraction, maintenance, birth ATP, bolus, mutation rate, and `MEASUREMENT_FLOOR` are not retuned.",
        "",
        "## Control and mutation",
        "",
        "Three branches, each from that seed's own phase-3 parasites:",
        "- `common_a`: parasite list from `common_a/archive.jsonl`, passage `coevolve`, parasite mutation rate 0.",
        "- `common_b`: parasite list from `common_b/archive.jsonl`, passage `coevolve`, parasite mutation rate 0.",
        "- `absent`: passage `absent` (`PASSAGE_ABSENT`). `_apply_hp_env_contact` returns no contacts and no debit.",
        "Host `reproduction.enabled` stays true. Host `parent_atp_cost` stays the booted cost.",
        "Host `bit_flip_rate` is 0. That is recognition mutation off, not reproduction off.",
        "The birth chamber is on, because the outcross locus requires it. That is not a virulence change.",
        "`freeze_host_genotypic_inheritance` is not used. The absent branch is not a pure evolution control.",
        "`shuffled_labels` is not used. `shuffled_labels` is not a frozen genotype.",
        "Passage `frozen` is not used.",
        "Each branch stores its own archive hash. The common_a digest is not written onto the other branches.",
        "",
        "## Rules",
        "",
        IMPORTANCE_RULE,
        "SUPPORTED is forbidden.",
        f"`MEASUREMENT_FLOOR` stays {MEASUREMENT_FLOOR} and is not lowered. It is not the importance bound.",
        "CPU workers at most 7.",
        "Source archives are read-only. They are not modified, deleted, or rewritten:",
        "- `runs/rq-mechanism-v2/phase3-frequency/by_seed/seed9501/common_a/archive.jsonl`",
        "- `runs/rq-mechanism-v2/phase3-frequency/by_seed/seed9501/common_b/archive.jsonl`",
        "- `runs/rq-mechanism-v2/phase3-frequency/by_seed/seed9502/common_a/archive.jsonl`",
        "- `runs/rq-mechanism-v2/phase3-frequency/by_seed/seed9502/common_b/archive.jsonl`",
        "- `runs/rq-mechanism-v2/phase3-frequency/by_seed/seed9503/common_a/archive.jsonl`",
        "- `runs/rq-mechanism-v2/phase3-frequency/by_seed/seed9503/common_b/archive.jsonl`",
        "- `runs/rq-mechanism-v2/phase3-frequency/by_seed/seed9504/common_a/archive.jsonl`",
        "- `runs/rq-mechanism-v2/phase3-frequency/by_seed/seed9504/common_b/archive.jsonl`",
        "Output: `runs/rq-mechanism-v2/phase4b-fitness/`.",
        "Do not write into `runs/rq-mechanism-v2/phase4-fitness/`.",
        "Raw archives are kept. A partial run is kept. The seed is not replaced.",
        "`red_queen_proved` stays false.",
        "",
        NO_FITNESS_SENTENCE,
        "",
    ]
    text_out = "\n".join(lines)
    if re.search(r"F\s*=\s*-?\d", text_out):
        raise ConfigurationError("lock text must not contain a fitness result")
    return text_out
