"""HE03 ClaimGate adapter is a port. It does not invent research results."""

from __future__ import annotations

from hashlib import sha256

import pytest

from codontrace.claimgate.adapters.codontrace_he03 import bundle_from_hard_experiment_03
from codontrace.errors import ConfigurationError


def test_he03_adapter_refuses_missing_tree_artifact() -> None:
    with pytest.raises(ConfigurationError, match="not in the tree"):
        bundle_from_hard_experiment_03()


def test_he03_in_memory_campaign_uses_schema_roles() -> None:
    digest = sha256(b"he03-claimgate-adapter-toy").hexdigest()
    bundle = bundle_from_hard_experiment_03(
        {
            "seeds": [1000, 1001],
            "protocol_digest": digest,
            "schema_version": "hard_experiment_03_v1",
            "claim_ceiling": "runtime_observation",
            "interventions": [
                {"arm": "cost_0", "role": "control"},
                {"arm": "cost_moderate", "role": "treatment"},
                {"arm": "cost_high", "role": "treatment"},
                {"arm": "channel_off", "role": "channel_off"},
                {"arm": "isolation_probe", "role": "secondary_assay"},
            ],
            "seed_records": [
                {
                    "cost_0": {"d_sym": 0.10},
                    "cost_moderate": {"d_sym": 0.20},
                    "cost_high": {"d_sym": 0.21},
                    "channel_off": {"d_sym": 0.11},
                    "isolation_probe": {"d_sym": 0.09},
                },
                {
                    "cost_0": {"d_sym": 0.12},
                    "cost_moderate": {"d_sym": 0.22},
                    "cost_high": {"d_sym": 0.19},
                    "channel_off": {"d_sym": 0.10},
                    "isolation_probe": {"d_sym": 0.08},
                },
            ],
        }
    )
    roles = {arm.name: arm.role for arm in bundle.arms}
    assert roles["cost_0"] == "negative_control"
    assert roles["cost_moderate"] == "treatment"
    assert roles["isolation_probe"] == "negative_control"
    assert set(roles.values()) <= {
        "treatment",
        "mechanism_ablation",
        "channel_off",
        "negative_control",
        "dose",
    }
    extra = bundle.extra or {}
    assert extra["he03_research_not_in_tree"] is True
    assert extra["claim_ceiling"] == "runtime_observation"
    assert extra["agi"] is False
