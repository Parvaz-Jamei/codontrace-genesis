#!/usr/bin/env python3
from __future__ import annotations
from pathlib import Path
import json
import sys

BAD_DIR_TOKENS = {"__pycache__", ".pytest_cache", ".phase3_", ".ipynb_checkpoints"}
BAD_SUFFIXES = {".pyc", ".pyo"}
BAD_NAMES = {".DS_Store"}

def audit(root: str | Path = ".") -> dict:
    base = Path(root)
    bad = []
    for p in base.rglob("*"):
        s = str(p).replace("\\", "/")
        if any(tok in s for tok in BAD_DIR_TOKENS) or p.suffix in BAD_SUFFIXES or p.name in BAD_NAMES:
            bad.append(s)
    return {"schema_version":"integration_package_hygiene_v1", "passed": not bad, "bad_paths": sorted(bad)}

def main(argv=None) -> int:
    argv = argv or sys.argv[1:]
    root = argv[0] if argv else "."
    result = audit(root)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["passed"] else 1
if __name__ == "__main__":
    raise SystemExit(main())
