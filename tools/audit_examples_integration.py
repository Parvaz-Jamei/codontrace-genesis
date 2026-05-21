#!/usr/bin/env python3
from __future__ import annotations
from pathlib import Path
import json, re, sys

def audit(root: str | Path = ".") -> dict:
    base = Path(root)
    issues=[]
    for p in (base/"examples").glob("*.py"):
        text=p.read_text(encoding="utf-8")
        rel=str(p.relative_to(base)).replace("\\","/")
        if "from codontrace.genesis._" in text or "import codontrace.genesis._" in text:
            issues.append({"path":rel,"label":"private_import"})
        if re.search(r"claim_gate_decision_digest\s*=\s*['\"]fake|not_run:.*claim", text):
            issues.append({"path":rel,"label":"fake_positive_claim"})
        if "--out" not in text and "argparse" in text and rel.startswith("examples/genesis_integration"):
            issues.append({"path":rel,"label":"missing_out_argument"})
    return {"schema_version":"integration_examples_audit_v1","passed":not issues,"issues":issues}

def main(argv=None):
    result=audit(argv[0] if argv else ".")
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["passed"] else 1
if __name__ == "__main__": raise SystemExit(main())
