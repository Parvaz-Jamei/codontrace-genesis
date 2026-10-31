# JR5 evidence-gated path for `red_queen_proved`

This replaces the permanent ban. Phase 1 documents it only. The adapter is built and reviewed in phase 2c (see PREREG.md section 10). Until then, every site listed below still refuses the flag.

## The single path

A new JR5 verdict adapter in `codontrace.claimgate` sets `red_queen_proved = True` only if every one of (a) to (e) holds. Otherwise it returns the matching typed outcome from PREREG.md section 2, and the flag stays `False`.

**(a) Cost gate.** E1 TOST passes at sex ratio 0.5 and at 0.25:
- the 90% interval lies inside [1.8, 2.2] and inside [1.2, 1.4667];
- each 95% interval excludes 1.

**(b) Invasion, both population sizes.** At N = 200 and separately at N = 50, the E2 high-virulence test (copassaged minus fixed, paired t, two-sided) is significant after Holm correction at family alpha 0.05, with copassaged lower than fixed.
- The family is the four tests {N200 high, N200 low, N50 high, N50 low}.
- Both high-virulence tests must pass.
- For each of the two, the paired t test and the paired BCa bootstrap interval (10,000 resamples, seed 12345) at the Holm-adjusted level of that test's step (98.75% at step 1, down to 95% at step 4; PREREG.md section 3) must both be significant, in the same direction. Any disagreement makes the result `inconclusive` and the flag stays `False`.

**(c) Coevolution is required.** At N = 200 and high virulence, the copassaged arm is lower than the fixed arm and lower than the frozen-replay arm:
- paired t, one-sided alpha 0.025 each;
- both paired BCa bootstrap two-sided 95% intervals (10,000 resamples, seed 12345), the level that matches one-sided alpha 0.025 (these two tests are not in the Holm family), exclude 0 on the same side as the t test. Any disagreement makes the result `inconclusive`.

**(d) Alternatives are ruled out.** All three are needed. A non-significant result does not rule an alternative out. Each one is ruled out only by an equivalence result or by an effect in the opposite direction, both with 60 paired seeds at N = 200:
- *Mutation load:* in the no-parasite arms at host mutation 0.05, the paired outcross-minus-self log terminal-fitness ratio has a 90% interval inside ±log 1.1 (±0.0953), or a 95% interval entirely below 0.
- *Diversity without cycles:* the frozen-minus-fixed paired difference of terminal uniparental frequency has a 90% interval inside ±0.10, or a 95% interval entirely on the opposite side of 0 from the copassaged effect. In addition, at least one registered E4 time-shift window has a host or parasite effect whose 95% interval excludes 0, with the sign expected under cycling.
- *Fitness tax:* the uniform-tax-minus-fixed paired difference has a 90% interval inside ±0.10, or a 95% interval entirely on the opposite side of 0 from the copassaged effect.
- Sensitivity at 60 seeds (PREREG.md section 7): MDE 0.368 SD of the paired difference; equivalence power at ±0.10 is 0.84 at SD 0.25. If an alternative is neither ruled out nor detected, (d) fails.

**(e) Replay.** Every run in (a) to (d):
- verifies its replay digest;
- has an ATP ledger residual of at most 1e-9;
- has a one-shot versus resume scientific body that matches.

All sealed-lock replays named in PREREG.md section 9 must also verify.

## Adapter tests (phase 2c)

- A planted full RQ signal gives `True`.
- Each planted alternative gives `False` with its typed outcome: load, diversity without cycles, tax, and none.
- Each single failed condition (a) to (e), with the other four passing, gives `False`.
- A hand-set `red_queen_proved=True` on any input is refused.
- `assert_claim_allowed("red_queen_proved")` is passed only with a verified JR5 verdict record whose conditions (a) to (e) all hold. A test shows that every other caller, and the JR5 adapter with any other verdict, still raises.
- The existing tests that pin the block stay and keep passing (see below).

## Gates that phase 2c must change

Both get the same JR5-only exemption. Each keeps blocking every other path.

1. **Profile block.** `src/codontrace/claimgate/domain.py:118`: `"red_queen_proved"` is in `HOST_PARASITE.blocked_claims`. `assert_claim_allowed` in `src/codontrace/claimgate/adapters/host_parasite.py:87-99` raises on any claim in that set. This is the gate that refuses the flag on the host_parasite profile.
   - Design: `blocked_claims` keeps `red_queen_proved`. The 2c adapter calls a separate check that accepts the claim only when it is given a JR5 verdict record that verifies (record digest equal to `record.json`, all five conditions true). `assert_claim_allowed` itself is unchanged, so every existing caller still raises.
   - The 2c adapter must provably reach a pass only through the JR5 verdict: a test with each single condition false, and one with a forged or unverified record, must raise.
   - Tests that pin the block and must keep passing: `tests/test_claimgate_host_parasite.py:45`; `assert_claim_allowed("red_queen_proved")` raise tests at `tests/test_host_parasite_phase19.py:45`, `tests/test_host_parasite_type3_rare_lock.py:64`, `tests/test_host_parasite_dk_region_map.py:48`, `tests/measurements/test_rq_frequency_clocks.py:93`, `tests/closed_loop/test_closed_loop_hp_arm01.py:57`, `tests/closed_loop/test_closed_loop_hp_arm01_confirm.py:74`, `tests/closed_loop/test_closed_loop_hp_arm01_rq_earn.py:62`, `tests/closed_loop/test_closed_loop_hp_arm01_rq_earn_confirm.py:50` and `:197`, `tests/closed_loop/test_closed_loop_hp_arm01_persistence.py:113`, `tests/closed_loop/test_closed_loop_pearl_spc.py:39`, `tests/closed_loop/test_closed_loop_p6_accept.py:126`.
   - `tests/test_jr5_prereg.py` pins that the gate blocks `red_queen_proved` today.
2. **Global ban.** `src/codontrace/claimgate/auditor.py:293` adds `red_queen_proved` to the forbidden set. The JR5 adapter needs an explicit exemption keyed to the same verified JR5 verdict record. The ban stays for every other source.

## Other sites that refuse the flag at 66f57a5

These are diagnostics and campaign paths, not evidence paths. They stay untouched and keep refusing. The lists are not exhaustive: there are about 34 forbidden-claims lists and about 40 constant-False sites in total, and every one of them, listed here or not, stays as it is.

**Raises on True in `src/codontrace/claimgate/adapters/host_parasite.py`** (line of the raise):
`:729`, `:823`, `:894`, `:966`, `:1008`, `:1119`, `:1176`, `:1214`, `:1281`, `:1349`, `:1428`, `:1503`, `:1572`, `:1644`, `:1717`, `:1945`, `:2021`, `:2161`.

**Multi-flag raises in the same file** (line of the `if`; the raise is on the next line): `:1794`, `:1872`, `:2089`, `:2239`, `:2318`, `:2400`, `:2470`. Three of them also call `assert_claim_allowed("red_queen_proved")` (`:1877`, `:2326`, `:2476`).

**Raises in the arm01 modules** (line of the `if`):
- `src/codontrace/genesis/closed_loop_hp_arm01.py:1289`
- `src/codontrace/genesis/closed_loop_hp_arm01_confirm.py:319`
- `src/codontrace/genesis/closed_loop_hp_arm01_mating.py:650`
- `src/codontrace/genesis/closed_loop_hp_arm01_persistence.py:581`
- `src/codontrace/genesis/closed_loop_hp_arm01_rq_earn.py:393`
- `src/codontrace/genesis/closed_loop_hp_arm01_rq_earn_confirm.py:984`
- `src/codontrace/genesis/closed_loop_hp_arm01_selfing_hold.py:744`

**Raises on True in other modules:**
- `src/codontrace/genesis/host_parasite_metrics.py:277`
- `src/codontrace/genesis/host_parasite_wave6_smoke.py:285`
- `src/codontrace/genesis/host_parasite_he_hp_refresh.py:133`
- `src/codontrace/genesis/campaigns/discovery_q_20260928_measurement.py:181`
- `src/codontrace/genesis/campaigns/discovery_q_20260928_jsonl_track_c.py:227`
- `src/codontrace/genesis/campaigns/discovery_q_20260928_jsonl_campaign.py:192`
- `src/codontrace/genesis/campaigns/discovery_q_20260928_jsonl_smoke.py:170`
- `src/codontrace/genesis/campaigns/discovery_q_20260928_jsonl_engine.py:288`
- `src/codontrace/genesis/rq_mechanism_v2_phase6.py:1074`
- `src/codontrace/genesis/host_parasite_attach_registry.py:195`
- `src/codontrace/genesis/host_parasite_calibration.py:232`
- `src/codontrace/genesis/host_parasite_analytics.py:433`
- `src/codontrace/genesis/host_parasite_analytics.py:750`
- `src/codontrace/genesis/host_parasite_analytics.py:978`
- `src/codontrace/genesis/host_parasite_analytics.py:1254`
- `src/codontrace/genesis/host_parasite_analytics.py:1538`

**Examples of forbidden-claims lists:**
- `src/codontrace/genesis/host_parasite_sim_fidelity_campaigns.py:680`
- `src/codontrace/genesis/host_parasite_diff_campaigns.py:605`
- `src/codontrace/genesis/host_parasite_diff_campaigns.py:697`
- `src/codontrace/genesis/host_parasite_cell_microbe_hard_campaigns.py:356`
- `src/codontrace/claimgate/adapters/host_parasite_prereg.py:17`, :55

**Examples of constants that are always False:**
- `src/codontrace/experiments/models.py:27` (used at :46 and :103, and by `t05_red_queen.py:15`, :154);
- `src/codontrace/genesis/rq_mechanism_v2_phase3.py:117`;
- `src/codontrace/genesis/rq_bidirectional_timeshift.py:118`.
