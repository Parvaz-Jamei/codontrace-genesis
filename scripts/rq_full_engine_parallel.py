"""Fixed-budget exploratory Genesis runs with fail-closed archive validation.

Treatment physics, selection and RNG are unchanged. Partial data are retained.

EXECUTION BOUNDARY & ARCHITECTURAL CLASSIFICATION:
Backend: GENESIS_ENGINE (Full Digital Organism Coevolution Simulation)
Engine Substrate: CodonTrace GenesisEngine coevolutionary dynamics with codon translation,
reproduction, host-parasite contacts, and biological assay verification.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import sys
import threading
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path
from typing import Any

from codontrace.errors import ConfigurationError
from codontrace.genesis.rq_bidirectional_timeshift import config_digest
from codontrace.genesis.rq_controlled_benchmark import engine_diagnostics, randomized_time_matrix, write_json
from codontrace.genesis.rq_mechanism_v2_phase5 import (
    ARCHIVE_SCHEMA,
    replay_phase5_archive,
    run_phase5_history,
)

ARMS = ('coevolve', 'adaptation_cut', 'constant_parasite')


def worker(seed: int, root: str, generations: int) -> dict[str, Any]:
    return dict(run_phase5_history(seed, root, generations, compare_one_shot=True))


def validate_archive(path: Path, seed: int, generations: int, expected_config: str) -> None:
    """Check each persisted identity and invariant; count without loading the entire file."""
    expected = {(arm, g) for arm in ARMS for g in range(1, generations + 1)}
    seen: set[tuple[str, int]] = set()
    try:
        with path.open(encoding='utf-8') as archive:
            for number, line in enumerate(archive, start=1):
                row = json.loads(line)
                if not isinstance(row, dict):
                    raise ConfigurationError(f'archive row {number} is not an object')
                generation = row.get('generation')
                arm = row.get('arm')
                if type(generation) is not int or not isinstance(arm, str):
                    raise ConfigurationError(f'invalid arm/generation at row {number}')
                key = (arm, generation)
                if key not in expected or key in seen:
                    raise ConfigurationError(f'missing/unexpected/duplicate arm-generation at row {number}')
                if type(row.get('seed')) is not int or row['seed'] != seed:
                    raise ConfigurationError(f'wrong history seed at row {number}')
                if row.get('schema') != ARCHIVE_SCHEMA or row.get('config_digest') != expected_config:
                    raise ConfigurationError(f'wrong archive schema/config at row {number}')
                if row.get('invariant') != 'ok' or row.get('reproduction_enabled') is not True:
                    raise ConfigurationError(f'invalid engine invariant at row {number}')
                if row.get('red_queen_proved') is not False:
                    raise ConfigurationError(f'forbidden proof flag at row {number}')
                for field in ('contact_debit', 'contact_credit'):
                    value = row.get(field)
                    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value < 0:
                        raise ConfigurationError(f'invalid {field} at row {number}')
                contacts = row.get('contacts')
                if type(contacts) is not int or contacts < 0:
                    raise ConfigurationError(f'invalid contact count at row {number}')
                seen.add(key)
    except (OSError, json.JSONDecodeError) as exc:
        raise ConfigurationError(f'archive unreadable: {type(exc).__name__}: {exc}') from exc
    if seen != expected:
        raise ConfigurationError('incomplete arm-generation archive')


def horizon_diagnostics(root: Path, seeds: tuple[int, ...], generations: int) -> None:
    lag = max(5, generations // 100)
    centers = tuple(sorted({round(generations*f) for f in (.25, .5, .75)
        if round(generations*f)-lag >= 1 and round(generations*f)+lag <= generations}))
    matrices = []
    for seed in seeds:
        rows = [json.loads(line) for line in (root/'by_seed'/f'seed{seed}'/'archive.jsonl').read_text().splitlines()]
        cells = []
        for center in centers:
            try:
                cells.append(randomized_time_matrix(rows, center-lag, center, center+lag))
            except ConfigurationError as exc:
                cells.append(dict(present=center, blocked_reason=str(exc)))
        matrices.append(dict(seed=seed, matrices=cells))
    write_json(root/'long_horizon_time_shift.json', dict(by_seed=matrices, centers=centers,
        lag=lag, permutations=8, exploratory=True, red_queen_proved=False))


def run(root: Path, seeds: tuple[int, ...], generations: int, workers: int, max_seconds: float, budget_kind: str = 'active_time') -> dict[str, Any]:
    if not seeds or any(type(s) is not int or s < 0 for s in seeds) or len(set(seeds)) != len(seeds):
        raise ConfigurationError('history seeds must be unique nonnegative integers')
    if type(workers) is not int or workers < 1 or type(generations) is not int or generations < 2:
        raise ConfigurationError('invalid worker/generation budget')
    if isinstance(max_seconds, bool) or not isinstance(max_seconds, (int, float)) or not math.isfinite(max_seconds) or max_seconds <= 0:
        raise ConfigurationError('invalid time budget')
    if budget_kind not in ('active_time', 'wall_deadline'):
        raise ConfigurationError(f'invalid budget_kind: {budget_kind}')
    root = root.resolve()
    root.mkdir(parents=True, exist_ok=False)
    source = Path(__file__).resolve()
    source_root = source.parents[1] / 'src'
    source_hashes = {str(p.relative_to(source_root)): hashlib.sha256(p.read_bytes()).hexdigest()
                     for p in sorted((source_root/'codontrace').rglob('*.py'))}
    expected_config = config_digest()
    write_json(root/'LOCK.json', dict(seeds=seeds, generations=generations, workers=workers,
        arms=ARMS, exploratory=True, compare_one_shot=True, max_seconds=max_seconds,
        budget_kind=budget_kind,
        wall_budget_scope='worker simulation and one-shot checks; cooperative stop, diagnostics outside budget',
        driver_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
        source_sha256=source_hashes, config_digest=expected_config, red_queen_proved=False))
    stop = threading.Event()
    started = time.monotonic()
    paused_accumulated = [0.0]

    def monitor() -> None:
        with (root/'health.log').open('w', encoding='utf-8', buffering=1) as log:
            while not stop.is_set():
                if ((root/'PAUSE').is_file() or ((root.parent/'PAUSE').is_file())):
                    pause_start = time.monotonic()
                    while ((root/'PAUSE').is_file() or ((root.parent/'PAUSE').is_file())):
                        if stop.is_set() or (root/'STOP').exists() or ((root.parent/'STOP').is_file()):
                            break
                        time.sleep(0.2)
                    pause_duration = time.monotonic() - pause_start
                    paused_accumulated[0] += pause_duration

                wall_elapsed = time.monotonic() - started
                active_elapsed = max(0.0, wall_elapsed - paused_accumulated[0])
                effective_elapsed = active_elapsed if budget_kind == 'active_time' else wall_elapsed

                log.write(json.dumps(dict(
                    elapsed_seconds=round(effective_elapsed, 2),
                    active_elapsed_seconds=round(active_elapsed, 2),
                    paused_seconds=round(paused_accumulated[0], 2),
                    wall_elapsed_seconds=round(wall_elapsed, 2),
                    budget_kind=budget_kind,
                    stop_file=(root/'STOP').exists()
                ))+'\n')

                if effective_elapsed >= max_seconds:
                    (root/'STOP').write_text(f'fixed {budget_kind} budget exhausted\n', encoding='utf-8')
                    return
                remaining = max_seconds - effective_elapsed
                stop.wait(min(600.0, max(0.01, remaining)))

    thread = threading.Thread(target=monitor, daemon=True)
    thread.start()
    outcomes = []
    try:
        with ProcessPoolExecutor(max_workers=workers) as pool:
            futures = {pool.submit(worker, seed, str(root), generations): seed for seed in seeds}
            for future in as_completed(futures):
                try:
                    result = future.result()
                except Exception as exc:
                    result = dict(seed=futures[future], failed=f'{type(exc).__name__}: {exc}')
                outcomes.append(result)
                print(json.dumps(result), flush=True)
                write_json(root/'partial_execution.json', outcomes)
                if result.get('failed'):
                    (root/'STOP').write_text(str(result['failed'])+'\n', encoding='utf-8')
    finally:
        stop.set()
        thread.join(timeout=2)
    replays = []
    errors = []
    complete = len(outcomes) == len(seeds) and not (root/'STOP').exists() and all(not r.get('failed') for r in outcomes)
    if complete:
        for seed in seeds:
            path = root/'by_seed'/f'seed{seed}'/'archive.jsonl'
            try:
                validate_archive(path, seed, generations, expected_config)
                replay = replay_phase5_archive(path)
                replays.append(replay)
                if not replay['matched']:
                    raise ConfigurationError('engine contact replay mismatch')
            except Exception as exc:
                complete = False
                reason = f'{type(exc).__name__}: {exc}'
                errors.append(dict(seed=seed, reason=reason))
                (root/'STOP').write_text(reason+'\n', encoding='utf-8')
                break
    wall_total = time.monotonic() - started
    active_total = max(0.0, wall_total - paused_accumulated[0])
    report = dict(complete=complete,
        simulation_elapsed_seconds=round(active_total, 2),
        active_elapsed_seconds=round(active_total, 2),
        paused_seconds=round(paused_accumulated[0], 2),
        wall_elapsed_seconds=round(wall_total, 2),
        budget_kind=budget_kind,
        outcomes=sorted(outcomes, key=lambda row: row['seed']), replays=replays,
        validation_failures=errors, diagnostics_complete=False,
        engine_backend='genesis_engine',
        model_scope='full_digital_organism_simulation',
        model_boundary_notice='Full digital organism coevolution engine with codon translation and biological assays.',
        red_queen_proved=False, exploratory=True)
    write_json(root/'execution.json', report)
    if complete:
        try:
            engine_diagnostics(root, outcomes, generations)
            horizon_diagnostics(root, seeds, generations)
            report['diagnostics_complete'] = True
        except Exception as exc:
            report['complete'] = False
            reason = f'{type(exc).__name__}: {exc}'
            errors.append(dict(seed=None, reason=reason, stage='diagnostics'))
            (root/'STOP').write_text(reason+'\n', encoding='utf-8')
    wall_total_end = time.monotonic() - started
    active_total_end = max(0.0, wall_total_end - paused_accumulated[0])
    report['elapsed_seconds'] = round(active_total_end if budget_kind == 'active_time' else wall_total_end, 2)
    report['active_elapsed_seconds'] = round(active_total_end, 2)
    report['paused_seconds'] = round(paused_accumulated[0], 2)
    report['wall_elapsed_seconds'] = round(wall_total_end, 2)
    write_json(root/'execution.json', report)
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--histories', type=int, default=12)
    parser.add_argument('--generations', type=int, default=100)
    parser.add_argument('--seed-start', type=int, default=16001)
    parser.add_argument('--seeds', type=str, default=None, help='Comma-separated explicit seeds')
    parser.add_argument('--workers', type=int, default=os.cpu_count() or 1)
    parser.add_argument('--max-seconds', type=float, default=1800.0)
    parser.add_argument('--budget-kind', choices=['active_time', 'wall_deadline'], default='active_time')
    args = parser.parse_known_args()[0]
    if args.seeds:
        parsed_seeds = tuple(int(s.strip()) for s in args.seeds.split(',') if s.strip())
    else:
        if args.histories < 1:
            parser.error('histories must be positive')
        parsed_seeds = tuple(range(args.seed_start, args.seed_start + args.histories))
    report = run(args.output, parsed_seeds,
        args.generations, args.workers, args.max_seconds, budget_kind=args.budget_kind)
    print(json.dumps({k: v for k, v in report.items() if k not in ('outcomes', 'replays')}))
    if not report['complete']:
        sys.exit(2)


if __name__ == '__main__':
    main()
