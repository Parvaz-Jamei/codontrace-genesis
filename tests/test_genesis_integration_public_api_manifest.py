from codontrace.genesis.public_api_manifest import (
    ROOT_PUBLIC_API_POLICY,
    build_public_api_manifest,
    import_public_symbol,
    validate_public_api_manifest,
)


def test_public_api_manifest_imports_stable_symbols():
    rows = build_public_api_manifest()
    stable = [row for row in rows if row.stability_status == "stable"]
    assert stable
    for row in stable:
        assert import_public_symbol(row) is not None


def test_provisional_symbols_not_claim_ready_and_policy_is_explicit():
    rows = build_public_api_manifest()
    assert ROOT_PUBLIC_API_POLICY == "genesis_scientific_api_under_codontrace.genesis"
    assert all(not row.claim_ready_allowed for row in rows if row.stability_status == "provisional")
    audit = validate_public_api_manifest(rows)
    assert audit["passed"], audit["issues"]
