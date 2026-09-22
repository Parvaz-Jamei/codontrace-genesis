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
| Avida `.dat` | `adapters.avida` | no |
| MABE2 CSV | `adapters.mabe2` | no |
| Declared score table | `claimgate.domain` | no |
| Biomedical labels | `adapters.biomedical` → `domain.BIOMEDICAL` | no |
| ESP32 stub | `adapters.esp32_bridge` | optional |

Adding a domain means a new `DomainProfile` or ingest adapter.
It does not mean forking `engine.py`.
