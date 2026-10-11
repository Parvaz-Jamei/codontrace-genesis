"""Record real digital-engine generations for the Atlas (not physical sensor data)."""
from __future__ import annotations

import argparse
from pathlib import Path

from codontrace.genesis.engine import GenesisEngine
from codontrace.genesis.runtime_profiles import GenesisRuntimeProfile
from codontrace.visualization import SimulationRecorder


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--generations',type=int,default=24);p.add_argument('--population',type=int,default=16)
    args=p.parse_args()
    if not 1<=args.generations<=1000 or not 2<=args.population<=1000:
        p.error('generations 1..1000 and population 2..1000 required')
    for seed in (7,8,9):
        engine=GenesisEngine.from_spec(GenesisRuntimeProfile.life_loop_world(seed=seed,tick_count=args.generations,population=args.population))
        SimulationRecorder(args.output).attach(engine)
        result=engine.run_ticks()
        assert result.validate_consistency().passed
        print(f'seed {seed}: {len(result.ticks)} real engine generations recorded',flush=True)


if __name__=='__main__':main()
