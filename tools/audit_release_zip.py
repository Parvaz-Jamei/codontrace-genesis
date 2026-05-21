#!/usr/bin/env python3
from __future__ import annotations
import json, sys, zipfile
BAD = ("__pycache__", ".pytest_cache", ".phase3_", ".ipynb_checkpoints")
BAD_SUFFIX = (".pyc", ".pyo")

def audit(zip_path: str) -> dict:
    with zipfile.ZipFile(zip_path) as z:
        names=z.namelist()
    bad=[n for n in names if any(tok in n for tok in BAD) or n.endswith(BAD_SUFFIX) or n.endswith(".DS_Store")]
    required=["pyproject.toml", "src/codontrace/__init__.py", "src/codontrace/genesis/__init__.py", "tests", "examples"]
    missing=[]
    for req in required:
        if req == "tests" or req == "examples":
            if not any(n.startswith(req+"/") for n in names): missing.append(req)
        elif req not in names: missing.append(req)
    return {"schema_version":"integration_release_zip_audit_v1", "passed": not bad and not missing, "bad_paths":bad, "missing":missing, "file_count":len(names)}

def main(argv=None):
    argv=argv or sys.argv[1:]
    if not argv: print("usage: audit_release_zip.py <zip>", file=sys.stderr); return 2
    result=audit(argv[0]); print(json.dumps(result, indent=2, sort_keys=True)); return 0 if result["passed"] else 1
if __name__ == "__main__": raise SystemExit(main())
