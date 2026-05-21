from codontrace.genesis.evidence_consistency import audit_result_evidence_consistency


def test_fake_placeholder_not_run_cannot_be_positive_evidence():
    out = audit_result_evidence_consistency(claims=[
        {"status":"allowed", "required_evidence":["fake"]},
        {"status":"claim_ready", "required_evidence":["placeholder"]},
        {"status":"measured", "required_evidence":["not_run:replay"]},
    ])
    assert not out["passed"]
    assert sum(1 for issue in out["issues"] if issue["code"] == "positive_claim_with_non_real_digest") >= 3
