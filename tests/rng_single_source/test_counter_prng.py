"""The experiment PRNG is RNGManager's counter stream, bit-identical to before.

golden_counter_prng.json was written by the old math_utils implementation
(commit 7f72ff6) before the move.
"""

from __future__ import annotations

import ast
import json
from pathlib import Path

from codontrace.experiments import math_utils as m
from codontrace.rng import RNGManager

GOLD = json.loads((Path(__file__).parent / "golden_counter_prng.json").read_text(encoding="utf-8"))
SRC = Path(__file__).resolve().parents[2] / "src" / "codontrace"


def test_math_utils_names_are_rngmanager_streams() -> None:
    assert m.sha_prng_float is RNGManager.counter_float
    assert m.sha_prng_int is RNGManager.counter_int
    assert m.sha_prng_int_unbiased is RNGManager.counter_int_unbiased


def test_outputs_match_the_pre_move_golden() -> None:
    f = [m.sha_prng_float(s, t, x) for s in (0, 7, -3, 2**40) for t in (0, 1, 99) for x in ("a", "mut", "")]
    i = [m.sha_prng_int(s, t, "x", -5, 17) for s in range(5) for t in range(4)]
    u = [m.sha_prng_int_unbiased(s, t, "y", 0, 2**70) for s in range(4) for t in range(3)]
    u.append(m.sha_prng_int_unbiased(1, 2, "z", 3, 3))
    assert f == GOLD["float"] and i == GOLD["int"] and u == GOLD["intu"]


def test_no_module_outside_rng_hashes_its_own_random_stream() -> None:
    tree = ast.parse((SRC / "experiments" / "math_utils.py").read_text(encoding="utf-8"))
    imported = {a.name for n in ast.walk(tree) if isinstance(n, ast.Import) for a in n.names}
    assert "hashlib" not in imported and "random" not in imported
