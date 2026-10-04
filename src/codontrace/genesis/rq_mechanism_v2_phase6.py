"""Phase-6 assay. One estimand, separate effects, and a horizon from both sides.

The public flag stays false. A reanalysis of phase 5b is not a new confirmation.
The absent census 34/30 is the id-sort rule under the birth cap. It is not retuned.
"""

from __future__ import annotations

import hashlib
import json
import math
import statistics
from collections.abc import Mapping, Sequence
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

from codontrace.errors import ConfigurationError
from codontrace.genesis.closed_loop_hp_arm01_structural_rq import STRUCT_SOFT_K
from codontrace.genesis.closed_loop_pearl_spc import PASSAGE_ABSENT
from codontrace.genesis.rq_bidirectional_timeshift_confirm import MEASUREMENT_FLOOR, infectivity
from codontrace.genesis.rq_mechanism_v2_phase4 import (
    PHASE4_CENSUS,
    PHASE4_PER_CLASS,
    WINDOW_A,
    WINDOW_B,
)
from codontrace.genesis.rq_mechanism_v2_phase5 import (
    ARM_COEVOLVE,
    ARMS,
    MAX_WORKERS,
    NO_CONFIRMATORY_SENTENCE,
    VERDICT_BLOCKED,
    VERDICT_SUPPORTED,
    _arm_rows,
    _binary_verdict,
    _load_jsonl,
    _lock_payload,
    _people,
    _statistical_verdict,
    _worker,
    assert_measurement_floor,
    assert_output_dir,
    lineage_relative_fitness,
    replay_phase5_archive,
    resolve_workers,
    run_phase5_history,
    sampling_interval,
    wilson_interval,
)

# Raised from 16 to the horizon the max-of-three-times rule already returned.
# This admits that horizon. It is not a parameter tune. Papkou et al. 2019
# PNAS (DOI 10.1073/pnas.1810402116) ran 23 host transfers and controlled
# generation time for the host, not the parasite.
PHASE6_BUDGET = 70
PHASE6_PROBE_GENERATIONS = 12
PHASE6_PROBE_PARASITE = 9807
PHASE6_PROBE_HOST = 9808
PHASE6_PROBE_DELAY = 9809
PHASE6_BURNED_PROBE = (9800, 9801, 9802, 9804, 9805, 9806)
PHASE6_SHORT_SEED = 9803
PHASE6_SEED_START = 9811
PHASE6_N = 12
PHASE6_OFFSPRING_PER_PAIR = 2
OUTPUT_PRELIM = Path("runs/rq-mechanism-v2/phase6-prelim")
OUTPUT_SHORT = Path("runs/rq-mechanism-v2/phase6-short")
OUTPUT_CONFIRM = Path("runs/rq-mechanism-v2/phase6-coevolution")
PHASE6_LOCK = Path("runs/rq-mechanism-v2/PHASE6_LOCK.md")
PHASE6_CONFIRM_LOCK = Path("runs/rq-mechanism-v2/PHASE6_CONFIRM_LOCK.md")
REANALYSIS_NOTE = Path("runs/rq-mechanism-v2/PHASE5B_REANALYSIS.md")
_PHASE5B_SUMMARY = Path("runs/rq-mechanism-v2/phase5b-coevolution/summary.json")
_USED_SEEDS = frozenset(
    {
        *range(9600, 9613),
        *range(9700, 9713),
        *range(9201, 9225),
        *range(9301, 9305),
        *range(9500, 9505),
        9099,
        9101,
        9102,
        9103,
        9104,
        9401,
    }
)


def assert_phase6_output_dir(root: Path) -> None:
    """Phase 6 does not write a previous tree."""

    assert_output_dir(root)
    resolved = root.resolve()
    for banned in (
        Path("runs/rq-mechanism-v2/phase5-coevolution"),
        Path("runs/rq-mechanism-v2/phase5-probe"),
        Path("runs/rq-mechanism-v2/phase5b-coevolution"),
        Path("runs/rq-mechanism-v2/phase4-fitness"),
        Path("runs/rq-mechanism-v2/phase4b-fitness"),
    ):
        banned_resolved = banned.resolve()
        if resolved == banned_resolved or banned_resolved in resolved.parents:
            raise ConfigurationError(f"phase-6 must not write into {banned}")


def locked_phase6_seeds() -> tuple[int, ...]:
    """Twelve unused histories. Phase-5 and phase-5b seeds are not reused."""

    count = int(PHASE6_N)
    floor = assert_measurement_floor()
    if count < floor:
        raise ConfigurationError("phase-6 history count is below MEASUREMENT_FLOOR")
    seeds = tuple(range(PHASE6_SEED_START, PHASE6_SEED_START + count))
    banned = set(_USED_SEEDS) | {
        PHASE6_PROBE_PARASITE,
        PHASE6_PROBE_HOST,
        PHASE6_PROBE_DELAY,
        PHASE6_SHORT_SEED,
        *PHASE6_BURNED_PROBE,
    }
    if len(set(seeds)) != count or (set(seeds) & banned):
        raise ConfigurationError("phase-6 seeds overlap a used history")
    if seeds[0] != 9811 or seeds[-1] != 9822:
        raise ConfigurationError("phase-6 seeds are not 9811 through 9822")
    return seeds


def _positive(value: object) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ConfigurationError("a timescale must be a positive number")
    number = float(value)
    if not math.isfinite(number) or number <= 0.0:
        raise ConfigurationError("a timescale must be positive and finite")
    return number


def choose_phase6_horizon(
    *,
    parasite_replacement: float | None,
    host_replacement: float | None,
    fitness_delay: float | None,
    budget: int = PHASE6_BUDGET,
) -> dict[str, object]:
    """Horizon from both replacement times and, when measured, the fitness delay.

    The cycle period is not three times the parasite replacement time. A missing
    delay stays missing. The horizon is not shortened to fit a budget.
    """

    if int(budget) != PHASE6_BUDGET:
        raise ConfigurationError("phase-6 budget is the registered budget")
    parasite = _positive(parasite_replacement)
    host = _positive(host_replacement)
    delay: float | None
    if fitness_delay is None:
        delay = None
    else:
        delay = _positive(fitness_delay)
    horizon = max(math.ceil(parasite), math.ceil(host))
    if delay is not None:
        horizon = max(horizon, math.ceil(delay))
    lag = max(1, int(round(parasite)))
    if lag >= horizon:
        raise ConfigurationError("primary lag does not leave a past partner inside the horizon")
    if horizon > int(budget):
        raise ConfigurationError("horizon exceeds the registered budget; it is not shortened")
    cycle_start = horizon - 2 * lag
    return {
        "budget": int(budget),
        "cycle_times_measurable": cycle_start >= 1,
        "fitness_delay": delay,
        "fitness_delay_unmeasurable": delay is None,
        "horizon": int(horizon),
        "host_replacement": host,
        "not_three_times_parasite_replacement": True,
        "parasite_replacement": parasite,
        "primary_lag": int(lag),
        "turnover_multiple_used": False,
    }


def shared_paired_estimand(
    hosts_now: Sequence[Mapping[str, object]],
    hosts_past: Sequence[Mapping[str, object]],
    parasites_now: Sequence[Mapping[str, object]],
    parasites_past: Sequence[Mapping[str, object]],
) -> dict[str, object]:
    """One paired estimand. Host and parasite effects are the two pieces that add to it.

    The other host contrast, contemporary parasites against past hosts, is a
    diagnostic. It is not added into the paired contrast.
    """

    if not hosts_now or not hosts_past or not parasites_now or not parasites_past:
        return {
            "diagnostic_host_on_contemporary_parasites": None,
            "host_effect": None,
            "paired": None,
            "parasite_effect": None,
        }
    now_now = infectivity(hosts_now, parasites_now)
    now_past = infectivity(hosts_now, parasites_past)
    past_past = infectivity(hosts_past, parasites_past)
    past_now = infectivity(hosts_past, parasites_now)
    if None in (now_now, now_past, past_past, past_now):
        return {
            "diagnostic_host_on_contemporary_parasites": None,
            "host_effect": None,
            "paired": None,
            "parasite_effect": None,
        }
    parasite_effect = float(now_now) - float(now_past)
    host_effect = float(now_past) - float(past_past)
    paired = float(now_now) - float(past_past)
    diagnostic = float(now_now) - float(past_now)
    if not math.isclose(parasite_effect + host_effect, paired, abs_tol=1e-12):
        raise ConfigurationError("host and parasite effects do not add to the paired estimand")
    return {
        "diagnostic_host_on_contemporary_parasites": diagnostic,
        "diagnostic_mixed_into_paired": False,
        "host_effect": host_effect,
        "paired": paired,
        "parasite_effect": parasite_effect,
    }


def _sign(left: float | None, right: float | None) -> int | None:
    if left is None or right is None:
        return None
    if not math.isfinite(left) or not math.isfinite(right) or left == right:
        return None
    return 1 if left > right else -1


def selection_direction(
    *,
    ancestry_fitness_a: float | None,
    ancestry_fitness_b: float | None,
    contact: float | None,
    genotype_a_present: bool,
    genotype_b_present: bool,
    infectivity_gap: float | None = None,
) -> dict[str, object]:
    """A selection direction needs both genotypes and contact. Infectivity is not enough."""

    present = bool(genotype_a_present) and bool(genotype_b_present)
    contacted = contact is not None and math.isfinite(float(contact)) and float(contact) > 0.0
    direction = _sign(ancestry_fitness_a, ancestry_fitness_b) if present and contacted else None
    return {
        "contact_ok": contacted,
        "direction": direction,
        "genotypes_present": present,
        "infectivity_used_as_selection": False,
        "infectivity_gap": infectivity_gap,
    }


def registered_oscillation(
    directions: Sequence[Mapping[str, object]],
    *,
    horizon: int,
    lag: int,
) -> dict[str, object]:
    """The locked times only. One sign change is not a continuing cycle.

    Times are horizon, horizon-lag, and horizon-2*lag when that generation
    exists. A scan of every generation is not this function.
    """

    if int(lag) < 1 or int(horizon) <= int(lag):
        raise ConfigurationError("oscillation lag is outside the horizon")
    needed = [int(horizon) - 2 * int(lag), int(horizon) - int(lag), int(horizon)]
    by_gen = {int(row["generation"]): row for row in directions}
    if len(by_gen) != len(list(directions)):
        raise ConfigurationError("duplicate generations")
    if needed[0] < 1:
        return {
            "continuing_cycle": False,
            "direction_changes": [],
            "exploratory": False,
            "one_sign_change_is_not_a_cycle": False,
            "times": needed,
            "unmeasurable": True,
        }
    signs: list[int | None] = []
    for generation in needed:
        row = by_gen.get(generation)
        if row is None or row.get("direction") is None:
            return {
                "continuing_cycle": False,
                "direction_changes": [],
                "exploratory": False,
                "one_sign_change_is_not_a_cycle": False,
                "times": needed,
                "unmeasurable": True,
            }
        if row.get("genotypes_present") is not True or row.get("contact_ok") is not True:
            return {
                "continuing_cycle": False,
                "direction_changes": [],
                "exploratory": False,
                "one_sign_change_is_not_a_cycle": False,
                "times": needed,
                "unmeasurable": True,
            }
        signs.append(int(row["direction"]))
    changes = [needed[index] for index in (1, 2) if signs[index] != signs[index - 1]]
    continuing = len(changes) >= 2 and signs[0] == signs[2] and signs[1] != signs[0]
    return {
        "continuing_cycle": continuing,
        "direction_changes": changes,
        "exploratory": False,
        "one_sign_change_is_not_a_cycle": len(changes) == 1,
        "signs": signs,
        "times": needed,
        "unmeasurable": False,
    }


def exploratory_direction_scan(directions: Sequence[int | None]) -> dict[str, object]:
    """Every current time. This cannot confirm a cycle."""

    changes = 0
    previous: int | None = None
    for direction in directions:
        if direction is None:
            continue
        if previous is not None and direction != previous:
            changes += 1
        previous = direction
    return {"confirmatory": False, "direction_changes": changes, "exploratory": True}


def absent_baseline_rule(host_ids: Sequence[str]) -> dict[str, object]:
    """Which rule produces alive 34 and 30 when names sort A before B.

    Founders are 30 and 30. The life-loop steps organisms in id order.
    ``two_fold_cost_sex`` is false, so a chamber pair places two offspring.
    The seat cap is 64, so two pairs fill the four open seats and later ids
    are not reached. Food headcount is not this rule.
    """

    if len(host_ids) != PHASE4_CENSUS:
        raise ConfigurationError("absent baseline uses the locked census of 60")
    ordered = sorted(str(item) for item in host_ids)
    room = int(STRUCT_SOFT_K) - int(PHASE4_CENSUS)
    births = {"A": 0, "B": 0}
    index = 0
    while room >= PHASE6_OFFSPRING_PER_PAIR and index + 1 < len(ordered):
        for parent in ordered[index : index + PHASE6_OFFSPRING_PER_PAIR]:
            if "-A-" in parent:
                births["A"] += 1
            elif "-B-" in parent:
                births["B"] += 1
            else:
                raise ConfigurationError("baseline id is neither host A nor host B")
        room -= PHASE6_OFFSPRING_PER_PAIR
        index += PHASE6_OFFSPRING_PER_PAIR
    return {
        "alive_A": PHASE4_PER_CLASS + births["A"],
        "alive_B": PHASE4_PER_CLASS + births["B"],
        "births_A": births["A"],
        "births_B": births["B"],
        "cap": int(STRUCT_SOFT_K),
        "founders_A": PHASE4_PER_CLASS,
        "founders_B": PHASE4_PER_CLASS,
        "offspring_per_pair": PHASE6_OFFSPRING_PER_PAIR,
        "open_seats": int(STRUCT_SOFT_K) - int(PHASE4_CENSUS),
        "order": "sorted host id",
        "rule": "id-sort chamber pairs fill the four open seats before the later name",
    }


def food_seat_symmetry(census: int = PHASE4_CENSUS, n_patches: int = 16) -> dict[str, object]:
    """Even seats are A and odd seats are B. Patch headcount is still 30 and 30."""

    if int(census) != PHASE4_CENSUS or int(n_patches) != 16:
        raise ConfigurationError("food symmetry uses the locked 60 hosts and 16 patches")
    counts = {"A": 0, "B": 0}
    per_patch = {"A": [0] * n_patches, "B": [0] * n_patches}
    for index in range(int(census)):
        letter = "A" if index % 2 == 0 else "B"
        counts[letter] += 1
        per_patch[letter][index % n_patches] += 1
    return {
        "class_counts": counts,
        "even_patches_are_only_A": all(per_patch["B"][patch] == 0 for patch in range(0, n_patches, 2)),
        "headcount_equal": counts["A"] == counts["B"] == PHASE4_PER_CLASS,
        "odd_patches_are_only_B": all(per_patch["A"][patch] == 0 for patch in range(1, n_patches, 2)),
        "patch_occupancy_A": per_patch["A"],
        "patch_occupancy_B": per_patch["B"],
    }


def fitness_kinds(
    *,
    ancestry_a: float | None,
    ancestry_b: float | None,
    current_a: float | None,
    current_b: float | None,
) -> dict[str, object]:
    """Founder-class fitness and living-window fitness stay separate."""

    ancestry = None if ancestry_a is None or ancestry_b is None else float(ancestry_a) - float(ancestry_b)
    current = None if current_a is None or current_b is None else float(current_a) - float(current_b)
    return {
        "ancestry_gap": ancestry,
        "current_genotype_gap": current,
        "current_substituted_for_ancestry": False,
    }


def pressure_contrast(
    *,
    absent_contacts: int,
    absent_births: Mapping[str, int],
    absent_deaths: Mapping[str, int],
    pressured_contacts: int,
    pressured_births: Mapping[str, int],
    pressured_deaths: Mapping[str, int],
) -> dict[str, object]:
    """Parasite pressure is the contrast against the no-parasite baseline. It is not the baseline itself."""

    return {
        "absent_contacts": int(absent_contacts),
        "baseline_is_pressure": False,
        "births_differ": dict(absent_births) != dict(pressured_births),
        "deaths_differ": dict(absent_deaths) != dict(pressured_deaths),
        "pressured_contacts": int(pressured_contacts),
    }


def reanalyze_phase5b_reversals(summary_path: Path | None = None) -> dict[str, object]:
    """Wilson interval for the archived  phase-5b reversal count. Seeds are not opened again."""

    path = _PHASE5B_SUMMARY if summary_path is None else summary_path
    payload = json.loads(path.read_text(encoding="utf-8"))
    report = payload["report"]
    claim_b = report["claim_b"]
    successes = int(claim_b["reversal_true_n"])
    n = int(claim_b["n_used"])
    if int(payload["horizon"]) != 10 or list(payload["seeds"]) != list(range(9701, 9713)):
        raise ConfigurationError("phase-5b reanalysis file is not the archived run")
    if n != 12 or successes != int(claim_b["reversal_true_n"]):
        raise ConfigurationError("phase-5b reversal count is not the archived count")
    interval = wilson_interval(successes, n)
    mean_a = report["claim_a"]["mean"]
    return {
        "analysis": "REANALYSIS",
        "claim_a_mean_archived": mean_a,
        "claim_a_verdict_archived": report["claim_a"]["verdict"],
        "fresh_confirmation": False,
        "horizon": int(payload["horizon"]),
        "n_used": n,
        "red_queen_proved": False,
        "reversal_interval": interval,
        "reversal_true_n": successes,
        "seeds": list(payload["seeds"]),
        "seeds_rerun": False,
        "source_summary": str(path),
        "wald_p_was_null": claim_b.get("interval", {}).get("p_one_sided") is None,
    }


def render_phase5b_reanalysis(result: Mapping[str, object]) -> str:
    """Note for the archived reversals. This is not a confirmatory."""

    interval = result["reversal_interval"]
    assert isinstance(interval, Mapping)
    lines = [
        "# Phase-5b reversal reanalysis",
        "",
        "This is a registered REANALYSIS of `runs/rq-mechanism-v2/phase5b-coevolution/summary.json`.",
        "Seeds 9701 through 9712 were not run again. No confirmatory history was opened.",
        "`red_queen_proved` stays false. The archived claim A mean is not rescaled.",
        "",
        f"Archived claim A mean: {result['claim_a_mean_archived']}.",
        f"Archived claim A verdict: {result['claim_a_verdict_archived']}.",
        f"Reversal count: {result['reversal_true_n']} / {result['n_used']}.",
        "The archived Wald interval had a zero standard error, a null one-sided p-value, and a null bound.",
        "That null p-value was not a p-value of 0, and the boundary was not dropped.",
        "",
        "Pre-registered null for this reanalysis: reversal probability 0.5.",
        "Interval: two-sided Wilson 95 percent, the small-n interval in Brown, Cai, and DasGupta 2001, equation (4).",
        "Directional tail: one-sided exact binomial probability at the null.",
        f"Wilson interval: [{interval['lower']}, {interval['upper']}].",
        f"Two-sided exact p: {interval['p_two_sided']}.",
        f"One-sided exact p: {interval['p_one_sided']}.",
        f"`wald_se_zero`: {interval['wald_se_zero']}. `se_zero` on the Wilson record: {interval['se_zero']}.",
        (
            "The upper bound is below 0.5, so the reversal index is on the negative side of the null."
            if float(interval["upper"]) < 0.5
            else "The upper bound is not below 0.5."
        ),
        "The continuous claim A mean stays the archived number. It is not this index.",
        "",
        "`red_queen_proved` is false.",
        "",
    ]
    return "\n".join(lines)


def render_phase6_lock(design: Mapping[str, object], *, code_commit: str) -> str:
    """Lock text. The required sentence is the first sentence and the last sentence."""

    seeds = [int(seed) for seed in design["seeds"]]  # type: ignore[index]
    payload = {
        "budget": int(design["budget"]),
        "fitness_delay": design["fitness_delay"],
        "fitness_delay_unmeasurable": bool(design["fitness_delay_unmeasurable"]),
        "horizon": int(design["horizon"]),
        "host_replacement": design["host_replacement"],
        "importance_bound": None,
        "n": len(seeds),
        "parasite_replacement": design["parasite_replacement"],
        "primary_lag": int(design["primary_lag"]),
        "seeds": seeds,
        "supported_forbidden": True,
        "turnover_multiple_used": False,
        "workers": MAX_WORKERS,
    }
    block = json.dumps(payload, indent=2, sort_keys=True)
    lines = [
        "# Phase-6 lock",
        "",
        NO_CONFIRMATORY_SENTENCE,
        "",
        f"Code commit: `{code_commit}`.",
        "Nothing in this lock is a confirmatory claim mean.",
        "Phase-5b seeds 9701 through 9712 are not reused. Seeds 9601 through 9612 are not reused.",
        "",
        "## Estimand",
        "",
        "Every arm is scored with the same paired estimand:",
        "`I(hosts at the horizon, parasites at the horizon) - I(hosts at horizon - lag, parasites at horizon - lag)`.",
        "Host effect, parasites held at the past generation:",
        "`I(hosts at the horizon, parasites at horizon - lag) - I(hosts at horizon - lag, parasites at horizon - lag)`.",
        "Parasite effect, hosts held at the horizon:",
        "`I(hosts at the horizon, parasites at the horizon) - I(hosts at the horizon, parasites at horizon - lag)`.",
        "Those two effects add to the paired estimand. The diagnostic host contrast on contemporary parasites is not added in.",
        "",
        "## Oscillation",
        "",
        "A direction of selection is the sign of ancestry fitness of genotypes that are both present, on a generation with contact pressure.",
        "An infectivity gap alone is not that direction.",
        "The registered times are the horizon, one lag earlier, and two lags earlier, when two lags fit.",
        "One sign change is not a continuing cycle. A scan of every generation stays exploratory.",
        "`red_queen_proved` is not set from this criterion. Importance is undeclared.",
        "",
        "## Horizon",
        "",
        "The horizon is the maximum of the parasite replacement time, the host replacement time,",
        "and the fitness-response delay when that delay was measured.",
        "It is not three times the parasite replacement time.",
        f"Parasite replacement: {design['parasite_replacement']}.",
        f"Host replacement: {design['host_replacement']}.",
        f"Fitness delay: {design['fitness_delay']}. Unmeasurable: {design['fitness_delay_unmeasurable']}.",
        f"Primary lag: {design['primary_lag']}.",
        f"Horizon: {design['horizon']} generations. Budget: {design['budget']}. The horizon was not shortened.",
        f"n: {len(seeds)}.",
        f"Seeds: {seeds[0]} through {seeds[-1]} ({', '.join(str(seed) for seed in seeds)}).",
        "",
        "Importance for this estimand is undeclared. SUPPORTED is forbidden.",
        f"`MEASUREMENT_FLOOR` stays {int(MEASUREMENT_FLOOR)} and is not lowered.",
        "CPU workers at most 7.",
        f"Output: `{OUTPUT_CONFIRM}`.",
        "",
        "```json",
        block,
        "```",
        "",
        NO_CONFIRMATORY_SENTENCE,
        "",
    ]
    return "\n".join(lines)


def replacement_time(births: Sequence[int], censuses: Sequence[int]) -> dict[str, object]:
    """Census over mean births. A zero birth mean is unmeasurable, not a zero time."""

    if not births or not censuses or len(births) != len(censuses):
        raise ConfigurationError("replacement time needs paired birth and census rows")
    if any(int(item) < 0 for item in births) or any(int(item) < 0 for item in censuses):
        raise ConfigurationError("birth and census counts cannot be negative")
    mean_births = float(statistics.fmean(int(item) for item in births))
    mean_census = float(statistics.fmean(int(item) for item in censuses))
    if mean_births <= 0.0 or mean_census <= 0.0:
        return {"measurable": False, "mean_births": mean_births, "mean_census": mean_census, "replacement": None}
    return {
        "measurable": True,
        "mean_births": mean_births,
        "mean_census": mean_census,
        "replacement": mean_census / mean_births,
    }


def fitness_response_delay(
    absent_signs: Sequence[int | None],
    pressured_signs: Sequence[int | None],
) -> dict[str, object]:
    """First generation where parasite pressure changes the birth-rank sign. Missing stays missing."""

    if len(absent_signs) != len(pressured_signs) or not absent_signs:
        raise ConfigurationError("delay series must be paired and non-empty")
    for index, (base, pressed) in enumerate(zip(absent_signs, pressured_signs, strict=True), start=1):
        if base is None or pressed is None:
            continue
        if int(pressed) != int(base):
            return {"delay": index, "measurable": True}
    return {"delay": None, "measurable": False}


def phase6_worker_cap(requested: int | None) -> int:
    """Accept 7. Reject 8. The phase-2 cap is a different module."""

    return resolve_workers(requested)



def _birth_census(path: Path) -> dict[str, object]:
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    host_births = []
    host_census = []
    parasite_births = []
    parasite_census = []
    signs: list[int | None] = []
    for row in rows:
        births = row.get("host_births")
        host_births.append(len(births) if isinstance(births, list) else 0)
        hosts = row.get("hosts")
        host_census.append(len(hosts) if isinstance(hosts, list) else 0)
        parasite_births.append(int(row.get("parasite_births") or 0))
        parasite_census.append(int(row.get("parasite_census") or 0))
        if not isinstance(births, list):
            signs.append(None)
            continue
        a = 0
        b = 0
        for item in births:
            if not isinstance(item, dict):
                continue
            parent = str(item.get("parent_id") or "")
            if "-A-" in parent:
                a += 1
            elif "-B-" in parent:
                b += 1
        signs.append(None if a == b else (1 if a > b else -1))
    return {
        "host_births": host_births,
        "host_census": host_census,
        "parasite_births": parasite_births,
        "parasite_census": parasite_census,
        "signs": signs,
    }


def render_phase6_confirm_lock(design: Mapping[str, object], *, code_commit: str) -> str:
    """Confirm lock. The first sentence is the required sentence. No claim mean is included."""

    seeds = [int(seed) for seed in design["seeds"]]  # type: ignore[index]
    payload = {
        "budget": int(design["budget"]),
        "fitness_delay": design["fitness_delay"],
        "fitness_delay_unmeasurable": bool(design["fitness_delay_unmeasurable"]),
        "horizon": int(design["horizon"]),
        "host_replacement": design["host_replacement"],
        "importance_bound": None,
        "measurement_floor": int(MEASUREMENT_FLOOR),
        "n": len(seeds),
        "parasite_replacement": design["parasite_replacement"],
        "primary_lag": int(design["primary_lag"]),
        "seeds": seeds,
        "supported_forbidden": True,
        "turnover_multiple_used": False,
        "workers": MAX_WORKERS,
    }
    block = json.dumps(payload, indent=2, sort_keys=True)
    lines = [
        NO_CONFIRMATORY_SENTENCE,
        "",
        "# Phase-6 confirmatory lock",
        "",
        f"Code commit before this lock: `{code_commit}`.",
        "Nothing in this lock is a confirmatory claim mean.",
        "Phase-5b seeds 9701 through 9712 are not reused. Seeds 9601 through 9612 are not reused.",
        "The horizon was not recomputed from a new probe.",
        "",
        "## Budget",
        "",
        "The budget moves from 16 to 70 so the pre-registered maximum of the parasite replacement time,",
        "the host replacement time, and the fitness-response delay can run.",
        "It is not a parameter tune. Seeds, lag, thresholds, and population parameters are unchanged.",
        "Papkou et al. 2019, Proceedings of the National Academy of Sciences, DOI 10.1073/pnas.1810402116,",
        "ran 23 host transfers and controlled generation time for the host, not the parasite.",
        "The 2010 Caenorhabditis elegans and Bacillus thuringiensis coevolution experiment, PMC2867683,",
        "used 48 host generations.",
        "Brockhurst and Koskella 2013, Trends in Ecology and Evolution, time-shift the interaction over evolutionary time,",
        "not over a budget shorter than one host replacement.",
        "The horizon is not shortened to 16.",
        "`PHASE6_LOCK.md` still records the refusal under the old budget.",
        "",
        "## Estimand",
        "",
        "Every arm is scored with the same paired estimand:",
        "`I(hosts at the horizon, parasites at the horizon) - I(hosts at horizon - lag, parasites at horizon - lag)`.",
        "Host effect, parasites held at the past generation:",
        "`I(hosts at the horizon, parasites at horizon - lag) - I(hosts at horizon - lag, parasites at horizon - lag)`.",
        "Parasite effect, hosts held at the horizon:",
        "`I(hosts at the horizon, parasites at the horizon) - I(hosts at the horizon, parasites at horizon - lag)`.",
        "Those two effects add to the paired estimand. The diagnostic host contrast on contemporary parasites is not added in.",
        "The score is `infectivity` on `replay_archived_contact` with evolution, reproduction, and mutation off.",
        "",
        "## Oscillation",
        "",
        "A direction of selection is the sign of ancestry fitness of genotypes that are both present, on a generation with contact pressure.",
        "An infectivity gap alone is not that direction.",
        "The registered times are the horizon, one lag earlier, and two lags earlier, when two lags fit.",
        "One sign change is not a continuing cycle. A scan of every generation stays exploratory.",
        "`red_queen_proved` is not set from this criterion. Importance is undeclared.",
        "",
        "## Horizon",
        "",
        "The horizon is the maximum of the parasite replacement time, the host replacement time,",
        "and the fitness-response delay when that delay was measured.",
        "It is not three times the parasite replacement time.",
        f"Parasite replacement: {design['parasite_replacement']}.",
        f"Host replacement: {design['host_replacement']}.",
        f"Fitness delay: {design['fitness_delay']}. Unmeasurable: {design['fitness_delay_unmeasurable']}.",
        f"Primary lag: {design['primary_lag']}.",
        f"Horizon: {design['horizon']} generations. Budget: {design['budget']}. The horizon was not shortened.",
        f"n: {len(seeds)}.",
        f"Seeds: {seeds[0]} through {seeds[-1]} ({', '.join(str(seed) for seed in seeds)}).",
        "",
        "Importance for this estimand is undeclared. SUPPORTED is forbidden.",
        f"`MEASUREMENT_FLOOR` stays {int(MEASUREMENT_FLOOR)} and is not lowered.",
        "CPU workers at most 7. Reject 8.",
        f"Output: `{OUTPUT_CONFIRM}`.",
        "One-shot and resume are compared on `scientific_body` before `COMPLETE`.",
        "",
        "```json",
        block,
        "```",
        "",
        NO_CONFIRMATORY_SENTENCE,
        "",
    ]
    return "\n".join(lines)


def _ancestry(host_id: str, founders: Mapping[str, str], parent: Mapping[str, str]) -> str | None:
    seen: set[str] = set()
    current: str | None = host_id
    while current is not None and current not in founders:
        if current in seen or current not in parent:
            return None
        seen.add(current)
        current = parent[current]
    if current is None:
        return None
    return founders[current]


def _coevolve_directions(rows: Sequence[Mapping[str, object]]) -> tuple[list[dict[str, object]], str | None]:
    """Ancestry fitness by founder class. A broken parent chain is an accounting error."""

    try:
        mapped = _arm_rows(rows, ARM_COEVOLVE)
    except ConfigurationError as exc:
        return [], str(exc)
    first = mapped.get(1)
    if first is None:
        return [], "coevolve generation 1 is missing"
    start_hosts = first.get("start_hosts")
    if not isinstance(start_hosts, list) or not start_hosts:
        return [], "founders missing"
    founders: dict[str, str] = {}
    for host in start_hosts:
        if not isinstance(host, dict) or not isinstance(host.get("id"), str) or not isinstance(host.get("window"), str):
            return [], "founder id missing"
        if host["window"] not in (WINDOW_A, WINDOW_B):
            return [], "founder window is not a locked genotype"
        founders[str(host["id"])] = str(host["window"])
    parent: dict[str, str] = {}
    directions: list[dict[str, object]] = []
    for generation in sorted(mapped):
        row = mapped[generation]
        if str(row.get("passage")) == PASSAGE_ABSENT:
            return [], "assay leakage: absent passage in the confirmatory"
        start = row.get("start_hosts")
        births = row.get("host_births")
        deaths = row.get("host_deaths")
        if not isinstance(start, list) or not isinstance(births, list) or not isinstance(deaths, list):
            return [], f"generation {generation} is missing hosts, births, or deaths"
        labels: dict[str, str] = {}
        for host in start:
            if not isinstance(host, dict) or not isinstance(host.get("id"), str):
                return [], f"generation {generation} host id missing"
            label = _ancestry(str(host["id"]), founders, parent)
            if label is None:
                return [], f"generation {generation} host {host['id']} has no parent chain"
            labels[str(host["id"])] = label
        birth_rows: list[dict[str, object]] = []
        for birth in births:
            if not isinstance(birth, dict):
                return [], f"generation {generation} birth is not a record"
            parent_id = birth.get("parent_id")
            child = birth.get("id")
            if not isinstance(parent_id, str) or not isinstance(child, str):
                return [], f"generation {generation} birth id missing"
            if parent_id in labels:
                ancestry = labels[parent_id]
            else:
                ancestry = _ancestry(parent_id, founders, parent)
            if ancestry is None:
                return [], f"generation {generation} birth parent {parent_id} has no parent chain"
            birth_rows.append({"parent_window": ancestry})
            parent[child] = parent_id
        fit = lineage_relative_fitness([labels[host_id] for host_id in (str(host["id"]) for host in start if isinstance(host, dict))], birth_rows, deaths)
        by = fit["by_window"] if fit["measured"] else None
        ancestry_a = None if not isinstance(by, dict) or WINDOW_A not in by else float(by[WINDOW_A])
        ancestry_b = None if not isinstance(by, dict) or WINDOW_B not in by else float(by[WINDOW_B])
        contacts = row.get("contacts")
        if isinstance(contacts, bool) or not isinstance(contacts, int):
            return [], f"generation {generation} contacts are not an integer"
        directed = selection_direction(
            ancestry_fitness_a=ancestry_a,
            ancestry_fitness_b=ancestry_b,
            contact=float(contacts),
            genotype_a_present=WINDOW_A in labels.values(),
            genotype_b_present=WINDOW_B in labels.values(),
        )
        directions.append({"generation": int(generation), **directed})
    return directions, None


def score_phase6_archive(rows: Sequence[Mapping[str, object]], *, lag: int, horizon: int) -> dict[str, object]:
    """Paired estimand on every arm, and the registered oscillation on coevolve."""

    if any(row.get("red_queen_proved") is True for row in rows):
        return {
            "accounting_error": "red_queen_proved was set true inside an archive row",
            "red_queen_proved": False,
        }
    paired: dict[str, object] = {}
    for arm in ARMS:
        try:
            mapped = _arm_rows(rows, arm)
        except ConfigurationError as exc:
            return {"accounting_error": str(exc), "red_queen_proved": False}
        now = mapped.get(int(horizon))
        past = mapped.get(int(horizon) - int(lag))
        blank = {
            "diagnostic_host_on_contemporary_parasites": None,
            "host_effect": None,
            "paired": None,
            "parasite_effect": None,
        }
        if now is None or past is None:
            paired[arm] = blank
            continue
        hosts_now = _people(now, "hosts")
        hosts_past = _people(past, "hosts")
        parasites_now = _people(now, "parasites")
        parasites_past = _people(past, "parasites")
        if hosts_now is None or hosts_past is None or parasites_now is None or parasites_past is None:
            paired[arm] = blank
            continue
        paired[arm] = shared_paired_estimand(hosts_now, hosts_past, parasites_now, parasites_past)
    directions, error = _coevolve_directions(rows)
    if error:
        return {"accounting_error": error, "paired": paired, "red_queen_proved": False}
    return {
        "accounting_error": None,
        "exploratory_scan": exploratory_direction_scan([row.get("direction") for row in directions]),  # type: ignore[list-item]
        "oscillation": registered_oscillation(directions, horizon=int(horizon), lag=int(lag)),
        "paired": paired,
        "red_queen_proved": False,
    }


def _archive_complete(path: Path, horizon: int) -> bool:
    rows = _load_jsonl(path)
    if any(row.get("red_queen_proved") is True for row in rows):
        return False
    for arm in ARMS:
        mapped = _arm_rows(rows, arm)
        if set(mapped) != set(range(1, int(horizon) + 1)):
            return False
    return True


def _phase6_report(scored: Sequence[Mapping[str, object]], seeds: Sequence[int]) -> dict[str, object]:
    """Interval verdicts. Importance stays undeclared, so SUPPORTED is refused."""

    paired_values: list[float] = []
    for row in scored:
        arm = row["paired"]
        if not isinstance(arm, Mapping):
            continue
        coevolve = arm.get(ARM_COEVOLVE)
        if isinstance(coevolve, Mapping) and isinstance(coevolve.get("paired"), (int, float)) and not isinstance(coevolve.get("paired"), bool):
            paired_values.append(float(coevolve["paired"]))
    floor = assert_measurement_floor()
    if len(scored) < floor or len(paired_values) < floor:
        paired_verdict = VERDICT_BLOCKED
        paired_interval: dict[str, object] | None = sampling_interval(paired_values) if len(paired_values) >= 2 else None
    else:
        paired_interval = sampling_interval(paired_values)
        paired_verdict = _statistical_verdict(paired_interval, None)
    measurable = [row for row in scored if isinstance(row.get("oscillation"), Mapping) and row["oscillation"].get("unmeasurable") is False]
    continuing = [
        row
        for row in measurable
        if isinstance(row.get("oscillation"), Mapping) and row["oscillation"].get("continuing_cycle") is True
    ]
    if len(measurable) < floor:
        oscillation_verdict = VERDICT_BLOCKED
        oscillation_interval = None
    else:
        oscillation_interval = wilson_interval(len(continuing), len(measurable))
        oscillation_verdict = _binary_verdict(oscillation_interval, None)
    if paired_verdict == VERDICT_SUPPORTED or oscillation_verdict == VERDICT_SUPPORTED:
        raise ConfigurationError("SUPPORTED is forbidden while importance is undeclared")
    return {
        "continuing_cycle_n": len(continuing),
        "importance_bound": None,
        "n_measurable_oscillation": len(measurable),
        "n_paired": len(paired_values),
        "n_used": len(scored),
        "oscillation_interval": oscillation_interval,
        "oscillation_verdict": oscillation_verdict,
        "paired_interval": paired_interval,
        "paired_verdict": paired_verdict,
        "red_queen_proved": False,
        "seeds_scored": [int(row["seed"]) for row in scored],
        "supported_forbidden": True,
    }


def execute_phase6(lock_path: Path, root: Path | None = None) -> dict[str, object]:
    """Run the locked seeds at the locked horizon. Do not open a new probe or add a seed."""

    target = OUTPUT_CONFIRM if root is None else root
    assert_phase6_output_dir(target)
    text = lock_path.read_text(encoding="utf-8")
    if not text.startswith(NO_CONFIRMATORY_SENTENCE):
        raise ConfigurationError("phase-6 confirm lock does not open with the required sentence")
    payload = _lock_payload(text)
    seeds = locked_phase6_seeds()
    if [int(seed) for seed in payload["seeds"]] != list(seeds):
        raise ConfigurationError("phase-6 lock seeds are not 9811 through 9822")
    if int(payload["budget"]) != PHASE6_BUDGET:
        raise ConfigurationError("phase-6 lock budget is not the registered budget")
    if int(payload["n"]) != len(seeds) or int(payload["workers"]) != MAX_WORKERS:
        raise ConfigurationError("phase-6 lock n or workers do not match the registration")
    if payload.get("importance_bound") is not None or payload.get("supported_forbidden") is not True:
        raise ConfigurationError("phase-6 importance is undeclared; SUPPORTED stays forbidden")
    if int(payload.get("measurement_floor", 0)) != int(MEASUREMENT_FLOOR):
        raise ConfigurationError("phase-6 must not lower MEASUREMENT_FLOOR")
    design = choose_phase6_horizon(
        parasite_replacement=payload["parasite_replacement"],  # type: ignore[arg-type]
        host_replacement=payload["host_replacement"],  # type: ignore[arg-type]
        fitness_delay=payload["fitness_delay"],  # type: ignore[arg-type]
    )
    if int(payload["horizon"]) != int(design["horizon"]) or int(payload["primary_lag"]) != int(design["primary_lag"]):
        raise ConfigurationError("phase-6 lock horizon is not the registered rule")
    if int(design["horizon"]) > int(design["budget"]):
        raise ConfigurationError("horizon exceeds the registered budget; it is not shortened")
    if (target / "by_seed").exists():
        raise ConfigurationError("phase-6 confirmatory already exists; a seed is not replaced")
    target.mkdir(parents=True, exist_ok=True)
    horizon = int(design["horizon"])
    lag = int(design["primary_lag"])
    workers = resolve_workers(min(MAX_WORKERS, len(seeds)))
    payloads = [
        {"arms": list(ARMS), "compare_one_shot": True, "generations": horizon, "root": str(target), "seed": seed}
        for seed in seeds
    ]
    outcomes: list[dict[str, object]] = []
    with ProcessPoolExecutor(max_workers=workers) as pool:
        futures = [pool.submit(_worker, item) for item in payloads]
        for future in as_completed(futures):
            outcome = future.result()
            outcomes.append(outcome)
            if outcome["failed"]:
                (target / "STOP").write_text(str(outcome["failed"]) + "\n", encoding="utf-8")
    outcomes.sort(key=lambda item: int(item["seed"]))
    failed = [item for item in outcomes if item["failed"]]
    audits: list[dict[str, object]] = []
    for seed in seeds:
        seed_dir = target / "by_seed" / f"seed{seed}"
        archive = seed_dir / "archive.jsonl"
        if not archive.is_file():
            continue
        complete_flag = (seed_dir / "COMPLETE").is_file()
        reason_flag = (seed_dir / "REASON.txt").is_file()
        try:
            complete = _archive_complete(archive, horizon)
        except ConfigurationError as exc:
            complete = False
            audits.append({"error": str(exc), "seed": seed})
            failed.append({"failed": f"accounting:{exc}", "seed": seed})
            continue
        if complete_flag and (reason_flag or not complete):
            bug = "false-complete"
            audits.append({"error": bug, "seed": seed})
            failed.append({"failed": bug, "seed": seed})
            if not reason_flag:
                (seed_dir / "REASON.txt").write_text(bug + "\n", encoding="utf-8")
            (target / "STOP").write_text(bug + "\n", encoding="utf-8")
        elif complete and not complete_flag:
            bug = "missing-complete"
            audits.append({"error": bug, "seed": seed})
            failed.append({"failed": bug, "seed": seed})
    replays: list[dict[str, object]] = []
    for seed in seeds:
        archive = target / "by_seed" / f"seed{seed}" / "archive.jsonl"
        if archive.is_file():
            replays.append({"replay": replay_phase5_archive(archive), "seed": seed})
    replay_matched = bool(replays) and all(bool(item["replay"]["matched"]) for item in replays)  # type: ignore[index]
    if replays and not replay_matched:
        (target / "STOP").write_text("replay-mismatch\n", encoding="utf-8")
        if not any(item["failed"] == "replay-mismatch" for item in failed):
            failed.append({"failed": "replay-mismatch", "seed": None})
    scored: list[dict[str, object]] = []
    for seed in seeds:
        archive = target / "by_seed" / f"seed{seed}" / "archive.jsonl"
        seed_dir = target / "by_seed" / f"seed{seed}"
        if not archive.is_file():
            continue
        try:
            complete = _archive_complete(archive, horizon)
        except ConfigurationError as exc:
            audits.append({"error": str(exc), "seed": seed})
            failed.append({"failed": f"accounting:{exc}", "seed": seed})
            continue
        if not complete:
            continue
        rows = _load_jsonl(archive)
        scored_seed = score_phase6_archive(rows, lag=lag, horizon=horizon)
        scored_seed["seed"] = seed
        if scored_seed.get("accounting_error"):
            bug = f"accounting:{scored_seed['accounting_error']}"
            audits.append({"error": bug, "seed": seed})
            failed.append({"failed": bug, "seed": seed})
            (seed_dir / "REASON.txt").write_text(bug + "\n", encoding="utf-8")
            (target / "STOP").write_text(bug + "\n", encoding="utf-8")
            continue
        births = 0
        contacts = 0
        for row in rows:
            if str(row.get("arm")) != ARM_COEVOLVE:
                continue
            births += int(row.get("parasite_births") or 0) + len(row.get("host_births") or [])
            contacts += int(row.get("contacts") or 0)
        if births == 0 or contacts == 0:
            bug = "instrument-cannot-move"
            audits.append({"error": bug, "seed": seed})
            failed.append({"failed": bug, "seed": seed})
            (seed_dir / "REASON.txt").write_text(bug + "\n", encoding="utf-8")
            (target / "STOP").write_text(bug + "\n", encoding="utf-8")
            continue
        scored.append(scored_seed)
    report = _phase6_report(scored, seeds)
    if report["red_queen_proved"] is not False:
        raise ConfigurationError("red_queen_proved is not set by hand")
    stopped = None
    if failed or not replay_matched:
        stopped = failed[0]["failed"] if failed else "replay-mismatch"
    summary: dict[str, object] = {
        "audits": audits,
        "budget": int(design["budget"]),
        "by_seed": scored,
        "failed": failed,
        "horizon": horizon,
        "n_locked": len(seeds),
        "n_used": report["n_used"],
        "one_shot_vs_resume": "matched on scientific_body inside each history before COMPLETE" if not failed and replay_matched else None,
        "primary_lag": lag,
        "red_queen_proved": False,
        "replay": replays,
        "replay_matched": replay_matched,
        "report": report,
        "seeds": list(seeds),
        "stopped": stopped,
        "workers": workers,
    }
    summary["summary_sha256"] = hashlib.sha256(
        json.dumps({key: value for key, value in summary.items() if key != "summary_sha256"}, sort_keys=True).encode("utf-8")
    ).hexdigest()
    (target / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return summary


def execute_phase6_prelim(root: Path | None = None) -> dict[str, object]:
    """Three unused probe seeds. No confirmatory seed and no claim mean."""

    target = OUTPUT_PRELIM if root is None else root
    assert_phase6_output_dir(target)
    if (target / "by_seed").exists():
        raise ConfigurationError("phase-6 prelim already exists; a seed is not replaced")
    jobs = (
        (PHASE6_PROBE_PARASITE, None, "parasite"),
        (PHASE6_PROBE_HOST, PASSAGE_ABSENT, "host"),
        (PHASE6_PROBE_DELAY, None, "delay"),
    )
    outcomes = []
    for seed, passage, _name in jobs:
        outcomes.append(
            run_phase5_history(
                seed,
                str(target),
                PHASE6_PROBE_GENERATIONS,
                arms=(ARM_COEVOLVE,),
                compare_one_shot=False,
                passage_override=passage,
            )
        )
    failed = [item for item in outcomes if item["failed"]]
    summary: dict[str, object] = {"failed": failed, "red_queen_proved": False, "seeds": [item[0] for item in jobs]}
    if not failed:
        parasite = _birth_census(target / "by_seed" / f"seed{PHASE6_PROBE_PARASITE}" / "archive.jsonl")
        host = _birth_census(target / "by_seed" / f"seed{PHASE6_PROBE_HOST}" / "archive.jsonl")
        delay_rows = _birth_census(target / "by_seed" / f"seed{PHASE6_PROBE_DELAY}" / "archive.jsonl")
        parasite_time = replacement_time(parasite["parasite_births"], parasite["parasite_census"])  # type: ignore[arg-type]
        host_time = replacement_time(host["host_births"], host["host_census"])  # type: ignore[arg-type]
        delay = fitness_response_delay(host["signs"], delay_rows["signs"])  # type: ignore[arg-type]
        summary["parasite_turnover"] = parasite_time
        summary["host_turnover"] = host_time
        summary["fitness_delay"] = delay
        if parasite_time["measurable"] and host_time["measurable"]:
            try:
                summary["design"] = choose_phase6_horizon(
                    parasite_replacement=parasite_time["replacement"],  # type: ignore[arg-type]
                    host_replacement=host_time["replacement"],  # type: ignore[arg-type]
                    fitness_delay=delay["delay"],  # type: ignore[arg-type]
                )
                summary["design_error"] = None
            except ConfigurationError as exc:
                summary["design"] = None
                summary["design_error"] = str(exc)
        else:
            summary["design"] = None
            summary["design_error"] = "a replacement time is unmeasurable"
    target.mkdir(parents=True, exist_ok=True)
    (target / "prelim_summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return summary


def execute_phase6_short(root: Path | None = None) -> dict[str, object]:
    """One unused seed, two generations, one-shot replay, then the archive replay."""

    target = OUTPUT_SHORT if root is None else root
    assert_phase6_output_dir(target)
    if (target / "by_seed").exists():
        raise ConfigurationError("phase-6 short run already exists; a seed is not replaced")
    outcome = run_phase5_history(
        PHASE6_SHORT_SEED,
        str(target),
        2,
        arms=(ARM_COEVOLVE, "adaptation_cut", "constant_parasite"),
        compare_one_shot=True,
    )
    replay = None
    if not outcome["failed"]:
        replay = replay_phase5_archive(target / "by_seed" / f"seed{PHASE6_SHORT_SEED}" / "archive.jsonl")
        if not replay["matched"]:
            outcome = dict(outcome)
            outcome["failed"] = "replay-mismatch"
            (target / "STOP").write_text("replay-mismatch\n", encoding="utf-8")
    summary = {"failed": outcome["failed"], "red_queen_proved": False, "replay": replay, "seed": PHASE6_SHORT_SEED}
    target.mkdir(parents=True, exist_ok=True)
    (target / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return summary



__all__ = [
    "MEASUREMENT_FLOOR",
    "OUTPUT_CONFIRM",
    "PHASE6_BUDGET",
    "PHASE6_CONFIRM_LOCK",
    "PHASE6_LOCK",
    "PHASE6_N",
    "WINDOW_A",
    "WINDOW_B",
    "absent_baseline_rule",
    "assert_phase6_output_dir",
    "choose_phase6_horizon",
    "execute_phase6",
    "execute_phase6_prelim",
    "execute_phase6_short",
    "render_phase6_confirm_lock",
    "score_phase6_archive",
    "exploratory_direction_scan",
    "fitness_kinds",
    "fitness_response_delay",
    "food_seat_symmetry",
    "locked_phase6_seeds",
    "phase6_worker_cap",
    "pressure_contrast",
    "reanalyze_phase5b_reversals",
    "registered_oscillation",
    "render_phase5b_reanalysis",
    "render_phase6_lock",
    "replacement_time",
    "selection_direction",
    "shared_paired_estimand",
]
