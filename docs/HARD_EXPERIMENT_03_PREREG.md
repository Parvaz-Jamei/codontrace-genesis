# HARD_EXPERIMENT_03_PREREG (draft lock 2026-09-17)

Date: 2026-09-17. Repo: Parvaz-Jamei/codontrace-genesis @ main.
Status: **PREREG BEFORE CODE** — do not implement `TaskSwitchCostConfig` / IsolationAssay / `gorelick_nmi` engine paths, and do not run a research campaign, until this file is hashed and committed.

Experiment id (planned): `hard_experiment_03_task_switch_dol` (E3).
Identity: `0.3.0b4.dev0`. Not a new Phase letter. Not a tag or PyPI release.
Pins A–E: untouched. ClaimGate: never loosened.

## Question
Do rising task-switching costs promote division of labor (Gorelick NMI on individual×task matrices) and loss of lower-level autonomy (IsolationAssay performance drop) relative to zero-cost controls, under default-off E3 knobs only?

## H1 / H0
- H1: higher `switch_cost_atp` (moderate / high) raises primary DoL metric (`D_sym` and/or preregistered directional NMI) vs cost=0, with IsolationAssay showing greater solo performance drop under high cost when group specialists evolved; ordinal pattern cost0 < moderate ≤ high on DoL.
- H0: no Holm-surviving contrast after correction; or manipulation checks fail (cost not realized / matrix degenerate) → `assay_invalid`; ceiling stays `runtime_observation`.

## Arms sketch (finalize counts in amendment if needed)
| Arm | Role | Intervention sketch |
|-----|------|---------------------|
| `cost_0` | control | `TaskSwitchCostConfig.enabled` with switch cost 0 (or off-equivalent baseline) |
| `cost_moderate` | treatment | switch cost ≈ Goldsby 25-cycle analogue (ATP units TBD in code PR) |
| `cost_high` | treatment | switch cost ≈ Goldsby 50-cycle analogue |
| `channel_off` / task-off baseline | mechanism ablation | dual-resource A/B tasks unavailable or switch cost path disabled |
| `isolation_probe` | secondary assay (not a primary contrast) | evolved genotypes from cost arms re-run solo; report isolation drop |

Dual resources A/B with distinct eat/task actions are required so switching is observable. Exact ATP mapping and resource schedules lock in the first code PR **after** this hashed prereg — not in this docs-only PR.

## Metrics (Gorelick 2004 NMI / NME)
On individual×task probability matrix \(p(x,y)\):
- \(I(X;Y)\) mutual information
- \(D_{task} = I(X;Y)/H(Y)\)
- \(D_{indiv} = I(X;Y)/H(X)\)
- \(D_{sym} = I(X;Y)/\sqrt{H(X)H(Y)}\) (symmetric; primary candidate)

Planned module path (future code PR only): `codontrace.genesis.metrics.division_of_labor.gorelick_nmi`. Any non-NMI DoL proxy stays labeled **legacy** and is not confirmatory.

## IsolationAssay (Goldsby-style)
Re-run evolved specialists alone in a single-individual environment; report performance drop vs group context. Isolation drop is a **secondary** confirmatory readout of lost lower-level autonomy — not a license for `collective_intelligence*` claims.

## Seeds / scale
- Pilot only: 1000–1009 (calibration / smoke; garden-of-forking-paths fence)
- Analysis / research: disjoint seeds (HE01-style 11–40 or 30 research seeds); never reuse pilot for confirmatory contrasts
- Smoke in CI; research outside CI with committed `results_v1.json` when code exists
- Pure-Python scale is **not** claimed to match Avida / Goldsby update counts (E7 ceiling)

## Decision rule
- Holm over ≤3 primary contrasts among cost arms on the locked primary DoL metric (paired where applicable).
- Manipulation checks must pass (switch events incur cost when enabled; matrices non-degenerate; cost_0 ≠ cost_high intermediate records).
- IsolationAssay reported always; used as supporting pattern, not a solo claim escalator.
- ClaimGate ceiling at most `intervention_supported` if all CLAIMS.md §5 flags met — **never invent labels**; default ceiling `runtime_observation`.
- Forbidden: `collective_intelligence*`, intelligence / AGI aliases, Phase letter bump, pin A–E changes, ClaimGate loosening.

## Knob template (for later code PR — not this PR)
Every new config: frozen dataclass `slots=True`, `enabled=False`, `ConfigurationError` in `__post_init__`, `to_dict` non-defaults only, `canonical_digest`, one DAG edge, pin+runtime tests. **This PR adds zero `src/` code.**

## Non-goals / hard bans (this PR)
- No `TaskSwitchCostConfig` / IsolationAssay / `gorelick_nmi` implementation.
- No HE02 conflict paths (`hard_experiment_02*`, FoodPatchSignal*, DemeSelection*, SteppingStone*, HE02 ClaimGate adapter, CLAIMS.md HE02 sections).
- No new-goal / ASAL / LLM / ESP32 content.
- No tag / PyPI.

## Literature anchors
- Goldsby, Dornhaus, Kerr, Ofria (2012). Task-switching costs promote the evolution of division of labor and shifts in individuality. *PNAS* 109(34):13686–13691. doi:10.1073/pnas.1202233109
- Gorelick, Bertram, Killeen, Fewell (2004). Normalized mutual entropy in biology: quantifying division of labor. *Am Nat* 164:677–682. doi:10.1086/424968

See also short brief: `docs/hard_experiment_03/HE03_SCIENCE_BRIEF.md`.


## Document digest
`sha256:30cc3e914269e41707da5dd829d2dbe6e9e86fc30387dcb929b069fb0737c81f`
