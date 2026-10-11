"""Golden-file helper for characterization tests.

The fixtures under ``golden/`` pin what the code does today, not what it
should do. A mismatch is a failure by default. To regenerate after an
intentional, reviewed change run locally:

    CODONTRACE_UPDATE_GOLDENS=1 pytest tests/characterization

then inspect ``git diff tests/characterization/golden`` before committing.
Regeneration is refused when ``CI`` is set, and a missing fixture is a
failure (never silently created), so drift detection cannot be switched off
by accident.
"""
from __future__ import annotations

import json
import math
import os
import shutil
from pathlib import Path
from typing import Any

import pytest

GOLDEN_DIR = Path(__file__).resolve().parent / 'golden'
UPDATE_ENV = 'CODONTRACE_UPDATE_GOLDENS'


def updating() -> bool:
    if os.environ.get(UPDATE_ENV, '') not in ('', '0'):
        if os.environ.get('CI'):
            pytest.fail(f'{UPDATE_ENV} must not be set on CI; regenerate goldens locally and commit them')
        return True
    return False


def golden_json_bytes(value: Any) -> bytes:
    """Stable text form: sorted keys, repr-exact floats, no NaN/inf, trailing newline."""
    return (json.dumps(value, sort_keys=True, indent=1, ensure_ascii=True, allow_nan=False) + '\n').encode('ascii')


def _missing(path: Path) -> None:
    pytest.fail(f'golden fixture {path.relative_to(GOLDEN_DIR)} is missing; '
                f'create it with {UPDATE_ENV}=1 and review the result')


def check_bytes(name: str, data: bytes) -> None:
    path = GOLDEN_DIR / name
    if updating():
        path.parent.mkdir(parents=True, exist_ok=True)
        if not path.exists() or path.read_bytes() != data:
            path.write_bytes(data)
        return
    if not path.is_file():
        _missing(path)
    expected = path.read_bytes()
    if data != expected:
        # Report the first differing offset; full diffs of hashed bytes are noise.
        offset = next((i for i, (a, b) in enumerate(zip(data, expected)) if a != b), min(len(data), len(expected)))
        pytest.fail(f'{name} drifted from golden fixture: {len(data)} vs {len(expected)} bytes, '
                    f'first difference at byte {offset}: got {data[offset:offset + 80]!r}, '
                    f'expected {expected[offset:offset + 80]!r}')


def check_json(name: str, value: Any) -> None:
    check_bytes(name, golden_json_bytes(value))


def load_json(name: str) -> Any:
    path = GOLDEN_DIR / name
    if not path.is_file():
        _missing(path)
    return json.loads(path.read_text(encoding='ascii'))


def _tree(root: Path) -> dict[str, bytes]:
    return {p.relative_to(root).as_posix(): p.read_bytes() for p in sorted(root.rglob('*')) if p.is_file()}


def check_tree(name: str, produced: Path) -> None:
    """Every file under ``produced`` must equal the golden directory byte for byte (no extra, none missing)."""
    target = GOLDEN_DIR / name
    got = _tree(produced)
    if updating():
        if target.exists() and _tree(target) == got:
            return
        shutil.rmtree(target, ignore_errors=True)
        shutil.copytree(produced, target)
        return
    if not target.is_dir():
        _missing(target)
    expected = _tree(target)
    assert sorted(got) == sorted(expected), f'{name}: file layout drifted'
    for rel in sorted(expected):
        check_bytes(f'{name}/{rel}', got[rel])


def _close_diff(got: Any, expected: Any, path: str, rel_tol: float, abs_tol: float,
                loose_ints: dict[str, float] | None = None) -> str | None:
    """First structural or numeric difference, or None. Floats compare with a tolerance, all else exactly."""
    if isinstance(expected, bool) or isinstance(got, bool) or expected is None or isinstance(expected, str):
        return None if (type(got) is type(expected) and got == expected) else f'{path}: {got!r} != {expected!r}'
    if isinstance(expected, (int, float)) and isinstance(got, (int, float)):
        if isinstance(expected, int) and isinstance(got, int):
            loose = (loose_ints or {}).get(path.rsplit('.', 1)[-1])
            if got == expected or (loose is not None and abs(got - expected) <= loose * abs(expected)):
                return None
            return f'{path}: {got!r} != {expected!r}'
        if math.isclose(got, expected, rel_tol=rel_tol, abs_tol=abs_tol):
            return None
        return f'{path}: {got!r} not within rel {rel_tol}/abs {abs_tol} of {expected!r}'
    if isinstance(expected, list) and isinstance(got, list):
        if len(got) != len(expected):
            return f'{path}: length {len(got)} != {len(expected)}'
        for i, (a, b) in enumerate(zip(got, expected)):
            if (diff := _close_diff(a, b, f'{path}[{i}]', rel_tol, abs_tol, loose_ints)) is not None:
                return diff
        return None
    if isinstance(expected, dict) and isinstance(got, dict):
        if sorted(got) != sorted(expected):
            return f'{path}: keys {sorted(got)} != {sorted(expected)}'
        for key in sorted(expected):
            if (diff := _close_diff(got[key], expected[key], f'{path}.{key}', rel_tol, abs_tol, loose_ints)) is not None:
                return diff
        return None
    return f'{path}: type {type(got).__name__} != {type(expected).__name__}'


def check_json_close(name: str, value: Any, *, rel_tol: float = 1e-9, abs_tol: float = 1e-12,
                     loose_ints: dict[str, float] | None = None) -> None:
    """Like ``check_json`` but floats only need to agree to ``rel_tol``/``abs_tol``.

    For outputs of float arithmetic that legitimately differs in the last bits
    across Python versions or platforms (``sum()`` became compensated in 3.12;
    ``math.sin`` comes from the platform libm). Structure, keys, strings,
    booleans and integers (RNG draw counts, ids) are still exact, except the
    integers named in ``loose_ints`` (key -> relative tolerance), for counts
    derived from float text such as the byte length of a JSON payload.
    """
    value = json.loads(golden_json_bytes(value))  # same normalization as the stored form
    if updating():
        check_json(name, value)
        return
    if (diff := _close_diff(value, load_json(name), '$', rel_tol, abs_tol, loose_ints)) is not None:
        pytest.fail(f'{name} drifted from golden fixture: {diff}')
