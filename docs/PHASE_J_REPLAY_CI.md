# Phase J — replay-verified CI candidate packs (honest path)

CodonTrace Genesis Phase J closes the **replay_verification** gap after
Phase I ([`PHASE_I_CI_EVIDENCE.md`](PHASE_I_CI_EVIDENCE.md), PR #14 @
`6a0fe1a`). It is **evidence engineering**, not a claim unlock. ClaimGate
stays the authority. No version bump.

**Claim ceiling:** `runtime_observation` for new measurement objects; RAG
retrieval is documentation / measurement design.

**Still blocked:** `collective_intelligence`, `proved_collective_intelligence`,
`intelligence`, `agi`, `open_ended_intelligence`, `tokyo_type1_passed`,
`avida_replacement`.

`collective_intelligence_candidate` remains allowed **only** when the full
ClaimGate flag set is actually present, including honest
`replay_verification`. Phase J can *earn* that flag when an independent
re-execution produces matching campaign digests. Smoke runs **never** earn
flags. Digests are never faked.

Index: [`PHASE_INDEX.md`](PHASE_INDEX.md). Honesty:
[`WHY_NOT_INTELLIGENCE_YET.md`](WHY_NOT_INTELLIGENCE_YET.md).
Phase L: [`PHASE_L_AVIDA_FIDELITY.md`](PHASE_L_AVIDA_FIDELITY.md).

---

## 1. What shipped

| Surface | Role | Honesty |
|---|---|---|
| `capture_campaign_replay` / `verify_digest_replay` | Bind a campaign digest to its spec; re-execute independently; compare digests | Same-object “replay” is rejected; mismatch fails; placeholder digests rejected |
| `build_replay_verified_ci_candidate_pack` | Run Phase I research-scale earnable campaigns, re-execute, earn flags | Smoke never earns; does not mutate ClaimGate |
| `run_price_equation_covariance_scaffold` | Okasha/Price MLS1 between+within covariance on the two-task analog | Last-generation snapshot; transmission term **not** estimated; `major_transition_in_individuality=False` |
| RAG cite | Price 1970 Nature; Okasha digest updated | Retrieval is not evidence |

Default Phase A–E digest pins are unchanged.

---

## 2. How `replay_verification` is earned (never faked)

`earn_collective_intelligence_candidate_flags(..., replay=verification)`
accepts a `DigestReplayVerification` object. The flag is True only when
**all** of the following hold:

1. The verification object independently re-executed the captured specs
   (or received a **different object** produced by a separate run).
2. Every captured campaign digest equals the corresponding replay digest.
3. Digests are real SHA-256 evidence digests (not `fake` / `placeholder`).
4. The captured specs are at least exploratory-scale (`seed_count>=12`,
   `generations>=20`) and `smoke=False`.

Passing the same Python object as both capture and replay is **not**
re-execution. Smoke packs may *match* and still earn nothing.

Even when every candidate flag is True,
`collective_intelligence` stays forbidden.

---

## 3. When `collective_intelligence_candidate` becomes allowable

If a researcher builds a **research-scale** replay-verified pack and every
Phase I earnable flag is also True, ClaimGate **allows**
`collective_intelligence_candidate`. That is a candidate label only.

It does **not** allow:

- `collective_intelligence`
- `proved_collective_intelligence`
- `intelligence` / `agi`
- `tokyo_type1_passed`
- `avida_replacement`

Smoke (`seed_count=2`, `generations=6`) never reaches this bar.

Library default `seed_count=12` is exploratory; research-grade n is 30.
`generations=20` stays the library default.

---

## 4. Price-equation / Okasha covariance scaffold

`price_partition_from_groups` / `run_price_equation_covariance_scaffold`
record:

- trait `z` = heritable task preference
- organism fitness `w` = personal task yield
- MLS1 group fitness = mean personal fitness
- MLS2 analog group fitness = complementary-task group payoff (not in the
  MLS1 identity)

The MLS1 identity on equal-sized groups is
`Cov(w,z) = Cov(W,Z) + E[Cov_within]`. Residual is recorded.
`price_equation_complete=False`. This is bookkeeping, not a Price 1970
empirical paper.

---

## 5. RAG pointers added in Phase J

Canonical machine corpus: `src/codontrace/genesis/rag/corpus/seed.jsonl`.

| `doc_id` | Authority | Why it is here |
|---|---|---|
| `price_1970_selection_and_covariance` | Nature 1970 doi:10.1038/227520a0 | Selection as covariance; MLS1 partition source |
| `okasha_2006_levels_of_selection` | OUP 2006 (updated) | MLS1 bookkeeping vs MLS2 outcome; now names the Phase J scaffold |

```python
from codontrace.genesis import search_corpus, cite_sources
from codontrace.genesis.phase_j import build_replay_verified_ci_candidate_pack

pack = build_replay_verified_ci_candidate_pack(smoke=True)
assert not any(pack.as_mapping().values())
assert pack.candidate_allowed is False
print(cite_sources(search_corpus("Price equation covariance Okasha MLS1", k=5)))
```

Print-only smoke: `examples/genesis_phase_j_replay_ci.py`.

---

## 6. What is still missing for literature-grade CI

1. Avida-scale evolved coordination *instructions* (not a preference gene)
   — Phase K analog ISA; not Avida C++.
2. Goldsby 2012 ~50-replicate CPU-delay specialists + isolation failure that
   is evolved autonomy loss rather than payoff construction — Phase K
   harness (research default 50); not the PNAS experiment.
3. Full multi-generation Price analysis with a transmission term; Avida
   `DEME_GROUP` MLS2 — Phase K estimates transmission; `price_equation_complete`
   stays False.
4. Michod/Conlin endogenous conflict suppression and revertant assays —
   Phase K hooks only; endogenous flags stay False.
5. Chromaria knock-outs / Channon 2024 Type 1 **pass** / vocabulary+verifier
   gap closure — still later, still blocked as claims.

Keep building until evidence exists. Do not unlock claims by weakening the
gate.

---

## 7. ClaimGate remainder

Allowed when objects exist: `runtime_observation`,
`oee_measurement_only`, `tokyo_type1_measurement_only`,
`collective_intelligence_candidate` (full flags only, including honest
replay).

Forbidden after Phase J packs, Price scaffolding, and RAG retrieval: `agi`,
`intelligence`, `collective_intelligence`, `tokyo_type1_passed`,
`avida_replacement`, `open_ended_intelligence`.

Name the project **CodonTrace Genesis**. Package remains `codontrace`.
