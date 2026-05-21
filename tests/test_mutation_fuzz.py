from __future__ import annotations

from collections import Counter

from codontrace import ATPAccount, CodonTable, Mutation, SemanticGenome, WhiteBoxAgent, World2D


def test_1000_seeded_mutations_are_syntactically_safe_and_behaviorally_reported() -> None:
    table = CodonTable.default_minimal()
    genome = SemanticGenome.from_codons(["000", "001", "010", "011", "100", "101"])
    operations = ("point", "insert", "delete", "swap")
    counts: Counter[str] = Counter()
    valid = 0
    for index in range(1000):
        operation = operations[index % len(operations)]
        mutation = getattr(Mutation, operation)(seed=index)
        child = mutation.apply(genome, parent_id="root", generation=index, codon_table=table)
        assert len(child) > 0
        assert all(len(codon) == 3 for codon in child.to_codons())
        assert all(
            codon in {"000", "001", "010", "011", "100", "101", "110", "111"}
            for codon in child.to_codons()
        )
        world = World2D.from_ascii("""
...
.A.
...
""")
        agent = WhiteBoxAgent(
            id="mutant",
            genome=child,
            codon_table=table,
            atp_account=ATPAccount(10.0),
            position=(1, 1),
        )
        trace = agent.run(world.clone(), steps=min(5, len(child)))
        assert len(trace) > 0
        assert mutation.last_log[0].to_dict()
        counts[operation] += 1
        if mutation.last_log[0].syntactic_valid and mutation.last_log[0].behavioral_valid:
            valid += 1
    assert valid >= 950
    assert counts == {"point": 250, "insert": 250, "delete": 250, "swap": 250}
