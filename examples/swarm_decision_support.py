"""Reproducible synthetic instrument probes, not physical or scientific verdicts."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from codontrace.rng import RNGManager
from codontrace.swarm.decision_support import capsule_shadow, residual_interval
from codontrace.swarm.experiments import hello, reading
from codontrace.swarm.policies import Pipeline
from codontrace.swarm.runtime import SwarmCoordinator


def run_probe(seed: int) -> dict:
    rng=RNGManager(seed=seed,namespace='swarm/decision-support/probe')
    references=[0.]*128
    values=[2*rng.random()-1 for _ in references]
    # Disjoint halves: calibration of a frozen baseline and later evaluation.
    # Constant-zero predictor for noisy observations: same predictor in cal/test.
    interval=residual_interval([0.]*64,values[:64],estimate=0.,training_id='frozen-baseline',
                               calibration_id=f'cal-{seed}',model_id='constant-zero')
    observed_coverage=sum(interval['lower']<=x<=interval['upper'] for x in values[64:])/64
    independent=capsule_shadow(Pipeline(alpha=.1),Pipeline(),values[64:],references[64:],
                               training_id='fixed-before-run',evaluation_id=f'test-{seed}')
    # A ramp is a positive control for harmful smoothing, not selected favorable noise.
    ramp=[float(i) for i in range(16)]
    rollback=capsule_shadow(Pipeline(alpha=.1),Pipeline(),ramp,ramp,training_id='fixed-before-run',
                            evaluation_id=f'drift-{seed}',phase='monitoring')
    swarm=SwarmCoordinator('probe')
    for node in ('a','b','c'):
        swarm.ingest(hello('probe',node),now_ms=1000)
        swarm.ingest(reading('probe',node,1,1000,0.),now_ms=1000)
    models={node+'/s':dict(group='same' if node in ('a','b') else 'other',noise_variance=.1,
                           process_variance_per_ms=.01,latency_ms=10,success_probability=.9,
                           payload_bytes=100,evidence_id='synthetic-model') for node in ('a','b','c')}
    schedule=swarm.freshness_plan(models,'signal','arb',now_ms=2000,byte_budget=200)
    return {'seed':seed,'synthetic':True,'interval':interval,'heldout_coverage':observed_coverage,
            'shadow':independent,'rollback_control':rollback,'schedule':schedule,'rng':rng.snapshot()}


def main() -> None:
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--seeds',type=int,default=16);args=p.parse_args()
    if not 1<=args.seeds<=256:p.error('seeds must be 1..256')
    args.output.mkdir(parents=True,exist_ok=True)
    path=args.output/'swarm_decision_support.json'
    # Do not overwrite a prior run, which may be a locked evidence artifact.
    with path.open('x',encoding='utf-8') as handle:
        json.dump({'schema':'genesis_swarm_decision_report_v1','synthetic':True,'physical_validation':False,
                   'scope':'synthetic_instrument_probes','reports':[run_probe(i) for i in range(args.seeds)]},handle,indent=2,allow_nan=False)
    print(path)


if __name__=='__main__':main()
