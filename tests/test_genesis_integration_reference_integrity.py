from pathlib import Path
from tools.audit_genesis_references import audit
from tools.audit_examples_integration import audit as audit_examples


def test_reference_audit_fails_on_unallowlisted_old_artifact_key(tmp_path):
    src = tmp_path / "src" / "codontrace"
    src.mkdir(parents=True)
    (src / "bad.py").write_text("placeholder_claim_ready = True", encoding="utf-8")
    result = audit(tmp_path)
    assert not result["passed"]
    assert result["issues"][0]["label"] == "old_artifact_key"


def test_reference_audit_allows_intentional_negative_test_fixture(tmp_path):
    tests = tmp_path / "tests"
    tests.mkdir()
    (tests / "test_negative.py").write_text("claim_supported=True # not_run:fixture", encoding="utf-8")
    (tmp_path / "tools").mkdir()
    (tmp_path / "tools" / "audit_allowlist_integration.json").write_text('{"paths": [], "patterns": [{"path":"tests/**", "label":"positive_not_run"}]}', encoding="utf-8")
    assert audit(tmp_path)["passed"]


def test_examples_audit_rejects_private_import(tmp_path):
    examples = tmp_path / "examples"
    examples.mkdir()
    (examples / "bad.py").write_text("from codontrace.genesis._private import X", encoding="utf-8")
    assert not audit_examples(tmp_path)["passed"]
