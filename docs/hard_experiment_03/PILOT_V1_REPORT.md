# HE03 pilot v1 — task-switch → DoL → ablation → isolation

Product: CodonTrace Genesis. Date: 2026-09-24 (Asia/Tehran).
Artifact: `docs/hard_experiment_03/pilot_v1.json`
Campaign digest: `5fc131a99cc6f399bd82c454770192329f5b90145251d0eb7faecd98191a2597`
File SHA-256: `1788b0c56420f673d280a9247324ebd5af422779b7aca4392ebbb1efe203b482`

## Design (locked slice)

Dual-action life-loop overlay (EAT_LUMEN = TASK_A, EMIT_NEXUS = TASK_B) with
persisted `last_task_class` so Goldsby-style switch costs can charge across
ticks. Arms: cost_0 / cost_moderate (0.25 ATP) / cost_high (0.50 ATP) /
channel_off / isolation_probe. Primary metric: Gorelick D_sym. Scale: pilot
seeds 1000–1009, 16 ticks, population 8.

Literature: Goldsby et al. 2012 *PNAS* doi:10.1073/pnas.1202233109;
Gorelick et al. 2004 *Am Nat* doi:10.1086/424968.

Dual-action genomes **enable** switching; they are **not** evolved specialists.

## Arm means (n = 10)

| Arm | mean D_sym | mean switches | mean isolation drop |
|---|---:|---:|---:|
| cost_0 | 0.0222591281 | 10.1 | — |
| cost_moderate | 0.0254163808 | 8.1 | — |
| cost_high | 0.0254163808 | 8.1 | — |
| channel_off | 0.0455191111 | 0.0 | — |
| isolation_probe | 0.0254163808 | 8.1 | **−0.93675** |

Ordinal gate cost_0 ≤ moderate ≤ high: **pass**. Assay: **pass** (non-degenerate
matrices; switch costs realized on moderate/high).

## Paired Holm contrasts on D_sym

| Contrast | mean Δ | dz | 95% CI | p_Holm | directional OK |
|---|---:|---:|---|---:|---|
| cost_high − cost_0 | +0.003157 | 1.489 | [0.000958, 0.003778] | 0.015625 | yes |
| cost_moderate − cost_0 | +0.003157 | 1.489 | [0.000958, 0.003778] | 0.015625 | yes |
| cost_high − channel_off | **−0.020103** | −4.908 | [−0.021809, −0.017148] | 0.005859 | **no** |

## Decision / ClaimGate

- `claim_ceiling`: `runtime_observation`
- `decision_rule_passed`: **False**
- Failures: `ablation_contrast_wrong_sign_or_null`, `scale_not_research`,
  `collective_intelligence_candidate_refused`
- `collective_intelligence` / `collective_intelligence_candidate`: **REFUSED**
- `intelligence` / `agi` / `tokyo_type1_passed` / `modes_passed`: False
- Research `results_v1.json`: **not** committed (deferred)

## Honest scientific reading

1. **Positive (narrow):** under this dual-action overlay, raising switch cost
   from 0 to moderate/high slightly raises D_sym vs cost_0 (Holm-surviving,
   positive). This is a measurement-layer cost→DoL *hint*, not the PNAS
   experiment and not evolved DoL.
2. **FAIL (mechanism ablation):** channel_off mean D_sym (0.0455) **exceeds**
   cost_high (0.0254). Disabling the cost knob does not collapse DoL relative
   to high cost — opposite of the intended causal story. Decision rule refuses.
3. **FAIL (isolation secondary):** mean isolation drop −0.93675 (solo ATP >
   group). Not Goldsby-style loss of lower-level autonomy.
4. **CI candidate:** refused — heldout partners, non-capsule cooperation,
   ClaimGate ablation flags, and evolved (not seeded) specialists remain unmet.

## BAIC pins (byte-identical)

- `results_v7.json` → `35bb593604438797755e5e7b28af4d1371992a6181a403d08005f7f45421cbd6`
- `risk_bar.json` → `4dbe4aa3a6ef8e771f180d2a6589c64b0dd5ffebe0aa73703a7256c17d771cd7`
- `biomedical_study.json` → `9685f2fbafb21477d977dfa0c0bf73e02bea81d084e7605978ea25c47bf5ddce`

Phase A life-loop digests unchanged when HE03 knobs are off.

## Next queue step

Stay on step (1) until ablation is honest (cost_high D_sym > channel_off) and
isolation drop is non-negative under high cost on a research-scale run — or
document a confirmed null. Do **not** skip to earning `collective_intelligence_candidate`.
Suggested deepening: longer-horizon evolution under switch cost (mutation +
selection on dual-action genomes) before Goldsby-grade group work (queue step 3).
