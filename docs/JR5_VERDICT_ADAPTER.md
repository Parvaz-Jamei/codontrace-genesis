# JR5 raw-evidence verdict adapter (phase 2c)

The core is `codontrace.claimgate.jr5_verdict`; the previous
`codontrace.claimgate.adapters.jr5_verdict` import remains a re-export.
Only a recomputed, positive JR5 verdict can lift the auditor's Red Queen ban.
The host-parasite profile's general claim block is unchanged.

## Trust and synchronization

The package ships the preregistration manifest record and constants as JSON
resources. The loader recomputes the manifest and compares it to the code pin,
checks its unique constants entry against both the actual bytes and the code
constants pin, and parses those same bytes. Each resource is read once. There
is no caller-selected preregistration directory or caller-supplied hash path.
A tuned mapping, a rehashed replacement manifest, and a copied folder do not
establish provenance. These resources work in an installed wheel without a
source checkout. Changes to the lock require a reviewed pin/resource update;
the locked documents are never edited by this adapter.

The finalized preregistration is merged; phase 3 integration remains pending.
Current manifest digest:
`1e1fe67f176fbf4e36725f63bb8773cedf3c6d6c9585f160be14a8a05c238c1d`.
Constants SHA-256:
`e27d3d9eae739097b6fa712ba6ae4f12f568c3479197c67db27bef7439fab026`.
The shipped record file SHA-256 is
`2948e1e961afb0c451c437fea1719dc454fa1019ac9f93c2d3513bc9a72db88e`.
The amended manifest, constants, and record-file SHA values are separate
identifiers; a plan digest is not interchangeable with the manifest digest.
No confirmatory run or final whole-package validation is represented by the
planted fixtures used here.

## Evidence interface

`Jr5Evidence.from_dict()` accepts exactly:

- `prereg_record_digest`: the pinned manifest digest, a string.
- `runs`: a list of exactly 3,760 addressed raw records, covering the complete
  registered experiment/cell/host-size/seed grid once. Run IDs are unique.
- `sealed_locks`: the five section 9 names mapped to full digest strings.
- `e1_gate_record`: the complete phase 3 `jr5_e1_gate_v3` object.

Each run has `run_id`, `experiment` (strings), `cell` (object), `host_n`,
`seed` (integers), `data`, `replay` (objects), and `sha256` (64 lowercase hex
characters). The address is SHA-256 of the canonical JSON of every field
except `sha256`; canonicalization preserves JSON floating-point values and
rejects non-finite numbers. This addresses the raw record, not a supplied
summary or merely a seed label. JSON whitespace is not scientific content.

`replay` contains `expected_digest`, `replayed_digest`,
`one_shot_body_sha256`, `resumed_body_sha256` (64-hex strings), and
`atp_ledger_residual` (finite number). Digests and scientific body hashes must
agree; the absolute residual must be **at most** 1e-9 (closed boundary).

The registered run `data` fields are:

- E1: `uniparental_counts`, integers for every generation 0..T.
- E2 and uniform-tax: `terminal_uniparental_frequency`, a number in [0,1].
- Mutation-load: `log_terminal_fitness`, a finite number.
- N200 copassaged-high E2 additionally has `e4`, exactly `host_effect` and
  `parasite_effect`, and `e4_window`, exactly `[67,70]` (horizon 70, lag 3).
  The expected host sign is negative and parasite sign positive; neither
  signs nor alternative windows are accepted from the input.
- Other registered experiments currently carry an empty data object; their
  run addresses and replay obligations are still required. Additional
  endpoint fields need a reviewed schema extension, not silent acceptance.

Unknown keys and hand-set decisions are refused. Passing a constructed
`Jr5Evidence` does not bypass validation: public entry points reparse its
addressed records, including nested mappings changed after construction.

## Complete E1 gate compatibility

The v3 top-level keys are `schema`, `constants_sha256`,
`prereg_manifest_digest`, `spec`, `cells`, `passed`, `instrument_failure`,
and `digest`. The adapter compares every spec field to the verified constants
and checks the canonical record digest. All four cells and exact seed sets
are required, including excluded seeds and both reported population sizes.
It independently refits the raw generation counts with the registered
bias-reduced modified-score procedure, then checks all cell counts, fixation
and loss lists, intervals, tests, and decisions against the gate record.
Excluded/fixed/lost audit lists are compared by seed membership, independent
of population input order; the complete seed vector remains sorted.
Only numerical evaluation roundoff is tolerated (relative 1e-9, absolute
1e-11); spec values, seeds, counts, types and decisions are not approximate.

N50 equivalence is report-only. An exclusion-cap breach in **any** cell is an
instrument failure; a gated-cell cap breach also prevents `passed`. A
supplied passing flag or a summary-only `adapter_e1()` result is insufficient.
The interface is specified in `docs/jr5_phase3_gate_contract.md` on phase 3.

## Recomputed decisions

The adapter recomputes paired t tests and paired BCa intervals with 10,000
resamples at seed 12345. The four E2 tests use step-down family alpha from
the constants, stop at the first non-rejection, and use the interval level
of each test's actual step. Condition (c) uses the separately registered
one-sided tests and 95% intervals. No unused interval maps are required for
the alternatives. The load trend uses average ranks and a stable upper tail;
its level is derived from the registered family alpha.

"E2 is not significant" for `load_consistent` means none of **all four** E2
family members is significant, including low virulence. Non-significance
does not rule an alternative out: equivalence or an opposite-sign interval
is required, along with a correctly signed registered E4 contrast for the
diversity arm. "Inside" is **strict** at both interval endpoints. An interval
touching an equivalence boundary fails. The planted E1 generator uses the
updated N200 bias-reduced slope SDs 0.076 and 0.051, not the first-pass SDs.

`evaluate_jr5_verdict()` returns `Jr5Verdict`. Its `to_dict()` has `outcome`
(string), `red_queen_proved` (boolean), `conditions` (object with exactly
boolean a..e), `evidence_digest` and `prereg_record_digest` (strings).
`verify_jr5_verdict()` recomputes and compares the complete record;
`assert_jr5_red_queen_claim_allowed()` additionally requires a positive flag.

## Auditor binding

`audit_bundle()` itself imports the verifier lazily; it has no callable
exemption parameter. `jr5_bundle_fields(evidence)` returns the required
bundle projection: `config_digest`, `seeds`, `preregistration_digest`,
`arms`, `outcomes`, `comparisons`, `replay`, and `artifacts`. The auditor
recomputes that projection too. Arm names address each complete per-cell
run-address list. Outcome vectors follow sorted seeds and the displayed
paired comparisons are recomputed. Artifacts cover every raw run plus the
evidence object. Merely appending a valid verdict, matching seed list, or
evidence artifact to unrelated arms/outcomes cannot lift the ban.
Displayed comparison intervals are unadjusted 95% intervals; only the verdict
applies the registered multiplicity and resampling decision rules.

Reference-digest contracts are registered by the consuming claimgate layer.
The engine registry no longer names campaign-specific adapter classes.
Raw replay/body SHA fields are checked in their addressed envelopes, not
represented by separate summary-only digest dataclasses.

## Threat model

This validates content, provenance, completeness, statistical analysis, replay
agreement and bundle identity. It rejects edited summaries, incomplete runs,
wrong lock digests, substituted preregistrations, forged records and staple-on
claims. It does **not** prove that a caller actually executed a simulation or
replay, authenticate an external preregistration timestamp, or defeat a
consistently fabricated raw campaign/replay set. Independent execution of the
registered seeds and the external preregistration receipt remain necessary.
Hostile in-process code changes are outside this boundary.

Section 9 abbreviates the mating campaign suffix as `0f5`; the underlying
sealed handoff record's full digest ends in `0f0a5`. The code pins and tests
the full sealed value. No locked document was silently rewritten.
