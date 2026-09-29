# D-2 recovery window — archived experiment record (2026-09-29)

This README is the complete record of one experiment: question, design, instrument, protocol, raw
data, analysis and result. It is written to be read without the working tree.

* **Record:** `codontrace-genesis/docs/experiments/2026-09-29/d2_recovery_window/`
* **Working tree for the runs:** `docs/experiments/2026-09-29/d2_recovery_window/` (same files plus the generator scripts)
* **Claim ceiling:** `phase2_design`; `hypothesis_supported = false`; `red_queen_proved = false`
* **Standing verdict:** **measurement-level — the locked endpoint is not measurably reachable**
  (`BLOCKED_MEASUREMENT`). Round-4 `FALSIFIED_IN_MODEL` and round-3 `BLOCKED_MEASUREMENT`
  (fork isolation) are **superseded history**, retained and labelled as such in §9.

All paths are relative to the record directory unless stated otherwise. The record holds 202 files,
excluding the tarball listed as not imported in §5.

---

## 1. Question and hypothesis

Does the **contact structure** of the life-loop engine causally mediate recovery of a declared
functional innovation after a named contact edge is cut — beyond a degree/ATP/edge-count matched
random cut and a sham — and does recovery probability decline with normalised intervention time `t̃`?

Hypothesis under test (D-2 / idea 4): at a fixed checkpoint, cutting the pre-registered source-path
scaffold `SCAF-CONTACT-SRC-PATH-V1` (edges `E0`, `E1`) changes recovery of the rare-class
contact-yield function relative to an independent, matched rewiring cut, because the named edges are
held by particular organisms and the loss is endpoint-specific rather than a global cost.

Refusal conditions fixed in advance: if named and rewired arms share realised contacts and
population trajectory, or if a difference is only the coupler's global edge-cost penalty, the
mediation claim is dead. A second condition was added by review and applied here: **if no positive
control can reach the locked endpoint, the result is measurement-level, not a falsification of any
intervention.**

### References (search dated 2026-09-29)

1. Yedid, Ofria & Lenski (2008), *Journal of Evolutionary Biology* 21:1335–1347,
   [doi:10.1111/j.1420-9101.2008.01564.x](https://doi.org/10.1111/j.1420-9101.2008.01564.x) —
   re-evolution of a complex feature lost during a mass extinction in digital organisms. Recovery
   after loss is already published and is not by itself a novelty claim.
2. Yedid, Ofria, McKelvey & Lenski (2009), *The American Naturalist*,
   [doi:10.1086/597228](https://doi.org/10.1086/597228) — selective press extinctions cause delayed
   ecological recovery in communities of digital organisms; random pulse extinctions do not. Nearest
   precedent for measuring recovery after perturbation in this medium.
3. Blount, Lenski & Losos (2018), *Science* 362, eaam5979,
   [doi:10.1126/science.aam5979](https://doi.org/10.1126/science.aam5979) — contingency and
   determinism when replaying life's tape. Divergent replay is not a result by itself.
4. Blount, Borland & Lenski (2008), *PNAS* 105:7899,
   [doi:10.1073/pnas.0803151105](https://doi.org/10.1073/pnas.0803151105) — historical contingency
   and the evolution of a key innovation. Basis for treating a competence as a threshold event.
5. Avida ecological-network study (2016), *Nature Communications* 7:12462,
   [doi:10.1038/ncomms12462](https://doi.org/10.1038/ncomms12462) — environmental change makes
   robust ecological networks fragile. Digital contact networks are studied; the difference sought
   here is per-edge causal mediation at run level.
6. Buckingham & Ashby (2022), *Journal of Evolutionary Biology* 35:205–224,
   [doi:10.1111/jeb.13981](https://doi.org/10.1111/jeb.13981) — coevolutionary theory of hosts and
   parasites. The bound that forbids reading a single cycling signature as a discovery.

**Only admissible novelty:** causal mediation of function recovery by *which organisms hold the cut
contact edges*, separated from a global cost penalty, under a locked endpoint. Absence of a search
hit is not proof of uniqueness.

---

## 2. Pre-registered endpoint and locked margins (fixed before any run)

| Item | Locked value | Where fixed |
|---|---|---|
| Competence ID | `FI-RARECLASS-CONTACT-YIELD-V1` | `IDEA4_PHASE2_DESIGN_DIGEST.md`, 2026-09-28 |
| Success rule | mean rare-class contact yield ≥ **1.25×** the run's own pre-checkpoint baseline, sustained for **≥ 3 consecutive** generation boundaries ending at or before `T` | same |
| Horizon | `T = 40` boundaries after the checkpoint | same |
| `t̃` grid | at least 3 normalised times; used `t = 10, 20, 30` → `t̃ = 0.25, 0.50, 0.75` | phase-1 boundary + design digest |
| Ecology/knowledge margin | `|ΔP| ≥ 0.20` versus the matched control at fixed `t̃`; window slope `≥ 0.15` | phase-1 boundary §7 |
| Unit of replication | the independent population **history** (seed × checkpoint); contact pairs are never `N` | common protocol |
| Second endpoint | `GENOME-DIGEST-LOST-THEN-REGAINED-V1` (2026-09-29), **exploratory**, reported separately | owner record |

No threshold, seed or parameter was moved at any point in this record. The 1.25× and 3-boundary
rules are exactly as pre-registered; the 0.20 margin is applied later in §9, not relaxed.

---

## 3. Instrument

**Life-loop ecology.** Each history is a `GenesisEngine` life loop built by
`build_idea4_engine_spec`. Organisms carry a six-bit recognition window in three two-bit sub-loci,
consume runtime ATP, reproduce above a threshold and die below it; the world is a 2-D resource grid
with respawn. Every random draw derives from `(spec.seed, absolute tick index)`, so a history is
deterministic given its specification.

**Audited ledger.** A `ContactAtpLedger` holds named contact edges `E0…E11` with class tags and an
ATP yield per edge, the pre-registered scaffold set `SCAF-CONTACT-SRC-PATH-V1` = {`E0`,`E1`}, a
planted mirror `match_mirrors = {E0→E6, E1→E7}`, the recovery token
`token:recovery:FI-RARECLASS-CONTACT-YIELD-V1`, and a failed-prediction digest key.

**"Yield".** `harvest_rare_class_yield(ledger)` is ledger arithmetic: the sum of `atp_yield` over
present, unmasked edges tagged `rare`, times a token factor (1.0 `eligible`, 0.55 relocated,
0.35 absent), times a scaffold factor `0.4 + 0.6 × (present members / total members)`, times 0.75
when the failed-prediction digest list is empty. It is a tagged-contact yield, not a genotype
quantity. The product of the three multipliers cannot exceed **1.0**, which is the arithmetic root
of the measurement-level verdict in §9.

**"Digest return".** The exploratory endpoint: a genome digest present in the checkpoint census
disappears at a later boundary and is present again later. Never pooled with the pre-registered
endpoint.

**Coupler.** `EngineCoupledLedgerObserver` samples the engine at each generation boundary, applies
the scheduled operation, and feeds the ledger delta back. The analysed allocation is
`incident_endpoints_realised`: the debit is the realised ATP of the changed contact edges, charged to
the organisms bound to those edges' endpoints, with `burden_edge_changes = 0.0` so the global count
penalty cannot explain an arm difference.

**Topology flags (landed `ec4f3c0`, still standing).** The node→organism binding behind that debit
is a **name-ordered list of the sorted live organisms**, which is not the contact that actually
occurred, and no engine contact event is read on that path. The same return previously reported
`topology_effect_identified = True`. The flag patch forces `endpoint_map_is_contact_physics = False`,
`contact_structure_effect_identified = False` and `topology_effect_identified = False`, keeps the
binding's completeness as `endpoint_binding_complete`, and records
`topology_flag_reason = "endpoint binding is name-ordered, not an engine contact event"`. The flags
may return to `True` only when **both contact endpoints and the realised transfer source come from an
engine event**. Idea-4's default allocation remains `global_smear`.

**Round-3 fork-isolation failure and the round-4 fix.** Arms were first branched with
`GenesisEngine.capture_fork`/`from_fork`. Task-7 found the fork was not state-complete; the landed
fix restored `qd_archive`, `nexus_layer`, `world` and per-organism state, and 6/6 identity cells
(K ∈ {0,3} × N ∈ {1,2,5}) then matched on tick index, tick digest, generation digest and population
digest (negative control: all six unpatched cells failed). A residual remained: `population` and
`element_grid` are **shared references** because `mappingproxy` registries make `copy.deepcopy`
impossible, so `fork_state_exact = false`. Round 3 therefore recorded `BLOCKED_MEASUREMENT` rather
than an arm contrast. Round 4 removed the residual by **independent re-simulation per arm**: every
arm is a fresh engine from `from_spec`, advanced from tick 0 to the checkpoint, so `fork_used =
false` and the 18 arm populations are 18 distinct objects. The isolation probe interleaves three
independently built engines after the checkpoint: same-arm engines are byte-identical
(`ed2602ed74a5`, `509bb9cabae2`, `4471e2ed2c74`) and the different arm diverges
(`ccf9e19b2bff`, `c7d49cdc9b04`, `bf2330f6832b`).

---

## 4. Design actually run

* **Histories:** 6 = seeds `5501`, `5502` × checkpoints `t = 10, 20, 30`.
* **Arms per history:** `cut_named_scaffold` (cut `E0`,`E1`), `cut_matched_random` (cut `E6`,`E7`;
  equal edge count, degree and ATP; `match_exact = true`, `independent_control = false`), `sham`
  (token relocated, nothing else). 18 arm runs.
* **Positive control:** run **before any arm contrast** — `positive_keep_eligible` (checkpoint leaves
  the token `eligible`), `positive_restore_token` (relocate, then restore payload `eligible`), and
  `control_relocated` (round-4 checkpoint behaviour) for reference.
* **Horizon:** 40 boundaries after the checkpoint. **Ecology:** `ecology = "persistence_safe"`.
* **Exclusions:** none; every assigned history, arm and control is reported.

---

## 5. Protocol and provenance

| Item | Value |
|---|---|
| HEAD when the record was finalised | `a8ec47e558c47d4fe04506c1eac9b13571f2b641`, working tree clean |
| Task-16 flag patch landed | `ec4f3c0` (confirmed by the Lead); flags present in the module |
| Round-4 run HEAD | `01ee4a23489a63bc8073a43a82c2037c73b7bbff` (the manager named `02cc725`; both recorded in `run_manifest.json`) |
| Config digest (round 4) | `20a38187cb61b12e47d3418e4c5609cd` |
| Python / workers | 3.14, one worker, `PYTHONPATH=<repo>/src` |
| `git` | absolute binary `C:/Users/parvaz/AppData/Local/GitHubDesktop/app-3.5.12/resources/app/git/cmd/git.exe` with `-c safe.directory=*` |
| Provenance archive | `provenance/tip.tar`, 21,032,960 bytes, sha256 `e4ba113bbc5858f90f579309cc5c7510771d1c25e221b06d96e01f0043926c7e` |
| Import policy | the 20 MB tarball is **deliberately not imported**; its sha256 is recorded here, in `evidence_files.sha256` and in `provenance/tip.txt` |

---

## 6. What ran, with n and wall time

| Tier | What | n | Wall time |
|---|---|---|---|
| Stage 0 | hand-computed cases, fork/identity cells, controls, determinism | 10 checks + 6 identity cells | `stage0_report.json`, `logs/task7_fork_proof.json` |
| Round 2 | segment-based calibration, 36 raw JSONL runs | 36 | `logs/pack_r2.txt` |
| Round 3 | forked arms from one payload (superseded) | 18 arm runs | 149.0 s |
| Round 4 | independent re-simulation arms | 18 arm runs | 294.85 s |
| Task-16 | **positive control before arm contrasts** | 18 runs | 302.26 s |

Budget ceilings were 8 minutes per test and 45 minutes for the pack; all tiers met them.

---

## 7. Raw data files and how to read them

**Positive control (decides the verdict):**

| File | sha256 | Bytes |
|---|---|---|
| `logs/task16_positive_control.json` | `7c0e7b16110c31f38c711c9e5caa8241fa1305264c43a9229c6c5ee8cd9e98cb` | 14,342 |
| `analysis_task16.json` | `8732d0b25628ade4d6cc21f03d5869d1e2f8c999cd9c680bc8d9a1807066348c` | 1,346 |
| `logs/task16.txt` | `98f0c0bf0bde338f237d396e3c1bd743de135fe996e6f25b9d4dd84df1a61600` | 2,307 |
| `PROPOSED_CHANGE_topology_flag.patch` | `4f355bbaa36a59b4c9d1bcbf73ca6d54b8e096f573f5723e12aa3dc24667dd21` | 1,294 |
| `decision.md` | `d585b8ab69b179a0249f04375b2fddb3932541a46bec41d9c965767cfe0bde6b` | 6,435 |

**Round 4 (arm contrasts):** `raw/round4/round4_raw.json`
`758608f366d06715b9fdcabf6c83917f8c2287a07f5142889556d6340697a8db` (139,796 bytes);
`analysis_round4.json` `439ab1d228d4cc8b6700d5e98f045fdb73d5eff65b40f7a65fb9552d9398760a`.

**Round 3 (superseded):** `raw/round3/round3_raw.json`
`dcf1e8769f8fe5645f768e9d8079e704d4ef4587fa459b2b2aad74aef11edbce`;
`analysis_round3.json` `69bfa99ee4eafdb948f7c9502376d84dcecab55b053f6ba4fc07e7e4d2321151`.

**Task-7 fork proof:** `logs/task7_fork_proof.json`
`ee69f40531320ef1043c564e667a44720e175ea88411a0835b086e50a3ee090d`.

**Round-2 raw JSONL:** `raw/d2-s<seed>-t<t>-<arm>/` for 2 seeds × 3 checkpoints × 6 arms, each with
`events.jsonl`, `population.jsonl`, `run_manifest.json`. The authoritative per-file hash list for the
whole record is `evidence_files.sha256` (`sha256  size  path` per line); use it when verifying a copy.

**Parsing.** `logs/task16_positive_control.json` → `rows[]` (one per run: `run_id`, `seed`,
`t_intervene`, `arm`, `baseline_mean_rare_yield`, `max_yield_ratio`,
`max_consecutive_boundaries_at_1.25x`, `recover_preregistered`, `n_alive_end`, `post_yield_tail`) and
`summary` per arm. `round4_raw.json` → `cells[]` with `population_object_id`, `fork_used`,
`paths[]`, `n_alive_series[]`, `ledger_digest`, plus `isolation[]`. `events.jsonl` carries
`run_id, seed, arm, generation, event_id, organism_id, parent_id, genotype_digest,
antagonist_digest, contact_edge_id, opportunity, matched, intended_debit, realised_debit, atp_before,
atp_after, birth, death, mutation, intervention_id`; quantities the model does not expose are defined
nulls, with the reason for each in `harness/d2_common.py → NULL_REASONS`. `population.jsonl` carries
`n_alive`, class/genotype counts and frequencies, `atp_sum`, `atp_mean`, `resource_mass`,
`genealogy`, `population_path_digest`, and nulls for `antagonist_frequency`, `fitness`,
`contact_opportunities`, `pi_realised`, `pi_intended`.

---

## 8. Analysis method (from raw only)

`analysis_task16.json` is derived exclusively from `logs/task16_positive_control.json`; no quantity is
read from a live engine. Per arm: number of runs, recoveries, maximum `post_yield / baseline_mean`,
the longest run of consecutive boundaries at or above 1.25×, and mean survivors at `T`. The
isolated-design rule is evaluated as: every arm built independently (`fork_used = false`), all
population objects distinct, same-arm interleaved engines identical, different arms diverging after
the checkpoint. Proportions are reported on the history unit; with six histories per arm no
randomisation interval can exclude zero, so none is promoted to a claim.

---

## 9. Results

### 9.1 Positive control, reported before the arm contrasts

| Control | runs | recoveries | max yield ratio | best consecutive boundaries at 1.25× | mean `n_alive` at T |
|---|---|---|---|---|---|
| `positive_keep_eligible` | 6 | 0 | **1.036** | 0 | 2.0 |
| `positive_restore_token` | 6 | 0 | **1.036** | 0 | 2.0 |
| `control_relocated` | 6 | 0 | **0.570** | 0 | 2.0 |

The most favourable state the model can present — token `eligible` (1.0), scaffold intact (1.0),
failed-prediction digest present (1.0) — peaks at **1.036× baseline**, against the locked
requirement of **≥ 1.25× for ≥ 3 consecutive boundaries**. The multiplier product cannot exceed 1.0,
so only an ecology-driven rise of the raw tagged sum could close the gap, and the observed rise is
about 4 %. **The locked endpoint is not measurably reachable in this model and regime.**

### 9.2 Arm contrasts (round 4, retained; not read as a falsification)

| Arm | runs | recoveries | max yield ratio | mean `n_alive` at T |
|---|---|---|---|---|
| `cut_named_scaffold` | 6 | 0 | 0.059 | 2.0 |
| `cut_matched_random` | 6 | 0 | 0.573 | 2.0 |
| `sham` | 6 | 0 | 0.570 | 2.0 |

Named − matched mediation contrast = **0**; against the fixed 0.20 margin, `|ΔP| = 0.00`. Isolation
passed: `fork_used = false`, 18 distinct population objects. Every arm sat below a ceiling no arm can
cross, so these zeroes are a property of the endpoint, not evidence about contact mediation.

### 9.3 Separate ecology finding (recorded as such, not an endpoint)

Persistence-safe ecology removes the extinction artefact: `n_alive_end_zero_rate = 0.00` in every arm
and mean **2.0 survivors at T = 40**, against **100 % extinction** in round 2, where every run died and
the endpoint could not be measured at all. This is a measurement-precondition improvement.

### 9.4 Verdict and superseded history

* **Standing verdict:** measurement-level — **the locked endpoint is not measurably reachable**
  (`BLOCKED_MEASUREMENT`). Not a falsification of any intervention.
* **Superseded:** round-4 `FALSIFIED_IN_MODEL` (recorded before the positive control existed;
  `analysis_round4.json` unchanged), round-3 `BLOCKED_MEASUREMENT` (fork isolation), and round-2
  `INCONCLUSIVE` (100 % extinction). All retained as history and labelled.
* **Limits:** six histories cannot exclude a rare event; a four-seed pilot would be needed for any
  supported/falsified statement, with its budget locked before any holdout. The topology flags remain
  `False` until endpoints come from engine events, so no topology effect can be claimed from this
  record.

---

## 10. Replay commands (in-repo paths only)

```text
# HEAD of the working tree used for this record
"C:/Users/parvaz/AppData/Local/GitHubDesktop/app-3.5.12/resources/app/git/cmd/git.exe" \
  -c safe.directory=* -C codontrace-genesis rev-parse HEAD    # a8ec47e558c47d4fe04506c1eac9b13571f2b641

# positive control before arm contrasts (~302 s, one worker)
python docs/experiments/2026-09-29/d2_recovery_window/harness/d2_task16.py

# round-4 arm contrasts (~295 s, one worker) and their derived analysis
python docs/experiments/2026-09-29/d2_recovery_window/harness/d2_round4.py
python docs/experiments/2026-09-29/d2_recovery_window/harness/d2_round4_finalise.py

# replay one raw run from its own manifest (checksums + schema + summary from raw)
python docs/experiments/2026-09-29/d2_recovery_window/harness/d2_replay.py --run-dir docs/experiments/2026-09-29/d2_recovery_window/raw/d2-s5501-t10-cut_named_scaffold
```

Re-deriving must reproduce the numbers in §9 exactly; any difference is an instrument failure, not a
new result.
