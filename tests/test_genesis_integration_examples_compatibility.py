from pathlib import Path
from tools.audit_examples_integration import audit


def test_examples_audit_passes_current_tree():
    result = audit(Path("."))
    assert result["passed"], result["issues"]


def test_integration_example_declares_out_and_negative_outputs():
    text = Path("examples/genesis_integration_end_to_end_validation.py").read_text(encoding="utf-8")
    assert "--out" in text
    assert "integration_negative_results.json" in text
    assert "integration_final_claim_manifest.json" in text
