"""Honest T01–T12 readiness. A class or a config field is not a connection."""

from __future__ import annotations

from typing import Any

SCHEMA_VERSION = 1

STATUSES = (
    "طرح",
    "در حال پیاده‌سازی",
    "نیازمند اتصال",
    "آمادهٔ پایلوت",
    "آمادهٔ کمپین",
)

# Assessment words for a new campaign. They are not aliases of the 29 September ledger.
ASSESSMENT_WORDS = (
    "SUPPORTED_IN_THIS_MODEL",
    "NOT_SUPPORTED",
    "INCONCLUSIVE",
    "INVALID_MEASUREMENT",
    "UNASSESSED",
)

LEDGER_WORDS = (
    "SUPPORTED_IN_MODEL",
    "FALSIFIED_IN_MODEL",
    "INCONCLUSIVE",
    "BLOCKED_MEASUREMENT",
)


def assessments_are_distinct(left: str, right: str) -> bool:
    """Lack of support, uncertainty, and rejection of a prediction are different."""

    return left != right


EXPERIMENTS: tuple[dict[str, Any], ...] = (
    {
        "experiment_id": "T01",
        "backend": "ENGINE",
        "runner": None,
        "features": ["ecological selection", "quality-diversity archive", "held-out phenotype"],
        "runtime_consumer": None,
        "data_path": None,
        "controls": None,
        "measure": "held-out functional-phenotype AUC",
        "analyst": "scripts/board_campaign_analyst.py",
        "status": "نیازمند اتصال",
        "run_enabled": False,
        "evidence": "scripts/grand_frontier_4challenge_campaign.py is a REFERENCE model. Its _match_count is not consumed by selection.",
        "owner": "Coder 1",
        "gap": "No engine path consumes a functional phenotype for this question.",
    },
    {
        "experiment_id": "T02",
        "backend": "ENGINE",
        "runner": None,
        "features": ["demes", "real offspring counts", "Price partition"],
        "runtime_consumer": None,
        "data_path": None,
        "controls": None,
        "measure": "functional cooperation, last 500 generations",
        "analyst": "scripts/board_campaign_analyst.py",
        "status": "نیازمند اتصال",
        "run_enabled": False,
        "evidence": "codontrace.genesis.phase_j.PriceEquationPartition exists. It is not wired to deme reproduction for T02.",
        "owner": "Coder 1",
        "gap": "The Price partition does not account this experiment's births.",
    },
    {
        "experiment_id": "T03",
        "backend": "INTEGRATED",
        "runner": None,
        "features": ["vertical transmission", "collective reproduction", "partner assay"],
        "runtime_consumer": None,
        "data_path": None,
        "controls": None,
        "measure": "mutual-benefit partnership surviving to the horizon",
        "analyst": "scripts/board_campaign_analyst.py",
        "status": "نیازمند اتصال",
        "run_enabled": False,
        "evidence": "The four-challenge transition arm is a REFERENCE formula, not an engine attachment.",
        "owner": "Coder 2",
        "gap": "No recorded exchange between a mutualism submodel and GenesisEngine.",
    },
    {
        "experiment_id": "T04",
        "backend": "ENGINE",
        "runner": None,
        "features": ["fork", "held-out function", "founder-clustered replay"],
        "runtime_consumer": None,
        "data_path": None,
        "controls": None,
        "measure": "probability of the locked held-out function",
        "analyst": "scripts/board_campaign_analyst.py",
        "status": "نیازمند اتصال",
        "run_enabled": False,
        "evidence": "GenesisEngine.capture_fork is real. The contingency protocol that uses it is not.",
        "owner": "Coder 3",
        "gap": "A checkpoint is not the historical-contingency experiment.",
    },
    {
        "experiment_id": "T05",
        "backend": "ENGINE",
        "runner": None,
        "features": ["host-parasite contacts", "time-shift assay"],
        "runtime_consumer": None,
        "data_path": None,
        "controls": None,
        "measure": "paired two-sided temporal contrast",
        "analyst": "scripts/board_campaign_analyst.py",
        "status": "نیازمند اتصال",
        "run_enabled": False,
        "evidence": "scripts/rq_full_engine_parallel.py runs phase-5 histories. That protocol is not the locked T05 design.",
        "owner": "Coder 2",
        "gap": "Do not relabel the phase-5 script as T05.",
    },
    {
        "experiment_id": "T06",
        "backend": "ENGINE",
        "runner": None,
        "features": ["ledger consumed by an action"],
        "runtime_consumer": None,
        "data_path": None,
        "controls": None,
        "measure": "held-out success against a matched ablation",
        "analyst": "scripts/board_campaign_analyst.py",
        "status": "نیازمند اتصال",
        "run_enabled": False,
        "evidence": "Causal-graph config can be present while unused. Presence is not consumption.",
        "owner": "Coder 3",
        "gap": "No runner shows ledger change changing the chosen action.",
    },
    {
        "experiment_id": "T07",
        "backend": "ENGINE",
        "runner": None,
        "features": ["capsule transfer", "held-out task"],
        "runtime_consumer": None,
        "data_path": None,
        "controls": None,
        "measure": "evaluations until the locked criterion",
        "analyst": "scripts/board_campaign_analyst.py",
        "status": "نیازمند اتصال",
        "run_enabled": False,
        "evidence": "Capsule config exists. No T07 runner shows the capsule contents changing a later action.",
        "owner": "Coder 3",
        "gap": "Transfer is not connected to a held-out task.",
    },
    {
        "experiment_id": "T08",
        "backend": "ENGINE",
        "runner": None,
        "features": ["macro expansion", "ATP account"],
        "runtime_consumer": None,
        "data_path": None,
        "controls": None,
        "measure": "held-out success per real ATP",
        "analyst": "scripts/board_campaign_analyst.py",
        "status": "نیازمند اتصال",
        "run_enabled": False,
        "evidence": "ADF types exist. No T08 runner compares them with an equivalent primitive sequence.",
        "owner": "Coder 3",
        "gap": "Skill compression is not connected to an energy-matched assay.",
    },
    {
        "experiment_id": "T09",
        "backend": "ENGINE",
        "runner": None,
        "features": ["defined reference space", "independent sampler"],
        "runtime_consumer": None,
        "data_path": None,
        "controls": None,
        "measure": "functional information in one fixed space",
        "analyst": "scripts/board_campaign_analyst.py",
        "status": "نیازمند اتصال",
        "run_enabled": False,
        "evidence": "The console evaluator names a Hazen protocol. It does not draw the locked reference sample.",
        "owner": "Coder 4",
        "gap": "No sampler writes the successes this measure needs.",
    },
    {
        "experiment_id": "T10",
        "backend": "ENGINE",
        "runner": None,
        "features": ["resource shock", "recovery assay"],
        "runtime_consumer": None,
        "data_path": None,
        "controls": None,
        "measure": "area of the functional drop after the first shock",
        "analyst": "scripts/board_campaign_analyst.py",
        "status": "نیازمند اتصال",
        "run_enabled": False,
        "evidence": "The life-loop has resources. It has no locked two-shock schedule for this question.",
        "owner": "Coder 2",
        "gap": "Ecology in the preset is not the shock experiment.",
    },
    {
        "experiment_id": "T11",
        "backend": "ENGINE",
        "runner": "scripts/board_long_campaign.py",
        "features": ["life-loop preset", "capture_fork", "from_fork"],
        "runtime_consumer": "GenesisEngine.run_ticks",
        "data_path": "runs/T11/seed_<n>/arm_<arm>/",
        "controls": "checkpoint hash and equal horizon",
        "measure": "state digest after the same tick count, uninterrupted against resume",
        "analyst": "scripts/board_campaign_analyst.py",
        "status": "آمادهٔ پایلوت",
        "run_enabled": False,
        "evidence": "A calibration pilot can run. The 72-hour, three-workload endurance campaign cannot.",
        "owner": "Coder 4",
        "gap": "Board rate is unmeasured. UI pressure, multi-day memory, and a second architecture are not in this pilot.",
        "pilot_command": "python scripts/board_long_campaign.py run --experiment T11 --seed 7 --arm uninterrupted --ticks 4 --population 6 --workers 1 --output <dir>",
        "resume_command": "python scripts/board_long_campaign.py resume --experiment T11 --seed 7 --ticks 4 --population 6 --checkpoint <dir>/runs/T11/seed_7/arm_uninterrupted/checkpoints/mid.bin --output <dir>",
    },
    {
        "experiment_id": "T12",
        "backend": "ENGINE",
        "runner": None,
        "features": ["resource collection", "sensor failure", "simple baseline"],
        "runtime_consumer": None,
        "data_path": None,
        "controls": None,
        "measure": "resources delivered on held-out episodes",
        "analyst": "scripts/board_campaign_analyst.py",
        "status": "طرح",
        "run_enabled": False,
        "evidence": "SimEsp32Bridge remains a stub. A stub is not hardware-in-the-loop.",
        "owner": "Coder 4",
        "gap": "The swarm task and its baseline are not implemented.",
    },
)


def inventory() -> dict[str, Any]:
    rows = []
    for row in EXPERIMENTS:
        item = dict(row)
        item["schema_version"] = SCHEMA_VERSION
        item["long_campaign_ready"] = item["status"] == "آمادهٔ کمپین"
        rows.append(item)
    return {
        "schema_version": SCHEMA_VERSION,
        "basis_sha": "e90f9cd1d7287d2b51531cae82cd75dc0a18b2f1",
        "program": "docs/campaigns/orange_pi_zero3_long_program.md",
        "board_rate_measured": False,
        "experiments": rows,
    }


def experiment(experiment_id: str) -> dict[str, Any]:
    for row in inventory()["experiments"]:
        if row["experiment_id"] == experiment_id:
            return row
    msg = f"unknown experiment {experiment_id}"
    raise KeyError(msg)


def render_readiness_markdown() -> str:
    lines = [
        "# T01–T12 readiness",
        "",
        "Basis: `e90f9cd1d7287d2b51531cae82cd75dc0a18b2f1`. This table is not a result.",
        "A config field or a class is not a connection. `run_enabled` is false until that experiment's long-campaign preconditions pass.",
        "The Orange Pi rate has not been measured.",
        "",
        "| ID | Backend | Status | Runner | Consumer | Owner | Gap |",
        "|---|---|---|---|---|---|---|",
    ]
    for row in inventory()["experiments"]:
        runner = row["runner"] or "—"
        consumer = row["runtime_consumer"] or "—"
        lines.append(
            f"| {row['experiment_id']} | {row['backend']} | {row['status']} | `{runner}` | {consumer} | {row['owner']} | {row['gap']} |"
        )
    lines.extend(
        [
            "",
            "## Commands that exist",
            "",
            "```bash",
            "python scripts/board_long_campaign.py inventory",
            "python scripts/board_long_campaign.py run --experiment T11 --seed 7 --arm uninterrupted --ticks 4 --population 6 --workers 1 --output <dir>",
            "python scripts/board_long_campaign.py resume --experiment T11 --seed 7 --ticks 4 --population 6 --checkpoint <dir>/runs/T11/seed_7/arm_uninterrupted/checkpoints/mid.bin --output <dir>",
            "python scripts/board_campaign_analyst.py --campaign <dir>",
            "```",
            "",
            "T11's pilot uses `GenesisRuntimeProfile.life_loop_world` and `GenesisEngine.capture_fork` / `from_fork`. It does not answer T01–T10 or T12. It does not measure the board.",
            "",
            "## Board plan",
            "",
            "On the Orange Pi Zero 3, with the RAM and cooling that will actually be used, run the T11 calibration for 60 to 120 minutes and record seconds per generation, RSS, temperature, and throttling. Do not multiply a single-core time by a hoped-for worker count. The long horizon stays locked only after that measurement. This file does not contain that measurement.",
            "",
        ]
    )
    return "\n".join(lines)
