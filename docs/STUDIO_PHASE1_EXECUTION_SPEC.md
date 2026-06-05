# CodonTrace Studio — Phase 1 Core-Safe Execution Spec

Status: public beta handoff for `codontrace` `0.3.0b1`.

This document is the Markdown companion to `docs/STUDIO_PHASE1_EXECUTION_SPEC.html`. Keep the HTML file for the designed handoff view and use this Markdown file for GitHub review, diffs, and PR discussion.

## 1. Core boundary

`codontrace-genesis` must remain a pure Python research library. Do not add UI, dashboard, FastAPI, Uvicorn, Starlette, WebSocket server, React, Vite, Tauri, product installer, product CLI, or Code Import workflows to `src/codontrace`.

All Studio product work belongs in a separate `codontrace-studio` repository or app layer.

## 2. Version and Python support

The beta release identity is `0.3.0b1` and must stay aligned across:

- `pyproject.toml`
- `src/codontrace/__init__.py`
- `src/codontrace/genesis/__init__.py`
- release labels and artifact names
- docs and tests
- wheel metadata

Supported Python range for this beta line is:

```toml
requires-python = ">=3.11,<3.15"
```

CI must verify Python `3.11`, `3.12`, `3.13`, and `3.14`. Python `3.14.5` is the latest stable release checked for this handoff. Python `3.15+` should be added only after a stable release and dedicated CI validation.

## 3. GitHub Actions requirements

The core CI must have a real cross-OS smoke matrix:

```yaml
strategy:
  fail-fast: false
  matrix:
    os: [ubuntu-latest, windows-latest, macos-latest]
    python-version: ["3.11", "3.12", "3.13", "3.14"]
runs-on: ${{ matrix.os }}
```

Use current official action majors for this beta handoff:

```yaml
- uses: actions/checkout@v6
- uses: actions/setup-python@v6
- uses: actions/upload-artifact@v7
- uses: actions/download-artifact@v8
```

## 4. AST boundary guard

Use `tools/check_core_boundary.py` as an AST-based guard, not a raw text search. It should block real imports and dynamic imports such as:

```python
import fastapi
from starlette.websockets import WebSocket
importlib.import_module("uvicorn")
```

It should not fail merely because docs, comments, or strings mention forbidden product-layer technologies.

## 5. FastAPI worker ownership note for Studio

If Studio uses FastAPI, do not let long Genesis runs be owned implicitly by FastAPI route execution. FastAPI may execute normal `def` path operations in an external threadpool. Studio should own Genesis execution through an explicit worker, process, or serialized run queue. REST and WebSocket endpoints should only adapt to that worker state.

## 6. Live execution path

For benchmarks and docs, prefer explicit non-zero run specs:

```python
from codontrace.genesis import GenesisEngine, GenesisExperimentSpec

spec = GenesisExperimentSpec(tick_count=50, seed=7)
result = GenesisEngine.from_spec(spec).run_ticks()
print(result.digest())
```

Avoid confusing examples with a zero-tick run in official handoff docs.

## 7. Acceptance checklist

- Runtime core dependencies stay empty.
- `python tools/check_core_boundary.py` passes.
- `python -m compileall -q src tests examples tools` passes.
- Release tests and Genesis gates pass.
- Wheel metadata reports `Version: 0.3.0b1`.
- Clean wheel install can import `codontrace` and run a tiny `GenesisEngine` smoke test.
- GitHub Actions validates Ubuntu, Windows, and macOS across Python `3.11`–`3.14`.

## 8. Commercial license gate

The core license remains `AGPL-3.0-or-later`. Commercial closed-source, SaaS, or proprietary Studio distribution needs a separate license strategy before release.
