# Swarm code paths after the engine integration

The swarm module keeps its commands, HTTP API, MQTT bridge and journal file
formats. The general parts now live in engine sections; the swarm files call
them. Each section has its own tests.

| Capability | Section (engine side) | Swarm entry point | Tests |
|---|---|---|---|
| Journal: hash chain, segments, checkpoints, retention, file lock | `src/codontrace/genesis/journal/` | `swarm/runtime.py` (`SwarmCoordinator` subclasses `HashChainedJournal`) | `tests/test_genesis_journal.py`, `tests/characterization/test_swarm_journal_*.py` |
| Journal head anchor | `src/codontrace/genesis/journal/anchor.py` | `SwarmCoordinator.run_reference()` | `tests/test_run_refs.py` |
| Membership, commands, trust, readings, fusion, diagnosis, sampling plans | `src/codontrace/genesis/swarm/` | `swarm/runtime.py`, `swarm/policies.py` (`diagnose`) | `tests/test_genesis_swarm_core.py` |
| Channel descriptors and normalization | `src/codontrace/contracts/channels.py` | `swarm/sensors.py` (re-exports), `swarm/adapters/fdc.py`, `swarm/adapters/esp32.py` | `tests/test_contracts_channels.py`, `tests/test_esp32_split.py` |
| Pipeline search and coevolution | `src/codontrace/genesis/qd_parametric.py`, `src/codontrace/genesis/coevolution.py` | `swarm/policies.py` (`PolicyArchive.fit`), `swarm/coevolution.py` | `tests/test_genesis_qd_parametric.py` |
| Split conformal interval, shadow comparison, disturbances | `src/codontrace/life_loop/conformal_bands.py`, `src/codontrace/genesis/shadow_evaluation.py`, `src/codontrace/life_loop/disturbance.py` | `swarm/decision_support.py`, `swarm/research.py` (`perturb`) | `tests/test_decision_support_unification.py` |
| Sampling schedule | `src/codontrace/genesis/swarm/active_sampling.py` | `swarm/decision_support.py` | `tests/test_decision_support_unification.py` |
| Run root | `src/codontrace/contracts/run_roots.py` | `swarm/service.py` (`CODONTRACE_SWARM_DIR`) | `tests/test_run_refs.py` |
| MQTT client setup | `src/codontrace/swarm/transport/mqtt_session.py` | `swarm/mqtt.py` | `tests/test_esp32_split.py`, `tests/test_swarm_mqtt_broker.py` |
| ESP32 device I/O | `src/codontrace/genesis/transferability.py` (STR record only) | `swarm/devices/esp32.py` (implementation; `claimgate/adapters/esp32_bridge.py` re-exports it) | `tests/test_discovery_qd_wire_esp32_bridge.py`, `tests/test_esp32_split.py` |

## Population members on the wire

`codontrace.genesis.swarm.population_adapter` turns engine members into swarm
hello and reading messages (`hello_messages`, `reading_messages`). Swarm node
ids must match the core identifier rule (`contracts.wire_validation.identifier`:
an ASCII letter or digit, then up to 63 letters, digits, `_` or `-`), and
organism ids may not. Each member id becomes a node id like this:

- every character that is not alphanumeric, `_` or `-` becomes `-`
  (`'org.1'` and `'org/1'` both become `'org-1'`);
- `m` is prepended when the result does not start with an alphanumeric
  character (`'_x'` becomes `'m_x'`);
- the result is cut to 64 characters.

Ids that already follow the rule, such as the engine's own `'org-0'` or
`'org-0-g2-1edd0641fd'`, are unchanged, so the engine digests are unchanged.

When two different member ids in one call map to the same node id (for
example `'org.1'` and `'org-1'`, or two ids that differ only after
character 64), both functions raise `ValueError` naming the two ids and the
node id. Before this check the second member was dropped without notice: the
core answered its hello as `duplicate_or_reordered` and fusion counted one
member.

Limits:

- The check is per call. If `'org.1'` is sent in one call and `'org-1'` in a
  later call, the core treats them as one node. Keep one member list per
  swarm, or pass every member in a single call.
- `str.isalnum()` accepts any Unicode letter or digit, so a non-ASCII id such
  as `'é1'` passes through unchanged. The core then rejects it with
  `invalid identifier`. That error is loud, but use ASCII member ids.
- The core's member capacity (256 nodes) also applies to populations.

Tests: `tests/test_genesis_swarm_core.py`.

Rules that hold for every row: same seeds give the same outputs as before the
move (pinned in `tests/characterization`), randomness comes from
`RNGManager`, and the engine sections never import `codontrace.swarm`.

Method notes and sources are in [SOURCES.md](SOURCES.md) and in each module
docstring.
