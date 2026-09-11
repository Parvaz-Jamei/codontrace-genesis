# Phase E capsule / memory / role / collective substrate — literature checklist

Phase E adds **opt-in runtime effects** and first-class protocol objects for
associative capsule memory, Avida-inspired role/propagule gates, a deme
messaging subset, a phenotypic-plasticity *experimental-design* object over
Phase C environment cues, and an `AvidaParityProtocolSpec` recipe. It does
not prove learning, evolved plasticity, collective intelligence, or that
CodonTrace Genesis replaces Avida.

Phase D's MODES / Bedau / multi-generation measurement layer is unchanged.
When Phase E is enabled, those metrics can observe the resulting action, ATP,
and birth records because the substrate actually changes subsequent behavior.

## Checklist (must remain honest in docs, tests, and ClaimGate)

| Source | What Phase E implements | What Phase E does **not** claim |
|---|---|---|
| Avida demes / group selection — `devosoft/avida` wiki [Deme-introduction](https://github.com/devosoft/avida/wiki/Deme-introduction); `avida.cfg` `DEME_GROUP`; `DEMES_*` / GermlineReplication | Deme/group containers, mean-fitness replication trigger with a recorded event, optional germline copy, `CollectiveDemePayoffPack` contribution ledger, Phase F `run_collective_deme_payoff_campaign` (group-vs-individual contrast + ranking) | Not a C++ Avida deme port; ranking ≠ multilevel-selection experiment (`scaffold_only`); group fitness is `runtime_observation`; `collective_intelligence` blocked |
| Goldsby et al. coordination instructions / division of labor | Messaging buffer with `send_message`, `retrieve_message`, `broadcast_message`, `block_propagation`; DoL *metrics* (`build_deme_division_of_labor_observation`); Phase F `communication_ablation_status=not_run`; Phase H runnable ablation harness | Not evolved communication, language, or literature-grade DoL; Phase H measurement does not set ClaimGate `ablation_result` |
| GECCO 2008 digital germlines / cooperative networks | Soma vs germline / messenger role tags that **gate** reproduction or messaging when enabled; germline copy on deme replicate | Not evolved division of labor or collective intelligence |
| Clune 2007; Lalejini & Ofria 2016; Frontiers 2021 Adaptive Phenotypic Plasticity (`sense-react-*`) | Sensory-read API over Phase C regime + local patches; optional sense-react action bias; `LearningCausalPayoffPack` cue→action→ATP with ablation | Not a claim that phenotypic plasticity evolved |
| Ghalambor / Clune four-condition designs | Checklist object: ancestral static, novel static, fluctuating, assimilation under constant novel | Experimental-design checklist only |
| Am Nat 2020 associative learning; PLOS One odometry case study | Organism-local or lineage capsule slots that change **subsequent** action choice, ATP, or task eligibility under a fixed seed (ablation: disabled capsule ⇒ different digest / behavior); multi-seed payoff protocol | Not proved associative learning or navigation intelligence; `instinct_improved` stays gated |
| Ofria & Wilke 2004; avida.cfg 2.14.0 Logic-9; BMC Evol Biol 2021 | Opt-in Logic-9 reaction→resource→merit/ATP coupling; resource×population×mutation axes recorded | Not an Avida NAND CPU; not that 2021 paper replicated; `avida_replacement` blocked |
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

See also [`SCIENTIFIC_AUTHORITIES_2026.md`](SCIENTIFIC_AUTHORITIES_2026.md) and
[`WHY_NOT_INTELLIGENCE_YET.md`](WHY_NOT_INTELLIGENCE_YET.md) (CodonTrace Genesis
is not close to AGI; group fitness is not collective intelligence).
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
`examples/genesis_phase_e_substrate.py`,
`examples/genesis_scientific_gaps_2026.py`.
