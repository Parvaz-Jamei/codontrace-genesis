from __future__ import annotations

import json
from pathlib import Path

OUT = Path(__file__).resolve().parent
d = json.loads((OUT / "analysis_live.json").read_text(encoding="utf-8"))
s = d["summary"]
lines = [f"integrity={json.dumps(s.get('integrity'))}"]
for name, e in s["arms"].items():
    lines.append(
        f"{name}: n={e['n_seeds']} labels={e['labels']} n_support={e['n_support']} "
        f"i_c_mean={e['i_contemp_mean']} i_l_mean={e['i_lag_mean']}"
    )
    for k in ("i_contemp_interval", "i_lag_interval"):
        if k in e:
            v = e[k]
            lines.append(
                f"   {k}: point={v['point']:.6f} lo={v['lo']:.6f} hi={v['hi']:.6f} "
                f"excl0={v['excludes_zero']} n_runs={v['n_runs']}"
            )
lines.append(f"rotation={json.dumps(s['rotation_control'])}")
lines.append(f"decision={json.dumps(d['decision'])}")
lines.append(f"flags={json.dumps(d['flags'])}")
for r in d["per_seed"]:
    co = r["arms"].get("copassaged", {})
    lines.append(
        f"seed={r['seed']} phase={r['phase']} co_label={co.get('label')} "
        f"co_supports={co.get('supports')} i_c={co.get('contrast', {}).get('i_contemp')} "
        f"i_l={co.get('contrast', {}).get('i_lag')} imax={co.get('contrast', {}).get('i_max_cell')}"
    )
text = "\n".join(lines)
(OUT / "logs" / "live_analysis_extract.txt").write_text(text + "\n", encoding="utf-8")
print(text)
