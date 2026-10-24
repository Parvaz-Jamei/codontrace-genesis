# Closed, absolute ATP accounting (world ledger)

Module: `codontrace.atp_ledger.WorldATPLedger` (engine layer; imports nothing
from `genesis/` or `experiments/`). Tests: `tests/test_atp_ledger.py`
(Hypothesis property tests) and the world/experiment wiring tests.

## What "closed" and "absolute" mean here

* **Absolute**: every ATP unit is in exactly one named account at every
  moment: `agent:<id>`, `world:reservoir`, `world:clearing` (only inside a
  transfer), `source:<name>` (boundary inflow, balance <= 0) or `sink:<name>`
  (boundary outflow, balance >= 0).
* **Closed**: every change is a double-entry posting (one amount leaves one
  account and enters another), so the signed sum of all accounts is exactly 0.
  Equivalently `agents + reservoir = sum(sources in) - sum(sinks out)`.
* **Exact**: amounts are the IEEE-754 values the engine actually stores, held
  as integers in units of 2^-1074 (every finite double is an exact multiple),
  so checks use `==` (IEEE 754-2019 sec. 3.3: every finite binary64 is an
  integer multiple of 2^-1074). There is no tolerance window anywhere. Inside a
  `transfer_scope` the caller books the exact rounding error of each float
  operation that produced the legs (`float_error`, `coupling_rounding_units`,
  `book_rounding`, against `source:rounding` / `sink:rounding`) and the
  clearing residual must then equal the engine's own computed loss exactly
  (`expect_loss`); a residual below zero, or any mismatch, raises and rolls
  the transfer back. An injected creation of 1e-15 per transfer fails
  (`tests/test_atp_ledger_exact_rounding.py`).

## Invariants checked every tick (`close_tick`)

1. Sum of all accounts == 0.
2. Each open agent account == the engine's own balance for that agent
   (an `ATPAccount.current_atp`, or a scalar `atp` field). A write that goes
   around the ledger raises `ATPConservationError` ("bypass").
3. Open agents == live agents (no ghost energy after a death, no unledgered
   newborn).
4. Sources <= 0, sinks >= 0, reservoir >= 0, clearing == 0 outside a transfer.

Each tick's postings, totals and a state digest are appended to an in-memory
hash chain with the `genesis.journal` record shape
(`previous, action, args, state_digest, digest`); `ledger.head` is the replay
digest of the whole energy history and `verify_ledger_chain(records)` replays
the postings and re-checks the chain and conservation from the records alone.

## Flows

| Event | Posting |
|---|---|
| founders | `source:genesis -> world:reservoir -> agent` |
| birth endowment | `world:reservoir -> child` (shortfall first enters as `source:inflow -> world:reservoir`) |
| death | remaining balance `agent -> world:reservoir` (recycled, not destroyed) |
| basal / birth cost | `agent -> sink:<action>` (maintenance / construction) |
| reward / foraging | `source:<action> -> agent` |
| coupling (host -> parasite) | `holder -> world:clearing -> occupant`; residual `-> sink:coupling_loss` |
| `ATPAccount` 10-digit rounding | `source:rounding` / `sink:rounding` |
| float rounding of a transfer's legs (exact error of each `+`/`-`) | `world:clearing <-> source:rounding / sink:rounding`, then residual == engine loss exactly |

Finding while building it: `ATPAccount.debit/credit` round balances to 10
digits, so a single entry can create or destroy up to 5e-11 ATP. The ledger
books that residue explicitly against `source:rounding`/`sink:rounding`
instead of hiding it; the account arithmetic itself is unchanged, so legacy
digests stay byte-identical.

## Atomicity and copies

* `ATPAccount` calls its world-ledger observer *before* it commits an entry
  (`current_atp` and the entry list change only after the observer returns).
  The ledger books each entry all-or-nothing, so an observer error leaves both
  the account and the ledger untouched.
* `transfer_scope` is a transaction: if its body raises, every posting made in
  the scope is reversed exactly (integer units undo exactly) and every
  `ATPAccount` touched in it is restored, so the clearing residual is 0 and
  ledger == accounts again.
* Copying or pickling an attached `ATPAccount` on its own (`copy.copy`,
  `copy.deepcopy`, `pickle`) gives a *detached* account: the copy never books
  into, and never drags along, the live ledger. Copying or pickling the
  *ledger* (alone or with its world) carries its attached accounts and
  re-attaches them to the copy, so a cloned world is closed on its own.

## Digests

The observer hook on `ATPAccount` is not serialized, compared or digested, and
the scalar path (`adjust`) returns exactly `current + delta`, so every existing
engine digest is unchanged. The ledger head is a new, additional digest; it is
not mixed into any legacy digest.

## Bounded journal and cost

* Balances are exact integers in units of 2^-1074 (every finite double is a
  multiple of it), so the arithmetic is still exact but runs on ints, not
  `Fraction`s. Records serialise the same reduced `num/den` strings, so the
  ledger head is byte-identical to the `Fraction` implementation.
* The head chains the whole history, but only the records since the last
  checkpoint are kept (`checkpoint_every`, default 256 ticks).
  `journal_base()` returns that checkpoint (head + exact balances) and
  `verify_ledger_chain(journal_records(), journal_base())` verifies the
  window on its own. `record_sink=` streams every record out as it closes,
  for persistence or a full replay from genesis. Checkpoint spacing never
  changes the head (Hypothesis-tested).
* T01 pop64 x 3000 generations: before this change 3.75 s / 156 MB; after,
  about 1.7 s / 76 MB, against 0.6 s / 68 MB on main (box timings, which
  vary under load). The remaining time is the cost of booking and
  hash-chaining about 190k postings exactly.

## Research basis

* Avida resources: initial quantity, inflow, outflow, depletable resources
  (Ofria & Wilke 2004, Artificial Life 10(2); Ofria, Bryson & Wilke 2009,
  Avida introduction). Tierra treats CPU time as the energy analogue (Ray 1991).
  Here the reservoir/inflow/sink split follows Avida's resource model.
* Flow-Lenia: mass conservation as an invariant of the update rule
  (Plantec et al. 2023, ALIFE 2023, "Flow-Lenia: Towards open-ended evolution
  in cellular automata through mass conservation and parameter localization";
  Plantec et al. 2025, Artificial Life 31(2), doi:10.1162/artl_a_00471,
  arXiv:2506.08569).
* Double-entry / stock-flow-consistent agent-based models: every flow has a
  matching stock change and rows/columns of the transaction-flow matrix sum
  to zero each period (Godley & Lavoie 2007; Caiani et al. 2016, J. Econ.
  Dyn. Control 69; Baldauf 2023, sfctools, JOSS 8(87) 4980,
  doi:10.21105/joss.04980; Reissl, Fierro, Lamperti & Roventini 2024,
  DSK-SFC, LEM WP 2024/09, Ecological Economics 2025,
  doi:10.1016/j.ecolecon.2025.108641, which checks the identities at agent,
  sector and aggregate level every period).
* ATP budgets: cell energy partitions into growth (construction) and
  maintenance, counted in ATP hydrolyses (Lynch & Marinov 2015, PNAS 112:15690;
  Lynch 2024, Evolutionary Cell Biology, OUP, ch. "The Costs of Cellular
  Features", doi:10.1093/oso/9780192847287.003.0017; Ortega-Arzola, Higgins &
  Cockell 2024, Sci. Rep. 14:5267, minimum energy to build a cell). The
  `sink:basal` (maintenance) vs `sink:birth` (construction) names follow
  that partition.
* Property-based testing: Hypothesis (MacIver, Hatfield-Dodds et al. 2019,
  JOSS 4(43) 1891), version pinned by `hypothesis>=6.0,<7` (6.170 in CI venv).

## Where it is wired

Every ATP owner in the code base books into a closed world ledger. Two modes:

* **push**: the ledger observes an `ATPAccount` (`attach` / `open_agent`), so
  each `debit` / `credit` is booked before it is committed;
* **pull**: `sync_accounts(accounts, tick=)` books every account entry not yet
  booked, by agent id, from the account's append-only entry log. It opens ids
  it has not seen (births, from `source:birth_endowment`, or founders from
  `source:genesis`, at the entry log's `initial_atp`, then replays the log),
  closes ids that disappeared (deaths, `sink:death_remainder`), and raises if
  a known id's log was rewritten rather than extended. Engines that rebuild
  organisms every step (`to_dict` / `from_dict` clones carry the full log) use
  this mode, so cloning never loses a hook. Entry labels are the action /
  reason name up to the first `:` (per-instance suffixes are not accounts).

| Owner | Mode | How |
|---|---|---|
| `HostParasiteWorld` | push | `atp_ledger` field; accounts created only by `_open_account`, removed only by `_close_account`; coupling in one `transfer_scope("coupling")`; `check_atp_conservation()` at the start of `tick()`, `close_tick()` at the end |
| `PopulationRunner` (so `GenesisEngine`, `engine_runtime`, every `closed_loop_*` arm, `rq_mechanism_v2_phase2..5`, `hard_experiment_*`, `phase_e`, `materials` and the `life_loop` coupler, all of which move ATP only through `GenesisOrganism.atp_state` inside a runner) | pull | `atp_ledger` field; `settle_atp()` books runtime and learning accounts (`organism_atp_accounts`) before each `step_population` (changes made between generations by observers or experiment code) and closes the tick after it |
| `closed_loop_p6.run_match_arm`, shared-census arm (custom loops outside a runner) | pull | a per-run ledger; `assert_single_atp_owner(..., ledger=, tick=generation)` every generation and once after the loop |
| `assert_single_atp_owner(organisms, ledger=None, *, tick=None)` | either | one account per organism, balance equals the replay of its entries; with `ledger` a world check; with `ledger` and `tick` the pull sync and a closed tick. Every post-step call in `closed_loop_hp_arm01`, `closed_loop_p1/p2/p3/p5/p6` passes `runner.atp_ledger` and the generation |
| `Simulation.run` (classic `WhiteBoxAgent`) | pull | `atp_ledger=` kwarg (fresh ledger if omitted); founders opened from `source:genesis`, every tick closed |
| `WhiteBoxAgent.run`, `GenesisOrganism.run` (single-agent loops) | pull | `atp_ledger=` kwarg; every step / tick closed |
| `EnergyCoupling.apply` (pure function over a balances map) | push | optional `atp_ledger=`: both realised legs settled through `world:clearing` in one `transfer_scope("ENERGY_COUPLING")`, the loss to `sink:ENERGY_COUPLING_loss`. Its two engine callers (`HostParasiteWorld`, `closed_loop_p3`) realise the result through ledgered `ATPAccount`s, so they do not pass it (that would book twice) |
| `d2_recovery_v2.apply_locked_recovery_arm` (standalone control on two organisms) | pull | `atp_ledger=` kwarg (fresh ledger per control if omitted); both organisms synced and the control's ticks closed |
| Per-organism helpers `apply_logic9_runtime_bonus`, `apply_task_switch_cost`, `apply_phase_e_action_choice`, `apply_organism_material_coupling`, `emit_causal_capsule` / `read_nexus_capsules` | pull | they debit/credit `atp_state` of organisms owned by a `PopulationRunner` (called from `step_population`), so the runner's `settle_atp` books every entry they make |
| `T01OEERunner`, `T04ContingencyRunner` | push | `atp_ledger`; survival reward via `atp_ledger.adjust(... source:task_reward / sink:metabolism)`; births from the reservoir; leavers' ATP returned; invariant checked before and after every generation; T04 replays start a fresh ledger from the snapshot (`source:genesis`) |
| `T02MLSPriceRunner`, `T03MutualismRunner`, `T05RedQueenRunner` (scalar `atp` / `host_atp` / `symbiont_atp` fields) | pull | `atp_book = ScalarATPBook(...)`: each individual gets a ledger id on first sight; `settle` before and after every generation opens births, closes deaths and checks every field exactly; T02 migration keeps the id (`carry`); T03 payoffs are written only as `x = self.atp_book.assign(...)` (`source:payoff` / `sink:payoff`) |

Outputs are byte-identical: the ledger only reads balances and entry logs.
Checked against `main` with `/workspace`-local pin scripts (T01/T04/HP pins,
T02/T03/T05 run reprs, `GenesisEngine` run digests with the source-tree
provenance hash held fixed, since that hash covers the source files
themselves) and the repository's pinned-digest tests.

## No bypasses (AST-enforced, plus runtime)

`tests/test_atp_ledger_experiments_wiring.py::atp_bypasses` parses every module
under `src/codontrace` and fails on any write of an ATP balance field outside
`energy.py` / `atp_ledger.py`, in every form Python offers:
`x.current_atp = / += / : T =`, tuple targets, `setattr(x, "current_atp", v)`,
`object.__setattr__(x, ...)`, `x.__setattr__(...)`, `x.__dict__[...] =`,
`vars(x)[...] =`, `x.__dict__.update(current_atp=...)` and
`dataclasses.replace(x, current_atp=...)`. The private fields `_observer`,
`_ledger` and `_verified` are protected the same way on any receiver other than
`self`. In T01-T05 the scalar fields `atp`, `host_atp` and `symbiont_atp` are
protected too; their only allowed writes are `x.f = self.atp_ledger.adjust(...)`
and `x.f = self.atp_book.assign(...)`. Mutant tests (15 fixed forms plus a
Hypothesis property over forms x receivers x fields) prove the gate catches
each form. The gate is a guard rail, not the proof: `getattr`-computed names or
`exec` cannot be seen statically, and the runtime check (`close_tick` mirror
equality, `verify_balance`) catches any balance changed outside the ledger.
`host_parasite_world.py` must still create, insert and remove `ATPAccount`s
only in `_open_account` / `_close_account`.
