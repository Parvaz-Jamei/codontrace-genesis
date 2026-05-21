"""WorldEvent and timeline export example for CodonTrace current alpha."""

from __future__ import annotations

try:
    from ._path_bootstrap import ensure_src_path
except ImportError:  # direct script or runpy execution outside the examples package
    import sys as _sys
    from pathlib import Path as _Path

    _EXAMPLES_DIR = _Path(__file__).resolve().parent
    if str(_EXAMPLES_DIR) not in _sys.path:
        _sys.path.insert(0, str(_EXAMPLES_DIR))
    from _path_bootstrap import ensure_src_path

ensure_src_path()

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from codontrace import CausalReplay, RunRecorder, WhiteBoxAgent, World2D

world = World2D(20, 10)
recorder = RunRecorder()

recorder.place_resource(world, (10, 5), 8.0, step=0, reason="initial food")
world_event_only_digest = world.digest()
replayed = CausalReplay.apply_world_events(World2D(20, 10), recorder.trace.world_events)
assert replayed.digest() == world_event_only_digest

agent = WhiteBoxAgent.quick(genome="101111000", initial_atp=6.0, position=(10, 5))
agent.step(world, recorder.trace)

bundle_json = recorder.trace.to_bundle_json()
engine_json = recorder.trace.to_engine_json()

print("bundle_digest", recorder.trace.bundle_digest())
print("engine_events", len(recorder.trace.to_engine_events()))
print("world-event-replay-match", replayed.digest() == world_event_only_digest)
print("world_event_only_digest", world_event_only_digest)
print("final_world_digest_after_agent_actions", world.digest())
print("bundle_json_size", len(bundle_json))
print("engine_json_size", len(engine_json))
