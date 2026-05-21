import subprocess
import sys
from pathlib import Path
from tools.build_clean_release_zip import build
from tools.audit_release_zip import audit


def test_build_clean_release_zip_excludes_cache_files(tmp_path):
    root = tmp_path / "pkg"
    (root / "src/codontrace/genesis").mkdir(parents=True)
    (root / "tests").mkdir()
    (root / "examples").mkdir()
    (root / "tests" / "test_placeholder.py").write_text("def test_ok():\n    assert True\n", encoding="utf-8")
    (root / "examples" / "placeholder.py").write_text("print(\"ok\")\n", encoding="utf-8")
    (root / "pyproject.toml").write_text("[project]\nname='x'\nversion='0'\n", encoding="utf-8")
    (root / "src/codontrace/__init__.py").parent.mkdir(parents=True, exist_ok=True)
    (root / "src/codontrace/__init__.py").write_text("", encoding="utf-8")
    (root / "src/codontrace/genesis/__init__.py").write_text("", encoding="utf-8")
    bad = root / "src" / "__pycache__"
    bad.mkdir()
    (bad / "x.pyc").write_bytes(b"bad")
    zip_path = tmp_path / "out.zip"
    build(root, zip_path)
    out = audit(str(zip_path))
    assert out["passed"], out


def test_current_tree_release_zip_audit_passes(tmp_path):
    zip_path = tmp_path / "codontrace-integration.zip"
    subprocess.run([sys.executable, "tools/build_clean_release_zip.py", ".", str(zip_path)], check=True)
    out = audit(str(zip_path))
    assert out["passed"], out
