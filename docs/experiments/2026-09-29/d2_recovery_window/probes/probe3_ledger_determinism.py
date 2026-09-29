"""D-2 probe 3: is the ledger operation layer byte-reproducible?

Pure ledger (no engine), so it is cheap. Prints one digest per arm; the caller
runs it in two separate processes and with a pinned PYTHONHASHSEED to see
whether arm choice depends on process hash order.
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
from typing import Any

sys.path.insert(0, r"E:\مقاله پزشکی شبیه سازی ویروس\codontrace-genesis\src")

from codontrace.genesis.campaigns.discovery_q_20260928_idea4 import (
    RECOVERY_TOKEN_KEY,
    SCAFFOLD_ID,
    _apply_ops_cell,
    harvest_rare_class_yield,
)
from codontrace.life_loop.contact_atp_ledger import build_engine_scaffold_ledger

SEED = 301
ARMS = ("control", "scramble_contacts", "cut_named_scaffold", "cut_matched_random", "ablate_knowledge_digest")

out: dict[str, Any] = {
    "pythonhashseed": os.environ.get("PYTHONHASHSEED", "<unset>"),
    "seed": SEED,
    "arms": {},
}


def _h(payload: Any) -> str:
    return hashlib.sha256(json.dumps(payload, sort_keys=True, default=str).encode()).hexdigest()[:32]


for arm in ARMS:
    ledger = build_engine_scaffold_ledger(seed=SEED)
    before_digest = ledger.digest()
    ckpt = ledger.relocate_recovery_token(RECOVERY_TOKEN_KEY, remove=False, new_payload="relocated_engine")
    cell = _apply_ops_cell(ledger, arm) if arm != "control" else {"op": "control"}
    detail: dict[str, Any] = {
        "op": cell.get("op"),
        "cut_edge_ids": cell.get("cut_edge_ids"),
        "rewired": cell.get("rewired"),
        "n_edges_cut": cell.get("n_edges_cut"),
        "degree_sum": cell.get("degree_sum"),
        "atp_lost": cell.get("atp_lost"),
        "match_exact": cell.get("match_exact"),
        "used_nearest_fallback": cell.get("used_nearest_fallback"),
        "design_failure": cell.get("design_failure"),
        "independent_control": cell.get("independent_control"),
        "scientific_contrast_eligible": cell.get("scientific_contrast_eligible"),
        "n_edges_present_after": sum(1 for e in ledger.edges.values() if e.present),
        "n_edges_total": len(ledger.edges),
    }
    # Step the pure ledger forward a few boundaries exactly as the observer does.
    for _ in range(5):
        ledger.advance_generation()
    out["arms"][arm] = {
        "before_digest": before_digest,
        "ckpt_after": ckpt.get("after"),
        "detail": detail,
        "rare_yield": round(float(harvest_rare_class_yield(ledger)), 9),
        "ledger_digest": ledger.digest(),
        "detail_hash": _h(detail),
    }

print(json.dumps(out, indent=2, sort_keys=True, default=str))
