"""RQ-3 stage-0 reconnaissance probe (read-only; no repo writes).

Purpose: establish, with raw live evidence, whether the current model can host the
RQ-3 arms and the RQ-3 meter. It builds arms from the existing public API only.

Outputs one JSON object to stdout. Nothing is written outside test-runs/rq3/.
"""

from __future__ import annotations

import hashlib
import json
import sys
import time
from collections import Counter

REPO = r"E:\مقاله پزشکی شبیه سازی ویروس\codontrace-genesis"
sys.path.insert(0, REPO + r"\src")

from codontrace.genesis.closed_loop_hp_arm01 import (  # noqa: E402
    ARM_AVIRULENT,
    ARM_COPASSAGED,
    ARM_FIXED,
)
from codontrace.genesis.closed_loop_hp_arm01_structural_rq import (  # noqa: E402
    StructuralRQArm,
    graded_affinity,
    host_realised_pressure_from_contacts,
)


def digest(obj: object) -> str:
    return hashlib.sha256(
        json.dumps(obj, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def class_freq(counts: tuple[tuple[str, int], ...]) -> dict[str, float]:
    total = sum(c for _, c in counts) or 1
    return {k: c / total for k, c in counts}


def probe(arm: str, seed: int, generations: int) -> dict[str, object]:
    t0 = time.perf_counter()
    a = StructuralRQArm.boot_structural(arm=arm, seed=seed)
    a.collect_realised_host_pressure = True
    a.run_generations(generations)
    wall = time.perf_counter() - t0

    host_hist = [class_freq(counts) for counts in a.host_joint_class_series]
    para_hist = [class_freq(counts) for counts in a.parasite_class_hist_series]

    host_dom = []
    for h in host_hist:
        host_dom.append(max(h.items(), key=lambda kv: (kv[1], kv[0]))[0] if h else None)
    dom_changes = sum(
        1 for i in range(1, len(host_dom)) if host_dom[i] != host_dom[i - 1]
    )

    # Distinct parasite classes over time (does the antagonist composition move?)
    distinct_para = [len(h) for h in para_hist]
    para_moves = sum(
        1
        for i in range(1, len(para_hist))
        if digest(para_hist[i]) != digest(para_hist[i - 1])
    )

    # Realised pressure per host class, as recorded by the existing collector.
    pressure_rounds = len(a.host_realised_pressure_series)
    classes_seen: set[str] = set()
    pressure_by_class: dict[str, list[tuple[float, int]]] = {}
    for round_ in a.host_realised_pressure_series:
        for cls, value, contacts in round_:
            classes_seen.add(cls)
            pressure_by_class.setdefault(cls, []).append((float(value), int(contacts)))
    sorted_classes = sorted(classes_seen, key=lambda c: -len(pressure_by_class[c]))

    turning = []
    for cls in sorted_classes[:3]:
        series = pressure_by_class[cls]
        turning.append(
            {
                "class": cls,
                "rounds": len(series),
                "first_value": series[0][0] if series else None,
                "last_value": series[-1][0] if series else None,
                "max_value": max((v for v, _ in series), default=None),
                "sum_contacts": sum(c for _, c in series),
            }
        )

    # Antagonist bookkeeping: is there per-unit identity or ancestry anywhere?
    sample_window = a.parasite_windows[0] if a.parasite_windows else None
    antagonist_state_fields = {
        "parasite_windows_is_list_of_str": isinstance(a.parasite_windows, list),
        "parasite_windows_len": len(a.parasite_windows),
        "sample_window_type": type(sample_window).__name__,
        "turnover_kept_sum": sum(a.turnover_kept),
        "turnover_replaced_sum": sum(a.turnover_replaced),
        "turnover_mut_events_sum": sum(a.turnover_mut_events),
        "has_ancestor_id_attribute": hasattr(a, "ancestor_id"),
        "has_parent_id_attribute": hasattr(a, "parent_id"),
    }

    # Contact accounting.
    contacts_per_gen = [int(n) for n in a.graded_contact_count]
    affinity_per_gen = [float(v) for v in a.graded_affinity_sum]

    host_windows_now = [w for w in getattr(a, "_window", lambda *_: "")()] if False else None

    return {
        "arm": arm,
        "seed": seed,
        "generations": generations,
        "wall_s": round(wall, 3),
        "census_series_first": None,
        "distinct_host_classes_first": len(host_hist[0]) if host_hist else 0,
        "distinct_host_classes_last": len(host_hist[-1]) if host_hist else 0,
        "host_dominant_first": host_dom[0],
        "host_dominant_last": host_dom[-1],
        "host_dominant_changes": dom_changes,
        "distinct_para_classes_last": distinct_para[-1] if distinct_para else 0,
        "para_composition_moves": para_moves,
        "host_pressure_rounds_recorded": pressure_rounds,
        "host_pressure_classes": len(classes_seen),
        "pressure_turning": turning,
        "contacts_total": sum(contacts_per_gen),
        "contacts_per_gen_first": contacts_per_gen[:3],
        "contacts_per_gen_last": contacts_per_gen[-3:],
        "affinity_total": round(sum(affinity_per_gen), 6),
        "antagonist_state": antagonist_state_fields,
        "host_windows_probe": host_windows_now,
    }


def main() -> int:
    out = {}
    configs = [
        ("coevolve", ARM_COPASSAGED, 10, 40),
        ("fixed", ARM_FIXED, 10, 40),
        ("absent", ARM_AVIRULENT, 10, 40),
        ("coevolve-long", ARM_COPASSAGED, 11, 80),
    ]
    for label, arm, seed, gens in configs:
        out[label] = probe(arm, seed, gens)

    # Hand-computed contact rule reference (P0 of the program): keep the meter honest.
    out["hand_reference"] = {
        "affinity_000000_000001": graded_affinity("000000", "000001"),
        "affinity_000000_000011": graded_affinity("000000", "000011"),
        "affinity_111100_000001": graded_affinity("111100", "000001"),
        "affinity_111100_000011": graded_affinity("111100", "000011"),
        "pressure_a": host_realised_pressure_from_contacts(
            host_affinity_sums={"A": 5 / 6 + 4 / 6},
            host_contact_counts={"A": 2},
            host_min_available={"A": 1000.0},
        ),
        "pressure_b": host_realised_pressure_from_contacts(
            host_affinity_sums={"B": 1 / 6 + 1 / 6},
            host_contact_counts={"B": 2},
            host_min_available={"B": 1000.0},
        ),
    }
    print(json.dumps(out, indent=2, sort_keys=True, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
