"""Engine-contact-backed matching-allele calibration, not the full life loop.

The engine supplies the infection matrix. An explicit Wright-Fisher reference
model supplies reproduction; it does NOT replace Genesis birth or energy
accounting. A positive calibration says the detector works in this model,
not that the unmodified life-loop engine exhibits Red Queen dynamics.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import random
import statistics
import sys
import threading
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from codontrace.dynvalues import same_float
from codontrace.errors import ConfigurationError
from codontrace.genesis.rq_bidirectional_timeshift import replay_archived_contact
from codontrace.genesis.rq_bidirectional_timeshift_confirm import infectivity, student_t_ppf
from codontrace.genesis.rq_mechanism_v2_phase5 import replay_phase5_archive, run_phase5_history
from codontrace.genesis.rq_reciprocal_validity import matrix_margins

ARMS = ("coevolve", "neutral", "host_selection_cut", "parasite_selection_cut")
SCHEMA = "rq-controlled-benchmark/1"


@dataclass(frozen=True)
class Design:
    """Fixed calibration budget. Defaults are specified before measurement."""

    seeds: tuple[int, ...] = tuple(range(10101, 10113))
    population: int = 128
    generations: int = 300
    burn_in: int = 30
    mutation: float = 0.005
    host_selection: float = 0.6
    parasite_selection: float = 0.6
    hysteresis: float = 0.1
    minimum_coupling_effect: float = 0.0001
    alpha_family: float = 0.05

    def validate(self) -> None:
        if not self.seeds or len(set(self.seeds)) != len(self.seeds):
            raise ConfigurationError("seeds must be nonempty and unique")
        if any(isinstance(s, bool) or not isinstance(s, int) or s < 0 for s in self.seeds):
            raise ConfigurationError("seeds must be nonnegative integers")
        for value in (self.population, self.generations, self.burn_in):
            if isinstance(value, bool) or not isinstance(value, int):
                raise ConfigurationError("population and generation counts must be integers")
        if self.population < 16 or not 0 <= self.burn_in < self.generations - 2:
            raise ConfigurationError("invalid population or generation budget")
        real = (self.mutation, self.host_selection, self.parasite_selection,
                self.hysteresis, self.minimum_coupling_effect, self.alpha_family)
        if any(isinstance(x, bool) or not math.isfinite(x) for x in real):
            raise ConfigurationError("parameters must be finite real numbers")
        if not 0 <= self.mutation < 0.5 or not 0 < self.hysteresis < 0.5:
            raise ConfigurationError("invalid mutation or hysteresis")
        if not 0 <= self.host_selection <= 4 or not 0 <= self.parasite_selection <= 4:
            raise ConfigurationError("selection coefficients must lie in [0,4]")
        if self.minimum_coupling_effect < 0 or not 0 < self.alpha_family < 1:
            raise ConfigurationError("invalid effect bound or alpha")


def stream(seed: int, generation: int, species: str) -> random.Random:
    """Independent histories/species; common random numbers across paired arms."""
    digest = hashlib.sha256(f"{SCHEMA}/{seed}/{generation}/{species}".encode()).digest()
    return random.Random(int.from_bytes(digest, "big"))


def contact_matrix() -> tuple[list[list[float]], list[dict[str, Any]]]:
    """Read four real engine contact assays and verify debit/loss consistency."""
    windows = ("000000", "111111")
    matrix: list[list[float]] = []
    evidence: list[dict[str, Any]] = []
    for i, host in enumerate(windows):
        values = []
        for j, parasite in enumerate(windows):
            result = replay_archived_contact(
                [{"id": "calibration-host", "window": host, "runtime_atp": 48.0}],
                [{"unit_id": "calibration-parasite", "window": parasite, "energy": 1.0}],
                atp_override=48.0,
            )
            value = result["infectivity"]
            if value is None or not 0 <= same_float(value) <= 1:
                raise ConfigurationError("unmeasurable or invalid engine contact cell")
            if result["contacts"] != 1 or not math.isclose(same_float(result["debit"]), same_float(result["loss"]), abs_tol=1e-9):
                raise ConfigurationError("engine contact energy witness does not close")
            if result["archive_mutated"] or result["evolution"] or result["reproduction"]:
                raise ConfigurationError("measurement assay changed archived evolution state")
            values.append(same_float(value))
            evidence.append(dict(host_type=i, parasite_type=j, **result))
        matrix.append(values)
    if not matrix[0][0] > matrix[0][1] or not matrix[1][1] > matrix[1][0]:
        raise ConfigurationError("engine matrix is not a matching-allele interaction")
    return matrix, evidence


def selected_frequency(frequency: float, fitness_zero: float, fitness_one: float, mutation: float) -> float:
    """Haploid viability/fecundity selection followed by symmetric mutation."""
    denominator = (1-frequency)*fitness_zero + frequency*fitness_one
    if denominator <= 0 or not math.isfinite(denominator):
        raise ConfigurationError("invalid reproductive fitness")
    selected = frequency*fitness_one/denominator
    return mutation+(1-2*mutation)*selected


def transitions(h: float, p: float, matrix: list[list[float]], design: Design, arm: str) -> dict[str, float]:
    """Expected fitness before sampling; negative host, positive parasite effect."""
    if arm not in ARMS:
        raise ConfigurationError("unknown calibration arm")
    host_pressure = [(1-p)*row[0]+p*row[1] for row in matrix]
    parasite_gain = [(1-h)*matrix[0][i]+h*matrix[1][i] for i in range(2)]
    sh = 0.0 if arm in ("neutral", "host_selection_cut") else design.host_selection
    sp = 0.0 if arm in ("neutral", "parasite_selection_cut") else design.parasite_selection
    wh = [math.exp(-sh*x) for x in host_pressure]
    wp = [math.exp(sp*x) for x in parasite_gain]
    return dict(q_host=selected_frequency(h, wh[0], wh[1], design.mutation),
                q_parasite=selected_frequency(p, wp[0], wp[1], design.mutation),
                host_pressure_gap=host_pressure[1]-host_pressure[0],
                parasite_gain_gap=parasite_gain[1]-parasite_gain[0],
                host_log_fitness_gap=math.log(wh[1]/wh[0]),
                parasite_log_fitness_gap=math.log(wp[1]/wp[0]))


def simulate(seed: int, design: Design, matrix: list[list[float]], arm: str) -> list[dict[str, Any]]:
    """Non-overlapping clonal generations, with binomial sampling and fixed N."""
    h_count = round(design.population*0.55)
    p_count = round(design.population*0.45)
    rows = []
    for generation in range(1, design.generations+1):
        h, p = h_count/design.population, p_count/design.population
        expected = transitions(h, p, matrix, design, arm)
        hrng, prng = stream(seed, generation, "host"), stream(seed, generation, "parasite")
        hn = sum(hrng.random() < expected["q_host"] for _ in range(design.population))
        pn = sum(prng.random() < expected["q_parasite"] for _ in range(design.population))
        row = dict(schema=SCHEMA, seed=seed, arm=arm, generation=generation,
                   host_one=h_count, parasite_one=p_count, host_next_one=hn,
                   parasite_next_one=pn, population=design.population, **expected)
        if not all(0 <= count <= design.population for count in (h_count, p_count, hn, pn)):
            raise ConfigurationError("calibration census invariant failed")
        rows.append(row)
        h_count, p_count = hn, pn
    return rows


def reversals(values: list[float], hysteresis: float) -> int:
    """Count completed crossings of both bands; wiggles near 0.5 do not count."""
    previous = 0
    count = 0
    for value in values:
        current = 1 if value >= 0.5+hysteresis else -1 if value <= 0.5-hysteresis else 0
        if current:
            count += int(previous != 0 and previous != current)
            previous = current
    return count


def history_scores(rows: list[dict[str, Any]], design: Design) -> dict[str, float]:
    """One score per history, never one independent sample per time point."""
    if len(rows) != design.generations or [r["generation"] for r in rows] != list(range(1, design.generations+1)):
        raise ConfigurationError("history has missing or duplicate generations")
    if len({(r["seed"], r["arm"]) for r in rows}) != 1:
        raise ConfigurationError("mixed history/arm rows")
    selected = rows[design.burn_in:]
    host = [-r["host_pressure_gap"]*(r["host_next_one"]-r["host_one"])/design.population for r in selected]
    parasite = [r["parasite_gain_gap"]*(r["parasite_next_one"]-r["parasite_one"])/design.population for r in selected]
    hrev = reversals([r["host_one"]/design.population for r in selected], design.hysteresis)
    prev = reversals([r["parasite_one"]/design.population for r in selected], design.hysteresis)
    return dict(host_coupling=statistics.fmean(host), parasite_coupling=statistics.fmean(parasite),
                reciprocal_crossings=float(min(hrev, prev)), host_crossings=float(hrev), parasite_crossings=float(prev))


def lower_bound(values: list[float], alpha: float) -> dict[str, float | None]:
    """History-level paired t lower bound. Zero variance is not infinite certainty."""
    if not values or not 0 < alpha < 1 or any(not math.isfinite(v) for v in values):
        raise ConfigurationError("invalid history sample or interval alpha")
    mean = statistics.fmean(values)
    if len(values) < 2 or statistics.stdev(values) == 0:
        return dict(mean=mean, lower=None, standard_error=None)
    se = statistics.stdev(values)/math.sqrt(len(values))
    return dict(mean=mean, lower=mean-student_t_ppf(1-alpha, len(values)-1)*se, standard_error=se)


def assess(scores: dict[int, dict[str, dict[str, float]]], design: Design) -> dict[str, Any]:
    if set(scores) != set(design.seeds):
        raise ConfigurationError("missing or unlocked history")
    if any(set(arms) != set(ARMS) for arms in scores.values()):
        raise ConfigurationError("missing calibration arm")
    contrasts = {}
    specs = (("host_vs_neutral", "host_coupling", "neutral"),
             ("parasite_vs_neutral", "parasite_coupling", "neutral"),
             ("host_vs_cut", "host_coupling", "host_selection_cut"),
             ("parasite_vs_cut", "parasite_coupling", "parasite_selection_cut"),
             ("crossings_vs_neutral", "reciprocal_crossings", "neutral"))
    alpha = design.alpha_family/len(specs)
    passed = len(scores) >= 12
    for name, metric, control in specs:
        values = [scores[s]["coevolve"][metric]-scores[s][control][metric] for s in design.seeds]
        interval = lower_bound(values, alpha)
        threshold = 0.0 if metric == "reciprocal_crossings" else design.minimum_coupling_effect
        supported = interval["lower"] is not None and interval["lower"] > threshold
        contrasts[name] = dict(values=values, interval=interval, effect_bound=threshold, supported=supported)
        passed = passed and supported
    replicated = sum(scores[s]["coevolve"]["reciprocal_crossings"] >= 2 for s in design.seeds)
    # Candidate cycling must occur in at least half the independent histories.
    passed = passed and replicated >= math.ceil(len(scores)/2)
    return dict(calibration_verdict="SUPPORTED_REFERENCE_MODEL" if passed else "INCONCLUSIVE",
                red_queen_proved=False, full_engine_claim=False, n_independent=len(scores),
                histories_with_two_reciprocal_crossings=replicated, alpha_per_contrast=alpha,
                contrasts=contrasts, by_seed=scores,
                limitation="known matching-allele calibration with Wright-Fisher reproduction; not Genesis life-loop evidence")


def write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False)+"\n", encoding="utf-8")


def run_reference(output: Path, design: Design) -> dict[str, Any]:
    design.validate()
    output.mkdir(parents=True, exist_ok=False)
    matrix, evidence = contact_matrix()
    source_hash = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    write_json(output/"LOCK.json", dict(schema=SCHEMA, design=asdict(design), matrix=matrix,
        source_sha256=source_hash, model="engine contact + Wright-Fisher reference reproduction",
        primary_metrics="paired history-level coupling and hysteretic crossing contrasts",
        no_optional_stopping=True, controls=ARMS, red_queen_proved=False))
    write_json(output/"engine_contact_witness.json", evidence)
    scores: dict[int, dict[str, dict[str, float]]] = {}
    try:
        with (output/"live.log").open("w", encoding="utf-8", buffering=1) as live:
            for seed in design.seeds:
                scores[seed] = {}
                for arm in ARMS:
                    rows = simulate(seed, design, matrix, arm)
                    path = output/f"seed{seed}_{arm}.jsonl"
                    with path.open("w", encoding="utf-8") as archive:
                        for row in rows:
                            archive.write(json.dumps(row, sort_keys=True, allow_nan=False)+"\n")
                    scores[seed][arm] = history_scores(rows, design)
                    live.write(f"seed={seed} arm={arm} generations={len(rows)} invariant=ok\n")
        report = assess(scores, design)
        report["archive_sha256"] = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(output.glob("*.jsonl"))}
        write_json(output/"assessment.json", report)
        return report
    except Exception as exc:
        (output/"STOP").write_text(f"{type(exc).__name__}: {exc}\n", encoding="utf-8")
        raise


def verify_reference(output: Path) -> dict[str, Any]:
    """Recompute engine witnesses and replay every reference history from its lock."""
    lock = json.loads((output/"LOCK.json").read_text(encoding="utf-8"))
    if lock.get("schema") != SCHEMA:
        raise ConfigurationError("unknown reference schema")
    if lock.get("source_sha256") != hashlib.sha256(Path(__file__).read_bytes()).hexdigest():
        raise ConfigurationError("reference source differs from locked implementation")
    params = dict(lock["design"])
    params["seeds"] = tuple(params["seeds"])
    design = Design(**params)
    design.validate()
    matrix, witnesses = contact_matrix()
    if matrix != lock["matrix"] or witnesses != json.loads((output/"engine_contact_witness.json").read_text()):
        raise ConfigurationError("engine contact witness differs from locked evidence")
    names = {f"seed{s}_{a}.jsonl" for s in design.seeds for a in ARMS}
    if {p.name for p in output.glob("*.jsonl")} != names:
        raise ConfigurationError("missing or extra reference archive")
    scores: dict[int, dict[str, dict[str, float]]] = {}
    replayed_rows = 0
    for seed in design.seeds:
        scores[seed] = {}
        for arm in ARMS:
            path = output/f"seed{seed}_{arm}.jsonl"
            rows = [json.loads(line) for line in path.read_text().splitlines()]
            expected = simulate(seed, design, matrix, arm)
            if rows != expected:
                raise ConfigurationError("reference replay mismatch")
            scores[seed][arm] = history_scores(rows, design)
            replayed_rows += len(rows)
    assessment = assess(scores, design)
    stored = json.loads((output/"assessment.json").read_text())
    # JSON converts integer mapping keys to strings; compare canonical objects.
    for key, value in assessment.items():
        if json.loads(json.dumps(value)) != stored.get(key):
            raise ConfigurationError("assessment differs from raw archive reanalysis")
    hashes = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in output.glob("*.jsonl")}
    if hashes != stored.get("archive_sha256"):
        raise ConfigurationError("archive digest mismatch")
    report = dict(verified=True, replayed_rows=replayed_rows, calibration_verdict=assessment["calibration_verdict"],
                  red_queen_proved=False, full_engine_claim=False)
    write_json(output/"verification.json", report)
    return report


def randomized_time_matrix(rows: list[dict[str, Any]], past: int, present: int, future: int,
                           permutations: int = 8) -> dict[str, Any]:
    """Diagnostic only: average real seat-contact assays over random rosters.

    Shared roster permutations within a matrix reduce ordering noise. This is
    an ensemble seat-contact estimand, not the original single-roster assay.
    No offspring, survival, selection or dynamics are changed by measurement.
    """
    if permutations < 2 or not past < present < future:
        raise ConfigurationError("invalid time-matrix assay design")
    mapping = {r["generation"]: r for r in rows if r["arm"] == "coevolve"}
    if len(mapping) != sum(r["arm"] == "coevolve" for r in rows):
        raise ConfigurationError("duplicate coevolve generation")
    if any(t not in mapping for t in (past,present,future)):
        raise ConfigurationError("missing matrix generation")
    if len({r['seed'] for r in mapping.values()}) != 1:
        raise ConfigurationError("mixed history matrix")
    seed = next(iter(mapping.values()))['seed']
    values: dict[str, list[float]] = {}
    for permutation in range(permutations):
        rosters = {}
        for label, generation in (("past",past),("present",present),("future",future)):
            for species, field in (("host","hosts"),("parasite","parasites")):
                roster = [dict(person) for person in mapping[generation][field]]
                if not roster:
                    raise ConfigurationError("extinct population: matrix unmeasurable")
                stream(seed, permutation, f"matrix/{species}/{generation}").shuffle(roster)
                rosters[label,species] = roster
        for h in ("past","present","future"):
            for p in ("past","present","future"):
                key = f"{h}_host__{p}_parasite"
                value = infectivity(rosters[h,'host'], rosters[p,'parasite'])
                if value is None:
                    raise ConfigurationError("unmeasurable matrix contact")
                values.setdefault(key, []).append(value)
    cells = {key: statistics.fmean(v) for key,v in values.items()}
    return dict(past=past,present=present,future=future,permutations=permutations,
                cells=cells, seat_standard_deviation={k:statistics.stdev(v) for k,v in values.items()},
                margins=matrix_margins(cells), red_queen_proved=False)


def engine_diagnostics(output: Path, outcomes: list[dict[str, Any]], generations: int) -> dict[str, Any]:
    """Fixed-budget time-shift diagnostics, explicitly not a confirmation gate."""
    centers = tuple(t for t in (25,50,75) if t+5 <= generations)
    results = []
    for outcome in outcomes:
        if outcome['failed']:
            continue
        seed = outcome['seed']
        path = output/'by_seed'/f'seed{seed}'/'archive.jsonl'
        rows = [json.loads(line) for line in path.read_text().splitlines()]
        matrices = []
        for center in centers:
            try:
                matrices.append(randomized_time_matrix(rows,center-5,center,center+5))
            except ConfigurationError as exc:
                matrices.append(dict(present=center, blocked_reason=str(exc)))
        results.append(dict(seed=seed, matrices=matrices))
    report = dict(by_seed=results, centers=centers, lag=5, permutations=8,
        exploratory=True, red_queen_proved=False,
        reason='randomized contact matrices are not genotype-specific offspring fitness or a matched full-engine drift control')
    write_json(output/'time_shift_diagnostics.json',report)
    return report


def engine_pilot(output: Path, seeds: tuple[int, ...], generations: int, max_seconds: float) -> dict[str, Any]:
    """Run the existing life loop without changing its model or proof gate."""
    if (not seeds or len(set(seeds)) != len(seeds)
            or any(isinstance(s, bool) or not isinstance(s, int) or s < 0 for s in seeds)
            or isinstance(generations, bool) or not isinstance(generations, int) or generations < 2
            or not math.isfinite(max_seconds) or max_seconds <= 0):
        raise ConfigurationError("invalid engine pilot budget")
    output.mkdir(parents=True, exist_ok=False)
    write_json(output/"LOCK.json", dict(seeds=seeds, generations=generations, max_seconds=max_seconds,
        compare_one_shot=True, purpose="exploratory full-engine pilot", red_queen_proved=False,
        implementation_sha256={name: hashlib.sha256((Path(__file__).parent/name).read_bytes()).hexdigest()
            for name in ("rq_controlled_benchmark.py", "rq_mechanism_v2_phase5.py",
                         "rq_reciprocal_validity.py", "closed_loop_hp_arm01_structural_rq.py",
                         "measurements/antagonist_population.py")}))
    stop = threading.Event()
    began = time.monotonic()

    def monitor() -> None:
        with (output/"health.log").open("w", encoding="utf-8", buffering=1) as health:
            while not stop.is_set():
                elapsed = time.monotonic()-began
                health.write(json.dumps(dict(elapsed_seconds=elapsed, stop_file=(output/"STOP").exists()))+"\n")
                if elapsed >= max_seconds:
                    (output/"STOP").write_text("fixed wall-time budget exhausted; retain partial histories\n")
                    return
                stop.wait(min(600.0, max(0.01, max_seconds-elapsed)))

    thread = threading.Thread(target=monitor, daemon=True)
    thread.start()
    outcomes, replays = [], []
    try:
        for seed in seeds:
            if (output/"STOP").exists():
                break
            result = run_phase5_history(seed, str(output), generations, compare_one_shot=True)
            outcomes.append(result)
            if result["failed"]:
                break
            replays.append(replay_phase5_archive(output/"by_seed"/f"seed{seed}"/"archive.jsonl"))
            if not replays[-1]["matched"]:
                (output/"STOP").write_text("engine contact replay mismatch\n")
                break
    finally:
        stop.set()
        thread.join(timeout=2)
    report = dict(exploratory=True, red_queen_proved=False, outcomes=outcomes, replays=replays,
        completed_histories=len(replays), locked_histories=len(seeds),
        complete=len(replays)==len(seeds) and all(r["matched"] for r in replays) and not (output/"STOP").exists())
    write_json(output/"execution.json", report)
    if report["complete"]:
        engine_diagnostics(output, outcomes, generations)
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument("--engine-pilot", action="store_true")
    modes.add_argument("--verify-reference", action="store_true")
    parser.add_argument("--histories", type=int, default=12)
    parser.add_argument("--generations", type=int, default=None)
    parser.add_argument("--seed-start", type=int, default=None)
    parser.add_argument("--max-seconds", type=float, default=1800.0)
    args = parser.parse_args()
    if args.verify_reference:
        sys.stdout.write(json.dumps(verify_reference(args.output)) + "\n")
        sys.stdout.flush()
        return
    if args.histories < 1:
        parser.error("histories must be positive")
    start = args.seed_start if args.seed_start is not None else (10301 if args.engine_pilot else 10101)
    seeds = tuple(range(start, start+args.histories))
    if args.engine_pilot:
        report = engine_pilot(args.output, seeds, 100 if args.generations is None else args.generations, args.max_seconds)
    else:
        report = run_reference(args.output, Design(seeds=seeds, generations=300 if args.generations is None else args.generations))
    sys.stdout.write(json.dumps({k: v for k, v in report.items() if k not in ("by_seed", "contrasts", "archive_sha256")}) + "\n")
    sys.stdout.flush()


if __name__ == "__main__":
    main()
