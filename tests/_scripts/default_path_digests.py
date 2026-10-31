"""Print the default-path digest table (life-loop world plus T01-T05 runners) as JSON."""

import dataclasses
import enum
import hashlib
import json
import os
import tempfile

os.environ["CODONTRACE_SOURCE_ROOT"] = tempfile.mkdtemp()
from codontrace.engine import GenesisEngine
from codontrace.engine_digest import _digest
from codontrace.genesis.runtime_profiles import GenesisRuntimeProfile

out = {}
for seed in (0, 7):
    spec = GenesisRuntimeProfile.life_loop_world(seed=seed, tick_count=12, population=6)
    out[f"s{seed}.spec"] = spec.digest()
    for hist in (False, True):
        e = GenesisEngine.from_spec(spec)
        if hist:
            e.runner.configs = spec.population_configs
        r = e.run_ticks()
        k = f"s{seed}.{'hist' if hist else 'def'}"
        out[k + ".snap"] = r.snapshot.digest()
        out[k + ".ticks"] = _digest([t.digest() for t in r.ticks])
        out[k + ".core"] = _digest(r._core_payload())
        if not hist:
            out[k + ".full"] = r.digest()
from codontrace.experiments import t01_oee, t02_mls_price, t03_mutualism, t04_contingency, t05_red_queen


def _canonical(o):
    """JSON-ready form with floats fixed to 12 decimal places.

    Run summaries come from float sums whose last bits depend on the
    interpreter (built-in sum() of floats is compensated from 3.12 on), so
    floats are rounded before hashing; 12 places keeps every metric but drops
    the sub-1e-12 rounding noise.
    """

    if isinstance(o, enum.Enum):
        return _canonical(o.value)
    if dataclasses.is_dataclass(o) and not isinstance(o, type):
        return {f.name: _canonical(getattr(o, f.name)) for f in dataclasses.fields(o)}
    if isinstance(o, bool) or o is None or isinstance(o, (int, str)):
        return o
    if isinstance(o, float):
        return format(round(o, 12) + 0.0, ".12f")
    if isinstance(o, dict):
        return {str(k): _canonical(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [_canonical(v) for v in o]
    raise TypeError(type(o).__name__)


def h(o):
    text = json.dumps(_canonical(o), sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(text.encode()).hexdigest()


for name, mk in [
    ("t01", lambda s: t01_oee.T01OEERunner(s, population_size=16, generations=6)),
    (
        "t02",
        lambda s: (
            t02_mls_price.T02MLSPriceRunner(s, num_demes=3, deme_capacity=6, generations=6)
            if hasattr(t02_mls_price, "T02MLSPriceRunner")
            else None
        ),
    ),
    (
        "t03",
        lambda s: (
            t03_mutualism.T03MutualismRunner(s, population_size=16, generations=6)
            if hasattr(t03_mutualism, "T03MutualismRunner")
            else None
        ),
    ),
    (
        "t04",
        lambda s: [c for n, c in vars(t04_contingency).items() if n.startswith("T04") and n.endswith("Runner")][0](
            s, population_size=16, generations=8, replay_branches=2, replay_generations=3
        ),
    ),
    (
        "t05",
        lambda s: (
            t05_red_queen.T05RedQueenRunner(s, population_size=16, generations=6)
            if hasattr(t05_red_queen, "T05RedQueenRunner")
            else None
        ),
    ),
]:
    for s in (0, 7, -3, 2**64 - 1):
        try:
            r = mk(s)
            recs = []
            summ = r.run(on_generation=lambda m: recs.append(m))
            out[f"{name}.{s}"] = h((summ, recs))
        except Exception as ex:
            out[f"{name}.{s}"] = "ERR " + type(ex).__name__ + ": " + str(ex)[:80]
print(json.dumps(out, indent=1, sort_keys=True))
