"""Translate HE01 campaign arm names/roles into claimgate_bundle_v1 roles.

The v7 artifact uses auxiliary_control, sensitivity_negative_control, and
positive_control. The public schema allows treatment, mechanism_ablation,
channel_off, negative_control, and dose. Translation stays in the adapter;
artifact bytes are not rewritten.
"""

from __future__ import annotations

ARM_ROLES: dict[str, str] = {
    "source_bias_on": "treatment",
    "source_bias_off": "mechanism_ablation",
    "capsules_off": "channel_off",
    "capsules_shuffled": "negative_control",
    "oracle_capsule": "dose",
    "capsules_content_null": "negative_control",
    "capsules_activity_matched": "negative_control",
}
ROLE_ALIASES: dict[str, str] = {
    "auxiliary_control": "negative_control",
    "sensitivity_negative_control": "negative_control",
    "positive_control": "dose",
}
SCHEMA_ROLES = frozenset(
    {
        "treatment",
        "mechanism_ablation",
        "channel_off",
        "negative_control",
        "dose",
    }
)


def canonical_role(arm_name: str, raw_role: str = "") -> str:
    mapped = ARM_ROLES.get(arm_name, "")
    if mapped:
        return mapped
    if raw_role in SCHEMA_ROLES:
        return raw_role
    return ROLE_ALIASES.get(raw_role, "")
