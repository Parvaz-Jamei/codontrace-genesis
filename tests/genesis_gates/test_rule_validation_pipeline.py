from __future__ import annotations

import pytest

from codontrace.errors import ConfigurationError
from codontrace.genesis.rules import (
    ApprovalStatus,
    ApprovedRuleSet,
    HumanApprovalRecord,
    RuleProposal,
    RuleProposalSource,
    RuleSetDiff,
    RuleValidator,
)


def test_rule_validation_blocks_unsafe_and_requires_human_approval() -> None:
    validator = RuleValidator()
    bad = RuleProposal(
        "p1",
        RuleProposalSource.LLM,
        RuleSetDiff(
            add=({"output_element": "Unknown", "conservative": False, "code": "print(1)"},)
        ),
    )
    result = validator.validate(bad)
    assert not result.passed
    assert "unknown_output_element" in result.issues
    good = RuleProposal(
        "p2", RuleProposalSource.HUMAN, RuleSetDiff(add=({"output_element": "Lumen", "radius": 1},))
    )
    good_result = validator.validate(good)
    assert good_result.passed
    with pytest.raises(ConfigurationError):
        ApprovedRuleSet(
            good,
            good_result,
            HumanApprovalRecord(
                good.digest(), "lead", ApprovalStatus.PENDING, "not yet", good_result.digest()
            ),
        )
    approved = ApprovedRuleSet(
        good,
        good_result,
        HumanApprovalRecord(
            good.digest(), "lead", ApprovalStatus.APPROVED, "ok", good_result.digest()
        ),
    )
    assert approved.digest()
