# Phase 19 review — ARD→FSD transition + cost-of-generalism digests

Human research review of a time-sliced ARD→FSD *transition protocol* with
cost-of-generalism proxies. Builds on Phase 5 labels without claiming wet
ARD/FSD identity. ``red_queen_proved`` stays False forever.

**Experts:** A — digital evolution / ALife · B — microbial / phage honesty ·
C — ClaimGate / V&V / causal methodology.

## What Phase 19 delivers

- `run_ard_fsd_transition_campaign` in `host_parasite_ard_fsd_transition.py`.
- Early/late slice digests per arm; parasite / structure-null / abiotic dual-null.
- Cost-of-generalism proxy from joint infectivity/resistance breadth.
- Falsification of `dynamics_always_ard_under_parasitism`.
- `attach_ard_fsd_transition` (prereg-bound).
- Tests in `tests/test_host_parasite_phase19.py`.

## موج ۱ / Critique round 1 (experts A / B / C)

### A — feasibility / testable innovation

1. **Phase 5 shipped ARD/FSD enums only** — no temporal transition protocol
   reviewers could attach; without early/late windows this phase is taxonomy.

### B — microbial honesty

2. **Cost-of-generalism (Koskella & Brockhurst synthesis) had no digital proxy**,
   so ARD→FSD framing lacked the wet literature’s driver language (as labels).

### C — ClaimGate honesty

3. Transition digests must never set `red_queen_proved` or claim wet ARD/FSD
   identity.

### Fixes (round 1)

- Added early/late windowed slice digests with pairwise distinctness.
- Added non-negative cost-of-generalism proxy on every slice.
- Forced `red_queen_proved=False` and `wet_ard_fsd_identity=False`.

### Retest (round 1)

Phase 19 green; hypothesis falsified under transition or dual-null.

## موج ۲ / Critique round 2 (experts A / B / C)

### A

1. Dual-null arms must not all collapse to `ard_like`, or “always ARD” cannot
   fail honestly.

### B

2. Parasite coevolution arm should be able to show label change across windows
   (transition_observed) without proving Red Queen.

### C

3. Attach without re-checking blocked Red Queen would be weak journal form;
   prereg required.

### Fixes (round 2)

- Structure-null + abiotic-only arms required; tests assert dual-null labels are
  not universally `ard_like`.
- Attach re-asserts `red_queen_proved` block and forces wet identity False.
- Preregistration digest required.

### Retest (round 2) — sign-off

Phase 19 green; BAIC pins and `engine.py` untouched; never proves Red Queen.
A/B/C sign-off: proceed to Phase 20.
