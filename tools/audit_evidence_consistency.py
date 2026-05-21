#!/usr/bin/env python3
from __future__ import annotations
import json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from codontrace.genesis.evidence_consistency import audit_result_evidence_consistency
from codontrace.genesis.runtime_wiring_audit import integration_feature_catalog

def main(argv=None) -> int:
    required = tuple(f.record_class_path for f in integration_feature_catalog())
    result = audit_result_evidence_consistency(required_class_paths=required)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["passed"] else 1
if __name__ == "__main__":
    raise SystemExit(main())
