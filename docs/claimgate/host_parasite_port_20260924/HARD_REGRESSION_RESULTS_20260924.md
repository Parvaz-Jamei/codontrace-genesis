# Hard regression results — host_parasite ClaimGate (2026-09-24)

**Project:** CodonTrace Genesis  
**Branch:** `test/hard-unsolved-host-parasite-regressions`  
**Suite:** `tests/test_host_parasite_hard_regressions.py` (20 tests)  
**Scope:** Find important unsolved / weakly covered hard cases after Waves 3–6
(`origin/main` tip including #49/#50 / PyPI 0.3.0b7). Prefer honesty and wiring
fixes over new biology features. Hard locks unchanged (one DomainProfile; cell =
substrate; no infection in `engine.py`; BAIC pins byte-identical; blocked claims
not loosened).

**Local time note:** authored 2026-09-24 ~04:06 IRST (UTC+3:30).

---

## Hunt summary (why these cases)

Scanned existing phase tests, Wave 5/6 completeness audits, `COMPARATOR_MATRIX`,
`CHALLENGES`, HE_HP locked pack, replay digest registration (#50), and
literature pressure from Avida / MODES / Cornish / Floreano–Knoester. Soft Wave-6
smoke already covers happy-path attach order and ladder non-rise. Remaining hard
holes were:

1. Phase-18 matrix listed OEE/MODES / complexity / gene-identity refuses, but
   `assert_claim_allowed` / `claimed=` still accepted them (test even faked the
   raise for non-profile claims).
2. Alias spellings (`intelligence_proved`, `modes_passed`, `oee_modes_passed`)
   bypassed blocked `intelligence` / comparator refuses.
3. Sequential Cornish all-success schedules (`later_intervention_failed=False`)
   were not explicitly audited against granting `intervention_supported`.
4. `candidate_evidence` could clear with structure-null or abiotic-only alone —
   Floreano/Knoester content-control honesty gap.
5. HE_HP locked JSON honesty flags were checked, but schema /
   `engine_infection_physics` were not fail-closed under adversarial packs.
6. Contingency seed triples that still *support* the universal law were not
   audited for “support ≠ prove complexity emergence.”
7. Replay-policy registration for all `host_parasite*` digest dataclasses needed
   an explicit hard regression after #50.

---

## Case results

### HC1 — Fail-closed ClaimGate matrix under adversarial `claimed=`

| Field | Detail |
|---|---|
| **What / why hard** | Journal `BLOCKED_CLAIM_MATRIX` listed `modes_passed_proved`, `oee_type1_proved`, `complexity_emergence_proved`, `gene_identity_proved`, plus therapy / Red Queen / CRISPR / BSL strings. Soft Phase-18 test only called `assert_claim_allowed` for profile members and *synthetically raised* for the rest — documentation theater, not fail-closed wiring. |
| **Outcome** | **fail → fix → pass.** Bundle factory accepted `claimed="modes_passed_proved"` (and siblings) before the fix. |
| **Fix** | Extended `HOST_PARASITE.blocked_claims` in `domain.py`; aligned `BLOCKED_CLAIM_MATRIX`; Phase-18 test now asserts every matrix refuse via `assert_claim_allowed`. |
| **References** | Dolson et al. 2019 MODES doi:10.1162/artl_a_00280; Channon 2024 Tokyo Type-1 doi:10.1162/artl_a_00430; Zaman et al. 2014 doi:10.1371/journal.pbio.1002023 (complexity humility); port `CITATIONS.md` §24–25; `DEPTH_BRAINSTORM_WAVE6_COMPLETENESS.md` refuse list. |
| **Explanation / ClaimGate honesty** | Comparator measurement papers must never become public claim ceilings. A `claimed=` string that the matrix calls “never attach as proved” must raise `ConfigurationError` the same way `red_queen_proved` does. |

### HC2 — Adversarial aliases (`intelligence_proved`, `modes_passed`, …)

| Field | Detail |
|---|---|
| **What / why hard** | `intelligence` was blocked but `intelligence_proved` was allowed. `modes_passed` / `oee_modes_passed` likewise slipped past the canonical `*_proved` spellings. |
| **Outcome** | **fail → fix → pass.** |
| **Fix** | Added aliases to `blocked_claims` and the matrix. |
| **References** | Hard-lock refuse list (intelligence proved; OEE-MODES passed); ALIFE profile precedent for `intelligence`; Dolson/Channon comparators above. |
| **Explanation / ClaimGate honesty** | Fail-closed labeling must cover common alias spellings, not only the first string that happened to be typed into the frozenset. |

### HC3 — Sequential Cornish all-success still refuses `intervention_supported`

| Field | Detail |
|---|---|
| **What / why hard** | Default schedule makes later interventions effect-distinct, so `later_intervention_failed=False`. Soft Phase-22 tests did not stress the “all interventions succeed after observational match” edge that could tempt granting support. |
| **Outcome** | **pass** (result + attach already refused; adversarial `replace(..., intervention_supported=True)` refused). No production change required beyond regression coverage. |
| **References** | Cornish et al. JMLR 27(152) 2026 / arXiv:2301.07210; Phase 22 review; `COMPARATOR_MATRIX` Cornish row. |
| **Explanation / ClaimGate honesty** | Observational match alone never grants `intervention_supported`, even when every later digital intervention is effect-distinct. Attach overwrites the flag to `False` and refuses `True` inputs. |

### HC4 — `candidate_evidence` requires content-null (Floreano honesty)

| Field | Detail |
|---|---|
| **What / why hard** | Falsification previously cleared if *any* of structure-null / dual-null / abiotic / content-null differed from intact. Structure-only or abiotic-only campaigns could therefore take `candidate_evidence` without a content-sensitive control — the classic channel-off-looks-like-a-win hole. |
| **Outcome** | **fail → fix → pass.** |
| **Fix** | `_evaluate_falsification(..., require_content_null=)` on the candidate_evidence path; `_content_null_distinct` also compares payloads so `steal_fraction=0` score ties still separate empty content-null payloads from intact. |
| **References** | Floreano et al. 2007 doi:10.1016/j.cub.2007.01.058; Knoester et al. 2008 doi:10.1145/1389095.1389130; challenge E4 in `CHALLENGES.md`; HE02 content-null lineage in `CITATIONS.md` §16–17. |
| **Explanation / ClaimGate honesty** | Structure-null (seat / overlap off) is not a substitute for content-null (payload emptied). Candidate ceilings require the content arm. |

### HC5 — HE_HP locked-pack schema / engine integrity

| Field | Detail |
|---|---|
| **What / why hard** | Refresh replayed campaign digests and checked several honesty flags, but an adversarial pack could flip `engine_infection_physics` or forge `schema` without a dedicated validator. Not a BAIC pin mutation — host_parasite artifact integrity. |
| **Outcome** | **fail → fix → pass** (validator added; live pack + adversarial mutations covered). |
| **Fix** | `validate_he_hp_locked_pack()` enforces schema, `engine_infection_physics='not_in_engine_core'`, honesty flags, required campaigns, and non-empty `locked_digest`. |
| **References** | `docs/hard_experiment_hp/locked_campaign_digests.json`; Phase 25 review; engine boundary challenge E1; Acosta & Zaman 2022 doi:10.3389/fevo.2021.750772 (CPU-theft comparator stays *outside* engine). |
| **Explanation / ClaimGate honesty** | Locked digests certify digital campaign replay, not infection physics inside `engine.py`. Schema drift or “in_engine_core” claims must fail closed. |

### HC6 — Contingency supporting seeds cannot prove complexity emergence

| Field | Detail |
|---|---|
| **What / why hard** | Many seed triples (e.g. `(1,2,4)`) still *support* `parasites_always_raise_complexity_across_seeds` under `runtime_observation`. Soft Phase-21 tests used falsifying seeds only. Risk: readers equate “hypothesis_supported” with proved emergence. |
| **Outcome** | **pass** after audit (campaign already kept `complexity_emergence_proved=False`; `candidate_evidence` refused while the law still holds; attach refuses evil `True` flag). Regression locks the edge. |
| **References** | Zaman et al. 2014 doi:10.1371/journal.pbio.1002023; challenge S1; Phase 21 review; Wave-6 entropy×contingency bridge humility. |
| **Explanation / ClaimGate honesty** | Contingency assays may report that a universal rise law still holds for some seeds; that report never unlocks complexity emergence or raises the ladder. Dual-null parasite-absent digests remain distinct. |

### HC7 — Replay-policy digest registration (#50 regression)

| Field | Detail |
|---|---|
| **What / why hard** | #50 registered 23 Waves 3–6 host–parasite digest dataclasses into `NON_REPLAY_CRITICAL`. Without a host_parasite-scoped hard sweep, a new digest dataclass could silently fall out of policy. |
| **Outcome** | **pass** (all current `host_parasite*.py` digest dataclasses registered; registry audit empty). |
| **References** | PR #50 commit `8ba6e08`; `tests/science_gates/test_replay_digest_policy_sweep.py`; `ENGINE_REPLAY_CONTRACT.md`. |
| **Explanation / ClaimGate honesty** | Digests identify campaign/cell artifacts only; registration does not grant clinical, wet-lab, intelligence, or Avida-replacement claims. |

---

## Pins / engine / locks

| Check | Status |
|---|---|
| `docs/hard_experiment_01/results_v7.json` SHA256 `35bb5936…21cbd6` | OK |
| `docs/claimgate/risk_bar.json` SHA256 `4dbe4aa3…771cd7` | OK |
| `docs/claimgate/biomedical_study.json` SHA256 `9685f2fb…f5ddce` | OK |
| `engine.py` free of `HostParasiteEnv` / inject | OK |
| `population/` untracked | OK |
| Blocked claims tightened (not loosened) | OK |

---

## Test counts (local)

| Suite | Collected / result |
|---|---|
| New hard regressions | **20 passed** |
| Hard + all `test_host_parasite_*` + claimgate HP + digest sweep | **222 passed** |

---

## ClaimGate honesty note (global)

None of these hardenings raise the public ClaimGate ladder, prove Red Queen
dynamics, clear phage therapy, certify BSL, establish CRISPR identity, pass
OEE/MODES, or prove intelligence / complexity emergence. They close wiring
holes so those refuses stay fail-closed under adversarial packets.
