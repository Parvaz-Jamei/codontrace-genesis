"""Simulator-agnostic ClaimGate evidence auditor for CodonTrace Genesis.

Public ladder names are CLAIMS.md §5 (levels 0–5). Rules are CLAIMS.md §5
and §8. Forbidden aliases are unchanged. This package does not import the
Genesis engine or population modules.
"""

from codontrace.claimgate.auditor import ClaimAuditReport, audit_bundle
from codontrace.claimgate.domain import (
    ALIFE,
    BIOMEDICAL,
    HARDWARE,
    PROFILES,
    DomainProfile,
    bundle_from_declared_scores,
)
from codontrace.claimgate.ladder import (
    INTERNAL_TO_PUBLIC_LEVEL,
    PUBLIC_CLAIM_LEVEL_NAMES,
    PUBLIC_LADDER,
    public_level_for_internal,
    public_level_name,
    public_level_title,
)
from codontrace.claimgate.schema import (
    SCHEMA_VERSION,
    ClaimgateArm,
    ClaimgateArtifact,
    ClaimgateBundle,
    ClaimgateComparison,
    ClaimgateOutcome,
    ClaimgateReplay,
    ClaimgateSoftware,
    parse_claimgate_bundle,
)

__all__ = [
    "ALIFE",
    "BIOMEDICAL",
    "ClaimAuditReport",
    "ClaimgateArm",
    "ClaimgateArtifact",
    "ClaimgateBundle",
    "ClaimgateComparison",
    "ClaimgateOutcome",
    "ClaimgateReplay",
    "ClaimgateSoftware",
    "DomainProfile",
    "HARDWARE",
    "INTERNAL_TO_PUBLIC_LEVEL",
    "PROFILES",
    "PUBLIC_CLAIM_LEVEL_NAMES",
    "PUBLIC_LADDER",
    "SCHEMA_VERSION",
    "audit_bundle",
    "bundle_from_declared_scores",
    "parse_claimgate_bundle",
    "public_level_for_internal",
    "public_level_name",
    "public_level_title",
]
