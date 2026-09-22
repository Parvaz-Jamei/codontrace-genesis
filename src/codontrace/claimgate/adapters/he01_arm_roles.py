"""HE01 arm names for ClaimGate. Shared translation lives in ``roles``."""

from __future__ import annotations

from codontrace.claimgate.adapters.roles import ROLE_ALIASES, SCHEMA_ROLES
from codontrace.claimgate.adapters.roles import canonical_role as _canonical_role

ARM_ROLES: dict[str, str] = {
    "source_bias_on": "treatment",
    "source_bias_off": "mechanism_ablation",
    "capsules_off": "channel_off",
    "capsules_shuffled": "negative_control",
    "oracle_capsule": "dose",
    "capsules_content_null": "negative_control",
    "capsules_activity_matched": "negative_control",
}


def canonical_role(arm_name: str, raw_role: str = "") -> str:
    return _canonical_role(arm_name, raw_role, arm_map=ARM_ROLES)


__all__ = ["ARM_ROLES", "ROLE_ALIASES", "SCHEMA_ROLES", "canonical_role"]
