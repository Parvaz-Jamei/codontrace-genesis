# HARD_EXPERIMENT_02_PREREG (draft lock 2026-09-13)

Date: 2026-09-13. Repo: Parvaz-Jamei/codontrace-genesis @ main after handoff 289e966.
Status: **PREREG BEFORE CODE** — do not run research campaign until this file is hashed and committed.

## Question
Does capsule-mediated food-location information transfer, under deme/kin selection structure, produce Holm-surviving gains vs content-null / activity-matched / channel-off controls when E1+E2+E5 knobs are enabled?

## H1 / H0
- H1: treatment (patch signal + appropriate deme cell) > content_null on primary outcome (receiver/group yield proxy), with MI(payload; patch)>0 in treatment and ≈0 under content scramble.
- H0: no Holm-surviving contrast after correction; or manipulation checks fail → assay_invalid.

## Arms (sketch; finalize counts in amendment if needed)
| Arm | Role |
|-----|------|
| treatment | E1+E2 cell per prereg pattern + E5 optional |
| content_null | cost-matched useless payloads |
| activity_matched | yoked escape-from-WAIT |
| channel_off | CapsuleTransfer disabled |
| capsules_shuffled | source↔payload association ablation |
| oracle_moderate | f∈{0.25,0.5,1.0} useful fraction |

## E2 pattern prediction (ordinal; Floreano/Knoester)
GERMLINE×CLONAL > GERMLINE×MIXED ≈ INDIVIDUAL×CLONAL > INDIVIDUAL×MIXED (deception risk).

## Seeds / scale
- Pilot only: 1000–1009 (calibration + Morris if needed)
- Research: 30 seeds, disjoint from pilot; ticks/pop TBD after smoke timing
- Smoke in CI; research outside CI with committed results_v1.json

## Decision rule
Holm over ≤3 primary contrasts; content_null must not beat channel_off; ClaimGate ceiling at most intervention_supported if all CLAIMS.md §5 flags met — never invent labels.

## Knob template
Every new config: frozen dataclass slots=True, enabled=False, ConfigurationError in __post_init__, to_dict non-defaults only, canonical_digest, one DAG edge, pin+runtime tests.

## Literature
See `docs/hard_experiment_02/HE02_SCIENCE_BRIEF.md`.


## Document digest
`sha256:f01fae62cc8adeeecee7eaf4658df4166d6ce4f80fd88d22f0e1a381aeb62253`
