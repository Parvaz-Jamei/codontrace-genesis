#!/usr/bin/env python3
from __future__ import annotations
from pathlib import Path
import fnmatch, json, re, sys

DEFAULT_SCAN = ("src/codontrace", "tests", "examples", "docs", "README.md", "RELEASE_EVIDENCE.md")
DEFAULT_FORBIDDEN = {
    "old_result_object": r"OldGenesisRunResult|LegacyGenesisResult",
    "old_artifact_key": r"phase3_fake_|placeholder_claim_ready",
    "positive_not_run": r"claim_(ready|eligible|supported)\s*[=:]\s*True.*not_run:",
    "fake_lineage_path": r"fake lineage path|fake_lineage_path",
}

def _load_allowlist(path: Path) -> dict:
    if not path.exists():
        return {"paths": [], "patterns": []}
    return json.loads(path.read_text(encoding="utf-8"))

def _allowed(rel: str, label: str, allow: dict) -> bool:
    for item in allow.get("paths", []):
        if fnmatch.fnmatch(rel, item):
            return True
    for item in allow.get("patterns", []):
        if item.get("label") == label and fnmatch.fnmatch(rel, item.get("path", "")):
            return True
    return False

def audit(root: str | Path = ".", allowlist: str | Path = "tools/audit_allowlist_integration.json") -> dict:
    base = Path(root)
    allow = _load_allowlist(base / allowlist)
    issues = []
    for target in DEFAULT_SCAN:
        p = base / target
        if not p.exists():
            continue
        files = [p] if p.is_file() else [x for x in p.rglob("*") if x.is_file() and x.suffix.lower() in {".py", ".md", ".json", ".toml", ".txt"}]
        for file in files:
            rel = str(file.relative_to(base)).replace("\\", "/")
            if _allowed(rel, "file", allow):
                continue
            try:
                text = file.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                continue
            for label, pattern in DEFAULT_FORBIDDEN.items():
                if re.search(pattern, text, flags=re.IGNORECASE | re.DOTALL) and not _allowed(rel, label, allow):
                    issues.append({"path": rel, "label": label})
            if rel.startswith("examples/") and "from codontrace.genesis._" in text and not _allowed(rel, "private_example_import", allow):
                issues.append({"path": rel, "label": "private_example_import"})
    return {"schema_version":"integration_reference_audit_v1", "passed": not issues, "issues": issues}

def main(argv=None) -> int:
    argv = argv or sys.argv[1:]
    result = audit(argv[0] if argv else ".")
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["passed"] else 1
if __name__ == "__main__":
    raise SystemExit(main())
