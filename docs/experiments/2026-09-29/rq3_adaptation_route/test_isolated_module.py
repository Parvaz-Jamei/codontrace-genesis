"""Isolated functional test of the patched antagonist population (test-runs/rq3)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = Path(r"E:\مقاله پزشکی شبیه سازی ویروس\codontrace-genesis")
sys.path.insert(0, str(REPO / "src"))

from importlib.machinery import SourceFileLoader  # noqa: E402
from importlib.util import module_from_spec, spec_from_loader  # noqa: E402

module_path = HERE / "antagonist_population.py"
name = "codontrace.genesis.measurements.antagonist_population"
loader = SourceFileLoader(name, str(module_path))
module = module_from_spec(spec_from_loader(name, loader))
sys.modules[name] = module
loader.exec_module(module)

from codontrace.genesis.closed_loop_hp_arm01 import _mutate_window  # noqa: E402
from codontrace.rng import RNGManager  # noqa: E402

P = module.AntagonistPopulation
SHUFFLED = module.ANTAGONIST_PASSAGE_SHUFFLED_LABELS
WINDOWS = ["000000", "000001", "111100", "111111"]
CONTACTS = ["000000", "000000", "111100"]
PAID = [0.6, 0.6, 0.6]


def run(mode: str, generations: int = 40, seed: int = 7) -> dict:
    pop = P.founders(WINDOWS, keep_fraction=0.5, mutation_rate=0.25)
    rng = RNGManager(seed=seed, namespace=f"rq3-{mode}")
    shares = []
    alive = []
    for gen in range(1, generations + 1):
        pop.begin_round()
        ledger = pop.advance(
            matched_windows=CONTACTS,
            served_contacts=list(zip(CONTACTS, PAID, strict=True)),
            mode=mode,
            generation=gen,
            rng=rng.fork(f"passage/{gen}"),
            mutate_window=_mutate_window,
        )
        windows = pop.windows()
        shares.append(windows.count("000000") / max(1, len(windows)))
        alive.append(ledger.alive)
    return {"shares": shares, "alive": alive}


def run_arm_via_arm_api(arm_mode: str, generations: int = 40, seed: int = 7) -> dict:
    """The same contrast on the landed arm, with the SAME maintenance in every arm.

    This is the acceptance path the manager gates on: the arm-level opt-in builds the
    population, contact is real, and only the update route differs between arms.
    """

    SHUFFLED_MODE = module.ANTAGONIST_PASSAGE_SHUFFLED_LABELS
    del SHUFFLED_MODE
    sys.path.insert(0, str(REPO / "src"))
    import codontrace.genesis.closed_loop_hp_arm01_structural_rq as live

    arm_labels = {"coevolve": "copassaged", "frozen": "fixed"}
    test_module.ARM_LABELS = {"coevolve": "copassaged", "frozen": "fixed"}
    del arm_labels
    from codontrace.genesis.measurements.antagonist_population import (
        ANTAGONIST_PASSAGE_SHUFFLED_LABELS as SHUFFLED_LABEL,
    )

    del SHUFFLED_LABEL
    del live
    raise NotImplementedError


def main() -> int:
    out = {}
    for mode in ("coevolve", SHUFFLED, "frozen"):
        result = run(mode)
        out[mode] = {
            "common_share_first": result["shares"][0],
            "common_share_g10": result["shares"][9],
            "common_share_last": result["shares"][-1],
            "alive_last": result["alive"][-1],
            "extinct": result["alive"][-1] == 0,
        }
    coevo = out["coevolve"]["common_share_last"]
    out["verdict"] = {
        "heritable_adaptation_exists": coevo > out[SHUFFLED]["common_share_last"] + 0.1,
        "cut_removes_it": abs(
            out[SHUFFLED]["common_share_last"] - out["frozen"]["common_share_last"]
        )
        < 0.15,
        "no_extinction": not any(v["extinct"] for v in out.values() if isinstance(v, dict)),
    }
    print(json.dumps(out, indent=1, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
