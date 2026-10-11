"""Domain-free life-loop contracts (event schemas + digests).

Kernel extension surface for the modular ALife platform. Discipline modules
configure primitives; they do not reimplement tick physics here.
"""

from codontrace.contracts.banned import BANNED_DOMAIN_TOKENS
from codontrace.contracts.digest_contract import SCHEMA_VERSION as DIGEST_SCHEMA_VERSION
from codontrace.contracts.digest_contract import world_digest
from codontrace.contracts.life_loop_events import (
    EVENT_TYPES,
    HOOK_NAMES,
    SCHEMA_VERSION,
    AblationArmEvent,
    AttachmentEvent,
    BirthAttachEvent,
    ContactEvent,
    EnergyCouplingEvent,
    LifeLoopEvent,
    LifeLoopEventEnvelope,
    PopulationRegistryEvent,
    ScheduleLockEvent,
    load_event,
)
from codontrace.contracts.wire_validation import (
    bounded_int,
    bounded_text,
    exact_keys,
    finite_number,
    identifier,
    wire_canonical,
)

__all__ = [
    "AblationArmEvent",
    "AttachmentEvent",
    "BANNED_DOMAIN_TOKENS",
    "BirthAttachEvent",
    "ContactEvent",
    "DIGEST_SCHEMA_VERSION",
    "EVENT_TYPES",
    "EnergyCouplingEvent",
    "HOOK_NAMES",
    "LifeLoopEvent",
    "LifeLoopEventEnvelope",
    "PopulationRegistryEvent",
    "SCHEMA_VERSION",
    "ScheduleLockEvent",
    "bounded_int",
    "bounded_text",
    "exact_keys",
    "finite_number",
    "identifier",
    "load_event",
    "wire_canonical",
    "world_digest",
]
