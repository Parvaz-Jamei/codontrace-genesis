# V3 validation — 2026-10-11

Base: 694af75a4047c98a24eb90e7f1c8bf10ff149d8c (b29), exact user-attached V2 upgraded in an isolated checkout. No core-engine edits or digest baseline repinning. Original repository left untouched.

- 130 targeted Python tests passed: swarm protocol/runtime/API/engine link, recorder/reader/export/LLM Atlas inspection, actual engine equality including extinction, existing console regressions, life-loop digest history, console followups and LLM review API contract.
- 33 TypeScript/React tests passed: existing controls, provider settings and charts; service worker; coordinate/color/lifecycle checks; export cache mutation and explicit token precedence.
- Strict TypeScript checks and both production builds passed. Atlas remains a lazy main-console view and independent locally bundled page. Vite still advises about a main chunk over 500 kB; no Orange Pi performance claim is derived from build success.
- Real HTTP plus jsdom interaction passed with actual engine recordings: correct population, next/play/pause, seed switch, inspector and sequence export. Export ZIP integrity and manifest seed/engine ID/generation count verified. This is not a native browser screenshot/layout test.
- Three actual digital-engine seeds × 24 generations + initial snapshots = 75 new frames. Includes births, deaths and extinction; consistency checks passed. After extinction, action ticks may stay fixed while recorded generations advance.
- Independently rendered SVG with CairoSVG was visually inspected. No invented cells, motion, classifications or missing-generation interpolation.
- Fresh 16-seed × 10 synthetic engineering probes = 160 raw records. Reproducible paired seed-level exploratory bootstrap summary is included; no time-sample pseudoreplication or physical-performance claim.
- Ruff checks passed for changed Python modules and the three new-feature test files.
- Full-base and exact-V2 upgrade installation are checked separately, including SHA-256 after application. The installer never commits, pushes, downloads or deletes project files.

Python command (install declared test extras and optional swarm dependency first):

```bash
python -m pytest -o addopts='' tests/test_swarm_protocol_runtime.py tests/test_swarm_engine_api.py tests/test_simulation_observatory.py tests/test_console_preview.py tests/test_v4_review_regressions.py tests/test_life_loop_digest_history.py tests/test_console_followups_2026_10_10.py tests/genesis_gates/test_llm_review_api_contract.py
```

Frontend commands:

```bash
cd console
npm ci
npm test
npm run build
npm run build:simulation
```

Limitations: live TLS MQTT broker, physical boards, real power/latency/memory profiling and native-browser/mobile layout remain untested. Chromium 131 could not launch here; failed launch is recorded rather than counted as a pass. The full repository suite was not executed. Recorder must attach in each actual custom worker; summary-only artifacts cannot supply spatial positions. Recorder locking does not make concurrent engine mutation safe. Physical firmware must enforce command identity, boot/expiry and idempotent acknowledgements.

See AUDIT_V3_FA.md for fixed issues, empirical results, prior-art boundaries and five-phase physical/research acceptance plan. V2's 97/30 checks are historical and superseded for this package by the numbers above.
