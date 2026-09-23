# Design workshop — Wave 3 (genome-aware host–parasite)

**Context:** Phases 1–9 merged on main (`d66f0db`). Genomes already exist in
CodonTrace Genesis (`SemanticGenome`, `GenomeProgram`, diversity metrics) but
host–parasite campaigns still speak mostly in repertoire analogues. This
workshop runs **two new innovation-focused rounds** (not a re-run of
`DEPTH_BRAINSTORM_GENOME_CELL.md`) before locking Wave-3 earn-in phases.

**Innovation bar:** ClaimGate-auditable protocols that *existing* genomes
uniquely enable — not taxonomy theater, not an Avida clone, not infection
physics in `engine.py`.

**Roles (same three experts)**

- **A — Digital evolution / ALife** (Zaman freeze–replay; schedule vs live)
- **B — Microbial / cell genome** (HGT / compartment honesty; COU labels)
- **C — ClaimGate / V&V** (dual-null, prereg, ceilings, blocked claims)

Starting proposals from `DEPTH_BRAINSTORM_GENOME_CELL.md` §7 (Phases 10–12;
idea 5 optional). Rounds below may refine, reorder, or add innovations.

---

## Shared diagnosis entering Wave 3

Delivered: fail-closed `host_parasite` profile; env outside engine; Zaman
three-arm repertoire; continuum + VT×spatial; evolvability falsification;
Cornish observational refusal; HE_HP locked digests; vocabulary lock (cell =
substrate; microbe/bacterium = COU labels; one profile).

Unused differentiator: `SemanticGenome.digest()`, `codon_usage_entropy`,
`mean_genome_distance`, `GenomeProgram` identity/provenance digests, and
structural codon-segment copy as a *labeled* payload channel.

---

## Round 1 — Force disagreement on Phase 10 shape

**A:** Phase 10 must make freeze ≠ replay ≠ reciprocal *at the genotype
digest level*, not only attach a static `SemanticGenome.digest()` beside
repertoire. Otherwise Wave 3 is taxonomy theater with SHA-256 stickers.

Concrete arm semantics A demands:

| Arm | Host genome | Parasite genome |
|---|---|---|
| `freeze_parasites` | mutates under pressure | **digest frozen at t0** |
| `replay_parasite_schedule` | mutates without reciprocal pressure | **precomputed digest schedule** (locked trajectory) |
| `reciprocal_coevolution` | mutates each step | **co-adapts** (codon flips each step) |

Also: layer genomes **on top of** repertoire — do not delete Phase 7 richness
fields. Continuity matters for ClaimGate attach diffs.

**B:** Accepts A's arm table. Adds: do **not** call frozen digests “contingency
loci” or “CRISPR spacers.” Optional docs may say *digest-level contingency
analogue* only. Intracellular/free-living wait for Phase 12.

**C:** Approves only if:

1. Per-arm digests include host+parasite genome digests **and** remain pairwise
   distinct for `candidate_evidence`.
2. `complexity_emergence_proved` / `red_queen_proved` stay False forever.
3. Prereg required before attach; ladder never rises.
4. No path that treats genome digest equality as wet identity.

**Disagreement:** A wants optional `GenomeProgram.identity_digest` as a second
observable (lineage/provenance). C allows it only as a **secondary field**
that never substitutes for `SemanticGenome.digest()` and never claims
structural-mutation = infection. B indifferent if naming stays digital.

**Round-1 refinement locked:** Phase 10 = layered dual-genome Zaman with
freeze/replay/reciprocal genotype semantics + repertoire continuity;
`GenomeProgram` digests optional secondary; complexity/RQ unproved.

---

## Round 2 — What genomes uniquely unlock beyond Phase 10 (innovation pressure)

**A — new assay ideas that repertoire cannot do:**

1. **Schedule-bound genome digest contingency** — replay arm stores a
   *digest-of-digest-trajectory* (canonical digest over the ordered parasite
   genome digests). Freeze has a singleton frozen digest; reciprocal has a
   live changing trajectory. This is the genotype-level Zaman contrast.
2. **Codon-entropy / Hamming dual-null** (Phase 11) — content-null (shuffle
   symbols, preserve length) vs structure-null (permute codon order, preserve
   multiset) vs intact biotic; can **fail**
   `parasites_always_raise_codon_entropy` under abiotic stress (Scanlan/
   Buckling humility at genotype level; HE02 honesty pattern).
3. **Segment-transfer dual-null** (feeds Phase 12) — structured codon-segment
   copy vs equal-length random-noise transfer; falsifies “any transfer raises
   host diversity.”

**B — HGT / compartment pack (Phase 12) refined:**

| Arm / factor | Digital meaning (labels only) |
|---|---|
| `hgt_analogue_segment_copy` | Copy a codon window host↔parasite; emit transfer digest |
| `intracellular_seat_constraint` | Parasite genome evolves only while seated; VT co-copy |
| `free_living_horizontal_inject` | Independent parasite genome + horizontal inject |

Same `host_parasite` profile. COU may say `microbe` / `bacterium_analogue`.
Never conjugation, wet HGT, plasmid identity, or CRISPR spacer acquisition.
Capsule channel may be cited as ambient comparator in docs — not branded as
HGT.

**C — refuse / keep table for Round 2 ideas:**

| Idea | Keep? | Why |
|---|---|---|
| Layered dual-genome Zaman (Round 1) | **Keep — Phase 10** | Genomes uniquely required |
| Schedule-bound digest-of-trajectory | **Keep (inside Phase 10)** | Makes freeze≠replay≠reciprocal genotype-auditable |
| Codon-entropy / Hamming dual-null + fail universal claim | **Keep — Phase 11** | HE02 honesty; Scanlan humility analogue |
| Segment-transfer dual-null | **Keep (inside Phase 12)** | Auditable transfer story |
| Intracellular vs free-living factorial | **Keep — Phase 12 pack** | Same profile; COU axes |
| Declared task–gene map digests | **Defer — Phase 13 optional** | Risk of “gene identity proved”; earn only after 10–12 |
| Separate bacteria/cell DomainProfiles | **Refuse** | Still no unique blocked-claim set |
| Infection in `engine.py` / CRISPR genetics / VAE genomes | **Refuse** | Hard non-goals |

**Disagreement resolved:** A wanted task–gene maps in Wave 3 core; C+B force
deferral until dual-genome + entropy dual-null are digest-solid. A accepts
Phase 13 earn-in only if 10–12 green and time remains.

**New innovation accepted (was soft in genome-cell doc):** schedule-bound
digest-of-trajectory + segment-transfer dual-null as first-class Wave-3
protocol pieces, not docs-only asides.

---

## LOCKED Wave-3 phase plan

### Phase 10 — Genome-aware dual digests on Zaman arms

- Layer host+parasite `SemanticGenome.digest()` onto freeze / replay /
  reciprocal arms with genotype semantics above; keep repertoire summaries.
- Emit schedule-bound parasite digest trajectory + digest-of-trajectory.
- Optional secondary `GenomeProgram` identity digest fields (never primary).
- ClaimGate attach + prereg; complexity/RQ unproved; ceiling max
  `candidate_evidence` when arms distinct.
- Tests: `tests/test_host_parasite_phase10.py`; `PHASE10_REVIEW.md` (2 rounds).

### Phase 11 — Codon-entropy / Hamming dual-null (HE02 honesty)

- Arms: intact biotic, content-null, structure-null (± abiotic stress).
- Metrics: `codon_usage_entropy`, `mean_genome_distance`, `unique_genome_count`.
- Must be able to **fail** `parasites_always_raise_codon_entropy`.
- Digests locked; blocked claims unchanged.
- Tests + `PHASE11_REVIEW.md` (2 rounds).

### Phase 12 — HGT-analogue + intracellular / free-living pack

- Declared digital-only kinds: `hgt_analogue_segment_copy`,
  `intracellular_seat_constraint`, `free_living_horizontal_inject`
  (extend `DECLARED_INTERVENTION_KINDS`).
- Segment-transfer dual-null (structured vs noise) + compartment factorial
  under the same profile.
- COU labels may include `microbe` / `bacterium_analogue`; no new DomainProfile.
- Tests + `PHASE12_REVIEW.md` (2 rounds).

### Phase 13 (optional earn-in) — Declared task–gene map digests

- Only if 10–12 solid and wall-clock allows.
- Declared codon-window → task-label map digests; refuse any “gene identity
  proved” language; never unblock CRISPR / major-transition claims.

### Hard non-goals (unchanged)

- New DomainProfiles; infection in `engine.py`; BAIC pin edits; `population/`
  junk; AI/agent/LLM meta in committed docs; wet HGT / conjugation / CRISPR
  identity / therapy; proved Red Queen / major transition / complexity.

---

## Relation to prior docs

- `DEPTH_BRAINSTORM_GENOME_CELL.md` locked one profile + ranked ideas 1–4.
- This Wave-3 workshop **refines** those ideas with genotype arm semantics,
  schedule-bound digest-of-trajectory, segment-transfer dual-null, and a
  stricter Phase-13 earn gate — then implementation proceeds on
  `feat/host-parasite-wave3-genome`.

## Persian one-liner

موج ۳: ژنوم‌های موجود را مشاهده‌پذیرِ قابل‌حسابرسی می‌کند (freeze≠replay≠reciprocal
در سطح digest؛ آنتروپی کدون با dual-null؛ HGT-مانند برچسب‌خورده) — نه پروفایل
باکتری جدا و نه فیزیک عفونت در موتور.
