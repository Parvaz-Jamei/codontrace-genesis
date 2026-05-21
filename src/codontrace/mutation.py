"""Deterministic valid genome mutation with serializable lineage logs."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field

from codontrace.codon import CodonTable
from codontrace.genome import SemanticGenome
from codontrace.rng import RNGManager
from codontrace.specs import GenomeSpec


@dataclass(frozen=True, slots=True)
class MutationLog:
    """Serializable mutation lineage entry."""

    parent_id: str
    child_id: str
    generation: int
    operation: str
    before_genome: str
    after_genome: str
    syntactic_valid: bool
    behavioral_valid: bool

    def to_dict(self) -> dict[str, str | int | bool]:
        """Return a JSON-friendly dictionary."""

        return asdict(self)


@dataclass(slots=True)
class Mutation:
    """One deterministic mutation operation."""

    operation: str
    index: int | None = None
    value: str | None = None
    seed: int | None = None
    rng: RNGManager | None = None
    last_log: list[MutationLog] = field(default_factory=list, init=False)

    @classmethod
    def point(cls, index: int | None = None, seed: int | None = None) -> Mutation:
        return cls(operation="point", index=index, seed=seed)

    @classmethod
    def insert(
        cls,
        index: int | None = None,
        value: str | None = None,
        seed: int | None = None,
    ) -> Mutation:
        return cls(operation="insert", index=index, value=value, seed=seed)

    @classmethod
    def delete(cls, index: int | None = None, seed: int | None = None) -> Mutation:
        return cls(operation="delete", index=index, seed=seed)

    @classmethod
    def swap(cls, index: int | None = None, seed: int | None = None) -> Mutation:
        return cls(operation="swap", index=index, seed=seed)

    def apply(
        self,
        genome: SemanticGenome,
        *,
        parent_id: str = "parent",
        generation: int = 0,
        codon_table: CodonTable | None = None,
    ) -> SemanticGenome:
        """Apply mutation and return a valid new genome."""

        codons = list(genome.to_codons())
        genome_spec = genome.spec
        stream = (
            self.rng if self.rng is not None else RNGManager(seed=self.seed).fork(self.operation)
        )
        self.last_log.clear()

        if self.operation == "point":
            codon_index = self._resolve_index(stream, len(codons))
            bit_index = stream.randrange(genome_spec.codon_width)
            original = codons[codon_index]
            choices = tuple(
                symbol for symbol in genome_spec.alphabet if symbol != original[bit_index]
            )
            replacement = stream.choice(choices)
            codons[codon_index] = original[:bit_index] + replacement + original[bit_index + 1 :]
        elif self.operation == "insert":
            insert_index = self._resolve_insert_index(stream, len(codons))
            value = (
                self.value if self.value is not None else self._random_codon(stream, genome_spec)
            )
            SemanticGenome.from_codons([value], spec=genome_spec)
            codons.insert(insert_index, value)
        elif self.operation == "delete":
            if len(codons) <= 1:
                msg = "Cannot delete the only codon in a genome."
                raise ValueError(msg)
            delete_index = self._resolve_index(stream, len(codons))
            codons.pop(delete_index)
        elif self.operation == "swap":
            if len(codons) <= 1:
                msg = "Cannot swap codons in a one-codon genome."
                raise ValueError(msg)
            first = self._resolve_index(stream, len(codons))
            second = stream.randrange(len(codons))
            while second == first:
                second = stream.randrange(len(codons))
            codons[first], codons[second] = codons[second], codons[first]
        else:
            msg = f"Unsupported mutation operation {self.operation!r}."
            raise ValueError(msg)

        child = SemanticGenome.from_codons(codons, spec=genome_spec)
        table = codon_table if codon_table is not None else CodonTable.default_minimal()
        syntactic_valid = True
        behavioral_valid = self._is_behaviorally_valid(child, table)
        log = MutationLog(
            parent_id=parent_id,
            child_id=child.digest()[:16],
            generation=generation,
            operation=self.operation,
            before_genome=genome.to_compact(),
            after_genome=child.to_compact(),
            syntactic_valid=syntactic_valid,
            behavioral_valid=behavioral_valid,
        )
        self.last_log.append(log)
        return child

    def _resolve_index(self, stream: RNGManager, length: int) -> int:
        if self.index is None:
            return stream.randrange(length)
        if not 0 <= self.index < length:
            msg = f"Mutation index {self.index} out of range for length {length}."
            raise IndexError(msg)
        return self.index

    def _resolve_insert_index(self, stream: RNGManager, length: int) -> int:
        if self.index is None:
            return stream.randrange(length + 1)
        if not 0 <= self.index <= length:
            msg = f"Insert index {self.index} out of range for length {length}."
            raise IndexError(msg)
        return self.index

    @staticmethod
    def _random_codon(stream: RNGManager, spec: GenomeSpec) -> str:
        return "".join(stream.choice(spec.alphabet) for _ in range(spec.codon_width))

    @staticmethod
    def _is_behaviorally_valid(genome: SemanticGenome, table: CodonTable) -> bool:
        """Return whether a genome executes a compact deterministic scenario without crash."""

        from codontrace.agent import WhiteBoxAgent
        from codontrace.energy import ATPAccount
        from codontrace.world import World2D

        try:
            if not all(table.validate(codon) for codon in genome.to_codons()):
                return False
            world = World2D.from_ascii("""
...
.A.
...
""")
            agent = WhiteBoxAgent(
                id="mutant",
                genome=genome,
                codon_table=table,
                atp_account=ATPAccount(10.0),
                position=(1, 1),
            )
            trace = agent.run(world, steps=min(5, len(genome)))
            return len(trace) > 0
        except (ValueError, KeyError, IndexError, RuntimeError):
            return False
