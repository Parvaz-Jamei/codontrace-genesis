"""Run one RQ-1 confirmatory seed with the archived runner, unchanged, at 6187ff4.

usage: python run_one_seed.py <runner_dir> <reference_checkout> <output_dir> <seed>
"""
import sys
from pathlib import Path

runner_dir, checkout, out, seed = sys.argv[1], sys.argv[2], sys.argv[3], int(sys.argv[4])
sys.path.insert(0, runner_dir)
import confirmatory_rq1 as cr  # noqa: E402

sys.argv = ["confirmatory_rq1.py", "--reference-checkout", checkout, "--output", out]
cr._install()
import codontrace  # noqa: E402

assert Path(codontrace.__file__).resolve().is_relative_to(Path(checkout).resolve()), codontrace.__file__
rec = cr.run_seed(seed)
print({"seed": seed, "wall_s": rec["wall_s"], "gates_ok": rec["seed_gates_ok"]}, flush=True)
