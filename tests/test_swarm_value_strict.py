"""Strict reading-value types for codontrace.swarm.protocol.decode and the shared wire fixtures."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from codontrace.swarm.experiments import reading
from codontrace.swarm.protocol import canonical, decode, reading_value

GOLDEN = Path(__file__).parent / 'golden' / 'swarm'


def manifest() -> dict[str, str]:
    rows = (line.split() for line in (GOLDEN / 'MANIFEST.sha256').read_text().splitlines() if line.strip())
    return {name: digest for digest, name in rows}


def fixtures(kind: str) -> list[Path]:
    return sorted((GOLDEN / kind).glob('*.json'))


def test_manifest_pins_every_fixture_by_sha256() -> None:
    pinned = manifest()
    on_disk = {p.relative_to(GOLDEN).as_posix() for p in GOLDEN.glob('*/*.json')}
    assert set(pinned) == on_disk and len(fixtures('valid')) >= 7 and len(fixtures('invalid')) >= 10
    for name, digest in pinned.items():
        assert hashlib.sha256((GOLDEN / name).read_bytes()).hexdigest() == digest, name


@pytest.mark.parametrize('path', fixtures('valid'), ids=lambda p: p.stem)
def test_valid_fixture_decodes_and_round_trips(path: Path) -> None:
    raw = path.read_bytes()
    first = decode(raw)
    assert first == json.loads(raw)
    assert decode(canonical(first)) == first == decode(first)


@pytest.mark.parametrize('path', fixtures('invalid'), ids=lambda p: p.stem)
def test_invalid_fixture_is_rejected(path: Path) -> None:
    with pytest.raises(ValueError):
        decode(path.read_bytes())


@pytest.mark.parametrize('value', [0, -1.5, 1e12, [-1, 2.25], [0.5] * 256, True, False, 'open', 'µ "q"'])
def test_every_encoder_value_type_is_accepted(value: object) -> None:
    assert reading_value(value) == value


@pytest.mark.parametrize('value', [None, [], [[1.0]], [True], ['1'], {'x': 1}, float('nan'), float('inf'), 1e13,
                                   '', ' ', 'c' * 129, [0.5] * 257])
def test_reading_value_rejects_everything_else(value: object) -> None:
    with pytest.raises(ValueError):
        reading_value(value)


def test_python_v1_encoder_round_trips() -> None:
    message = reading('lab', 'n1', 3, 1000, 21.5)
    assert decode(canonical(message)) == message


@pytest.mark.parametrize('depth', [2, 3, 32, 62])
def test_nested_value_arrays_are_rejected_below_the_document_depth_guard(depth: int) -> None:
    frame = json.loads((GOLDEN / 'valid' / 'v2_vector.json').read_text())
    frame['payload']['value'] = 1.0
    for _ in range(depth):
        frame['payload']['value'] = [frame['payload']['value']]
    with pytest.raises(ValueError, match='finite number required'):
        decode(json.dumps(frame))
