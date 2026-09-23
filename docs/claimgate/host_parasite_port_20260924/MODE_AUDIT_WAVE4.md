# Mode audit — Wave 4 (host–parasite)

**Purpose:** Inventory every brainstormed transmission / spatial / intervention /
arm mode from Waves 1–3 docs against code under `src/codontrace/genesis/host_parasite*.py`
and ClaimGate adapters + tests. Wave 4 must not leave modes as stubs or docs-only.

**Sources audited**

- `DEPTH_BRAINSTORM.md` (Phases 4–6)
- `DEPTH_BRAINSTORM_WAVE2.md` (Phases 7–9)
- `DEPTH_BRAINSTORM_WAVE3.md` + `DEPTH_BRAINSTORM_GENOME_CELL.md` (Phases 10–13)
- `EXPERT_BRAINSTORM.md` (modes / knobs only)

**Legend:** ✓ solid (digest + tests + attach where applicable) · ◐ thin (code
exists but gap) · ✗ missing · ∅ refused with reason

---

## Master table

| Mode / arm | Brainstorm source | Implemented? | Digest + tests? | Gaps |
|---|---|---|---|---|
| `horizontal` transmission | DEPTH Ph5; EXPERT | ✓ env | ✓ phase5 / env tests | No dedicated mode-contrast campaign digest until Wave 4 Ph14 |
| `vertical` transmission | DEPTH Ph5; EXPERT | ✓ env | ✓ phase5 | Same — unit-tested blend gates; campaign digest thin |
| `mixed` (must blend H+V) | DEPTH Ph5 **explicit** | ✓ env (`try_horizontal_inject` + `replicate_host`) | ✓ `test_mixed_mode_blends_*` | Snapshot flag only; no ClaimGate attach of three-way mode digests (Ph14) |
| `well_mixed` spatial | DEPTH Ph5; WAVE2 Ph8 | ✓ env + continuum | ✓ phase5/8 | Solid |
| `local_neighborhood` spatial | DEPTH Ph5; WAVE2 Ph8 | ✓ env + continuum | ✓ phase5/8 | Solid |
| continuum `interaction_value` ∈ [-1,+1] | WAVE2 Ph8; EXPERT | ✓ env + continuum factorial | ✓ phase8 + attach | Repertoire-level only; genome cross-factorial missing (Ph15) |
| `freeze_replay_parasites` (legacy single arm) | DEPTH Ph4 | ✓ campaign | ✓ phase4 | Superseded by three-arm Zaman; kept for continuity |
| `freeze_parasites` | WAVE2 Ph7; WAVE3 Ph10 | ✓ zaman + genome_zaman | ✓ phase7/10 + attach | Solid |
| `replay_parasite_schedule` | WAVE2 Ph7; WAVE3 Ph10 | ✓ | ✓ phase7/10 | Solid (schedule-bound digest-of-trajectory) |
| `reciprocal_coevolution` | WAVE2 Ph7; WAVE3 Ph10 | ✓ | ✓ phase7/10 | Solid |
| dual-null content / structure / abiotic | DEPTH Ph4; WAVE3 Ph11 | ✓ campaign + genome_diversity | ✓ phase4/11 | Solid |
| ARD-like / FSD-like / mixed diagnostics | DEPTH Ph5 | ✓ diagnostics | ✓ phase5 + attach | Labels only; `red_queen_proved=False` |
| VT × spatial factorial | WAVE2 Ph8 | ✓ continuum | ✓ phase8 + attach | No genome digests on cells (Ph15) |
| Cornish observational vs interventional | WAVE2 Ph9 | ✓ cornish | ✓ phase9 + attach | Solid |
| evolvability falsification | WAVE2 Ph9 / S5 | ✓ evolvability | ✓ phase9 | Solid |
| codon-entropy / Hamming dual-null | WAVE3 Ph11 | ✓ genome_diversity | ✓ phase11 | Solid |
| `hgt_analogue_segment_copy` | WAVE3 Ph12 | ✓ hgt | ✓ phase12 + attach | Solid |
| `hgt_analogue_noise_transfer` | WAVE3 Ph12 dual-null | ✓ hgt campaign | ✓ phase12 digests | ◐ **Not** in `DECLARED_INTERVENTION_KINDS` (Ph14 harden) |
| `intracellular_seat_constraint` | WAVE3 Ph12 | ✓ hgt | ✓ phase12 | Solid |
| `free_living_horizontal_inject` | WAVE3 Ph12 | ✓ hgt | ✓ phase12 | Solid |
| declared task–gene map | WAVE3 Ph13 | ✓ task_gene | ✓ phase13 | Solid; gene_identity unproved |
| Genome × (VT × spatial × continuum) | implied WAVE2×WAVE3 | ✗ | ✗ | **Ph15** |
| virulence / resistance *quality* proxies (Gandon S7) | CHALLENGES S7; EXPERT | ✗ (only range ARD/FSD) | ✗ | **Ph16**; `virulence_optimized_for_humans` stays blocked |
| Price≠causality refusal assay (Okasha S8) | CHALLENGES S8; REQUIREMENTS | ◐ worksheet only | ◐ phase3 honesty | Digest-backed refusal assay thin → **Ph17 optional** |
| bacteria / cell DomainProfiles | GENOME_CELL | ∅ refused | — | One profile `host_parasite` only |
| wet HGT / conjugation / CRISPR genetics | WAVE3 hard non-goals | ∅ refused | — | Flags always False |
| infection physics in `engine.py` | all waves | ∅ refused | — | engine untouched |

---

## Priority verification notes

### Mixed transmission actually blends H+V

`HostParasiteEnv.replicate_host` fires vertical when mode ∈ {vertical, mixed}
and draw < VT probability. `try_horizontal_inject` is blocked only when mode
is `vertical`. Mixed keeps both paths. Unit tests assert this. **Gap:** no
canonical three-mode campaign digest proving pairwise-distinct
horizontal / vertical / mixed outcomes for ClaimGate attach (Wave 4 Phase 14).

### Phase 12 four arms

All four arms run, emit distinct arm digests and transfer digests, dual-null
falsifies “any transfer raises diversity,” attach requires prereg and refuses
wet claims. **Gap:** noise-transfer kind missing from declared intervention
menu frozenset.

### Zaman three arms + continuum × VT × spatial + dual-nulls

Delivered and tested. Genome layer on Zaman is Phase 10. Continuum still
repertoire-score based — genome observables on the factorial grid are Wave 4
Phase 15.

### Mode × ClaimGate attach digests

Most campaign suites have attach_*. Transmission-mode trio and virulence-quality
diagnostics do not until Wave 4.

---

## Wave-4 hardening targets (from this audit)

1. **Phase 14** — Mode-completeness: register noise-transfer on menu; transmission
   mode-contrast digests + attach; soft-complete README mode table; audit tests
   that every brainstormed keep-mode is exercised.
2. **Phase 15** — Genome × (VT × spatial × continuum) factorial digests.
3. **Phase 16** — Virulence / resistance quality proxies as labeled diagnostics;
   `virulence_optimized_for_humans` still blocked.
4. **Phase 17 (optional)** — Multilevel caution digests / Price≠causality refusal
   assay; never prove major transition.

Audit complete before Wave-4 brainstorm lock.
