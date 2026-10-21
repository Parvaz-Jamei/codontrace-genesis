# Ports, not a domain-specific engine

```text
        adapters (Avida / MABE2 / biomedical table / ESP32 stub)
                          |
                          v
                   ClaimGate bundle
                          |
                          v
                    audit_bundle()
                          |
                          v
                    public ladder 0-5

GenesisEngine  -->  ticks / digest / replay
        |
        +--> native adapter  -->  same ClaimGate bundle
```

The engine runs a specified world. It does not know medicine, Avida, or
robots. Domains attach at the **adapter** port.

| Port | Module | Engine used? |
|---|---|---|
| Native ALife campaign | `adapters.codontrace` | yes |
| HE02 campaign JSON | `adapters.codontrace_he02` | no (adapter reads artifact) |
| HE03 campaign JSON | `adapters.codontrace_he03` | no; research file absent |
| Avida `.dat` | `adapters.avida` | no |
| MABE2 CSV | `adapters.mabe2` | no |
| Declared score table | `claimgate.domain` | no |
| Biomedical labels | `adapters.biomedical` → `domain.BIOMEDICAL` | no |
| Device-model analog (SiMD/SaMD labels) | `bundle_from_device_model_cou` | no |
| ESP32 stub | `adapters.esp32_bridge` (re-export of `swarm.devices.esp32`) | optional |
| Text-file digest (LF identity) | `genesis.text_digest.sha256_text_file` | no |
| Arm-role translation | `adapters.roles.canonical_role` | no |

Engine-side ports used by modules (all under `codontrace`; experimental, see
`genesis.public_api_manifest`):

| Port | Module | Engine used? |
|---|---|---|
| Exogenous world events per generation | `engine_spec.GenerationInputProvider`, replay via `replay.RecordedInputProvider` | yes |
| Sensor channel descriptors and normalization | `contracts.channels` | no |
| Hash-chained event journal | `genesis.journal.HashChainedJournal` (+ `journal_anchor`, `verify_anchor`) | no |
| Swarm coordination state machine | `genesis.swarm.SwarmCoordinatorCore` | no |
| Parameter-space QD search and coevolution | `genesis.qd_parametric`, `genesis.coevolution` | no |
| Paired shadow evaluation | `genesis.shadow_evaluation` | no |
| Split conformal intervals, disturbances | `life_loop.conformal_bands`, `life_loop.disturbance` | no |
| Sim-to-real disparity record | `genesis.transferability` | no |
| Run roots and module run references | `contracts.run_roots`, `genesis.run_refs` | optional |

Module-side implementations of those ports:

| Module | Uses |
|---|---|
| `swarm.runtime.SwarmCoordinator` | `genesis.swarm` core, `genesis.journal` |
| `swarm.policies`, `swarm.coevolution` | `genesis.qd_parametric`, `genesis.coevolution`, `genesis.shadow_evaluation` |
| `swarm.decision_support`, `swarm.research` | `life_loop.conformal_bands`, `genesis.shadow_evaluation`, `life_loop.disturbance` |
| `swarm.adapters.fdc`, `swarm.adapters.esp32` | `contracts.channels` |
| `swarm.devices.esp32` | device I/O implementation (`adapters.esp32_bridge` re-exports it); STR record from `genesis.transferability` |
| `swarm.transport.mqtt_session` | MQTT client setup for `swarm.mqtt` |

Adding a domain means a new `DomainProfile` or ingest adapter.
It does not mean forking `engine.py`.

Shared adapter helpers (not second engines):

- `canonical_role` maps campaign labels such as `auxiliary_control` onto
  the five public ClaimGate roles.
- `sha256_text_file` pins markdown/JSON/`.dat`/CSV to Git LF bytes so
  Windows `core.autocrlf` does not break Linux pins.

