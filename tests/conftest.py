"""Suite-wide test isolation."""

from __future__ import annotations

import os
from collections.abc import Iterator

import pytest


@pytest.fixture(autouse=True)
def _restore_cpu_affinity() -> Iterator[None]:
    """Restore this process's CPU affinity after every test.

    The campaign workers in scripts/grand_frontier_* call
    os.sched_setaffinity(0, {core}) on the calling process. Tests that run a
    worker in-process (test_grand_frontier_challenges_suite.py,
    test_five_phase_fixes.py) otherwise pin the whole pytest process, or
    xdist worker, to one CPU for every later test: that made
    test_tester1_r06_r10.py's cores check fail on CI and slowed the suite.
    """
    get_affinity = getattr(os, "sched_getaffinity", None)
    set_affinity = getattr(os, "sched_setaffinity", None)
    before = get_affinity(0) if callable(get_affinity) else None
    yield
    if before is not None and callable(set_affinity):
        set_affinity(0, before)
