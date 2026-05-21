"""Compact Quality-Diversity archive hook example for CodonTrace GENESIS."""

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
    BehaviorDescriptorSchema,
    QDArchive,
    QDArchiveConfig,
    QDElite,
    assign_behavior_bin,
    summarize_qd_archive,
    update_qd_archive,
)


def main() -> None:
    schema = BehaviorDescriptorSchema(
        descriptor_names=("novelty", "complexity"),
        bins_per_descriptor={"novelty": 4, "complexity": 4},
        min_values={"novelty": 0.0, "complexity": 0.0},
        max_values={"novelty": 10.0, "complexity": 10.0},
    )
    archive = QDArchive.empty(QDArchiveConfig(schema=schema))
    descriptor = {"novelty": 7.0, "complexity": 3.0}
    behavior_bin = assign_behavior_bin(descriptor, schema)
    elite = QDElite("organism-demo", 2.5, descriptor, behavior_bin, "genome-demo", "trace-demo")
    updated = update_qd_archive(archive, elite).archive
    summary = summarize_qd_archive(updated)
    print(
        {
            "filled_bins": summary.filled_bins,
            "coverage": summary.coverage,
            "qd_score": summary.qd_score,
        }
    )


if __name__ == "__main__":
    main()
