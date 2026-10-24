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
- The paired bootstrap 95% interval (10,000 draws, seed 12345) must agree in sign.

**(c) Coevolution is required.** At N = 200 and high virulence, the copassaged arm is lower than the fixed arm and lower than the frozen-replay arm:
- paired t, one-sided alpha 0.025 each;
- both paired bootstrap 95% intervals exclude 0.

**(d) Alternatives fail their own signatures.** All three are needed.
- *Mutation load:* in the no-parasite arms, the contrast of outcross minus self (extinction or terminal fitness) at host mutation 0.05 has a 95% interval that includes 0, or Spearman rho across the grid {0, 0.01, 0.05} is not positive at one-sided p < 0.05.
- *Diversity without cycles:* the frozen-replay arm does not reproduce the copassaged effect. Its frozen-minus-fixed interval includes 0 or has the opposite sign. In addition, at least one registered E4 time-shift window has a host or parasite effect whose 95% interval excludes 0, with the sign expected under cycling.
- *Fitness tax:* the uniform-tax-minus-fixed paired 95% interval includes 0 or has the opposite sign to the copassaged effect.

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

## Current blocking sites at 66f57a5

**Global ban.** `src/codontrace/claimgate/auditor.py:293`. The JR5 adapter needs an explicit exemption keyed to the JR5 verdict record. The ban stays for every other source.

**Constants that are always False:**
- `src/codontrace/experiments/models.py:27` (used at :46 and :103, and by `t05_red_queen.py:15`, :154);
- `src/codontrace/genesis/rq_mechanism_v2_phase3.py:117`;
- `src/codontrace/genesis/rq_bidirectional_timeshift.py:118`.

**Raises on True in `src/codontrace/claimgate/adapters/host_parasite.py`.** These are diagnostics and campaign adapters, not evidence paths, so they keep their raise:
`:729`, `:823`, `:894`, `:966`, `:1008`, `:1119`, `:1176`, `:1214`, `:1281`, `:1349`, `:1428`, `:1503`, `:1572`, `:1644`, `:1717`, `:1945`, `:2021`, `:2161`.

**Raises on True in other modules** (all diagnostics, all keep their raise):
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

**Forbidden-claims lists:**
- `src/codontrace/genesis/host_parasite_sim_fidelity_campaigns.py:680`
- `src/codontrace/genesis/host_parasite_diff_campaigns.py:605`
- `src/codontrace/genesis/host_parasite_diff_campaigns.py:697`
- `src/codontrace/genesis/host_parasite_cell_microbe_hard_campaigns.py:356`
- `src/codontrace/claimgate/adapters/host_parasite_prereg.py:17`, :55
