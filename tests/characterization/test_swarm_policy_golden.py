"""Characterization: PolicyArchive.fit, coevolve and run_seed numeric outputs.

Pins the exact RNG draw order (namespaces ``swarm/pipelines``,
``swarm/coevolution``, ``swarm/engineering-probes``) and the resulting floats,
so a later move onto engine QD / coevolution primitives must reproduce them
bit for bit. Floats are stored as repr-exact JSON numbers.
"""
from __future__ import annotations

from dataclasses import asdict

import pytest

from codontrace.swarm.coevolution import coevolve
from codontrace.swarm.experiments import run_seed
from codontrace.swarm.policies import Pipeline, PolicyArchive, transfer_decision

from ._golden import check_json, check_json_close, load_json

SEEDS = (0, 1, 7)


def _series(n: int = 48) -> tuple[list[float], list[float]]:
    """Stored inputs (no libm at test time), originally
    ``refs[i] = sin(i/6)``, ``noisy[i] = refs[i] + 0.3*sin(1.7*i) + (1.5 if i % 11 == 5 else 0)``."""
    data = load_json('policy_inputs.json')[str(n)]
    return list(data['noisy']), list(data['refs'])


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
    # Probe outputs are float arithmetic over math.sin and sum(); 3.11 and 3.12+
    # differ in the last bits (sum() is compensated since 3.12), so floats are
    # compared to 1e-9 and payload byte counts (length of float text) to 5 %.
    # Ids, flags, counts and probe order stay exact.
    check_json_close(f'run_seed_seed{seed}.json', rows,
                     loose_ints={'raw_payload_bytes': 0.05, 'feature_payload_bytes': 0.05})


def test_policy_archive_cap_evicts_oldest_beyond_4096():
    """17 fits x 256 candidates overflow the 4096-entry archive; the oldest digests go first."""
    noisy, refs = _series()
    archive = PolicyArchive(3)
    order: list[str] = []
    for _ in range(17):
        before = set(archive.entries)
        archive.fit(noisy[:6], refs[:6], rounds=64)
        order += [d for d in archive.entries if d not in before]
    assert len(archive.entries) == 4096
    assert list(archive.entries) == order[-4096:]
    check_json('policy_archive_cap.json', {'seen': len(order), 'first_kept': next(iter(archive.entries)),
                                           'last_kept': list(archive.entries)[-1],
                                           'rng_draws': archive.rng.snapshot()['draw_count']})


def test_pipeline_event_threshold_is_inclusive():
    filtered, events = Pipeline(alpha=0.5, clip=1.0, event_threshold=2.0).process([0.0, 2.0, 2.5, 0.5, 0.5])
    assert events == [1, 3]  # |2.0 - 0.0| == threshold counts; |0.5 - 2.5| == 2.0 counts
    assert filtered == [0.0, 0.5, 1.0, 0.75, 0.625]
