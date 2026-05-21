#!/usr/bin/env python3
from __future__ import annotations
import json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from codontrace.genesis.runtime_wiring_audit import audit_runtime_wiring

def main(argv=None) -> int:
    result = audit_runtime_wiring()
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["passed"] else 1
if __name__ == "__main__":
    raise SystemExit(main())
