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
| ESP32 stub | `adapters.esp32_bridge` | optional |
| Text-file digest (LF identity) | `genesis.text_digest.sha256_text_file` | no |
| Arm-role translation | `adapters.roles.canonical_role` | no |

Adding a domain means a new `DomainProfile` or ingest adapter.
It does not mean forking `engine.py`.

Shared adapter helpers (not second engines):

- `canonical_role` maps campaign labels such as `auxiliary_control` onto
  the five public ClaimGate roles.
- `sha256_text_file` pins markdown/JSON/`.dat`/CSV to Git LF bytes so
  Windows `core.autocrlf` does not break Linux pins.

