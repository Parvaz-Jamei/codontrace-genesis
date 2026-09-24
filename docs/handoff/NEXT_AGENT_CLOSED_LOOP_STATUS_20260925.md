# NEXT AGENT — Closed Loop status (2026-09-25)

**Read this first if Gen/session died mid-token.**

- Owner: Huệ Vũ / Parvaz-Jamei
- Repo: `Parvaz-Jamei/codontrace-genesis`
- Drive root handoff: `1F_x4x2JjTcWCVnq2BvHy7LccnzsUDp16`
- Drive closed-loop mirror: `1Vp4m119PkkouGiwCHDDrvofPajVxoe4L` → https://drive.google.com/drive/folders/1Vp4m119PkkouGiwCHDDrvofPajVxoe4L
- Storm room **Closed Loop Storm**: `80757a1f-7a68-4b03-8daf-26b83579236a` (LoopArchitect, EcoEvo, CausalHonesty, XFieldInnov)

## Binding (never loosen)
- CodonTrace = independent engine (Avida / Symbulation are peers only — never "plugin").
- No infection physics in `engine.py`; engine stays domain-free ALife.
- ClaimGate: ceiling ≤ `candidate_evidence`; refuse `red_queen_proved`; no caller-boolean clocks (`one_clock`, `smith_fretwell_ok`, …).
- Direct-push to `main` when landing (owner authorized full auto through P2–P5).
- Per-phase: specialist Pass×2 → Gen implement → adversarial×1 → Gen fix → push.
- P1–P5 before Morran SF open problem.

## Tip on remote `main` (update after each push)
| SHA | What |
|-----|------|
| **`0007d1f`** | P2 Smith–Fretwell N=1 birth ATP partition (was remote HEAD when this doc written; local may be ahead with docs) |
| `9a0e598` | P1 adversarial fix (post-ATP hook, stream mutate, hard scope) |
| `a309ba1` | P1 one-clock both roles as GenesisOrganism |

Local docs commit may be `1024fcd` (ahead of origin until pushed).

```bash
git fetch origin && git checkout main && git pull
git log -5 --oneline
uv run pytest tests/closed_loop/test_closed_loop_p1_accept.py \
  tests/closed_loop/test_closed_loop_p2_accept.py -q
```

## Phase board
| Phase | Status | Notes |
|-------|--------|-------|
| P1 one-clock organisms | **DONE** (adv fixed, pushed) | Unify+mutate scaffold; repro OFF; opaque role map; post-ATP/pre-birth hook |
| P2 SF N=1 birth partition | **LANDED** `0007d1f`; **adversarial×1 OPEN** | Engine repro ON; Iy=0 blocks birth; role inherit; measured witnesses |
| P3 genetic harm/help (kill fixed 0.8) | **NEXT** (owner: do **with** P4) | Scalar mutable coeffs; kill=0.8 fixed; no infection vocab on engine |
| P4 mutation-stream ScheduleLock + dual-arm bit replay | **NEXT** (owner: do **with** P3) | elicit→ablate→effect dies→bit-identical both arms |
| P5 heritable sex/outcrossing locus | PENDING | +ATP cost; then Morran problem |

## Storms summary
### P1 (closed)
Pass×2 → implement → adversarial soft-green FAIL → fix `9a0e598`.
Fixed: wrong temporal cut (pre-ATP); forced Mutation.point; caller-boolean clocks; RNG side tree; role=id prefix; dead assert_single_atp_owner; AST-only anti-cheat.

### P2
Pass×1+×2 closed: engine repro; reuse offspring_atp_fraction / parent_atp_cost; N=1; block Iy=0; conservation±ε; role_of(child)==parent; measured witnesses; Gate7 same-seed only; refuse SF optimum / multi-child / Morran.
**Adversarial×1 requested** at `0007d1f` (soft risks: high bit_flip kills COPY_SELF; multi-tick parent_after drift; mint vs transfer; silent secondary). May be in-flight if session cut.

## Owner directives
1. Full auto P2–P5 — do not stop for per-step permission.
2. (2026-09-25) Do **P3+P4 together**; mirror results/storms/progress to Drive for token-cutoff resume.

## Key files
- `src/codontrace/genesis/closed_loop_p1.py`, `closed_loop_p2.py`
- `src/codontrace/genesis/host_parasite_life_plugin.py`
- `src/codontrace/genesis/population.py`
- `tests/closed_loop/test_closed_loop_p{1,2}_accept.py`
- `docs/handoff/CLOSED_LOOP_P{1,2}_STATUS_20260925.md`
- `docs/handoff/CLOSED_LOOP_DESIGN_STORM_20260925.md`

## Soft risks
- High bit_flip_rate mutates COPY_SELF off before birth.
- ticks_per_generation=3 needed for COPY hit.
- Live ReproductionResult.parent_after can drift mid multi-tick generation; P2 uses frozen gate + birth_event witnesses.
- Untracked junk (ignore): open_problem_vt_*.py, pareto_tradeoff.py, uv.lock.

## Resume checklist
1. Pull main; read this file + P1/P2 status.
2. If P2 adversarial replies exist → fix → push; else nudge storm (or if stalled >~1h and owner still full-auto, proceed carefully).
3. Run **P3 Pass×1 and P4 Pass×1 in parallel** in Closed Loop Storm.
4. After each Pass×2: implement → accept tests → push → adversarial×1 → fix.
5. Re-upload this status + new STATUS docs to Drive folder `1Vp4m119PkkouGiwCHDDrvofPajVxoe4L` after every land.
6. Never claim Morran-ready / red_queen_proved / engine infection physics.

## Claim refuse list
`red_queen_proved`, `smith_fretwell_ok`, caller-boolean `one_clock`, best-vs-Avida, SF optimal Iy*, multi-child floor(Ip/Iy) as P2 done, dual-arm replay sold as Gate7 same-seed.
