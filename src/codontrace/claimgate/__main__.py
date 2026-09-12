"""CLI: ``python -m codontrace.claimgate audit bundle.json``."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from codontrace.claimgate.auditor import audit_bundle
from codontrace.claimgate.schema import ClaimgateBundle, parse_claimgate_bundle
from codontrace.errors import ConfigurationError


def _load_bundle(path: Path) -> ClaimgateBundle:
    if not path.is_file():
        raise ConfigurationError(f"bundle file not found: {path}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ConfigurationError("bundle JSON must be an object.")
    return parse_claimgate_bundle(payload)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m codontrace.claimgate",
        description=(
            "CodonTrace Genesis ClaimGate auditor. Grades claims given evidence. "
            "Does not grant OEE / Tokyo Type 1 or loosen forbidden aliases."
        ),
    )
    sub = parser.add_subparsers(dest="command", required=True)
    audit = sub.add_parser("audit", help="audit a claimgate_bundle_v1 JSON file")
    audit.add_argument("bundle", type=Path, help="path to bundle.json")
    args = parser.parse_args(argv)
    if args.command != "audit":
        parser.error("only the audit command is available")
    try:
        report = audit_bundle(_load_bundle(args.bundle))
    except (OSError, json.JSONDecodeError, ConfigurationError) as exc:
        print(f"claimgate-audit-error: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(report.to_dict(), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
