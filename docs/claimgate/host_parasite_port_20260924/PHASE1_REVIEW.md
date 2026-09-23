# Phase 1 review — ClaimGate `host_parasite` profile complete

Human research review of the Phase 1 hardening work: adapter surface, fail-closed
blocks, declared COU/risk labels, and the declared intervention-menu schema stub.
Two critique rounds below each name a real defect, the fix, and the retest result.

## What Phase 1 delivers

- Profile blocks expanded to cover CRISPR-identity / CRISPR-therapy aliases and
  `red_queen_proved` / `major_transition_proved`, while keeping the existing
  clinical, therapy, epidemic, BSL, and intelligence blocks.
- Adapter helpers: `declared_cou_risk_labels`, `declared_intervention_menu`,
  `attach_declared_intervention_menu`, with fail-closed validation.
- Declared intervention kinds limited to digital falsification hooks
  (remove parasites, content-null, structure-null, abiotic-only, and related).
- Tests under `tests/test_claimgate_host_parasite.py` covering registration,
  blocked aliases, blank claims, COU overrides, menu schema, domain isolation,
  and ladder non-promotion.

Infection physics remain unimplemented in the engine. A declared menu is not an
executed campaign and does not raise the public ClaimGate ladder.

## Critique round 1

### Flaws found

1. **Boolean / string flag mismatch.** `DeclaredIntervention.to_dict()` emitted
   the strings `"false"` for `executed` and `raises_claim_ladder`, while
   `DeclaredInterventionMenu.to_dict()` used JSON booleans. Downstream auditors
   comparing types would disagree with themselves.
2. **Menu attach was domain-blind.** `attach_declared_intervention_menu` would
   accept a biomedical bundle and stamp a host–parasite menu onto it, mixing
   domain labels.
3. **Unknown COU override keys were ignored.** Passing
   `cou_risk_overrides={"not_a_real_key": ...}` succeeded silently, which is the
   opposite of fail-closed labeling.

### Fixes

- Normalize intervention row flags to JSON booleans.
- Require `extra["domain"] == "host_parasite"` before attach.
- Reject unknown `cou_risk_overrides` keys with `ConfigurationError`.

### Retest

`PYTHONPATH=src pytest tests/test_claimgate_host_parasite.py` — all tests green,
including new regressions for bool flags, biomedical attach rejection, and
unknown override keys.

## Critique round 2

### Flaws found

1. **Silent menu overwrite.** Attaching a second declared menu replaced the
   first without error. For claim labeling, silent replacement of a registered
   falsification plan is an honesty defect: a later reader cannot tell which
   menu was intended.

### Fixes

- Refuse a second attach when `declared_intervention_menu` is already present.
  Callers must build a new bundle if they need a different menu.

### Retest

Same pytest file — green, including
`test_attach_menu_refuses_silent_overwrite`.

## Honest limits after Phase 1

- No `HostParasiteEnv` yet (Phase 2).
- No executed intervention falsification (Phase 3).
- Optional ARD/FSD dynamics labels are not proved; `red_queen_proved` stays
  blocked.
- BAIC pins (`results_v7.json`, `risk_bar.json`, `biomedical_study.json`) are
  untouched.
