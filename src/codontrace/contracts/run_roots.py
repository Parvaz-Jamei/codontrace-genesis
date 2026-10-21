"""Where runs of each kind live (standard library only).

* ``simulation``: ``CODONTRACE_RUNS_DIR`` (created), else ``./simulation_runs``
  if it is a directory, else ``~/simulation_runs`` if it is a directory, else
  ``./simulation_runs`` (created).
* ``swarm``: ``CODONTRACE_SWARM_DIR``, else ``~/.local/share/codontrace/swarm_runs``;
  must be absolute (storage must not depend on the working directory); not created.

Other run kinds take an explicit output directory.
"""
from __future__ import annotations

import os
from pathlib import Path

__all__ = ['SHARED_ROOT_KINDS', 'resolve_run_root']

SHARED_ROOT_KINDS = ('simulation', 'swarm')


def resolve_run_root(kind: str) -> Path:
    if kind == 'simulation':
        custom = os.environ.get("CODONTRACE_RUNS_DIR", "").strip()
        if custom:
            p = Path(custom).expanduser()
            p.mkdir(parents=True, exist_ok=True)
            return p
        local = Path("simulation_runs").resolve()
        if local.is_dir():
            return local
        home_runs = Path.home() / "simulation_runs"
        if home_runs.is_dir():
            return home_runs
        local.mkdir(parents=True, exist_ok=True)
        return local
    if kind == 'swarm':
        root = Path(os.environ.get('CODONTRACE_SWARM_DIR',
                                   str(Path.home() / '.local' / 'share' / 'codontrace' / 'swarm_runs'))).expanduser()
        if not root.is_absolute():
            raise ValueError('CODONTRACE_SWARM_DIR must be absolute; storage must not depend on CWD')
        return root.resolve()
    raise ValueError(f'no shared run root for kind {kind!r}; pass an explicit output directory')
