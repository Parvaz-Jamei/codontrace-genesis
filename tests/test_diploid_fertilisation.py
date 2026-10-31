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
    DIPLOID_FERTILISATION_MECHANISM,
    fuse_gametes,
    meiotic_gamete,
    split_diploid_homologs,
)
from codontrace.genesis.closed_loop_p5 import ClosedLoopP5Session
from codontrace.genesis.population import PopulationConfigs
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


def test_marked_homologs_at_full_recombination_prob() -> None:
    """With crossover on, a gamete joins the a and b end markers at 17/48.

    Basis: homolog a carries marker ``101`` at paired locus 0 and homolog b
    carries marker ``010`` at paired locus 3 (m = 4, other codons ``000`` and
    ``111``). The test calls ``_fertilise`` with ``crossover=True``, which is
    what the chamber passes at recombination_prob = 1 (the chamber path itself
    is covered by the step_population tests below). A gamete holds both markers only when loci 0 and 3 come from
    different homologs (probability 17/24, derived in the helper) and locus 0
    comes from homolog a (one half by symmetry of the lead choice), so the
    expected rate is 17/48. The own gamete is the even codons of the fused
    child. Tolerance: 4 binomial standard errors over 4000 zygotes, seed 21.
    With crossover off the rate is 0.
    """

    from codontrace.genesis.birth import IncipientOffspring
    from codontrace.genesis.population import _fertilise

    a = ["101", "000", "000", "000"]
    b = ["111", "111", "111", "010"]
    parent = "".join(x + y for x, y in zip(a, b, strict=True))

    def slot(slot_id: str) -> IncipientOffspring:
        return IncipientOffspring(
            slot_id=slot_id,
            parent_id=f"p{slot_id}",
            genome_bits=parent,
            genome_digest="d",
            entered_tick=0,
            parent_position=(0, 0),
            offspring_runtime_atp=0.0,
            parent_generation=0,
            codon_width=WIDTH,
            ledger_entry_ids=(),
        )

    own, mate = slot("s1"), slot("s2")
    expected = _expected_end_to_end_recombinant_fraction(4) / 2
    assert abs(expected - 17 / 48) < 1e-12
    rng = RNGManager(21)
    n = 4000

    def rate(crossover: bool, tag: str, count: int) -> float:
        hits = 0
        for i in range(count):
            record = _fertilise(own, mate, rng.fork(f"{tag}/{i}"), crossover=crossover)
            assert record is not None
            child = record.child_genome_bits
            assert len(child) == len(parent)
            gamete = [child[j * WIDTH : (j + 1) * WIDTH] for j in range(0, 8, 2)]
            hits += gamete[0] == "101" and gamete[3] == "010"
        return hits / count

    se = (expected * (1 - expected) / n) ** 0.5
    assert abs(rate(True, "x", n) - expected) < 4 * se
    assert rate(False, "n", 300) == 0.0


# sha256[:16] of the default-path digest table printed by
# tests/_scripts/default_path_digests.py (newline included), with
# diploid_meiosis off; matches the value recorded on main before the fix.
DEFAULT_PATH_TABLE_DIGEST = "224e72bce17aa5a4"
# Python 3.11 value, also given by main 7db2227 and 73c3bff on 3.11. Only the
# T02 and T03 rows differ, in the last bits of float metrics: the built-in
# sum() of floats uses compensated summation from 3.12 on, so 3.11 rounds
# differently (3.11: sum([0.1] * 10) == 0.9999999999999999; 3.12+: 1.0).
DEFAULT_PATH_TABLE_DIGEST_PY311 = "82dd7aa7e9bd2ba4"


def test_default_path_digest_table_is_unchanged() -> None:
    """The fix leaves every default-path digest unchanged.

    Basis: diploid_meiosis is off by default, so the life-loop world (seeds 0
    and 7, default and history configs) and the T01-T05 runners never reach
    meiosis or fusion, and their digests must equal the pre-fix values. The
    script runs in a fresh process because it sets CODONTRACE_SOURCE_ROOT
    before importing the engine. Expected: the table hash equals
    DEFAULT_PATH_TABLE_DIGEST exactly; tolerance zero. On Python 3.11 the
    expected value is DEFAULT_PATH_TABLE_DIGEST_PY311, because float sum()
    changed in 3.12 (see the constant); that difference predates the fix.
    """

    import hashlib
    import os
    import subprocess
    import sys
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    env = dict(os.environ, PYTHONPATH=str(root / "src"))
    out = subprocess.run(
        [sys.executable, str(root / "tests" / "_scripts" / "default_path_digests.py")],
        check=True,
        capture_output=True,
        env=env,
        timeout=900,
    ).stdout
    expected = DEFAULT_PATH_TABLE_DIGEST_PY311 if sys.version_info[:2] == (3, 11) else DEFAULT_PATH_TABLE_DIGEST
    assert sum([0.1] * 10) == (0.9999999999999999 if sys.version_info[:2] == (3, 11) else 1.0)
    assert hashlib.sha256(out).hexdigest()[:16] == expected


# Parent ``111 000 111 000``: even homolog ``111 111``, odd homolog
# ``000 000``, so it is heterozygous at both paired loci; the program
# reproduces under the chamber config below.
_CHAMBER_PARENT = "111000111000"


def _chamber_configs(recombination_prob: float) -> PopulationConfigs:
    """Chamber config with diploid on: clean reproduction, no mutation."""

    from codontrace.genesis.birth import ReproductionMode, SexualRecombinationConfig
    from codontrace.genesis.liveness import AliveGateConfig
    from codontrace.genesis.population import (
        MutationConfig,
        OffspringPlacementPolicy,
        PopulationConfigs,
        ReproductionConfig,
    )

    return PopulationConfigs(
        reproduction=ReproductionConfig(
            min_runtime_atp=1.0,
            parent_atp_cost=1.0,
            max_population=8,
            offspring_placement=OffspringPlacementPolicy.SAME_CELL,
            reproduction_mode=ReproductionMode.SEXUAL_CROSSOVER,
        ),
        mutation=MutationConfig(bit_flip_rate=0.0),
        alive_gate=AliveGateConfig(
            min_ticks=1,
            min_executed_actions=0,
            max_blocked_ratio=1.0,
            require_positive_runtime_atp=True,
        ),
        sexual_recombination=SexualRecombinationConfig(
            enabled=True,
            diploid_meiosis=True,
            chamber_capacity=8,
            recombination_prob=recombination_prob,
        ),
    )


def _chamber_children(recombination_prob: float, seeds: range) -> list[tuple[str, str | None]]:
    """Children of two copies of one heterozygous genome, with record mechanism."""

    from codontrace.genesis.organism import GenesisOrganism
    from codontrace.genesis.population import PopulationState, step_population
    from codontrace.world import World2D

    configs = _chamber_configs(recombination_prob)
    out: list[tuple[str, str | None]] = []
    for seed in seeds:
        parents = tuple(
            GenesisOrganism.from_bits(name, _CHAMBER_PARENT, initial_runtime_atp=20.0, position=(0, i))
            for i, name in enumerate(("a", "a2"))
        )
        result = step_population(PopulationState(0, 0, parents, (), ()), World2D(4, 4), configs, seed=seed)
        mechanisms = [
            rec.reproduction_result.recombination_record.mechanism
            for rec in result.organism_records
            if rec.reproduction_result is not None and rec.reproduction_result.recombination_record is not None
        ]
        children = [o.genome.to_compact() for o in result.population.organisms[2:]]
        assert children and mechanisms
        out.extend((child, mechanisms[0]) for child in children)
    return out


def _paired_loci(child: str) -> list[tuple[str, str]]:
    codons = [child[i : i + WIDTH] for i in range(0, len(child), WIDTH)]
    return list(zip(codons[0::2], codons[1::2], strict=True))


def test_chamber_step_selfs_by_meiosis_and_fusion() -> None:
    """step_population with diploid on fuses gametes; selfed H is about 1/2.

    Basis: both parents carry one fully heterozygous genome, so a child is
    genetically selfed. Each gamete carries either allele at a locus with
    probability 1/2 (the lead homolog is chosen with p = 1/2 and the crossover
    window is symmetric in the two homologs), and the two gametes are
    independent meioses, so a child locus is heterozygous with probability
    1/2: expected H = 0.5. Every record must name diploid_gamete_fusion and
    the child keeps the 12-bit parent length; routing the chamber to the
    haploid segment swap changes the mechanism and fails. Tolerance: per-child
    H lies in [0, 1] with variance at most 1/4, so 4 SE over n children is at
    most 4 * 0.5 / sqrt(n); seeds 0..399.
    """

    children = _chamber_children(1.0, range(400))
    assert {mechanism for _, mechanism in children} == {DIPLOID_FERTILISATION_MECHANISM}
    assert all(len(child) == len(_CHAMBER_PARENT) for child, _ in children)
    h = [sum(even != odd for even, odd in _paired_loci(child)) / 2 for child, _ in children]
    n = len(h)
    assert abs(sum(h) / n - 0.5) < 4 * 0.5 / n**0.5


def test_chamber_with_zero_recombination_prob_has_no_recombinant_gametes() -> None:
    """recombination_prob = 0 with diploid on: gametes keep whole homologs.

    Basis: with m = 2 paired loci the homologs are ``111 111`` and
    ``000 000``. Without crossover a gamete is one whole homolog, so its two
    loci always match (recombinant fraction 0). With obligate crossover the
    window for m = 2 always swaps exactly one locus (start 0 is cut to length
    1, start 1 has length 1), so every gamete is recombinant (fraction 1).
    The own gamete is the child's even codons and the mate gamete its odd
    codons. Expected: exactly 0 and exactly 1; tolerance zero; seeds 0..59.
    """

    def recombinant(children: list[tuple[str, str | None]]) -> float:
        gametes = [side for child, _ in children for side in zip(*_paired_loci(child), strict=True)]
        return sum(g[0] != g[1] for g in gametes) / len(gametes)

    off = _chamber_children(0.0, range(60))
    assert {mechanism for _, mechanism in off} == {DIPLOID_FERTILISATION_MECHANISM}
    assert recombinant(off) == 0.0
    assert recombinant(_chamber_children(1.0, range(60))) == 1.0


def test_forged_fusion_record_is_rejected() -> None:
    """A fusion record whose child is not the two gametes interleaved fails.

    Basis: a fused child must hold the own gamete on even codons and the mate
    gamete on odd codons. Replacing the child with the parent clone, or
    swapping the two gametes, breaks that layout, so is_gamete_fusion is False
    and the record refuses to build. Expected: True for the genuine record,
    False and ValueError for each forgery.
    """

    import dataclasses

    import pytest

    from codontrace.genesis.birth import fertilisation_record, is_gamete_fusion

    own, mate = "111000", "000111"
    record = fertilisation_record(
        own_id="a",
        mate_id="b",
        own_gamete=own,
        mate_gamete=mate,
        own_digest="da",
        mate_digest="db",
        codon_width=WIDTH,
        parent_codon_count=4,
        rng=RNGManager(5),
    )
    assert is_gamete_fusion(record.child_genome_bits, own, mate, WIDTH)
    for forged_child in (_CHAMBER_PARENT[:12], fuse_gametes(mate, own, WIDTH, parent_codon_count=4)):
        assert not is_gamete_fusion(forged_child, own, mate, WIDTH)
        with pytest.raises(ValueError, match="interleave"):
            dataclasses.replace(record, child_genome_bits=forged_child)


def test_fused_child_drops_parent_spans() -> None:
    """A fused diploid child carries no parent spans; the haploid swap keeps them.

    Basis: spans are bit intervals on the parent's layout. Fusion interleaves
    two gametes, so a parent interval no longer marks the same codons in the
    child, and the fusion path returns the child without spans. Both parents
    carry a silent span on bits 9-12 of ``111 000 111 000``. Expected: with
    diploid on, every child has spans == () and keeps the 12-bit length; with
    diploid off, the segment swap of two identical parents keeps the span, so
    removing the fusion branch fails the first check. Seed 3, exact.
    """

    import dataclasses

    from codontrace.genome import BitSpan

    span = BitSpan(9, 12, "silent", "tag")
    base = _chamber_configs(1.0)

    def children(diploid: bool) -> list[tuple[str, tuple[BitSpan, ...]]]:
        from codontrace.genesis.organism import GenesisOrganism
        from codontrace.genesis.population import PopulationState, step_population
        from codontrace.world import World2D

        configs = dataclasses.replace(
            base,
            sexual_recombination=dataclasses.replace(base.sexual_recombination, diploid_meiosis=diploid),
        )
        parents = []
        for i, name in enumerate(("a", "a2")):
            org = GenesisOrganism.from_bits(name, _CHAMBER_PARENT, initial_runtime_atp=20.0, position=(0, i))
            parents.append(dataclasses.replace(org, genome=org.genome.with_spans((span,))))
        result = step_population(PopulationState(0, 0, tuple(parents), (), ()), World2D(4, 4), configs, seed=3)
        return [(o.genome.to_compact(), o.genome.spans) for o in result.population.organisms[2:]]

    fused = children(True)
    assert fused and all(spans == () and len(bits) == 12 for bits, spans in fused)
    swapped = children(False)
    assert swapped and all(spans == (span,) for _, spans in swapped)
