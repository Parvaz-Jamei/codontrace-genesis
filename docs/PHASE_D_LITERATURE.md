# Phase D multi-generation evidence — literature checklist

Phase D adds a **measurement layer** for multi-generation fitness and
instinct/behavior trajectories. It does not prove open-ended evolution,
intelligence, or instinct evolution.

CodonTrace Genesis already had `LifeLoopObservation`, `OEEMetricsReport`, QD
archives, lineage records, and ClaimGate. Phase D wires those into
first-class library APIs that are more complete than a typical Avida
post-hoc analyze-mode dump: callers get a Python
`MultiGenerationEvidencePack` with JSON + digest export.

## Checklist (must remain honest in docs, tests, and ClaimGate)

| Source | What Phase D implements | What Phase D does **not** claim |
|---|---|---|
| MODES toolbox — Dolson, Vostinar, Wiser, Ofria 2019 *Artificial Life* | Change, novelty, complexity, ecological potential **after a persistence filter**: only lineages with descendants alive after `persistence_window_t` generations count. Filter is an organism-id coalescence window, not a full Empirical systematics shadow run | Not a bit-identical C++ MODES port; not proof of open-endedness |
| Empirical MODES / systematics notes | Opt-in Python shuffled-parentage adapter (`build_empirical_systematics_shadow`) can supply a real `shadow_digest` for Tokyo step_4; default off; limitations still recorded when unused | Not an Empirical C++ phylogeny port; not a Type 1 pass |
| Bedau evolutionary activity | Library objects for novelty (first appearances), diversity (currently present components), and cumulative activity from genotype/behavior presence | Not a proof that evolutionary activity is unbounded |
| Channon 2024 Tokyo Type 1 procedure | Opt-in `TokyoType1MeasurementProtocol` and `TokyoType1MeasurementCampaign` (≥2 seeds) record activity/novelty/shadow *measurement steps*; `run_channon_avida_modes_shadow_suite` pins `persistence_window_t` sweeps | `tokyo_type1_passed` blocked; measurement ≠ pass |
| ALife OEE encyclopedia hallmarks | Descriptive flags: ongoing novelty / complexity / activity metrics were observed | Hallmarks observed as metrics ≠ OEE demonstrated |
| ISAL 2024 MODES assessment (Bohm / Zhang / Dolson) | Report the four MODES axes with persistence filtering and explicit limitations | Not a publication-grade OEE assessment by itself |
| User philosophy | Survivors reproduce; measure whether next-gen fitness/behavior **metrics** move | Metric deltas are runtime observations, not instinct/intelligence proof |
| Existing CodonTrace Genesis surfaces | `LifeLoopObservation` hook unchanged by default; `OEEMetricsReport` filled as `measurement_only`; lineage + behavior descriptors consumed; ClaimGate remains the authority | Default Phase A/B/C presets and digests stay stable |

## ClaimGate

- Default pack ceiling: `runtime_observation`
- `instinct_improved` requires metric delta + same-seed paired comparison + **multi-seed protocol** + ablation/control + persistence filter. Missing any of those downgrades to `runtime_observation`.
- OEE ceiling: `oee_measurement_only`. `oee_candidate` still needs the existing research-grade thresholds (seeds, shadow, CIs, …).
- Channon 2024 Tokyo Type 1: `TokyoType1MeasurementProtocol` records measurement steps at ceiling `tokyo_type1_measurement_only`. Pack-level `evaluate_tokyo_type1_measurement_claim(pack)` is a cheap vocabulary hook that aliases to `oee_measurement_only` unless Channon steps are recorded. This is **not** a Type 1 pass. `tokyo_type1_passed` remains forbidden. CLIP / ASAL foundation-model OE (arXiv 2412.17799) is **not** implemented.
- Blocked: `open_ended_intelligence`, `proved_instinct_evolution`, `proved_open_endedness`, AGI, collective intelligence, Tokyo Type 1 passed.

See also [`SCIENTIFIC_AUTHORITIES_2026.md`](SCIENTIFIC_AUTHORITIES_2026.md). Pack `LITERATURE_CHECKLIST` keys are unchanged so Phase D pack payloads stay stable.

## API entry points

```python
from codontrace.genesis import (
    GenesisEngine,
    GenesisRuntimeProfile,
    build_multi_generation_evidence_pack,
    evaluate_instinct_improvement_claim,
    evaluate_oee_measurement_claim,
    evaluate_tokyo_type1_measurement_claim,
)

spec = GenesisRuntimeProfile.life_loop_world(seed=7, tick_count=12, population=6)
result = GenesisEngine.from_spec(spec).run_ticks()
pack = build_multi_generation_evidence_pack(result, spec=spec)
print(pack.digest)
print(evaluate_instinct_improvement_claim(pack).final_claim)
print(evaluate_oee_measurement_claim(pack).final_claim)
print(evaluate_tokyo_type1_measurement_claim(pack).final_claim)  # oee_measurement_only; Type 1 not passed
```

Optional: `life_loop_world(reproduction_mode=SEXUAL_CROSSOVER)` and
`dynamic_environment_world()` remain substrate opt-ins. Phase D reads
their records; it does not change their defaults.

Print-only smoke: `examples/genesis_multi_generation_evidence.py`,
`examples/genesis_tokyo_type1_measurement.py`,
`examples/genesis_scientific_gaps_2026.py`.

See also `docs/SCIENTIFIC_AUTHORITIES_2026.md`.
