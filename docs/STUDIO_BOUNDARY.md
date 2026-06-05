# CodonTrace Studio Boundary Policy

Status: **required for `0.3.0b1` beta and later**.

This repository is the **CodonTrace Genesis core research library**. It must remain deterministic, dependency-free at runtime, object-first, and suitable for scientific replay/audit workflows.

## Non-negotiable boundary

The following must **not** be added under `src/codontrace`:

- UI code, dashboards, HTML/CSS/JS assets, React/Vite/Tauri code.
- FastAPI, Starlette, Uvicorn, WebSocket, HTTP routes, SSE, or local server lifecycle code.
- Product CLI/launcher/installer code.
- Code-import, dynamic `eval`/`exec` workflows, or user-project sandbox execution.
- Mandatory file-writing workflows for ordinary engine execution.
- Database/cloud/session services.

Studio work belongs in a separate consumer repository, for example `codontrace-studio`, which may depend on `codontrace==0.3.0b1` and adapt the public Python object API into local REST/WebSocket/UI flows.

## Allowed in core

Core may add APIs only when they are useful outside the UI product and remain dependency-free:

- Deterministic engine stepping primitives.
- Replay/evidence/artifact object contracts.
- Typed capability metadata.
- Profiling helpers that use the Python standard library.
- Tests and docs that protect scientific semantics and package hygiene.

## CI guard: AST import scanner, not raw text search

Use `tools/check_core_boundary.py` in CI:

```bash
python tools/check_core_boundary.py
```

This guard uses Python's `ast` module to inspect imports and dynamic import calls under `src/codontrace`. It intentionally does **not** fail on comments, documentation strings, or policy text that mention FastAPI, WebSocket, React, Tauri, or other Studio-only technologies. A raw string search is too noisy for this repository because boundary documentation must be able to name forbidden technologies while still blocking real core dependencies.

Blocked examples:

```python
import fastapi
from fastapi import FastAPI
import importlib
importlib.import_module("uvicorn")
```

Allowed examples:

```python
"""FastAPI is forbidden in core and belongs in Studio."""
FORBIDDEN_POLICY_TEXT = "websocket belongs outside src/codontrace"
```

## Studio API worker/thread ownership note

FastAPI path operations declared with regular `def` are executed in an external threadpool by FastAPI/Starlette. Therefore, the future `codontrace-studio` local API must not let request-handler threadpool behavior implicitly own a long-running `GenesisEngine` run. The Studio sidecar should use an explicit run owner, such as a dedicated worker thread/process or a serialized run queue, and expose REST/WebSocket messages as adapters around that owner. Core must stay unaware of threads, WebSocket transports, and server lifecycle.

## Review checklist

Before merging any PR into this repository:

- `project.dependencies` remains empty unless a core scientific dependency is explicitly justified.
- `codontrace.__version__`, `pyproject.toml`, `CITATION.cff`, `RELEASE_EVIDENCE.md`, and current identity tests agree.
- Public API changes include tests and do not require Studio to import private internals.
- Performance changes preserve replay digests, RNG schedule, final evidence semantics, and claim boundaries.
