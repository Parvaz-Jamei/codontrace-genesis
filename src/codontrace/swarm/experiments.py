"""Ten synthetic engineering probes with measured outputs, not discovery verdicts."""
from __future__ import annotations

import math
from dataclasses import asdict
from typing import Any

from codontrace.rng import RNGManager
from codontrace.swarm.coevolution import coevolve
from codontrace.swarm.policies import Pipeline, PolicyArchive, transfer_decision
from codontrace.swarm.protocol import VERSION, canonical, integer
from codontrace.swarm.research import SensorTwin, mse, perturb, processing_contrast
from codontrace.swarm.runtime import SwarmCoordinator


def packet(sid: str, node: str, seq: int, kind: str, payload: dict[str, Any], *, boot: str = 'boot1') -> dict[str, Any]:
    return {'schema': VERSION, 'swarm_id': sid, 'node_id': node, 'boot_id': boot,
            'seq': seq, 'kind': kind, 'payload': payload}


def hello(sid: str, node: str) -> dict[str, Any]:
    return packet(sid, node, 0, 'hello', {'wifi': True, 'channels': {'s': {'quantity': 'signal', 'unit': 'arb'}},
                                        'operations': ['sample', 'raw', 'result', 'pipeline', 'capsule']})


def reading(sid: str, node: str, seq: int, now: int, value: float) -> dict[str, Any]:
    return packet(sid, node, seq, 'reading', {'channel': 's', 'sample_ms': now, 'value': value,
                                            'processing_version': 'synthetic_v1'})


def run_seed(seed: int, *, samples: int = 64) -> list[dict[str, Any]]:
    integer(seed); integer(samples, high=4096)
    if samples < 16:
        raise ValueError('at least 16 samples required')
    rng = RNGManager(seed=seed, namespace='swarm/engineering-probes')
    refs = [math.sin(i/8) for i in range(samples)]
    noisy = [v for v in perturb(refs, rng=rng, amplitude=0.8) if v is not None]
    cut = samples//2
    archive = PolicyArchive(seed)
    trained = archive.fit(noisy[:cut], refs[:cut], rounds=8)
    base = Pipeline(); filtered, events = trained.process(noisy[cut:])
    fixed, _ = base.process(noisy[cut:])
    common = {'seed': seed, 'synthetic': True, 'independent_history_id': f'synthetic-seed-{seed}',
              'claim': 'engineering_probe_only', 'physical_validation': False}
    rows = []
    def emit(idea: str, **metrics: Any) -> None:
        rows.append({**common, 'idea': idea, **metrics})
    swarm = SwarmCoordinator('probe')
    for node in ('a', 'b', 'c'):
        swarm.ingest(hello('probe', node), now_ms=1000)
    learned_errors = []; mean_errors = []
    for i, ref in enumerate(refs):
        now = 1000+i
        for j, node in enumerate(('a', 'b', 'c')):
            observation = ref+(0.2*(rng.random()-0.5))+(5 if j == 2 else 0)
            swarm.ingest(reading('probe', node, i+1, now, observation), now_ms=now)
            if i < cut:
                swarm.calibrate(node+'/s', ref, 'synthetic-reference', now_ms=now, scale=0.25)
        if i >= cut:
            learned_errors.append(swarm.fuse('signal', 'arb', now_ms=now, mode='calibrated')['value'])
            mean_errors.append(swarm.fuse('signal', 'arb', now_ms=now, mode='mean')['value'])
    emit('01_contextual_trust', learned_mse=mse(learned_errors, refs[cut:]), mean_mse=mse(mean_errors, refs[cut:]),
         limitation='training references externally supplied; shared faults need independent reference')
    diagnosis = swarm.diagnose('signal', 'arb', now_ms=now, reference=refs[-1], tolerance=2)
    emit('02_fault_vs_change', suspect_count=len(diagnosis['suspects']), diagnosis=diagnosis,
         limitation='single seeded fault instrument check, not population-level diagnostic accuracy')
    plan = swarm.plan('signal', 'arb', now_ms=now, budget=2)
    emit('03_active_measurement', requested_count=len(plan), requested_nodes=[c['node_id'] for c in plan],
         limitation='capability-aware oldest-first baseline; information-gain optimizer is a research extension')
    emit('04_pipeline_evolution', heldout_mse=mse(filtered, refs[cut:]), fixed_mse=mse(fixed, refs[cut:]),
         pipeline=asdict(trained), raw_event_count=len(events), archive_size=len(archive.entries))
    decision = transfer_decision(trained, base, noisy[cut:], refs[cut:])
    decision['validation_scope'] = decision.pop('claim')
    emit('05_selective_capsule', **decision, limitation='local validation result; independent post-adoption test required')
    contrast = processing_contrast({'raw': [refs[-1]]*5, 'value': refs[-1]+5}, reference=refs[-1])
    emit('06_processing_audit', **contrast)
    # Physical sensor dropout is represented by stale samples, not fake zero measurements.
    future = now+11000
    empty = swarm.fuse('signal', 'arb', now_ms=future)
    emit('07_dropout_reconfiguration', stale_contributors=empty['count'], estimate=empty['value'],
         limitation='availability instrument check; live reallocation tested separately')
    raw_bytes = len(canonical({'raw': noisy}).encode()); feature_bytes = len(canonical({'mean': sum(noisy)/len(noisy)}).encode())
    emit('08_information_level', raw_payload_bytes=raw_bytes, feature_payload_bytes=feature_bytes,
         limitation='application payload bytes only; no claimed Wi-Fi energy savings')
    twin = SensorTwin.fit(refs[:cut], [2*x+3 for x in refs[:cut]])
    emit('09_sensor_twin', heldout_mse=mse([twin.predict(x) for x in refs[cut:]], [2*x+3 for x in refs[cut:]]),
         twin=asdict(twin), limitation='linear synthetic calibration, not a complete physical network twin')
    disturbed = [v for v in perturb(refs[cut:], rng=rng, amplitude=1.5, bias=0.4) if v is not None]
    competition = coevolve(refs[:cut], seed=seed, rounds=6)
    competitor = Pipeline(**competition['pipeline'])
    evolved, _ = competitor.process(disturbed); fixed, _ = base.process(disturbed)
    emit('10_disturbance_competition', heldout_mse=mse(evolved, refs[cut:]), fixed_mse=mse(fixed, refs[cut:]),
         limitation='bounded co-adaptation, independent noisy held-out sequence; not biological Red Queen evidence',
         training=competition, rng=rng.snapshot())
    return rows
