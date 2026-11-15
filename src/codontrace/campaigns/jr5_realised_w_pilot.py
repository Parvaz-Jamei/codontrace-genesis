"""JR5 realised-w pilot (PREREG section 7): runner for the E1 instrument check.

The pilot measures the engine's realised per-generation odds ratio w of an
all-female asexual line against obligate outcrossers before any
confirmatory seed runs: m = 0.5, N = 200, T = 5, one population per seed,
seeds 13201-13240, the full section-4 engine config. Every setting comes
from the locked prereg constants (``realised_w_pilot``, ``gate_e1``,
``seeds``, ``validity`` and ``host_mating_arm_modes.engine_config``), read
through ``load_e1_gate_spec`` so the plan digest and the constants sha256
are verified first. The one exception is the population design (below):
the prereg does not fix it, and each of its fields can move realised w. It
is therefore pinned by its digest in a pre-pilot ``DEVIATIONS.md`` entry,
and the pilot mode refuses any design whose digest that entry does not name.

Per population: the founders are N organisms on the outcross locus, of which
the registered founder share (0.2N) are marked as the asexual lineage. Each
generation is one ``run_generations(1)`` step of ``LifeLoopEcologyArm`` (the
registered timing harness) with no parasite (avirulent arm, passage
absent). The census row records the asexual count out of the census; the
E1 fit is the registered bias-reduced logit, loaded from the file the prereg
names (``gate_e1.fit.implementation``) and pinned by sha256 here. The cell is
then evaluated by ``evaluate_e1_pilot_cell``, the E1 cell rule with the
pilot's seed block, so exclusion, cap, TOST and the 95% check are E1's own
code. The pilot passes exactly when that cell passes (the 90% interval
inside the registered bounds with the exclusion cap respected; inside those
bounds the 95% interval always excludes 1).

The demography that turns an engine step into a generation at census N is
not fixed by the prereg. It is a ``PopulationDesign`` (generation model and
the harness settings), recorded with its digest in every output.
``PILOT_POPULATION_DESIGN`` is None until that design is decided, and the
pilot mode refuses to run while it is None, and unless the latest design
line of the verified deviations log names its digest in an entry that
declares no pilot seed ran before it. The smoke mode (development and
tests) runs any design on seeds outside every registered and sealed block,
at a host N below the pilot's, and never produces a pilot decision. Smoke
mode is blind: the fit is run (its convergence is checked) but no smoke
output holds a realised-w estimate, so a design cannot be tuned on w.

Outputs, all under one output directory that may not lie in the prereg
folder or the packaged constants: ``run.json`` (configuration, fixed at
the first start, checked on every resume), ``progress.log`` (append-only
JSON lines: per-seed start and end, rows written, invariant results, ETA,
any traceback), ``seeds/seed-<s>.jsonl`` (one row per generation and a
final fit row), ``populations.csv``, ``result.json`` (pilot mode, all seeds
done) and ``manifest.json`` (sha256 and size of every file). Files are
written to a temporary name, synced and renamed into place. The scientific
files hold no timestamps, so a one-shot and a resumed run write the same
bytes. A seed whose final file exists is kept only after its rows pass the
invariants again, its fit is recomputed to the stored fit row, and its
sha256 matches the previous manifest. A seed whose run was killed is re-run
on the same seed and the incomplete file is kept beside it, never replaced.

The run stops at the first broken invariant or non-finite number. This
module draws no random numbers; the engine draws from the run seed through
RNGManager.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import io
import json
import math
import os
import platform
import re
import sys
import time
import traceback
from collections.abc import Callable, Iterator, Mapping, Sequence
from dataclasses import asdict, dataclass, field, replace
from datetime import UTC, datetime
from pathlib import Path
from types import ModuleType
from typing import Any

from codontrace._types import JsonValue
from codontrace.campaigns.jr5_e1_gate import (
    CONSTANTS_RELPATH,
    LOCKED_PREREG_MANIFEST_DIGEST,
    PREREG_RELDIR,
    E1CellResult,
    E1GateSpec,
    E1Population,
    evaluate_e1_pilot_cell,
    load_e1_gate_spec,
)
from codontrace.errors import ConfigurationError
from codontrace.genesis.canonical import canonical_digest
from codontrace.preregistration.jr5_locked_plan import (
    DEVIATIONS_RELPATH,
    deviations_log_entries,
    read_deviations_log,
    verify_deviations_log,
    verify_jr5_record_at_root,
)

__all__ = [
    "DESIGN_DIGEST_LINE",
    "FIT_IMPLEMENTATION_SHA256",
    "GENERATION_MODELS",
    "PRE_PILOT_LINE",
    "PILOT_POPULATION_DESIGN",
    "PilotInvariantError",
    "PopulationDesign",
    "RealisedWPilotSpec",
    "build_population",
    "census_row",
    "check_output_dir",
    "check_pilot_seeds",
    "check_smoke_seeds",
    "fit_population",
    "load_realised_w_pilot_spec",
    "main",
    "pilot_decision",
    "run_pilot",
    "spec_from_constants",
    "verified_pilot_design_digest",
]

RUN_SCHEMA = "jr5_realised_w_pilot_run_v1"
RESULT_SCHEMA = "jr5_realised_w_pilot_result_v1"
MODE_PILOT = "pilot"
MODE_SMOKE = "smoke"
# sha256 of tests/_jr5_e1_fit.py, the fit the prereg names
# (gate_e1.fit.implementation). A changed file is refused: the pilot rule
# says the estimator is never changed.
FIT_IMPLEMENTATION_SHA256 = "1fecda121b2dae21e680f95d2ae0fc6671fd82452773b1ad399f92a4b86b2118"
# Generation models a design may name. Only the engine's own overlapping
# generations (one run_generations(1) step, parents stay) are wired; the
# others are refused until their code is reviewed.
GENERATION_MODELS = (
    "engine_overlapping",
    "parent_removal_each_generation",
    "resample_to_census",
    "founders_below_census",
)
_WIRED_GENERATION_MODELS = frozenset({"engine_overlapping"})
# The pre-pilot DEVIATIONS entry names the design with this line, and states
# that no pilot seed ran before it with the second.
DESIGN_DIGEST_LINE = re.compile(
    r"^- Realised-w pilot population design: `(jr5_e1_population_design:[0-9a-f]{64})`$", re.M
)
PRE_PILOT_LINE = "- Pilot seeds run before this entry: none."
# Paths under the repo root the runner never writes into.
_PROTECTED_RELDIRS = (PREREG_RELDIR, "src", "tests")


class PilotInvariantError(ConfigurationError):
    """A run invariant broke; the run stops at the first one."""


def _now() -> str:
    return datetime.now(UTC).astimezone().isoformat(timespec="seconds")


def _sha256_bytes(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _sha256_file(path: Path) -> str:
    return _sha256_bytes(path.read_bytes())


def _mapping(value: object, what: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ConfigurationError(f"{what} must be a mapping.")
    return value


def _number(value: object, what: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(float(value)):
        raise ConfigurationError(f"{what} must be a finite number.")
    return float(value)


def _integer(value: object, what: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ConfigurationError(f"{what} must be an integer.")
    return value


def _text(value: object, what: str) -> str:
    if not isinstance(value, str) or not value:
        raise ConfigurationError(f"{what} must be a non-empty string.")
    return value


def _block(value: object, what: str) -> tuple[int, int]:
    if not isinstance(value, Sequence) or isinstance(value, str) or len(value) != 2:
        raise ConfigurationError(f"{what} must be a [first, last] pair.")
    first, last = _integer(value[0], what), _integer(value[1], what)
    if last < first:
        raise ConfigurationError(f"{what} must have first <= last.")
    return (first, last)


def _overlaps(a: tuple[int, int], b: tuple[int, int]) -> bool:
    return a[0] <= b[1] and b[0] <= a[1]


# --------------------------------------------------------------------- spec


@dataclass(frozen=True, slots=True)
class RealisedWPilotSpec:
    """Pilot settings, each read from the locked constants and cross-checked against E1."""

    gate: E1GateSpec
    seed_block: tuple[int, int]
    populations: int
    sex_ratio: float
    host_n: int
    horizon: int
    founder_share: float
    ci_level: float
    bounds: tuple[float, float]
    on_fail: str
    max_reruns_after_fix: int
    fit_tol: float
    fit_max_iter: int
    fit_implementation: str
    max_ledger_residual: float
    other_blocks: tuple[tuple[str, int, int], ...]
    sealed_ranges: tuple[tuple[int, int], ...]
    engine_config: Mapping[str, Any] = field(compare=False)

    @property
    def seeds(self) -> range:
        return range(self.seed_block[0], self.seed_block[1] + 1)

    def to_record(self) -> dict[str, JsonValue]:
        return {
            "constants_sha256": self.gate.constants_sha256,
            "prereg_plan_digest": self.gate.prereg_manifest_sha256,
            "seed_block": list(self.seed_block),
            "populations": self.populations,
            "sex_ratio": self.sex_ratio,
            "host_n": self.host_n,
            "horizon": self.horizon,
            "founder_share": self.founder_share,
            "ci_level": self.ci_level,
            "bounds": list(self.bounds),
            "on_fail": self.on_fail,
            "max_reruns_after_fix": self.max_reruns_after_fix,
            "fit_tol": self.fit_tol,
            "fit_max_iter": self.fit_max_iter,
            "fit_implementation": self.fit_implementation,
            "max_ledger_residual": self.max_ledger_residual,
            "engine_config": json.loads(json.dumps(self.engine_config)),
        }


def load_realised_w_pilot_spec(root: str | Path | None = None) -> RealisedWPilotSpec:
    """Verify the lock (through the E1 gate loader), then read and cross-check the pilot block.

    Refused unless every stated pilot number agrees with E1 at the pilot's
    sex ratio: horizon = gate_e1.generations[m], bounds = the registered E1
    bounds, ci_level = the E1 TOST level, populations = the seed block size
    = gate_e1.populations_per_cell, host N gated, estimator the E1 one, the
    outcross fee 0.0 in both the pilot block and the section-4 engine config,
    diploid_meiosis on in both; and unless the seed block lies outside every
    other registered block and every sealed range.
    """

    gate = load_e1_gate_spec(root)
    base = Path(root) if root is not None else Path(__file__).resolve().parents[3]
    raw = (base / CONSTANTS_RELPATH).read_bytes()
    if _sha256_bytes(raw) != gate.constants_sha256:
        raise ConfigurationError("constants file changed after the lock was verified.")
    return spec_from_constants(gate, _mapping(json.loads(raw.decode("utf-8")), "constants"))


def spec_from_constants(gate: E1GateSpec, constants: Mapping[str, Any]) -> RealisedWPilotSpec:
    """Decode and cross-check the pilot block; ``load_realised_w_pilot_spec`` verifies the bytes first."""

    pilot = _mapping(constants.get("realised_w_pilot"), "realised_w_pilot")
    g = _mapping(constants.get("gate_e1"), "gate_e1")
    seeds = _mapping(constants.get("seeds"), "seeds")
    validity = _mapping(constants.get("validity"), "validity")
    modes = _mapping(constants.get("host_mating_arm_modes"), "host_mating_arm_modes")
    engine = _mapping(modes.get("engine_config"), "host_mating_arm_modes.engine_config")
    if pilot.get("confirmatory") is not False or pilot.get("enters_claims") is not False:
        raise ConfigurationError("realised_w_pilot must be non-confirmatory and enter no claim.")
    if pilot.get("engine_config") != "host_mating_arm_modes.engine_config":
        raise ConfigurationError("realised_w_pilot.engine_config must name host_mating_arm_modes.engine_config.")
    if pilot.get("estimator") != "same_as_gate_e1" or pilot.get("fit") != "bias_reduced":
        raise ConfigurationError("realised_w_pilot must use the E1 bias-reduced estimator.")
    block = _block(pilot.get("seed_block"), "realised_w_pilot.seed_block")
    if _block(seeds.get("realised_w_pilot_block"), "seeds.realised_w_pilot_block") != block:
        raise ConfigurationError("realised_w_pilot.seed_block disagrees with seeds.realised_w_pilot_block.")
    populations = _integer(pilot.get("populations"), "realised_w_pilot.populations")
    if populations != block[1] - block[0] + 1 or populations != gate.populations_per_cell:
        raise ConfigurationError("realised_w_pilot.populations must equal its seed block and the E1 cell size.")
    m = _number(pilot.get("sex_ratio"), "realised_w_pilot.sex_ratio")
    low, high = gate.ratio_bounds(m)
    bounds = tuple(_number(b, "realised_w_pilot.bounds") for b in pilot.get("bounds", ()))
    if bounds != (low, high):
        raise ConfigurationError("realised_w_pilot.bounds must equal the registered E1 bounds.")
    host_n = _integer(pilot.get("host_n"), "realised_w_pilot.host_n")
    if host_n != gate.host_n_gate:
        raise ConfigurationError("realised_w_pilot.host_n must be the gated E1 host N.")
    horizon = _integer(pilot.get("horizon"), "realised_w_pilot.horizon")
    generations = _mapping(g.get("generations"), "gate_e1.generations")
    if horizon != _integer(generations.get(str(m)), f"gate_e1.generations[{m}]") or horizon < 1:
        raise ConfigurationError("realised_w_pilot.horizon must equal the E1 horizon at its sex ratio.")
    ci = _number(pilot.get("ci_level"), "realised_w_pilot.ci_level")
    if ci != 1.0 - 2.0 * gate.alpha:
        raise ConfigurationError("realised_w_pilot.ci_level must be the E1 TOST level.")
    share = _number(g.get("founder_uniparental_frequency"), "gate_e1.founder_uniparental_frequency")
    if not 0.0 < share < 1.0 or g.get("founder") != "all_female_asexual":
        raise ConfigurationError("gate_e1 founder share must be in (0, 1) and all-female asexual.")
    if pilot.get("diploid_meiosis") is not True:
        raise ConfigurationError("realised_w_pilot.diploid_meiosis must be true.")
    if _number(pilot.get("outcross_mating_fee_atp"), "realised_w_pilot.outcross_mating_fee_atp") != 0.0:
        raise ConfigurationError("realised_w_pilot.outcross_mating_fee_atp must be 0.0.")
    sexual = _mapping(engine.get("sexual_recombination"), "engine_config.sexual_recombination")
    life = _mapping(engine.get("closed_loop_hp_life"), "engine_config.closed_loop_hp_life")
    if sexual.get("diploid_meiosis") is not True:
        raise ConfigurationError("engine_config.sexual_recombination.diploid_meiosis must be true.")
    if _number(life.get("outcross_runtime_atp"), "engine_config.closed_loop_hp_life.outcross_runtime_atp") != 0.0:
        raise ConfigurationError("engine_config outcross_runtime_atp must be 0.0.")
    fit = _mapping(g.get("fit"), "gate_e1.fit")
    implementation = fit.get("implementation")
    if not isinstance(implementation, str) or fit.get("on_no_convergence") != "raise":
        raise ConfigurationError("gate_e1.fit must name its implementation and raise on no convergence.")
    residual = _number(validity.get("atp_ledger_max_residual"), "validity.atp_ledger_max_residual")
    other: list[tuple[str, int, int]] = []
    for name in ("confirmatory_block", "e1_calibration_block", "pilot_block"):
        first, last = _block(seeds.get(name), f"seeds.{name}")
        if _overlaps(block, (first, last)):
            raise ConfigurationError(f"realised-w pilot block overlaps seeds.{name}.")
        other.append((name, first, last))
    sealed_raw = seeds.get("sealed_ranges")
    if not isinstance(sealed_raw, Sequence) or isinstance(sealed_raw, str):
        raise ConfigurationError("seeds.sealed_ranges must be a list.")
    sealed = tuple(_block(r, "seeds.sealed_ranges") for r in sealed_raw)
    for r in sealed:
        if _overlaps(block, r):
            raise ConfigurationError(f"realised-w pilot block overlaps sealed range {r[0]}-{r[1]}.")
    return RealisedWPilotSpec(
        gate=gate,
        seed_block=block,
        populations=populations,
        sex_ratio=m,
        host_n=host_n,
        horizon=horizon,
        founder_share=share,
        ci_level=ci,
        bounds=(low, high),
        on_fail=_text(pilot.get("on_fail"), "realised_w_pilot.on_fail"),
        max_reruns_after_fix=_integer(pilot.get("max_reruns_after_fix"), "realised_w_pilot.max_reruns_after_fix"),
        fit_tol=_number(fit.get("tol"), "gate_e1.fit.tol"),
        fit_max_iter=_integer(fit.get("max_iter"), "gate_e1.fit.max_iter"),
        fit_implementation=implementation,
        max_ledger_residual=residual,
        other_blocks=tuple(other),
        sealed_ranges=sealed,
        engine_config=engine,
    )


# --------------------------------------------------------------- seed guards


def check_pilot_seeds(spec: RealisedWPilotSpec, seeds: Sequence[int]) -> tuple[int, ...]:
    """Pilot mode: every seed lies in the registered block, each once."""

    chosen = tuple(seeds)
    if not chosen:
        raise ConfigurationError("no pilot seeds given.")
    for s in chosen:
        if isinstance(s, bool) or not isinstance(s, int) or s not in spec.seeds:
            raise ConfigurationError(f"seed {s!r} is outside the realised-w pilot block {spec.seed_block}.")
    if len(set(chosen)) != len(chosen):
        raise ConfigurationError("pilot seeds must not repeat.")
    return chosen


def check_smoke_seeds(spec: RealisedWPilotSpec, seeds: Sequence[int]) -> tuple[int, ...]:
    """Smoke mode: no seed may touch the pilot block, another registered block or a sealed range."""

    chosen = tuple(seeds)
    if not chosen:
        raise ConfigurationError("no smoke seeds given.")
    blocks = [("realised_w_pilot", *spec.seed_block), *spec.other_blocks]
    for s in chosen:
        if isinstance(s, bool) or not isinstance(s, int) or s < 0:
            raise ConfigurationError(f"smoke seed {s!r} must be a non-negative integer.")
        for name, first, last in blocks:
            if first <= s <= last:
                raise ConfigurationError(f"smoke seed {s} lies in the registered {name} block.")
        for first, last in spec.sealed_ranges:
            if first <= s <= last:
                raise ConfigurationError(f"smoke seed {s} lies in sealed range {first}-{last}.")
    if len(set(chosen)) != len(chosen):
        raise ConfigurationError("smoke seeds must not repeat.")
    return chosen


def check_output_dir(out_dir: str | Path, root: str | Path | None = None) -> Path:
    """Refuse an output directory inside the prereg folder, the source or test tree, or the repo root.

    The directory may not be, lie inside, or contain ``docs/prereg/jr5``,
    ``src`` (the packaged constants included) or ``tests``, may not be the
    repo root itself, and
    may not contain any file listed in the prereg ``record.json`` manifest.
    """

    base = (Path(root) if root is not None else Path(__file__).resolve().parents[3]).resolve()
    out = Path(out_dir).resolve()
    if out == base:
        raise ConfigurationError("output directory must not be the repository root.")
    for rel in _PROTECTED_RELDIRS:
        protected = (base / rel).resolve()
        if out == protected or protected in out.parents or out in protected.parents:
            raise ConfigurationError(f"output directory must not be or contain {rel}.")
    record = base / PREREG_RELDIR / "record.json"
    if record.is_file():
        manifest = _mapping(json.loads(record.read_text(encoding="utf-8")).get("manifest"), "record manifest")
        for entry in manifest.get("files", []):
            locked = (base / str(entry[0])).resolve()
            if locked == out or out in locked.parents:
                raise ConfigurationError(f"output directory must not contain the locked file {entry[0]}.")
    if out.exists() and not out.is_dir():
        raise ConfigurationError("output path exists and is not a directory.")
    return out


# ------------------------------------------------------------------ design


@dataclass(frozen=True, slots=True)
class PopulationDesign:
    """Demography of one E1 population on ``LifeLoopEcologyArm``.

    Founders are always ``host_n`` organisms (PREREG section 7: founder
    count 0.2N and founder frequency 0.2). ``soft_k_multiple`` scales
    ``host_n`` to the harness's soft carrying capacity. The other fields are
    ``LifeLoopEcologyArm.boot`` arguments. The sexual and mating-fee settings
    are not here: they come from the locked section-4 engine config.
    """

    label: str
    generation_model: str
    soft_k_multiple: float
    world_size: int
    birth_atp: float
    basal_runtime_atp_cost: float
    passage_refill_mode: str
    resource_bolus_amount: float
    food_patches: tuple[tuple[int, int], ...]
    founder_spatial_policy: str
    mating_locus_lock: bool
    mate_search_radius: int | None
    outcross_mates_per_generation_cap: int | None
    chamber_max_birth_wait_ticks: int | None
    chamber_timeout_policy: str
    founder_windows: tuple[str, ...]

    def __post_init__(self) -> None:
        if not self.label or not self.founder_windows or self.world_size < 1:
            raise ConfigurationError("population design needs a label, founder windows and a world size.")
        if not math.isfinite(self.soft_k_multiple) or self.soft_k_multiple < 1.0:
            raise ConfigurationError("soft_k_multiple must be a finite number >= 1.")
        if self.generation_model not in GENERATION_MODELS:
            raise ConfigurationError(f"generation_model must be one of {GENERATION_MODELS}.")

    def soft_k(self, host_n: int) -> int:
        k = self.soft_k_multiple * host_n
        if k != int(k):
            raise ConfigurationError("soft_k_multiple * host_n must be an integer.")
        return int(k)

    def to_record(self) -> dict[str, JsonValue]:
        """Every field, so the digest covers the whole design."""

        payload: dict[str, Any] = asdict(self)
        payload["food_patches"] = [list(p) for p in self.food_patches]
        payload["founder_windows"] = list(self.founder_windows)
        record: dict[str, JsonValue] = json.loads(json.dumps(payload))
        return record

    def digest(self) -> str:
        return canonical_digest(self.to_record(), prefix="jr5_e1_population_design")


# Not decided: see the module docstring. The pilot mode refuses while None.
PILOT_POPULATION_DESIGN: PopulationDesign | None = None


def verified_pilot_design_digest(root: str | Path | None = None) -> tuple[str, str]:
    """(design digest, entry heading) from the latest design line of the verified deviations log.

    The log is verified through the locked-plan check (record.json fresh
    hashes, accepted checkpoints, chain, last entry = the plan digest); the
    bytes parsed here must be the bytes record.json lists. The latest entry
    with a design line wins; it must name exactly one design and state that
    no pilot seed ran before it. Refused when no entry names a design.
    """

    base = Path(root) if root is not None else Path(__file__).resolve().parents[3]
    manifest, plan = verify_jr5_record_at_root(base, locked_plan_digest=LOCKED_PREREG_MANIFEST_DIGEST)
    try:
        text = read_deviations_log(base / DEVIATIONS_RELPATH)
    except OSError as exc:
        raise ConfigurationError("DEVIATIONS.md is not readable.") from exc
    listed = dict(manifest.files).get(DEVIATIONS_RELPATH)
    if listed != _sha256_bytes(text.encode("utf-8")):
        raise ConfigurationError("DEVIATIONS.md changed after record.json was verified.")
    verify_deviations_log(text, expected_plan_digest=plan)
    named: list[tuple[str, str]] = []
    for entry in deviations_log_entries(text):
        found = DESIGN_DIGEST_LINE.findall(entry)
        if len(found) > 1:
            raise ConfigurationError("a DEVIATIONS.md entry names more than one pilot population design.")
        if found:
            if PRE_PILOT_LINE not in entry.splitlines():
                raise ConfigurationError(
                    "the DEVIATIONS.md design entry does not state that no pilot seed ran before it."
                )
            named.append((found[0], entry.splitlines()[0]))
    if not named:
        raise ConfigurationError("no DEVIATIONS.md entry names a pilot population design.")
    return named[-1]


def _guard_boot(spec: RealisedWPilotSpec, mode: str, seed: int) -> None:
    """Second barrier, immediately before an engine boot: the seed must pass its mode's guard again."""

    if mode == MODE_SMOKE:
        check_smoke_seeds(spec, [seed])
    elif mode == MODE_PILOT:
        check_pilot_seeds(spec, [seed])
    else:
        raise ConfigurationError(f"mode must be {MODE_PILOT!r} or {MODE_SMOKE!r}.")


def build_population(spec: RealisedWPilotSpec, design: PopulationDesign, seed: int, host_n: int) -> Any:
    """One E1 population: founders, asexual share, section-4 engine config, no parasite."""

    from codontrace.genesis.closed_loop_hp_arm01 import ARM_AVIRULENT, LifeLoopEcologyArm
    from codontrace.genesis.host_parasite_life_plugin import OUTCROSS_OUT_BITS, hp_life_config

    if design.generation_model not in _WIRED_GENERATION_MODELS:
        raise ConfigurationError(f"generation model {design.generation_model!r} is not wired in this runner.")
    engine = spec.engine_config
    sexual = _mapping(engine.get("sexual_recombination"), "engine_config.sexual_recombination")
    life = _mapping(engine.get("closed_loop_hp_life"), "engine_config.closed_loop_hp_life")
    locus = _mapping(engine.get("outcross_locus"), "engine_config.outcross_locus")
    types = _mapping(engine.get("mating_type_set"), "engine_config.mating_type_set")
    if locus.get("obligate_outcross") != OUTCROSS_OUT_BITS:
        raise ConfigurationError("the engine's outcross allele differs from the registered obligate_outcross locus.")
    if engine.get("delayed_selfing") is not False:
        raise ConfigurationError("engine_config.delayed_selfing must be false.")
    asexual_n = spec.founder_share * host_n
    if asexual_n != int(asexual_n) or int(asexual_n) < 1:
        raise ConfigurationError("founder share times host N must be a positive integer.")
    stride = 1.0 / spec.founder_share
    if stride != int(stride):
        raise ConfigurationError("founder share must be 1/k for an even spread of asexual founders.")
    windows = design.founder_windows
    arm = LifeLoopEcologyArm.boot(
        arm=ARM_AVIRULENT,
        seed=seed,
        birth_atp=design.birth_atp,
        founders=[("outcross", windows[i % len(windows)]) for i in range(host_n)],
        world_size=design.world_size,
        soft_carrying_capacity=design.soft_k(host_n),
        basal_runtime_atp_cost=design.basal_runtime_atp_cost,
        passage_refill_mode=design.passage_refill_mode,
        resource_bolus_amount=design.resource_bolus_amount,
        food_patches=design.food_patches,
        founder_spatial_policy=design.founder_spatial_policy,
        two_fold_cost_sex=bool(sexual.get("two_fold_cost_sex")),
        mating_locus_lock=design.mating_locus_lock,
        selfing_birth_atp_endowment=_number(life.get("selfing_birth_atp_endowment"), "selfing_birth_atp_endowment"),
        mate_search_radius=design.mate_search_radius,
        outcross_mates_per_generation_cap=design.outcross_mates_per_generation_cap,
        chamber_max_birth_wait_ticks=design.chamber_max_birth_wait_ticks,
        chamber_timeout_policy=design.chamber_timeout_policy,
    )
    configs = arm.runner.configs
    sexual_cfg = replace(
        configs.sexual_recombination,
        enabled=sexual.get("enabled") is True,
        mating_types_enabled=sexual.get("mating_types_enabled") is True,
        sex_assignment=str(sexual.get("sex_assignment")),
        pairing_policy=str(sexual.get("pairing_policy")),
        two_fold_cost_sex=sexual.get("two_fold_cost_sex") is True,
        hermaphrodite_selfing=sexual.get("hermaphrodite_selfing") is True,
        diploid_meiosis=sexual.get("diploid_meiosis") is True,
        mating_type_set=tuple(str(t) for t in types.get("obligate_outcross", ())),
        sex_ratio=spec.sex_ratio,
    )
    life_cfg = replace(
        hp_life_config(configs.closed_loop_hp_life),
        outcross_enabled=life.get("outcross_enabled") is True,
        selfing_birth_atp_endowment=_number(life.get("selfing_birth_atp_endowment"), "selfing_birth_atp_endowment"),
        outcross_runtime_atp=_number(life.get("outcross_runtime_atp"), "outcross_runtime_atp"),
    )
    arm.runner.configs = replace(configs, sexual_recombination=sexual_cfg, closed_loop_hp_life=life_cfg)
    step = int(stride)
    organisms = tuple(
        replace(org, asexual_lineage=(index % step == 0)) for index, org in enumerate(arm.runner.population.organisms)
    )
    arm.runner.population = replace(arm.runner.population, organisms=organisms)
    return arm


# ------------------------------------------------------------------ census


def _ledger_residual(arm: Any) -> float:
    ledger = arm.runner.atp_ledger
    if ledger is None:
        raise PilotInvariantError("the population has no world ATP ledger to check.")
    try:
        ledger.check()
    except Exception as exc:
        raise PilotInvariantError(f"world ATP ledger check failed: {exc}") from exc
    totals = ledger.totals()
    residual = totals["sources_in"] - totals["sinks_out"] - totals["agents"] - totals["reservoir"] - totals["clearing"]
    return float(residual)


def _fee_atp(arm: Any) -> float:
    total = 0.0
    for org in arm.runner.population.organisms:
        ledger = org.atp_state.runtime.to_dict().get("ledger", [])
        if isinstance(ledger, list):
            for entry in ledger:
                if isinstance(entry, dict) and entry.get("reason") == "outcross_runtime_cost":
                    total += float(entry.get("amount", 0.0))
    return total


def census_row(arm: Any, generation: int, seen: set[str], genome_length: int, seed: int) -> dict[str, Any]:
    """Census of one generation: counts by type, asexual count, census, births, ledger and fee."""

    from codontrace.genesis.population import mating_type_census

    population = arm.runner.population
    sexual = arm.runner.configs.effective_sexual_config
    ids = [o.id for o in population.organisms]
    births = sum(1 for i in ids if i not in seen)
    seen.update(ids)
    lengths = sorted({len(o.genome.to_compact()) for o in population.organisms})
    counts = mating_type_census(population, seed=seed + 1, sexual=sexual)
    return {
        "kind": "generation",
        "generation": generation,
        "census": len(ids),
        "asexual": sum(1 for o in population.organisms if o.asexual_lineage),
        "counts": counts,
        "births": births if generation > 0 else 0,
        "genome_lengths": lengths,
        "genome_length_founders": genome_length,
        "ledger_residual": _ledger_residual(arm),
        "outcross_fee_atp": _fee_atp(arm),
    }


def check_row(
    row: Mapping[str, Any], previous: Mapping[str, Any] | None, spec: RealisedWPilotSpec, soft_k: int
) -> list[str]:
    """Invariant names that hold for ``row``; raise PilotInvariantError at the first that does not."""

    checked: list[str] = []

    def need(name: str, ok: bool, detail: str) -> None:
        if not ok:
            raise PilotInvariantError(f"invariant {name} broke at generation {row.get('generation')}: {detail}")
        checked.append(name)

    numbers = [row["census"], row["asexual"], row["births"], row["ledger_residual"], row["outcross_fee_atp"]]
    need("finite", all(isinstance(v, (int, float)) and math.isfinite(float(v)) for v in numbers), f"{numbers}")
    census, asexual = int(row["census"]), int(row["asexual"])
    need("census_positive", census >= 1, f"census {census}")
    need("asexual_within_census", 0 <= asexual <= census, f"asexual {asexual} of {census}")
    need("census_within_soft_k", census <= soft_k, f"census {census} > soft K {soft_k}")
    need(
        "counts_sum_to_census",
        sum(row["counts"].values()) == census and row["counts"].get("asexual", 0) == asexual,
        f"{row['counts']}",
    )
    need(
        "genome_length_conserved", row["genome_lengths"] == [row["genome_length_founders"]], f"{row['genome_lengths']}"
    )
    need("ledger_residual", abs(float(row["ledger_residual"])) <= spec.max_ledger_residual, f"{row['ledger_residual']}")
    need("outcross_fee_zero", float(row["outcross_fee_atp"]) == 0.0, f"{row['outcross_fee_atp']}")
    if previous is None:
        need("founder_share", asexual == round(spec.founder_share * census) and census >= 1, f"{asexual} of {census}")
    else:
        need("generation_step", row["generation"] == previous["generation"] + 1, "generation index")
        need(
            "births_present",
            int(row["births"]) >= 1,
            "no births: the population did not reproduce, so the asexual share cannot change",
        )
        was_fixed = previous["asexual"] == previous["census"]
        was_lost = previous["asexual"] == 0
        need("fixation_absorbing", not was_fixed or asexual == census, "asexual line lost fixation")
        need("loss_absorbing", not was_lost or asexual == 0, "asexual line reappeared")
    return checked


# --------------------------------------------------------------------- fit


def load_fit(spec: RealisedWPilotSpec, root: str | Path | None = None) -> tuple[ModuleType, str]:
    """Load the registered fit file by path; refuse it unless its sha256 is the pinned one."""

    base = Path(root) if root is not None else Path(__file__).resolve().parents[3]
    path = base / spec.fit_implementation
    try:
        raw = path.read_bytes()
    except OSError as exc:
        raise ConfigurationError(f"registered fit {spec.fit_implementation} is not readable.") from exc
    digest = _sha256_bytes(raw)
    if digest != FIT_IMPLEMENTATION_SHA256:
        raise ConfigurationError("registered fit file does not match its pinned sha256.")
    module_spec = importlib.util.spec_from_file_location("_jr5_registered_e1_fit", path)
    if module_spec is None or module_spec.loader is None:
        raise ConfigurationError("registered fit file cannot be loaded.")
    module = importlib.util.module_from_spec(module_spec)
    module_spec.loader.exec_module(module)
    if getattr(module, "TOL", None) != spec.fit_tol or getattr(module, "MAX_ITER", None) != spec.fit_max_iter:
        raise ConfigurationError("registered fit tolerance or iteration cap disagrees with gate_e1.fit.")
    return module, digest


def fit_population(
    fit_module: ModuleType, spec: RealisedWPilotSpec, rows: Sequence[Mapping[str, Any]]
) -> tuple[float | None, int | None, int | None, bool]:
    """(log w, fixed generation, lost generation, converged) from the census rows.

    log w is the slope of the bias-reduced logit of asexual count out of
    census against generation over all generations 0 to T. Fixed: the first
    generation with count = census; lost: the first with count 0. A fit that
    does not converge raises for a population kept by the exclusion rule
    (gate_e1.fit.on_no_convergence) and gives None for an excluded one.
    """

    import numpy as np

    x = np.array([float(r["generation"]) for r in rows], dtype=float)
    k = np.array([float(r["asexual"]) for r in rows], dtype=float)
    n = np.array([float(r["census"]) for r in rows], dtype=float)
    fixed = next((int(r["generation"]) for r in rows if r["asexual"] == r["census"]), None)
    lost = next((int(r["generation"]) for r in rows if r["asexual"] == 0), None)
    excluded = fixed is not None and fixed < spec.gate.early_fixation_generation
    try:
        beta = fit_module.fit_logit(k, n, x, bias_reduced=True, tol=spec.fit_tol, max_iter=spec.fit_max_iter)
    except RuntimeError:
        if excluded:
            return None, fixed, lost, False
        raise
    slope = float(beta[1])
    if not math.isfinite(slope) or not math.isfinite(float(beta[0])):
        if excluded:
            return None, fixed, lost, False
        raise PilotInvariantError("the bias-reduced fit returned a non-finite estimate.")
    return slope, fixed, lost, True


def pilot_decision(spec: RealisedWPilotSpec, populations: Sequence[E1Population]) -> tuple[E1CellResult, bool]:
    """The E1 cell rule on the pilot block; the pilot passes exactly when that cell passes."""

    cell = evaluate_e1_pilot_cell(spec.gate, spec.sex_ratio, spec.host_n, populations, spec.seed_block)
    return cell, cell.passed


# ------------------------------------------------------------------ runner


class _Progress:
    def __init__(self, path: Path) -> None:
        self.path = path

    def write(self, event: str, **fields: Any) -> None:
        line = json.dumps({"ts": _now(), "event": event, **fields}, sort_keys=True, default=str)
        with self.path.open("a", encoding="utf-8") as fh:
            fh.write(line + "\n")
            fh.flush()


def _json_bytes(payload: Any) -> bytes:
    return (json.dumps(payload, sort_keys=True, indent=1, allow_nan=False) + "\n").encode("utf-8")


def _git_head(root: Path) -> str | None:
    head = root / ".git"
    try:
        if head.is_file():
            gitdir = Path(head.read_text(encoding="utf-8").split(":", 1)[1].strip())
            head = gitdir if gitdir.is_absolute() else root / gitdir
        ref = (head / "HEAD").read_text(encoding="utf-8").strip()
        if ref.startswith("ref: "):
            name = ref[5:]
            loose = head / name
            if loose.is_file():
                return loose.read_text(encoding="utf-8").strip()
            common = head / "commondir"
            base = (head / common.read_text(encoding="utf-8").strip()).resolve() if common.is_file() else head
            loose = base / name
            if loose.is_file():
                return loose.read_text(encoding="utf-8").strip()
            packed = base / "packed-refs"
            if packed.is_file():
                for line in packed.read_text(encoding="utf-8").splitlines():
                    if line.endswith(" " + name):
                        return line.split(" ", 1)[0]
            return None
        return ref
    except OSError:
        return None


def _run_seed(
    spec: RealisedWPilotSpec,
    design: PopulationDesign,
    seed: int,
    host_n: int,
    horizon: int,
    fit_module: ModuleType,
    on_row: Callable[[dict[str, Any], list[str]], None],
    mode: str,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    _guard_boot(spec, mode, seed)
    arm = build_population(spec, design, seed, host_n)
    soft_k = design.soft_k(host_n)
    founders = arm.runner.population.organisms
    lengths = {len(o.genome.to_compact()) for o in founders}
    if len(lengths) != 1:
        raise PilotInvariantError("founders differ in genome length.")
    genome_length = lengths.pop()
    seen: set[str] = set()
    rows: list[dict[str, Any]] = []
    previous: dict[str, Any] | None = None
    for generation in range(horizon + 1):
        if generation > 0:
            arm.run_generations(1)
        row = census_row(arm, generation, seen, genome_length, seed)
        checked = check_row(row, previous, spec, soft_k)
        rows.append(row)
        on_row(row, checked)
        previous = row
    return rows, _fit_row(fit_module, spec, rows, seed, mode)


def _fit_row(
    fit_module: ModuleType, spec: RealisedWPilotSpec, rows: Sequence[Mapping[str, Any]], seed: int, mode: str
) -> dict[str, Any]:
    """The fit row; in smoke mode the estimate is withheld (log_w null, blinded true)."""

    log_w, fixed, lost, converged = fit_population(fit_module, spec, rows)
    blinded = mode != MODE_PILOT
    return {
        "kind": "fit",
        "seed": seed,
        "log_w": None if blinded else log_w,
        "blinded": blinded,
        "fixed_generation": fixed,
        "lost_generation": lost,
        "converged": converged,
        "generations": [r["generation"] for r in rows],
        "asexual": [r["asexual"] for r in rows],
        "census": [r["census"] for r in rows],
    }


def _read_json(path: Path, what: str) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, ValueError) as exc:
        raise ConfigurationError(f"{what} is not readable JSON; it is never rewritten.") from exc


def _verify_kept_seed(
    path: Path,
    seed: int,
    spec: RealisedWPilotSpec,
    soft_k: int,
    horizon: int,
    fit_module: ModuleType,
    mode: str,
    listed_sha256: str | None,
) -> dict[str, Any]:
    """A kept seed file is used only if it would be written again as it is."""

    raw = path.read_bytes()
    if listed_sha256 is not None and _sha256_bytes(raw) != listed_sha256:
        raise ConfigurationError(f"{path.name} differs from the previous manifest; it is never rewritten.")
    try:
        records = [json.loads(line) for line in raw.decode("utf-8").splitlines()]
    except (UnicodeError, ValueError) as exc:
        raise ConfigurationError(f"{path.name} is not JSON lines; it is never rewritten.") from exc
    if not records or not isinstance(records[-1], dict) or records[-1].get("kind") != "fit":
        raise ConfigurationError(f"{path.name} exists without its fit row; it is never rewritten.")
    stored = records[-1]
    if stored.get("seed") != seed:
        raise ConfigurationError(f"{path.name} holds the fit row of another seed.")
    rows = records[:-1]
    if [r.get("generation") for r in rows] != list(range(horizon + 1)):
        raise ConfigurationError(f"{path.name} does not hold generations 0 to {horizon}.")
    previous: dict[str, Any] | None = None
    for row in rows:
        check_row(row, previous, spec, soft_k)
        previous = row
    if _fit_row(fit_module, spec, rows, seed, mode) != stored:
        raise ConfigurationError(f"{path.name} fit row does not match its rows; it is never rewritten.")
    return dict(stored)


def _fsync_dir(directory: Path) -> None:
    fd = os.open(directory, os.O_RDONLY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def _atomic_write(path: Path, data: bytes) -> None:
    """Write to a temporary name, sync, rename into place and sync the directory."""

    tmp = path.with_name(path.name + ".tmp")
    with tmp.open("wb") as fh:
        fh.write(data)
        fh.flush()
        os.fsync(fh.fileno())
    os.replace(tmp, path)
    _fsync_dir(path.parent)


def _manifest(out: Path, run_info: Mapping[str, Any]) -> dict[str, Any]:
    files = []
    for path in sorted(p for p in out.rglob("*") if p.is_file() and p.name != "manifest.json"):
        files.append(
            {"path": path.relative_to(out).as_posix(), "sha256": _sha256_file(path), "bytes": path.stat().st_size}
        )
    body = [f for f in files if f["path"] != "progress.log"]
    return {
        "schema": RUN_SCHEMA,
        "run": dict(run_info),
        "files": files,
        "body_digest": canonical_digest({"files": body}, prefix="jr5_realised_w_pilot_body"),
    }


def _previous_manifest_shas(out: Path) -> dict[str, str]:
    path = out / "manifest.json"
    if not path.exists():
        return {}
    stored = _read_json(path, "manifest.json")
    files = stored.get("files") if isinstance(stored, dict) else None
    if not isinstance(files, list):
        raise ConfigurationError("manifest.json has no file list; it is never rewritten.")
    shas: dict[str, str] = {}
    for entry in files:
        if (
            not isinstance(entry, dict)
            or not isinstance(entry.get("path"), str)
            or not isinstance(entry.get("sha256"), str)
        ):
            raise ConfigurationError("manifest.json file entries must name a path and a sha256.")
        shas[entry["path"]] = entry["sha256"]
    return shas


def _populations_csv(run_seeds: Sequence[int], fits: Mapping[int, Mapping[str, Any]], mode: str) -> bytes:
    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator="\n")
    blinded = mode != MODE_PILOT
    header = ["seed", "fixed_generation", "lost_generation", "converged"]
    writer.writerow(header if blinded else ["seed", "log_w", *header[1:]])
    for seed in run_seeds:
        f = fits[seed]
        tail = [f["fixed_generation"], f["lost_generation"], f["converged"]]
        writer.writerow([seed, *tail] if blinded else [seed, repr(f["log_w"]), *tail])
    return buffer.getvalue().encode("utf-8")


def run_pilot(
    out_dir: str | Path,
    *,
    mode: str = MODE_PILOT,
    seeds: Sequence[int] | None = None,
    design: PopulationDesign | None = None,
    host_n: int | None = None,
    horizon: int | None = None,
    root: str | Path | None = None,
    spec: RealisedWPilotSpec | None = None,
) -> dict[str, Any]:
    """Run (or resume) the pilot or a smoke run; return the run summary.

    Pilot mode: ``seeds`` default to the whole registered block,
    ``host_n``/``horizon`` must be left at the registered values and the
    design is ``PILOT_POPULATION_DESIGN`` (refused while None, and unless the
    verified deviations log names its digest in a pre-pilot entry). The
    decision is written only when every seed of the block is complete. Smoke
    mode: an explicit design, seeds outside every registered and sealed
    block and a host N below the pilot's; blind (no w estimate is written);
    no decision.
    """

    pilot_spec = spec if spec is not None else load_realised_w_pilot_spec(root)
    base = (Path(root) if root is not None else Path(__file__).resolve().parents[3]).resolve()
    out = check_output_dir(out_dir, base)
    if mode == MODE_PILOT:
        if design is not None or host_n is not None or horizon is not None:
            raise ConfigurationError("pilot mode takes no design, host N or horizon override.")
        if PILOT_POPULATION_DESIGN is None:
            raise ConfigurationError(
                "the pilot population design is not decided (PILOT_POPULATION_DESIGN is None); no pilot seed runs."
            )
        run_design = PILOT_POPULATION_DESIGN
        pinned, _heading = verified_pilot_design_digest(base)
        if pinned != run_design.digest():
            raise ConfigurationError("the pilot population design is not the one the DEVIATIONS.md entry pins.")
        run_seeds = check_pilot_seeds(pilot_spec, list(pilot_spec.seeds) if seeds is None else seeds)
        run_n, run_t = pilot_spec.host_n, pilot_spec.horizon
    elif mode == MODE_SMOKE:
        if design is None or seeds is None or host_n is None:
            raise ConfigurationError("smoke mode needs a design, seeds and a host N.")
        run_design = design
        run_seeds = check_smoke_seeds(pilot_spec, seeds)
        if isinstance(host_n, bool) or not isinstance(host_n, int) or not 1 <= host_n < pilot_spec.host_n:
            raise ConfigurationError("smoke host N must be an integer below the pilot host N.")
        run_n = host_n
        run_t = pilot_spec.horizon if horizon is None else horizon
        if isinstance(run_t, bool) or not isinstance(run_t, int) or run_t < 1:
            raise ConfigurationError("smoke horizon must be a positive integer.")
    else:
        raise ConfigurationError(f"mode must be {MODE_PILOT!r} or {MODE_SMOKE!r}.")
    fit_module, fit_sha = load_fit(pilot_spec, base)
    import numpy as np

    run_info: dict[str, Any] = {
        "schema": RUN_SCHEMA,
        "mode": mode,
        "blinded": mode != MODE_PILOT,
        "seeds": list(run_seeds),
        "host_n": run_n,
        "horizon": run_t,
        "spec": pilot_spec.to_record(),
        "design": run_design.to_record(),
        "design_digest": run_design.digest(),
        "fit_sha256": fit_sha,
        "git_head": _git_head(base),
        "python": platform.python_version(),
        "numpy": str(np.__version__),
    }
    out.mkdir(parents=True, exist_ok=True)
    (out / "seeds").mkdir(exist_ok=True)
    run_path = out / "run.json"
    progress = _Progress(out / "progress.log")
    soft_k = run_design.soft_k(run_n)
    if run_path.exists():
        stored = _read_json(run_path, "run.json")
        if not isinstance(stored, dict):
            raise ConfigurationError("run.json must hold an object.")
        same = {k: v for k, v in stored.items() if k not in ("git_head", "python", "numpy")}
        mine = {k: v for k, v in json.loads(json.dumps(run_info)).items() if k not in ("git_head", "python", "numpy")}
        if same != mine:
            raise ConfigurationError("run.json in the output directory belongs to a different configuration.")
        progress.write("resume", run_digest=canonical_digest(mine, prefix="jr5_rwp_run"), git_head=run_info["git_head"])
    else:
        _atomic_write(run_path, _json_bytes(run_info))
        progress.write(
            "start",
            run_digest=canonical_digest(json.loads(json.dumps(run_info)), prefix="jr5_rwp_run"),
            mode=mode,
            seeds=len(run_seeds),
            host_n=run_n,
            horizon=run_t,
            design_digest=run_design.digest(),
        )
    listed = _previous_manifest_shas(out)
    fits: dict[int, dict[str, Any]] = {}
    durations: list[float] = []
    try:
        for index, seed in enumerate(run_seeds):
            final = out / "seeds" / f"seed-{seed}.jsonl"
            if final.exists():
                fits[seed] = _verify_kept_seed(
                    final, seed, pilot_spec, soft_k, run_t, fit_module, mode, listed.get(f"seeds/{final.name}")
                )
                progress.write("seed_kept", seed=seed, sha256=_sha256_file(final))
                continue
            partial = final.with_name(final.name + ".partial")
            if partial.exists():
                killed = 1
                while final.with_name(f"{final.name}.killed-{killed}").exists():
                    killed += 1
                partial.rename(final.with_name(f"{final.name}.killed-{killed}"))
                progress.write("seed_rerun_same_seed", seed=seed, killed_copy=killed)
            started = time.monotonic()
            progress.write("seed_start", seed=seed, index=index, of=len(run_seeds))
            rows_written = 0
            with partial.open("w", encoding="utf-8") as fh:

                def on_row(row: dict[str, Any], checked: list[str], _fh: io.TextIOBase = fh) -> None:
                    nonlocal rows_written
                    _fh.write(json.dumps(row, sort_keys=True, allow_nan=False) + "\n")
                    _fh.flush()
                    rows_written += 1
                    progress.write(
                        "generation",
                        seed=seed,
                        generation=row["generation"],
                        census=row["census"],
                        asexual=row["asexual"],
                        births=row["births"],
                        invariants_ok=checked,
                    )

                _rows, fit_row = _run_seed(pilot_spec, run_design, seed, run_n, run_t, fit_module, on_row, mode)
                fh.write(json.dumps(fit_row, sort_keys=True, allow_nan=False) + "\n")
                fh.flush()
                os.fsync(fh.fileno())
                rows_written += 1
            os.replace(partial, final)
            _fsync_dir(final.parent)
            fits[seed] = fit_row
            elapsed = time.monotonic() - started
            durations.append(elapsed)
            remaining = sum(1 for s in run_seeds[index + 1 :] if not (out / "seeds" / f"seed-{s}.jsonl").exists())
            end_fields: dict[str, Any] = {
                "seed": seed,
                "rows_written": rows_written,
                "seconds": round(elapsed, 3),
                "fixed_generation": fit_row["fixed_generation"],
                "lost_generation": fit_row["lost_generation"],
                "converged": fit_row["converged"],
                "eta_seconds": round(remaining * (sum(durations) / len(durations)), 1),
                "sha256": _sha256_file(final),
            }
            if mode == MODE_PILOT:
                end_fields["log_w"] = fit_row["log_w"]
            progress.write("seed_end", **end_fields)
    except Exception as exc:
        progress.write("failed", error=f"{type(exc).__name__}: {exc}", traceback=traceback.format_exc())
        for partial in sorted((out / "seeds").glob("*.partial")):
            stem = partial.name.removesuffix(".partial")
            failed = 1
            while partial.with_name(f"{stem}.failed-{failed}").exists():
                failed += 1
            partial.rename(partial.with_name(f"{stem}.failed-{failed}"))
        _atomic_write(out / "manifest.json", _json_bytes(_manifest(out, run_info)))
        raise
    _atomic_write(out / "populations.csv", _populations_csv(run_seeds, fits, mode))
    summary: dict[str, Any] = {"mode": mode, "seeds_done": len(fits), "decision_written": False}
    if mode == MODE_PILOT and set(fits) == set(pilot_spec.seeds):
        populations = [
            E1Population(
                seed=s,
                log_w=fits[s]["log_w"],
                fixed_generation=fits[s]["fixed_generation"],
                lost_generation=fits[s]["lost_generation"],
            )
            for s in sorted(fits)
        ]
        cell, passed = pilot_decision(pilot_spec, populations)
        result: dict[str, Any] = {
            "schema": RESULT_SCHEMA,
            "constants_sha256": pilot_spec.gate.constants_sha256,
            "prereg_plan_digest": pilot_spec.gate.prereg_manifest_sha256,
            "design_digest": run_design.digest(),
            "fit_sha256": fit_sha,
            "cell": cell.to_record(),
            "pilot_passed": passed,
            "on_fail": pilot_spec.on_fail,
            "max_reruns_after_fix": pilot_spec.max_reruns_after_fix,
            "confirmatory": False,
            "enters_claims": False,
        }
        result["digest"] = canonical_digest(result, prefix="jr5_realised_w_pilot_result")
        _atomic_write(out / "result.json", _json_bytes(result))
        summary.update(decision_written=True, pilot_passed=passed, ratio_ci90=cell.ratio_ci90())
        progress.write(
            "decision",
            pilot_passed=passed,
            ratio_ci90=cell.ratio_ci90(),
            excluded=len(cell.excluded_seeds),
            cap_exceeded=cell.exclusion_cap_exceeded,
        )
    body_digest = _manifest(out, run_info)["body_digest"]
    progress.write("done", seeds_done=len(fits), body_digest=body_digest)
    # Written after the last progress line, so every listed sha256 is final.
    manifest = _manifest(out, run_info)
    if manifest["body_digest"] != body_digest:
        raise PilotInvariantError("output files changed while the manifest was written.")
    _atomic_write(out / "manifest.json", _json_bytes(manifest))
    summary["body_digest"] = manifest["body_digest"]
    return summary


# --------------------------------------------------------------------- CLI


def _design_from_json(path: str) -> PopulationDesign:
    raw = _mapping(json.loads(Path(path).read_text(encoding="utf-8")), "design")
    data = dict(raw)
    data["food_patches"] = tuple(tuple(int(v) for v in p) for p in data.get("food_patches", ()))
    data["founder_windows"] = tuple(str(w) for w in data.get("founder_windows", ()))
    try:
        return PopulationDesign(**data)
    except TypeError as exc:
        raise ConfigurationError(f"design file fields do not match PopulationDesign: {exc}") from exc


def _iter_seeds(text: str | None) -> Iterator[int]:
    if not text:
        return
    for part in text.split(","):
        part = part.strip()
        if "-" in part:
            first, last = part.split("-", 1)
            yield from range(int(first), int(last) + 1)
        elif part:
            yield int(part)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m codontrace.campaigns.jr5_realised_w_pilot", description=__doc__.splitlines()[0]
    )
    parser.add_argument("--out", required=True, help="output directory (never inside docs/prereg or claimgate/data)")
    parser.add_argument("--mode", choices=(MODE_PILOT, MODE_SMOKE), default=MODE_PILOT)
    parser.add_argument("--seeds", help="smoke: seeds, e.g. 20011,20012 or 20011-20013; pilot: a subset of the block")
    parser.add_argument("--host-n", type=int, help="smoke only")
    parser.add_argument("--horizon", type=int, help="smoke only")
    parser.add_argument("--design-json", help="smoke only: a PopulationDesign as JSON")
    parser.add_argument("--root", help="repository root (default: this checkout)")
    parser.add_argument("--dry-run", action="store_true", help="print the configuration and checks, write nothing")
    args = parser.parse_args(argv)
    try:
        return _main(args)
    except ConfigurationError as exc:
        sys.stderr.write(f"refused: {exc}\n")
        return 2


def _main(args: argparse.Namespace) -> int:
    spec = load_realised_w_pilot_spec(args.root)
    seeds = list(_iter_seeds(args.seeds)) or None
    design = _design_from_json(args.design_json) if args.design_json else None
    if args.dry_run:
        base = (Path(args.root) if args.root else Path(__file__).resolve().parents[3]).resolve()
        out = check_output_dir(args.out, base)
        if args.mode == MODE_PILOT:
            chosen = check_pilot_seeds(spec, seeds if seeds is not None else list(spec.seeds))
            shown = PILOT_POPULATION_DESIGN
        else:
            chosen = check_smoke_seeds(spec, seeds or [])
            shown = design
        _module, fit_sha = load_fit(spec, base)
        try:
            pin: str = verified_pilot_design_digest(base)[0]
        except ConfigurationError as exc:
            pin = f"refused: {exc}"
        sys.stdout.write(
            json.dumps(
                {
                    "mode": args.mode,
                    "out": str(out),
                    "seeds": [chosen[0], chosen[-1], len(chosen)],
                    "spec": spec.to_record(),
                    "design": None if shown is None else shown.to_record(),
                    "design_digest": None if shown is None else shown.digest(),
                    "fit_sha256": fit_sha,
                    "design_pin": pin,
                    "runnable": shown is not None and (args.mode == MODE_SMOKE or pin == shown.digest()),
                },
                indent=1,
                sort_keys=True,
            )
            + "\n"
        )
        return 0
    summary = run_pilot(
        args.out,
        mode=args.mode,
        seeds=seeds,
        design=design,
        host_n=args.host_n,
        horizon=args.horizon,
        root=args.root,
        spec=spec,
    )
    sys.stdout.write(json.dumps(summary, sort_keys=True) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
