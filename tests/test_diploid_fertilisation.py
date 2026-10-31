"""Diploid meiosis and fertilisation conserve genome length and segregate 1:1.

A diploid genome stores two homologs as interleaved codons (even and odd
positions). Meiosis makes one haploid gamete (segregation plus an optional
crossover between the homologs); fertilisation fuses one gamete from each
parent back into two homologs. This is the standard two-homolog model used by
forward population-genetic simulators, where an individual is a pair of
haploid genomes, one inherited from each parent.
"""

from __future__ import annotations

from collections import Counter

from codontrace.genesis.birth import (
    fuse_gametes,
    meiotic_gamete,
    split_diploid_homologs,
)
from codontrace.genesis.closed_loop_p5 import ClosedLoopP5Session
from codontrace.rng import RNGManager

WIDTH = 3


def _heterozygote(codons: int) -> str:
    """Even homolog all ``000``, odd homolog all ``111``: heterozygous at every locus."""

    return "".join("000" if i % 2 == 0 else "111" for i in range(codons))


def _heterozygosity(bits: str) -> float:
    even, odd = split_diploid_homologs(bits, WIDTH)
    pairs = [(even[i : i + WIDTH], odd[i : i + WIDTH]) for i in range(0, len(odd) - len(odd) % WIDTH, WIDTH)]
    return sum(a != b for a, b in pairs) / len(pairs)


def test_genome_length_is_conserved_over_many_generations() -> None:
    """Fertilisation is the inverse of the homolog split, so length is invariant.

    Basis: a zygote holds one homolog from each gamete, and each gamete holds one
    copy of every locus, so the diploid length after syngamy equals the parent
    length. Expected value: the founder length, exactly, after 50 generations,
    for even and odd codon counts and a genome with trailing non-codon bits.
    """

    rng = RNGManager(20261031)
    for start in ("010110001111000101", "0101100011110001011", "01011000111100010111001"):
        own, mate = start, start[::-1]
        for generation in range(50):
            gen_rng = rng.fork(f"{len(start)}/{generation}")
            child_a = fuse_gametes(
                meiotic_gamete(own, WIDTH, gen_rng.fork("a")),
                meiotic_gamete(mate, WIDTH, gen_rng.fork("b")),
                WIDTH,
                parent_codon_count=len(own) // WIDTH,
            )
            child_b = fuse_gametes(
                meiotic_gamete(mate, WIDTH, gen_rng.fork("c")),
                meiotic_gamete(own, WIDTH, gen_rng.fork("d")),
                WIDTH,
                parent_codon_count=len(mate) // WIDTH,
            )
            own, mate = child_a, child_b
            assert len(own) == len(start)
            assert len(mate) == len(start)


def test_heterozygote_segregates_one_to_one() -> None:
    """A heterozygote transmits each allele to half of its gametes.

    Basis: Mendelian segregation; each gamete carries one of the two homologs at
    a locus with probability 1/2, with or without a crossover. Test: Pearson
    chi-square with 1 degree of freedom on 4000 gametes at the first locus,
    alpha = 0.01, critical value 6.635 (chi-square quantile 0.99, 1 df);
    fixed seed 7.
    """

    parent = _heterozygote(8)
    rng = RNGManager(7)
    n = 4000
    counts = Counter(meiotic_gamete(parent, WIDTH, rng.fork(f"g/{i}"))[:WIDTH] for i in range(n))
    assert set(counts) == {"000", "111"}
    expected = n / 2
    chi2 = sum((counts[a] - expected) ** 2 / expected for a in ("000", "111"))
    assert chi2 < 6.635


def test_selfing_halves_heterozygosity_each_generation() -> None:
    """Selfing a heterozygote halves heterozygosity per generation.

    Basis: under self-fertilisation a heterozygous locus stays heterozygous with
    probability 1/2 and homozygotes stay homozygous, so H_t = H_0 / 2**t
    (expected ratio 1/2 per generation). Tolerance: H is a mean of values in
    [0, 1], whose variance is at most 1/4, so 4 standard errors are at most
    4 * 0.5 / sqrt(N) for N independent selfed lineages; fixed seed 99.
    """

    n = 3000
    rng = RNGManager(99)
    lineages = [_heterozygote(8)] * n
    tolerance = 4 * 0.5 / n**0.5
    for generation in range(1, 4):
        nxt = []
        for i, parent in enumerate(lineages):
            r = rng.fork(f"{generation}/{i}")
            nxt.append(
                fuse_gametes(
                    meiotic_gamete(parent, WIDTH, r.fork("egg")),
                    meiotic_gamete(parent, WIDTH, r.fork("pollen")),
                    WIDTH,
                    parent_codon_count=len(parent) // WIDTH,
                )
            )
        lineages = nxt
        mean_h = sum(_heterozygosity(b) for b in lineages) / n
        assert abs(mean_h - 0.5**generation) < tolerance


def test_p5_run_with_diploid_meiosis_keeps_both_arms_and_genome_length() -> None:
    """Both P5 arms persist over 30 ticks with diploid meiosis on.

    Basis: with fusion fertilisation the genome length is conserved, so the
    outcross locus and the program stay decodable and neither arm is lost to
    shrinking genomes. Uses the outcross P5 session on main (the selfing arm is
    on a separate branch). Expected: founder length 18 bits for every organism
    and at least one organism of each role after 30 ticks, seed 11, as in the
    diploid-off run with the same settings; the diploid-off digest is unchanged.
    """

    kwargs = {"initial_atp": 200.0, "basal_atp_cost": 0.0, "max_population": 24}
    session = ClosedLoopP5Session.boot(seed=11, diploid_meiosis=True, **kwargs)
    session.run_ticks(30)
    organisms = session.runner.population.organisms
    roles = Counter(session.roles.get(o.id) for o in organisms)
    assert roles["primary"] > 0
    assert roles["secondary"] > 0
    assert {len(o.genome.to_compact()) for o in organisms} == {18}
    assert session.recombination_births > 0
