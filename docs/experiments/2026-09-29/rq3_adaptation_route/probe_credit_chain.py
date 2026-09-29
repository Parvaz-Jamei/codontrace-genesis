"""Instrumented one-generation credit probe on the patched mirror (test-runs/rq3 only).

Loads the patched arm + module from test-runs/rq3/applycheck (refreshed by verify_patch),
runs exactly one copassaged generation with antagonist_ecology="population", and prints
every link in the credit chain: records appended, served tuple handed to the passage
update, roster size, queue keys, and how many units matched a seat.
"""

from __future__ import annotations

import json
import sys
from importlib.machinery import SourceFileLoader
from importlib.util import module_from_spec, spec_from_loader
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = Path(r"E:\مقاله پزشکی شبیه سازی ویروس\codontrace-genesis")
MIRROR = HERE / "applycheck"
PATCHED = MIRROR / "patched"
TARGET_REL = "src/codontrace/genesis/closed_loop_hp_arm01_structural_rq.py"
NEW_REL = "src/codontrace/genesis/measurements/antagonist_population.py"

sys.path.insert(0, str(REPO / "src"))


def load(name: str, path: Path):
    loader = SourceFileLoader(name, str(path))
    spec = spec_from_loader(name, loader)
    module = module_from_spec(spec)
    sys.modules[name] = module
    loader.exec_module(module)
    return module


module_name = "codontrace.genesis.measurements.antagonist_population"
pop_module = load(module_name, PATCHED / NEW_REL)
arm_name = "codontrace.genesis.closed_loop_hp_arm01_structural_rq"
arm_module = load(arm_name, PATCHED / TARGET_REL)

from codontrace.genesis.closed_loop_hp_arm01 import ARM_COPASSAGED  # noqa: E402

arm = arm_module.StructuralRQArm.boot_structural(
    arm=ARM_COPASSAGED, seed=43, antagonist_ecology="population"
)
pop = arm.antagonist_pop

report: dict[str, object] = {
    "roster_at_boot": len(pop.units) if pop else 0,
    "maintenance_cost": getattr(pop, "maintenance_cost", None),
    "records_before": len(arm.contact_pair_records),
    "unit_windows_sample": [u.window for u in pop.units[:8]] if pop else [],
}

arm.run_generations(1)

report["records_after_one_generation"] = len(arm.contact_pair_records)
if arm.contact_pair_records:
    first = arm.contact_pair_records[-1]
    report["first_record_len"] = len(first)
    report["first_record_first_tuple"] = list(first[0]) if first else None
    windows = [record[1] for record in first]
    report["seat_window_distinct"] = len(set(windows))
    report["seat_window_sample"] = windows[:8]
pop = arm.antagonist_pop
report["roster_after"] = len(pop.units) if pop else 0
report["ledgers"] = len(pop.ledgers) if pop else 0
if pop and pop.ledgers:
    led = pop.ledgers[0]
    report["ledger_alive"] = int(led.alive)
    report["ledger_contacts"] = int(led.contacts)
    report["ledger_newborns"] = len(led.newborns)
    report["ledger_deaths"] = len(led.deaths)
    report["ledger_mean_energy"] = float(led.mean_energy)
report["unit_energies_after"] = [round(float(u.energy), 6) for u in pop.units[:8]] if pop else []
report["units_served_gt_zero"] = (
    sum(1 for u in pop.units if int(u.contacts_served) > 0) if pop else 0
)
report["parasite_windows_after"] = len(arm.parasite_windows)

print(json.dumps(report, indent=1, sort_keys=True))
