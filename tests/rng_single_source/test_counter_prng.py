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


def _is_seed_name(name: str) -> bool:
    return "seed" in name.lower()


_TRANSPARENT_FUNCS = {"int", "str", "repr", "bytes", "bytearray", "hex", "abs", "format", "float"}
_TRANSPARENT_METHODS = {"encode", "to_bytes", "format", "join", "hex", "digest", "hexdigest"}


def _mentions(node: ast.AST, tainted: set[str]) -> set[str]:
    """Seed-like or tainted names used in ``node``, skipping dict literals.

    Records and payload dicts that merely carry a seed field are digests, not
    streams, so a ``{"seed": seed}`` literal does not count.
    """
    found: set[str] = set()
    stack = [node]
    while stack:
        sub = stack.pop()
        if isinstance(sub, ast.Dict):
            continue
        if isinstance(sub, ast.Call):
            # Follow data through value conversions only; the result of any
            # other call (a path lookup, a record builder) is not the seed.
            f = sub.func
            if isinstance(f, ast.Name) and f.id in _TRANSPARENT_FUNCS:
                stack.extend(sub.args)
            elif isinstance(f, ast.Attribute) and f.attr in _TRANSPARENT_METHODS:
                stack.append(f.value)
                stack.extend(sub.args)
            continue
        name = sub.id if isinstance(sub, ast.Name) else sub.attr if isinstance(sub, ast.Attribute) else None
        if name and (_is_seed_name(name) or name in tainted):
            found.add(name)
        stack.extend(ast.iter_child_nodes(sub))
    return found


def _is_hashlib_import_call(node: ast.AST) -> bool:
    """``importlib.import_module("hashlib")``, ``import_module(...)``, ``__import__(...)``."""
    if not isinstance(node, ast.Call) or not node.args:
        return False
    arg = node.args[0]
    if not (isinstance(arg, ast.Constant) and arg.value == "hashlib"):
        return False
    f = node.func
    return (isinstance(f, ast.Attribute) and f.attr == "import_module") or (
        isinstance(f, ast.Name) and f.id in {"import_module", "__import__"}
    )


def _assignments(tree: ast.AST) -> list[tuple[list[str], ast.AST]]:
    out: list[tuple[list[str], ast.AST]] = []
    for n in ast.walk(tree):
        if isinstance(n, ast.Assign):
            names = [t.id for tgt in n.targets for t in ast.walk(tgt) if isinstance(t, ast.Name)]
            out.append((names, n.value))
        elif isinstance(n, (ast.AnnAssign, ast.AugAssign)) and n.value is not None and isinstance(n.target, ast.Name):
            out.append(([n.target.id], n.value))
        elif isinstance(n, ast.NamedExpr):
            out.append(([n.target.id], n.value))
    return out


def seeded_hash_calls(tree: ast.AST) -> list[tuple[int, str]]:
    """Hashes computed from data that derives from a seed.

    Recognises the hash however it is reached: ``import hashlib [as h]``,
    ``h = importlib.import_module("hashlib")``, ``from hashlib import sha256
    [as x]``, ``from hashlib import *``, and bound aliases such as
    ``H = hashlib.sha256``. Data counts as seed-derived when it names a seed or
    a variable assigned (transitively, to a fixed point) from one, so
    ``s = seed`` and two-step ``a = f(seed); b = g(a)`` are followed. Both
    constructor arguments and ``hasher.update(...)`` calls are checked.
    """
    modules = {"hashlib"}
    funcs: set[str] = set()
    for n in ast.walk(tree):
        if isinstance(n, ast.Import):
            modules |= {a.asname or a.name for a in n.names if a.name == "hashlib"}
        elif isinstance(n, ast.ImportFrom) and n.module == "hashlib":
            for a in n.names:
                if a.name == "*":
                    funcs |= HASH_FUNCS
                else:
                    funcs.add(a.asname or a.name)
    assigns = _assignments(tree)

    def is_hash_func(f: ast.AST) -> bool:
        if isinstance(f, ast.Name):
            return f.id in funcs
        if isinstance(f, ast.Attribute) and f.attr in HASH_FUNCS:
            v = f.value
            return (isinstance(v, ast.Name) and v.id in modules) or _is_hashlib_import_call(v)
        return False

    hashers: set[str] = set()
    tainted: set[str] = set()
    changed = True
    while changed:
        changed = False
        for names, value in assigns:
            new: set[str] = set()
            if _is_hashlib_import_call(value) or (isinstance(value, ast.Name) and value.id in modules):
                if not set(names) <= modules:
                    modules |= set(names)
                    changed = True
                continue
            if is_hash_func(value):
                new_funcs = set(names) - funcs
                if new_funcs:
                    funcs |= new_funcs
                    changed = True
                continue
            if isinstance(value, ast.Call) and is_hash_func(value.func):
                new_h = set(names) - hashers
                if new_h:
                    hashers |= new_h
                    changed = True
            if _mentions(value, tainted):
                new = set(names) - tainted
            if new:
                tainted |= new
                changed = True

    hits: list[tuple[int, str]] = []
    for n in ast.walk(tree):
        if not isinstance(n, ast.Call):
            continue
        f = n.func
        checked = is_hash_func(f) or (
            isinstance(f, ast.Attribute)
            and f.attr == "update"
            and (
                (isinstance(f.value, ast.Name) and f.value.id in hashers)
                or (isinstance(f.value, ast.Call) and is_hash_func(f.value.func))
            )
        )
        if checked:
            names: set[str] = set()
            for a in [*n.args, *(k.value for k in n.keywords)]:
                names |= _mentions(a, tainted)
            hits.extend((n.lineno, name) for name in sorted(names))
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
        # Review F10 residuals: each was missed by the previous guard.
        "import hashlib\ns = seed\nhashlib.sha256(str(s).encode())",
        "import hashlib\nH = hashlib.sha256\nH(f'{seed}'.encode())",
        "import hashlib\nhasher = hashlib.sha256()\nhasher.update(str(seed).encode())",
        "import hashlib\na = int(seed) + 1\nb = str(a).encode()\nhashlib.sha256(b)",
        "from hashlib import *\nsha256(f'{seed}'.encode())",
        "import importlib\nh = importlib.import_module('hashlib')\nh.sha256(f'{seed}'.encode())",
    ],
    ids=["attr", "alias", "from", "from-as", "one-step", "rename", "bound-alias", "update", "two-step", "star",
         "import-module"],
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


_F10_MUTANTS = {
    "rename": "s = seed\nhashlib.sha256(str(s).encode())",
    "bound-alias": "H = hashlib.sha256\nH(f'{seed}'.encode())",
    "update": "hasher = hashlib.sha256()\nhasher.update(str(seed).encode())",
    "two-step": "a = int(seed) + 1\nb = str(a).encode()\nhashlib.sha256(b)",
    "star": "from hashlib import *\nsha256(f'{seed}'.encode())",
    "import-module": "import importlib\nh = importlib.import_module('hashlib')\nh.sha256(f'{seed}'.encode())",
}


@pytest.mark.parametrize("kind", sorted(_F10_MUTANTS))
def test_mutated_source_module_is_flagged(kind: str) -> None:
    """Each review-F10 bypass, planted in a real module, is caught by the scan."""
    path = SRC / "experiments" / "math_utils.py"
    text = path.read_text(encoding="utf-8")
    assert seeded_hash_calls(ast.parse(text)) == []
    mutant = text + "\n\nimport hashlib\n\n\ndef _planted(seed):\n" + "".join(
        f"    {line}\n" for line in _F10_MUTANTS[kind].splitlines()
    )
    assert seeded_hash_calls(ast.parse(mutant)), kind
