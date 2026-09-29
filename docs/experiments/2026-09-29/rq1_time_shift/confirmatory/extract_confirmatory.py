from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
RAW = HERE / "raw"
for path in sorted(RAW.glob("seed_*.json")):
    d = json.loads(path.read_text(encoding="utf-8"))
    print(f"== seed {d['seed']} wall={d['wall_s']} gates={d['seed_gates_ok']} frozen_zero={d['frozen_is_zero']} match0={d['arm_match_at_generation_0']}")
    for regime in ("copassaged", "fixed"):
        r = (d.get("regimes") or {}).get(regime)
        if not r:
            print(f"  {regime}: MISSING")
            continue
        m = r["matrix"]
        vals = [m[h][a] for h in ("past", "now", "future") for a in ("past", "now", "future")]
        print(f"  {regime}: label={r['label']} i_c={r['contrast']['i_contemp']} i_l={r['contrast']['i_lag']} "
              f"imax={r['contrast']['i_max']}@{r['contrast']['i_max_cell']} min={min(vals)} max={max(vals)}")
        print(f"    matrix={json.dumps(m)}")
        print(f"    rotations={json.dumps(r['rotation_labels'])}")
        print(f"    diag={json.dumps(r['slot_diagnostics'])}")
