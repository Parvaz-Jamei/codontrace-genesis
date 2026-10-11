"""Characterization: PolicyArchive.fit, coevolve and run_seed numeric outputs.

Pins the exact RNG draw order (namespaces ``swarm/pipelines``,
``swarm/coevolution``, ``swarm/engineering-probes``) and the resulting floats,
so a later move onto engine QD / coevolution primitives must reproduce them
bit for bit. Floats are stored as repr-exact JSON numbers.
"""
from __future__ import annotations

import math
from dataclasses import asdict

import pytest

from codontrace.swarm.coevolution import coevolve
from codontrace.swarm.experiments import run_seed
from codontrace.swarm.policies import Pipeline, PolicyArchive, transfer_decision

from ._golden import check_json

SEEDS = (0, 1, 7)


def _series(n: int = 48) -> tuple[list[float], list[float]]:
    refs = [math.sin(i / 6) for i in range(n)]
    # Fixed deterministic "noise" without RNG: the inputs themselves are pinned too.
    noisy = [r + 0.3 * math.sin(i * 1.7) + (1.5 if i % 11 == 5 else 0.0) for i, r in enumerate(refs)]
    return noisy, refs


@pytest.mark.parametrize('seed', SEEDS)
def test_policy_archive_fit_golden(seed):
    noisy, refs = _series()
    archive = PolicyArchive(seed)
    best = archive.fit(noisy, refs, rounds=6)
    decision = transfer_decision(best, Pipeline(), noisy, refs)
    check_json(f'policy_archive_fit_seed{seed}.json', {
        'best': asdict(best), 'best_digest': best.digest,
        'entries': archive.entries, 'entry_order': list(archive.entries),
        'rng': archive.rng.snapshot(), 'processed': best.process(noisy[:12]),
        'transfer_decision': decision})


@pytest.mark.parametrize('seed', SEEDS)
def test_coevolve_golden(seed):
    _, refs = _series(32)
    check_json(f'coevolve_seed{seed}.json', coevolve(refs, seed=seed, rounds=5, disturbance_budget=0.8))


@pytest.mark.parametrize('seed', SEEDS)
def test_run_seed_probes_golden(seed):
    rows = run_seed(seed, samples=48)
    assert [r['idea'][:2] for r in rows] == [f'{i:02d}' for i in range(1, 11)]
    check_json(f'run_seed_seed{seed}.json', rows)
