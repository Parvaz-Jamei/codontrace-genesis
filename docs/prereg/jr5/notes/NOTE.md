## 2026-11-21 15:27 +03 — Disk status

`/tmp/rqm-horizon-clock/NOTE.md` (245 lines; last written 2026-11-21 15:18 +03, RM-5) was lost during a box copy-in that finished at 15:26 +03. The persistent store hydrated 924250 files; `/tmp` is not in that store, and no copy of the note was found under `/workspace` or the agent store. A byte check of the earlier 188 lines is therefore impossible.

The RM-5 section below is restored from the work record of the 15:18 write, not from disk, and is labelled as such. The Task A (14:59) and RM-4 (15:09) sections are not reconstructed here. From this point the canonical copy is `/workspace/rqm-horizon-clock/NOTE.md`, also mirrored at `/tmp/rqm-horizon-clock/NOTE.md`.

## 2026-11-21 15:32 +03 — Restore of Task A and RM-4

The two sections below are reconstructed from the work record of the original run (the surviving prefixes and suffixes of the write commands, plus that run's final report). Each is labelled. They are not byte-identical copies of the lost file. The stored write commands were truncated at about 4,000 characters, so the span between each cut is filled from the final report. The disk-status section above is left as written at 15:27. The RM-5 and RM-6 sections that follow are unchanged.

# JR5 E2/E5 horizon clock (RQM, read-only review)

**Restored 2026-11-21 15:32 +03 from the work record of the 14:59 write, not from disk, and not a byte-identical copy of the lost file.** The write command was truncated in the record at "the parasi…ded as a check"; the span between those cuts is filled from that run's final report. Headings use the original file timestamps.

Scope: recommendation for the E2/E5 generation clock and the section 6 horizon rule. Read-only: no repo edit, commit or push. One core (taskset -c 0, numpy, OMP/BLAS threads 1). No engine run of any kind, no registered or sealed seed, no smoke log_w. Private seeds 20261121, 20261131, 20261132. Newest plan files read on /workspace/jr5-p4 at ff5010e (branch jr5/phase4-pilot; remote tip identical). That checkout carries uncommitted coder edits in src/codontrace/campaigns/jr5_realised_w_pilot.py and tests/test_jr5_realised_w_pilot.py (the discrete_uniform_census model); they were read, not touched. Line numbers below are at ff5010e. PREREG/JSON/DEVIATIONS are identical in content to jr5-p2c (c547392) and jr5-p3 except where noted; the packaged copy src/codontrace/claimgate/data/jr5_prereg_constants.json is identical to docs/prereg/jr5/jr5_prereg_constants.json.

Files here: clock_sim.py (+clock_sim_results.json, clock_sim.log), delay_sim.py (+delay_sim_results.json), src/ (copies of opened sources, abstracts.txt).

## 2026-11-21 14:59:04 +03 — Findings, High/Medium first

**H1 (High). The parasite schedule is per engine step, so the discrete clock cuts infection pressure per host generation by the host lifespan in steps unless it is re-registered.** In LifeLoopEcologyArm one run_generations(1) step does: host step, one contact round, one passage, census (closed_loop_hp_arm01.py:958-976). Contact pairs parasite i with hosts[i % len(hosts)] (:867-871), so each step makes at most P contacts (default P = 8, :131, :627; selfing-hold constants also P = 8). Contacts per host per host generation = P·L/N, L = host lifespan in steps. Overlapping with L ≈ 70 (the RQ-v2 host replacement): 2.8 at N = 200. Discrete (L = 1): 0.04 at N = 200, 0.16 at N = 50 (clock_sim_results.json part3). To hold a uniparental line with per-generation advantage 1/(1-m) the parasite pool must infect enough of the sexual hosts. Even with perfect targeting, P = 8 can hold a w = 2 line only at p ≤ P/(mN) = 0.08 at N = 200 (0.32 at N = 50), below the intro frequency of 0.2. P, the low/high virulence values and parasite mutation are not pinned anywhere in PREREG or the JSON. They need pinning together with k (contact-and-passage rounds per host generation). Pin c = kP/N equal at both N. Without that, E2 and E5 are close to null by construction, and the N = 200 vs N = 50 contrast also becomes a parasite-pressure contrast.

**H2 (High). Option (b) has no single conversion factor.** In an overlapping vacancy model with m = 0.5 and d = 1/69.5 (clock_sim):
- The asexual advantage per replacement time depends on frequency: 2.67 at p = 0.01, 2.29 at 0.2, 1.95 at 0.5, 1.75 at 0.8 and 1.67 at 0.95.
- Converting with the Felsenstein generation time instead gives 1.64–1.81.
- At m = 0.25 the range is 1.29–1.39.
- That spread is wider than the ±10% E1 margin. The per-step cost of sex also rises with host mortality (Lively 2010, abstract), and mortality differs between parasite arms, so the E2 contrast would carry an arm-dependent cost that E1 never measured.

**H3 (High, likely, not checked on the engine). An overlapping clock can make section 6 refuse the design.** Host replacement is measured with passage absent (rq_mechanism_v2_phase6.py:1111-1113, :1134), so it is set by ATP death alone. RQ-v2 got 69.5 on a different harness, and Genesis reported no births in 5 steps at K = N. With selfing-hold-like constants (birth ATP 48, basal 0.05 per tick, 2 ticks per step), starvation alone takes up to about 480 steps. That is over the cap of 200, so section 6 would refuse the design.

**M1 (Medium). The fitness-delay rule measures drift.** The RQ-v2 probes used different seeds (9808 and 9809). Under a neutral null, the discrete clock gives median 2, p95 16, 0.36% of draws above 100 and 0.66% unmeasurable (delay_sim). An RQ-v2-like birth rate gives median 5 and p95 22, so RQ-v2's delay of 9 sits inside the noise. JR5 hosts have no A/B parent tags (:640-651), so the sign needs a JR5 definition. Ideally both probes share a seed, and the neutral null is reported next to the result.

**M2 (Medium). The E4 windows are pinned to RQ-v2's clock.** claimgate/jr5_verdict.py:107 hard-codes E4_WINDOW_GENERATIONS = (67, 70). Under the discrete clock the lag is 1 (rq_mechanism_v2_phase6.py:164), so this note's first wording set the windows to H-2, H-1 and H. The adapter rejects any other window (:1154-1155). This problem exists under either clock.

**M3 (Medium). The horizon function can't be reused as is.** choose_phase6_horizon refuses any budget other than 70 (:57, :152-153). JR5 needs its own version with floor 100, cap 200 and refuse-not-shorten.

**M4 (Medium). The order within a generation must be registered.** The order of birth, contact, passage, thinning and census decides soft versus hard selection, and therefore whether E5 extinction can happen at all.

**M5 (Medium). Contact targets are positional, not random.** Parasite i contacts hosts[i % len(hosts)] (:871), so the first P hosts in population order are always hit. A random draw from an RNGManager fork would make the schedule clock-neutral.

**L1 (Low).** Under the discrete clock the fixed arm reaches p = 0.998 by generation 11, so E2 becomes a question of whether copassage prevents fixation. The E2 SD planning values of 0.25–0.30 are unverified for that setting. By contrast, overlapping H = 100 is about 1.4 host generations and only reaches p ≈ 0.43.

**L2 (Low).** The type of the mixed-invasion mutant is not pinned (self_mode is null). If it is a selfer, PREREG:31 says its advantage is not 1/(1−m).

## 2026-11-21 14:59:04 +03 — Literature (opened) and what could not be opened

Full text opened:
- Gokhale et al. 2013 (BMC Evol Biol, PMC4225518)
- Haller & Messer 2019 (MBE, PMC6389312) plus its supplement
- Wakeley, coalescent chapter 3 PDF
- Allendorf & Ryman 2026 (Evol Appl, PMC13346920)
- MacPherson & Otto 2018 (author reprint)

Abstracts only, via Europe PMC:
- Lively 2010 (Ecology 91:3-6)
- Hamilton, Axelrod & Tanese 1990
- Decaestecker 2007 (Nature 450:870)
- Salathé 2008 (Evolution 62:295)
- Agrawal 2009 (Evolution 63:2131)
- Ashby & King 2015 (J Evol Biol 28:511)

Search-index text only, not cited for numbers: the Agrawal 2009 body, the Lively 2010 per-step cost formula and Felsenstein 1971 (its PMC page is page scans).

Not opened: Hamilton 1980; the Lively, Salathé, Agrawal, Ashby & King and Decaestecker full texts (Wiley returned 403 and the Agrawal lab PDF a 404); the SLiM manual.

## 2026-11-21 14:59:04 +03 — Recommendation

Use a hybrid clock. Every JR5 host arm (E1, E2, E5, the alternative arms and the phase 4 pilot) should run on E1's discrete clock: parents removed each generation, uniform thinning to N, K = 3N, no refusals. On top of that, the parasite schedule per host generation has to be registered before any pilot seed runs. The only change from Genesis's option (a) is that last part, and it is essential (H1). Overlapping E2/E5 with a conversion factor (option (b)) is rejected (H2, H3).

## 2026-11-21 14:59:04 +03 — H under the recommended clock

Everything is in host generations, where one generation is one discrete step.
- **Host replacement:** census divided by recruits kept after thinning, using the replacement_time function at :580-596. It is 1 by construction and should be recorded as an invariant check.
- **Parasite replacement:** from the coevolve probe, it is 1/k, so 1 when k = 1.
- **Fitness delay:** the RQ-v2 rule, run on 200-generation probes on pilot seeds 13901–13930. Ideally both probes share a seed, and the neutral null is reported next to the result.
- **Result:** H = max(100, ceil(max(1, 1/k, delay))) gives 100 unless the delay is over 100, with refusal above 200. The lag is 1, and the registered E4 windows are H-2, H-1 and H.
- **Compared with the old budget:** it is the same 100 steps, but that now means about 100 host generations instead of about 1.4. The step cost rises because each step makes up to 3N offspring. An unmeasured guess is 75–150 CPU-hours for the N = 200 part instead of 22.5. The pilot has to re-time this; seeds are not cut.

## 2026-11-21 14:59:04 +03 — Lines touched (jr5-p4 at ff5010e)

- **PREREG.md:** :54-62, :66, :67, :72-75, :98-101, :108-110, :114-118, :162-167, :175 and :190-192.
- **JSON:** the e2 block :108-136, horizon :149-154, host_mating_arm_modes :171-306, timing_basis :504-513 and budget :514-523, plus new parasite-schedule keys. The same edits apply to the packaged copy src/codontrace/claimgate/data/jr5_prereg_constants.json, which is identical, and to jr5_deviations.md, record.json and DEVIATIONS.md.
- **Code and tests:** jr5_verdict.py:107, rq_mechanism_v2_phase6.py:57/139-180/599-660 and tests/test_jr5_prereg.py:205-226.

## 2026-11-21 14:59:04 +03 — Risks

- Parasite dynamics, from H1, M4 and M5. Contacts now hit only newborns, which hold 0.25 of the parent's ATP, so virulence has to be chosen for this clock.
- Budget and wall time.
- RQ-v2 values (H 70, replacement times 2.92 and 69.5, delay 9, lag 3) don't carry over; only the method does. Sealed replays stay valid only if the discrete mode is off by default.
- The frozen-replay and time-shift arms move to lag 1, and the adapter's E4 windows must move with them.
- With the delay rule measuring noise, H will almost always be the floor of 100.
- The claim path depends on parasites overcoming a twofold cost per generation, which is unreachable if H1 isn't fixed.
- The deviation must be logged before any pilot seed runs, including the pilot runner's required line "- Pilot seeds run before this entry: none."

## 2026-11-21 14:59:04 +03 — DEVIATIONS draft (plain prose; fill the bracketed values)

## [date]: one generation clock for every JR5 host arm, and the horizon in host generations

- Reason: one generation clock for every JR5 host arm, so the realised E1 cost sits next to every maintenance statement in the same units. Lively 2010 (abstract): the per-step cost of sex rises with host mortality, and mortality will differ between parasite arms under an overlapping clock.
- Parasite schedule: P, k, c = kP/N (equal at both N), a random contact draw, the order within a generation, and the virulence and mutation values, all pinned before any pilot seed.
- The horizon measurement rule. Host replacement is census divided by recruits kept after thinning (replacement_time at :580-596). It is 1 by construction and should be recorded as a check. Parasite replacement is the parasite census over parasite births per host generation from the coevolve probe, [1/k]. The fitness delay is the RQ-v2 phase 6 rule on probes of 200 host generations on pilot seeds, with the sign defined as [definition]. H = max(100, ceil(max(host replacement, parasite replacement, fitness delay))), cap 200, refused above the cap and not shortened. Unless the delay exceeds 100, H is 100 host generations. The primary lag is max(1, round(parasite replacement)) = [1], and the registered E4 windows are H - 2, H - 1 and H; the windows 67 and 70 taken from RQ-v2 phase 6 are in that study's overlapping steps and are replaced.
- Budget: H = 100 is the same number of steps as before, but each step now makes up to 3N offspring before thinning. Seconds per generation are measured again in the phase 4 pilot on pilot seeds. Seeds are not cut; the run is scheduled longer (section 7).
- Comparability: the RQ-v2 phase 6 values (horizon 70, replacement times 2.92 and 69.5, delay 9, lag 3) are in overlapping steps of another harness. Only the method is reused. With the flag off every sealed lock still replays byte-identically.
- Files: PREREG.md, jr5_prereg_constants.json, DEVIATIONS.md, record.json, and the packaged copies under src/codontrace/claimgate/data/.
- Record digest: [old] -> [new]
- Pilot seeds run before this entry: none.
- Runs: no JR5 run has started, the pilot included, so no endpoint moves to exploratory.

## 2026-11-21 14:59:04 +03 — Not checked

- No engine run: host lifespan in steps under JR5 settings, the per-step cost of the discrete mode, and the order of next_organisms were not measured.
- The coder's uncommitted discrete_uniform_census code was read for intent only, not reviewed or tested.
- No E2/E5 simulation with a coevolving parasite (matching alleles); H1 is an upper bound from contact counts, not a full model.
- Not duplicated: the male-as-mother fix and smoke blinding (coder), R51 (tester).

## 2026-11-21 15:09:58 +03 — RM-4: a priori parasite schedule for the discrete clock

**Restored 2026-11-21 15:32 +03 from the work record of the 15:09 write, not from disk, and not a byte-identical copy of the lost file.** The write command was truncated in the record at "it is an ATP loss…of the energy design"; the span between those cuts is filled from that run's final report. Two line-number corrections applied to the original file after the write (fuse_gametes, birth.py:1692-1716; _passage_update_standing :1057-1115) are included here. The heading timestamp is the one later read from the lost file (15:09:58), not the 15:08:59 clock reading taken just before the write.

Scope: read-only on /workspace/jr5-p4, 1 core, numpy/analytic only (schedule_calc.py, schedule_calc_results.json), no engine run, no registered seed, no log_w, nothing tuned on a simulated w or a maintenance probability. Checkout note: jr5-p4 HEAD is now be7d058 (local commit "R51: blind smoke outputs, discrete census model wired", not on origin, which is still ff5010e); engine files cited below are unchanged between ff5010e and be7d058 (the diff touches only CHANGELOG.md, jr5_realised_w_pilot.py and two test files), so the line numbers hold for both. File paths are under src/codontrace/genesis/ unless stated.

### Engine mechanics read (facts used below)

- Step order in LifeLoopEcologyArm.run_generations: refill, host step, record births, contact, passage, census (closed_loop_hp_arm01.py:958-976). One contact round and one passage per step.
- Contact (:851-908): seats reset each round (:859, _reset_env_hosts :845); parasite i goes to hosts[i % len(hosts)] (:871). Infection needs task overlap, i.e. the parasite window equals the host window exactly (host_parasite_env.py:264-277; tasks are "allele_"+window). One seat per host per round: a later parasite on an occupied seat is refused (seat_occupied, host_parasite_env.py:375-389), so exposures do not stack within a round; seats reset next round, so they would stack across rounds.
- Damage: steal = 1 - retained = min(1, steal_fraction / resource_productivity) with interaction -1, productivity 1, handling 0 (host_parasite_env.py:427-460, :453), so debit D = virulence × steal_fraction ATP per infection (closed_loop_hp_arm01.py:883-884), paid as min(ATP, D) (:886). A host with ATP <= 0 after the round is removed (:899-907). Infection is therefore lethal exactly when D >= the host's ATP at contact; otherwise it is an ATP loss only. Defaults are virulence 8.0, steal_fraction 0.8, parasite_n 8, parasite_mutation 0.5 (:623-631).
- Newborn ATP: a child gets (parent ATP − 1) × 0.25 (population.py:2618). Later children of the same mother get less: 9.75, 7.06, 5.05 from a 40-ATP mother (schedule_calc.py). From a 48-ATP mother the first child has 11.75 ATP, so the default D = 8 × 0.8 = 6.4 is not lethal against a first-born recruit.
- Passage: P new windows are drawn from the windows of infected hosts; each mutates with probability μ by flipping one random bit of the 6 (:575-581, :910-930). The fixed arm resets every window to the most common founder window (:914-916, :566).
- Host genotype under diploid meiosis: the 6-bit window is an ordered pair of 3-bit alleles, one from each gamete (birth.py:1619-1642; fuse_gametes, birth.py:1692-1716). Host mutation is 0 in this arm (:743), so the only host alleles are the founders'.
- Founders in this arm (:146-157) carry alleles 000 and 111, so host windows are 3 or 6 bits apart. A single bit flip never reaches another host genotype, and passage keeps only matched windows.

### Issues first

- **H1. Two incompatible infection models, and neither is pinned.** The timing basis and the realised-w pilot use LifeLoopEcologyArm: exact matching, all parasites replaced each round, lag 1. RQ-v2 phase 6, whose E4 method JR5 reuses, used StructuralRQArm: partial matching where any shared bit causes damage, half the parasite pool kept (STRUCT_KEEP_FRACTION 0.5, :122; _passage_update_standing :1057-1115), lag 2 (closed_loop_hp_arm01_structural_rq.py:122, :279-301, :884-941).
- **H2. With the default founders, parasites cannot track hosts by mutation.** The founders (:146-157) carry alleles 000 and 111, so the host windows are 3 or 6 bits apart. A single bit flip never reaches another host genotype, and passage keeps only matched windows. Parasites can move only after a round with no match at all, which gives sweep-and-search dynamics rather than tracking. Founder windows and host mutation for E2/E5 are not pinned.
- **H3. Contact before thinning ties exposure to fecundity.** Hitting the up-to-3N offspring pool dilutes exposure per host in more productive populations, which biases E2 toward the uniparental line. Contact after thinning gives exactly c exposures per host in every arm.

- **M1.** k>1 stacks damage across rounds, on top of shortening the parasite generation time.
- **M2.** High virulence can be made reliably lethal. Low virulence cannot be made reliably sublethal, because the smallest newborn can have as little as 0.55 ATP (schedule_calc, parent ATP 8).
- **M3.** The fixed arm's target depends on the founder design and how ties are broken. The heat-killed and frozen-replay arms have no passage mode in this arm (:105-109); that is coder work.
- **M4.** The passage random stream is separate per arm (:962), so a contact lottery with no arm in its stream name would let paired arms share draws and tighten the E2 contrast.
- **M5.** The parasite archive is written after passage (:968-971), so "contemporary" parasites for E4 need defining.

- **L1.** With P=50 at N=50, the parasite pool's neutral drift time (about 50 generations) is shorter than H. Selection dominates, so no change.

### Recommended schedule (a priori)

- **k = 1.** Lag is 1 for any k ≥ 1 and H stays at the floor, so k>1 gains nothing and stacks damage. It is the conservative case per Salathé 2008 / Agrawal 2009 (abstracts).
- **P = N (200 and 50).** Keeps c the same at both N. This P/N of 1 matches RQ-v2's 64 parasites for 64 hosts.
- **c = kP/N = 1.0.** At most 1−e^−c ≈ 0.63 of a fully matched line is removed per generation (exact: 0.633 at N=200, 0.636 at N=50; schedule_calc). It must reach m, so c ≥ −ln(1−m): 0.69 at m=0.5, 0.29 at m=0.25. A fully matched single-genotype population doesn't collapse deterministically while c ≤ ln F, where F is offspring per breeding host. c=1 sits inside [ln 2, ln 3].
- **Contact lottery:** RNGManager(run seed, "jr5-contact").fork("g<gen>/r<round>"), no arm in the name. Hosts sorted by id, P draws with replacement, so each host's exposure is about Poisson(c). P>N needs no special case, and the engine's one-seat rule stays.
- **Order:** host step → thin to N with the E1 fork → contact → remove ATP ≤ 0 → passage → census. This is E1's order with contact and passage added, so E1 and E2/E5 share every step. Uniform thinning doesn't erase selection. Contact kills are hard selection within the generation, and E5 extinction becomes possible.
- **High virulence:** lethal on every match: D above an upper bound of newborn ATP from the energy design, plus a run-time check that every match killed. Lethal is the only damage whose fitness cost is known without the engine (s=1). Red Queen models need severe effects (Howard & Lively 1994, Lively 2009), and the cost is twofold for annual hosts (Lively 2010).
- **Parasite mutation μ = 0.25** per new parasite per passage (one bit flip). 75% of new parasites stay faithful. Supply to a given 1-bit neighbour per passage is Pμ/6 = 2.1 at P=50 and 8.3 at P=200. This is RQ-v2's value, and it only helps if founder alleles are 1 bit apart (H2).

### Decisions the owner still needs to make

- **OD1, infection model:**
  - Exact matching (LifeLoopEcologyArm): lag 1 and strong genotype specificity.
  - Partial matching (StructuralRQArm): consistent with RQ-v2, lag 2, but weak specificity, close to the uniform-tax arm.
- **OD2, founder alleles and host mutation:**
  - Alleles 1 bit apart, so parasites can track.
  - Keep 000/111 and add host mutation (RQ-v2 used 0.02).
  - Keep the defaults and state sweep-and-search as a design property.
  - Also choose which genotype the uniparental mutant carries, since the fixed arm attacks only the ancestral window.
- **OD3, low virulence:**
  - (a) a debit below the median newborn ATP of the energy design, accepting that some late-born recruits die (cost not known a priori); (b) a probabilistic lethal infection (kill with probability q per match), which needs harness code but gives a known s = q, for example q = 0.25 against the 0.5 threshold; (c) drop the claim that low is sublethal and state it as "lower debit".
- **OD4, fecundity:** the c window [-ln(1 - m), ln F] needs F from the coder's max-births report; if F <= 2, choose between losing the no-collapse condition and lowering c below ln 2.
- **OD5, k > 1 for a parasite generation-time advantage:** not recommended (above); if wanted, contact must be separated from passage so parasites can adapt without extra host debit (the Salathé-type life cycle), which is new harness code.
- **OD6, energy design:** steal_fraction, birth_atp, bolus and patches set recruit ATP and hence what "lethal" and "low" mean; they must be pinned together with virulence.

### Literature opened for this section

Abstracts via Europe PMC: Howard & Lively 1994, Nature 367:554-557; Peters & Lively 1999, Am Nat 154:393-405 (epistasis sign changes every two to five generations); Otto & Nuismer 2004, Science 304:1018-1020 (species interactions typically select against sex); Lively 2009, J Evol Biol 22:2086-2093; Engelstädter 2015, Am Nat 185:E117-E129; Reznick 2016, J Hered 107:3-14. Earlier sections: Lively 2010, Salathé et al. 2008, Agrawal 2009 (abstracts). Not opened: Wallace's original papers, Hamilton 1980, any full text of the above.

### Not checked

No engine run, so recruit ATP distributions, F, and the effect of a sublethal debit are unmeasured. The inheritance of the outcross locus (codon 5, odd homolog, paired with program codon 4) under fusion was noticed while reading birth.py and not followed up; it belongs to the coder's male-fix work. Task B waits on the coder's push.

## 2026-11-21 15:18 +03 — RM-5: founder counts, E4 contemporary pairing, uniform-tax rule (a priori, locked schedule)

**Restored 2026-11-21 15:27 +03 from the work record of the 15:18 write, not from disk. Not a byte-identical copy of the lost file.**

Checked against local checkout `544a3d5` (two local pilot-runner commits on top of origin `ff5010e`; they touch only `src/codontrace/campaigns/jr5_realised_w_pilot.py` and tests, not `src/codontrace/genesis/`). No engine run, no registered seed, no `log_w`, 1 core. Founder counts come from `founder_counts.py` (pure Python). Locked decisions (OD1 to OD3, k=1, P=N, c=1.0 provisional on F, μ=0.25, order, lottery fork) are recorded as given and not reopened.

### Issues first
- **M1 (E4 window shape).** `E4_WINDOW_GENERATIONS = (67, 70)` (`src/codontrace/claimgate/jr5_verdict.py:107`) is the primary pair (horizon − lag, horizon), not a triple. The phase 6 estimand (`jr5_verdict.py:100-105`, `src/codontrace/genesis/rq_mechanism_v2_phase6.py:537-541`) uses H and H − lag. With lag 1 it becomes **(H − 1, H)**. The triple (H − 2, H − 1, H) is the oscillation time set (`rq_mechanism_v2_phase6.py:264-274`), not the E4 window.
- **M2 (E4 score path).** RQ-v2's infectivity replay `replay_archived_contact` (`src/codontrace/genesis/rq_bidirectional_timeshift.py:405-460`) builds `ARM_C` with the Structural constants (graded affinity). That conflicts with OD1. JR5 needs a score that uses exact matching (rule E4.5 below).
- **M3 (archive timing).** The census archive holds parasites after passage (`closed_loop_hp_arm01.py:968-971, 932-939`), and only as frequencies (`_parasite_freq`). Pairing census hosts at t with that pool pairs them with the pool that will contact generation t+1, not the pool that selected them. That reverses cause and effect. Fix: take a contact snapshot (E4.1).
- **M4 (uniform-tax burden).** Using the same lottery and the same s on every selected host matches the *per-contact* cost of an infection that matches every host. It does not match the realised burden of the arm it is contrasted with: `fixed_high` (`jr5_verdict.py:1146`) only kills exposed 000000 hosts, about 0.25 × 0.632 of hosts at the start. Uniform tax at high virulence kills 1 − e^{-1} ≈ 0.632 of recruits every generation, so it persists only if F·e^{-1} ≥ 1, i.e. F ≥ e ≈ 2.72. That is the same boundary as c ≤ ln F, so it depends on the coder's F. This follows the lock, but the owner should know that "matched to infection cost" here means matched per infection, not matched total kills.
- **L1 (modal at N=200).** All four windows tie at 50, so 000000 is the fixed-arm window only because of the lexical tie-break. That is valid and deterministic, but "modal" carries no information at N=200.
- **L2 (N=50 asymmetry).** Uniparentals make up 3/13 = 0.231 of the 000000 class, against 0.200 overall, so the fixed arm hits uniparentals slightly more. Expected first-generation shift in uniparental frequency at fixed-high ≈ −0.006, far inside ±0.10. Record it; do not fix it.

### (1) Founder window counts
Cycle `W = (000000, 000001, 001000, 001001)` (pairs of 3-bit alleles: (000,000), (000,001), (001,000), (001,001)).

**The engine does not define "organism index within each mating class".** Boot enumerates `founder_rows` and names hosts `h{index}` (`closed_loop_hp_arm01.py:654, 663`). The E1 pilot marks the uniparental class by global index `index % step == 0`, step = 1/intro = 5 (`src/codontrace/campaigns/jr5_realised_w_pilot.py:632-634, 689-691`), and assigns windows by *global* index `i % 4` (`:638`). **Recommended default (not yet locked):**
1. Build `founder_rows[i]` for i = 0..N−1, in this order.
2. class(i) = uniparental iff `i % 5 == 0`, otherwise outcross (same marker rule as E1).
3. r(i) = number of j < i with class(j) = class(i). This is the within-class rank by numeric index i, **not** by string id: `"h10" < "h2"`.
4. window(i) = `W[r(i) % 4]`. The id is `h{i}`, and spatial placement follows i as in boot.

Results, identical under the global-index E1 rule (counts identical, per-organism assignment different):

| N | class (n) | 000000 | 000001 | 001000 | 001001 |
|---|---|---|---|---|---|
| 200 | outcross (160) | 40 | 40 | 40 | 40 |
| 200 | uniparental (40) | 10 | 10 | 10 | 10 |
| 200 | **total** | 50 | 50 | 50 | 50 |
| 50 | outcross (40) | 10 | 10 | 10 | 10 |
| 50 | uniparental (10) | 3 | 3 | 2 | 2 |
| 50 | **total** | 13 | 13 | 12 | 12 |

Mode: N=200 is a four-way tie at 50. N=50 is a tie between 000000 and 000001 at 13. `_modal_window` (`closed_loop_hp_arm01.py:566-572`, applied to founders at `:689`) takes the lexically smallest winner. **The fixed-arm ancestral window is 000000 at both N: confirmed.** Uniparental share within every window is 0.2 at N=200; at N=50 it is 3/13, 3/13, 2/12, 2/12 (L2).

### (2) E4 contemporary pairing (lag 1, discrete clock)
Generation g = 1..H is the g-th pass of: refill → host step → thin to N (E1 fork) → contact → remove ATP ≤ 0 → passage → census.
1. **Contact snapshot.** In generation g, immediately after thinning and before any contact draw, write `contact/g{g}`. It holds: `R(g)` = the N recruit (id, window) pairs sorted by id; `Pc(g)` = the **ordered** list of the P parasite windows about to contact (the list order is the order the lottery uses). Pc(1) = the founder parasite pool, and Pc(g+1) = the passage output of generation g. Label it with g. Write it for every g (it is small).
2. **Census snapshot.** Keep the existing census for generation g (survivors, and the post-passage pool = Pc(g+1)) as `census/g{g}`. It is not used for E4.
3. **Contemporary pool.** The pool contemporary to host generation g is `Pc(g)`, the pool that actually contacted R(g). Score hosts as `R(g)`, the hosts at the moment of contact. Do not use the survivor census: with lethal virulence, survivors are filtered by that same pool, which biases I(H, P_now) downward by construction.
4. **E4 contrast.** Window (W_past, W_now) = (H − 1, H), and H comes from the horizon rule. host effect = I(R(H), Pc(H−1)) − I(R(H−1), Pc(H−1)); parasite effect = I(R(H), Pc(H)) − I(R(H), Pc(H−1)). Expected signs −1 and +1 (`jr5_verdict.py:108`). Load files `contact/g{H-1}` and `contact/g{H}` only. Oscillation times read `contact/g{H-2}`, `g{H-1}`, `g{H}`. Set `e4_window = [H-1, H]` in each run record, and replace the hard-coded `(67, 70)` with the registered (H − 1, H).
5. **Score (exact match, no RNG).** I(R, P) = Σ_w f_R(w)·f_P(w), the probability that one random host–parasite contact matches exactly. The score does not depend on ATP, needs no replay arm, and needs no seed. It replaces the Structural replay (M2). If the owner wants an engine-path replay instead, it must run on `LifeLoopEcologyArm` exact matching, and its expectation equals this formula.
6. **Frozen replay arm.** In generation g, the contact pool is `Pc(g)` loaded from `contact/g{g}` of the copassaged run with the same (seed, N, virulence), in stored order. There is no passage in the replay arm: the pool is replaced each generation from the archive. Use the same lottery fork. The replay arm's own contact snapshots are written the same way, so its E4 (if computed) also uses rule 4.

### (3) Uniform-tax rule (harness-ready)
Per generation g, after thinning to N (E1 fork) and before census:
1. **Lottery (shared with the parasite arms).** `hosts` = the N recruits sorted by id string. `rng = RNGManager(seed=run_seed, namespace="jr5-contact").fork(f"g{g}/r0")` (k = 1, so round 0 only). For p = 0..P−1, draw `idx_p = rng.randrange(0, N)` and target = `hosts[idx_p]`. This is the same draw schedule as in the parasite arms (in parasite arms, parasite p is `Pc(g)[p]`). Shared draws give the same *indices*. They give the same *host ids* only while two arms' populations are identical (generation 1 of paired arms). After that, matching holds in distribution: the same P, the same exposure law.
2. **Multi-hits.** S = the set of distinct targets. A host drawn k ≥ 1 times is taxed **once**. This matches the engine's one-seat rule: a matching parasite on an already-infected host is refused with `seat_occupied` (`host_parasite_env.py:375-389`). In the parasite arms, a host is infected iff at least one of its contacts matches exactly. Expected |S|/N = 1 − (1 − 1/N)^P ≈ 0.632 (0.634 at N=200, 0.636 at N=50).
3. **Kill draw (shared by tax and parasite arms).** For each h in S (tax) or each infected h (parasite arms), u_h = `RNGManager(seed=run_seed, namespace="jr5-kill").fork(f"g{g}/h{h.id}").random()`. Kill iff u_h < s, with s = 1 at high (always killed; drawing anyway costs nothing and keeps a single code path) and s = q = 0.25 at low. One draw per host per generation, never per extra lottery hit. Keying by (g, id), not by stream position, means a host's draw does not depend on which other hosts were hit. When two arms contain the same id at g, they get the same u. The namespace is separate from `jr5-contact` and from the E1 fork. Assert that ids contain no `/`, so fork keys cannot collide.
4. **Apply.** For a killed host, debit all remaining runtime ATP through the ATP ledger with a dedicated reason code (`jr5_tax_kill`; parasite arms use their match reason). Then remove ATP ≤ 0. Surviving hosts are untouched: no sublethal debit at either level. No passage. Then census.
5. **Record per generation.** `g`, `draw_idx[0..P-1]`, `target_ids` (with repeats), `selected_ids = sorted(S)`, per selected id `u_h` and `killed`, plus `n_selected`, `n_killed` and the census after. In parasite arms, also `matched` per selected id and the contact snapshot of (2).
6. **Checks.** The tax depends only on lottery indices and ids, never on the window: **genotype-blind**. Per selected host the kill probability is s, exactly as for a host hit by an exactly matching parasite: **same expected s per infection** (s = 1 high, s = 0.25 low). Expected kill fraction per generation = s·(1 − e^{-c}). Burden caveat: M4.

### Owner decisions left
- OD-A: adopt the within-class rank rule (1) as written, or use the E1 global-index rule. Counts are identical either way; only per-organism and spatial assignment differ.
- OD-B: E4 score = the analytic exact-match formula (E4.5, recommended), or an engine replay on LifeLoop.
- OD-C: accept M4 (uniform tax matched per infection, total burden about 4× fixed-high at the start), or switch to burden matching. Only if the owner wants that; it would reopen the lock.

## 2026-11-21 15:27 +03 — RM-6: locked decisions (OD-A, OD-B, OD-C)

Recorded after Genesis checked RM-5 against the engine at ff5010e. Do not retune on a simulated w. **Do not put this wiring in the current R51 package.**

### Confirmations (no change)
- **M1.** `E4_WINDOW_GENERATIONS = (67, 70)` is the pair (H − lag, H). With lag = 1 the registered window is `[H-1, H]`. Oscillation times stay `(H − 2·lag, H − lag, H)`.
- **M2.** `replay_archived_contact` uses Structural constants and graded affinity, so it is not the E4 score under OD1.
- **M3.** The host-effect and parasite-effect formulas match the locked estimand comments in `jr5_verdict.py`.
- **L1** and **L2** accepted (the −0.006 arithmetic checks).
- Shared-lottery correction accepted: common draw indices, not common host ids after paired populations diverge.

### OD-A locked: within-class numeric rank
In every JR5 arm that carries these windows:
1. Build `founder_rows[i]` for i = 0..N−1, in this order.
2. class(i) = uniparental iff `i % 5 == 0`, otherwise outcross.
3. r(i) = number of j < i with class(j) = class(i). Rank is by numeric index i, never by string-id order (`"h10" < "h2"`).
4. window(i) = `W[r(i) % 4]` with `W = (000000, 000001, 001000, 001001)`.
5. id = `h{i}`; spatial placement follows i.

This is not the E1 global `i % 4` assignment. Counts are the same as under that rule; per-organism and spatial assignment differ.

### OD-B locked: analytic E4 score
- Estimand: `I(R,P) = Σ_w f_R(w)·f_P(w)` on `R(g)` and `Pc(g)` from the contact snapshot (after thin, before lottery). Hosts are scored on `R(g)`, not on survivors.
- Engine replay is not the estimand. A lottery infection rate may be reported only as a supplement.
- `e4_window = [H-1, H]`. Replace the hard-coded `(67, 70)`.
- Frozen replay: in generation g the contact pool is `Pc(g)` loaded from `contact/g{g}` of the copassaged run with the same (seed, N, virulence), in stored order; no passage in the replay arm; same lottery fork.
- Oscillation times stay `(H − 2·lag, H − lag, H)` and read `contact/g{H-2}`, `g{H-1}`, `g{H}`.

### OD-C locked: per-infection matching
Keep per-infection matching. Do not reopen the lock to match total load. Record the ~4× initial load of uniform tax versus `fixed_high`, and the survival bound F ≥ e ≈ 2.72 at high virulence (same boundary as c ≤ ln F). That bound still waits on the coder's max-births report. c = 1.0 remains provisional: if F ≤ 2, c is revisited.

### Still waiting (not new decisions)
- Coder max-births F (provisional c, and the F ≥ e bound).
- Exact high-virulence debit (D above the recruit-ATP upper bound from the locked energy design, plus the run-time invariant).
- Task B: male-fix push.

No further owner decisions in this addendum.

## 2026-11-21 16:27:19 +0300 — Task B: births, recruit ATP, census collapse, w/K/F, D and c (ac9b9c5)

Scope: read-only. Code at `ac9b9c5` (already in `/workspace/jr5-p4`, HEAD = ac9b9c5, worktree clean; nothing edited). `1021ae3` has the same patch-id as the coder's local fix `85a9df7` (91515d62…), and `85a9df7..ac9b9c5` changes only `genesis/statistical_protocol.py` under `src/codontrace/genesis/`. So the coder's data from `/workspace/jr5-malefix` (1d38a72) applies to the ac9b9c5 engine. No engine run, no registered seed, no engine log_w, 1 core. Checks: `taskb_w_check.py` (toy numpy, seeds 20261121+), output `taskb_w_check.out.json`. Owner rule (16:23): engine changes may be proposed; no parameter tuning.

### High
- **H1. The census collapse comes from the model, not a bug in 1021ae3.** Two independent mechanisms each cause it on their own:
  - (a) **Token budget.** A discrete-model life is one step of `ticks_per_generation = 2` (`closed_loop_hp_arm01.py:745`). Max-age death applies at `tick − birth_tick ≥ max_age_ticks = 2` (`death.py:565-570`). Newborns start at cursor 0 (`organism.py:181`) and are not stepped in their birth step. The executed brain is the 3-codon prefix `EAT, COPY, WAIT`. So each life executes exactly (EAT, COPY): **at most 1 reproduction per lifetime**. Births per adult: asexual λ_a ≤ 1, sexual λ_s ≤ 1 − m (males never mother, 1021ae3). Without any energy limit the sexual class goes extinct and the census settles at the asexual founder count (toy: median census at g20 = 10 of 50 and 40 of 200, sexual 0).
  - (b) **Energy closure.** Food inflow is 8 patch cells × 20 per generation, independent of N: `HOLD_FOOD_PATCHES`, `closed_loop_hp_arm01_selfing_hold.py:84-86`. Refill **sets** the cell rather than adding to it: `closed_loop_hp_arm01.py:941-952`, `world.py:366-379`. The recruit endowment is 0.25·(A − 9.9 + F). Unfed founder recruits get 9.525, below the EAT-first threshold of 9.9. The recurrence E' = 0.25(E + 10.1) goes 14.525 → 6.156 → 4.064 → 3.541 → 3.410 → 3.378 → fixed point 3.367, exactly matching `recruit-atp-pooled.jsonl`. From g ≥ 2 every birth needs a full patch-cell EAT, so births ≤ 8 per generation at any N (≤ 16.2 even if food were perfectly divisible: 160/9.9). Toy with food cap: census at g20 ≈ 2–3.
  - The pre-fix data (`bpm-main.jsonl` census 16, 9, 3 and 196, 79, 3) collapse too. The fix only removed births mothered by males (male_parent_ids 11/17/201/198 → 0).
- **H2. Every JR5 arm is untenable under the current discrete design, the parasite-free E1 included.** F per adult ≤ 1 (asexual) and ≤ 0.5 (outcross, m = 0.5), so the viability window [−ln(1 − m), ln F] is empty for every c ≥ 0: the outcross upper bound is ln 0.5 < 0. c = 1.0 is therefore untenable. Even with F ≤ 2 (b = 2, or K = 3N with refusal-stop, H3), outcross at m = 0.5 has F = 1 and cannot absorb any mortality. Untenable then: E5 outcross (low and high), uniform_tax high, copassaged high, frozen_replay high, and fixed_high once the matched fraction exceeds about 0.5. At m = 0.25 (F = 1.5) the low-virulence arms (kill ≤ 0.158) are tenable, the high arms with full matching are not (need survival ≥ 0.667).
- **H3. K = 3N caps F per adult at 2.** In the discrete runner any capacity refusal stops the run (`jr5_realised_w_pilot.py:36-37`, `capacity_refusals` :715-738). Parents are alive when their offspring are placed (`max_population` counts live positions, `population.py` ~6023-6035). So births ≤ 3N − N = 2N per step, and F_adult ≤ 2 < e. c = 1.0 cannot be met under K = 3N whatever the fecundity. In the current census model K is moot (births ≤ 0.6N). In the non-census harness it binds at N = 200 (census 600 = 3N in `bpm-main`).

### Medium
- **M1. Fecundity confound if lifetime energy rises.** The coder saw recombinant prefixes such as (COPY, COPY, ·) (4 of 58 by g8). A second COPY needs A_s ≥ 21.12. Any fix that gives recruits more ATP would let *sexual-only* recombinants double their fecundity, an anti-conservative bias in favour of sex. The fix must cap reproduction events at 1 per lifetime and assert that founder coding prefixes are homozygous (see EC-3).
- **M2. The coder's harness is not the JR5 design.** It uses `_INVASION_FOUNDERS` 000111/111000 (not the OD2 windows), all founders "outcross", `mate_search_radius=None` and cap None (HOLD values 1 and 1, `selfing_hold.py:94-95`), side max(12, ⌈√(4N)⌉), ARM_AVIRULENT, m = 0.5 only, 2 seeds, G = 6, and no `apply_census` call (moot, since births < N). The counts are valid for this harness only. With radius 1 the pairing success π < 1 would add to the cost of sex: E1's upper bound w = 2.2 at m = 0.5 tolerates π ≥ 0.909.

### Low
- L1. `births_per_mother.py` counts births per mother **per generation**. That equals per lifetime only in census mode. Births are counted by `parent_id`, so sires are not counted (correct for mothers). Consistency check passed: in census runs, total births equal the sum of census sizes (33, 28, 174, 167), so there are no phantom or blocked records.
- L2. Census g1 at N = 200 holds 30 recruits with mean ATP 1.40 (42.075/30), below the fed values. I did not resolve their provenance statically (likely deferred chamber placements or COPY-first parents). They cannot reproduce (E < 9.05), so the conclusion is unchanged.
- L3. `recruit-atp-bound.md:53` says the census runs used seed 20501. `recruit-atp-pooled.jsonl` agrees, but `bpm-fix-n20/n200` also contain census runs on seed 20502.

### (1) Verification of the coder's claims
| claim | result | evidence |
|---|---|---|
| max births/mother observed = 1 | **verified** | every record in the 3 bpm files and the pooled file: `per_generation_max` all 1, `distribution` {"1": n} |
| theoretical ceiling = 2 | **verified per generation** (2 tokens/gen, `closed_loop_hp_arm01.py:745`; 1 COPY → 1 slot → ≤ 1 product per mother, `population.py` `_drain_chamber_pairs`). **Per lifetime in census mode the ceiling is 1** for the founder program; the 2nd COPY of a (COPY, COPY) recombinant needs A_s ≥ 21.12 > 14.525 | codon costs `codon.py:252-261` (EAT 0.8, COPY 8.0, WAIT 0.1) |
| recruit ATP ≤ 14.525 | **verified** = 0.25·(48 + 20 − 9.9). Unfed 9.525. Thresholds: COPY-first 9.05, EAT-first unfed 9.9. Pooled max = 14.525 at g0 in all 6 runs | `taskb_w_check.out.json` |
| census collapses within 3 gens to 3–6 | **verified** (fix): N=20 → 11, 6, **4** / 12, 4, **3**; N=200 → 120, 30, **6** / 118, 25, **6**; constant afterwards | bpm-fix files |
| g0 births | expected 0.2N + 0.8N(1 − m) = 120 (N=200) and 12 (N=20) at m = 0.5; observed 120, 118 and 11, 12. Consistent with every paired non-male founder reproducing once | — |

### (2) w, K, F and root cause
- **Expected w.** Per generation w = λ_a/λ_s = 1/((1 − m)·π), with π the sexual pairing success (≈ 1 with global search). That is 2 at m = 0.5 and 4/3 at m = 0.25, matching PREREG E1 (`PREREG.md:50-52`) whenever fecundity is equal per mother. Toy: generation-1 log w = 0.69–0.70 (m = 0.5) and 0.28–0.30 (m = 0.25), both with b = 1 and b = 6. Under the food cap, w comes from patch luck (toy 0.60 at m = 0.5) and the population ends, so the E1 fit is not estimable.
- **F.** Per breeding mother ≤ 1 per lifetime. Per adult: asexual ≤ 1, outcross ≤ 1 − m. With the food cap, ≤ 8/census.
- **K.** Moot in the census model. Caps F_adult ≤ 2 whenever it could bind (H3).
- **Root cause.** H1(a) and H1(b) together. The HOLD energy calibration (`HOLD_SOFT_K = 32`, 8 patches) was built for overlapping generations at about 32 hosts. A semelparous 2-tick life on that calibration cannot replace itself. This is a design incompatibility, not a coding bug in 1021ae3 or in the runner's thinning.

### (3) Proposal: modular engine change "discrete semelparous census generation" (opt-in; RQM proposes, coder implements)
The three changes below are switched on together by one flag, `PopulationDesign.generation_model == "discrete_uniform_census"` or a new `DiscreteCensusConfig(enabled=True, brood_size=b)` on `PopulationConfigs`. They are inert when off.
- **EC-1 Fixed equal brood b per reproduction event.** `ReproductionConfig.brood_size: int = 1` (default 1 = today's behaviour).
  - In `_drain_chamber_pairs` (`population.py` ~6023-6100): each mother product becomes b children. Each child is an independent meiosis/fusion (`birth.py` `split_diploid_homologs` :1619-1642, `fuse_gametes` :1692-1716) with its own RNG fork `…/brood/<k>`.
  - Each child's sex is drawn independently at `sex_ratio` (random_at_birth unchanged). Males remain sire-only (1021ae3 untouched). Asexual and selfed children use the same b (like-for-like, `PREREG.md:76`; constants `offspring_per_reproduction: equal_to_outcrossing_mother` :262).
  - The mother's endowment E = 0.25(A_c − 1) (`population.py:5651-5680`) is split E/b per child, so ATP is conserved.
- **EC-2 Census re-endowment.** In `apply_census` (`jr5_realised_w_pilot.py:762-778`), after thinning, set each kept recruit's runtime ATP to `birth_atp` (48, the locked founder value).
  - Book it through a new ledger source account `source:jr5_census_endowment`, the mirror of `CENSUS_THINNING_SINK` (:158). The old remainder closes to that sink.
  - Engine support: `WorldATPLedger.sync_accounts(..., open_from=…)`, or a `credit_runtime` with its own reason code, so the residual check (`ledger.check`) still closes.
  - Justification: in a discrete Wright–Fisher generation, energy does not carry across generations. Every generation then starts like g0, where the engine is shown to work (120/200 births = all paired non-males). Food, costs, the 0.25 fraction, 48 and the patches are unchanged; no ATP constant is changed.
- **EC-3 One reproduction event per lifetime, plus non-binding transient K.**
  - `ReproductionConfig.max_reproduction_events_per_lifetime: int | None = None`, set to 1 in discrete mode: a second COPY is refused with reason `semelparous_event_cap`. This removes the M1 sexual-only fecundity confound.
  - Boot assertion: in every JR5 arm, founder homologs have identical coding prefixes.
  - `max_population = (1 + b)·N` in discrete mode, so even an all-asexual census never hits a capacity refusal. Keep the runner's capacity-refusal stop as a guard.
- **Choice of b (a priori, not tuned on w).** w = 1/(1 − m) does not depend on b (toy confirms). b is set by the locked c = 1: an outcross population fully matched at high virulence (survival e^{-c}) must be *able* to persist, b(1 − m)e^{-1} ≥ 1, i.e. b ≥ e/(1 − m) = 5.44 (m = 0.5) and 3.62 (m = 0.25). One b for all arms (like-for-like): **b = 6**. Then F_out = 3 (m = 0.5), window [0.693, 1.099] ∋ 1; F_out = 4.5 (m = 0.25), window [0.288, 1.504] ∋ 1; F_asex = 6.
  - b < 5.44 would force outcross extinction under full matching: a design bias *against* Red Queen in E5 and the high arms.
  - A much larger b turns hard selection into soft selection and removes the E5 extinction contrast. Infinite-fecundity WF was rejected for that reason.
  - b = 6 is the smallest integer that keeps the locked schedule feasible. Owner decision OD-B1.
- **No regression.** All three are default-off. Sexes-off and overlapping-model digests and sealed replays are byte-identical. New tests needed:
  - brood b produces b children with independent gametes and sexes;
  - the ledger closes with the source/sink terms;
  - the event cap refuses a 2nd COPY;
  - births ≤ (1 + b)N − N;
  - g0 births = b·(asexual + paired non-males).
- **Modular.** Brood and event cap live in `ReproductionConfig` and the chamber/clone placement. Re-endowment lives in the runner's census hook. No arm-specific logic.
- **Alternatives rejected.**
  - Longer lifetime / more ticks: does not lift the food cap and makes fecundity program-dependent.
  - Scaling food with N: changes an ATP constant and still leaves b ≤ 1.
  - Infinite-fecundity WF: removes E5 extinction.
- **D (high virulence).** Today D = v·min(1, sf/(rp·(1 + h)))·(−interaction_value) = 0.8v (sf 0.8 `host_parasite_env.py:24`, rp 1.0 :173, h 0.0 `closed_loop_hp_arm01.py:132`, interaction −1.0 :174). The debit is `min(A, D)` and survivors need ATP > 0 (`closed_loop_hp_arm01.py:885-907`), so a matched host dies **iff D ≥ A** (non-strict).
  - Current design: A_max at contact = 14.525 → D ≥ 14.525 ⇔ v ≥ 18.15625.
  - Under EC-2: A = 48 at contact → D ≥ 48 ⇔ v ≥ 60.
  - **Recommended:** implement lethality as the explicit kill of RM-5 rule 3.4 (debit all remaining ATP, reason `jr5_kill`; u < s with s = 1 or q), so D is not a free constant. Run-time invariant: every killed host has ATP 0.0 after the debit and is absent from the census.
- **c = 1.0.** Untenable under the current constants (H2). Tenable under EC-1..3 with b = 6 at both m. The low-virulence kill q = 0.25 is tenable in every arm under the proposal (worst case survival 0.842).

### Owner decisions
- OD-B1: adopt EC-1..3 with b = 6, derived above. No retuning of c, P, k, μ, ATP constants or virulence.
- OD-B2: kill semantics for high (recommended) or v ≥ 60 on the steal path.
- OD-B3: the pilot design must also fix mate_search_radius. With radius 1, record π; E1 needs π ≥ 0.909 at m = 0.5.

## 2026-11-21 16:34:41 +0300 — Task B: locked decisions (OD-B1, OD-B2, OD-B3)

Genesis accepted Task B (H1–H3 and the coder's claims confirmed on ac9b9c5 and the bpm / recruit-ATP files). Lines 1–275 remain byte-identical. The locks:

- **OD-B1.** Adopt EC-1..3 with b = 6, default off. Do not retune c, P, k, μ, or ATP constants.
- **OD-B2.** High virulence is an explicit kill (not v ≥ 60), the same rule as RM-5 (rule 3.4).
- **OD-B3.** Option A stands: radius None, cap None, wait 2, fail. Do not take the HOLD radius of 1. These fields are recorded in the pilot design. With global search, π ≈ 1, so the E1 cap w = 2.2 is not spatially constrained.

The coder writes these in the package after R51. Review stays read-only, 1 core, and waits for that package to be pushed. No further decisions.
