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
    QDArchivePolicy,
    QDElite,
    assign_behavior_bin,
    update_qd_archive_many,
)

schema = BehaviorDescriptorSchema(
    descriptor_names=("novelty", "complexity"),
    bins_per_descriptor={"novelty": 4, "complexity": 4},
    min_values={"novelty": 0.0, "complexity": 0.0},
    max_values={"novelty": 4.0, "complexity": 4.0},
)
config = QDArchiveConfig(
    schema=schema,
    policy=QDArchivePolicy(replacement_policy="higher_fitness"),
    archive_id="demo-archive",
)


def elite(name: str, fitness: float, novelty: float, complexity: float) -> QDElite:
    descriptor = {"novelty": novelty, "complexity": complexity}
    return QDElite(
        organism_id=name,
        fitness=fitness,
        behavior_descriptor=descriptor,
        behavior_bin=assign_behavior_bin(descriptor, schema),
        genome_digest=f"genome:{name}",
        trace_digest=f"trace:{name}",
    )


batch = update_qd_archive_many(
    QDArchive.empty(config),
    (elite("a", 1.0, 0.5, 0.5), elite("b", 2.0, 0.6, 0.6), elite("c", 0.8, 3.0, 3.0)),
)
summary = batch.summary
print({"filled_bins": summary.filled_bins, "coverage_percent": summary.coverage_percent})
