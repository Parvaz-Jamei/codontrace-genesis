"""Fork isolation patch: prove an independent per-arm population + identity cells.

Deliverable target: PopulationState carries a complete serialisable full-state
payload so from_fork rebuilds an INDEPENDENT population object (mappingproxy
registries rule out deepcopy of the whole population).

This script (a) diagnoses the three lossy organism attributes, (b) applies the
candidate repair at runtime, (c) re-runs the 6/6 identity cells, (d) asserts
per-arm population object distinctness AND mutation isolation, (e) runs the
negative control on the landed un-repaired from_fork.
"""

from __future__ import annotations

import copy
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
REPO = ROOT / "codontrace-genesis"
D2 = ROOT / "test-runs" / "d2"
sys.path.insert(0, str(REPO / "src"))

from codontrace.engine_runtime import GenesisEngine  # noqa: E402
from codontrace.engine_spec import GenesisExperimentSpec  # noqa: E402
from codontrace.genesis.population import PopulationState  # noqa: E402

SEED = 31
ATTRS = ("action_runtime_config", "causal_graph", "ribosome")


def fork_payload(k: int) -> tuple[Any, dict[str, Any], Any]:
    spec = GenesisExperimentSpec(tick_count=0, seed=SEED)
    engine = GenesisEngine.from_spec(spec)
    engine.run_ticks(k)
    return engine, engine.capture_fork(), spec


def diagnose() -> dict[str, Any]:
    engine, fork, _ = fork_payload(3)
    rebuilt = PopulationState.from_dict(dict(fork["population"]))
    o = sorted(engine.runner.population.organisms, key=lambda x: str(x.id))[0]
    n = sorted(rebuilt.organisms, key=lambda x: str(x.id))[0]
    out: dict[str, Any] = {"organism_id": str(o.id), "attrs": {}}
    for attr in ATTRS:
        vo, vn = getattr(o, attr), getattr(n, attr)
        entry: dict[str, Any] = {
            "type": type(vo).__name__,
            "rebuilt_is_same_object": vo is vn,
            "rebuilt_equal": repr(vo) == repr(vn),
            "has_to_dict": hasattr(vo, "to_dict"),
            "has_from_dict": hasattr(type(vo), "from_dict"),
        }
        try:
            copy.deepcopy(vo)
            entry["deepcopy"] = "ok"
        except Exception as exc:  # noqa: BLE001
            entry["deepcopy"] = f"{type(exc).__name__}: {exc}"[:80]
        if entry["has_to_dict"] and entry["has_from_dict"]:
            try:
                entry["roundtrip_equal"] = repr(type(vo).from_dict(vo.to_dict())) == repr(vo)
            except Exception as exc:  # noqa: BLE001
                entry["roundtrip_equal"] = f"error {type(exc).__name__}"
        out["attrs"][attr] = entry
    return out


def rebuild_population(fork: dict[str, Any], source_engine: Any) -> tuple[Any, dict[str, str]]:
    """The candidate repair: fresh population object + complete per-organism state."""

    population = PopulationState.from_dict(dict(fork["population"]))
    src = {str(x.id): x for x in source_engine.runner.population.organisms}
    strategies: dict[str, str] = {}
    for org in population.organisms:
        ref = src.get(str(org.id))
        if ref is None:
            continue
        for attr in ATTRS:
            value = getattr(ref, attr, None)
            if value is None:
                continue
            try:
                setattr(org, attr, copy.deepcopy(value))
                strategies[attr] = "deepcopy"
                continue
            except Exception:  # noqa: BLE001
                pass
            try:
                cls = type(value)
                setattr(org, attr, cls.from_dict(value.to_dict()))
                strategies[attr] = "to_dict/from_dict"
                continue
            except Exception:  # noqa: BLE001
                pass
            strategies[attr] = "UNSERIALISABLE_kept_shared_reference"
    return population, strategies


def restored_engine(spec: Any, fork: dict[str, Any], source_engine: Any, *, repair: bool) -> Any:
    engine = GenesisEngine.from_fork(spec, fork)
    if repair:
        population, strategies = rebuild_population(fork, source_engine)
        engine.runner.population = population
        engine.runner.world = copy.deepcopy(source_engine.runner.world)
        engine.runner.nexus_layer = copy.deepcopy(source_engine.runner.nexus_layer)
        engine.qd_archive = copy.deepcopy(source_engine.qd_archive)
        engine.repair_strategies = strategies
    return engine


def identity_cells(*, repair: bool) -> list[dict[str, Any]]:
    rows = []
    for k in (0, 3):
        for n in (1, 2, 5):
            _, fork, spec = fork_payload(k)
            engine, fork2, spec = fork_payload(k)
            original = engine
            restored = restored_engine(spec, fork2, original, repair=repair)
            orig = original.run_ticks(n)
            rest = restored.run_ticks(n)
            rows.append(
                {
                    "k": k,
                    "n": n,
                    "tick_index_equal": [t.index for t in orig.ticks][-n:] == [t.index for t in rest.ticks][-n:],
                    "tick_digests_equal": [t.digest() for t in orig.ticks][-n:] == [t.digest() for t in rest.ticks][-n:],
                    "generation_digests_equal": [t.generation_result.digest() for t in orig.ticks][-n:]
                    == [t.generation_result.digest() for t in rest.ticks][-n:],
                }
            )
    return rows


def isolation_test(*, repair: bool) -> dict[str, Any]:
    engine, fork, spec = fork_payload(3)
    arm_a = restored_engine(spec, fork, engine, repair=repair)
    arm_b = restored_engine(spec, fork, engine, repair=repair)
    distinct = arm_a.runner.population is not arm_b.runner.population
    strategies = getattr(arm_a, "repair_strategies", None)
    # mutation isolation: damage arm A's population state, then compare arm B to the original
    target = sorted(arm_a.runner.population.organisms, key=lambda x: str(x.id))[0]
    target.atp_state.debit_runtime(
        min(5.0, float(target.atp_state.runtime_available)),
        tick=3,
        organism_id=str(target.id),
        codon="test",
        action="isolation_probe",
        reason="mutation_isolation_probe",
    )
    original_digests: list[str] = []
    a_digests: list[str] = []
    b_digests: list[str] = []
    for _ in range(3):
        original_digests.append(engine.run_ticks(1).ticks[-1].digest())
        a_digests.append(arm_a.run_ticks(1).ticks[-1].digest())
        b_digests.append(arm_b.run_ticks(1).ticks[-1].digest())
    return {
        "population_objects_distinct": distinct,
        "repair_strategies": strategies,
        "arm_a_differs_after_mutation": a_digests != original_digests,
        "arm_b_unchanged_by_arm_a_mutation": b_digests == original_digests,
        "mutation_isolation_holds": a_digests != original_digests and b_digests == original_digests,
        "original": [d[:12] for d in original_digests],
        "arm_a": [d[:12] for d in a_digests],
        "arm_b": [d[:12] for d in b_digests],
    }


def main() -> int:
    report: dict[str, Any] = {"seed": SEED, "diagnosis": diagnose()}
    report["negative_control_unrepaired"] = {
        "identity_cells": identity_cells(repair=False),
        "isolation": isolation_test(repair=False),
    }
    report["candidate_repair"] = {
        "identity_cells": identity_cells(repair=True),
        "isolation": isolation_test(repair=True),
    }
    report["identity_cells_pass_unrepaired"] = all(
        c["tick_digests_equal"] and c["generation_digests_equal"] for c in report["negative_control_unrepaired"]["identity_cells"]
    )
    report["identity_cells_pass_repaired"] = all(
        c["tick_index_equal"] and c["tick_digests_equal"] and c["generation_digests_equal"]
        for c in report["candidate_repair"]["identity_cells"]
    )
    report["isolation_holds_repaired"] = bool(
        report["candidate_repair"]["isolation"]["population_objects_distinct"]
        and report["candidate_repair"]["isolation"]["mutation_isolation_holds"]
    )
    report["isolation_holds_unrepaired"] = bool(
        report["negative_control_unrepaired"]["isolation"]["population_objects_distinct"]
        and report["negative_control_unrepaired"]["isolation"]["mutation_isolation_holds"]
    )
    out = D2 / "logs" / "fork_isolation_proof.json"
    out.write_text(json.dumps(report, indent=2, sort_keys=True, default=str), encoding="utf-8")
    print(json.dumps({
        "diagnosis": report["diagnosis"],
        "unrepaired": {"identity_pass": report["identity_cells_pass_unrepaired"], "isolation": report["isolation_holds_unrepaired"]},
        "repaired": {"identity_pass": report["identity_cells_pass_repaired"], "isolation": report["isolation_holds_repaired"],
                      "strategies": report["candidate_repair"]["isolation"]["repair_strategies"]},
        "mutation_isolation": report["candidate_repair"]["isolation"]["mutation_isolation_holds"],
    }, indent=1, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
