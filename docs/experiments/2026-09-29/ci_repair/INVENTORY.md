# CI repair inventory — task-9 (owner: pressure-fix)

Scope (disjoint, handed over as a patch; the manager is the only writer):

1. `src/codontrace/rng.py`
2. `src/codontrace/life_loop/contact_atp_ledger.py`
3. `src/codontrace/genesis/campaigns/discovery_q_20260928_idea1.py`
4. `src/codontrace/genesis/campaigns/discovery_q_20260928_idea2.py`
5. `src/codontrace/genesis/campaigns/discovery_q_20260928_idea3.py`
6. `src/codontrace/genesis/campaigns/discovery_q_20260928_idea5.py`
7. `src/codontrace/genesis/campaigns/discovery_q_20260928_idea6.py`

Explicitly **not** touched (manager hygiene commit): `engine_runtime.py`,
`life_loop/engine_ledger_coupler.py`,
`genesis/campaigns/discovery_q_20260928_jsonl_engine.py`.

## 1. Failure class (RNG static rule) — root cause

`tests/test_rng.py::test_no_direct_random_usage_outside_rng_module` scans every
`src/codontrace/**/*.py` except `rng.py` for the literal markers
`"import random"`, `"from random"`, `"random."`, `"Random("`, `"pickle"`.

20 offending markers at the pushed tip, in my scope:

| file | line | marker(s) | code |
| --- | --- | --- | --- |
| `life_loop/contact_atp_ledger.py` | 14 | `import random` | stdlib import |
| `life_loop/contact_atp_ledger.py` | 159 | `random.Random` | `_rng: random.Random = field(default_factory=random.Random)` |
| `life_loop/contact_atp_ledger.py` | 162 | `random.Random` | `self._rng = random.Random(int(self.rng_seed))` |
| `life_loop/contact_atp_ledger.py` | 1359 | `random.` | comment: `...for cut_matched_random.` |
| `genesis/campaigns/discovery_q_20260928_idea1.py` | 193,195 | `import random`, `Random(` | function-local `import random as _random` + `_random.Random(...)` |
| `...idea2.py` | 234,236 | same | same |
| `...idea3.py` | 207,209 | same | same |
| `...idea5.py` | 237,239 | same | same |
| `...idea6.py` | 221,223 | same | same |

Root cause: all five campaign modules and the ledger were written against the
standard library's `random.Random` instead of the project facade
`codontrace.rng`, which the static rule requires. The 20 markers are 9 real code
sites (1 import + 3 ledger `Random(` sites + 5 module-local `import random` +
5 module-local `Random(` sites), with the remaining markers being the same text
matching more than one forbidden substring.

## 2. Design of the fix

`rng.py` is exempt from the scan, so the stdlib-compatible stream lives there:

* new `StdlibSeedRNG` dataclass (`rng.py`) — forwards the seed **untouched** to
  `random.Random(seed)` and exposes `random`, `randrange`, `choice`, `shuffle`,
  `sample`, `fork`, `snapshot`, `state_digest`, `getstate`/`setstate`,
  `draw_count`. Namespaced derivation is deliberately **not** applied, because
  hashing the seed (as `RNGManager` does) would move every recorded number.
* `contact_atp_ledger.py` imports `StdlibSeedRNG` and uses it for the field
  default and the `__post_init__` re-seed; the comment containing `random.` is
  reworded to "the matched cut op" (meaning preserved).
* each idea module replaces its function-local `import random as _random` and
  `_random.Random(<expr>)` with `from codontrace.rng import StdlibSeedRNG` and
  `StdlibSeedRNG(seed=<expr>)`; `<expr>` is untouched, so the seed value is
  identical.

No threshold, seed, gate, refusal, pin or expectation was touched. No test was
modified.

## 3. Equality proof (recorded numbers must not move)

`prove_rng_equality.py` → `rng_equality_out.txt` / `rng_equality_out.json`
(exit 0, `ALL_EQUAL`):

* 8 call-site seed expressions (idea1/2/3/5/6, incl. the `cell + arm` variant)
  × 32 draws in two method schedules (`random()` only, and a mixed
  `random`/`randrange`/`choice`/`shuffle` schedule) — every value `repr`-equal,
  i.e. bit-for-bit identical streams.
* the **real ledger** driven through one fixed op schedule
  (`matched_random_edge`, `matched_random_edge(degree=2)`,
  `reward_explore_eps`, `reallocate_contact_budget`) with the legacy
  `random.Random(401)` stream versus the new `StdlibSeedRNG(seed=401)` stream —
  identical op results.
* scaffold ledger digests for seeds 0/1/7/11/401/5501 identical
  (`contact_atp_ledger:8732a7c3…` in both).
* unseeded default path: `StdlibSeedRNG()` is OS-entropy seeded like
  `random.Random()` (two instances differ), and the re-seeded path is equal.

Whole-campaign end-to-end comparison (20 scored cells across idea1/2/3/5/6 at
seed 401, before vs after): `campaigns_before.json` vs `campaigns_after.json` —
`cells_equal True`, `ledgers_equal True`, identical SHA-256
`2394fd82f06a0557bbfb4d95adf75e40…`.

## 4. Acceptance evidence (patched scratch tree = baseline + patch)

| command | result |
| --- | --- |
| `python -m pytest tests/test_rng.py -q --disable-plugin-autoload` | 3 passed, 1 failed — the only remaining offenders are the two `pickle` tokens in `engine_runtime.py` and `discovery_q_20260928_jsonl_engine.py`, both assigned to the manager. My scope has **0** offenders. |
| scope-only marker scan over the 7 files | 0 offenders outside `rng.py` (which the test exempts) |
| `python -m ruff check src tests` | `All checks passed!` (exit 0) |
| `python -m compileall -q src` | exit 0 |
| `pytest tests/campaigns/discovery_questions_20260928 -q` | 86 passed |
| `pytest tests/test_life_loop_contracts.py tests/campaigns -q` | 149 passed |
| `pytest tests/test_life_loop_contracts.py tests/test_life_loop_contact_inherit.py tests/campaigns -q` | same single pre-existing failure on baseline **and** patched tree (see §6.1) |

### Pre-existing failures proved unchanged by the patch

1. `tests/test_life_loop_contact_inherit.py::test_banned_tokens_absent_from_new_life_loop_modules`
   fails identically on `docs/experiments/2026-09-29/verification/full6187ff4` (unpatched) and on the
   patched tree: both enumerate exactly
   `['engine_ledger_coupler.py:infect', 'engine_ledger_coupler.py:infection']`.
   Not caused by, and not fixable from, this patch (manager-owned file).
2. the two `pickle` tokens in `engine_runtime.py:339` and
   `discovery_q_20260928_jsonl_engine.py:272` (manager hygiene items).

## 5. Patch provenance and application

* `PROPOSED_CHANGE_rng_backend.patch` — unified diff, `--- a/<path>` /
  `+++ b/<path>` headers, generated by `make_rng_patch.py` from
  `docs/experiments/2026-09-29/verification/full6187ff4` (baseline) vs `test-runs/ci_verify_scratch` (staging directory, removed and not distributed; the surviving equivalent is `docs/experiments/2026-09-29/verification/`) (staging directory, removed and not distributed; the surviving equivalent is `docs/experiments/2026-09-29/verification/`) (staging directory, removed and not distributed; the surviving equivalent is `docs/experiments/2026-09-29/verification/`) (staging directory, removed and not distributed; the surviving equivalent is `docs/experiments/2026-09-29/verification/`) (staging directory, removed and not distributed; the surviving equivalent is `docs/experiments/2026-09-29/verification/`)
  (patched). Apply from the repository root with `git apply -p1`.
* `verify_patch_applies.py` → `verify_patch_applies_out.txt`: applies the patch
  to a fresh copy of the baseline and asserts byte-identity with the verified
  patched tree — `PATCH_REPRODUCES_TREE: True` (7/7 files).
* `apply_rng_patch.py` — the deterministic generator of the change (idempotent;
  refuses to run twice).

## 6. Notes / residual risk

* The scaffold ledger digest is seed-independent by construction (the digest is
  taken before any RNG-consuming op), so the digest-equality check above is a
  consistency check, not a strong sensitivity test; the stream-equality and
  op-schedule checks carry that weight.
* The unseeded field default (`random.Random()` → `StdlibSeedRNG()`) is never
  observable, because `__post_init__` immediately re-seeds from `rng_seed`; it
  is preserved for behavioural equivalence only.
* No git operations were performed by this owner; the repo was never edited —
  all experiments ran against copies under the staging directory `test-runs/`, which was removed from the workspace; the surviving copies are archived under `docs/experiments/2026-09-29/`.
