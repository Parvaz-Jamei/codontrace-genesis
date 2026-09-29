"""Task-7 diagnostic: capture_fork/from_fork continuation is not byte-identical.

Localises the missing state by comparing the original engine at tick K with a
restored fork at tick K, then tests candidate repairs at runtime.
Raw output is the printed JSON.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[3] / "codontrace-genesis"
sys.path.insert(0, str(REPO / "src"))

from codontrace.engine_runtime import GenesisEngine  # noqa: E402
from codontrace.engine_spec import GenesisExperimentSpec  # noqa: E402

SEED = 31
report: dict[str, Any] = {"seed": SEED, "task": "task-7", "cells": {}, "bisect": {}}


def _safe(fn: Any, fallback: str = "<err>") -> str:
    try:
        value = fn()
        return value if isinstance(value, str) else str(value)
    except Exception as exc:  # noqa: BLE001
        return f"{fallback}:{type(exc).__name__}"


def engine_state(engine: Any) -> dict[str, Any]:
    return {
        "tick_index_offset": int(getattr(engine, "_tick_offset", -1)),
        "n_tick_results": len(getattr(engine, "_tick_results", [])),
        "n_snapshots": len(getattr(engine, "_snapshots", [])),
        "population_generation": int(getattr(engine.runner.population, "generation", -1)),
        "population_tick": int(getattr(engine.runner.population, "tick", -1)),
        "n_organisms": len(list(engine.runner.population.organisms)),
        "world_digest": _safe(lambda: engine.runner.world.digest()),
        "element_grid_digest": _safe(lambda: engine.element_grid.digest()) if engine.element_grid is not None else None,
        "qd_digest": _safe(lambda: engine.qd_archive.digest()) if engine.qd_archive is not None else None,
        "nexus_layer": type(engine.runner.nexus_layer).__name__ if engine.runner.nexus_layer is not None else None,
        "nexus_digest": _safe(lambda: engine.runner.nexus_layer.digest()) if engine.runner.nexus_layer is not None else None,
        "population_to_dict_hash": _safe(lambda: __import__("hashlib").sha256(json.dumps(engine.runner.population.to_dict(), sort_keys=True, default=str).encode()).hexdigest()[:16]),
    }


def run_cell(k: int, n: int) -> dict[str, Any]:
    spec = GenesisExperimentSpec(tick_count=0, seed=SEED)
    original = GenesisEngine.from_spec(spec)
    original.run_ticks(k)
    fork = original.capture_fork()
    state_at_fork = engine_state(original)
    restored = GenesisEngine.from_fork(spec, fork)
    state_restored = engine_state(restored)
    orig_result = original.run_ticks(n)
    rest_result = restored.run_ticks(n)
    return {
        "k": k,
        "n": n,
        "tick_index_original": [t.index for t in orig_result.ticks],
        "tick_index_restored": [t.index for t in rest_result.ticks],
        "tick_digest_original": [t.digest()[:16] for t in orig_result.ticks],
        "tick_digest_restored": [t.digest()[:16] for t in rest_result.ticks],
        "generation_digest_original": [t.generation_result.digest()[:16] for t in orig_result.ticks],
        "generation_digest_restored": [t.generation_result.digest()[:16] for t in rest_result.ticks],
        "tick_digests_equal": [t.digest() for t in orig_result.ticks] == [t.digest() for t in rest_result.ticks],
        "generation_digests_equal": [t.generation_result.digest() for t in orig_result.ticks]
        == [t.generation_result.digest() for t in rest_result.ticks],
        "state_at_fork": state_at_fork,
        "state_restored": state_restored,
        "state_diff": {key: (state_at_fork[key], state_restored[key]) for key in state_at_fork if state_at_fork[key] != state_restored[key]},
        "seed_digests_original": [t.seed if hasattr(t, "seed") else None for t in orig_result.ticks],
    }


def bisect_organisms(k: int = 3) -> dict[str, Any]:
    """Compare each organism attribute between the original and a restored fork."""

    spec = GenesisExperimentSpec(tick_count=0, seed=SEED)
    original = GenesisEngine.from_spec(spec)
    original.run_ticks(k)
    fork = original.capture_fork()
    restored = GenesisEngine.from_fork(spec, fork)
    orgs_o = sorted(original.runner.population.organisms, key=lambda o: str(o.id))
    orgs_r = sorted(restored.runner.population.organisms, key=lambda o: str(o.id))
    out: dict[str, Any] = {"n_original": len(orgs_o), "n_restored": len(orgs_r), "ids_equal": [str(o.id) for o in orgs_o] == [str(o.id) for o in orgs_r]}
    if not orgs_o or not orgs_r or not out["ids_equal"]:
        return out
    o, r = orgs_o[0], orgs_r[0]
    names = sorted(
        n
        for n in dir(o)
        if not n.startswith("__") and not callable(getattr(o, n, None))
    )
    differing: dict[str, Any] = {}
    for name in names:
        try:
            vo = getattr(o, name)
            vr = getattr(r, name)
        except Exception:  # noqa: BLE001
            continue
        try:
            same = bool(vo == vr)
        except Exception:  # noqa: BLE001
            same = repr(vo) == repr(vr)
        if not same:
            differing[name] = {
                "original": repr(vo)[:120],
                "restored": repr(vr)[:120],
                "type_original": type(vo).__name__,
                "type_restored": type(vr).__name__,
            }
    out["organism_id"] = str(o.id)
    out["n_attributes_checked"] = len(names)
    out["differing_attributes"] = differing
    out["population_to_dict_equal"] = original.runner.population.to_dict() == restored.runner.population.to_dict()
    return out


def repair_probe(k: int = 3, n: int = 2, repair: str = "none") -> dict[str, Any]:
    """Test a candidate repair applied only in-process (no repo edit)."""

    spec = GenesisExperimentSpec(tick_count=0, seed=SEED)
    original = GenesisEngine.from_spec(spec)
    original.run_ticks(k)
    fork = original.capture_fork()
    restored = GenesisEngine.from_fork(spec, fork)
    if repair == "nexus+qd+grid":
        restored.runner.nexus_layer = original.runner.nexus_layer
        restored.qd_archive = original.qd_archive
        restored.element_grid = original.element_grid
    elif repair == "replace_population_object":
        restored.runner.population = original.runner.population
    elif repair == "replace_world+population+nexus":
        restored.runner.population = original.runner.population
        restored.runner.world = original.runner.world
        restored.runner.nexus_layer = original.runner.nexus_layer
        restored.qd_archive = original.qd_archive
    orig_result = original.run_ticks(n)
    rest_result = restored.run_ticks(n)
    return {
        "repair": repair,
        "k": k,
        "n": n,
        "tick_digests_equal": [t.digest() for t in orig_result.ticks] == [t.digest() for t in rest_result.ticks],
        "generation_digests_equal": [t.generation_result.digest() for t in orig_result.ticks]
        == [t.generation_result.digest() for t in rest_result.ticks],
        "original": [t.digest()[:12] for t in orig_result.ticks],
        "restored": [t.digest()[:12] for t in rest_result.ticks],
    }


def main() -> int:
    spec = GenesisExperimentSpec(tick_count=0, seed=SEED)
    report["spec_digest"] = spec.digest()
    report["spec_fields"] = sorted(getattr(type(spec), "__dataclass_fields__", {}).keys())
    for k in (0, 3):
        for n in (1, 2, 5):
            report["cells"][f"K{k}N{n}"] = run_cell(k, n)
    report["bisect"] = bisect_organisms(3)
    report["repairs"] = [
        repair_probe(3, 2, "none"),
        repair_probe(3, 2, "nexus+qd+grid"),
        repair_probe(3, 2, "replace_population_object"),
        repair_probe(3, 2, "replace_world+population+nexus"),
    ]
    out = Path(__file__).resolve().parents[1] / "logs" / "task7_fork_identity.json"
    out.write_text(json.dumps(report, indent=2, sort_keys=True, default=str), encoding="utf-8")
    compact = {
        "cells": {
            key: {
                "tick_idx_ok": cell["tick_index_original"] == cell["tick_index_restored"],
                "tick_digests_equal": cell["tick_digests_equal"],
                "generation_digests_equal": cell["generation_digests_equal"],
                "state_diff": cell["state_diff"],
            }
            for key, cell in report["cells"].items()
        },
        "bisect_differing": list(report["bisect"].get("differing_attributes", {}).keys()),
        "bisect_population_to_dict_equal": report["bisect"].get("population_to_dict_equal"),
        "repairs": [{k: v for k, v in r.items() if k in ("repair", "tick_digests_equal", "generation_digests_equal")} for r in report["repairs"]],
    }
    print(json.dumps(compact, indent=1, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
