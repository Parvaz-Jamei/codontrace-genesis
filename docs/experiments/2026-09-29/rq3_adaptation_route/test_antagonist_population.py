"""Functional test of the PROPOSED_CHANGE antagonist population (module extracted from
the patch, not applied to the repository).

Three checks:
  1. coevolve: a window that matches the common host class earns more energy and
     reproduces more than one that does not (heritable adaptation exists);
  2. shuffled-labels: the same contact and cost records leave the next generation's
     composition independent of the common host class (the delayed route is cut);
  3. frozen: composition does not move at all.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
REPO = Path(r"E:\مقاله پزشکی شبیه سازی ویروس\codontrace-genesis")
sys.path.insert(0, str(REPO / "src"))

module = ROOT / "_patch_module.py"
if not module.is_file():
    raise SystemExit("run the patch-extract step first (see out_patchsyntax2.txt)")

namespace: dict = {"__name__": "antagonist_population_extracted"}
sys.modules["antagonist_population_extracted"] = type(sys)("antagonist_population_extracted")
exec(compile(module.read_text(encoding="utf-8"), str(module), "exec"), namespace)
AntagonistPopulation = namespace["AntagonistPopulation"]
SHUFFLED = namespace["ANTAGONIST_PASSAGE_SHUFFLED_LABELS"]

from codontrace.genesis.closed_loop_hp_arm01 import _mutate_window  # noqa: E402
from codontrace.rng import RNGManager  # noqa: E402

ANCESTRAL = ["000000", "000001", "111100", "111111"]
COMMON_HOST = "000000"
RARE_HOST = "111100"
# Contact seats: the common host class meets two windows, the rare host class one.
CONTACT_WINDOWS = [COMMON_HOST, COMMON_HOST, RARE_HOST]
PAID = [0.6, 0.6, 0.6]


def run_arm(mode: str, generations: int = 6, seed: int = 7) -> dict:
    pop = AntagonistPopulation.founders(ANCESTRAL, keep_fraction=0.5, mutation_rate=0.25)
    rng = RNGManager(seed=seed, namespace=f"rq3-{mode}")
    history = []
    for generation in range(1, generations + 1):
        pop.begin_round()
        ledger = pop.advance(
            matched_windows=CONTACT_WINDOWS,
            served_contacts=list(zip(CONTACT_WINDOWS, PAID, strict=True)),
            mode=mode,
            generation=generation,
            rng=rng.fork(f"passage/{generation}"),
            mutate_window=_mutate_window,
        )
        history.append(
            {
                "generation": generation,
                "windows": pop.windows(),
                "class_counts": {w: pop.windows().count(w) for w in sorted(set(pop.windows()))},
                "newborns": len(ledger.newborns),
                "deaths": len(ledger.deaths),
                "mutations": ledger.mutation_events,
                "alive": ledger.alive,
                "mean_energy": round(ledger.mean_energy, 6),
            }
        )
    return {"mode": mode, "history": history}


def composition_tracks_common(run: dict) -> float:
    """Share of units whose window equals the common host window, last generation."""

    last = run["history"][-1]
    total = sum(last["class_counts"].values()) or 1
    return last["class_counts"].get(COMMON_HOST, 0) / total


def main() -> int:
    coevolve = run_arm("coevolve")
    shuffled = run_arm(SHUFFLED)
    frozen = run_arm("frozen")
    out = {
        "antagonist_population_functional_test": {
            "coevolve": coevolve,
            "shuffled_labels": shuffled,
            "frozen": frozen,
        },
        "summary": {
            "coevolve_common_share_last": composition_tracks_common(coevolve),
            "shuffled_common_share_last": composition_tracks_common(shuffled),
            "frozen_common_share_last": composition_tracks_common(frozen),
            "coevolve_mutations_total": sum(
                h["mutations"] for h in coevolve["history"]
            ),
            "shuffled_mutations_total": sum(
                h["mutations"] for h in shuffled["history"]
            ),
            "coevolve_ancestry_available": True,
        },
    }
    print(json.dumps(out, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
