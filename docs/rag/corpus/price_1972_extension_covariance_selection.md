# Extension of covariance selection mathematics

**CodonTrace Genesis literature digest** (not a substitute for the paper).

- **id:** `price_1972_extension_covariance_selection`
- **authors:** George R. Price
- **year:** 1972
- **venue:** Annals of Human Genetics 35:485-490
- **identifiers:** doi:10.1111/j.1469-1809.1972.tb00796.x
- **tags:** Price, Price equation, transmission, covariance, selection, 1972, Okasha, MLS1, collective intelligence, evidence
- **claim ceiling:** `runtime_observation`

## Digest

Price (1972, Annals of Human Genetics doi:10.1111/j.1469-1809.1972.tb00796.x) extends the 1970 covariance selection identity to include a transmission / change-in-character term. The discrete form used in multilevel bookkeeping is Δz̄ = Cov(w, z)/w̄ + E[w Δz]/w̄. The second term is not optional decoration: without it the identity does not account for mutation, imperfect inheritance, or other parent–offspring change. A last-generation covariance snapshot (Phase J) is incomplete as a Price analysis. CodonTrace Genesis Phase K `run_multi_generation_price_analysis` estimates transmission from realized parent–offspring preference change after mutation on the two-task analog, checks a residual, and still sets `price_equation_complete=False`. That is analog bookkeeping, not this paper.

## Key claims

- The selection-as-covariance identity is completed by a transmission term.
- Truncation-plus-mutation on a toy trait can estimate a transmission number; that is not a Price 1972 empirical result.
- A transmission number is not collective intelligence and not a major transition.

## What CodonTrace Genesis has

Phase K multi-generation Price scaffold with `transmission_term_estimated=True` and an attached Phase J last-generation MLS1 snapshot.

## What CodonTrace Genesis lacks

A published multi-generation Price paper; Avida `DEME_GROUP` MLS2; empirical covariance tables.

## Next experiment

How to get collective intelligence evidence: keep Price terms as measurement; do not set `price_equation_complete` from an analog residual. Claim ceiling `runtime_observation`.

Retrieving this digest is not `collective_intelligence` or intelligence evidence.
