from pathlib import Path
from tools.audit_package_hygiene import audit


def test_package_hygiene_accepts_clean_tree(tmp_path):
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "ok.py").write_text("x=1", encoding="utf-8")
    assert audit(tmp_path)["passed"]


def test_package_hygiene_rejects_pycache(tmp_path):
    bad = tmp_path / "src" / "__pycache__"
    bad.mkdir(parents=True)
    (bad / "x.pyc").write_bytes(b"bad")
    result = audit(tmp_path)
    assert not result["passed"]
    assert result["bad_paths"]
