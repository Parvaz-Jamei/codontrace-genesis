#!/usr/bin/env python3
"""ILW-5 confirmatory partial campaign (requires pilot artifact gates PASS).

Runs a meaningful held-out subset and checkpoints outputs/ilw5_campaign_partial.json
after each newly completed cell. Does not invent outcomes or raise ClaimGate.
"""

from __future__ import annotations

import argparse
import json
import sys


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--max-cells",
        type=int,
        default=None,
        help="Stop after this many newly executed cells (resume-friendly).",
    )
    parser.add_argument(
        "--ablation-seeds",
        type=int,
        nargs="+",
        default=[4100, 4101],
        help="Held-out seeds for full 8-arm ablation (default: 4100 4101).",
    )
    parser.add_argument(
        "--interaction-seeds",
        type=int,
        nargs="*",
        default=[4100],
        help="Seeds for interaction screening cells (default: 4100).",
    )
    parser.add_argument(
        "--s4-seeds",
        type=int,
        nargs="*",
        default=[4100],
        help="Seeds for small S4 scale slice (default: 4100).",
    )
    parser.add_argument(
        "--s4-widths",
        type=int,
        nargs="+",
        default=[32, 64],
        help="S4 widths for the small slice.",
    )
    parser.add_argument(
        "--s4-horizons",
        type=int,
        nargs="+",
        default=[128],
        help="S4 tick horizons for the small slice.",
    )
    parser.add_argument(
        "--s4-pop-caps",
        type=int,
        nargs="+",
        default=[64],
        help="S4 population caps for the small slice.",
    )
    parser.add_argument(
        "--run-replay",
        action="store_true",
        help="Enable digest replay (roughly 2× wall clock).",
    )
    parser.add_argument(
        "--no-resume",
        action="store_true",
        help="Ignore existing partial artifact and re-run from scratch.",
    )
    args = parser.parse_args(argv)

    from codontrace.genesis.ilw.campaign import run_ilw5_partial

    payload = run_ilw5_partial(
        max_cells=args.max_cells,
        ablation_seeds=tuple(args.ablation_seeds),
        interaction_seeds=tuple(args.interaction_seeds),
        s4_seeds=tuple(args.s4_seeds),
        s4_widths=tuple(args.s4_widths),
        s4_horizons=tuple(args.s4_horizons),
        s4_pop_caps=tuple(args.s4_pop_caps),
        run_replay=bool(args.run_replay),
        resume=not args.no_resume,
        write_artifact=True,
    )
    print(
        json.dumps(
            {
                "status": payload["status"],
                "claim_ceiling": payload["claim_ceiling"],
                "executed_count": payload["executed_count"],
                "planned_count": payload["planned_count"],
                "enumerated_total": payload["enumerated_total"],
                "newly_run_this_invocation": payload["newly_run_this_invocation"],
                "executed_by_kind": payload["executed_by_kind"],
                "executed_ids": [c["cell"]["cell_id"] for c in payload["executed_cells"]],
                "remaining_planned": payload["remaining_planned_cell_ids"],
                "campaign_outcomes_invented": payload["campaign_outcomes_invented"],
                "intelligence_claimed": payload["intelligence_claimed"],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
