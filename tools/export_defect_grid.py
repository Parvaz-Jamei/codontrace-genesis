"""Write docs/claimgate/defect_grid.json from the live auditor."""

from __future__ import annotations

import json
from pathlib import Path

from codontrace.claimgate.defect_grid import defect_grid_payload

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "claimgate" / "defect_grid.json"


def main() -> None:
    payload = defect_grid_payload()
    OUT.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(OUT)
    print(payload["n_escaped"], "/", payload["n_defects"], payload["digest"])


if __name__ == "__main__":
    main()
