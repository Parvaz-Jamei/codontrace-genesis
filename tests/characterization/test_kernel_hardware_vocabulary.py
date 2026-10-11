"""Kernel vocabulary: no hardware / device / transport words in engine core.

Word list and scope from ENGINE_INTEGRATION_PLAN.md section 2 ("Kernel-vocabulary
rule"): ``esp32``, ``fdc``, ``mqtt``, ``firmware``, ``board``, ``wifi``, ``paho``,
scoped to ``contracts/``, ``life_loop/``, the kernel facade/seams and the
planned ``genesis/swarm/``, ``genesis/journal/``, ``genesis/qd_parametric.py``
and ``genesis/coevolution.py`` (optional until they exist, like import-linter's
parenthesised layers).

Matching is on word tokens of the whole source text (code, comments, strings):
the text is split on non-alphanumerics, ``snake_case`` and ``camelCase``
boundaries, and a token is a hit when it equals a word or is that word
followed by a short digit-bearing model suffix (``esp32s3``, ``fdc1004``,
``fdc2x1x``). ``wi-fi`` / ``wi_fi`` / ``WiFi`` normalise to ``wifi``. So
``dashboard`` or ``onboarding`` are not hits, ``board`` / ``Board`` / ``board_id``
are. The rest of ``genesis/`` is out of scope (it already names ESP32 in the
discovery-wire digest registry).
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

PKG = Path(__file__).resolve().parents[2] / 'src' / 'codontrace'
HARDWARE_WORDS = ('esp32', 'fdc', 'mqtt', 'firmware', 'board', 'wifi', 'paho')
KERNEL_FILES = ('engine.py', 'engine_spec.py', 'engine_runtime.py', 'engine_results.py', 'engine_digest.py',
                'engine_run_result.py', 'engine_claims.py', 'rng.py', 'world.py', 'recorder.py', 'replay.py',
                'trace.py', 'plugins.py', 'topology.py', 'scheduling.py')
KERNEL_DIRS = ('contracts', 'life_loop')
PLANNED = ('genesis/swarm', 'genesis/journal', 'genesis/qd_parametric.py', 'genesis/coevolution.py',
           'genesis/transferability.py')

_WIFI = re.compile(r'wi[-_ ]?fi', re.IGNORECASE)
_WORD = re.compile(r'[A-Za-z0-9]+')
_CAMEL = re.compile(r'[A-Z]+(?=[A-Z][a-z])|[A-Z]?[a-z]+|[A-Z]+|[0-9]+[A-Za-z0-9]*')
_HIT = re.compile('(?:' + '|'.join(HARDWARE_WORDS) + r')(?:[a-z]?[0-9][a-z0-9]{0,5})?')


def hardware_hits(text: str) -> list[str]:
    text = _WIFI.sub('wifi', text)
    hits = []
    for word in _WORD.findall(text):
        # Keep e.g. "ESP32S3" / "FDC1004" whole; split camelCase otherwise.
        parts = [word] if _HIT.fullmatch(word.lower()) else _CAMEL.findall(word)
        hits.extend(p.lower() for p in parts if _HIT.fullmatch(p.lower()))
    return hits


def kernel_paths() -> list[Path]:
    paths = [PKG / name for name in KERNEL_FILES]
    for name in KERNEL_DIRS:
        paths += sorted((PKG / name).rglob('*.py'))
    for name in PLANNED:
        target = PKG / name
        if target.is_dir():
            paths += sorted(target.rglob('*.py'))
        elif target.is_file():
            paths.append(target)
    return paths


@pytest.mark.parametrize(('text', 'expected'), [
    ('ESP32 bridge', ['esp32']), ('esp32s3_node', ['esp32s3']), ('FDC1004 sample', ['fdc1004']),
    ('fdc2x1x', ['fdc2x1x']), ('MqttTransport', ['mqtt']), ('import paho.mqtt.client', ['paho', 'mqtt']),
    ('Wi-Fi node', ['wifi']), ('wifi_ssid', ['wifi']), ('WiFi', ['wifi']), ('board_id', ['board']),
    ('OrangePiBoard', ['board']), ('firmware/esp32', ['firmware', 'esp32']),
    ('dashboard onboarding keyboard boardroom', []), ('fdcx, pahoehoe', []), ('mqttx', []),
])
def test_matcher(text, expected):
    assert hardware_hits(text) == expected


def test_kernel_scope_exists():
    for name in KERNEL_FILES:
        assert (PKG / name).is_file(), f'{name} moved; update KERNEL_FILES'
    for name in KERNEL_DIRS:
        assert (PKG / name).is_dir(), name


def test_engine_kernel_has_no_hardware_words():
    offenders = []
    for path in kernel_paths():
        for lineno, line in enumerate(path.read_text(encoding='utf-8').splitlines(), 1):
            for hit in hardware_hits(line):
                offenders.append(f'{path.relative_to(PKG)}:{lineno}: {hit}')
    assert offenders == []
