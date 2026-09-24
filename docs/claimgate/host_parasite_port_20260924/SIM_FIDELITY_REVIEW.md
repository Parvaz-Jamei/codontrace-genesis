# SIM fidelity + differentiation review — 2026-09-24

Human research review of Scientific Simulation Fidelity (SF1–SF8) and
Differentiation (DX1–DX8) campaigns on the CodonTrace Genesis `host_parasite`
port. Claim ceilings stay fail-closed; infection physics stay outside
`engine.py`.

**Experts:** A — digital evolution / ALife · B — microbial / phage honesty ·
C — ClaimGate / V&V / causal methodology.

## What this pack delivers

- `host_parasite_sim_fidelity_campaigns.py` — SF1–SF8 qualitative literature
  signature tests with SUCCESS / PARTIAL / FAIL.
- `host_parasite_diff_campaigns.py` — DX1–DX8 ClaimGate / causal-audit contrasts
  (not another Avida).
- Combined pack + `tests/test_host_parasite_sim_fidelity.py`.
- Results: `SIM_FIDELITY_CAMPAIGNS_20260924.md` (+ `_FA.md`),
  `sim_fidelity_campaigns_results.json`.
- Intentional hard FAIL: SF4 multi-host Red Queen cycling (model limitation).

## موج ۱ / Critique round 1 (experts A / B / C)

### A (ALife)

1. SF1 coexistence assay initially used Python `hash()` for noise — process-unstable
   under `PYTHONHASHSEED`, breaking pack digests across runs.
2. SF3 must not overclaim Gómez mixing→ARD; the implemented signature is
   cost-rise→FSD (Hall-style), complementary to mixing.

### B (microbial / genome honesty)

3. SF4 must remain an honest FAIL if perpetual dominance cycles are absent;
   do not soft-pass with PARTIAL cosmetics.
4. Channon Tokyo Type 1 DOI in DX3 must be the published `artl_a_00430`, not a
   guessed neighbor.

### C (ClaimGate)

5. New `SimFidelityPack` digest class must register in
   `NON_REPLAY_CRITICAL_DIGEST_CLASSES` or HC7 regressions fail.
6. DX1 theatrical refuse list must include aliases (`intelligence`,
   `modes_passed`, `tokyo_type1_passed`) that soft tests previously missed.

### Fixes (round 1)

- Replaced `hash(v)` with stable `sum(ord)` indexing in SF1; stripped
  `history_tail` from trial payloads.
- SF3 honesty note documents cost-rise→FSD vs Gómez mixing→ARD.
- SF4 success criterion keeps FAIL when `n_cycling_seeds == 0`;
  `intentional_hard_failure=True`.
- DX3 `doi_channon` set to `10.1162/artl_a_00430`; Dolson MODES kept as comparator.
- Registered `SimFidelityPack` in `replay_integrity.py`.
- DX1 refuses 17 theatrical claims including aliases; all blocked.

### Retest (round 1)

`pytest tests/test_host_parasite_sim_fidelity.py
tests/test_host_parasite_hard_regressions.py
tests/test_host_parasite_cell_microbe_hard_campaigns.py` green.
Cross-process pack digest stable. BAIC pins intact.

## موج ۲ / Critique round 2 (experts A / B / C)

### A

1. Pack schema should distinguish SF vs DX counts for auditability (`n_sf`, `n_dx`).
2. Engine boundary must scan both `genesis/engine.py` re-export and
   `codontrace/engine.py` core.

### B

3. Persian summary must state the bachelor-level sentence:
   «شبیه‌سازی می‌تواند اثر ببیند ولی claim ثابت‌شده را قفل می‌کند»
   with concrete DX1 / DX5 / DX7 numbers.
4. Quigley published DOI must be `10.1098/rspb.2012.0769` (not an RSTB guess).

### C

5. DX6 must show profile-scoped refuse (HP blocks phage; other profiles may
   allow the string) without implying other domains cleared phage therapy.
6. Two matrices side-by-side required in results MD; ladder must stay unchanged.

### Fixes (round 2)

- Pack exposes `n_sf=8`, `n_dx=8`; schema
  `host_parasite_sim_fidelity_diff_campaigns_v1`.
- SF8 + DX8 both scan genesis re-export and core engine; env positive control.
- `_FA.md` leads with the required sentence and numbered contrasts.
- SF1 `doi` = `10.1098/rspb.2012.0769` with `doi_arxiv` retained.
- DX6 honesty note: profile-scoped auditor feature, not cross-domain clearance.
- Results MD Matrix A / Matrix B; `ladder_unchanged=True` in audit.

### Retest (round 2) — sign-off

Full SF/DX + hard regression + cell↔microbe hard suites green.
Pins A–C byte-identical. `engine.py` untouched for infection physics.
A / B / C sign-off for merge-ready PR (do not merge unless asked).

**Headline contrasts for readers:** DX1 (0.444 Δentropy + 0.22 cost jump vs 17/17
blocks), DX7 (0.2 vs 1.0/1.0/1.0 still no intervention support), DX5 (0.20 vs 1.00
null trap), SF4 honest FAIL on Red Queen cycles.
