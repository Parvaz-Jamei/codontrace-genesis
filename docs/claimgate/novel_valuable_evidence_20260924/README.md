# Novel valuable evidence — CodonTrace Genesis (2026-09-24)

**Product:** CodonTrace Genesis  
**Scope:** New evidence only. No `src/` edits. Pins untouched:

- `docs/hard_experiment_01/results_v7.json`
- `docs/claimgate/risk_bar.json`
- `docs/claimgate/biomedical_study.json`

Sibling additive pack (biomedical DomainProfile stress tests):
`docs/claimgate/applied_medical_evidence_20260924/`.

## What this is / is not

| Is | Is not |
|---|---|
| Cross-campaign ClaimGate portfolio (HE01 vs HE02) | A proof of collective intelligence |
| Honest fail of HE02 communication under content-null | Proof that HE02 “communicates” |
| Overclaim demotion when CI flags are forced | An AGI / Tokyo Type-1 pass |
| Risk-bar discipline applied to ALife claims | FDA clearance or ASME V&V 40 pass |
| Deterministic causal-replay smoke | A full Price causal decomposition paper |

## Literature problems (mapped)

1. **Price ≠ automatic causality** — A Price / covariance identity is statistical;
   a causal reading needs interventions and a DAG (Okasha & Otsuka 2020). N5
   checks that the library’s causal replay is deterministic under controlled
   perturbations; it does **not** turn a covariance into a causal law.
2. **When is a group a collective agent?** — Collective / multilevel claims need
   earned criteria; renaming extras must not promote the ladder (Michod-style
   individuality shifts are a research target, not a free label). N2 blocks
   `collective_intelligence` / `agi` aliases and **demotes** the audit when the
   forbidden flag is forced on HE02.
3. **Communication / DoL honesty** — Channel-off alone can look like a win;
   content-sensitive shuffled controls are required (Floreano et al. 2007;
   Knoester et al. 2008; HE02 prereg E1/E2). N3 encodes the committed HE02
   pattern: Holm survives vs `channel_off` / `content_null`, fails vs
   `capsules_shuffled` → `information_control_not_separated`.
4. **Task-switching / DoL ceiling** — Goldsby et al. 2012 is the authority for
   switch-cost driven division of labour; HE03 is the planned assay and is
   still empty on this tip (adapter only). This suite does **not** claim DoL.
5. **Reproducibility / claim–evidence mismatch** — Same auditor, different
   campaigns, different grades (Pineau et al. 2021 reproducibility culture;
   BioModels-style credibility pressure). N1 + N6.
6. **Commensurate evidence under risk** — Evidence must match stated model risk
   (FDA 2023 CM&S; ASME V&V 40). N4 applies the committed risk-3 bar to HE01
   (meets) vs HE02 level 2 (fails) without medical theater.

## Citations (primary)

- Okasha, S., & Otsuka, J. (2020). The Price equation and the causal analysis of
  evolutionary change. *Philosophical Transactions of the Royal Society B*,
  375, 20190365. https://doi.org/10.1098/rstb.2019.0365
- Floreano, D., Mitri, S., Magnenat, S., & Keller, L. (2007). Evolutionary
  conditions for the emergence of communication in robots. *Current Biology*,
  17(6), 514–519. https://doi.org/10.1016/j.cub.2007.01.058
- Knoester, D. B., McKinley, P. K., & Ofria, C. (2008). Cooperative network
  construction using digital germlines. *GECCO ’08*, 613–620.
  https://doi.org/10.1145/1389095.1389130
- Goldsby, H. J., Dornhaus, A., Kerr, B., & Ofria, C. (2012). Task-switching
  costs promote the evolution of division of labor and shifts in individuality.
  *PNAS*, 109(34), 13686–13691. https://doi.org/10.1073/pnas.1202233109
- Pineau, J., et al. (2021). Improving reproducibility in machine learning
  research (a report from the NeurIPS 2019 reproducibility program).
  *Journal of Machine Learning Research*, 22(164), 1–20.
- FDA (2023). *Assessing the Credibility of Computational Modeling and
  Simulation in Medical Device Submissions* (final guidance).
  https://www.fda.gov/media/175363/download
- ASME V&V 40-2018. *Assessing Credibility of Computational Modeling through
  Verification and Validation: Application to Medical Devices*.

Internal science briefs (same repo, not substitutes for the papers above):

- `docs/hard_experiment_02/HE02_SCIENCE_BRIEF.md`
- `docs/hard_experiment_02/analysis_v1b_contrasts.json`
- `docs/HARD_EXPERIMENT_01.md` (Okasha DAG section)
- `docs/HARD_EXPERIMENT_03_PREREG.md` (Goldsby switch-cost plan)

## Scientifically interesting HE02 pattern (from committed analysis)

From `docs/hard_experiment_02/analysis_v1b_contrasts.json` + `PILOT_REPORT.md`:

| Contrast | dz (approx.) | p_Holm (approx.) | Holm |
|---|---|---|---|
| treatment vs `channel_off` / `content_null` | 1.13 | 1.5×10⁻⁴ | survives |
| treatment vs `capsules_shuffled` | 0.20 | 0.37 | **fails** |

- `decision_rule_passed: false` (`information_control_not_separated`)
- Claim ceiling remains `runtime_observation`
- ClaimGate public grade: level 2 `candidate_evidence` (replay not verified)

**Reading:** a content-independent channel effect is **not** enough for an honest
communication claim under the Floreano/Knoester control logic built into HE02.

## Tests (N1–N6)

| ID | Result | Maps to |
|---|---|---|
| N1 | PASS | Same auditor: HE01 L4 `replicated_effect` (replay) vs HE02 L2 `candidate_evidence` |
| N2 | PASS | CI/agi overclaim blocked; forcing CI on HE02 **demotes** 2→1; rename ≠ promote |
| N3 | PASS | HE02 content-null pattern from committed analysis_v1b |
| N4 | PASS | Risk-3 bar: HE01 meets; HE02 L2 fails (`achieved_below_bar`) |
| N5 | PASS | `examples/causal_replay_demo.py` deterministic match |
| N6 | PASS | Incomplete `ScientificEvidencePack` force-downgrades overclaimed ceiling |

**6/6 PASS.** Pins unchanged at suite run time.

Structured outputs: `suite_results.json`, `SUMMARY.md`, `evidence/*.json`.

## How to re-run (read-only on pins)

```bash
PYTHONPATH=src python3 docs/claimgate/novel_valuable_evidence_20260924/run_suite.py
```

The suite chdirs to the repo root (via `pyproject.toml` /
`docs/hard_experiment_01`) so `biomedical_risk_bar_payload()` can resolve its
relative pin path. Outputs overwrite only files under this folder.

## What remains UNSOLVED

- **HE02 confirmatory** communication / information-control separation
- **HE03** — adapter exists; no `results_v1.json` yet (Goldsby switch-cost path)
- **True `collective_intelligence`** — ClaimGate blocks until earned
- **Major evolutionary transition** claims — not earned

## Honesty

Do **not** read this suite as: intelligence, FDA approval, ASME pass, HE02
proved communication, or that renaming extras can buy `intervention_supported`.
The innovation is **claim–evidence discrimination**, not a solved CI result.
