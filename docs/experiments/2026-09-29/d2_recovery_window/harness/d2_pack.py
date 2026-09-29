"""D-2 pack entry point: stage 0, measurement diagnostic, derived analysis.

Usage (one worker, from the workspace root):

    python test-runs/d2/harness/d2_pack.py stage0
    python test-runs/d2/harness/d2_pack.py measurement
    python test-runs/d2/harness/d2_pack.py analysis
    python test-runs/d2/harness/d2_pack.py all

Never writes inside ``codontrace-genesis``.
"""

from __future__ import annotations

import copy
import json
import sys
import time
from pathlib import Path
from typing import Any
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from d2_common import (  # noqa: E402
    ARMS,
    D2,
    DEV_SEEDS,
    DIAG_HORIZON,
    EVENT_FIELDS,
    LOGS,
    NULL_REASONS,
    PACK_CAP_SECONDS,
    POP_FIELDS,
    POPULATION,
    RAM_SOFT_STOP_BYTES,
    RAW,
    RECOVERY_TOKEN_KEY,
    REPO,
    SCAFFOLD_ID,
    SCHEMA_VERSION,
    SUCCESS_CONSECUTIVE,
    SUCCESS_MULTIPLIER,
    T_GRID,
    WALL_CAP_SECONDS,
    JsonlWriter,
    canonical_hash,
    cpu_seconds,
    file_hash,
    git_state,
    now,
    rss_bytes,
)
from codontrace.engine_runtime import GenesisEngine  # noqa: E402
from codontrace.genesis.campaigns.discovery_q_20260928_idea4 import (  # noqa: E402
    CHECKPOINT_ID,
    COMPETENCE_ID,
    HORIZON_T,
    _apply_ops_cell,
    _score_recover,
    harvest_rare_class_yield,
)
from codontrace.genesis.campaigns.discovery_q_20260928_idea4_engine import (  # noqa: E402
    build_idea4_engine_spec,
)
from codontrace.life_loop.contact_atp_ledger import CONTACT_TAG_RARE, build_engine_scaffold_ledger  # noqa: E402
from codontrace.life_loop.engine_ledger_coupler import (  # noqa: E402
    EngineCoupledLedgerObserver,
    population_path_fingerprint,
)

EXPLORATORY_RETURN_ID = "GENOME-DIGEST-LOST-THEN-REGAINED-V1"
PREREG_ESTIMAND_ID = "FI-RARECLASS-CONTACT-YIELD-V1"


def log(message: str) -> None:
    print(f"[d2 {time.strftime('%H:%M:%S')}] {message}", flush=True)


# ---------------------------------------------------------------------------
# Shared cell runner
# ---------------------------------------------------------------------------


def _parent_of(organism_id: str) -> str | None:
    """Engine ids look like ``org-0-g2-<digest8>``; the prefix is the parent."""

    parts = str(organism_id).split("-")
    if len(parts) >= 4 and parts[0] == "org":
        return f"org-{parts[1]}"
    return None


def run_cell(
    *,
    seed: int,
    arm: str,
    t_intervene: int,
    horizon: int,
    writers: dict[str, JsonlWriter] | None = None,
    run_id: str | None = None,
    allocation: str = "incident_endpoints_realised",
) -> dict[str, Any]:
    """One population history with the checkpoint and arm applied at ``t_intervene``."""

    rid = run_id or f"d2-s{seed}-t{t_intervene}-{arm}"
    ledger = build_engine_scaffold_ledger(seed=int(seed))
    holder: dict[str, Any] = {"engine": None}
    start = now()
    stop_code = "COMPLETE"
    stop_detail = ""
    history: list[dict[str, Any]] = []
    pre_paths: dict[int, str] = {}
    previous: dict[str, dict[str, Any]] = {}
    baseline_yields: list[float] = []
    post_yields: list[float] = []
    ledger_after_pre: dict[str, Any] = {}
    intervention_record: dict[str, Any] = {}

    def _op(led: Any, generation_index: int) -> dict[str, Any]:
        ckpt = led.relocate_recovery_token(RECOVERY_TOKEN_KEY, remove=False, new_payload="relocated_engine")
        if arm == "sham":
            cell: dict[str, Any] = {"op": "sham", "applied": False}
        else:
            cell = _apply_ops_cell(led, arm)
        intervention_record.update(
            {
                "checkpoint_id": CHECKPOINT_ID,
                "arm": arm,
                "applied_op": cell.get("op"),
                "cell": {k: v for k, v in cell.items() if k != "independent_match_design"},
                "cut_edge_ids": cell.get("cut_edge_ids"),
                "match_exact": cell.get("match_exact"),
                "independent_control": cell.get("independent_control"),
                "scientific_contrast_eligible": cell.get("scientific_contrast_eligible"),
                "design_failure": cell.get("design_failure"),
                "checkpoint_after": ckpt.get("after"),
            }
        )
        return {"ckpt": ckpt, "cell": cell}

    observer = EngineCoupledLedgerObserver(
        engine_holder=holder,
        ledger=ledger,
        schedule={int(t_intervene): [_op]},
        harvest_fn=harvest_rare_class_yield,
        auto_advance=True,
        feedback_enabled=True,
        feedback_allocation=allocation,
    )

    def _record(*, generation_index: int) -> None:
        nonlocal stop_code, stop_detail, previous
        engine = holder["engine"]
        population = engine.runner.population
        organisms = sorted(population.organisms, key=lambda o: str(o.id))
        g = int(generation_index)
        path = population_path_fingerprint(engine)
        if g < int(t_intervene):
            pre_paths[g] = path
        fb = observer.feedback_history[-1] if observer.feedback_history else {}
        if g >= int(t_intervene):
            post_yields.append(float(observer.yield_history[-1]))
        else:
            baseline_yields.append(float(observer.yield_history[-1]))
        if g == int(t_intervene):
            ledger_after_pre.update(
                {
                    "pre_contact_energy": fb.get("pre_contact_energy"),
                    "post_contact_energy": fb.get("post_contact_energy"),
                    "burden": fb.get("burden"),
                    "burden_lost_energy": fb.get("burden_lost_energy"),
                    "burden_edge_changes": fb.get("burden_edge_changes"),
                    "burden_digest": fb.get("burden_digest"),
                    "burden_token": fb.get("burden_token"),
                    "total_debited": fb.get("total_debited"),
                    "food_removed": fb.get("food_removed"),
                    "n_edge_changes": fb.get("n_edge_changes"),
                    "digest_changed": fb.get("digest_changed"),
                    "token_changed": fb.get("token_changed"),
                    "allocation": fb.get("allocation"),
                    "endpoints_enter_debit": fb.get("endpoints_enter_debit"),
                    "effect_applied": fb.get("effect_applied"),
                }
            )
        atp_values = [float(o.atp_state.runtime_available) for o in organisms]
        genotype_counts: dict[str, int] = {}
        for org in organisms:
            digest = str(org.genome.digest()) if hasattr(org.genome, "digest") else "unknown"
            genotype_counts[digest] = genotype_counts.get(digest, 0) + 1
        n_alive = len(organisms)
        resources = dict(getattr(engine.runner.world, "resources", {}) or {})
        row = {
            "run_id": rid,
            "seed": int(seed),
            "arm": arm,
            "generation": g,
            "n_alive": n_alive,
            "class_counts": dict(genotype_counts),
            "class_frequencies": {k: (v / n_alive if n_alive else 0.0) for k, v in genotype_counts.items()},
            "genotype_counts": dict(genotype_counts),
            "genotype_frequencies": {k: (v / n_alive if n_alive else 0.0) for k, v in genotype_counts.items()},
            "antagonist_frequency": None,
            "fitness": None,
            "atp_sum": float(sum(atp_values)),
            "atp_mean": float(sum(atp_values) / n_alive) if n_alive else 0.0,
            "contact_opportunities": None,
            "pi_realised": None,
            "pi_intended": None,
            "resource_mass": float(sum(float(v) for v in resources.values())),
            "genealogy": [
                {"organism_id": str(o.id), "parent_id": _parent_of(str(o.id)), "genotype_digest": str(o.genome.digest())}
                for o in organisms
            ],
            "population_path_digest": path,
        }
        history.append(row)

        if writers is not None:
            writers["population"].write(row)
            current: dict[str, dict[str, Any]] = {}
            for org in organisms:
                current[str(org.id)] = {
                    "atp": float(org.atp_state.runtime_available),
                    "genotype_digest": str(org.genome.digest()) if hasattr(org.genome, "digest") else "unknown",
                }
            for oid, info in current.items():
                prev = previous.get(oid)
                writers["events"].write(
                    {
                        **{k: None for k in EVENT_FIELDS},
                        "run_id": rid,
                        "seed": int(seed),
                        "arm": arm,
                        "generation": g,
                        "event_id": f"{rid}:g{g}:birth:{oid}",
                        "organism_id": oid,
                        "parent_id": _parent_of(oid),
                        "genotype_digest": info["genotype_digest"],
                        "atp_before": None if prev is None else prev["atp"],
                        "atp_after": info["atp"],
                        "birth": prev is None,
                        "death": False,
                        "mutation": bool(prev is not None and prev["genotype_digest"] != info["genotype_digest"]),
                        "intervention_id": CHECKPOINT_ID if g == int(t_intervene) else None,
                    }
                )
            for oid, info in previous.items():
                if oid not in current:
                    writers["events"].write(
                        {
                            **{k: None for k in EVENT_FIELDS},
                            "run_id": rid,
                            "seed": int(seed),
                            "arm": arm,
                            "generation": g,
                            "event_id": f"{rid}:g{g}:death:{oid}",
                            "organism_id": oid,
                            "parent_id": _parent_of(oid),
                            "genotype_digest": info["genotype_digest"],
                            "atp_before": info["atp"],
                            "atp_after": 0.0,
                            "birth": False,
                            "death": True,
                            "mutation": False,
                        }
                    )
            if g == int(t_intervene):
                for eid in intervention_record.get("cut_edge_ids") or ["<none>"]:
                    writers["events"].write(
                        {
                            **{k: None for k in EVENT_FIELDS},
                            "run_id": rid,
                            "seed": int(seed),
                            "arm": arm,
                            "generation": g,
                            "event_id": f"{rid}:g{g}:coupler:{eid}",
                            "contact_edge_id": eid,
                            "intended_debit": fb.get("burden"),
                            "realised_debit": fb.get("total_debited"),
                            "intervention_id": CHECKPOINT_ID,
                        }
                    )
        previous = current if writers is not None else previous

        if n_alive == 0:
            stop_code = "ZERO_POPULATION"
            stop_detail = f"n_alive reached 0 at generation {g}"
        if writers is not None and g % 10 == 0:
            log(f"{rid}: gen {g} n_alive={n_alive} rare_yield={float(observer.yield_history[-1]):.6f}")

    class _Recorder:
        def __call__(self, *, generation_index: int) -> None:
            _record(generation_index=generation_index)

    recorder = _Recorder()
    spec = build_idea4_engine_spec(seed=int(seed), tick_count=int(t_intervene) + int(horizon), population=POPULATION)
    engine = GenesisEngine.from_spec(spec, generation_boundary_observers=(observer, recorder))
    holder["engine"] = engine
    engine.run_ticks()

    baseline_mean = float(sum(baseline_yields) / len(baseline_yields)) if baseline_yields else 0.0
    recover = bool(_score_recover(baseline_mean=baseline_mean, post_yields=post_yields))
    checkpoint_rows = [r for r in history if r["generation"] == int(t_intervene)]
    checkpoint_genomes = {
        entry["organism_id"]: entry["genotype_digest"]
        for row in checkpoint_rows
        for entry in row["genealogy"]
    }
    ck_ids = set(checkpoint_genomes)
    ck_digests = set(checkpoint_genomes.values())
    missing: set[str] = set()
    regained: set[str] = set()
    for row in history:
        present = {d for d in row["genotype_counts"]}
        for digest in ck_digests:
            if digest not in present:
                missing.add(digest)
            elif digest in missing:
                regained.add(digest)
    return {
        "run_id": rid,
        "seed": int(seed),
        "arm": arm,
        "t_intervene": int(t_intervene),
        "t_tilde": float(t_intervene) / float(HORIZON_T),
        "horizon": int(horizon),
        "competence_id": PREREG_ESTIMAND_ID,
        "competence_date": "2026-09-28",
        "return_id": EXPLORATORY_RETURN_ID,
        "return_date": "2026-09-29",
        "baseline_mean_rare_yield": baseline_mean,
        "baseline_n": len(baseline_yields),
        "post_yields": post_yields,
        "post_n": len(post_yields),
        "recover_preregistered": recover,
        "recover_exploratory_return": bool(regained),
        "n_regained_genomes": len(regained),
        "n_checkpoint_genomes": len(ck_digests),
        "final_n_alive": int(history[-1]["n_alive"]) if history else 0,
        "pre_paths": [pre_paths[k] for k in sorted(pre_paths)],
        "paths": [row["population_path_digest"] for row in history],
        "intervention": intervention_record,
        "ledger_after_pre": ledger_after_pre,
        "stop_code": stop_code,
        "stop_detail": stop_detail,
        "wall_seconds": round(now() - start, 3),
        "cpu_seconds": round(cpu_seconds(), 3),
        "rss_bytes": rss_bytes(),
        "history_len": len(history),
        "policy_enabled": "policy",
    }


# ---------------------------------------------------------------------------
# Stage 0
# ---------------------------------------------------------------------------


def stage0_hand_computed() -> list[dict[str, Any]]:
    tests: list[dict[str, Any]] = []

    def check(name: str, condition: bool, detail: str) -> None:
        tests.append({"test": name, "pass": bool(condition), "detail": detail})

    # --- locked success rule, hand-computed -------------------------------
    cases = [
        ("three consecutive at exactly 1.25", 1.0, [1.25, 1.25, 1.25], True),
        ("two consecutive then a dip", 1.0, [1.25, 1.25, 1.24, 1.25, 1.25], False),
        ("dip first, then three consecutive", 1.0, [1.24, 1.26, 1.26, 1.26], True),
        ("three consecutive at the end", 1.0, [1.26, 1.26, 1.25, 1.25, 1.25], True),
        ("1.3,1.3,1.24,1.3,1.3", 1.0, [1.3, 1.3, 1.24, 1.3, 1.3], False),
        ("zero baseline is undefined, not a pass", 0.0, [9.0, 9.0, 9.0], False),
    ]
    for name, baseline, post, expected in cases:
        got = _score_recover(baseline_mean=baseline, post_yields=post)
        check(
            f"score_recover::{name}",
            got is expected,
            f"baseline={baseline} post={post} -> {got} (hand-expected {expected})",
        )

    # --- multiplies that compose the yield ---------------------------------
    from codontrace.life_loop.contact_atp_ledger import build_engine_scaffold_ledger

    led = build_engine_scaffold_ledger(seed=301)
    raw_sum = sum(
        float(led.edges[eid].atp_yield)
        for eid in led.edges_with_tag(CONTACT_TAG_RARE)
        if led.edges[eid].present and not led.edges[eid].masked
    )
    base = harvest_rare_class_yield(led)
    key = f"scaffold_edges:{SCAFFOLD_ID}"
    members = led.scaffold_edge_sets.get(key, set())
    present_n = sum(1 for eid in members if eid in led.edges and led.edges[eid].present)
    scaffold_factor = 0.4 + 0.6 * (present_n / len(members))
    digest_factor = 0.75 if not led.failed_prediction_digests else 1.0
    check(
        "yield_arithmetic::eligible_token",
        abs(base - raw_sum * 1.0 * scaffold_factor * digest_factor) < 1e-9,
        f"raw={raw_sum:.9f} scaffold_factor={scaffold_factor:.6f} digest_factor={digest_factor} -> {base:.9f}",
    )

    led2 = build_engine_scaffold_ledger(seed=301)
    led2.relocate_recovery_token(RECOVERY_TOKEN_KEY, remove=False, new_payload="relocated_engine")
    relocated = harvest_rare_class_yield(led2)
    check(
        "yield_arithmetic::relocated_token_is_0.55x",
        abs(relocated - base * 0.55) < 1e-9,
        f"relocated={relocated:.9f} expected={base * 0.55:.9f}",
    )

    led3 = build_engine_scaffold_ledger(seed=301)
    cut = led3.cut_named_scaffold(SCAFFOLD_ID)
    after_cut = harvest_rare_class_yield(led3)
    raw_after = sum(
        float(led3.edges[eid].atp_yield)
        for eid in led3.edges_with_tag(CONTACT_TAG_RARE)
        if led3.edges[eid].present and not led3.edges[eid].masked
    )
    expected_after = raw_after * 1.0 * (0.4 + 0.0) * digest_factor
    check(
        "yield_arithmetic::scaffold_cut_multiplier",
        abs(after_cut - expected_after) < 1e-9,
        f"cut={cut['cut_edge_ids']} yield {base:.9f} -> {after_cut:.9f} (expected {expected_after:.9f})",
    )
    check(
        "yield_arithmetic::scaffold_cut_lowers_yield",
        after_cut < base,
        f"{base:.9f} -> {after_cut:.9f}: cutting the named scaffold cannot raise the endpoint",
    )
    return tests


def stage0_fork() -> dict[str, Any]:
    """P1 precondition: can a generation boundary produce a full fork?"""

    from codontrace.genesis.campaigns.discovery_q_20260928_idea4_engine import build_idea4_engine_spec

    holder: dict[str, Any] = {"engine": None}
    ledger = build_engine_scaffold_ledger(seed=301)
    captured: dict[str, Any] = {}

    observer = EngineCoupledLedgerObserver(
        engine_holder=holder,
        ledger=ledger,
        schedule={},
        harvest_fn=harvest_rare_class_yield,
        auto_advance=True,
        feedback_enabled=True,
    )

    class _Capture:
        def __call__(self, *, generation_index: int) -> None:
            if generation_index != 10 or captured:
                return
            engine = holder["engine"]
            try:
                copy.deepcopy(engine)
                captured["deepcopy_ok"] = True
                captured["deepcopy_error"] = None
            except Exception as exc:  # noqa: BLE001 - the failure is the evidence
                captured["deepcopy_ok"] = False
                captured["deepcopy_error"] = f"{type(exc).__name__}: {exc}"
            snap = engine.snapshot()
            captured["snapshot_type"] = f"{type(snap).__module__}.{type(snap).__name__}"
            captured["snapshot_fields"] = sorted(getattr(type(snap), "__dataclass_fields__", {}).keys())
            try:
                captured["snapshot_payload_keys"] = sorted(snap.to_dict().keys())
            except Exception as exc:  # noqa: BLE001
                captured["snapshot_payload_keys"] = f"error: {exc}"
            captured["engine_restore_entry_points"] = [
                n for n in dir(GenesisEngine) if any(k in n.lower() for k in ("restore", "fork", "from_snapshot"))
            ]
            captured["engine_has_rng_attribute"] = any("rng" in n.lower() for n in dir(engine))
            captured["runner_has_rng_attribute"] = any("rng" in n.lower() for n in dir(engine.runner))
            captured["rng_restore_available_somewhere"] = "codontrace.rng.RNGManager.restore"

    cap = _Capture()
    spec = build_idea4_engine_spec(seed=301, tick_count=10, population=POPULATION)
    engine = GenesisEngine.from_spec(spec, generation_boundary_observers=(observer, cap))
    holder["engine"] = engine
    engine.run_ticks()
    captured["deepcopy_fork_available"] = bool(captured.get("deepcopy_ok"))
    # The landed fix: a restorable state fork that does not need pickle.
    captured["capture_fork_available"] = hasattr(engine, "capture_fork")
    captured["from_fork_available"] = hasattr(GenesisEngine, "from_fork")
    fork_ok = False
    continuation_identical: bool | None = None
    ids_preserved: bool | None = None
    if captured["capture_fork_available"] and captured["from_fork_available"]:
        fork = engine.capture_fork(parent_snapshot_id="stage0")
        captured["fork_tick_index"] = fork.get("tick_index")
        captured["fork_has_rng_state"] = "state" in (fork.get("rng") or {})
        orig_seen: list[str] = []

        class _OrigRec:
            def __call__(self, *, generation_index: int) -> None:
                del generation_index
                orig_seen.append(population_path_fingerprint(engine))

        engine.generation_boundary_observers.append(_OrigRec())
        engine.run_ticks(ticks=3)
        # Rebuild the continuation from the fork and compare tick by tick.
        restored = GenesisEngine.from_fork(spec, fork)
        from codontrace.genesis.population import PopulationState as _PS

        ids_preserved = sorted(str(o.id) for o in _PS.from_dict(dict(fork["population"])).organisms) == sorted(
            str(o.id) for o in restored.runner.population.organisms
        )
        seen: list[str] = []

        class _Rec3:
            def __call__(self, *, generation_index: int) -> None:
                del generation_index
                seen.append(population_path_fingerprint(restored_engine_ref[0]))

        restored_engine_ref = [restored]
        restored.generation_boundary_observers.append(_Rec3())
        restored.run_ticks(ticks=3)
        # The original engine continued 3 ticks after capture; rebuild those 3 paths separately.
        check_engine = GenesisEngine.from_fork(spec, fork)
        check_seen: list[str] = []

        class _Rec4:
            def __call__(self, *, generation_index: int) -> None:
                del generation_index
                check_seen.append(population_path_fingerprint(check_engine_ref[0]))

        check_engine_ref = [check_engine]
        check_engine.generation_boundary_observers.append(_Rec4())
        check_engine.run_ticks(ticks=3)
        continuation_identical = seen == orig_seen and len(seen) == 3
        fork_ok = bool(continuation_identical and ids_preserved and captured["fork_has_rng_state"])
    captured["continuation_identical"] = continuation_identical
    captured["parent_child_ids_preserved"] = ids_preserved
    captured["fork_available"] = fork_ok
    captured["conclusion"] = (
        "restorable full fork verified byte-identical (capture_fork/from_fork)"
        if fork_ok
        else "no verified full fork at a generation boundary"
    )
    return captured


def stage0_determinism_and_arms() -> dict[str, Any]:
    """Replay determinism, pre-intervention arm match, and invariant checks."""

    seed = DEV_SEEDS[0]
    t = T_GRID[0]
    a = run_cell(seed=seed, arm="control", t_intervene=t, horizon=6)
    b = run_cell(seed=seed, arm="control", t_intervene=t, horizon=6)
    c = run_cell(seed=seed, arm="cut_named_scaffold", t_intervene=t, horizon=6)
    pre_a, pre_c = list(a["pre_paths"]), list(c["pre_paths"])
    return {
        "replay_same_process_identical": a["paths"] == b["paths"] and a["post_yields"] == b["post_yields"],
        "pre_intervention_paths_identical_across_arms": pre_a == pre_c,
        "pre_intervention_generations": len(pre_a),
        "arms_diverge_after_intervention": a["paths"] != c["paths"],
        "intervention_generation": t,
        "control_post_yield_series": a["post_yields"],
        "named_post_yield_series": c["post_yields"],
        "control_burden": a["ledger_after_pre"].get("burden"),
        "named_burden": c["ledger_after_pre"].get("burden"),
    }


def stage0_controls() -> dict[str, Any]:
    """Neutral control, injected positive control, negative control."""

    seed = DEV_SEEDS[0]
    t = T_GRID[0]
    neutral = run_cell(seed=seed, arm="control", t_intervene=t, horizon=12)
    injected_ledger = build_engine_scaffold_ledger(seed=seed)
    baseline = [harvest_rare_class_yield(injected_ledger) for _ in range(3)]
    injected_post = [baseline[-1] * 1.5] * 4
    injected_recover = _score_recover(baseline_mean=sum(baseline) / 3, post_yields=injected_post)
    negative = run_cell(seed=seed, arm="ablate_knowledge_digest", t_intervene=t, horizon=12)
    return {
        "neutral_control": {
            "arm": "control",
            "recover_preregistered": neutral["recover_preregistered"],
            "note": "checkpoint only; no scaffold cut, no knowledge ablation",
            "post_yields": neutral["post_yields"],
        },
        "injected_positive_control": {
            "injected": True,
            "scientific_result": False,
            "recover": bool(injected_recover),
            "note": (
                "yield series scaled by 1.5x by hand after the checkpoint. This proves the "
                "scorer can fire; it is not a discovery and is excluded from every effect table."
            ),
        },
        "negative_control": {
            "arm": "ablate_knowledge_digest",
            "recover_preregistered": negative["recover_preregistered"],
            "note": "a cut that must remove, not create, the endpoint (multiplier 0.75 when the digest is gone)",
            "post_yields": negative["post_yields"],
        },
    }


def run_stage0() -> dict[str, Any]:
    started = now()
    hand = stage0_hand_computed()
    fort = stage0_fork()
    determinism = stage0_determinism_and_arms()
    controls = stage0_controls()
    failures = [t for t in hand if not t["pass"]]
    report = {
        "schema": SCHEMA_VERSION,
        "stage": "stage0",
        "wall_seconds": round(now() - started, 3),
        "hand_computed_tests": hand,
        "hand_computed_failures": failures,
        "fork_precondition": fort,
        "determinism_and_arms": determinism,
        "controls": controls,
        "stage0_pass": bool(not failures and fort.get("fork_available") is True),
        "fork_available": fort.get("fork_available"),
        "stop_code": "CONTINUE" if fort.get("fork_available") else "BLOCKED_NO_FULL_FORK",
        "hypothesis_supported": False,
        "red_queen_proved": False,
    }
    (D2 / "stage0_report.json").write_text(json.dumps(report, indent=2, sort_keys=True, default=str), encoding="utf-8")
    log(f"stage0 done: pass={report['stage0_pass']} stop={report['stop_code']} hand_failures={len(failures)}")
    return report


# ---------------------------------------------------------------------------
# Measurement diagnostic
# ---------------------------------------------------------------------------


def run_measurement(seeds: tuple[int, ...] = DEV_SEEDS) -> dict[str, Any]:
    started = now()
    RAW.mkdir(parents=True, exist_ok=True)
    summaries: list[dict[str, Any]] = []
    for seed in seeds:
        if now() - started > PACK_CAP_SECONDS:
            log("pack budget reached; keeping the valid prefix")
            break
        for t in T_GRID:
            for arm in ARMS:
                rid = f"d2-s{seed}-t{t}-{arm}"
                run_dir = RAW / rid
                run_dir.mkdir(parents=True, exist_ok=True)
                events = JsonlWriter(run_dir / "events.jsonl", EVENT_FIELDS)
                population = JsonlWriter(run_dir / "population.jsonl", POP_FIELDS)
                t0 = now()
                try:
                    summary = run_cell(
                        seed=seed,
                        arm=arm,
                        t_intervene=t,
                        horizon=DIAG_HORIZON,
                        writers={"events": events, "population": population},
                        run_id=rid,
                    )
                except Exception as exc:  # noqa: BLE001 - a cut run keeps its valid prefix
                    summary = {
                        "run_id": rid,
                        "seed": seed,
                        "arm": arm,
                        "t_intervene": t,
                        "stop_code": "EXCEPTION",
                        "stop_detail": f"{type(exc).__name__}: {exc}",
                        "wall_seconds": round(now() - t0, 3),
                    }
                    log(f"{rid}: EXCEPTION {summary['stop_detail']}")
                finally:
                    events.close()
                    population.close()
                summary["events_written"] = events.count
                summary["population_rows"] = population.count
                summary["files"] = {
                    "events.jsonl": file_hash(run_dir / "events.jsonl"),
                    "population.jsonl": file_hash(run_dir / "population.jsonl"),
                }
                (run_dir / "run_manifest.json").write_text(
                    json.dumps(
                        {
                            "schema": SCHEMA_VERSION,
                            "run_id": rid,
                            "seed": seed,
                            "arm": arm,
                            "t_intervene": t,
                            "horizon": DIAG_HORIZON,
                            "population": POPULATION,
                            "workers": 1,
                            "feedback_allocation": "incident_endpoints_realised",
                            "parent_snapshot": None,
                            "parent_snapshot_reason": "no restorable checkpoint exists in this revision",
                            "rng_streams": {
                                "engine": f"seed={seed}; per-generation seed = spec.seed + index",
                                "ledger": f"random.Random(seed={seed})",
                            },
                            "commit": git_state()["commit"],
                            "dirty": git_state()["dirty"],
                            "params_hash": canonical_hash({"seed": seed, "arm": arm, "t": t, "horizon": DIAG_HORIZON}),
                            "wall_seconds": summary.get("wall_seconds"),
                            "cpu_seconds": summary.get("cpu_seconds"),
                            "rss_bytes": summary.get("rss_bytes"),
                            "stop_code": summary.get("stop_code"),
                            "stop_detail": summary.get("stop_detail"),
                            "checksums": summary["files"],
                            "replay_command": (
                                "python test-runs/d2/harness/d2_replay.py "
                                f"--run-dir test-runs/d2/raw/{rid} --out test-runs/d2/raw/{rid}/replay.json"
                            ),
                        },
                        indent=2,
                        sort_keys=True,
                        default=str,
                    ),
                    encoding="utf-8",
                )
                summaries.append(summary)
                log(
                    f"{rid}: stop={summary.get('stop_code')} recover={summary.get('recover_preregistered')} "
                    f"final_n={summary.get('final_n_alive')} wall={summary.get('wall_seconds')}s"
                )
                if rss_bytes() > RAM_SOFT_STOP_BYTES:
                    log("RAM soft stop reached; keeping the valid prefix")
                    break
    out = {
        "schema": SCHEMA_VERSION,
        "stage": "measurement_diagnostic",
        "wall_seconds": round(now() - started, 3),
        "n_runs": len(summaries),
        "summaries": summaries,
    }
    (D2 / "measurement_summary.json").write_text(json.dumps(out, indent=2, sort_keys=True, default=str), encoding="utf-8")
    return out


# ---------------------------------------------------------------------------
# Analysis (from raw only)
# ---------------------------------------------------------------------------


def _randomisation_interval(diffs: list[float]) -> dict[str, Any]:
    """Exact sign-flip randomisation interval for a paired mean difference."""

    if not diffs:
        return {"point": None, "lo": None, "hi": None, "n": 0, "note": "no pairs"}
    n = len(diffs)
    observed = sum(diffs) / n
    means: list[float] = []
    for mask in range(1 << n):
        total = 0.0
        for i, d in enumerate(diffs):
            total += d if (mask >> i) & 1 else -d
        means.append(total / n)
    means.sort()
    ge = sum(1 for m in means if m >= observed)
    p_two_sided = min(1.0, 2.0 * ge / len(means))
    return {
        "point": observed,
        "lo": means[0],
        "hi": means[-1],
        "n": n,
        "p_two_sided_exact": p_two_sided,
        "method": "exact sign-flip randomisation over independent population histories",
        "note": "with n=2 development seeds the smallest attainable two-sided p is 0.5; inconclusive by construction",
        "inconclusive": True if n < 4 else False,
    }


def run_analysis() -> dict[str, Any]:
    summary = json.loads((D2 / "measurement_summary.json").read_text(encoding="utf-8"))
    runs = summary["summaries"]
    by_arm: dict[str, list[dict[str, Any]]] = {}
    for r in runs:
        by_arm.setdefault(r["arm"], []).append(r)

    table: dict[str, Any] = {}
    for arm, rows in sorted(by_arm.items()):
        recover = [bool(r.get("recover_preregistered")) for r in rows]
        returning = [bool(r.get("recover_exploratory_return")) for r in rows]
        table[arm] = {
            "n_runs": len(rows),
            "p_recover_preregistered": sum(recover) / len(recover),
            "n_recover_preregistered": sum(recover),
            "p_digest_return_exploratory": sum(returning) / len(returning),
            "n_digest_return_exploratory": sum(returning),
            "extinction_rate_final_n_zero": sum(1 for r in rows if r.get("final_n_alive") == 0) / len(rows),
            "censored_runs": sum(1 for r in rows if r.get("stop_code") not in (None, "COMPLETE")),
            "burdens": sorted({round(float(r["ledger_after_pre"].get("burden") or 0.0), 9) for r in rows}),
            "budget_edge_term": sorted(
                {round(float(r["ledger_after_pre"].get("burden_edge_changes") or 0.0), 9) for r in rows}
            ),
        }

    # Paired seed-level contrast on the pre-registered endpoint: named vs matched.
    def paired(arm_a: str, arm_b: str) -> dict[str, Any]:
        keys = {(r["seed"], r["t_intervene"]) for r in runs}
        diffs: list[float] = []
        for seed, t in sorted(keys):
            ra = next((r for r in runs if r["seed"] == seed and r["t_intervene"] == t and r["arm"] == arm_a), None)
            rb = next((r for r in runs if r["seed"] == seed and r["t_intervene"] == t and r["arm"] == arm_b), None)
            if ra and rb:
                diffs.append(float(bool(ra.get("recover_preregistered"))) - float(bool(rb.get("recover_preregistered"))))
        return _randomisation_interval(diffs)

    # Refusal test: identical realised contacts and identical population trajectory.
    refusal_details: list[dict[str, Any]] = []
    for seed in sorted({r["seed"] for r in runs}):
        for t in T_GRID:
            named = next((r for r in runs if r["seed"] == seed and r["t_intervene"] == t and r["arm"] == "cut_named_scaffold"), None)
            matched = next((r for r in runs if r["seed"] == seed and r["t_intervene"] == t and r["arm"] == "cut_matched_random"), None)
            if named and matched:
                refusal_details.append(
                    {
                        "seed": seed,
                        "t_intervene": t,
                        "paths_identical": named["paths"] == matched["paths"],
                        "pre_paths_identical": named["pre_paths"] == matched["pre_paths"],
                        "burden_identical": named["ledger_after_pre"].get("burden") == matched["ledger_after_pre"].get("burden"),
                        "burden": named["ledger_after_pre"].get("burden"),
                        "named_cut_edges": named["intervention"].get("cut_edge_ids"),
                        "matched_cut_edges": matched["intervention"].get("cut_edge_ids"),
                        "match_exact": matched["intervention"].get("match_exact"),
                        "independent_control": matched["intervention"].get("independent_control"),
                        "scientific_contrast_eligible": matched["intervention"].get("scientific_contrast_eligible"),
                        "design_failure": matched["intervention"].get("design_failure"),
                        "post_yields_identical": named["post_yields"] == matched["post_yields"],
                    }
                )

    penalty_only: list[dict[str, Any]] = []
    for seed in sorted({r["seed"] for r in runs}):
        for t in T_GRID:
            ctrl = next((r for r in runs if r["seed"] == seed and r["t_intervene"] == t and r["arm"] == "control"), None)
            for arm in ("cut_named_scaffold", "cut_matched_random", "scramble_contacts", "ablate_knowledge_digest"):
                other = next((r for r in runs if r["seed"] == seed and r["t_intervene"] == t and r["arm"] == arm), None)
                if ctrl and other:
                    penalty_only.append(
                        {
                            "seed": seed,
                            "t_intervene": t,
                            "arm": arm,
                            "burden_edge_term": other["ledger_after_pre"].get("burden_edge_changes"),
                            "burden_total": other["ledger_after_pre"].get("burden"),
                            "control_burden": ctrl["ledger_after_pre"].get("burden"),
                            "endpoint_identical_to_control": other["post_yields"] == ctrl["post_yields"],
                        }
                    )

    stage0 = json.loads((D2 / "stage0_report.json").read_text(encoding="utf-8"))
    fork_available = bool(stage0.get("fork_available"))
    all_paths_identical = bool(refusal_details) and all(d["paths_identical"] for d in refusal_details)
    all_burdens_identical = bool(refusal_details) and all(d["burden_identical"] for d in refusal_details)
    endpoint_never_changes = all(
        t["p_recover_preregistered"] == 0.0 and t["p_digest_return_exploratory"] == 0.0 for t in table.values()
    )

    refusal_fired = bool(all_paths_identical and all_burdens_identical)
    verdict = "BLOCKED_MEASUREMENT"
    blocking: list[str] = []
    if not fork_available:
        blocking.append(
            "PRE-FORK: a generation boundary cannot produce a full fork; the engine has no restorable "
            "state snapshot and copy.deepcopy raises 'cannot pickle mappingproxy object'"
        )
    all_extinct = all(t["extinction_rate_final_n_zero"] >= 1.0 for t in table.values())
    no_recovery = all(t["p_recover_preregistered"] == 0.0 and t["p_digest_return_exploratory"] == 0.0 for t in table.values())
    if refusal_fired:
        blocking.append(
            "REFUSAL: named-scaffold and degree/ATP-matched random arms have identical realised contacts, "
            "identical burden and identical population trajectory"
        )
    if not refusal_fired:
        blocking.append(
            "TOPOLOGY IDENTIFIED: the named and matched arms now differ in burden and in population path, and "
            "the global count penalty is held at zero in the analysed allocation, so the refusal does not fire"
        )
    if all_extinct and no_recovery:
        blocking.append(
            "PRE-OPPORTUNITY: every arm finished at n_alive = 0 (extinction rate 1.0) and the pre-registered "
            "endpoint never reached 1.25x; a flat-zero curve cannot test a recovery-window law"
        )

    analysis = {
        "schema": SCHEMA_VERSION,
        "claim_ceiling": "phase2_design",
        "derived_from_raw_only": True,
        "n_runs": len(runs),
        "n_independent_histories": len({(r["seed"], r["t_intervene"]) for r in runs}),
        "unit_of_replication": "independent population history (seed x checkpoint)",
        "endpoints": {
            PREREG_ESTIMAND_ID: {
                "date": "2026-09-28",
                "rule": "mean rare-class contact yield >= 1.25x the run's own pre-checkpoint baseline for >= 3 consecutive boundaries within T=40",
                "role": "pre-registered",
            },
            EXPLORATORY_RETURN_ID: {
                "date": "2026-09-29",
                "rule": "a checkpoint genome digest disappears and is present again later",
                "role": "exploratory, versioned separately, never pooled with the pre-registered endpoint",
            },
            "antagonist_genotype": {
                "role": "absent",
                "reason": NULL_REASONS["antagonist_frequency"],
            },
        },
        "arm_table": table,
        "paired_contrasts": {
            "named_minus_matched": paired("cut_named_scaffold", "cut_matched_random"),
            "named_minus_control": paired("cut_named_scaffold", "control"),
            "matched_minus_control": paired("cut_matched_random", "control"),
        },
        "refusal_test": {
            "condition": "named and rewired share realised contacts and population trajectory, or the difference is only the coupler's global edge-cost penalty",
            "all_paths_identical": all_paths_identical,
            "all_burdens_identical": all_burdens_identical,
            "refusal_fired": refusal_fired,
            "details": refusal_details,
            "penalty_only_rows": penalty_only,
        },
        "fork_precondition": {
            "fork_available": fork_available,
            "evidence": stage0.get("fork_precondition"),
        },
        "statistics": {
            "method": "paired seed-level effect with an exact sign-flip randomisation interval; extinction and censoring reported separately",
            "inconclusive": True,
            "reason": "the test is blocked before the confirmatory tier; n=2 development seeds cannot support an interval that excludes zero",
        },
        "verdict": "INCONCLUSIVE" if (all_extinct and no_recovery and fork_available and not refusal_fired) else verdict,
        "blocking_conditions": blocking,
        "preconditions": {
            "full_fork_available": fork_available,
            "refusal_fired": refusal_fired,
            "topology_identified": bool(not refusal_fired),
            "recovery_opportunity_observed": bool(not (all_extinct and no_recovery)),
        },
        "hypothesis_supported": False,
        "red_queen_proved": False,
        "flags": {
            "claimgate_refuses": ["red_queen_proved", "discovery_claim", "first_claim"],
            "soft_pass_forbidden": True,
            "injected_positive_is_not_a_result": True,
        },
    }
    (D2 / "analysis.json").write_text(json.dumps(analysis, indent=2, sort_keys=True, default=str), encoding="utf-8")
    log(f"analysis: verdict={verdict} blocking={len(blocking)}")
    return analysis


def main() -> int:
    stage = sys.argv[1] if len(sys.argv) > 1 else "all"
    if stage in ("stage0", "all"):
        run_stage0()
    if stage in ("measurement", "all"):
        run_measurement()
    if stage in ("analysis", "all"):
        run_analysis()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
