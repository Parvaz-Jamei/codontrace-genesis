"""Synthetic protocol/adapter demonstration; no firmware or hardware claim."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from codontrace.swarm.experiments import hello, reading
from codontrace.swarm.runtime import SwarmCoordinator
from codontrace.swarm.sensors import fdc_sample


def demonstrate(output: Path) -> dict:
    output.mkdir(parents=True,exist_ok=False)
    swarm=SwarmCoordinator('lab',journal=output/'events.jsonl',journal_segment_bytes=1024)
    row={'channel':0,'status':'Ok','raw24':0,'capacitancePf':3.125,'capdacCode':1,'capdacEnabled':True,'diagnosticFlags':0}
    channel,payload=fdc_sample(row,variant='FDC1004',config_id='fdc1')
    m=hello('lab','fdc');m['schema']='genesis_swarm_v2';m['payload']['channels']={'s':channel}
    swarm.ingest(m,now_ms=1000)
    sample=reading('lab','fdc',1,1000,0.);sample['schema']='genesis_swarm_v2';sample['payload'].update(payload)
    swarm.ingest(sample,now_ms=1000)
    for node,kind,value,extras in [('imu','vector',[1.,2.,3.],{'axes':['x','y','z'],'coordinate_frame':'body'}),
                                  ('switch','boolean',True,{}),('event','category','open',{}),
                                  ('vibration','waveform',[1.,0.,-1.],{'length':3,'sample_period_us':1000})]:
        descriptor={'value_type':kind,'measurement_model':'direct','feature_id':node,'source_unit':'1','config_id':'source1',**extras}
        m=hello('lab',node);m['schema']='genesis_swarm_v2';m['payload']['channels']={'s':{'quantity':node,'unit':'1','descriptor':descriptor}}
        swarm.ingest(m,now_ms=1000)
        sample=reading('lab',node,1,1000,value);sample['schema']='genesis_swarm_v2';sample['payload'].update(valid=True,status='ok',config_id='source1')
        swarm.ingest(sample,now_ms=1000)
    swarm.set_status('stopped',now_ms=1000)
    snapshot=swarm.snapshot(now_ms=1000)
    result={'synthetic':True,'physical_validation':False,'snapshot':snapshot}
    (output/'snapshot.json').write_text(json.dumps(result,indent=2,allow_nan=False))
    return result


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',type=Path,required=True)
    demonstrate(parser.parse_args().output)
