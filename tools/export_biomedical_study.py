"""Write docs/claimgate/biomedical_study.json from the live study audit."""

from __future__ import annotations

import json
from pathlib import Path

from codontrace.claimgate.adapters.biomedical import biomedical_study_payload

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "claimgate" / "biomedical_study.json"


def main() -> None:
    payload = biomedical_study_payload()
    OUT.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(OUT)
    print(payload["digest"])


if __name__ == "__main__":
    main()
