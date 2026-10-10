# T01–T12 readiness

Basis: runtime-capability-registry-v2. This table is not a result.
run_enabled permits an explicitly scoped pilot, not a validated scientific campaign. T01–T05 are REFERENCE; T11 is ENGINE calibration; other stubs remain disabled.
The Orange Pi rate has not been measured.

| ID | Backend | Status | Runner | Consumer | Owner | Gap |
|---|---|---|---|---|---|---|
| T01 | REFERENCE | آمادهٔ پایلوت | `scripts/genesis_long_board_campaign.py` | codontrace.experiments (standalone reference model) | Coder 1 | A registered cross-seed scientific campaign and GenesisEngine adapter are separate from this REFERENCE pilot. |
| T02 | REFERENCE | آمادهٔ پایلوت | `scripts/genesis_long_board_campaign.py` | codontrace.experiments (standalone reference model) | Coder 1 | A registered cross-seed scientific campaign and GenesisEngine adapter are separate from this REFERENCE pilot. |
| T03 | REFERENCE | آمادهٔ پایلوت | `scripts/genesis_long_board_campaign.py` | codontrace.experiments (standalone reference model) | Coder 2 | A registered cross-seed scientific campaign and GenesisEngine adapter are separate from this REFERENCE pilot. |
| T04 | REFERENCE | آمادهٔ پایلوت | `scripts/genesis_long_board_campaign.py` | codontrace.experiments (standalone reference model) | Coder 3 | A registered cross-seed scientific campaign and GenesisEngine adapter are separate from this REFERENCE pilot. |
| T05 | REFERENCE | آمادهٔ پایلوت | `scripts/genesis_long_board_campaign.py` | codontrace.experiments (standalone reference model) | Coder 2 | A registered cross-seed scientific campaign and GenesisEngine adapter are separate from this REFERENCE pilot. |
| T06 | ENGINE | نیازمند اتصال | `scripts/genesis_long_board_campaign.py` | — | Coder 3 | No runner shows ledger change changing the chosen action. |
| T07 | ENGINE | نیازمند اتصال | `scripts/genesis_long_board_campaign.py` | — | Coder 3 | Transfer is not connected to a held-out task. |
| T08 | ENGINE | نیازمند اتصال | `scripts/genesis_long_board_campaign.py` | — | Coder 3 | Skill compression is not connected to an energy-matched assay. |
| T09 | ENGINE | نیازمند اتصال | `scripts/genesis_long_board_campaign.py` | — | Coder 4 | No sampler writes the successes this measure needs. |
| T10 | ENGINE | نیازمند اتصال | `scripts/genesis_long_board_campaign.py` | — | Coder 2 | Ecology in the preset is not the shock experiment. |
| T11 | ENGINE | آمادهٔ پایلوت | `scripts/board_long_campaign.py` | GenesisEngine.run_ticks | Coder 4 | Board rate is unmeasured. UI pressure, multi-day memory, and a second architecture are not in this pilot. |
| T12 | ENGINE | نیازمند اتصال | `scripts/genesis_long_board_campaign.py` | — | Coder 4 | The swarm task and its baseline are not implemented. |

## Commands that exist

```bash
python scripts/board_long_campaign.py inventory
python scripts/board_long_campaign.py run --experiment T11 --seed 7 --arm uninterrupted --ticks 4 --population 6 --workers 1 --output <dir>
python scripts/board_long_campaign.py resume --experiment T11 --seed 7 --ticks 4 --population 6 --checkpoint <dir>/runs/T11/seed_7/arm_uninterrupted/checkpoints/mid.bin --output <dir>
python scripts/board_campaign_analyst.py --campaign <dir>
```

T11's pilot uses `GenesisRuntimeProfile.life_loop_world` and `GenesisEngine.capture_fork` / `from_fork`. It does not answer T01–T10 or T12. It does not measure the board.

## Board plan

On the Orange Pi Zero 3, with the RAM and cooling that will actually be used, run the T11 calibration for 60 to 120 minutes and record seconds per generation, RSS, temperature, and throttling. Do not multiply a single-core time by a hoped-for worker count. The long horizon stays locked only after that measurement. This file does not contain that measurement.
