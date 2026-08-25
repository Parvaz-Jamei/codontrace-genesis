"""Scientific evidence tests for heldout generalization protocol discipline."""

from __future__ import annotations

from codontrace.genesis.generalization import GeneralizationResult


def test_protocol_not_run_is_never_claim_eligible() -> None:
    result = GeneralizationResult(
        evaluation_id="engine_heldout_protocol_not_run_demo",
        train_digest="not_run:train",
        heldout_digest="not_run:heldout",
        score=0.0,
        claim_eligible=True,  # attempted override must be stripped
        status="protocol_not_run",
    )
    assert result.status == "protocol_not_run"
    assert result.claim_eligible is False


def test_identical_train_heldout_digest_rejects_claim() -> None:
    digest = "abc123"
    result = GeneralizationResult(
        evaluation_id="same",
        train_digest=digest,
        heldout_digest=digest,
        score=0.9,
        claim_eligible=True,
        status="measured",
    )
    assert result.claim_eligible is False


def test_measured_distinct_heldout_can_be_claim_eligible() -> None:
    result = GeneralizationResult(
        evaluation_id="real_heldout",
        train_digest="train_world_digest",
        heldout_digest="heldout_world_digest",
        score=0.42,
        claim_eligible=True,
        status="measured",
    )
    assert result.claim_eligible is True
    assert result.status == "measured"


def test_first_vs_last_proxy_style_not_run_marker() -> None:
    # Engine must emit not_run markers rather than tick digests as fake heldout.
    result = GeneralizationResult(
        evaluation_id="engine_heldout_protocol_not_run_x",
        train_digest="not_run:train",
        heldout_digest="not_run:heldout",
        score=0.0,
        claim_eligible=False,
        status="protocol_not_run",
    )
    assert result.train_digest.startswith("not_run")
    assert result.heldout_digest.startswith("not_run")
