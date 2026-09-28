"""Generation-boundary observer hooks for discovery phase-2 ledger ops.

Thin wrappers that satisfy GenerationBoundaryObserver
(``__call__(self, *, generation_index: int) -> None``) and apply
scheduled contact/ATP ledger interventions outside engine.py.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any

from codontrace.errors import ConfigurationError
from codontrace.life_loop.contact_atp_ledger import ContactAtpLedger

BoundaryOp = Callable[[ContactAtpLedger, int], Any]


@dataclass(slots=True)
class ScheduledLedgerHook:
    """Apply a ledger op at selected generation indices, then advance."""

    ledger: ContactAtpLedger
    schedule: Mapping[int, Sequence[BoundaryOp]]
    history: list[dict[str, Any]] = field(default_factory=list)
    auto_advance: bool = True

    def __call__(self, *, generation_index: int) -> None:
        if not isinstance(generation_index, int) or isinstance(generation_index, bool):
            raise ConfigurationError("generation_index must be an integer.")
        ops = self.schedule.get(int(generation_index), ())
        results: list[Any] = []
        for op in ops:
            results.append(op(self.ledger, int(generation_index)))
        self.history.append(
            {
                "generation_index": int(generation_index),
                "n_ops": len(results),
                "results": results,
            }
        )
        if self.auto_advance:
            # Keep ledger generation_index aligned with the observer call.
            if self.ledger.generation_index < int(generation_index):
                self.ledger.generation_index = int(generation_index)
            self.ledger.advance_generation()


def make_op(method_name: str, **kwargs: Any) -> BoundaryOp:
    """Build a BoundaryOp that calls ``ContactAtpLedger.<method_name>(**kwargs)``."""

    name = str(method_name).strip()
    if not name or name.startswith("_"):
        raise ConfigurationError(f"invalid ledger method: {method_name!r}.")

    def _op(ledger: ContactAtpLedger, generation_index: int) -> Any:
        del generation_index  # schedule already selected the boundary
        method = getattr(ledger, name, None)
        if not callable(method):
            raise ConfigurationError(f"ledger has no op {name!r}.")
        return method(**kwargs)

    _op.__name__ = f"ledger_op_{name}"
    return _op


def run_boundary_loop(
    ledger: ContactAtpLedger,
    *,
    generations: int,
    schedule: Mapping[int, Sequence[BoundaryOp]] | None = None,
) -> list[dict[str, Any]]:
    """Drive a short generation-boundary loop with an optional schedule."""

    if not isinstance(generations, int) or isinstance(generations, bool) or generations < 1:
        raise ConfigurationError("generations must be an int >= 1.")
    hook = ScheduledLedgerHook(ledger=ledger, schedule=dict(schedule or {}), auto_advance=True)
    for g in range(int(generations)):
        hook(generation_index=g)
    return list(hook.history)
