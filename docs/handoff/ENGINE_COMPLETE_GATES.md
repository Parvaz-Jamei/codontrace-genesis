# Engine-complete gates — HostParasiteWorld / life_loop (2026-09-25)

**Constraint:** life_loop + `engine.py` stay **domain-free / general** ALife (HP is a thin profile that *calls* primitives; no infection / vaccine / CRISPR / ARD vocabulary, `steal_fraction`, or HP physics in `engine.py` or kernel types). Engine and modules **may be updated** for fidelity; see `OWNER_ENGINE_MODULE_UPDATE_POLICY_20260926.md`. BAIC pin freezes are lifted (venue dropped). ClaimGate honesty bars unchanged.

**Tests:** `tests/engine_complete/test_engine_complete_gates.py`

| # | Gate | Result | Evidence |
|---|------|--------|----------|
| 1 | `tick` mutates **both** populations with real birth **and** death; extinction **and** coexistence both recordable | **PASS** | `test_gate1_*`; `birth_counts` / `death_counts` / `outcome_log` / `summary()["extinct_*","coexistence"]` |
| 2 | Mutation both sides via **core** `Mutation` + `RNGManager` — not `_deterministic_unit` hash sidecars | **PASS** | `test_gate2_*`; `_deterministic_unit` removed; genomes mutated with `Mutation(operation="point", rng=…)` |
| 3 | Quantitative attachment with capacity + fail reasons for **whole** population | **PASS** | `test_gate3_*`; `_attach_whole_population`; `attach_fail_census` includes `success` / `seat_full` / `already_occupant` |
| 4 | Energy from **core ATP ledger**; trade parameterized; no silent `ConfigurationError` swallow without census | **PASS** | `test_gate4_*`; `ATPAccount` debit/credit after `EnergyCoupling.apply`; `coupling_fail_census` always updated |
| 5 | `InheritAttachedPolicy` / `apply_birth_inherit` **invoked on birth** in `tick` | **PASS** | `test_gate5_*`; called inside `_birth_role` |
| 6 | `PopulationRegistry` participates in GenesisEngine life-loop via **one** orchestrated path (not a second engine) | **PASS** | `host_parasite_genesis_path.py` (`HostParasiteGenesisPath`); registry advanced only inside `HostParasiteWorld.tick`; optional lockstep `GenesisEngine.run_ticks(1)`; **no** infection in `engine.py` |
| 7 | Bit-identical replay for same seed+profile | **PASS** | `test_gate7_*`; matching `world_digest`, genome, energy ledger, RNG state digests |
| 8 | Main demographic effects only asserted with `n_seeds >= 30` | **PASS** | `test_gate8_*`; fixture may use `n<30`, effect test requires `n=30` |

## Architecture note (gate 6)

- **Spine:** `GenesisEngine` = organism / world physics (domain-free).
- **HP book:** `PopulationRegistry` + `AttachmentBook` advanced only inside `HostParasiteWorld.tick`.
- **Bridge:** `HostParasiteGenesisPath` mirrors opaque registry digests; may bind an engine for lockstep ticks without placing coevolution into the kernel.

## Explicit non-goals (still locked)

- No unsolved-challenge / literature SF tests yet
- ClaimGate refuses unchanged; BAIC pins no longer frozen (see OWNER_ENGINE_MODULE_UPDATE_POLICY_20260926.md)
- No infection physics in `engine.py`
- No Round-3 innovation-meter campaigns as template
- No “best-in-world” claims
