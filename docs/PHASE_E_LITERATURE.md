# Phase E capsule / memory / role / collective substrate — literature checklist

Phase E adds **opt-in runtime effects** and first-class protocol objects for
associative capsule memory, Avida-inspired role/propagule gates, a deme
messaging subset, a phenotypic-plasticity *experimental-design* object over
Phase C environment cues, and an `AvidaParityProtocolSpec` recipe. It does
not prove learning, evolved plasticity, collective intelligence, or that
CodonTrace replaces Avida.

Phase D's MODES / Bedau / multi-generation measurement layer is unchanged.
When Phase E is enabled, those metrics can observe the resulting action, ATP,
and birth records because the substrate actually changes subsequent behavior.

## Checklist (must remain honest in docs, tests, and ClaimGate)

| Source | What Phase E implements | What Phase E does **not** claim |
|---|---|---|
| Avida demes / group selection — `devosoft/avida` wiki [Deme-introduction](https://github.com/devosoft/avida/wiki/Deme-introduction); `DEMES_*` / GermlineReplication | Deme/group containers, optional mean-fitness replication trigger with a recorded event (minimal real path), germline/propagule-eligibility flags | Not a C++ Avida deme port; not group-selection proof |
| Goldsby et al. coordination instructions | Messaging buffer with `send_message`, `retrieve_message`, `broadcast_message`, `block_propagation` and digest-backed events | Not evolved communication or language |
| GECCO 2008 digital germlines / cooperative networks | Soma vs germline / messenger role tags that **gate** reproduction or messaging when enabled | Not evolved division of labor or collective intelligence |
| Clune 2007; Lalejini & Ofria 2016; Frontiers 2021 Adaptive Phenotypic Plasticity (`sense-react-*`) | Sensory-read API over Phase C regime + local patches; optional sense-react action bias | Not a claim that phenotypic plasticity evolved |
| Ghalambor / Clune four-condition designs | Checklist object: ancestral static, novel static, fluctuating, assimilation under constant novel | Experimental-design checklist only |
| Am Nat 2020 associative learning; PLOS One odometry case study | Organism-local or lineage capsule slots that change **subsequent** action choice, ATP, or task eligibility under a fixed seed (ablation: disabled capsule ⇒ different digest / behavior) | Not proved associative learning or navigation intelligence |
| OntoAvida / avidaR (Sci Data 2023; PeerJ CS) | Exportable `PhenotypeTranscriptomeEvidence` JSON+digest objects (genome, fitness, ATP, role, action-execution counts as a transcriptome *proxy*) | Not a transcriptome biology simulator |
| Typical Avida post-hoc analyze-mode | First-class Python APIs + replay digests (`PhaseEEvidencePack`, `AvidaParityProtocolSpec`) | Software capability only; no superiority claim |

## ClaimGate

- Default pack ceiling: `runtime_observation`
- OEE ceiling remains `oee_measurement_only` on the Phase D layer
  (`tokyo_type1_measurement_only` is a measurement-only alias; Type 1 is
  **not** passed)
- Capsule wiring must produce a **subsequent-action** effect under a sensory
  cue, with capsules-off ablation (Clune 2007; Lalejini & Ofria 2016;
  Frontiers 2021 Adaptive Phenotypic Plasticity / Ghalambor four conditions)
- Blocked: `collective_intelligence`, `proved_collective_intelligence`,
  `evolved_plasticity`, `avida_replacement`, `associative_learning_proved`,
  AGI, open-ended intelligence, Tokyo Type 1 passed

See also [`SCIENTIFIC_AUTHORITIES_2026.md`](SCIENTIFIC_AUTHORITIES_2026.md).
JaxLife, Aevol_4b, and ASAL/CLIP OE are documentation comparators or future
measurement options — not implemented in the 2026 eval bugfix.

## API entry points

```python
from codontrace.genesis import (
    GenesisEngine,
    GenesisRuntimeProfile,
    build_phase_e_evidence_pack,
    build_multi_generation_evidence_pack,
    evaluate_phase_e_claim,
    AvidaParityProtocolSpec,
)

spec = GenesisRuntimeProfile.phase_e_substrate_world(seed=7, tick_count=8, population=6)
result = GenesisEngine.from_spec(spec).run_ticks()
pack = build_phase_e_evidence_pack(result)
print(pack.digest)
print(evaluate_phase_e_claim(pack).final_claim)
print(AvidaParityProtocolSpec().notes)
# Phase D can observe Phase E behavior when E is enabled:
d_pack = build_multi_generation_evidence_pack(result, spec=spec)
print(d_pack.claim_ceiling)
```

Defaults for Phase A/B/C/D presets remain off. Print-only smoke:
`examples/genesis_phase_e_substrate.py`.
