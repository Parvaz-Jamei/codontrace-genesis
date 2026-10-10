# Local scientific console patch — 2026-10-10

Base: `5e7fefe1f0e5b0f3a99fe7242c3174cd8cd1638c`. No commit, tag, release, push or deployment is performed by this patch.

## Execution and scientific scope

T01–T05 have runnable **REFERENCE** pilots. They do not execute the Genesis VM and report zero VM ticks. T11 remains an **ENGINE calibration** route. T06–T10 and T12 remain blocked until their actual adapters and measurements exist. The UI must expose this distinction; adding a menu entry does not create a working engine experiment.

| Pilot | Actual change | Interpretation boundary |
|---|---|---|
| T01 | QD archive supplies actual parents; matched random-descriptor control | Bounded genomic descriptors, not executed Boolean programs or demonstrated open-ended evolution |
| T02 | Exact offspring allocation, actual deme sizes and retained offspring accounting | Price identity is accounting; an identity residual near zero alone does not support group-selection advantage |
| T03 | Partner permutation and measured individual payoffs; final-horizon assay | Immediate mutual benefit can be supported in the model; this is not evidence of collective individuality |
| T04 | Immutable historical snapshots, forks, matched future streams and exact replay calibration | Branches share histories; do not count branches as independent founder seeds |
| T05 | Real frozen populations, bounded archived time-shift assays and visible extinction | A plotted matrix is a measurement; the confirmatory question requires replicated controls and a specified inferential protocol |

Scientific support is accepted when an integrity-checked assessment with verified controls supports its stated hypothesis. Running, stopping and pausing do not erase recorded evidence or block descriptive analysis. Execution status, recorded assessment and a newly evaluated hypothesis are distinct fields. No universal claim is made that Red Queen must succeed or must fail.

The new unbiased integer stream is versioned `rejection-v2`; old pinned PRNG helpers are preserved. Comparing old and new streams requires recording the stream version, source SHA and configuration digest.

## Chat tools and output

`GET /api/science/tools` supplies the UI/LLM catalog. `POST /api/science/tools` accepts `{ "tool": "metric_series", "args": { "run_id": "...", "metric": "fitness", "seed_from": 7, "seed_to": 9 } }`.

Available tools: run inspection, opt-in registered project list, opt-in process names/PID/load, metric time series, seed/arm endpoint comparison, measured time-shift heatmap, recorded Price decomposition, diversity curves, descriptive seed bootstrap, mathematical equations, read-only reproduction snippet, recorded confusion matrix and paired quality/cost scatter.

The tools calculate on the host. A compatible local model selects tools through OpenAI-style function calls. Calls are read-only, limited to four tools and two model rounds. The selected run is enforced; project/process discovery requires an explicit user request. Process command arguments and unrelated file contents are not read. Code output is displayed, never executed.

Manual tools and deterministic chart requests work without a model. A small model without native tool-call support can use this manual path. A provider rejecting tool schemas with an explicit 400/422 unsupported-tool response gets one bounded text-only retry. No particular model has been downloaded or benchmarked on the board in this review.

A default chart uses only its selected run. Seed-comparison tools or explicit seed filters may compare recorded runs in the same campaign/experiment. Campaign reads share one total 8-MiB/20,000-record budget across at most 64 runs; retained tails and truncation are labelled in provenance. Charts preserve endpoints and bucket extrema within the retained window when downsampled. Raw data is unchanged. Partial data and malformed records remain identified in source provenance. Confusion matrices require actual recorded matrices and labels. Missing measurements produce a visible error rather than invented values. Different reruns are not connected as one trajectory, and duplicate seed/arm sessions block seed bootstrap instead of becoming extra independent replicates.

Inline chat output supports SVG charts, escaped tables/code and lazily loaded KaTeX. KaTeX uses `trust: false`, bounded expansion and bounded size. No CDN is needed for deployed font assets. Each artifact has run/source/snapshot provenance and a JSON download. Mathematics supplied as definitions is labelled separately from measured results.

## Lifecycle, progress and storage

Every card is keyed by its run ID, not by its title, selected row or script name. Details for all registered cards refresh with concurrency four; each response must identify the requested run. The store rejects stale per-session revisions, retains zero counters and keeps measurements, logs, parameters and threads independent. A successful empty registry removes deleted server cards, while a network failure preserves the last known data.

| Action | Real behavior |
|---|---|
| Launch | Creates a unique run, manifest and card; each readiness experiment has its own launch lock and error |
| Play on paused run | Requests cooperative resume when supported; waits for acknowledgement |
| Play on stopped/failed run | Starts a fresh replay through the restart route; does not claim checkpoint continuation |
| Pause | Requests PAUSING and waits for the worker's PAUSED acknowledgement |
| Stop | Targets that run's worker only and waits for terminal acknowledgement |
| Restart | After stop/finalization, launches a new run with the original scientific configuration and parent provenance; preserves old evidence |
| Remove | Requires the process/finalizer to have finished; removes the selected run without affecting other cards |

Duplicate action clicks are blocked per card. Keyed restarts are serialized and idempotent, including concurrent requests with the same request ID. Process incarnation tokens prevent a reused PID from owning old run data; when identity is unavailable, unrelated native processes are not force-signalled. Real two-process HTTP tests verify that pausing/stopping/removing one card leaves the other advancing.

Each run has a unique campaign/experiment/arm/seed/session ID. The canonical console directory owns manifest, status, flushed metrics JSONL and execution summary. Campaign directories link to the canonical run, avoiding divergent copies.

Progress counts actual model work units; seed count is separate. T04 includes branch work and distinguishes requested history horizon, planned upper bound and realized work. Valid extinction may terminate a fully observed experiment before its planned horizon; the preserved stop reason and original budget explain this. Stop requests do not masquerade as completed horizons.

Pause requests remain PAUSING until worker acknowledgement. Active elapsed time excludes ongoing acknowledged pauses. Resume clears the marker and waits for execution to continue. Capability controls are enabled only for runners that actually implement the callback. An exception retains partial data and records FAILED. Export hashes the bytes actually written into the ZIP, including live snapshot prefixes.

## Verification and remaining work

Focused Python tests cover real runner accounting, replay, streaming, pause/resume, failure, export hashes, HTTP tools, lifecycle-independent analysis, campaign seed uncertainty, path containment and native function-call exchange with a synthetic model server. Frontend tests cover structured charts, escaping, recorded assessments, malformed output and the actual backend catalog contract. Build runs TypeScript checking and bundles the static application.

The synthetic model server validates the protocol, not model reasoning. An alternate Chromium binary was installed, but browser startup failed with SIGTRAP in this environment. Actual browser visual layout, pointer interactions, accessibility navigation and Orange Pi resource measurements require local acceptance testing. Full repository tests and long confirmatory studies are not implied by the focused suite.

Before pushing: launch locally, test desktop/mobile and Persian/English, select a paused/stopped/failed/completed run, render every supported artifact, verify chart seed filters, compare displayed progress with status work counters, pause and resume an actual worker, and verify the manifest source/config/stream digests. Preserve existing data.

## Research basis

- Price decomposition includes selection and transmission; it is an identity: https://pmc.ncbi.nlm.nih.gov/articles/PMC3354028/
- Short-term arms races and later fluctuating selection need distinct interpretation: https://doi.org/10.1111/j.1461-0248.2011.01624.x
- Time-shift assays compare populations across actual sampling times: https://www.nature.com/articles/s41559-021-01390-7
- Ecological and physiological effects can alter host–virus dynamics: https://www.nature.com/articles/s41467-024-51344-3
- Mathematical rendering options and untrusted-input controls: https://katex.org/docs/options and https://katex.org/docs/security

Research informs the measurement contract; it does not establish scientific novelty of these code changes. Before each new protocol, search current primary papers, inspect current code and preregister endpoints/controls. Interdisciplinary ideas may guide new mechanisms, but require explicit assumptions and calibration before scientific inference.

## Chart studio V3

One bounded tool, `scientific_plot`, exposes two explicit modes. `raw` is the default and accepts only run_id/mode; no option silently changes the display. `tool` enables validated enum/string/integer parameters, generation/seed filters and exact arm. This is the same catalog used by the manual picker and native LLM tools. Models request a chart; the host computes it.

Examples:
```json
{"tool":"scientific_plot","args":{"mode":"raw"}}
{"tool":"scientific_plot","args":{"mode":"tool","chart":"histogram","metric":"fitness","seed_from":3,"seed_to":8,"generation_from":50,"generation_to":200,"palette":"accessible","bins":20}}
{"tool":"scientific_plot","args":{"mode":"tool","chart":"correlation","metrics":"fitness,energy_used"}}
```

Distribution calculations use all valid observations in the bounded snapshot before display downsampling. Histogram bins share bounds across series, including the upper endpoint. ECDF uses observed ranks, without smoothing. Boxes use linearly interpolated quartiles and Tukey 1.5-IQR whiskers/outliers. Gaussian KDE uses stated normal-reference bandwidth; it needs at least 3 nonconstant observations per group. Violin widths have equal peak normalization, not sample-size encoding. Correlations use pairwise-complete Pearson r with sample counts, minimum 3 pairs and missing values for constant/insufficient pairs; no p-values or causal conclusions. Error bars require recorded ordered lower/central/upper measurements and do not assert what confidence level they represent.

No filters modify the stored file. The source snapshot hashes, options, observation counts, limits and transformations accompany the artifact. More than 12 groups requires narrower filters rather than silently discarding groups. Log scale rejects unsupported geometries and nonpositive plotted coordinates. Color alone is not the only identifier: labels, dash patterns and data tables are included. This is not a claim of audited WCAG compliance. SVG is vector; PNG export is 1800×1320. Browser export/layout still needs local acceptance on a working browser.

Primary documentation consulted:
- https://vega.github.io/vega-lite/docs/boxplot.html
- https://vega.github.io/vega-lite/docs/density.html
- https://vega.github.io/vega/examples/violin-plot/
- https://www.w3.org/WAI/fundamentals/accessibility-principles/
- https://www.w3.org/WAI/WCAG22/Understanding/non-text-contrast

The renderer is local React/SVG; no Vega runtime, remote chart service or additional model weights are required. Network absence does not prevent manual chart generation. Native tool calling depends on the model/server; text fallback and manual tools remain available.

V3 also fixes a finalization race: sealed T11 completion work is used for the snapshot when the status writer has not yet flushed its final counters. A completed label alone does not fabricate done=total.

## Official cloud provider integration

`GET /api/providers` returns configuration flags and cached dynamic IDs, never credentials/fingerprints. `POST /api/providers` accepts save, refresh and disconnect. Discovery explicitly calls the official authenticated `/models`, bounded to 512 KiB / 2000 entries / 6 seconds. Fixed official HTTPS hosts and refused redirects prevent forwarding credentials to a model-selected URL. Model discovery performs no chat inference.

Environment `OPENAI_API_KEY` / `DEEPSEEK_API_KEY` wins over server-file keys. `CODONTRACE_CONFIG_DIR` defaults to `~/.config/codontrace`; `cloud_providers.json` is atomically written with POSIX mode 0600. This is plaintext server configuration, not encrypted storage. Windows inherits directory ACLs and is not covered by POSIX permission tests. Disconnect deletes the stored key and disables the provider even with an environment key present; save reconnects. Key inputs and remote settings tokens remain in component memory, not the browser store.

Settings mutations require the existing origin check plus a loopback caller when no settings token exists. With `CODONTRACE_SETTINGS_TOKEN`, the exact bearer token is required even locally. Forwarded clients are not local. Remote board users set a token or use a local SSH tunnel.

Dynamic IDs use `openai::ID` and `deepseek::ID`, avoiding local/GGUF collisions. GPT/text reasoning candidates use a name heuristic; image/audio/realtime/specialized models are excluded from chat choices. The fetched count remains visible. Listing access cannot establish Chat Completions/native-tool compatibility. This patch uses Chat Completions; Responses-only models are not generally supported. Incompatible models return explicit provider errors.

OpenAI uses max_completion_tokens without forced temperature for reasoning-model validation. DeepSeek likewise omits forced temperature. DeepSeek reasoning_content is preserved only inside its tool-round protocol, not exposed in chat/artifacts. Both providers work without a local LLM. They call the same read-only scoped scientific tools; no generated code executes. Authentication is retained in the bounded native-tool fallback.

Cloud selection is explicit and disclosed: message/selected-run context go to the selected provider and use account API credits. Catalog requests are explicit; ordinary status reads perform no cloud requests. No real keys or paid inference were used here.

Primary API documentation reviewed:
- https://developers.openai.com/api/reference/resources/models/methods/list
- https://developers.openai.com/api/reference/resources/chat/subresources/completions/methods/create
- https://api-docs.deepseek.com/api/list-models/
- https://api-docs.deepseek.com/api/create-chat-completion/
- https://api-docs.deepseek.com/guides/thinking_mode/


## V4 access and inference budgets

All chat, abort/cancel, endpoint-change and scientific-tool POST operations, and the tool catalog GET, require a direct loopback connection when `CODONTRACE_API_TOKEN` is unset. If configured, the exact bearer token is mandatory even on loopback. Forwarded callers do not inherit loopback trust. The usage token is entered in Settings and remains in page memory; the administrative `CODONTRACE_SETTINGS_TOKEN` is separate. An API usage token does not grant provider-key administration. Use an SSH tunnel or HTTPS reverse proxy for remote token/key transport. This does not claim that all existing run-management endpoints have acquired authorization.

Local inference keeps a 1800-second default via `CODONTRACE_LLM_TIMEOUT`; finite positive overrides are honored without a 60-second ceiling. Cloud inference uses `CODONTRACE_CLOUD_TIMEOUT` (default 120 seconds). Each multi-round call has one shared deadline. Cloud transport admits at most 4 concurrent responses by default (`CODONTRACE_CLOUD_MAX_CONCURRENT`, 1–32), and 30 requests/minute (`CODONTRACE_CLOUD_REQUESTS_PER_MINUTE`, 1–10000). These limits concern HTTP requests, not simulation CPU-core selection. Cancellation returns promptly but cannot retract an upstream request already accepted or guarantee reimbursement. Admission slots are held until the upstream response closes. Ambiguous paid POST timeouts are not automatically retried.

T03's primary removal assay now estimates **net** immediate benefit under explicitly inducible interaction investment: isolated individuals have the same external resources but neither pay interaction costs nor receive benefits. The previous constitutive-cost removal calculation remains a named diagnostic. These are different counterfactuals and must not be mixed across versions. Neither establishes reproductive collective individuality. Report version `inducible-investment-removal-v2` with the data.

Descriptive seed bootstrap now uses per-arm RNGManager streams; method `seed-endpoint-percentile-rngmanager-v2` includes RNG provenance. Its intervals can differ from V3; this is an explicit method change, not evidence that the biological effect changed.
