#!/bin/bash
set -e

PY=/home/parvaz/projects/ai-lab/.venv/bin/python
SCRIPT=/home/parvaz/custom_tests/grand_frontier_suite_extension.py
RUNS_DIR=/home/parvaz/simulation_runs

NOW=$(date +%s)

# Challenge 5: Functional Information Accretion & Wagner Neutral Network Percolation
C5_DIR="$RUNS_DIR/run_challenge_5_functional_info_72h"
mkdir -p "$C5_DIR"
rm -f "$C5_DIR/STOP" "$C5_DIR/run.pid"
> "$C5_DIR/live.log"
cat << EOF5 > "$C5_DIR/status.json"
{
  "schemaVersion": 1,
  "runId": "run_challenge_5_functional_info_72h",
  "title": "Challenge 5: Functional Info & Neutral Percolation (Hazen/Adami/Wagner, 72h)",
  "status": "RUNNING",
  "startedAt": $NOW,
  "pct": 0.0,
  "completedSeeds": 0,
  "totalSeeds": 1,
  "workerId": 4,
  "core": 0,
  "targetHours": 72.0,
  "generations": 500000000,
  "params": {"challenge": 5, "duration_hours": 72.0, "core": 0, "track": "extension"}
}
EOF5
cat << EOF5M > "$C5_DIR/run_manifest.json"
{
  "schemaVersion": 1,
  "runId": "run_challenge_5_functional_info_72h",
  "title": "Challenge 5: Functional Info & Neutral Percolation (Hazen/Adami/Wagner, 72h)",
  "startedAt": $NOW,
  "command": ["taskset", "-c", "0", "$PY", "$SCRIPT", "--challenge", "5", "--duration-hours", "72.0", "--output", "$C5_DIR", "--core", "0"],
  "params": {"challenge": 5, "duration_hours": 72.0, "core": 0}
}
EOF5M
nohup taskset -c 0 $PY $SCRIPT --challenge 5 --duration-hours 72.0 --output "$C5_DIR" --core 0 > "$C5_DIR/console.log" 2>&1 &
echo $! > "$C5_DIR/run.pid"

# Challenge 6: Eigen's Error Catastrophe & Quasispecies Critical Threshold
C6_DIR="$RUNS_DIR/run_challenge_6_quasispecies_72h"
mkdir -p "$C6_DIR"
rm -f "$C6_DIR/STOP" "$C6_DIR/run.pid"
> "$C6_DIR/live.log"
cat << EOF6 > "$C6_DIR/status.json"
{
  "schemaVersion": 1,
  "runId": "run_challenge_6_quasispecies_72h",
  "title": "Challenge 6: Eigen Error Catastrophe & Quasispecies (Eigen/Nowak/Wilke, 72h)",
  "status": "RUNNING",
  "startedAt": $NOW,
  "pct": 0.0,
  "completedSeeds": 0,
  "totalSeeds": 1,
  "workerId": 5,
  "core": 1,
  "targetHours": 72.0,
  "generations": 500000000,
  "params": {"challenge": 6, "duration_hours": 72.0, "core": 1, "track": "extension"}
}
EOF6
cat << EOF6M > "$C6_DIR/run_manifest.json"
{
  "schemaVersion": 1,
  "runId": "run_challenge_6_quasispecies_72h",
  "title": "Challenge 6: Eigen Error Catastrophe & Quasispecies (Eigen/Nowak/Wilke, 72h)",
  "startedAt": $NOW,
  "command": ["taskset", "-c", "1", "$PY", "$SCRIPT", "--challenge", "6", "--duration-hours", "72.0", "--output", "$C6_DIR", "--core", "1"],
  "params": {"challenge": 6, "duration_hours": 72.0, "core": 1}
}
EOF6M
nohup taskset -c 1 $PY $SCRIPT --challenge 6 --duration-hours 72.0 --output "$C6_DIR" --core 1 > "$C6_DIR/console.log" 2>&1 &
echo $! > "$C6_DIR/run.pid"

# Challenge 7: Open-Ended Evolutionary Activity vs Neutral Shadow
C7_DIR="$RUNS_DIR/run_challenge_7_oee_shadow_72h"
mkdir -p "$C7_DIR"
rm -f "$C7_DIR/STOP" "$C7_DIR/run.pid"
> "$C7_DIR/live.log"
cat << EOF7 > "$C7_DIR/status.json"
{
  "schemaVersion": 1,
  "runId": "run_challenge_7_oee_shadow_72h",
  "title": "Challenge 7: Open-Ended Evolutionary Activity vs Neutral Shadow (Bedau/Taylor, 72h)",
  "status": "RUNNING",
  "startedAt": $NOW,
  "pct": 0.0,
  "completedSeeds": 0,
  "totalSeeds": 1,
  "workerId": 6,
  "core": 2,
  "targetHours": 72.0,
  "generations": 500000000,
  "params": {"challenge": 7, "duration_hours": 72.0, "core": 2, "track": "extension"}
}
EOF7
cat << EOF7M > "$C7_DIR/run_manifest.json"
{
  "schemaVersion": 1,
  "runId": "run_challenge_7_oee_shadow_72h",
  "title": "Challenge 7: Open-Ended Evolutionary Activity vs Neutral Shadow (Bedau/Taylor, 72h)",
  "startedAt": $NOW,
  "command": ["taskset", "-c", "2", "$PY", "$SCRIPT", "--challenge", "7", "--duration-hours", "72.0", "--output", "$C7_DIR", "--core", "2"],
  "params": {"challenge": 7, "duration_hours": 72.0, "core": 2}
}
EOF7M
nohup taskset -c 2 $PY $SCRIPT --challenge 7 --duration-hours 72.0 --output "$C7_DIR" --core 2 > "$C7_DIR/console.log" 2>&1 &
echo $! > "$C7_DIR/run.pid"

# Challenge 8: Fisher's Geometric Model & Distribution of Fitness Effects (DFE)
C8_DIR="$RUNS_DIR/run_challenge_8_fisher_geometric_72h"
mkdir -p "$C8_DIR"
rm -f "$C8_DIR/STOP" "$C8_DIR/run.pid"
> "$C8_DIR/live.log"
cat << EOF8 > "$C8_DIR/status.json"
{
  "schemaVersion": 1,
  "runId": "run_challenge_8_fisher_geometric_72h",
  "title": "Challenge 8: Fisher Geometric Model & DFE (Fisher/Orr/Tenaillon, 72h)",
  "status": "RUNNING",
  "startedAt": $NOW,
  "pct": 0.0,
  "completedSeeds": 0,
  "totalSeeds": 1,
  "workerId": 7,
  "core": 3,
  "targetHours": 72.0,
  "generations": 500000000,
  "params": {"challenge": 8, "duration_hours": 72.0, "core": 3, "track": "extension"}
}
EOF8
cat << EOF8M > "$C8_DIR/run_manifest.json"
{
  "schemaVersion": 1,
  "runId": "run_challenge_8_fisher_geometric_72h",
  "title": "Challenge 8: Fisher Geometric Model & DFE (Fisher/Orr/Tenaillon, 72h)",
  "startedAt": $NOW,
  "command": ["taskset", "-c", "3", "$PY", "$SCRIPT", "--challenge", "8", "--duration-hours", "72.0", "--output", "$C8_DIR", "--core", "3"],
  "params": {"challenge": 8, "duration_hours": 72.0, "core": 3}
}
EOF8M
nohup taskset -c 3 $PY $SCRIPT --challenge 8 --duration-hours 72.0 --output "$C8_DIR" --core 3 > "$C8_DIR/console.log" 2>&1 &
echo $! > "$C8_DIR/run.pid"

echo "ALL_EXTENSION_CHALLENGES_LAUNCHED_OK"
