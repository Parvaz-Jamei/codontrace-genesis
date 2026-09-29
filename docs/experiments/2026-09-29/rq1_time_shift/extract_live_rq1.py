"""Compressed extract of raw/live_run.json gate evidence."""
from __future__ import annotations

import json
from pathlib import Path

OUT = Path(__file__).resolve().parent
rep = json.loads((OUT / "raw" / "live_run.json").read_text(encoding="utf-8"))
lines = []
lines.append(f"wall_s={rep.get('wall_s')} seeds={len(rep.get('seeds', []))}")
lines.append(f"calibration_gate_failed_at_seed={rep.get('calibration_gate_failed_at_seed')}")
for rec in rep.get("seeds", []):
    lines.append(
        f"seed={rec.get('seed')} phase={rec.get('phase')} skipped={rec.get('skipped')} "
        f"arm_match0={rec.get('arm_match_at_generation_0')}"
    )
    for k, v in (rec.get("arm_initial_state") or {}).items() if isinstance(rec.get("arm_initial_state"), dict) else []:
        lines.append(f"  init {k}={v}")
    ias = rec.get("arm_initial_state")
    if isinstance(ias, list):
        for item in ias:
            lines.append(f"  init {item}")
    for name, arm in (rec.get("arms") or {}).items():
        diag = arm.get("slot_diagnostics", {})
        lines.append(
            f"  arm={name} label={arm.get('label')} supports={arm.get('supports')} "
            f"i_c={arm.get('contrast_population', {}).get('i_contemp')} "
            f"i_l={arm.get('contrast_population', {}).get('i_lag')} "
            f"imax={arm.get('contrast_population', {}).get('i_max')}"
        )
        for slot, d in diag.items():
            lines.append(
                f"    {slot}: census={d['census']} para_n={d['parasite_n']} "
                f"host_cls={d['host_classes']} ant_cls={d['antagonist_classes']} "
                f"rich={d['host_richness']} dom={d['dominant_host']}"
            )
    for err in rec.get("errors", []):
        lines.append(f"  ERROR {err}")
text = "\n".join(lines)
(OUT / "logs" / "live_extract.txt").write_text(text + "\n", encoding="utf-8")
print(text[:3000])
