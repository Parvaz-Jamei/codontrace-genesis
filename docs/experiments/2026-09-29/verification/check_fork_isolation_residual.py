"""B4 residual probe: are two arms built from ONE captured payload isolated?

Captures a single fork payload, builds arm A and arm B from it, and reports:

  * whether the restored ``population`` / ``world`` / ``element_grid`` objects are
    the same Python object across arms (shared state) or distinct (isolated);
  * whether the payload is JSON-safe (a strict superset of the old contract);
  * whether each arm is still byte-identical to the original engine's tail.

Run with PYTHONPATH pointing at the tree under test.
"""

from __future__ import annotations

import hashlib
import json
import sys

from codontrace.engine_runtime import GenesisEngine
from codontrace.genesis.runtime_profiles import GenesisRuntimeProfile


def spec(seed: int, tick_count: int):
    return GenesisRuntimeProfile.life_loop_world(
        seed=seed, tick_count=tick_count, population=6
    )


def pop_digest(result) -> str:
    return hashlib.sha256(
        json.dumps(result.snapshot.to_dict(), sort_keys=True, default=str).encode()
    ).hexdigest()


def main() -> int:
    seed, k, n = 31, 3, 2
    total = k + n

    parent = GenesisEngine.from_spec(spec(seed, total))
    parent.run_ticks(k)
    payload = parent.capture_fork()

    try:
        json.dumps(payload)
        payload_json_safe = True
    except (TypeError, ValueError) as exc:
        payload_json_safe = False
        json_error = f"{type(exc).__name__}: {exc}"
    else:
        json_error = None

    arm_a = GenesisEngine.from_fork(spec(seed, total), payload)
    arm_b = GenesisEngine.from_fork(spec(seed, total), payload)

    shared_population = arm_a.runner.population is arm_b.runner.population
    shared_world = arm_a.runner.world is arm_b.runner.world
    shared_element_grid = arm_a.element_grid is arm_b.element_grid
    shared_with_parent_population = arm_a.runner.population is parent.runner.population

    # advance arm A one tick, then check whether arm B's population moved at all
    pop_a_before = json.dumps(arm_a.runner.population.to_dict(), sort_keys=True, default=str)
    pop_b_before = json.dumps(arm_b.runner.population.to_dict(), sort_keys=True, default=str)
    arm_a.run_ticks(1)
    pop_a_after = json.dumps(arm_a.runner.population.to_dict(), sort_keys=True, default=str)
    pop_b_after = json.dumps(arm_b.runner.population.to_dict(), sort_keys=True, default=str)
    a_moved = pop_a_before != pop_a_after
    b_moved_when_a_moved = pop_b_before != pop_b_after

    arm_a.run_ticks(n - 1)
    result_b = arm_b.run_ticks(n)

    # definitive alias test: mutate an object INSIDE arm A's population in place and
    # see whether arm B (or the parent) observes it.
    def first_organism(population):
        for attr in ("organisms", "members", "_organisms"):
            value = getattr(population, attr, None)
            if value:
                return next(iter(value.values())) if isinstance(value, dict) else value[0]
        return None

    organism_a = first_organism(arm_a.runner.population)
    organism_b = first_organism(arm_b.runner.population)
    organism_parent = first_organism(parent.runner.population)
    inplace_alias_observed = None
    inplace_alias_target = None
    if organism_a is not None and hasattr(organism_a, "id"):
        marker = f"task10_alias_{id(organism_a)}"
        original_id = organism_a.id
        organism_a.id = marker
        inplace_alias_target = organism_b is organism_a
        if organism_b is not None and getattr(organism_b, "id", None) == marker:
            inplace_alias_observed = "arm_b"
        elif organism_parent is not None and getattr(organism_parent, "id", None) == marker:
            inplace_alias_observed = "parent"
        else:
            inplace_alias_observed = "neither"
        organism_a.id = original_id

    original = GenesisEngine.from_spec(spec(seed, total))
    original_result = original.run_ticks(total)
    tail = original_result.ticks[k:]

    def identical(result) -> bool:
        return (
            [t.index for t in result.ticks] == [t.index for t in tail]
            and [t.digest() for t in result.ticks] == [t.digest() for t in tail]
            and pop_digest(result) == pop_digest(original_result)
        )

    report = {
        "payload_json_safe": payload_json_safe,
        "payload_json_error": json_error,
        "payload_has_live_objects_key": "live_objects" in payload,
        "fork_isolation": getattr(arm_a, "fork_isolation", None),
        "fork_state_exact": getattr(arm_a, "fork_state_exact", None),
        "arm_a_population_is_arm_b_population": shared_population,
        "arm_a_world_is_arm_b_world": shared_world,
        "arm_a_element_grid_is_arm_b_element_grid": shared_element_grid,
        "arm_a_population_is_parent_population": shared_with_parent_population,
        "arm_a_population_moved_after_its_tick": a_moved,
        "arm_b_population_moved_when_arm_a_advanced": b_moved_when_a_moved,
        "arm_b_first_organism_is_arm_a_first_organism": inplace_alias_target,
        "inplace_mutation_visible_in": inplace_alias_observed,
        "arm_a_matches_original_tail": identical(arm_a._last_result),
        "arm_b_matches_original_tail": identical(result_b),
    }
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
