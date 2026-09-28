# Phase-2 Track C scored JSONL note (Ideas 1 / 3 / 5 / 6)

**Date:** 2026-09-29  
**Status:** scored multi-cell N=run JSONL under claim ceiling `phase2_design`; Critic post-data pending  
**Claim ceiling:** `phase2_design`  
**hypothesis_supported:** `false` (every record; soft-pass forbidden)  
**red_queen_proved:** `false`

This note records that Track C Ideas 1, 3, 5, and 6 have a scored JSONL campaign path under the sealed phase-2 design digests. It does **not** elevate the claim ceiling, authorise a discovery claim, or replace Critic post-data review.

## Scope

- Output: `outputs/campaigns/discovery_questions_20260928/jsonl_track_c/`
- Module: `discovery_q_20260928_jsonl_track_c` (+ CLI `scripts/run_discovery_q_20260928_jsonl_track_c.py`)
- Separate from the Idea4+Idea2 `jsonl_campaign` path
- Default seeds: `range(401, 465)` (64 runs); avoids 201–264, 301–364, and sealed 801–816
- Scaffold builders only: `build_idea{N}_scaffold_ledger` (smoke aliases are not the evidence path)
- Unit of replication remains **run** (`n_unit=run`)

## Honesty locks

1. `claim_ceiling=phase2_design` on every record and the manifest.
2. `hypothesis_supported=false` on every record; `hypothesis_supported_any=false`.
3. Soft-pass forbidden (`soft_pass=false`, `soft_pass_claimed=false`).
4. Volume ≠ discovery; this is not a discovery or measurement claim.
5. Critic post-data seal remains pending.
6. Identity IDs non-empty, including Idea3 `REV-HIGH-NOISE-BLIND-ACCEPT-V1` and Idea6 `U-LEDGER-EVIDENCE-STRENGTH-V1` (+ `USTAR-RESTRAINT-V1`); ClaimGate ≠ u.

## Freeze locks exercised by scored cells

- **Idea1:** discriminate / reactive / reward_explore; `RP-LEDGER-ATP-DRAIN-V1`; assay separate from reward; margin without assay pass is not H2.
- **Idea3:** transmit / pool / imitate / cut / reversal; unreachability; empty cut reopens.
- **Idea5:** retain_teach / survival_only / shortcut_probe; world/law/probe IDs; held-out; θ=0.80; train-fit alone is FAIL.
- **Idea6:** withhold / consult / bold / support_on / support_cut; support-on vs cut; empty support_cut reopens.

## What this is not

- Not a discovery claim.
- Not Critic-sealed post-data evidence.
- Not authorisation to raise `hypothesis_supported`.
- Not a revision of sealed seeds or of Ideas 2 / 4 campaign results.
