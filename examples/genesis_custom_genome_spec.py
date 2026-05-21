"""Create non-binary genomes and codon tables without external dependencies."""

try:
    from ._path_bootstrap import ensure_src_path
except ImportError:  # direct script or runpy execution outside the examples package
    import sys as _sys
    from pathlib import Path as _Path

    _EXAMPLES_DIR = _Path(__file__).resolve().parent
    if str(_EXAMPLES_DIR) not in _sys.path:
        _sys.path.insert(0, str(_EXAMPLES_DIR))
    from _path_bootstrap import ensure_src_path

ensure_src_path()

from codontrace import Codon, CodonTable, CodonTableSpec, GenomeSpec, SemanticGenome

spec = GenomeSpec.dna3()
genome = SemanticGenome.from_codons(("ACG", "TTA"), spec=spec)
table_spec = CodonTableSpec(genome_spec=spec, table_name="dna_demo")
table = CodonTable(
    (Codon("ACG", "SENSE", 0.1, spec=spec), Codon("TTA", "WAIT", 0.0, spec=spec)), spec=table_spec
)
print({"genome": genome.to_dict(), "first_action": table.decode("ACG").action_name})
