# JR5 design note: sexes on top of `mating_types_enabled`

Base commit 66f57a5. Phase 1 changes no engine code.

## What the flag does today

`SexualRecombinationConfig.mating_types_enabled` is a stub.

- Declared at `src/codontrace/genesis/birth.py:187`, default `False`.
- Written by `to_dict` at `birth.py:224` on every call, even when it is `False`.
- Read back by `from_dict` at `birth.py:252`.
- The docstring at `birth.py:169` says mating-type and lekking flags "are stubs for later; they do not change pairing".
- Nothing else in `src/`, `tests/`, `docs/` or `runs/` reads it or sets it. A grep for `mating_types_enabled` and `.mating_types_enabled` over the tree returns only those three lines. No lock or preregistration sets it to `True`.
- `lekking` (`birth.py:188`) is in the same state.

Pairing actually happens in `src/codontrace/genesis/population.py` around lines 5600-5680:
- `_mate_ok` checks `outcross_same_role_only` through `plugin.mates_compatible`, the search radius, and the per-generation mate cap.
- `select_chamber_pair` picks a pair.
- `two_fold_cost_sex` (`population.py:5623`, `:5665`) places one recombinant product instead of two.

The "role" in `mates_compatible` is the host/parasite role from `host_parasite_life_plugin.py:30-31` (`clp1.role.primary` / `clp1.role.secondary`). It is not a sex.

The heritable selfing/outcross policy already exists. `decode_outcross` is at `host_parasite_life_plugin.py:361` and `silence_outcross_locus` at `:495`. The arm01 founders carry it as `("outcross" | "selfing", window)` rows (`closed_loop_hp_arm01.py:144-156`).

## Can the flag carry sexes?

Yes, as the master switch. It cannot carry them alone. A bool cannot hold the sex of an organism, the sex ratio, or the son allocation. So phase 2a adds those as fields of the same config and treats them as active only when `mating_types_enabled` is `True`. There is no second mechanism and no new top-level config.

## Digest constraint

`to_dict` already writes `"mating_types_enabled": false` into every sexual config payload. Old digests therefore contain that key, and its value must stay `false` for old locks. Any new field must follow the `diploid_meiosis` pattern (`birth.py:227-228`): written only when it differs from the default. Old payloads and their digests then stay byte-identical.

## Phase 2a (trait and policy, no cost)

1. New fields on `SexualRecombinationConfig`: `mating_type_set` (default `()`), `sex_ratio` (default `0.5`) and `sex_assignment` (`"none"`, `"random_at_birth"` or `"inherited_locus"`). They are validated in `__post_init__` and serialized only when not default. Setting `mating_types_enabled=True` with an empty set is an error.
2. A per-organism `mating_type` value is stored the way the life plugin stores `role_by_id`: an opaque map grown on birth, drawn from a dedicated `RNGManager.fork("mating_type/<slot>")` stream. Off-path RNG draws stay unchanged.
3. Pairing: when the flag is on, `_mate_ok` also requires compatible mating types: male × female, or hermaphrodite × anything. With the flag on, phase 2a refuses selfing for every mating type, hermaphrodites included. Hermaphrodite selfing with sexes on is not part of 2a. It arrives in phase 2b as an opt-in mode (below). The mating policy is still the existing outcross locus; it is not reimplemented.
4. Acceptance:
   - Every existing digest test passes unchanged.
   - Every sealed lock replay (arm01 mating, persistence, selfing-hold, RQ-earn, structural RQ, RQ-v2 phases 2-6) is byte-identical with the flag off.
   - The new tests cover the flag-on path.

## Phase 2b (cost and census)

1. Son production: a pair whose offspring is assigned male still places it, but a male never enters the chamber as a mother. The cost shows up in births, not through a multiplier. The ATP for every offspring, sons included, is posted to `WorldATPLedger` (`src/codontrace/atp_ledger.py:194`) under a `son_allocation` posting kind.
2. Census streams per generation: sex counts, mating-mode counts and the realised sex ratio.
3. `two_fold_cost_sex` keeps its existing meaning: one product placed. JR5 arms set it to `False` once sexes are on, so the cost is not charged twice. This is checked in config validation.
4. Opt-in hermaphrodite selfing with sexes on (prereg key `self_mode: "hermaphrodite_selfing_sexes_on"`; engine config: `sexual_recombination.hermaphrodite_selfing=True` with mating types on, `mating_type_set=[hermaphrodite]` in self arms and `[hermaphrodite, male]` in outcross arms, `diploid_meiosis=True` in every arm, `sex_assignment=random_at_birth`, `pairing_policy=birth_chamber`, `two_fold_cost_sex=False`, and `closed_loop_hp_life.outcross_enabled=True`, `selfing_birth_atp_endowment=0.0`; outcross locus `000` in self arms, `001` in outcross arms). A hermaphrodite with the outcross locus off may self. A selfed offspring is never a son, so selfers make no sons by construction. The JR5 self arms (E5 self half, mutation-load self arm) use this mode; outcross arms run in the same sexes-on mode and the same ledger. Self and outcross arms differ in the outcross locus and in whether males are present (the mating type set); together these are the mating system, the single manipulated factor, and every other setting is shared. The arms then differ by biology in two ledgered costs, not by turning a cost off: the son cost and the outcross mating fee (`outcross_runtime_atp = 1.0` ATP per outcross reproduction), each booked in `WorldATPLedger` as its own term (the fee is one debit per outcross reproduction, written as an `outcross_runtime_cost` row and reported as the ledger term `outcross_mating_fee`). The cost-of-males estimate uses only the son term. Like-for-like rule (preregistered, PREREG.md section 4): per reproduction, a selfing hermaphrodite produces the same number of offspring and draws the same ATP budget as an outcrossing mother, with no extra fitness term; the outcross mating fee is the one outcross-only ATP cost and is ledgered separately. Inbreeding cost comes only through the existing genome model. Genetics of selfing: with a haploid genome a selfed child would be a genetic clone of its parent, and selfing segregates alleles only when `diploid_meiosis` is on. It is on in every JR5 host arm, so selfing does segregate and inbreeding and purging come from the genome model. If this mode is not delivered, the self arms do not run and condition (d) fails. No delayed selfing: a hermaphrodite whose locus says outcross and that finds no mate is refused, with no selfing at a timeout, so the arms stay obligate selfing versus obligate outcrossing without reproductive assurance mixed in. Sex is fixed for life: it is assigned once, at birth or founding, from the run seed and the organism id, and never changes. This depends on the phase 2b fix and is checked there by an engine test that asserts zero mating-type changes over a multi-tick run (`tests/test_jr5_phase2b_self_mode.py::test_no_organism_ever_changes_sex_over_many_ticks` on the phase 2b branch). Self-arm founders are all hermaphrodites: with `mating_type_set=[hermaphrodite]` no type is drawn, so the self arms are male-free obligate selfers, as in the outcross-versus-self mutation-load experiment in REFERENCES.md (Nature, 2009). Outcross-arm founders draw their type from the run seed and organism id at the arm's sex ratio. Pinned in the prereg constants under `host_mating_arm_modes.founders`.
5. Acceptance: ledger residual at most 1e-9, replay identity, and the phase 3 gate.
