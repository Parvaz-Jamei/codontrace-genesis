"""Synthetic input wiring demo, not a physical sensor experiment."""
from codontrace.genesis.engine import GenesisEngine
from codontrace.genesis.runtime_profiles import GenesisRuntimeProfile
from codontrace.swarm import SwarmEngineLink
from codontrace.swarm.experiments import hello, reading
from codontrace.swarm.service import coordinator


def main():
    import time
    swarm = coordinator('demo')
    now = int(time.time()*1000)
    swarm.ingest(hello('demo', 'synthetic'), now_ms=now)
    swarm.ingest(reading('demo', 'synthetic', 1, now, 2), now_ms=now)
    engine = GenesisEngine.from_spec(GenesisRuntimeProfile.life_loop_world(seed=7, tick_count=2, population=2))
    # Example only: a unitless synthetic signal is mapped to a virtual resource.
    # Real physical inputs require a domain-specific, calibrated mapping.
    def mapper(world, fusion):
        world.place_resource((3, 3), fusion['value'])
    link = SwarmEngineLink(swarm, quantity='signal', unit='arb', environment_mapper=mapper).attach(engine)
    result = link.run_ticks()
    print({'synthetic': True, 'physical_validation': False, 'engine_consistency': result.validate_consistency().passed})


if __name__ == '__main__':
    main()
