# Host–parasite / microbe–virus ClaimGate port (2026-09-24)

**Additive DomainProfile port.** This folder documents a **separate** opt-in
ClaimGate profile for digital host–parasite and microbe–virus coevolution
evidence — analogous to the biomedical port — **without** baking infection
physics or medicine into `engine.py`.

## What this is / is not

| Is | Is not |
|---|---|
| A ClaimGate `DomainProfile` named `host_parasite` + thin adapter | A second Genesis engine or Avida/Symbulation reimplementation |
| Fail-closed blocked claims (vaccine, phage therapy, clinical pathogen, …) | Clinical, vaccine, antiviral, or epidemic-forecast certification |
| Docs + MVP claim labeling grounded in Avida/Symbulation/phage literature | Wet-lab BSL certification or virulence optimization for humans |
| Paper-safe additive pack (pins untouched) | A change to BAIC manuscript or HE01 empirical numbers |
| Opt-in: profile registered; unlisted clinical claims stay blocked | Implied FDA clearance or ASME V&V 40 pass |

## Architecture (port, not engine)

```
engine.py / genesis ticks     → domain-agnostic (unchanged)
ClaimGate DomainProfile       → host_parasite blocked_claims + limitations
adapters/host_parasite.py     → thin wrap of bundle_from_declared_scores
docs/claimgate/host_parasite… → requirements, challenges, brainstorm, API sketch
Phase 1                      → intervention menu stub + hardened blocks (delivered)
Phase 2                      → optional HostParasiteEnv + dual-null template (delivered)
Phase 3                      → intervention falsification + honesty gates (delivered)
Phase 4                      → multi-seed campaign digests + ClaimGate factory (delivered)
Phase 5                      → spatial/vertical transmission + range diagnostics (delivered)
Phase 6                      → factorial campaigns + network digests + preregistration (delivered)
Phase 7                      → freeze/replay/reciprocal campaign + richness digests (delivered)
Phase 8                      → interaction continuum + VT × spatial factorial (delivered)
Phase 9                      → evolvability/Cornish assays + comparator + HE_HP digests (delivered)
Phase 10                     → genome-aware Zaman dual digests (Wave 3; this PR)
Phase 11                     → codon-entropy / Hamming dual-null (Wave 3; this PR)
Phase 12                     → HGT-analogue + intracellular/free-living pack (Wave 3; this PR)
Phase 13                     → declared task–gene map digests (Wave 3 earn-in)
Phase 14                     → mode-completeness hardening (Wave 4; this PR)
Phase 15                     → genome × VT × spatial × continuum factorial (Wave 4; this PR)
Phase 16                     → virulence/resistance quality proxies (Wave 4; this PR)
Phase 17                     → Price≠causality refusal assay (Wave 4 earn-in)
Phase 18                     → soft-complete journal attach-registry packet (Wave 5; this PR)
Phase 19                     → ARD→FSD transition + cost-of-generalism (Wave 5; this PR)
Phase 20                     → resource × coevolution-dynamics factorial (Wave 5; this PR)
Phase 21                     → multi-seed contingency / repeatability S1 (Wave 5; this PR)
Phase 22                     → sequential Cornish multi-intervention (Wave 5; this PR)
Phase 23                     → Scanlan mutator dual-null (Wave 5 earn-in; this PR)
```

Phases 1–9 are on main; Waves 3–4 stack under Wave 5. Wave 5 (Phases 18–22, optional 23) lands on `feat/host-parasite-wave5-phases`. See `DEPTH_BRAINSTORM_WAVE5.md`.

Mirror of the biomedical pattern in `src/codontrace/claimgate/domain.py` and
`adapters/biomedical.py`: the profile labels claims; it does not change tick
semantics, grant a claim, or certify a device or therapy.

## Scope lock

This port uses digital **host** and **parasite** roles, as a microbe–virus
analogy. It does not add separate `DomainProfile`s for bacteria, archaea, or
wet-lab cells. Genesis cells remain the domain-agnostic ALife substrate;
`host_parasite` only labels claims and provides optional environment/campaign
protocols. CRISPR genetics, infection-in-engine, and taxonomic species packs
remain out of scope. The additive HE_HP campaign pack is documented in
[`docs/hard_experiment_hp/`](../../hard_experiment_hp/).

## Paper safety for BAIC / HE01

**Do not modify** (and this PR does not touch):

- `docs/hard_experiment_01/results_v7.json`
- `docs/claimgate/risk_bar.json`
- `docs/claimgate/biomedical_study.json`

Those pins remain BAIC / paper anchors. This pack is additive documentation
plus a thin registered profile. It does **not** change HE01 empirical numbers
or the BAIC manuscript.

## Sibling packs

- Biomedical applied evidence: `docs/claimgate/applied_medical_evidence_20260924/`
- ALife novel evidence: `docs/claimgate/novel_valuable_evidence_20260924/`

## How to use (opt-in)

```bash
PYTHONPATH=src python -c "
from codontrace.claimgate.adapters.host_parasite import (
    bundle_from_host_parasite_cou,
    assert_claim_allowed,
)
# clinical aliases raise ConfigurationError
"
```

See `API_SKETCH.md`, `REQUIREMENTS.md`, `EXPERT_BRAINSTORM.md` (consensus MVP),
`PHASE1_REVIEW.md`, `PHASE2_REVIEW.md`, `PHASE3_REVIEW.md`, `CITATIONS.md`, and `README_FA.md`.

## Honest limits

- Infection / transmission physics are **not** implemented.
- A ClaimGate grade is a **claim ceiling**, not wet-lab or clinical validity.
- FDA 2023 CM&S / ASME V&V 40 language may appear only as **declared COU risk
  labels**, same stance as the biomedical port — not clearance.
- Untracked junk under `src/codontrace/genesis/population/` is out of scope
  and must not be committed with this work.

Evidence comparator notes: `docs/claimgate/host_parasite_port_20260924/evidence/`.

## Brainstormed mode table (Waves 1–4)

| Mode / arm | Status | Where exercised |
|---|---|---|
| `horizontal` | delivered + digest | env + Phase 14 contrast |
| `vertical` | delivered + digest | env + Phase 14 contrast |
| `mixed` (blends H+V) | delivered + digest | env + Phase 14 contrast |
| `well_mixed` | delivered + digest | Phase 5/8 continuum |
| `local_neighborhood` | delivered + digest | Phase 5/8 continuum |
| continuum `interaction_value` | delivered + digest | Phase 8 + Phase 15 genome cross |
| `freeze_parasites` | delivered + digest | Phase 7/10 |
| `replay_parasite_schedule` | delivered + digest | Phase 7/10 |
| `reciprocal_coevolution` | delivered + digest | Phase 7/10 |
| dual-null content/structure/abiotic | delivered + digest | Phase 4/11 |
| `hgt_analogue_segment_copy` | delivered + digest | Phase 12 |
| `hgt_analogue_noise_transfer` | delivered + digest + menu | Phase 12/14 |
| `intracellular_seat_constraint` | delivered + digest | Phase 12 |
| `free_living_horizontal_inject` | delivered + digest | Phase 12 |
| genome × VT × spatial × continuum | delivered + digest | Phase 15 |
| virulence/resistance quality proxies | delivered + digest | Phase 16 (`virulence_optimized_for_humans` blocked) |
| Price≠causality refusal | delivered + digest | Phase 17 (`major_transition_proved` blocked) |
| journal attach-registry soft-complete | delivered + digest | Phase 18 (hygiene; no ladder rise) |
| ARD→FSD transition + cost-of-generalism | delivered + digest | Phase 19 (`red_queen_proved` blocked) |
| resource × dynamics factorial | delivered + digest | Phase 20 (Lopez Pascua honesty) |
| multi-seed contingency (S1) | delivered + digest | Phase 21 (`complexity_emergence_proved` False) |
| sequential Cornish multi-intervention | delivered + digest | Phase 22 (obs≠intervention) |
| Scanlan mutator / abiotic dual-null | delivered + digest | Phase 23 (`gene_identity_proved` False) |
| bacteria/cell DomainProfiles | refused | one `host_parasite` profile only |
| wet HGT / conjugation / CRISPR genetics | refused | flags always false |
| infection physics in `engine.py` | refused | engine untouched |

