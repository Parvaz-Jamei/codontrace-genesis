# HE03 mutational specialization — design brainstorm (pre-build)

Product: CodonTrace Genesis. Date: 2026-09-24 (Asia/Tehran).
Queue step (1) continuation after pilot_v1 FAIL (ablation wrong-signed).
Ordinary research design prose. Does not unlock claims.

## Literature (searched before coding)

| Citation | DOI | Use |
|---|---|---|
| Goldsby, Dornhaus, Kerr, Ofria (2012) PNAS 109:13686–13691 | 10.1073/pnas.1202233109 | Switch costs → evolved specialists via mutation+selection; isolation loss of autonomy |
| Gorelick et al. (2004) Am Nat 164:677–682 | 10.1086/424968 | D_sym / NMI measurement |
| Goldsby et al. (2014) PLOS ONE | 10.1371/journal.pone.0102713 | Multi-lineage specialists from mutation during replication |
| Dolson et al. MODES | 10.1162/artl_a_00280 | Comparator only; no modes_passed |

Competitor code reviewed: Phase K `run_goldsby_cpu_delay_specialist_campaign` (ISA analog);
prior HE03 dual-task overlay (PR #62).

## Pilot_v1 failure diagnosis

1. **Measurement asymmetry:** cost arms folded switch-record endpoints into the
   individual×task matrix (from_task + to_task), diluting D_sym. channel_off
   used traces only → higher D_sym → wrong-signed ablation.
2. **Ecology collapse:** basal 1.2 ATP extinguished populations by ~tick 5,
   leaving almost no mutational specialization time.
3. **Isolation bug:** solo retests rebuilt dual ancestral genomes instead of
   carrying evolved survivor genomes; ATP solo > group from food monopoly.
4. **Mechanism gap:** dual genomes were substrate enablement, not evolved
   specialists under switch cost (Goldsby’s actual causal path).

## Four experts

### Expert A — Digital-evolution empiricist
Goldsby needs mutation + selection under switch cost, then measure DoL.
Keep ancestral dual founders; raise HE03-only mutation; cushion metabolism so
lineages persist long enough for specialists to appear. Do not plant A/B halves.

### Expert B — ClaimGate auditor
Fixing sampling bias is mandatory honesty, not a soft-pass. Ablation must be
right-signed on the *same* task ecology. Keep decision rule refuse-closed unless
Holm + sign clear on research scale. CI candidate stays refused.

### Expert C — Measurement
Gorelick samples must come from activity traces classified by the same
TASK_A/B lexicon for every arm. Switch records stay for switch_count /
cost_realized only.

### Expert D — Cross-field innovator
Secondary IsolationAssay should score **genetic task-autonomy loss** relative to
the ancestral dual repertoire (Goldsby “cease to perform tasks”), not raw ATP
under food monopoly. Carry evolved genomes into solo retests.

## Critique wave 1 (pre-build)

1. Reject planting half-population EMIT specialists.
2. Reject loosening ClaimGate / inventing research results_v1.
3. Reject changing default life_loop_world pins (HE03 overlay only).
4. Accept HE03-only ecology cushion + mutation rate as mechanism enablement,
   documented as pure-Python scale analog — not Avida update counts.

## Locked slice

1. Trace-only Gorelick samples (all arms).
2. HE03 mutational specialization overlay: higher bit-flip, lower basal,
   modest food cushion, slightly longer pilot ticks.
3. Isolation: carry last non-empty evolved genomes; score ancestral-relative
   genetic task width (drop ≥0 when specialists evolve).
4. Re-run pilot; document positive and negative; refuse CI unless rules clear.
5. BAIC pins byte-identical; life-loop digests unchanged.

## Critique wave 2 (pre-build, after lock)

- cost_0 and channel_off may remain near-tied on D_sym (neither charges ATP);
  ordinal gate is cost_0 ≤ moderate ≤ high — channel_off is ablation, not ordinal.
- Genetic isolation drop can be zero if no specialists evolve — that is an
  honest null, not a soft-pass.
- Pilot remains exploratory (n=10); research still deferred.
