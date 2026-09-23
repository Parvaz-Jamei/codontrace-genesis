# Phase 19 review — ARD→FSD transition + cost-of-generalism digests

Human research review of a time-sliced ARD→FSD *transition protocol* with
cost-of-generalism proxies. Builds on Phase 5 labels without claiming wet
ARD/FSD identity. ``red_queen_proved`` stays False forever.

## What Phase 19 delivers

- `run_ard_fsd_transition_campaign` in `host_parasite_ard_fsd_transition.py`.
- Early/late slice digests per arm; parasite / structure-null / abiotic dual-null.
- Cost-of-generalism proxy from joint infectivity/resistance breadth.
- Falsification of `dynamics_always_ard_under_parasitism`.
- `attach_ard_fsd_transition` (prereg-bound).
- Tests in `tests/test_host_parasite_phase19.py`.

## Critique round 1

### Flaws found

1. **Phase 5 shipped ARD/FSD enums only** — no temporal transition protocol
   reviewers could attach.
2. **Cost-of-generalism (Koskella & Brockhurst synthesis) had no digital proxy.**

### Fixes

- Added early/late windowed slice digests with pairwise distinctness.
- Added non-negative cost-of-generalism proxy on every slice.

### Retest

Phase 19 green; hypothesis falsified under transition or dual-null; Red Queen
unproved.

## Critique round 2

### Flaws found

1. **Without dual-null**, “always ARD” could not fail honestly.
2. **Attach without re-checking blocked Red Queen** would be weak journal form.

### Fixes

- Structure-null + abiotic-only arms required; failure_reason recorded.
- Attach re-asserts `red_queen_proved` block and forces wet identity False.

### Retest

Phase 19 green; BAIC pins and `engine.py` untouched; never proves Red Queen.
