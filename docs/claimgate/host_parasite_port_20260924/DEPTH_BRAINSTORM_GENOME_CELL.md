# Depth brainstorm — genome × cell / microbe / bacteria (2026-09-24)

**CodonTrace Genesis** already ships cell genomes, codon tables, structural
mutation digests, and a delivered host–parasite ClaimGate port (Phases 1–9).
This workshop asks whether bacteria / microbe / cell topics deserve new
`DomainProfile`s, infection-in-engine physics, or only thin genome-aware
protocols under the existing `host_parasite` profile.

Differentiation stays claim-gating and causal audit — not another evolution
engine. Citations are limited to verified DOIs (repo `CITATIONS.md`, evidence
notes, or session-checked primary sources). No invented DOIs.

---

## 0. Locked lean (opening position)

Unless Expert C produces a claim set that *cannot* live under `host_parasite`:

1. Keep **one** `host_parasite` DomainProfile.
2. Treat **cell** as the domain-agnostic Genesis substrate that already carries
   genomes.
3. Treat **bacterium / microbe** as COU labels and assay-pack vocabulary on that
   same profile — not taxonomic theater.
4. Prefer Wave-3 = genome-aware digests + HGT-analogue protocol + dual-genome
   freeze/replay — **not** new DomainProfiles, not BAIC pin edits, not
   `engine.py` infection physics.

The five expert rounds below force disagreement; the closing LOCKED section
records what survived.

---

## 1. Codebase map (what Genesis already is)

### 1.1 Genome APIs

| Surface | Where | What it is |
|---|---|---|
| `SemanticGenome` | `src/codontrace/genome.py` | Immutable codon sequence + `GenomeSpec`; `from_codons` / `from_compact` / `random`; `digest()` (SHA-256 over canonical JSON including spec) |
| `GenomeSpec` | `src/codontrace/specs.py` | Alphabet + codon width (binary3 default; DNA/ternary/custom without source edits) |
| `Codon` / `CodonTable` | `src/codontrace/codon.py` | Action vocabulary; longest-match; `extend`/`replace`; minimal / genesis_v0 / toolchain tables |
| Structural mutation | `src/codontrace/genesis/structural_mutation.py` | `GenomeProgram`, insert/delete/duplicate/invert/translocate, digests, bloat guards |
| Diversity metrics | `src/codontrace/metrics/diversity.py` | `unique_genome_count`, `mean_genome_distance`, `codon_usage_entropy`, `genome_length_distribution` |
| Engine child records | `src/codontrace/engine.py` | `child_genome_records`, structural-mutation digests in run summaries |
| Mutation helpers | `src/codontrace/mutation.py` | Library-first mutation utilities (not infection) |

**Gap vs host_parasite today:** Phases 1–9 campaigns use **repertoire analogues**
(task-set cardinality, retained-CPU trajectories) more than raw
`SemanticGenome.digest()` / codon entropy / Hamming distance. Genomes exist in
the substrate; the port has not yet made them first-class *observables* with
dual-null and freeze/replay wiring.

### 1.2 What a “cell” already is in Genesis

- **World cell / custom cell markers:** `World2D.custom_cells` +
  `set_custom_cell` / `get_custom_cell` (`world.py`, `recorder.py`). Metadata
  markers on grid positions — not wet biology, not bacterial taxonomy.
- **Element cell / substrate:** `ElementCell`, `SubstrateRule`, Genesis
  substrate physics (`genesis/substrate.py`). Domain-agnostic ALife world
  chemistry/rules.
- **Organism / agent:** `WhiteBoxAgent` and `GenesisOrganism` execute a
  `SemanticGenome` through a `CodonTable` under ATP constraints. The “cell” in
  practice is an energy-bounded genome-executing agent, not a prokaryotic
  species pack.
- **Capsules:** `genesis/capsule.py` — stigmergic / causal-capsule transfer
  scaffolding. Explicitly does **not** prove knowledge transfer or infection.
  Useful as an ambient *payload channel* comparator for future HGT-analogue
  protocols (label carefully; do not call it conjugation).

**Honest mapping:** Genesis “cell” = genome-bearing digital organism + world
substrate. It is already the right abstraction for host and parasite roles.
Splitting a `cell` DomainProfile would duplicate the substrate without adding
claim ladders.

### 1.3 What `host_parasite` already covers as microbe analogy

Delivered on branch `feat/host-parasite-module-phases` (Phases 1–9):

- Fail-closed `HOST_PARASITE` profile (`claimgate/domain.py`): blocks phage
  therapy, BSL, clinical pathogen, vaccine, CRISPR identity, intelligence,
  proved Red Queen, proved major transition, Avida-replacement, etc.
- Thin adapter (`adapters/host_parasite.py`): COU risk labels, declared
  intervention menu, campaign attach, honesty gates — **no** tick-semantics
  change.
- Optional `HostParasiteEnv` outside `engine.py`: task-overlap infection
  analogue, steal fraction, dual-null template.
- Campaign suite: multi-seed digests; Zaman freeze / replay / reciprocal
  (repertoire richness); continuum + VT×spatial; evolvability falsification;
  Cornish observational-vs-interventional refusal; HE_HP locked digests.

README scope lock already states: no separate DomainProfiles for bacteria /
archaea / wet-lab cells; CRISPR genetics and infection-in-engine stay out of
scope. This brainstorm builds **on top** of that soft-complete stance.

### 1.4 Biomedical vs host_parasite ClaimGate pattern

Both are ports: label claims, refuse blocked aliases, declare COU risk, wrap
score/campaign tables. Neither is a second engine. Adding `bacteria` or `cell`
profiles would be taxonomy spam unless a *distinct blocked-claim / limitation
set* is required — Expert C’s test below.

---

## 2. Literature grounding (verified DOIs only)

### 2.1 Digital evolution / repertoire / freeze–replay

1. **Zaman et al. 2014** — Coevolution drives complex traits and promotes
   evolvability. *PLOS Biology*.
   doi:[10.1371/journal.pbio.1002023](https://doi.org/10.1371/journal.pbio.1002023)
   → Freeze/replay/reciprocal already ported as repertoire arms; genome
   contingency-loci *analogy* is still under-used (digest-level, not wet loci).

2. **Fortuna et al. 2021** — Ecological opportunity and complexity in digital
   organisms. *Frontiers in Ecology and Evolution*.
   doi:[10.3389/fevo.2021.750772](https://doi.org/10.3389/fevo.2021.750772)
   → Obligate parasites, ~CPU theft, task-overlap infection — env analogues.

3. **Fortuna et al. 2017** — Host–parasite network complexity / non-adaptive
   origins. *Phil. Trans. R. Soc. B*.
   doi:[10.1098/rstb.2016.0431](https://doi.org/10.1098/rstb.2016.0431)
   → Network digests already referenced in Phase 6 evidence notes.

4. **Gupta, Vostinar et al. 2021** — Symbiosis in digital evolution.
   *Frontiers in Ecology and Evolution*.
   doi:[10.3389/fevo.2021.739047](https://doi.org/10.3389/fevo.2021.739047);
   Symbulation Zenodo doi:[10.5281/zenodo.6380543](https://doi.org/10.5281/zenodo.6380543)
   → VT × spatial continuum already Phase 8; still repertoire/interaction-value,
   not dual genomes.

### 2.2 Empirical microbial / evolvability constraint

5. **Scanlan / Buckling line (2015)** — Genome-wide phage–bacteria coevolution
   constrains abiotic-beneficial mutations. *Mol. Biol. Evol.* 32(6).
   URL: https://academic.oup.com/mbe/article/32/6/1425
   (repo CITATIONS.md; Challenge S5 humility already in Phase 9 assay).

6. **Hall et al. 2011** / **Lopez Pascua et al. 2014** — ARD/FSD comparator
   diagnostics (see `evidence/hall_lopez_pascua_ard_fsd.md`).

### 2.3 Major-transitions caution (not a claim to prove)

7. **Okasha 2022** — Multilevel selection / major transitions framing.
   doi:[10.3389/fevo.2022.793824](https://doi.org/10.3389/fevo.2022.793824)

8. **Michod & Nedelcu 2003** — Fitness reorganization in major transitions.
   doi:[10.1093/icb/43.1.64](https://doi.org/10.1093/icb/43.1.64)

9. **Okasha & Otsuka 2020** — Price equation ≠ causality.
   doi:[10.1098/rstb.2019.0365](https://doi.org/10.1098/rstb.2019.0365)

`major_transition_proved` stays blocked. Genome modularity talk must stay
assay-level, never identity with wet transitions.

### 2.4 CRISPR–phage — external comparator only

10. Chabas / Westra line — doi:[10.1371/journal.pbio.3002122](https://doi.org/10.1371/journal.pbio.3002122)
11. CRISPR computational model — doi:[10.1371/journal.pcbi.1010329](https://doi.org/10.1371/journal.pcbi.1010329)
12. Punctuated CRISPR dynamics — doi:[10.1098/rsif.2024.0195](https://doi.org/10.1098/rsif.2024.0195)

Blocked: `crispr_identity_proved`, `crispr_therapy_validated`. Never implement
CRISPR genetics in Genesis to “match” these papers.

### 2.5 External framing for *why genomes matter* (not implementations)

13. **Mitchell & Cheney 2025** — The Genomic Code: the genome instantiates a
    generative model of the organism. *Trends in Genetics*.
    doi:[10.1016/j.tig.2025.01.008](https://doi.org/10.1016/j.tig.2025.01.008);
    preprint arXiv:2407.15908.
    → **EXTERNAL framing only.** Do **not** claim CodonTrace Genesis implements
    VAE genomes or developmental decoders.

14. **Waldegrave, Stepney & Trefzer 2025** — Cell division/differentiation with
    Developmental Graph Cellular Automata. ALIFE 2025.
    doi:[10.1162/isal.a.889](https://doi.org/10.1162/isal.a.889)
    → **Comparator only.** Graph-component “cells” ≠ Genesis organisms; no
    DGCA reimplementation planned.

### 2.6 Causal / V&V authority (unchanged)

15. Cornish et al. — Causal falsification of digital twins; JMLR 27(152) 2026 /
    arXiv:2301.07210.
16. FDA 2023 CM&S guidance; ASME V&V 40-2018 — COU risk *labels* only.

---

## 3. Three-expert brainstorm (5 rounds)

**Roles**

- **A — Digital evolution / ALife engineer** (Avida, Symbulation, JaxLife awareness)
- **B — Microbial / cell biologist** (wet bacteria vs microbe vs cell → honest digital maps)
- **C — ClaimGate / V&V / causal methodologist** (auditable ladders vs taxonomy spam)

**Core question:** Given Genesis already has cell genomes, should we
(1) keep one host_parasite microbe port, (2) add thin genome-aware protocols
under the SAME profile, or (3) split DomainProfiles for bacteria / cell —
and what *innovative* ClaimGate-auditable assays become possible *because*
genomes exist?

---

### Round 1 — Name the confusion honestly

**A:** Reviewers will ask “where is the genome?” after Zaman 2014. Task
repertoire is a good phenotype proxy, but Avida’s punchline was also
*genome* evolvability / contingency. Without genome digests on freeze/replay
arms, the port looks half-ported.

**B:** Wet language is three layers, not three engines:

| Wet concept | Honest Genesis map |
|---|---|
| **Cell** | Genome-executing organism + substrate (already exists) |
| **Microbe** | Ecological role / small free-living host–parasite context (COU label) |
| **Bacterium** | Optional prokaryote-flavored COU tag — **not** a species pack |

Intracellular vs free-living is a *compartment / transmission* story, not a
reason for a new profile. Plasmid-like payload transfer maps closer to capsule
or codon-segment copy than to “implement conjugation physics.”

**C:** Splitting `bacteria` and `cell` DomainProfiles without a distinct blocked
claim set is taxonomy theater. Profiles exist to fail-close dangerous aliases
and declare limitations. Cell substrate claims already sit under ALIFE /
engine-agnostic Genesis; microbial coevolution claims already sit under
`host_parasite`. Unless B can name a blocked alias that *must not* live on
either, do not split.

**Disagreement:** A wants genome observables soon; B wants vocabulary hygiene;
C refuses profile proliferation. No one wants infection-in-engine.

---

### Round 2 — What genomes uniquely unlock (innovation pressure)

**A:** Concrete assays that *require* genomes (repertoire alone cannot do these):

1. **Dual-genome freeze/replay** — freeze host genome digest, parasite genome
   digest, or both; replay schedules; reciprocal mutation allowed only when
   digests are live. Extends Zaman three-arm with genotype-level digests.
2. **Codon-entropy / Hamming dual-null** — content-null (shuffle codon symbols
   preserving length) vs structure-null (preserve codon multiset, break
   action map) as ClaimGate-labeled interventions on genome observables.
3. **Task–gene map digests** — optional map from codon windows → task labels as
   an *declared* phenotype link; refuse “gene identity proved.”

**B:** Horizontal gene transfer / plasmid analogue is scientifically interesting
*if and only if* labeled as digital payload exchange (codon-segment copy,
capsule-mediated transfer, or declared `hgt_analogue` intervention kind) —
never wet HGT, conjugation, or CRISPR spacer acquisition. Intracellular
parasite = parasite genome constrained to host spatial seat / vertical
co-copy; free-living = horizontal inject with independent genome evolution.
Same profile; different assay packs.

**C:** Approve only if each assay emits:

- preregistered metric,
- dual-null or abiotic control,
- canonical digest,
- explicit ceiling (`runtime_observation` / `candidate_evidence` until
  multi-arm falsification passes),
- no path to blocked claims.

Mitchell & Cheney (2025) may appear in docs as **why genomes matter** framing;
ClaimGate must never attach a “generative-model genome proved” grade.

**Disagreement:** A pushes task–gene maps; C wants them deferred until dual-
genome freeze/replay + entropy dual-null are digest-solid. B accepts HGT-
analogue only with harsh naming.

---

### Round 3 — Force the profile decision

**A:** One profile is fine *if* Wave-3 wires genome digests into existing Zaman /
evolvability / Cornish factories. A separate `bacteria` profile would not
change tick semantics anyway — so it is documentation cosplay.

**B:** Okasha / Michod caution: genome modularity and “major transition”
language must stay behind `major_transition_proved` block. Cell-as-substrate
vs bacterium-as-COU is the right split of *words*, not of *profiles*.

**C (overturn test):** Searched for a claim set that cannot live under
`host_parasite`:

| Hypothetical claim family | Why it fails the split test |
|---|---|
| Bacterial species pack / 16S identity | Not a ClaimGate concern; refuse as out of scope |
| Clinical bacteriology / AST | Already blocked via clinical / therapy aliases |
| Wet cell biology / organelle proof | Substrate claims stay ALIFE; do not need `cell` profile |
| Intelligence of microbes | Already blocked |

**Verdict this round:** Expert C does **not** overturn. Keep one profile.
Option (3) discarded unless future work invents a genuinely distinct blocked
set (none proposed here).

**Residual disagreement:** A still wants richer genomes/tasks in the env; C
insists audit protocols precede genome richness inflation (same tension as
Wave-1/2 brainstorms — keep it).

---

### Round 4 — Discard weak ideas; keep ClaimGate-honest ones

Evaluate the candidate directions from the brief:

| Idea | Keep? | Why |
|---|---|---|
| Genome-linked repertoire richness → codon/genome entropy + task–gene maps as observables with dual-null | **Keep (ranked)** | Closes the gap: campaigns use repertoire today; genomes already exist |
| HGT / plasmid-analogue as ClaimGate-labeled protocol | **Keep (thin)** | Innovative only as labeled digital transfer + digests; not wet HGT |
| Intracellular vs free-living as genome-compartment story without new profile | **Keep (pack)** | COU / assay axes on same profile |
| Cell as substrate vs bacterium as COU label | **Keep (locked vocab)** | Matches code + B’s wet map |
| Deepen Zaman arms with genome digests | **Keep (Wave-3 core)** | Literature-aligned; builds on Phase 7 |
| Separate `bacteria` / `cell` DomainProfiles | **Refuse** | Expert C finds no unique claim set; taxonomy theater |
| Infection physics in `engine.py` | **Refuse** | Hard constraint; HostParasiteEnv already outside core |
| CRISPR identity / therapy | **Refuse (blocked)** | Comparator papers only |
| Implement Mitchell–Cheney VAE genomes | **Refuse** | External framing; overclaim risk |
| Reimplement Waldegrave DGCA cells | **Refuse** | Comparator only |

---

### Round 5 — Lock recommendations + Wave-3 earn-in

**Shared diagnosis:** Phases 1–9 gave ClaimGate-auditable *repertoire* coevolution.
Genomes are the unused differentiator already inside CodonTrace Genesis.
Innovation = make genomes *auditable observables* under the same profile —
not rename the port “bacteria.”

**A:** Wave-3 must ship dual-genome freeze/replay before any “open-ended
microbial genomics” narrative.

**B:** Vocabulary lock in docs: cell = substrate; microbe/bacterium = COU /
assay labels; intracellular/free-living = transmission+compartment axes;
plasmid/HGT = analogue protocol names only.

**C:** Success criteria are digests + dual-null + prereg + fail-closed ceilings.
No BAIC pin edits; no `population/` junk; blocked claims unchanged.

---

## 4. Innovation shortlist (ranked)

1. **Dual-genome freeze / replay / reciprocal digests** — Why: extends Zaman
   2014 (doi:10.1371/journal.pbio.1002023) from task repertoire to host+parasite
   `SemanticGenome.digest()` schedules; only possible because Genesis genomes
   already exist.
2. **Codon-entropy / Hamming observables with dual-null** — Why: turns
   `codon_usage_entropy` / `mean_genome_distance` into ClaimGate-attached
   metrics with content-null vs structure-null, matching HE02-style honesty.
3. **HGT / plasmid-analogue protocol (ClaimGate-labeled)** — Why: thin additive
   intervention kind + digest of transferred codon segments; innovative as an
   *auditable* transfer story, not as wet microbiology.
4. **Intracellular vs free-living genome-compartment assay pack** — Why: same
   profile; varies seat constraint / VT co-copy vs horizontal inject; maps B’s
   wet distinction without taxonomy profiles.
5. **Declared task–gene map digests (optional, late)** — Why: bridges repertoire
   richness to codon windows; deferred until (1)–(2) are solid so maps cannot
   smuggle “gene identity proved.”

Honorable mention (docs-only): cite Mitchell & Cheney 2025 and Waldegrave et
al. 2025 as external comparators for “why cell genomes matter” / alternative
cell models — never as implemented features.

---

## 5. Non-goals (hard)

- New `bacteria` or `cell` DomainProfiles (taxonomy theater).
- Infection / transmission physics in `engine.py`.
- BAIC pin edits (`docs/hard_experiment_01/results_v7.json`,
  `docs/claimgate/risk_bar.json`, `docs/claimgate/biomedical_study.json`).
- Committing `population/` junk; AI/agent/LLM meta in committed docs.
- Unblocking: phage therapy, BSL, clinical pathogen, vaccine, antiviral,
  epidemic forecast, intelligence, proved Red Queen, proved major transition,
  CRISPR identity/therapy.
- Implementing CRISPR genetics, VAE genomes, or DGCA division physics.
- Claiming wet HGT, conjugation, or Speciation.

---

## 6. LOCKED recommendations

1. **One profile:** keep `host_parasite`. Do not split bacteria / cell.
2. **Vocabulary:** cell = Genesis genome substrate; microbe / bacterium =
   COU labels + assay packs under that profile.
3. **Build direction:** thin genome-aware protocols (option 2), not infection-
   in-engine and not DomainProfile sprawl (options 1+3 rejected as primary
   strategy — option 1 “status quo forever” rejected because genomes are
   unused; option 3 rejected by Expert C).
4. **Earn Wave-3** only for ranked ideas 1–4; idea 5 optional late.
5. **Paper safety:** additive docs/code only; pins untouched.

---

## 7. Proposed Wave-3 phases (earn-in)

Only ideas that survived Round 4. Titles + success criteria; implementation
is a later PR — this document does not implement them.

### Phase 10 — Genome-aware dual digests on Zaman arms

- Attach host and parasite `SemanticGenome.digest()` (or compact+spec digest)
  to freeze / replay / reciprocal campaign outcomes alongside existing
  repertoire summaries.
- Success: per-arm digests include genome digests; ClaimGate attach refuses
  ceilings above existing rules; repertoire fields remain for continuity;
  no engine infection physics.

### Phase 11 — Codon-entropy / Hamming dual-null assay

- Campaign arms that mutate or ablate genomes with content-null and
  structure-null controls; metrics from `codon_usage_entropy` /
  `mean_genome_distance` / `unique_genome_count`.
- Success: dual-null can falsify “parasites always raise genome diversity”
  (Scanlan/Buckling humility analogue at genotype level); digests locked;
  blocked claims unchanged.

### Phase 12 — HGT-analogue + intracellular/free-living pack (same profile)

- Declared intervention / arm kinds: `hgt_analogue_segment_copy`,
  `intracellular_seat_constraint`, `free_living_horizontal_inject` (names
  digital-scope only).
- Optional use of capsule or codon-segment copy as *payload channel* with
  digests — never branded as conjugation or wet HGT.
- Success: factorial digests under `host_parasite`; COU labels may say
  `microbe` / `bacterium_analogue`; no new DomainProfile; CRISPR remains
  comparator-only.

**No Phase for:** separate bacteria/cell profiles; task–gene maps as a
required Phase (optional after 10–11); Mitchell–Cheney implementation;
DGCA port.

---

## 8. Relation to prior depth docs

- `DEPTH_BRAINSTORM.md` / `DEPTH_BRAINSTORM_WAVE2.md` delivered Phases 4–9
  (campaign audit before genome richness). That ordering was correct.
- This document opens Wave 3 only because audit protocols now exist — genomes
  can be observables without becoming an unaudited toy.

---

## Persian one-liner

با وجود ژنوم سلول در CodonTrace Genesis، یک پروفایل `host_parasite` کافی است:
باکتری/میکروب برچسب COU است، نه DomainProfile جدا؛ موج ۳ = هضم ژنوم + پروتکل
HGT-مانند + freeze/replay دوژنوم، نه فیزیک عفونت در موتور.
