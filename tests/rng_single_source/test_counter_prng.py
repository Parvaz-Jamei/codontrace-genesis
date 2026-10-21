"""The experiment PRNG is RNGManager's counter stream, bit-identical to before.

golden_counter_prng.json was written by the old math_utils implementation
(commit 7f72ff6) before the move.
"""

from __future__ import annotations

import ast
import json
from pathlib import Path

import pytest

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


HASH_FUNCS = {"sha256", "sha1", "sha512", "md5", "blake2b", "blake2s", "sha3_256", "new"}
# Seed-derived hashes that are identifiers, not random draws.
ALLOWED = {
    # A short run-id slug for very long seeds; never used as a random value.
    ("experiments/orchestrator.py", "seed"),
    # File-integrity hashes of a snapshot file whose name contains a seed.
    ("genesis/rq_bidirectional_timeshift.py", "sample_path"),
}


def _seed_names(node: ast.AST) -> set[str]:
    found: set[str] = set()
    for sub in ast.walk(node):
        name = sub.id if isinstance(sub, ast.Name) else sub.attr if isinstance(sub, ast.Attribute) else None
        if name and "seed" in name.lower():
            found.add(name)
    return found


def seeded_hash_calls(tree: ast.AST) -> list[tuple[int, str]]:
    """Calls of a hashlib function on data that mentions a seed.

    Covers ``import hashlib``/``import hashlib as h`` (attribute calls) and
    ``from hashlib import sha256 [as x]`` (bare-name calls).
    """
    modules = {"hashlib"}
    direct: dict[str, str] = {}
    for n in ast.walk(tree):
        if isinstance(n, ast.Import):
            modules |= {a.asname or a.name for a in n.names if a.name == "hashlib"}
        elif isinstance(n, ast.ImportFrom) and n.module == "hashlib":
            direct |= {(a.asname or a.name): a.name for a in n.names}
    # One step of local data flow: a name assigned from a seed-bearing string
    # key is tainted (``raw = f"{seed}|x".encode(); sha256(raw)``). Records and
    # payload dicts that merely contain a seed field are digests, not streams.
    tainted: set[str] = set()
    for n in ast.walk(tree):
        if isinstance(n, ast.Assign) and any(
            isinstance(j, ast.JoinedStr) and _seed_names(j) for j in ast.walk(n.value)
        ):
            tainted |= {t.id for t in n.targets if isinstance(t, ast.Name)}
    hits: list[tuple[int, str]] = []
    for n in ast.walk(tree):
        if not isinstance(n, ast.Call):
            continue
        f = n.func
        is_hash = (
            isinstance(f, ast.Attribute) and isinstance(f.value, ast.Name)
            and f.value.id in modules and f.attr in HASH_FUNCS
        ) or (isinstance(f, ast.Name) and f.id in direct)
        if is_hash:
            names: set[str] = set()
            for a in n.args:
                names |= _seed_names(a)
                names |= {x.id for x in ast.walk(a) if isinstance(x, ast.Name) and x.id in tainted}
            for name in sorted(names):
                hits.append((n.lineno, name))
    return hits


def test_no_module_outside_rng_hashes_its_own_random_stream() -> None:
    offenders = []
    for path in sorted(SRC.rglob("*.py")):
        rel = path.relative_to(SRC).as_posix()
        if rel == "rng.py":
            continue
        for line, name in seeded_hash_calls(ast.parse(path.read_text(encoding="utf-8"))):
            if (rel, name) not in ALLOWED:
                offenders.append(f"{rel}:{line} ({name})")
    assert offenders == [], offenders


@pytest.mark.parametrize(
    "source",
    [
        "import hashlib\nhashlib.sha256(f'{seed}|x'.encode())",
        "import hashlib as h\nh.blake2b(str(self._seed).encode())",
        "from hashlib import sha256\nsha256(f'{int(seed)}|{salt}'.encode())",
        "from hashlib import sha256 as s\ns(repr(base_seed).encode())",
        "import hashlib\nraw = f'{int(seed)}|{salt}'.encode()\nhashlib.sha256(raw)",
    ],
)
def test_guard_catches_every_import_form(source: str) -> None:
    assert seeded_hash_calls(ast.parse(source))


def test_guard_ignores_unseeded_hashes() -> None:
    assert seeded_hash_calls(ast.parse("import hashlib\nhashlib.sha256(payload)")) == []


def test_byte_stream_helpers_are_the_old_formulas() -> None:
    import hashlib

    for seed in (0, 7, -3, 2**64 - 1, 10**30):
        for salt in ("", "host", "x|y", "\u00e9"):
            old = hashlib.sha256(f"{int(seed)}|{salt}".encode()).digest()
            assert RNGManager.counter_seed_bytes(seed, salt) == old
            assert RNGManager.counter_digest(f"{seed}|{salt}") == hashlib.sha256(f"{seed}|{salt}".encode()).digest()
            block = RNGManager.counter_block(old + b"m")
            assert block == hashlib.sha256(old + b"m").digest()
