# HE03 science brief (2026-09-17) — ≤2 targeted searches

## Searches performed
1. Goldsby, Dornhaus, Kerr, Ofria (2012). Task-switching costs promote the evolution of division of labor and shifts in individuality. *PNAS* 109(34):13686–13691. doi:10.1073/pnas.1202233109
2. Gorelick, Bertram, Killeen, Fewell (2004). Normalized mutual entropy in biology: quantifying division of labor. *Am Nat* 164:677–682. doi:10.1086/424968

## Design implications (locked into prereg)
- **E3 / Goldsby:** Cost gradient (0 / moderate≈25-cycle analogue / high≈50-cycle analogue) promotes DoL; under high cost, specialists often lose solo competence → IsolationAssay (isolation performance drop) as secondary readout of lost lower-level autonomy.
- **Gorelick NMI:** Confirmatory DoL = normalized mutual information / entropy on individual×task matrices: \(D_{task}=I/H(Y)\), \(D_{indiv}=I/H(X)\), \(D_{sym}=I/\sqrt{H(X)H(Y)}\). Planned `gorelick_nmi`; non-NMI proxies stay **legacy**.
- **Order:** HE03 (E3) after HE02 (E1+E2+E5). This brief + `docs/HARD_EXPERIMENT_03_PREREG.md` are **docs-only**; no engine code in the prereg PR.
- **Seeds:** pilot 1000–1009 vs disjoint analysis seeds.

## Non-goals
No intelligence / collective_intelligence / AGI claims. Ceiling starts at `runtime_observation`. Pins A–E unchanged. Default-off knobs only. No Avida-scale / Goldsby-update-count claims on pure Python. No HE02 path edits in the HE03 prereg PR.
