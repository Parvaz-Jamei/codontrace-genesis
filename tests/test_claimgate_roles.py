"""Shared ClaimGate role translation is adapter-only, not an engine fork."""

from __future__ import annotations

from codontrace.claimgate.adapters.roles import ROLE_ALIASES, SCHEMA_ROLES, canonical_role
from codontrace.claimgate.schema import ARM_ROLES


def test_schema_roles_are_the_public_set() -> None:
    assert SCHEMA_ROLES == ARM_ROLES
    assert ROLE_ALIASES["auxiliary_control"] == "negative_control"
    assert ROLE_ALIASES["positive_control"] == "dose"
    assert ROLE_ALIASES["control"] == "negative_control"
    assert ROLE_ALIASES["secondary_assay"] == "negative_control"


def test_canonical_role_prefers_arm_map_then_aliases() -> None:
    arm_map = {"oracle_capsule": "dose", "cost_0": "control"}
    assert canonical_role("oracle_capsule", "positive_control", arm_map=arm_map) == "dose"
    assert canonical_role("cost_0", "control", arm_map=arm_map) == "negative_control"
    assert canonical_role("unknown", "treatment") == "treatment"
    assert canonical_role("unknown", "not_a_role") == ""
