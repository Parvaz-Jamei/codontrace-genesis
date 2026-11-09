# JR5 phase 2b snapshot integrity follow-up

The saved mating seed fixes sex at birth. Checking only the stored types is
not sufficient to identify that seed: distinct seeds can draw the same finite
vector of types while assigning future newborns differently. The previous
check accepted an edit from seed 20011 to 20150 for a six-organism vector.

Serialized mating snapshots now include `mating_snapshot_digest`, the SHA-256
of the sorted-key compact JSON before adding that field. Restoration checks
the original serialized data before rebuilding organisms. A stamped or seeded
snapshot without its checksum is refused, as are an edited seed and a reset
of generation, tick and lineage. Untyped, unseeded snapshots retain their
previous representation. Existing typed snapshots without this field must be
replayed from their original initialization rather than silently trusted.

This is an accidental-edit check, not authentication. A party able to rewrite
the entire snapshot and recompute the checksum can forge it. Directly
constructed in-memory states remain trusted program inputs; there is no
signature or external trusted snapshot store.

The serialized sexes-on digests change because of the added field. Removing
only that field exactly reproduces all twelve preceding fixed-sex pins;
sexes-off pins and engine dynamics do not change. No fit, scientific threshold,
founder mixture, energy fee or preregistered endpoint changes in this follow-up.
The checksum helper is an explicitly qualified, counted RNG-checker exemption:
it produces an integrity identifier, never a random draw.

For the self-mode checks, two independent gametes carry either allele of a
heterozygous locus with probability 1/2. Their fusion is heterozygous with
probability 1/2, giving H_t = H_0 / 2**t under complete selfing without mutation
or selection. Genome length is conserved by restoring both homologs at fusion.
The step_population tests cover three descendant generations and assert the
specified four-standard-error bound as a regression check; related births
are not independent biological replicates, and this is not a power analysis.
