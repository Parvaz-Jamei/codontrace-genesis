"""Schema-role translation for ClaimGate adapters.

Campaign JSON may use auxiliary_control, positive_control, or other
local labels. The public bundle only accepts treatment,
mechanism_ablation, channel_off, negative_control, and dose.
Translation stays in the adapter; artifact bytes are not rewritten.
"""

from __future__ import annotations

from collections.abc import Mapping

from codontrace.claimgate.schema import ARM_ROLES as SCHEMA_ROLES

ROLE_ALIASES: dict[str, str] = {
    "auxiliary_control": "negative_control",
    "sensitivity_negative_control": "negative_control",
    "positive_control": "dose",
    "control": "negative_control",
    "secondary_assay": "negative_control",
}


def canonical_role(
    arm_name: str,
    raw_role: str = "",
    *,
    arm_map: Mapping[str, str] | None = None,
) -> str:
    """Map a campaign arm name/role onto a claimgate_bundle_v1 role."""

    candidates: list[str] = []
    if arm_map:
        mapped = arm_map.get(arm_name, "")
        if mapped:
            candidates.append(mapped)
    if raw_role:
        candidates.append(raw_role)
    for item in candidates:
        if item in SCHEMA_ROLES:
            return item
        aliased = ROLE_ALIASES.get(item, "")
        if aliased:
            return aliased
    return ""
