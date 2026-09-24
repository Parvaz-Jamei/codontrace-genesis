"""Domain-free life-loop runtime primitives (registry, attachment, coupling, contact, inherit)."""

from codontrace.life_loop.attachment import (
    ATTACH_FAIL_REASONS,
    AttachFailReason,
    AttachmentBook,
    AttachmentSlot,
)
from codontrace.life_loop.contact import (
    CANDIDATE_MODES,
    CONTACT_FAIL_REASONS,
    TRANSFER_MODES,
    CandidateMode,
    ContactAttemptCensus,
    ContactFailReason,
    ContactTransferPolicy,
    MatchRule,
    TransferMode,
    apply_contact,
    select_contact_candidates,
)
from codontrace.life_loop.energy_coupling import (
    COUPLING_FAIL_REASONS,
    CouplingFailReason,
    EnergyCoupling,
    EnergyTransferLedgerEntry,
)
from codontrace.life_loop.inherit_attached import (
    INHERIT_FAIL_REASONS,
    INHERIT_MODES,
    InheritAttachedPolicy,
    InheritAttemptCensus,
    InheritFailReason,
    InheritMode,
    apply_birth_inherit,
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
    "CANDIDATE_MODES",
    "CONTACT_FAIL_REASONS",
    "COUPLING_FAIL_REASONS",
    "CandidateMode",
    "ContactAttemptCensus",
    "ContactFailReason",
    "ContactTransferPolicy",
    "CouplingFailReason",
    "EnergyCoupling",
    "EnergyTransferLedgerEntry",
    "INHERIT_FAIL_REASONS",
    "INHERIT_MODES",
    "InheritAttachedPolicy",
    "InheritAttemptCensus",
    "InheritFailReason",
    "InheritMode",
    "MatchRule",
    "SCHEMA_VERSION",
    "TRANSFER_MODES",
    "TransferMode",
    "PopulationRecord",
    "PopulationRegistry",
    "apply_birth_inherit",
    "apply_contact",
    "select_contact_candidates",
]
