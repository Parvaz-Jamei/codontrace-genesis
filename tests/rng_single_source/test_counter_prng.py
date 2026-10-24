"""The experiment PRNG is RNGManager's counter stream, bit-identical to before.

golden_counter_prng.json was written by the old math_utils implementation
(commit 7f72ff6) before the move.
"""

from __future__ import annotations

import ast
import hashlib
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


# Every constructor hashlib guarantees on every platform, plus its generic
# and key-derivation entry points.
HASH_FUNCS = set(hashlib.algorithms_guaranteed) | {"new", "file_digest", "pbkdf2_hmac", "scrypt"}
HMAC_FUNCS = {"new", "digest", "HMAC"}
# Seeding another generator is the same mistake as hashing a seed by hand.
RANDOM_FUNCS = {"Random", "seed"}
NP_RANDOM_FUNCS = {
    "default_rng",
    "RandomState",
    "seed",
    "Generator",
    "SeedSequence",
    "PCG64",
    "PCG64DXSM",
    "MT19937",
    "Philox",
    "SFC64",
}
_KIND_FUNCS = {"hashlib": HASH_FUNCS, "hmac": HMAC_FUNCS, "random": RANDOM_FUNCS, "numpy.random": NP_RANDOM_FUNCS}
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
# Serialisers turn a whole structure, dict literals included, into hash input.
_SERIALISERS = {"dumps"}


def _mentions(node: ast.AST, tainted: set[str]) -> set[str]:
    """Seed-like or tainted names used in ``node``.

    Records and payload dicts that merely carry a seed field are digests, not
    streams, so a bare ``{"seed": seed}`` literal does not count. Once the
    structure goes through a serialiser (``json.dumps(...)``) and into a
    hash, it does: that is a seed turned into bytes.
    """
    found: set[str] = set()
    stack: list[tuple[ast.AST, bool]] = [(node, False)]
    while stack:
        sub, keep_dicts = stack.pop()
        if isinstance(sub, ast.Dict) and not keep_dicts:
            continue
        if isinstance(sub, (ast.ListComp, ast.SetComp, ast.GeneratorExp, ast.DictComp)):
            # Targets are local: a target bound from a seed-derived iterable
            # is tainted inside, any other target shadows an outer name.
            local = set(tainted)
            for gen in sub.generators:
                targets = {x.id for x in ast.walk(gen.target) if isinstance(x, ast.Name)}
                hit = _mentions(gen.iter, local)
                found |= hit
                local = (local | targets) if hit else (local - targets)
                for cond in gen.ifs:
                    found |= _mentions(cond, local) - targets
            elts = [sub.key, sub.value] if isinstance(sub, ast.DictComp) else [sub.elt]
            for e in elts:
                found |= _mentions(e, local)
            continue
        if isinstance(sub, ast.Call):
            # Follow data through value conversions only; the result of any
            # other call (a path lookup, a record builder) is not the seed.
            f = sub.func
            fname = f.id if isinstance(f, ast.Name) else f.attr if isinstance(f, ast.Attribute) else ""
            if fname in _SERIALISERS:
                stack.extend((a, True) for a in [*sub.args, *(k.value for k in sub.keywords)])
            elif isinstance(f, ast.Name) and f.id in _TRANSPARENT_FUNCS:
                stack.extend((a, keep_dicts) for a in sub.args)
            elif isinstance(f, ast.Attribute) and f.attr in _TRANSPARENT_METHODS:
                stack.append((f.value, keep_dicts))
                stack.extend((a, keep_dicts) for a in sub.args)
            continue
        name = sub.id if isinstance(sub, ast.Name) else sub.attr if isinstance(sub, ast.Attribute) else None
        if name and (_is_seed_name(name) or name in tainted):
            found.add(name)
        stack.extend((c, keep_dicts) for c in ast.iter_child_nodes(sub))
    return found


def _const_module(node: ast.AST) -> str | None:
    return node.value if isinstance(node, ast.Constant) and isinstance(node.value, str) else None


def _import_call_module(node: ast.AST) -> str | None:
    """``importlib.import_module("m")``, ``import_module("m")``, ``__import__("m")``,
    ``sys.modules["m"]`` and ``sys.modules.get("m")``."""
    if isinstance(node, ast.Subscript) and isinstance(node.value, ast.Attribute) and node.value.attr == "modules":
        return _const_module(node.slice)
    if not isinstance(node, ast.Call) or not node.args:
        return None
    f = node.func
    if (isinstance(f, ast.Attribute) and f.attr == "import_module") or (
        isinstance(f, ast.Name) and f.id in {"import_module", "__import__"}
    ):
        return _const_module(node.args[0])
    if (
        isinstance(f, ast.Attribute)
        and f.attr == "get"
        and isinstance(f.value, ast.Attribute)
        and f.value.attr == "modules"
    ):
        return _const_module(node.args[0])
    return None


def _is_hashlib_import_call(node: ast.AST) -> bool:
    return _import_call_module(node) == "hashlib"


def _assignments(tree: ast.AST) -> list[tuple[list[str], ast.AST]]:
    """Every binding: assignments, walrus, ``for`` targets (bound from their
    iterable) and ``with ... as`` names. Comprehension targets are local to
    the comprehension and are handled in ``_mentions``."""

    def names_in(t: ast.AST) -> list[str]:
        return [x.id for x in ast.walk(t) if isinstance(x, ast.Name)]

    out: list[tuple[list[str], ast.AST]] = []
    for n in ast.walk(tree):
        if isinstance(n, ast.Assign):
            out.append(([x for tgt in n.targets for x in names_in(tgt)], n.value))
        elif isinstance(n, (ast.AnnAssign, ast.AugAssign)) and n.value is not None and isinstance(n.target, ast.Name):
            out.append(([n.target.id], n.value))
        elif isinstance(n, ast.NamedExpr):
            out.append(([n.target.id], n.value))
        elif isinstance(n, (ast.For, ast.AsyncFor)):
            out.append((names_in(n.target), n.iter))
        elif isinstance(n, (ast.With, ast.AsyncWith)):
            out.extend((names_in(i.optional_vars), i.context_expr) for i in n.items if i.optional_vars is not None)
    return out


def _module_kinds(tree: ast.AST) -> tuple[dict[str, str], set[str]]:
    """Names bound to a hashing / RNG module, and names bound to one of their functions."""
    kinds: dict[str, str] = {"hashlib": "hashlib", "hmac": "hmac"}
    funcs: set[str] = set()
    for n in ast.walk(tree):
        if isinstance(n, ast.Import):
            for a in n.names:
                if a.name in _KIND_FUNCS:
                    kinds[a.asname or a.name.split(".")[0]] = a.name if a.asname else a.name.split(".")[0]
                elif a.name == "numpy":
                    kinds[a.asname or "numpy"] = "numpy"
        elif isinstance(n, ast.ImportFrom) and n.module in _KIND_FUNCS:
            for a in n.names:
                if a.name == "*":
                    funcs |= _KIND_FUNCS[n.module]
                elif a.name in _KIND_FUNCS[n.module]:
                    funcs.add(a.asname or a.name)
        elif isinstance(n, ast.ImportFrom) and n.module == "numpy":
            kinds.update({a.asname or a.name: "numpy.random" for a in n.names if a.name == "random"})
    return kinds, funcs


def _analyse(
    root: ast.AST, kinds: dict[str, str], funcs: set[str], helpers: set[str], tainted: set[str]
) -> list[tuple[int, str]]:
    """Hash / RNG calls under ``root`` whose input derives from a seed or ``tainted``."""
    kinds, funcs, tainted = dict(kinds), set(funcs), set(tainted)

    def kind_of(v: ast.AST) -> str | None:
        if isinstance(v, ast.Name):
            return kinds.get(v.id)
        if isinstance(v, ast.Attribute) and v.attr == "random" and kind_of(v.value) == "numpy":
            return "numpy.random"
        return _import_call_module(v)

    def is_hash_func(f: ast.AST) -> bool:
        if isinstance(f, ast.Name):
            return f.id in funcs or f.id in helpers
        if isinstance(f, ast.Attribute):
            k = kind_of(f.value)
            if k in _KIND_FUNCS and f.attr in _KIND_FUNCS[k]:
                return True
            return f.attr in helpers and isinstance(f.value, ast.Name) and f.value.id in {"self", "cls"}
        # getattr(hashlib, anything): any attribute of a hashing module
        return (
            isinstance(f, ast.Call)
            and isinstance(f.func, ast.Name)
            and f.func.id == "getattr"
            and bool(f.args)
            and kind_of(f.args[0]) in _KIND_FUNCS
        )

    assigns = _assignments(root)
    hashers: set[str] = set()
    changed = True
    while changed:
        changed = False
        for names, value in assigns:
            k = kind_of(value)
            if k is not None:
                if any(kinds.get(x) != k for x in names):
                    kinds.update(dict.fromkeys(names, k))
                    changed = True
                continue
            if is_hash_func(value):
                if set(names) - funcs:
                    funcs |= set(names)
                    changed = True
                continue
            if isinstance(value, ast.Call) and is_hash_func(value.func) and set(names) - hashers:
                hashers |= set(names)
                changed = True
            if _mentions(value, tainted) and set(names) - tainted:
                tainted |= set(names)
                changed = True

    hits: list[tuple[int, str]] = []
    for n in ast.walk(root):
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
            found: set[str] = set()
            for a in [*n.args, *(k.value for k in n.keywords)]:
                found |= _mentions(a, tainted)
            hits.extend((n.lineno, name) for name in sorted(found))
    return hits


def seeded_hash_calls(tree: ast.AST) -> list[tuple[int, str]]:
    """Hashes (and other generators) computed from data that derives from a seed.

    The hash is recognised however it is reached: ``import hashlib [as h]``,
    ``from hashlib import sha256 [as x]`` or ``*``, ``importlib.import_module``,
    ``__import__``, ``sys.modules["hashlib"]``, ``getattr(hashlib, name)``,
    bound aliases such as ``H = hashlib.sha256``, every guaranteed algorithm
    (sha224, sha384, shake_256, ...), ``hmac.new`` / ``hmac.digest``, and
    seeding ``random.Random`` or a NumPy generator. Data counts as seed-derived
    when it names a seed or a variable bound from one (assignment, loop
    target, ``with``), followed to a fixed point, including structures passed
    through ``json.dumps``. A local function that hashes one of its own
    parameters is a hashing helper, so passing a seed to it counts too.
    """
    kinds, funcs = _module_kinds(tree)
    defs = [n for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
    helpers: set[str] = set()
    changed = True
    while changed:
        changed = False
        for d in defs:
            if d.name in helpers:
                continue
            params = {a.arg for a in [*d.args.posonlyargs, *d.args.args, *d.args.kwonlyargs]} - {"self", "cls"}
            if not params:
                continue
            body = ast.Module(body=d.body, type_ignores=[])
            if any(name in params or name in helpers for _, name in _analyse(body, kinds, funcs, helpers, params)):
                helpers.add(d.name)
                changed = True
    return _analyse(tree, kinds, funcs, helpers, set())


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
    ids=[
        "attr",
        "alias",
        "from",
        "from-as",
        "one-step",
        "rename",
        "bound-alias",
        "update",
        "two-step",
        "star",
        "import-module",
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
    mutant = (
        text
        + "\n\nimport hashlib\n\n\ndef _planted(seed):\n"
        + "".join(f"    {line}\n" for line in _F10_MUTANTS[kind].splitlines())
    )
    assert seeded_hash_calls(ast.parse(mutant)), kind


# Review F11: further ways to turn a seed into a stream outside rng.py.
_F11_MUTANTS = {
    "getattr": "import hashlib\ngetattr(hashlib, 'sha256')(str(seed).encode())",
    "sys-modules": "import sys\nsys.modules['hashlib'].sha256(str(seed).encode())",
    "hmac": "import hmac\nhmac.new(str(seed).encode(), b'x', 'sha256')",
    "sha384": "import hashlib\nhashlib.sha384(str(seed).encode())",
    "sha224": "from hashlib import sha224\nsha224(str(seed).encode())",
    "shake-256": "import hashlib\nhashlib.shake_256(str(seed).encode()).digest(32)",
    "helper": (
        "import hashlib\n\n"
        "def _h(value):\n    return hashlib.sha256(str(value).encode()).digest()\n\n"
        "def run(seed):\n    return _h(seed)\n"
    ),
    "json-dumps": "import hashlib, json\nhashlib.sha256(json.dumps({'seed': seed}).encode())",
    "loop-variable": "import hashlib\nfor s in [seed]:\n    hashlib.sha256(str(s).encode())",
    "random-Random": "import random\nrandom.Random(seed)",
}


@pytest.mark.parametrize("kind", sorted(_F11_MUTANTS))
def test_f11_bypass_is_flagged(kind: str) -> None:
    assert seeded_hash_calls(ast.parse(_F11_MUTANTS[kind])), kind


@pytest.mark.parametrize("kind", sorted(_F11_MUTANTS))
def test_f11_bypass_in_real_module_is_flagged(kind: str) -> None:
    path = SRC / "experiments" / "math_utils.py"
    text = path.read_text(encoding="utf-8")
    body = "".join(f"    {line}\n" for line in _F11_MUTANTS[kind].splitlines())
    mutant = text + "\n\ndef _planted(seed):\n" + body
    assert seeded_hash_calls(ast.parse(mutant)), kind


def test_comprehension_targets_do_not_leak_between_scopes() -> None:
    source = (
        "import hashlib, json\n"
        "chosen = [int(s) for s in seeds]\n"
        "series = [(int(o), int(s)) for o, s in zip(a, b)]\n"
        "hashlib.sha256(json.dumps(series).encode())\n"
    )
    assert seeded_hash_calls(ast.parse(source)) == []
