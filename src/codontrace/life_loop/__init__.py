"""Domain-free life-loop runtime primitives (registry, attachment, coupling)."""

from codontrace.life_loop.attachment import (
    ATTACH_FAIL_REASONS,
    AttachFailReason,
    AttachmentBook,
    AttachmentSlot,
)
from codontrace.life_loop.energy_coupling import (
    COUPLING_FAIL_REASONS,
    CouplingFailReason,
    EnergyCoupling,
    EnergyTransferLedgerEntry,
)
from codontrace.life_loop.populations import (
    SCHEMA_VERSION,
    PopulationRecord,
    PopulationRegistry,
)

__all__ = [
    "ATTACH_FAIL_REASONS",
    "AttachFailReason",
    "AttachmentBook",
    "AttachmentSlot",
    "COUPLING_FAIL_REASONS",
    "CouplingFailReason",
    "EnergyCoupling",
    "EnergyTransferLedgerEntry",
    "SCHEMA_VERSION",
    "PopulationRecord",
    "PopulationRegistry",
]
