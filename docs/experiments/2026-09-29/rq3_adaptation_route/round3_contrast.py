"""RQ-3 round-3 acceptance probe: the same contrast through the landed arm API.

Runs the arm-level opt-in (`antagonist_ecology="population"`) with the SAME maintenance
value in every arm on the landed commit, and reports the common-window share of the
antagonist roster plus the per-arm ledger. Read-only; writes only under test-runs/rq3/.
"""

from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
# Provenance: run against a frozen extraction of the reviewed tip, never a dirty live tree.
# RQ3_REPO points at the extraction root whose "src" holds the codontrace package.
REPO = Path(
    __import__("os").environ.get(
        "RQ3_REPO", r"E:\مقاله پزشکی شبیه سازی ویروس\codontrace-genesis"
    )
)
sys.path.insert(0, str(REPO / "src"))

from codontrace.genesis.closed_loop_hp_arm01 import ARM_COPASSAGED  # noqa: E402
from codontrace.genesis.closed_loop_hp_arm01_structural_rq import (  # noqa: E402
    StructuralRQArm,
)
from codontrace.genesis.measurements.antagonist_population import (  # noqa: E402
    ANTAGONIST_ECOLOGY_POPULATION,
)
from codontrace.rng import RNGManager  # noqa: E402

MAINTENANCE = 0.15  # pre-declared value, identical in every arm
GENERATIONS = 60
SEED = 21051
COMMON_WINDOW = "000000"


def run_arm(label: str, *, mode: str) -> dict:
    """Boot with the opt-in, then drive the roster in one of the three modes."""

    arm = StructuralRQArm.boot_structural(
        arm=ARM_COPASSAGED,
        seed=SEED,
        antagonist_ecology=ANTAGONIST_ECOLOGY_POPULATION,
        antagonist_maintenance_cost=MAINTENANCE,
    )
    pop = arm.antagonist_pop
    rng = RNGManager(seed=arm.seed, namespace=f"rq3-{label}")
    shares: list[float] = []
    alive: list[int] = []
    with arm.__class__.__mro__[0].__dict__.get("_unused", None) or _nullcontext():
        from codontrace.genesis.closed_loop_hp_arm01_structural_rq import (
            _population_unique_id_guard,
        )

        with _population_unique_id_guard():
            for generation in range(1, GENERATIONS + 1):
                arm._apply_passage_refill()
                result = arm.runner.step_generation(
                    seed=arm.seed + arm.tick_index + 1
                )
                arm._record_births(result)
                arm._apply_hp_env_contact()
                records = (
                    tuple(
                        (record[1], record[4])
                        for record in arm.contact_pair_records[-1]
                    )
                    if arm.contact_pair_records
                    else ()
                )
                ledger = pop.advance(
                    matched_windows=records and [w for w, _ in records] or [],
                    served_contacts=records,
                    mode=mode,
                    generation=generation,
                    rng=rng.fork(f"passage/{generation}"),
                    mutate_window=__import__(
                        "codontrace.genesis.closed_loop_hp_arm01",
                        fromlist=["_mutate_window"],
                    )._mutate_window,
                )
                arm.parasite_windows = pop.windows()
                arm._census()
                arm.tick_index += 1
                windows = pop.windows()
                shares.append(
                    windows.count(COMMON_WINDOW) / max(1, len(windows))
                )
                alive.append(int(ledger.alive))
    counts = Counter(pop.windows())
    return {
        "arm": label,
        "mode": mode,
        "maintenance": MAINTENANCE,
        "generations": GENERATIONS,
        "common_share_first": shares[0],
        "common_share_g10": shares[9],
        "common_share_last": shares[-1],
        "alive_last": alive[-1],
        "extinct": alive[-1] == 0,
        "final_classes": len(counts),
        "final_common_count": counts.get(COMMON_WINDOW, 0),
        "final_roster": sum(counts.values()),
    }


class _nullcontext:
    def __enter__(self):
        return None

    def __exit__(self, *exc):
        return False


def main() -> int:
    from codontrace.genesis.measurements.antagonist_population import (
        ANTAGONIST_PASSAGE_SHUFFLED_LABELS as SHUFFLED,
    )

    out = {
        "coevolve": run_arm("coevolve", mode="coevolve"),
        "frozen": run_arm("frozen", mode="frozen"),
        "shuffled_labels": run_arm("shuffled_labels", mode=SHUFFLED),
    }
    coevo = out["coevolve"]["common_share_last"]
    out["verdict"] = {
        "maintenance_same_in_every_arm": MAINTENANCE,
        "coevolve_above_frozen": coevo > out["frozen"]["common_share_last"] + 0.1,
        "coevolve_above_shuffled": coevo
        > out["shuffled_labels"]["common_share_last"] + 0.1,
        "coevolve_share_last": coevo,
    }
    print(json.dumps(out, indent=1, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
