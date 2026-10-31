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
# P5 snapshot digest, diploid_meiosis off, seed 11, 30 ticks, initial_atp 200,
# basal cost 0, max_population 24; computed on main 7db2227 before the fix.
DIPLOID_OFF_P5_DIGEST = "clp5snap:c9f2709fa7315c7a1430fcbfa9867df993b838f83abf3017bc52de95542a9b95"


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
    and at least one organism of each role after 30 ticks, seed 11. The
    diploid-off run with the same settings must give the snapshot digest
    computed on main 7db2227 before this change (pinned below).
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
    off = ClosedLoopP5Session.boot(seed=11, **kwargs)
    off.run_ticks(30)
    assert off.snapshot_digest() == DIPLOID_OFF_P5_DIGEST


def _expected_end_to_end_recombinant_fraction(m: int) -> float:
    """Exact P(first and last codon of a gamete come from different homologs).

    The crossover window over ``m`` paired codons: start uniform on 0..m-1;
    length uniform on 1..(m - start), one less when start is 0; a start-0
    length-1 window becomes length 2 when m >= 3. The two end codons differ in
    source exactly when one of them lies inside the window.
    """

    total = 0.0
    for start in range(m):
        max_len = m - start - (1 if start == 0 else 0)
        for length in range(1, max_len + 1):
            eff = 2 if (m >= 3 and start == 0 and length == 1) else length
            inside = {i for i in range(start, start + eff)}
            total += (1 / m) * (1 / max_len) * ((0 in inside) != (m - 1 in inside))
    return total


def test_crossover_gives_the_derived_recombinant_fraction() -> None:
    """Meiotic crossover recombines the two end loci at the derived rate.

    Basis: a gamete is recombinant for two loci when they come from different
    homologs, which happens only through a crossover between them. For the
    one-window exchange used here, with m = 4 paired codons, enumerating the
    window distribution gives, by start codon 0..3, recombinant shares 1
    (windows 0-1, 0-1, 0-2), 1/3, 1/2 and 1, so P = (1 + 1/3 + 1/2 + 1) / 4 =
    17/24 (see the helper). Tolerance: 4 binomial standard errors
    over 4000 gametes, seed 13. Without crossover the fraction is 0, so a
    dropped crossover fails.
    """

    expected = _expected_end_to_end_recombinant_fraction(4)
    assert abs(expected - 17 / 24) < 1e-12
    parent = _heterozygote(8)
    rng = RNGManager(13)
    n = 4000
    hits = 0
    for i in range(n):
        gamete = meiotic_gamete(parent, WIDTH, rng.fork(f"x/{i}"))
        hits += gamete[:WIDTH] != gamete[3 * WIDTH : 4 * WIDTH]
    se = (expected * (1 - expected) / n) ** 0.5
    assert abs(hits / n - expected) < 4 * se
    no_x = sum(
        (g := meiotic_gamete(parent, WIDTH, rng.fork(f"n/{i}"), crossover=False))[:WIDTH] != g[3 * WIDTH : 4 * WIDTH]
        for i in range(200)
    )
    assert no_x == 0


def test_chamber_pair_from_one_parent_is_meiosis_and_fusion() -> None:
    """Two chamber slots of one parent give a selfed zygote, not a clone.

    Basis: selfing is two independent meioses of one parent and a fusion, so a
    locus heterozygous in the parent is heterozygous in the child with
    probability 1/2 (expected H = 0.5). Tolerance: H per child lies in [0, 1],
    variance at most 1/4, so 4 standard errors over N = 2000 children are at
    most 4 * 0.5 / sqrt(2000). The child keeps the parent's length.
    """

    from codontrace.genesis.birth import IncipientOffspring
    from codontrace.genesis.population import _fertilise

    parent = _heterozygote(8)
    slot = IncipientOffspring(
        slot_id="s1",
        parent_id="p",
        genome_bits=parent,
        genome_digest="d",
        entered_tick=0,
        parent_position=(0, 0),
        offspring_runtime_atp=1.0,
        parent_generation=0,
        codon_width=WIDTH,
    )
    other = IncipientOffspring(**{**{f: getattr(slot, f) for f in slot.__slots__}, "slot_id": "s2"})
    n = 2000
    total = 0.0
    for i in range(n):
        record = _fertilise(slot, other, RNGManager(i), crossover=True)
        assert record is not None
        assert len(record.child_genome_bits) == len(parent)
        assert record.parent_b_id == "p:self_gamete"
        total += _heterozygosity(record.child_genome_bits)
    assert abs(total / n - 0.5) < 4 * 0.5 / n**0.5
