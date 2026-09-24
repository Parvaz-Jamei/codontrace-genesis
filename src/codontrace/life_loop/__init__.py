"""Domain-free life-loop runtime primitives (registry first; physics later)."""

from codontrace.life_loop.populations import (
    SCHEMA_VERSION,
    PopulationRecord,
    PopulationRegistry,
)

__all__ = [
    "SCHEMA_VERSION",
    "PopulationRecord",
    "PopulationRegistry",
]
