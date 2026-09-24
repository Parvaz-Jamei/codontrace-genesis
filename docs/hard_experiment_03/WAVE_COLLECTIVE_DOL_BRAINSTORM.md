# HE03 collective DoL slice — expert brainstorm (pre-build)

Product: CodonTrace Genesis. Date: 2026-09-24 (Asia/Tehran).
Queue step (1): task-switching → DoL → ablation → isolation multi-seed.
This document is ordinary research design prose. It does not unlock claims.

## Literature anchors (searched before action)

| Citation | DOI | Use |
|---|---|---|
| Goldsby, Dornhaus, Kerr, Ofria (2012) PNAS 109:13686–13691 | 10.1073/pnas.1202233109 | Task-switch costs → DoL + loss of lower-level autonomy |
| Gorelick, Bertram, Killeen, Fewell (2004) Am Nat 164:677–682 | 10.1086/424968 | Normalized mutual entropy / NMI for DoL |
| Goldsby, Knoester, Kerr, Ofria (2014) PLOS ONE | 10.1371/journal.pone.0102713 | Conflicting within/between deme pressures (MLS context) |
| Dolson et al. MODES (Artif Life) | 10.1162/artl_a_00280 | OEE metrics — comparator only; no `modes_passed` |
| Frontiers 2021 adaptive phenotypic plasticity | 10.3389/fevo.2021.715381 | Plasticity conditions; not a CI claim |
| Conlin et al. 2023 bioRxiv DoL/multicellularity | 10.1101/2023.03.15.532780 | Entrenchment / isolation context |

Competitor code reviewed at design time: `devosoft/avida` deme wiki; Empirical/MODES tracker docs; Phase K `run_goldsby_cpu_delay_specialist_campaign` (ISA analog, not Avida C++).

## Status before this wave

- HE01 `results_v7.json` is locked (BAIC pin). Capsule source-bias only. `collective_intelligence=False`.
- HE03 knobs exist (`TaskSwitchCostConfig`, `gorelick_nmi`, `IsolationAssay`) but smoke is **assay_failed**: matrices degenerate, switch cost never realized — life-loop genomes only fire `EAT_LUMEN` (TASK_A), never TASK_B; `last_task_by_organism` resets every `step_population`, so cross-tick switches cannot be charged even when both tasks appear.
- Research `results_v1.json` still absent (honest deferral).
- ClaimGate must refuse `collective_intelligence` / `collective_intelligence_candidate` until the full flag set is earned.

## Four experts

### Expert A — Digital-evolution empiricist (Goldsby/Avida line)
The PNAS design needs three ingredients we still lack on the life-loop overlay: (1) organisms that can export **two** task classes, (2) a **realized** switch-cost charge across ticks, (3) multi-replicate DoL + isolation. Prefer deepening HE03 over inventing a Phase letter. Do **not** assign round-robin roles and call it evolved DoL.

### Expert B — Causal / ClaimGate auditor
HE01's strength is paired Holm + dual-null discipline. HE03 currently hardcodes `holm_contrasts_not_cleared` without computing contrasts — that is documentation theater. Ship real paired contrasts on `d_sym`, keep ceiling at `runtime_observation` unless manipulation checks and Holm survive on a committed artifact. IsolationAssay is secondary only.

### Expert C — Measurement / information-theory
Gorelick D_sym is confirmatory only on a non-degenerate individual×task matrix. First clear assay_invalid by producing both TASK_A and TASK_B samples. Channel_off (knob disabled) is the mechanism ablation. Report ordinal cost0 ≤ moderate ≤ high as a **gate**, not a soft pass.

### Expert D — Interdisciplinary innovator
Bridge HE03 substrate honesty with Phase K's CPU-delay specialist *measurement* without claiming the PNAS experiment. Dual-action genomes + persisted last-task is the minimal causal patch. Keep MODES/Tokyo/CI aliases blocked. Differentiation remains ClaimGate / causal audit, not another evolution engine.

## Critique wave 1 (pre-build)

1. **Soft-pass risk:** seeding half the population as pure EMIT specialists would manufacture DoL without switches. Rejected — seed **dual-action** genomes so individuals can switch; specialization must be measured, not planted.
2. **Pin risk:** mutating default `life_loop_world` genomes would break Phase A–E digests. Rejected — HE03 overlay only via `build_hard_experiment_03_spec` + organism runtime field omitted from digest summaries when unused.
3. **CI soft-read:** positive isolation_drop alone must not print `collective_intelligence_candidate`. Adapter and claim evaluators stay refuse-closed.
4. **Scope creep:** full 50-replicate Avida-scale research is out of this PR. Land a **pilot** multi-seed with honest assay status; research `results_v1` only if pilot clears and wall-clock allows.

## Locked slice (ONE)

**HE03 dual-task persistence + paired Holm pilot:**
1. Persist last classified task on the live organism across ticks (clone-safe).
2. HE03 overlay: dual-action genomes + nexus stigmergy so TASK_A (`EAT_LUMEN`) and TASK_B (`EMIT_NEXUS`) both fire.
3. Compute paired Holm contrasts on `d_sym` (cost_high vs cost_0, cost_moderate vs cost_0, cost_high vs channel_off).
4. Run multi-seed pilot (seeds 1000–1009), commit `pilot_v1.json`, keep research deferred unless gates clear.
5. IsolationAssay remains secondary; ClaimGate refuses CI candidate.

## Critique wave 2 (pre-build, after slice lock)

- Dual genomes are still **substrate enablement**, not evolved specialists — prose must say so.
- Pilot N may be underpowered vs Goldsby n=50; label exploratory.
- If assay still fails after the persistence fix, commit the failure artifact (HE01 honesty pattern) rather than fabricating DoL.
