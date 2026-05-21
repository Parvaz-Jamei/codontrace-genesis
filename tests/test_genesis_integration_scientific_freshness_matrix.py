from examples.genesis_integration_end_to_end_validation import _scientific_freshness_matrix


def test_scientific_freshness_matrix_has_required_paths_and_statuses():
    payload = _scientific_freshness_matrix()
    rows = payload["rows"]
    assert rows
    for row in rows:
        assert row["capability"]
        assert row["implementation_module"]
        assert row["test_file"]
        assert row["claim_gate"]
        assert row["status"]


def test_oee_and_collective_are_not_overclaimed_in_matrix():
    payload = _scientific_freshness_matrix()
    by_cap = {row["capability"]: row for row in payload["rows"]}
    assert by_cap["Open-endedness"]["status"] in {"descriptive_only", "complete_limited_claim"}
    assert by_cap["Collective/swarm evidence"]["status"] in {"descriptive_only", "complete_limited_claim"}
