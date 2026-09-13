# HE02 science brief (2026-09-13) — ≤2 targeted searches

## Searches performed
1. Floreano, Mitri, Magnenat, Keller (2007). Evolutionary conditions for the emergence of communication in robots. *Curr Biol* 17(6):514–519. doi:10.1016/j.cub.2007.01.058
2. Knoester, McKinley, Ofria (2008). Cooperative network construction using digital germlines. *GECCO ’08*. doi:10.1145/1389095.1389130

## Design implications (locked into prereg)
- **E1 (Floreano):** Food-location signals only evolve when information has selective value; honest signals favored under high relatedness + colony-level selection; individual×unrelated can yield deception. → `FoodPatchSignalConfig` + MI(payload; patch) manipulation check; capsules_shuffled MI≈0.
- **E2 (Knoester/Floreano MLS):** Germline / multilevel selection raises evolvability of cooperation. → `DemeSelectionConfig` 2×2 {INDIVIDUAL|GERMLINE_GROUP} × {CLONAL|MIXED} with preregistered ordinal pattern (not a single dz).
- **E5 (Lenski stepping-stone; cited in AGENT_PROMPT Addendum 2):** complex traits need intermediate rewards. → `SteppingStoneRewardConfig` inside HE02.
- **E6 already on main** (`hard_experiment_01_morris.py`); HE02 knobs should use Morris pilot seeds 1000–1009 before locking research config.

## Non-goals
No intelligence / collective_intelligence / AGI claims. Ceiling starts at `runtime_observation`. Pins A–E unchanged. Default-off knobs only.
