"""RQ-1 probe: time-shift host x antagonist contact matrix on the live model.

READ-ONLY with respect to ``codontrace-genesis``.  This script imports the
repository under test and writes only under ``test-runs/rq1/``.

Purpose
-------
RQ-1 asks for a 3x3 host-time x antagonist-time matrix of realised pressure
``pi_realised`` built *outside evolution* from three host snapshots and three
antagonist snapshots of the same dated history, with equal contact
opportunities and resources, plus frozen-antagonist, host-only and
shuffled-time-label controls.

This probe establishes, from raw output of the repository's own code, whether
the live model can supply the inputs of that assay:

  A. Does the live GenesisEngine contain an antagonist genotype population?
  B. Is ``pi_realised`` (graded-affinity ATP debit with reservation) an output
     of the live model's contact route?
  C. Does a full-state checkpoint/fork exist so the arms can start from one
     fork point with independent labelled RNG streams?
  D. What 3x3 cross-time matrix *can* be produced from one dated live history,
     and is it the model's ``pi_realised``?
  E. Does the stage-0 meter behave as pre-specified on hand fixtures
     (instrument only, never a live result)?
  F. Is replay/determinism byte-identical?

Every emitted number is raw evidence.  ``analysis_rq1.py`` derives the summary
from these raw files only.
"""

from __future__ import annotations

import hashlib
import json
import platform
import sys
import time
import traceback
from pathlib import Path

REPO = Path(r"E:\مقاله پزشکی شبیه سازی ویروس\codontrace-genesis")
SRC = REPO / "src"
OUT = Path(__file__).resolve().parent
RAW = OUT / "raw"
RAW.mkdir(parents=True, exist_ok=True)

if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

SCHEMA_VERSION = "rq1_probe_v1"
TIMES = ("past", "now", "future")


# --------------------------------------------------------------------------
# small utilities
# --------------------------------------------------------------------------
def sha256_file(path: Path) -> str | None:
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError:
        return None


def peak_rss_bytes() -> int | None:
    try:
        import psutil  # type: ignore

        return int(psutil.Process().memory_info().rss)
    except Exception:  # noqa: BLE001
        pass
    try:
        import ctypes
        import ctypes.wintypes as wt

        class PROCESS_MEMORY_COUNTERS(ctypes.Structure):
            _fields_ = [
                ("cb", wt.DWORD),
                ("PageFaultCount", wt.DWORD),
                ("PeakWorkingSetSize", ctypes.c_size_t),
                ("WorkingSetSize", ctypes.c_size_t),
                ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
                ("QuotaPagedPoolUsage", ctypes.c_size_t),
                ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
                ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
                ("PagefileUsage", ctypes.c_size_t),
                ("PeakPagefileUsage", ctypes.c_size_t),
            ]

        counters = PROCESS_MEMORY_COUNTERS()
        counters.cb = ctypes.sizeof(PROCESS_MEMORY_COUNTERS)
        handle = ctypes.windll.kernel32.GetCurrentProcess()
        ctypes.windll.psapi.GetProcessMemoryInfo(
            handle, ctypes.byref(counters), counters.cb
        )
        value = int(counters.PeakWorkingSetSize)
        return value if value > 0 else None
    except Exception:  # noqa: BLE001
        return None


def dump(name: str, payload: object) -> None:
    path = RAW / name
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True, default=str) + "\n",
        encoding="utf-8",
    )


def append_jsonl(path: Path, rows: list[dict]) -> None:
    with path.open("a", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True, default=str) + "\n")
        handle.flush()


def repo_head() -> dict:
    head = None
    ref = None
    commit = None
    packed = None
    try:
        head = (REPO / ".git" / "HEAD").read_text(encoding="utf-8").strip()
        if head.startswith("ref:"):
            ref = head.split(" ", 1)[1].strip()
            ref_file = REPO / ".git" / ref
            if ref_file.exists():
                commit = ref_file.read_text(encoding="utf-8").strip()
        elif len(head) == 40:
            commit = head
        if commit is None:
            pr = REPO / ".git" / "packed-refs"
            if pr.exists():
                packed = pr.read_text(encoding="utf-8")
                for line in packed.splitlines():
                    if line and not line.startswith("#") and ref and line.endswith(ref):
                        commit = line.split(" ", 1)[0]
                        break
    except OSError:
        pass
    return {
        "git_executable_available": False,
        "head_file": head,
        "ref": ref,
        "commit": commit,
        "packed_refs_present": packed is not None,
        "dirty_flag": None,
        "dirty_flag_reason": (
            "git executable is not on PATH in this session; the dirty flag "
            "cannot be computed and is recorded as null rather than guessed."
        ),
    }


def source_scan() -> dict:
    """Count the tokens that would have to exist for the RQ-1 inputs."""

    targets = {
        "engine_runtime.py (GenesisEngine)": REPO
        / "src"
        / "codontrace"
        / "engine_runtime.py",
        "genesis/engine.py (facade)": REPO / "src" / "codontrace" / "genesis" / "engine.py",
        "genesis/checkpointing.py": REPO / "src" / "codontrace" / "genesis" / "checkpointing.py",
        "genesis/host_parasite_world.py": REPO
        / "src"
        / "codontrace"
        / "genesis"
        / "host_parasite_world.py",
        "life_loop/contact.py": REPO / "src" / "codontrace" / "life_loop" / "contact.py",
    }
    tokens = (
        "parasite",
        "antagonist",
        "host_parasite",
        "infection",
        "realised",
        "graded_affinity",
        "def fork",
        "restore",
        "from_state",
    )
    out: dict[str, object] = {}
    for label, path in targets.items():
        try:
            text = path.read_text(encoding="utf-8")
        except OSError:
            out[label] = {"sha256": None, "exists": False}
            continue
        counts = {tok: text.count(tok) for tok in tokens}
        out[label] = {
            "exists": True,
            "sha256": sha256_file(path),
            "n_lines": text.count("\n") + 1,
            "token_counts": counts,
        }
    return {"files": out}


# --------------------------------------------------------------------------
# A/B/F: live GenesisEngine probes
# --------------------------------------------------------------------------
def probe_engine_antagonist() -> dict:
    """Run the repo's own Idea-2 engine cell and read its antagonist verdict."""

    from codontrace.genesis.campaigns.discovery_q_20260928_idea2_engine import (
        run_idea2_engine_cell,
    )

    out: dict[str, object] = {"cells": [], "errors": []}
    for seed in (301, 302):
        for cell in ("baseline", "do_ablation"):
            t0 = time.perf_counter()
            try:
                recs = run_idea2_engine_cell(
                    seed=seed, cell=cell, generations=8, population=4
                )
            except Exception:  # noqa: BLE001
                out["errors"].append(
                    {"seed": seed, "cell": cell, "traceback": traceback.format_exc()}
                )
                continue
            wall = time.perf_counter() - t0
            for rec in recs:
                out["cells"].append(
                    {
                        "seed": seed,
                        "cell": cell,
                        "arm": rec.get("arm"),
                        "wall_s": round(wall / max(1, len(recs)), 6),
                        "parasite_is_genotype_population": rec.get(
                            "parasite_is_genotype_population"
                        ),
                        "parasite_is_independent_population": rec.get(
                            "parasite_is_independent_population"
                        ),
                        "births_open_new_lineage": rec.get("births_open_new_lineage"),
                        "births_copy_oldest_living_lineage": rec.get(
                            "births_copy_oldest_living_lineage"
                        ),
                        "parent_child_lineage_recorded": rec.get(
                            "parent_child_lineage_recorded"
                        ),
                        "parasite_end": rec.get("parasite_end"),
                        "parasite_series_tail": rec.get("parasite_series_tail"),
                        "hosts_founded": rec.get("hosts_founded"),
                        "host_lineages_alive": rec.get("host_lineages_alive"),
                        "hypothesis_test_eligible": rec.get("hypothesis_test_eligible"),
                        "score_role": rec.get("score_role"),
                        "estimand": rec.get("estimand"),
                        "engine_result_digest": rec.get("engine_result_digest"),
                    }
                )
    # What the engine itself exposes: no antagonist attribute is expected.
    out["engine_antagonist_attributes"] = None
    try:
        from codontrace.genesis.campaigns.discovery_q_20260928_idea4_engine import (
            build_idea4_engine_spec,
        )
        from codontrace.genesis.engine import GenesisEngine

        spec = build_idea4_engine_spec(seed=301, tick_count=2, population=4)
        engine = GenesisEngine.from_spec(spec)
        candidates = [
            name
            for name in dir(engine)
            if any(
                tok in name.lower()
                for tok in ("parasite", "antagonist", "host", "infect", "contact")
            )
        ]
        out["engine_antagonist_attributes"] = candidates
    except Exception:  # noqa: BLE001
        out["errors"].append({"phase": "engine_attribute_scan", "traceback": traceback.format_exc()})
    return out


def probe_live_generations() -> tuple[dict, list[dict], list[dict]]:
    """Per-generation raw events from the live engine (no antagonist exists)."""

    from codontrace.genesis.campaigns.discovery_q_20260928_idea4_engine import (
        build_idea4_engine_spec,
    )
    from codontrace.genesis.engine import GenesisEngine
    from codontrace.life_loop.engine_ledger_coupler import sample_ecology

    events: list[dict] = []
    population_rows: list[dict] = []
    summary: dict[str, object] = {"runs": [], "errors": []}

    for seed in (301, 302):
        run_id = f"rq1-probe-seed{seed}-livegen"
        t0 = time.perf_counter()
        logged: list[dict] = []

        def _observer(*, generation_index: int, _logged=logged) -> None:
            engine = holder["engine"]
            eco = sample_ecology(engine)
            organisms = tuple(engine.runner.population.organisms)
            digests = []
            for org in organisms:
                genome = getattr(org, "genome", None)
                digests.append(
                    genome.digest() if genome is not None and hasattr(genome, "digest") else None
                )
            digests = [d for d in digests if d]
            _logged.append(
                {
                    "generation": int(generation_index),
                    "n_alive": int(eco["n_alive"]),
                    "mean_atp": float(eco["mean_atp"]),
                    "resource_mass": float(eco["resource_mass"]),
                    "resource_loc_fp": float(eco["resource_loc_fp"]),
                    "distinct_host_genotypes": len(set(digests)),
                    "host_genome_digests": sorted(set(digests)),
                }
            )

        holder: dict[str, object] = {"engine": None}
        try:
            spec = build_idea4_engine_spec(seed=seed, tick_count=8, population=4)
            engine = GenesisEngine.from_spec(spec, generation_boundary_observers=(_observer,))
            holder["engine"] = engine
            result = engine.run_ticks()
            wall = time.perf_counter() - t0
            summary["runs"].append(
                {
                    "seed": seed,
                    "run_id": run_id,
                    "generations": len(logged),
                    "wall_s": round(wall, 6),
                    "engine_result_digest": result.snapshot.digest(),
                    "antagonist_population_present": False,
                    "antagonist_genotype_field_present": False,
                    "contact_opportunities_observed": 0,
                    "reason": (
                        "GenesisEngine has no antagonist population and no "
                        "graded-affinity contact route, so no contact opportunity, "
                        "no realised debit and no pi_realised can be logged."
                    ),
                }
            )
        except Exception:  # noqa: BLE001
            summary["errors"].append({"seed": seed, "traceback": traceback.format_exc()})
            continue

        for row in logged:
            events.append(
                {
                    "schema_version": SCHEMA_VERSION,
                    "record_role": "precondition_probe_no_contact",
                    "run_id": run_id,
                    "seed": seed,
                    "arm": "live_generation_probe",
                    "generation": row["generation"],
                    "event_id": f"{run_id}-g{row['generation']}",
                    "organism_id": None,
                    "organism_id_null_reason": "generation-level probe record",
                    "parent_id": None,
                    "parent_id_null_reason": "no parent-child ids recorded by the engine route",
                    "genotype_digest": None,
                    "genotype_digest_null_reason": (
                        "aggregate generation record; per-organism digests are on the run summary"
                    ),
                    "antagonist_digest": None,
                    "antagonist_digest_null_reason": (
                        "MISSING PRECONDITION: no antagonist genotype population exists"
                    ),
                    "contact_edge_id": None,
                    "contact_edge_id_null_reason": (
                        "MISSING PRECONDITION: no host-antagonist contact edge exists"
                    ),
                    "opportunity": None,
                    "opportunity_null_reason": "no contact opportunity can be offered",
                    "matched": None,
                    "matched_null_reason": "no contact rule is applied",
                    "intended_debit": None,
                    "intended_debit_null_reason": "no graded-affinity debit is computed",
                    "realised_debit": None,
                    "realised_debit_null_reason": "no realised debit is computed",
                    "atp_before": None,
                    "atp_before_null_reason": "per-organism contact round not observed",
                    "atp_after": None,
                    "atp_after_null_reason": "per-organism contact round not observed",
                    "birth": None,
                    "death": None,
                    "mutation": None,
                    "intervention_id": None,
                    "host_genotypes_distinct": row["distinct_host_genotypes"],
                    "host_lineages_note": "hosts only; antagonist absent",
                }
            )
            population_rows.append(
                {
                    "schema_version": SCHEMA_VERSION,
                    "record_role": "precondition_probe_no_contact",
                    "run_id": run_id,
                    "seed": seed,
                    "arm": "live_generation_probe",
                    "generation": row["generation"],
                    "class_counts": None,
                    "class_counts_null_reason": "no class/genotype census of an antagonist exists",
                    "genotype_counts": {"host": row["distinct_host_genotypes"]},
                    "host_genotype_frequencies": None,
                    "antagonist_frequency": None,
                    "antagonist_frequency_null_reason": (
                        "MISSING PRECONDITION: antagonist is not a genotype population"
                    ),
                    "fitness": None,
                    "fitness_null_reason": "no contact-linked fitness is defined on this route",
                    "atp_mean": row["mean_atp"],
                    "contact_opportunities": 0,
                    "pi_intended": None,
                    "pi_realised": None,
                    "pi_realised_null_reason": (
                        "MISSING PRECONDITION: no realised-pressure contact route"
                    ),
                    "resources": {
                        "resource_mass": row["resource_mass"],
                        "resource_loc_fp": row["resource_loc_fp"],
                    },
                    "genealogy": None,
                    "genealogy_null_reason": "no parent-child ids recorded",
                    "n_alive": row["n_alive"],
                }
            )
    return summary, events, population_rows


def probe_checkpoint_fork() -> dict:
    """Does a full-state checkpoint/fork exist for the arms?"""

    from codontrace.genesis.campaigns.discovery_q_20260928_idea4_engine import (
        run_idea4_engine_cell,
    )

    out: dict[str, object] = {"idea4_cells": [], "errors": []}
    for seed in (301, 302):
        try:
            rec = run_idea4_engine_cell(
                seed=seed, ops_cell="control", t_intervene=1, t_horizon=5, population=4
            )
        except Exception:  # noqa: BLE001
            out["errors"].append({"seed": seed, "traceback": traceback.format_exc()})
            continue
        out["idea4_cells"].append(
            {
                "seed": seed,
                "checkpoint_fork_complete": rec.get("checkpoint_fork_complete"),
                "parent_child_ids_recorded": rec.get("parent_child_ids_recorded"),
                "lineage_recovery_established": rec.get("lineage_recovery_established"),
                "recovery_window_built": rec.get("recovery_window_built"),
                "recovery_window_missing": rec.get("recovery_window_missing"),
                "lineage_branching_real": rec.get("lineage_branching_real"),
                "innovation_observable": rec.get("innovation_observable"),
                "checkpoint_organism_ids": rec.get("checkpoint_organism_ids"),
                "checkpoint_genome_digests": rec.get("checkpoint_genome_digests"),
                "endpoint_map_is_contact_physics": rec.get("endpoint_map_is_contact_physics"),
                "topology_effect_identified": rec.get("topology_effect_identified"),
                "engine_result_digest": rec.get("engine_result_digest"),
            }
        )

    # Structural scan of the checkpoint primitive.
    from codontrace.genesis.checkpointing import RunCheckpoint

    fields = list(getattr(RunCheckpoint, "__dataclass_fields__", {}).keys())
    out["run_checkpoint_fields"] = fields
    out["run_checkpoint_carries_restorable_state"] = any(
        "state" in f and "digest" not in f for f in fields
    )
    try:
        from codontrace.genesis.host_parasite_world import HostParasiteWorld

        out["host_parasite_world_methods"] = sorted(
            m
            for m in dir(HostParasiteWorld)
            if any(tok in m.lower() for tok in ("fork", "snapshot", "restore", "from_state", "resume"))
        )
    except Exception:  # noqa: BLE001
        out["errors"].append({"phase": "world_fork_scan", "traceback": traceback.format_exc()})
    return out


# --------------------------------------------------------------------------
# D: the 3x3 cross-time matrix a dated live history can actually produce
# --------------------------------------------------------------------------
def _profile(seed: int):
    from codontrace.genesis.host_parasite_world import HostParasiteProfile

    return HostParasiteProfile(
        profile_id=f"rq1_ts_{seed}",
        seed=int(seed),
        birth_probability_primary=0.25,
        birth_probability_secondary=0.25,
        death_probability_primary=0.08,
        death_probability_secondary=0.08,
        mutation_probability_primary=0.4,
        mutation_probability_secondary=0.4,
        inherit_mode="copy",
        inherit_probability=1.0,
        match_rule_id="feature_overlap",
        max_population_primary=24,
        max_population_secondary=24,
    )


def probe_cross_time_matrix() -> dict:
    """Build the best 3x3 cross-time matrices one dated live history can give."""

    from codontrace.genesis.host_parasite_world import HostParasiteWorld
    from codontrace.life_loop.time_shift_assay import (
        allele_exact_rate,
        features_from_genome_compact,
    )
    from codontrace.genesis.measurements.rq_frequency_clocks import (
        realised_conditional_host_pressure,
    )

    out: dict[str, object] = {"histories": [], "errors": []}

    for seed in (11, 22):
        profile = _profile(seed)
        world = HostParasiteWorld(profile)
        ticks = 30
        lag = 10
        host_frames: dict[int, dict[str, frozenset]] = {}
        ant_frames: dict[int, dict[str, frozenset]] = {}
        compact_frames: dict[int, dict[str, str]] = {}
        pop_a = profile.population_id("primary")
        pop_b = profile.population_id("secondary")
        try:
            for step in range(ticks + 1):
                t = int(world.tick_index)
                host_frames[t] = {
                    str(mid): features_from_genome_compact(world.genomes[mid].to_compact())
                    for mid in world.registry.get(pop_a).member_ids
                    if mid in world.genomes
                }
                ant_frames[t] = {
                    str(mid): features_from_genome_compact(world.genomes[mid].to_compact())
                    for mid in world.registry.get(pop_b).member_ids
                    if mid in world.genomes
                }
                compact_frames[t] = {
                    str(mid): str(world.genomes[mid].to_compact())
                    for mid in world.genomes
                }
                if step < ticks:
                    world.tick()
            summary = world.summary()
        except Exception:  # noqa: BLE001
            out["errors"].append({"seed": seed, "traceback": traceback.format_exc()})
            continue

        focus = ticks - lag
        slots = {name: focus + offset for name, offset in zip(TIMES, (-lag, 0, lag))}
        slots = {k: max(0, v) for k, v in slots.items()}

        # (a) what the live witness's own currency gives: allele-exact match rate
        allele_matrix: dict[str, dict[str, float]] = {}
        for h in TIMES:
            allele_matrix[h] = {}
            for a in TIMES:
                ht, at = slots[h], slots[a]
                if not host_frames.get(ht) or not ant_frames.get(at):
                    allele_matrix[h][a] = 0.0
                    continue
                total = 0.0
                n = 0
                for hf in host_frames[ht].values():
                    for af in ant_frames[at].values():
                        total += allele_exact_rate(hf, af)
                        n += 1
                allele_matrix[h][a] = round(total / n, 10) if n else 0.0

        # (b) affinity-derived pi_realised on invented 6-bit windows.
        def window_of(tick: int, member: str) -> str | None:
            compact = compact_frames.get(tick, {}).get(member)
            if not compact or len(compact) < 6:
                return None
            return compact[:6]

        affinity_matrix: dict[str, dict[str, float]] = {}
        window_notes: list[str] = []
        for h in TIMES:
            affinity_matrix[h] = {}
            for a in TIMES:
                ht, at = slots[h], slots[a]
                hw = {
                    mid: window_of(ht, mid)
                    for mid in host_frames.get(ht, {})
                    if window_of(ht, mid)
                }
                pw = {
                    mid: window_of(at, mid)
                    for mid in ant_frames.get(at, {})
                    if window_of(at, mid)
                }
                if not hw or not pw:
                    affinity_matrix[h][a] = 0.0
                    window_notes.append(f"empty windows at {h}x{a}")
                    continue
                # One representative class per time slot: the most common window.
                from collections import Counter

                rep_h = Counter(hw.values()).most_common(1)[0][0]
                rep_p = Counter(pw.values()).most_common(1)[0][0]
                res = realised_conditional_host_pressure(
                    {"H": rep_h}, {"P": rep_p}, virulence=8.0, steal_fraction=0.15
                )
                affinity_matrix[h][a] = float(res["pressure"]["H"])  # type: ignore[index]

        out["histories"].append(
            {
                "seed": seed,
                "ticks": ticks,
                "lag": lag,
                "slots": slots,
                "host_members_per_slot": {k: len(host_frames.get(v, {})) for k, v in slots.items()},
                "antagonist_members_per_slot": {k: len(ant_frames.get(v, {})) for k, v in slots.items()},
                "extinct_primary": summary.get("extinct_primary"),
                "extinct_secondary": summary.get("extinct_secondary"),
                "coexistence": summary.get("coexistence"),
                "birth_counts": summary.get("birth_counts"),
                "death_counts": summary.get("death_counts"),
                "mutation_counts": summary.get("mutation_counts"),
                "hook_counts": summary.get("hook_counts"),
                "world_digest": summary.get("world_digest"),
                "matrix_allele_exact": allele_matrix,
                "matrix_affinity_pi": affinity_matrix,
                "affinity_window_definition": (
                    "INVENTED BY THIS PROBE: compact[:6]. The live model has no "
                    "6-bit recognition window and no graded-affinity ATP debit, so "
                    "this matrix is the analysis kernel applied to an imposed "
                    "definition, not the model's pi_realised."
                ),
                "window_notes": window_notes,
                "contact_physics_of_the_world": (
                    "apply_contact(ContactTransferPolicy): payload/book transfer "
                    "gated by a MatchRule; no per-contact ATP debit, no "
                    "reservation, no survival link."
                ),
            }
        )
    return out


def probe_measurement_kernel() -> dict:
    """Hand-computed cases through the repository's real measurement kernel."""

    from codontrace.genesis.measurements.rq_frequency_clocks import (
        affinity_matrix,
        realised_conditional_host_pressure,
        reference_graded_affinity,
    )

    out: dict[str, object] = {}
    out["example_histogram_blind"] = {
        "affinity_b_against_000011": reference_graded_affinity("111100", "000011"),
        "affinity_a_000000_000001": reference_graded_affinity("000000", "000001"),
    }
    p = realised_conditional_host_pressure(
        {"A": "000000", "B": "111100"},
        {"P1": "000001", "P2": "000011"},
        contact_mode="full_matrix",
    )
    out["two_host_classes"] = {
        "pressure": p["pressure"],
        "equal_exposure": p["equal_exposure"]["full_matrix"],
        "histogram_used": p["histogram_used"],
        "class_frequency_used": p["class_frequency_used"],
    }
    flat = realised_conditional_host_pressure(
        {"A": "000000"}, {"P1": "111111"}, affinity={"A": {"P1": 0.5}}
    )
    out["flat_affinity"] = {"pressure": flat["pressure"], "kappa": flat["kappa"]}
    trunc = realised_conditional_host_pressure(
        {"A": "000000"},
        {"P1": "111111"},
        affinity={"A": {"P1": 0.5}},
        host_capacity_units={"A": 0.5},
    )
    out["truncation"] = {"pressure": trunc["pressure"], "kappa": trunc["kappa"]}
    out["affinity_grid_example"] = affinity_matrix(
        {"past": "000000", "now": "111111", "future": "010101"},
        {"past": "000000", "now": "111111", "future": "010101"},
    )
    return out


def probe_meter_reachability() -> dict:
    """Property test: which time-shift labels are reachable under the model's affinity law?"""

    from codontrace.genesis.measurements.rq_frequency_clocks import (
        reference_graded_affinity,
    )

    windows = [format(i, "06b") for i in range(64)]
    aff = {
        h: {p: reference_graded_affinity(h, p) for p in windows} for h in windows
    }

    def directional(rows) -> bool:
        return all(rows[h][0] < rows[h][1] < rows[h][2] for h in TIMES)

    def contemporary(rows) -> bool:
        return all(
            rows[a][TIMES.index(a)] > rows[h][TIMES.index(a)]
            for a in TIMES
            for h in TIMES
            if h != a
        )

    def lagged(rows) -> bool:
        return (
            rows["now"][0] > rows["past"][0]
            and rows["now"][0] > rows["future"][0]
            and rows["future"][1] > rows["past"][1]
            and rows["future"][1] > rows["now"][1]
            and rows["future"][2] > rows["past"][2]
            and rows["future"][2] > rows["now"][2]
        )

    def to_matrix(rows) -> dict[str, dict[str, float]]:
        return {h: dict(zip(TIMES, rows[h])) for h in TIMES}

    def classify(m) -> str:
        if max(m[h][a] for h in TIMES for a in TIMES) - min(
            m[h][a] for h in TIMES for a in TIMES
        ) <= 1e-9:
            return "flat"
        if all(m[h]["past"] < m[h]["now"] < m[h]["future"] for h in TIMES):
            return "directional_increase"
        if all(
            m[ant][ant] > m[host][ant]
            for ant in TIMES
            for host in TIMES
            if host != ant
        ):
            return "contemporary_match"
        if (
            m["now"]["past"] > m["past"]["past"]
            and m["now"]["past"] > m["future"]["past"]
            and m["future"]["now"] > m["past"]["now"]
            and m["future"]["now"] > m["now"]["now"]
            and m["future"]["future"] > m["past"]["future"]
            and m["future"]["future"] > m["now"]["future"]
        ):
            return "lagged_match"
        return "other"

    # A bounded search, reported as bounded. Phase 1 is exhaustive over a
    # structured 8-window subset; phase 2 is a fixed-seed randomised search
    # over the full 64-window grid until the deadline.
    import random as _random

    structured = [
        w
        for w in windows
        if all(w[i : i + 2] in {"00", "11"} for i in range(0, 6, 2))
    ]
    rng = _random.Random(20260929)
    found: dict[str, object | None] = {
        "directional_increase": None,
        "contemporary_match": None,
        "lagged_match": None,
    }
    checked = 0
    capped = False
    t0 = time.perf_counter()
    deadline = t0 + 60.0

    def try_triple(ps) -> None:
        nonlocal checked
        checked += 1
        rows = {
            h: tuple(aff[h][ps[i]] for i in range(3)) for h in windows
        }
        if found["directional_increase"] is None:
            asc = [h for h in windows if rows[h][0] < rows[h][1] < rows[h][2]]
            if len(asc) >= 3:
                pick = {"past": asc[0], "now": asc[1], "future": asc[2]}
                m = to_matrix({h: rows[pick[h]] for h in TIMES})
                if classify(m) == "directional_increase":
                    found["directional_increase"] = {
                        "parasites": dict(zip(TIMES, ps)),
                        "hosts": pick,
                        "matrix": m,
                    }
        if found["contemporary_match"] is None:
            # diagonal-dominance: u wins col 0, v col 1, w col 2
            budget = 20000
            for u in windows:
                u0, u1, u2 = rows[u]
                v_cands = [v for v in windows if rows[v][0] < u0 and rows[v][1] > u1]
                w_cands = [w for w in windows if rows[w][0] < u0 and rows[w][2] > u2]
                for v in v_cands:
                    v1, v2 = rows[v][1], rows[v][2]
                    for w in w_cands:
                        budget -= 1
                        if budget < 0:
                            break
                        if rows[w][1] < v1 and rows[w][2] > v2:
                            pick = {"past": u, "now": v, "future": w}
                            m = to_matrix({h: rows[pick[h]] for h in TIMES})
                            if classify(m) == "contemporary_match":
                                found["contemporary_match"] = {
                                    "parasites": dict(zip(TIMES, ps)),
                                    "hosts": pick,
                                    "matrix": m,
                                }
                                break
                    if found["contemporary_match"] is not None or budget < 0:
                        break
                if found["contemporary_match"] is not None or budget < 0:
                    break
        if found["lagged_match"] is None:
            budget = 20000
            for u in windows:  # host past
                for v in windows:  # host now
                    if rows[v][0] <= rows[u][0]:
                        continue
                    for w in windows:  # host future
                        budget -= 1
                        if budget < 0:
                            break
                        if (
                            rows[w][0] < rows[v][0]
                            and rows[w][1] > rows[u][1]
                            and rows[w][1] > rows[v][1]
                            and rows[w][2] > rows[u][2]
                            and rows[w][2] > rows[v][2]
                        ):
                            pick = {"past": u, "now": v, "future": w}
                            m = to_matrix({h: rows[pick[h]] for h in TIMES})
                            if classify(m) == "lagged_match":
                                found["lagged_match"] = {
                                    "parasites": dict(zip(TIMES, ps)),
                                    "hosts": pick,
                                    "matrix": m,
                                }
                                break
                    if found["lagged_match"] is not None or budget < 0:
                        break
                if found["lagged_match"] is not None or budget < 0:
                    break

    for p1 in structured:
        for p2 in structured:
            for p3 in structured:
                try_triple((p1, p2, p3))
                if all(found.values()):
                    break
            if all(found.values()):
                break
        if all(found.values()):
            break

    random_triples = 0
    while not all(found.values()) and time.perf_counter() < deadline:
        ps = (rng.choice(windows), rng.choice(windows), rng.choice(windows))
        try_triple(ps)
        random_triples += 1
    if not all(found.values()):
        capped = True

    return {
        "grid": "64 windows of 6 bits, reference_graded_affinity",
        "structured_subset_size": len(structured),
        "structured_triples": len(structured) ** 3,
        "random_triples": random_triples,
        "triples_checked": checked,
        "bounded_search": True,
        "deadline_reached": capped,
        "wall_s": round(time.perf_counter() - t0, 3),
        "reachable": {
            k: {"reachable": v is not None, "witness": v} for k, v in found.items()
        },
    }


def probe_determinism() -> dict:
    from codontrace.genesis.campaigns.discovery_q_20260928_idea4_engine import (
        build_idea4_engine_spec,
    )
    from codontrace.genesis.engine import GenesisEngine
    from codontrace.genesis.host_parasite_world import HostParasiteWorld
    from codontrace.genesis.canonical import canonical_digest
    from codontrace.genesis.measurements.rq_frequency_clocks import (
        realised_conditional_host_pressure,
    )

    out: dict[str, object] = {}
    digests = []
    for _ in range(2):
        spec = build_idea4_engine_spec(seed=301, tick_count=6, population=4)
        engine = GenesisEngine.from_spec(spec)
        digests.append(engine.run_ticks().snapshot.digest())
    out["engine_replay_identical"] = digests[0] == digests[1]
    out["engine_digests"] = digests

    world_digests = []
    for _ in range(2):
        world = HostParasiteWorld(_profile(11))
        world.run(12)
        world_digests.append(world.summary().get("world_digest"))
    out["world_replay_identical"] = world_digests[0] == world_digests[1]
    out["world_digests"] = world_digests

    kernel = []
    for _ in range(2):
        res = realised_conditional_host_pressure(
            {"A": "000000", "B": "111100"}, {"P1": "000001", "P2": "000011"}
        )
        kernel.append(canonical_digest({k: v for k, v in res.items() if k != "red_queen_proved"}))
    out["kernel_replay_identical"] = kernel[0] == kernel[1]
    out["kernel_digests"] = kernel
    return out


# --------------------------------------------------------------------------
def main() -> int:
    started = time.perf_counter()
    cpu_started = time.process_time()
    run_report: dict[str, object] = {
        "schema_version": SCHEMA_VERSION,
        "python": sys.version,
        "platform": platform.platform(),
        "cwd": str(Path.cwd()),
        "repo": str(REPO),
        "repo_head": repo_head(),
        "steps": {},
        "errors": [],
    }

    def _step(name, fn):
        t0 = time.perf_counter()
        try:
            payload = fn()
            run_report["steps"][name] = {
                "ok": True,
                "wall_s": round(time.perf_counter() - t0, 3),
            }
            return payload
        except Exception:  # noqa: BLE001
            run_report["steps"][name] = {
                "ok": False,
                "wall_s": round(time.perf_counter() - t0, 3),
                "traceback": traceback.format_exc(),
            }
            run_report["errors"].append({"step": name, "traceback": traceback.format_exc()})
            return None

    scan = _step("source_scan", source_scan)
    if scan:
        dump("probe_source_scan.json", scan)

    antagonist = _step("engine_antagonist", probe_engine_antagonist)
    if antagonist:
        dump("probe_engine_antagonist.json", antagonist)

    gen_summary, events, population_rows = probe_live_generations()
    dump("probe_live_generations.json", gen_summary)
    events_path = RAW / "events.jsonl"
    population_path = RAW / "population.jsonl"
    events_path.unlink(missing_ok=True)
    population_path.unlink(missing_ok=True)
    append_jsonl(events_path, events)
    append_jsonl(population_path, population_rows)
    run_report["events_emitted"] = len(events)
    run_report["population_rows_emitted"] = len(population_rows)

    fork = _step("checkpoint_fork", probe_checkpoint_fork)
    if fork:
        dump("probe_checkpoint_fork.json", fork)

    world = _step("cross_time_matrix", probe_cross_time_matrix)
    if world:
        dump("probe_cross_time_matrix.json", world)

    kernel = _step("measurement_kernel", probe_measurement_kernel)
    if kernel:
        dump("probe_measurement_kernel.json", kernel)

    meter = _step("meter_reachability", probe_meter_reachability)
    if meter:
        dump("probe_meter_reachability.json", meter)

    det = _step("determinism", probe_determinism)
    if det:
        dump("probe_determinism.json", det)

    run_report["wall_s"] = round(time.perf_counter() - started, 3)
    run_report["cpu_s"] = round(time.process_time() - cpu_started, 3)
    run_report["peak_rss_bytes"] = peak_rss_bytes()
    dump("probe_run.json", run_report)
    print(json.dumps({k: v for k, v in run_report.items() if k != "steps"}, indent=2))
    print("steps:", json.dumps(run_report["steps"], indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
