"""Write docs/claimgate/ladder_validation.json from the live auditor."""

from __future__ import annotations

import json
from pathlib import Path

from codontrace.claimgate.ladder_packs import ladder_validation_payload

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "claimgate" / "ladder_validation.json"


def main() -> None:
    payload = ladder_validation_payload()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(OUT)
    print(payload["digest"])


if __name__ == "__main__":
    main()
