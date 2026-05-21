"""Demonstrate ADF/Dynamic Vocabulary proposal objects without file output."""

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

from codontrace.genesis import (
    DynamicVocabularyConfig,
    DynamicVocabularyState,
    GenesisATPState,
    propose_dynamic_vocabulary,
)
from codontrace.trace import TraceEvent


def event(step: int, action: str, codon: str) -> TraceEvent:
    return TraceEvent(
        step=step,
        agent_id="org-a",
        codon=codon,
        action=action,
        atp_before=10.0,
        atp_after=9.0,
        position_before=(0, 0),
        position_after=(0, 0),
    )


def main() -> None:
    traces = [
        [event(0, "WAIT", "000"), event(1, "MOVE_TOWARD", "011")],
        [event(0, "WAIT", "000"), event(1, "MOVE_TOWARD", "011")],
        [event(0, "WAIT", "000"), event(1, "MOVE_TOWARD", "011")],
    ]
    state = DynamicVocabularyState(base_table_version="genesis_v0")
    atp = GenesisATPState.from_runtime(10.0, learning_atp=4.0, learning_enabled=True)
    result = propose_dynamic_vocabulary(
        traces,
        state,
        atp,
        DynamicVocabularyConfig(allow_auto_accept=False),
        tick=2,
        organism_id="org-a",
    )
    print("ADF patterns:", result.patterns_found)
    print("ADF proposals:", result.proposals_created)
    print("Accepted proposals:", result.proposals_accepted)
    print("Vocabulary digest:", result.vocabulary_digest_after)


if __name__ == "__main__":
    main()
