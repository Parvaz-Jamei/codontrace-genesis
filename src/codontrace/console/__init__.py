"""Local preview console.

The server module uses only the standard library. It does not import
``codontrace.engine``, ``codontrace.genesis``, or the RNG, and it does not
set ``red_queen_proved``. Starting ``python -m codontrace.console`` still
loads this package's public API, because that is how a subpackage starts.
"""

from __future__ import annotations

__all__ = ["main"]


def main(argv: list[str] | None = None) -> int:
    from codontrace.console.server import main as serve

    return serve(argv)
