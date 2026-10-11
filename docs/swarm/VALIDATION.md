> Historical V1 report. V2 adds the Simulation Atlas and updates the main UI build; see ../simulation/VALIDATION.md for current validation.

# Validation — Wi-Fi Sensor Swarm V1

Base: `694af75a4047c98a24eb90e7f1c8bf10ff149d8c` (b29 main).
Date: 2026-10-11. Python 3.12.14, pytest 9.1.1, Hypothesis 6.168.5, optional paho-mqtt 2.1.0.

83 targeted tests passed (15.70 seconds): 39 protocol/runtime/policy/research tests, 6 engine/API tests, 25 existing console preview tests, 10 existing V4 regressions, 3 life-loop digest-history checks. No digest baseline was edited. This is scoped regression validation, not a claim the full repository suite is green.

Covered: malformed/non-finite values; identity, reboot and dedup; stale/future timestamps; unit/quality/alignment; transactional rollback; journal hashes, state replay, tampering and disk failure; stale cross-process writer rejection; command capabilities/ACK/expiry/pause; sensor dropout reallocation; concurrency; read-only LLM scope after stop; real localhost HTTP authorization and device-only tokens; actual GenesisEngine generation input mapping plus validate_consistency; paused swarm observation without crashing the engine; bounded deterministic pipeline search and nuisance co-adaptation; transfer rejection and no-effect controls; twin identifiability and representation budget feasibility.

MQTT validation uses the installed Paho 2.1 SDK with mocked broker/client calls, including TLS setup, MQTTv5, retained-message rejection, topic identity and command dispatch. A live TLS broker and physical board were **not** available. Do not claim radio latency/energy, firmware ACK reliability or hardware learning success from these tests.

16 seeds × 10 ideas = 160 recorded synthetic engineering probe rows; 64 samples/seed. All rows label synthetic=true and physical_validation=false. The CLI flushes per row and reports progress per seed. These are reproducibility/instrument checks, not confirmatory biological or hardware findings. Some controls intentionally produce no effect; improvement is not hard-coded as a verdict.

Standalone dashboard JavaScript syntax checked. DOM/API interaction is tested separately with jsdom and a real localhost backend; canvas drawing is stubbed in this check. Chromium could not launch in this environment (SIGTRAP), so no visual browser approval, screenshot comparison, responsive-layout approval or chart-pixel validation is claimed. Existing main index.html was not modified.

Before merging: apply the exact-base patch in a clean checkout, run supplied tests, then perform real-browser desktop/mobile QA and a live broker/device pilot. Check firmware capability advertisement, UTC calibration, duplicate command idempotence, actual ACK, broker ACL isolation, reconnect and stop semantics. For scientific conclusions follow RESEARCH_PLAN_FA.md; determine independent physical replication and statistical power from pilot variance, not seed count alone.
