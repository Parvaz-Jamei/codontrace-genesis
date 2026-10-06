"""Mechanistic, falsification and evidence-integrity tests for RQ calibration."""
import json
from dataclasses import replace

import pytest

from codontrace.errors import ConfigurationError
from codontrace.genesis.rq_controlled_benchmark import (
    ARMS,
    Design,
    assess,
    contact_matrix,
    history_scores,
    lower_bound,
    reversals,
    run_reference,
    simulate,
    transitions,
    verify_reference,
)


@pytest.mark.parametrize('change', [dict(seeds=(1,1)), dict(seeds=(True,)),
    dict(population=15), dict(generations=2, burn_in=1), dict(mutation=float('nan')),
    dict(mutation=.5), dict(host_selection=-1), dict(hysteresis=0)])
def test_invalid_design_is_not_an_experiment(change):
    with pytest.raises(ConfigurationError):
        replace(Design(), **change).validate()


def test_real_engine_matrix_matches_independent_two_type_expectation():
    matrix, witnesses = contact_matrix()
    # Equal six-bit windows match all loci; opposite windows match none.
    assert matrix == [[1.,0.],[0.,1.]]
    assert all(w['loss'] == pytest.approx(w['debit']) for w in witnesses)
    assert all(w['contacts']==1 and not w['archive_mutated'] for w in witnesses)


def test_reciprocal_selection_and_intervention_directions():
    d = replace(Design(), mutation=0)
    matrix = [[1.,0.],[0.,1.]]
    expected = transitions(.7,.8,matrix,d,'coevolve')
    assert expected['q_host'] < .7
    assert expected['q_parasite'] > .8
    neutral = transitions(.7,.8,matrix,d,'neutral')
    assert neutral['q_host'] == pytest.approx(.7)
    assert neutral['q_parasite'] == pytest.approx(.8)
    hcut = transitions(.7,.8,matrix,d,'host_selection_cut')
    pcut = transitions(.7,.8,matrix,d,'parasite_selection_cut')
    assert hcut['q_host'] == pytest.approx(.7) and hcut['q_parasite'] > .8
    assert pcut['q_parasite'] == pytest.approx(.8) and pcut['q_host'] < .7


def test_hysteresis_rejects_small_random_wiggles():
    assert reversals([.49,.51,.49,.51], .1)==0
    assert reversals([.2,.4,.8,.6,.2], .1)==2


def test_histories_replay_and_missing_rows_cannot_be_zero_filled():
    d = replace(Design(), seeds=(1,), generations=40, burn_in=10)
    matrix = [[1.,0.],[0.,1.]]
    a = simulate(1,d,matrix,'coevolve')
    assert a == simulate(1,d,matrix,'coevolve')
    assert a != simulate(2,d,matrix,'coevolve')
    with pytest.raises(ConfigurationError, match='missing or duplicate'):
        history_scores(a[:-1], d)
    with pytest.raises(ConfigurationError, match='mixed'):
        history_scores([dict(a[0],seed=2),*a[1:]],d)


def test_no_variation_is_not_infinite_confidence_or_a_proof():
    assert lower_bound([1.]*12,.01)['lower'] is None
    d = Design()
    scores = {s:{a:dict(host_coupling=0.,parasite_coupling=0.,reciprocal_crossings=0.) for a in ARMS} for s in d.seeds}
    report = assess(scores,d)
    assert report['calibration_verdict']=='INCONCLUSIVE'
    assert report['red_queen_proved'] is False
    with pytest.raises(ConfigurationError,match='missing or unlocked'):
        assess({},d)


def test_default_positive_control_and_independent_raw_replay(tmp_path):
    output = tmp_path/'reference'
    report = run_reference(output,Design())
    assert report['n_independent']==12
    assert report['calibration_verdict']=='SUPPORTED_REFERENCE_MODEL'
    assert report['full_engine_claim'] is False
    assert report['red_queen_proved'] is False
    replay = verify_reference(output)
    assert replay['replayed_rows']==12*4*300
    assert replay['verified'] is True
    archive = output/'seed10101_coevolve.jsonl'
    rows = [json.loads(line) for line in archive.read_text().splitlines()]
    rows[0]['host_next_one'] += 1
    archive.write_text('\n'.join(json.dumps(r) for r in rows)+'\n')
    with pytest.raises(ConfigurationError,match='replay mismatch'):
        verify_reference(output)


def test_randomized_time_matrix_uses_real_engine_and_refuses_missing_data():
    from codontrace.genesis.rq_controlled_benchmark import randomized_time_matrix
    rows = []
    for generation, window in ((1,'000000'),(2,'111111'),(3,'000000')):
        rows.append(dict(arm='coevolve',generation=generation,seed=7,
            hosts=[dict(id=f'h{i}',window=window,runtime_atp=48.) for i in range(2)],
            parasites=[dict(unit_id=f'p{i}',window=window,energy=1.) for i in range(2)]))
    matrix = randomized_time_matrix(rows,1,2,3,permutations=2)
    assert matrix['cells']['present_host__present_parasite'] == pytest.approx(1)
    assert matrix['cells']['present_host__past_parasite'] == pytest.approx(0)
    assert matrix['red_queen_proved'] is False
    with pytest.raises(ConfigurationError,match='missing'):
        randomized_time_matrix(rows[:-1],1,2,3)
    with pytest.raises(ConfigurationError,match='duplicate'):
        randomized_time_matrix(rows+[rows[0]],1,2,3)


def test_drift_only_calibration_cannot_pass_the_reciprocal_gate(tmp_path):
    d = replace(Design(), host_selection=0, parasite_selection=0)
    report = run_reference(tmp_path/'neutral_model',d)
    assert report['calibration_verdict']=='INCONCLUSIVE'
    assert all(c['interval']['mean']==0 for c in report['contrasts'].values())
    assert report['red_queen_proved'] is False
