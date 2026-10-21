"""genesis.qd_parametric and genesis.coevolution: exact reproduction of the
original pipeline searches, deterministic archives, and the optional pyribs
backend."""
from __future__ import annotations

import ast
import hashlib
import importlib.util
import json
import math
import statistics
from dataclasses import asdict
from pathlib import Path

import pytest

from codontrace.genesis.coevolution import minimax_coevolve
from codontrace.genesis.qd_parametric import (
    GaussianEmitter,
    HillClimbEmitter,
    MutationRule,
    ParameterBound,
    ParameterCandidate,
    ParameterSpace,
    PyribsGridBackend,
    ask_parameter_candidates,
    parameter_descriptor_config,
    tell_parameter_results,
)
from codontrace.genesis.qd_search import QDSearchArchive
from codontrace.rng import RNGManager
from codontrace.swarm.coevolution import coevolve
from codontrace.swarm.policies import Pipeline, PolicyArchive
from codontrace.swarm.research import mse

SRC = Path(__file__).resolve().parents[1] / 'src' / 'codontrace' / 'genesis'


def _data(seed, n=40):
    rng = RNGManager(seed=seed, namespace='test/qd-data')
    refs = [math.sin(i / 5) * 3 for i in range(n)]
    return [r + (rng.random() - 0.5) * 2 for r in refs], refs


def _reference_fit(seed, values, references, rounds):
    """The pre-refactor PolicyArchive.fit loop, frozen."""
    rng = RNGManager(seed=seed, namespace='swarm/pipelines')
    entries = {}
    best = Pipeline(); best_loss = math.inf
    for i in range(rounds * 4):
        candidate = Pipeline() if i == 0 else Pipeline(
            alpha=max(0.01, min(1.0, best.alpha + (rng.random() - 0.5) * 0.4)),
            clip=max(0.01, best.clip * (0.5 + rng.random())),
            event_threshold=best.event_threshold)
        output, _ = candidate.process(values)
        loss = statistics.mean((x-y)**2 for x, y in zip(output, references, strict=True))
        entries[candidate.digest] = {'pipeline': asdict(candidate), 'training_mse': loss}
        if len(entries) > 4096:
            del entries[next(iter(entries))]
        if loss < best_loss:
            best = candidate; best_loss = loss
    return best, entries, rng.snapshot()


def _reference_coevolve(references, seed, rounds, budget):
    rng = RNGManager(seed=seed, namespace='swarm/coevolution')
    policy = Pipeline(); nuisance = {'amplitude': budget, 'bias': 0.0, 'frequency': 1}
    history = []
    for generation in range(rounds):
        carrier = [2*rng.random()-1 for _ in references]

        def score(candidate, disturbance, carrier=carrier):
            values = [r + disturbance['bias'] + disturbance['amplitude'] * carrier[i//disturbance['frequency']]
                      for i, r in enumerate(references)]
            return mse(candidate.process(values)[0], references)
        challengers = [nuisance]
        for _ in range(3):
            bias = (2*rng.random()-1)*budget
            challengers.append({'amplitude': budget-abs(bias), 'bias': bias, 'frequency': rng.randrange(1, 5)})
        nuisance = max(challengers, key=lambda n: score(policy, n))
        defenders = [policy]
        for _ in range(3):
            defenders.append(Pipeline(alpha=max(.01, min(1, policy.alpha+(rng.random()-.5)*.5)),
                                      clip=max(.01, policy.clip*(.5+rng.random()))))
        policy = min(defenders, key=lambda p: max(score(p, n) for n in challengers))
        history.append({'generation': generation, 'training_worst_mse': max(score(policy, n) for n in challengers),
                        'pipeline': asdict(policy), 'disturbance': dict(nuisance)})
    return {'pipeline': asdict(policy), 'disturbance': nuisance, 'history': history, 'rng': rng.snapshot(),
            'scope': 'training_only_bounded_coadaptation', 'red_queen_proved': None, 'hypothesis_verdict': None}


def _exact(value):
    """JSON text keeps int vs float apart (1 vs 1.0), unlike ==."""
    return json.dumps(value, sort_keys=True)


@pytest.mark.parametrize(('seed', 'rounds'), [(0, 1), (1, 8), (7, 20), (123, 64)])
def test_policy_archive_fit_reproduces_original_loop(seed, rounds):
    values, refs = _data(seed)
    archive = PolicyArchive(seed=seed)
    best = archive.fit(values, refs, rounds=rounds)
    ref_best, ref_entries, ref_rng = _reference_fit(seed, values, refs, rounds)
    assert _exact(asdict(best)) == _exact(asdict(ref_best))
    assert _exact(list(archive.entries.items())) == _exact(list(ref_entries.items()))
    assert archive.rng.snapshot() == ref_rng


@pytest.mark.parametrize(('seed', 'rounds', 'budget'), [(0, 1, 1.0), (3, 8, 0.5), (11, 32, 4.0), (42, 12, 50.0)])
def test_coevolve_reproduces_original_loop(seed, rounds, budget):
    refs = [math.cos(i / 3) for i in range(24)]
    assert _exact(coevolve(refs, seed=seed, rounds=rounds, disturbance_budget=budget)) == \
        _exact(_reference_coevolve(refs, seed, rounds, budget))


def test_int_upper_bound_is_kept_as_given():
    rule = MutationRule('additive', 0.5, low=.01, high=1)

    class One:
        def random(self):
            return 1.0
    assert type(rule.apply(0.9, One())) is int  # min(1, 1.15) is the int 1


def test_policy_archive_qd_digest_is_deterministic():
    values, refs = _data(5)
    a, b, c = PolicyArchive(seed=5), PolicyArchive(seed=5), PolicyArchive(seed=6)
    for archive in (a, b, c):
        archive.fit(values, refs, rounds=16)
    assert a.archive_digest() == b.archive_digest() != c.archive_digest()
    assert a.qd_archive.elites
    assert max(e.quality for e in a.qd_archive.elites.values()) == -min(
        e['training_mse'] for e in a.entries.values())


SPACE = ParameterSpace((
    ParameterBound('x', -1.0, 1.0, 0.0, MutationRule('additive', 0.5, low=-1.0, high=1.0)),
    ParameterBound('y', -1.0, 1.0, 0.0, MutationRule('gaussian', 0.3, low=-1.0, high=1.0)),
))


def test_ask_tell_into_qd_archive():
    rng = RNGManager(seed=3, namespace='test/qd')
    config = parameter_descriptor_config(SPACE, bins=4)
    archive = QDSearchArchive()
    parent = SPACE.defaults()
    for _ in range(10):
        batch = ask_parameter_candidates(SPACE, HillClimbEmitter(), parent, rng, 5)
        assert all(SPACE.contains(c.params) for c in batch)
        qualities = [-(c.params['x'] - 0.5) ** 2 - (c.params['y'] + 0.25) ** 2 for c in batch]
        archive, _ = tell_parameter_results(archive, config, batch, qualities)
        parent = dict(max(zip(qualities, batch), key=lambda t: t[0])[1].params)
    again = RNGManager(seed=3, namespace='test/qd')
    assert len(archive.elites) > 4 and parent['x'] > 0.2
    assert ask_parameter_candidates(SPACE, HillClimbEmitter(), SPACE.defaults(), again, 2) == \
        ask_parameter_candidates(SPACE, HillClimbEmitter(), SPACE.defaults(), RNGManager(seed=3, namespace='test/qd'), 2)


def test_gaussian_emitter_stays_in_bounds_and_uses_two_draws_per_parameter():
    rng = RNGManager(seed=1, namespace='test/gauss')
    for _ in range(200):
        out = GaussianEmitter(sigma=2.0).emit(SPACE, {'x': 0.9, 'y': -0.9}, rng)
        assert SPACE.contains(out)
    assert rng.draw_count == 200 * 2 * 2


def test_space_and_candidate_digests_are_stable():
    assert SPACE.digest() == hashlib.sha256(json.dumps(SPACE.to_dict(), sort_keys=True, separators=(',', ':'))
                                            .encode()).hexdigest()
    c = ParameterCandidate({'y': 0.5, 'x': 0.25})
    assert c.genome == '{"x":0.25,"y":0.5}' and c.digest() == ParameterCandidate({'x': 0.25, 'y': 0.5}).digest()
    with pytest.raises(ValueError):
        ParameterCandidate({'x': math.nan})


def test_minimax_coevolve_finds_the_saddle_of_a_toy_game():
    # Defender picks d, challenger picks c in a grid; loss |d - c|. Worst case is minimized at the centre.
    grid = [i / 4 for i in range(-4, 5)]
    result = minimax_coevolve(1.0, 0.0, rounds=6, begin_round=lambda g: None,
                              propose_challengers=lambda c, _: [c] + grid,
                              propose_defenders=lambda d, _: [d] + grid,
                              score=lambda d, c, _: abs(d - c))
    assert result.defender == 0.0 and result.rounds[-1].worst_score == 1.0
    with pytest.raises(ValueError):
        minimax_coevolve(0, 0, rounds=0, begin_round=lambda g: None, propose_challengers=lambda c, _: [c],
                         propose_defenders=lambda d, _: [d], score=lambda d, c, _: 0.0)


def test_engine_search_modules_are_domain_free():
    for name in ('qd_parametric.py', 'coevolution.py'):
        tree = ast.parse((SRC / name).read_text(encoding='utf-8'))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module:
                assert not node.module.startswith(('codontrace.swarm', 'codontrace.console')), (name, node.module)
        # ribs is optional: only imported lazily inside PyribsGridBackend.
        top = [n.module for n in tree.body if isinstance(n, ast.ImportFrom)]
        assert not any(m and m.startswith('ribs') for m in top), name


@pytest.mark.skipif(importlib.util.find_spec('ribs') is not None, reason='ribs installed')
def test_pure_path_without_pyribs():
    with pytest.raises(ImportError, match=r'extra \[qd\]'):
        PyribsGridBackend(SPACE, parameter_descriptor_config(SPACE))


def test_pyribs_backend_parity_on_a_toy_problem():
    pytest.importorskip('ribs')
    config = parameter_descriptor_config(SPACE, bins=5)
    rng = RNGManager(seed=9, namespace='test/ribs')
    # Measures at cell centres +- 0.15 of a cell (far from ribs' epsilon at edges); distinct qualities.
    candidates = []
    for _ in range(300):
        cx, cy = rng.randrange(5), rng.randrange(5)
        x = -1 + (cx + 0.5 + (rng.random() - 0.5) * 0.3) * 0.4
        y = -1 + (cy + 0.5 + (rng.random() - 0.5) * 0.3) * 0.4
        candidates.append(ParameterCandidate({'x': x, 'y': y}))
    qualities = [-(c.params['x'] ** 2) - (c.params['y'] - 0.3) ** 2 + 1e-9 * i for i, c in enumerate(candidates)]
    pure, _ = tell_parameter_results(QDSearchArchive(), config, candidates, qualities)
    backend = PyribsGridBackend(SPACE, config)
    backend.tell(candidates, qualities)
    ribs_elites = backend.elites()
    assert set(ribs_elites) == set(pure.elites)
    for cell, elite in pure.elites.items():
        params, objective = ribs_elites[cell]
        assert objective == pytest.approx(elite.quality, rel=0, abs=1e-12)
        assert json.loads(elite.genome) == pytest.approx(params, abs=1e-12)
