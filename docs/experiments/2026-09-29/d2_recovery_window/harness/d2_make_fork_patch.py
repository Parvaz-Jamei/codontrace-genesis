"""Task-7: generate PROPOSED_CHANGE_fork.patch and prove the fix + negative control.

Run:  python test-runs/d2/harness/d2_make_fork_patch.py
Writes: test-runs/d2/PROPOSED_CHANGE_fork.patch, test-runs/d2/logs/task7_fork_proof.json
"""

from __future__ import annotations

import difflib
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
REPO = ROOT / "codontrace-genesis"
D2 = ROOT / "test-runs" / "d2"
TARGET = REPO / "src" / "codontrace" / "engine_runtime.py"
sys.path.insert(0, str(REPO / "src"))

CAPTURE_OLD = '''            "parent_snapshot_id": parent_snapshot_id,
        }
'''
CAPTURE_NEW = '''            "parent_snapshot_id": parent_snapshot_id,
            # Exact in-process branch state.  ``population.to_dict()`` is a
            # reduced payload: the rebuilt organisms differ from the source in
            # ``action_runtime_config``, ``causal_graph`` and ``ribosome``, and a
            # fresh engine also carries a freshly built ``qd_archive`` and
            # ``nexus_layer``.  Those differences change the next generation
            # digest, so the live objects are carried for an exact fork.
            "live_objects": {
                "population": self.runner.population,
                "world": self.runner.world,
                "nexus_layer": self.runner.nexus_layer,
                "qd_archive": self.qd_archive,
                "element_grid": self.element_grid,
            },
            "exact_state": True,
        }
'''

FROM_FORK_OLD = '''        engine = cls.from_spec(spec, generation_boundary_observers=generation_boundary_observers)
        engine.runner.population = PopulationState.from_dict(dict(fork["population"]))
        engine.runner.world = World2D.from_dict(dict(fork["world"]))
'''
FROM_FORK_NEW = '''        engine = cls.from_spec(spec, generation_boundary_observers=generation_boundary_observers)
        source = fork.get("live_objects") or {}
        if source:
            # Exact fork: attach the captured live objects so every per-object
            # field (organism action config, causal graph, ribosome, stigmergy
            # layer, QD archive, world bookkeeping) matches the checkpoint.
            # Each object is deep-copied per restore so two arms branched from
            # one checkpoint payload cannot alias each other.  Where deepcopy is
            # impossible (a mappingproxy inside the graph) the live reference is
            # attached and the isolation map records it explicitly.
            import copy as _copy

            isolation: dict[str, str] = {}

            def _take(name: str, value: Any) -> Any:
                try:
                    taken = _copy.deepcopy(value)
                except Exception:
                    isolation[name] = "shared_reference"
                    return value
                isolation[name] = "deepcopy"
                return taken

            engine.runner.population = _take("population", source["population"])
            engine.runner.world = _take("world", source["world"])
            if source.get("nexus_layer") is not None:
                engine.runner.nexus_layer = _take("nexus_layer", source["nexus_layer"])
            if source.get("qd_archive") is not None:
                engine.qd_archive = _take("qd_archive", source["qd_archive"])
            if source.get("element_grid") is not None:
                engine.element_grid = _take("element_grid", source["element_grid"])
            engine.fork_isolation = isolation
            engine.fork_state_exact = all(value == "deepcopy" for value in isolation.values())
        else:
            # Reduced fallback: serialisable payload only.  Documented as lossy.
            engine.runner.population = PopulationState.from_dict(dict(fork["population"]))
            engine.runner.world = World2D.from_dict(dict(fork["world"]))
'''


def build_patch() -> dict[str, Any]:
    text = TARGET.read_text(encoding="utf-8")
    patched = text
    for old, new in ((CAPTURE_OLD, CAPTURE_NEW), (FROM_FORK_OLD, FROM_FORK_NEW)):
        assert old in patched, old[:70]
        patched = patched.replace(old, new, 1)
    diff = "".join(
        difflib.unified_diff(
            text.splitlines(keepends=True),
            patched.splitlines(keepends=True),
            fromfile="a/src/codontrace/engine_runtime.py",
            tofile="b/src/codontrace/engine_runtime.py",
            n=3,
        )
    )
    out = D2 / "PROPOSED_CHANGE_fork.patch"
    out.write_text(diff, encoding="utf-8")
    return {"path": str(out), "lines": diff.count("\n"), "sha256": hashlib.sha256(diff.encode()).hexdigest()[:16]}


def apply_runtime_patch() -> None:
    import codontrace.engine_runtime as er

    src = TARGET.read_text(encoding="utf-8")
    for old, new in ((CAPTURE_OLD, CAPTURE_NEW), (FROM_FORK_OLD, FROM_FORK_NEW)):
        src = src.replace(old, new, 1)
    ns = dict(vars(er))
    exec(compile(src, str(TARGET), "exec"), ns)  # noqa: S102 - executes the patched module text
    er.GenesisEngine.capture_fork = ns["GenesisEngine"].__dict__["capture_fork"]
    er.GenesisEngine.from_fork = ns["GenesisEngine"].__dict__["from_fork"]


def population_hash(engine: Any) -> str:
    payload = json.dumps(engine.runner.population.to_dict(), sort_keys=True, default=str)
    return hashlib.sha256(payload.encode()).hexdigest()[:16]


def cell(k: int, n: int) -> dict[str, Any]:
    from codontrace.engine_runtime import GenesisEngine
    from codontrace.engine_spec import GenesisExperimentSpec

    spec = GenesisExperimentSpec(tick_count=0, seed=31)
    original = GenesisEngine.from_spec(spec)
    original.run_ticks(k)
    fork = original.capture_fork()
    restored = GenesisEngine.from_fork(spec, fork)
    orig = original.run_ticks(n)
    rest = restored.run_ticks(n)
    ticks_o = [t.index for t in orig.ticks][-n:]
    ticks_r = [t.index for t in rest.ticks][-n:]
    dig_o = [t.digest() for t in orig.ticks][-n:]
    dig_r = [t.digest() for t in rest.ticks][-n:]
    gen_o = [t.generation_result.digest() for t in orig.ticks][-n:]
    gen_r = [t.generation_result.digest() for t in rest.ticks][-n:]
    return {
        "k": k,
        "n": n,
        "tick_index_equal": ticks_o == ticks_r,
        "tick_digests_equal": dig_o == dig_r,
        "generation_digests_equal": gen_o == gen_r,
        "population_digest_equal": population_hash(original) == population_hash(restored),
        "original_tick_digests": [d[:12] for d in dig_o],
        "restored_tick_digests": [d[:12] for d in dig_r],
    }


def two_arm_isolation(k: int = 3, n: int = 2) -> dict[str, Any]:
    """Two arms branched from ONE fork payload must each match the original."""

    from codontrace.engine_runtime import GenesisEngine
    from codontrace.engine_spec import GenesisExperimentSpec

    spec = GenesisExperimentSpec(tick_count=0, seed=31)
    original = GenesisEngine.from_spec(spec)
    original.run_ticks(k)
    fork = original.capture_fork()
    arm_a = GenesisEngine.from_fork(spec, fork)
    arm_b = GenesisEngine.from_fork(spec, fork)
    isolation = {
        "arm_a": getattr(arm_a, "fork_isolation", None),
        "arm_b": getattr(arm_b, "fork_isolation", None),
        "state_exact_a": getattr(arm_a, "fork_state_exact", None),
        "state_exact_b": getattr(arm_b, "fork_state_exact", None),
        "objects_aliased": arm_a.runner.population is arm_b.runner.population,
    }
    orig = original.run_ticks(n)
    a = arm_a.run_ticks(n)
    b = arm_b.run_ticks(n)
    orig_dig = [t.digest() for t in orig.ticks][-n:]
    return {
        "k": k,
        "n": n,
        **isolation,
        "arm_a_matches_original": [t.digest() for t in a.ticks][-n:] == orig_dig,
        "arm_b_matches_original": [t.digest() for t in b.ticks][-n:] == orig_dig,
        "arms_match_each_other": [t.digest() for t in a.ticks][-n:] == [t.digest() for t in b.ticks][-n:],
    }


def interleaved_isolation(k: int = 3, ticks: int = 3) -> dict[str, Any]:
    """Worst case for shared references: alternate the two arms tick by tick."""

    from codontrace.engine_runtime import GenesisEngine
    from codontrace.engine_spec import GenesisExperimentSpec

    spec = GenesisExperimentSpec(tick_count=0, seed=31)
    original = GenesisEngine.from_spec(spec)
    original.run_ticks(k)
    fork = original.capture_fork()
    arm_a = GenesisEngine.from_fork(spec, fork)
    arm_b = GenesisEngine.from_fork(spec, fork)
    orig_digests: list[str] = []
    a_digests: list[str] = []
    b_digests: list[str] = []
    for _ in range(ticks):
        orig_digests.append(original.run_ticks(1).ticks[-1].digest())
        a_digests.append(arm_a.run_ticks(1).ticks[-1].digest())
        b_digests.append(arm_b.run_ticks(1).ticks[-1].digest())
    return {
        "k": k,
        "ticks": ticks,
        "interleaved_arm_a_matches_original": a_digests == orig_digests,
        "interleaved_arm_b_matches_original": b_digests == orig_digests,
        "arms_converge": a_digests == b_digests,
        "original": [d[:12] for d in orig_digests],
        "arm_a": [d[:12] for d in a_digests],
        "arm_b": [d[:12] for d in b_digests],
    }


def main() -> int:
    patch = build_patch()
    evidence: dict[str, Any] = {"task": "task-7", "seed": 31, "patch": patch}
    # Negative control on the unpatched tree.
    evidence["negative_control_unpatched"] = [cell(k, n) for k in (0, 3) for n in (1, 2, 5)]
    apply_runtime_patch()
    evidence["patched"] = [cell(k, n) for k in (0, 3) for n in (1, 2, 5)]
    evidence["two_arm_isolation"] = [two_arm_isolation(3, 2), two_arm_isolation(0, 3)]
    evidence["interleaved_isolation"] = [interleaved_isolation(3, 3), interleaved_isolation(0, 3)]
    evidence["negative_control_fails"] = not all(
        c["tick_digests_equal"] and c["generation_digests_equal"] for c in evidence["negative_control_unpatched"]
    )
    evidence["patched_all_equal"] = all(
        c["tick_index_equal"] and c["tick_digests_equal"] and c["generation_digests_equal"] and c["population_digest_equal"]
        for c in evidence["patched"]
    )
    evidence["multi_arm_branching_safe"] = all(
        c["arm_a_matches_original"] and c["arm_b_matches_original"] and c["arms_match_each_other"]
        for c in evidence["two_arm_isolation"]
    ) and all(
        c["interleaved_arm_a_matches_original"] and c["interleaved_arm_b_matches_original"] and c["arms_converge"]
        for c in evidence["interleaved_isolation"]
    )
    out = D2 / "logs" / "task7_fork_proof.json"
    out.write_text(json.dumps(evidence, indent=2, sort_keys=True, default=str), encoding="utf-8")
    print(json.dumps({
        "patch": patch,
        "negative_control_fails": evidence["negative_control_fails"],
        "patched_all_equal": evidence["patched_all_equal"],
        "multi_arm_branching_safe": evidence["multi_arm_branching_safe"],
        "isolation_objects": evidence["two_arm_isolation"][0]["arm_a"],
        "shared_reference_objects": sorted(
            k for k, v in evidence["two_arm_isolation"][0]["arm_a"].items() if v == "shared_reference"
        ),
        "interleaved": [
            {k: v for k, v in c.items() if k in ("k", "ticks", "interleaved_arm_a_matches_original", "interleaved_arm_b_matches_original", "arms_converge")}
            for c in evidence["interleaved_isolation"]
        ],
    }, indent=1, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
