"""Focused GENESIS Foundation Kernel path.

This example prints ordinary Python object summaries only. It does not create
files, dashboards, reports, notebooks, or visualizations.
"""

from __future__ import annotations

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

from codontrace import AliveGateConfig, GenesisOrganism, Ribosome, World2D


def main() -> None:
    codon_table = Ribosome.genesis_v0()
    genome_bits = "001011101000"  # SENSE_FOOD -> MOVE_TOWARD -> EAT_LUMEN -> WAIT
    translation = codon_table.translate(genome_bits)
    organism = GenesisOrganism.from_bits(
        "genesis-1",
        genome_bits,
        initial_runtime_atp=5.0,
        position=(0, 0),
        ribosome=codon_table,
    )
    world = World2D(3, 1, resources={(1, 0): 2.0})
    result = organism.run(world, ticks=4, alive_config=AliveGateConfig(min_ticks=4))

    print("Genesis Codon Table v0")
    print("Nexus genome bits:", translation.genome_bits)
    print("CompiledBrain tokens:", [token.action for token in result.compiled_brain.tokens])
    print("Trace actions:", [event.action for event in result.trace.events])
    print("Final ATP_runtime:", result.alive_result.final_runtime_atp)
    print("AliveGateResult passed:", result.alive_result.passed)


if __name__ == "__main__":
    main()
