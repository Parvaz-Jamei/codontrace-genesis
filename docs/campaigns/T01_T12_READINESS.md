# T01–T12 readiness

Basis: `e90f9cd1d7287d2b51531cae82cd75dc0a18b2f1`. This table is not a result.
A config field or a class is not a connection. `run_enabled` is false until that experiment's long-campaign preconditions pass.
The Orange Pi rate has not been measured.

| ID | Backend | Status | Runner | Consumer | Owner | Gap |
|---|---|---|---|---|---|---|
| T01 | ENGINE | نیازمند اتصال | `—` | — | Coder 1 | No engine path consumes a functional phenotype for this question. |
| T02 | ENGINE | نیازمند اتصال | `—` | — | Coder 1 | The Price partition does not account this experiment's births. |
| T03 | INTEGRATED | نیازمند اتصال | `—` | — | Coder 2 | No recorded exchange between a mutualism submodel and GenesisEngine. |
| T04 | ENGINE | نیازمند اتصال | `—` | — | Coder 3 | A checkpoint is not the historical-contingency experiment. |
| T05 | ENGINE | نیازمند اتصال | `—` | — | Coder 2 | Do not relabel the phase-5 script as T05. |
| T06 | ENGINE | نیازمند اتصال | `—` | — | Coder 3 | No runner shows ledger change changing the chosen action. |
| T07 | ENGINE | نیازمند اتصال | `—` | — | Coder 3 | Transfer is not connected to a held-out task. |
| T08 | ENGINE | نیازمند اتصال | `—` | — | Coder 3 | Skill compression is not connected to an energy-matched assay. |
| T09 | ENGINE | نیازمند اتصال | `—` | — | Coder 4 | No sampler writes the successes this measure needs. |
| T10 | ENGINE | نیازمند اتصال | `—` | — | Coder 2 | Ecology in the preset is not the shock experiment. |
| T11 | ENGINE | آمادهٔ پایلوت | `scripts/board_long_campaign.py` | GenesisEngine.run_ticks | Coder 4 | Board rate is unmeasured. UI pressure, multi-day memory, and a second architecture are not in this pilot. |
| T12 | ENGINE | طرح | `—` | — | Coder 4 | The swarm task and its baseline are not implemented. |

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
