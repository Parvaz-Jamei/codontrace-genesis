# Closed-loop P5 status — 2026-09-25

Scope: `outcross_locus_mating_effort_cost`. On `main` at the P5 commit, plus the silent-locus story.

## The experiment

Question: does bits `[15:18)` change mating effort without running as an action?

Three arms, one seed. `001` pays `outcross_runtime_cost` and uses the birth chamber. `000` and ablation pay no such line and birth alone. All three compile the same 15-bit program; the codon stays on the genome. `red_queen_proved` stays false. This is not Morran 2011.

## What this is

A heritable codon at genome bits `[15:18)`, after the 9-bit program and the 6-bit κ window.

- `000` selfs. Birth stays asexual. No sex-specific ATP line.
- Any other codon (`001` in the founders) enters the existing birth chamber and debits `outcross_runtime_atp` (default 1.0) from `atp_state` with reason `outcross_runtime_cost`.
- Ablation ignores the bits, forces asexual birth, and writes no such line.
- Same-role pairs only. A primary does not mate a secondary.
- Both recombinants are placed. `two_fold_cost_sex` stays false.
- The 1.0 debit is taken only after the birth gate, the population cap, and the chamber have already accepted the parent, and only after the offspring share is calculated. A refused birth leaves no `outcross_runtime_cost` line. The share itself is not shrunk by the fee.
- A waiting outcrosser who was accepted still pays. That is the entry cost. It is not a mate-found toll, and it is not the two-fold cost.
- The three locus bits are not executed. The brain is the 15-bit prefix. The codon remains on the genome and is what children inherit.

## What this is not

- Not Maynard Smith's two-fold cost of males. A flat debit that still places both offspring is mating-effort (Lehtonen, Jennions, Kokko 2012, doi:10.1016/j.tree.2011.09.016), not a halved birth rate.
- Not Morran 2011 (doi:10.1126/science.1206360). No control / evolution / coevolution arms. `red_queen_proved` is false. `morran_ready` is false. Ceiling is `candidate_evidence`.
- Not `xol-1` / `fog-2`.
- Not a change to `engine.py`, P3 founder literals, or default asexual reproduction.

## Why this shape

Researcher: the two-fold cost is one placed offspring, or a 2× debit per survivor. A fee is not that.
Creative: a waiting-chamber upkeep is the cost that matters in a starving world; do not discard a child and call it two-fold.
Systems: the locus must be one full codon or `mutate_genome` / `SemanticGenome` drops a partial tail. `111` must not be the allele, because that codon is `COPY_SELF` and debits 8.
Lock: gene-gated mating-effort debit on the existing chamber. Two-fold remains a later switch, default off.

## Accept

`tests/closed_loop/test_closed_loop_p5_accept.py`

- window does not move κ
- partial codon refused
- outcross pays and recombines; claims stay locked
- ablation: zero sex debit, asexual births
- selfing allele pays nothing
- cross-role pays the entry cost and does not recombine
- differing alleles `001` and `010` are what children carry
- replay matches; P3 replay still matches; engine.py has no outcross/infection/parasite/red_queen
