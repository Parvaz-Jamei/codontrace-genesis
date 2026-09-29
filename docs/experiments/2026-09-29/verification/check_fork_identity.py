"""913f18e identity cells + unpatched negative control (run against either tree).

For each K in {0, 3} and N in {1, 2, 5}:

    original = engine(spec).run_ticks(K + N)
    fork     = engine(spec).run_ticks(K) then capture_fork() then from_fork().run_ticks(N)

and the fork continuation must be identical to the original tail on
  (a) tick index, (b) tick digest, (c) generation digest, (d) population digest.

Run with PYTHONPATH pointing at whichever tree is under test; the script prints the
tree it actually imported so a stale PYTHONPATH is visible.

    set PYTHONPATH=<tree>\\src
    set PYTHONUTF8=1
    python test-runs/verify/check_fork_identity.py --tree <tree>
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys

from codontrace.engine_runtime import GenesisEngine, __file__ as ENGINE_FILE
from codontrace.genesis.runtime_profiles import GenesisRuntimeProfile


def spec(seed: int, tick_count: int):
    return GenesisRuntimeProfile.life_loop_world(
        seed=seed, tick_count=tick_count, population=6
    )


def pop_digest(result) -> str:
    snapshot = result.snapshot
    payload = json.dumps(snapshot.to_dict(), sort_keys=True, default=str)
    return hashlib.sha256(payload.encode()).hexdigest()


def cell(seed: int, k: int, n: int) -> dict[str, object]:
    total = k + n
    original = GenesisEngine.from_spec(spec(seed, total))
    original_result = original.run_ticks(total)

    parent = GenesisEngine.from_spec(spec(seed, total))
    parent.run_ticks(k)
    payload = parent.capture_fork()
    child = GenesisEngine.from_fork(spec(seed, total), payload)
    child_result = child.run_ticks(n)

    orig_tail = original_result.ticks[k:]
    child_ticks = child_result.ticks

    index_ok = [t.index for t in child_ticks] == [t.index for t in orig_tail]
    tick_digest_ok = [t.digest() for t in child_ticks] == [t.digest() for t in orig_tail]
    gen_digest_ok = [
        t.generation_result.digest() for t in child_ticks
    ] == [t.generation_result.digest() for t in orig_tail]
    pop_digest_ok = pop_digest(child_result) == pop_digest(original_result)

    return {
        "K": k,
        "N": n,
        "child_indices": [t.index for t in child_ticks],
        "original_tail_indices": [t.index for t in orig_tail],
        "index_ok": index_ok,
        "tick_digest_ok": tick_digest_ok,
        "generation_digest_ok": gen_digest_ok,
        "population_digest_ok": pop_digest_ok,
        "all_four_ok": all([index_ok, tick_digest_ok, gen_digest_ok, pop_digest_ok]),
        "fork_isolation": getattr(child, "fork_isolation", None),
        "fork_state_exact": getattr(child, "fork_state_exact", None),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--tree", default="unknown")
    parser.add_argument("--seed", type=int, default=31)
    args = parser.parse_args()

    print(f"tree under test : {args.tree}")
    print(f"engine module   : {ENGINE_FILE}")
    print(f"seed            : {args.seed}")

    cells = []
    for k in (0, 3):
        for n in (1, 2, 5):
            result = cell(args.seed, k, n)
            cells.append(result)
            print(json.dumps(result, indent=2, sort_keys=True))

    passed = sum(1 for item in cells if item["all_four_ok"])
    print(f"\n=== identity cells {passed}/6 PASS ===")
    for item in cells:
        print(
            f"  K={item['K']} N={item['N']} "
            f"index={item['index_ok']} tick={item['tick_digest_ok']} "
            f"gen={item['generation_digest_ok']} pop={item['population_digest_ok']}"
        )
    return 0 if passed == 6 else 1


if __name__ == "__main__":
    sys.exit(main())
