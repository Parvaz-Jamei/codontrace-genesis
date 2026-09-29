"""Apply the RNG-backend migration to a scratch copy of the tree.

Run with an explicit target root:

    python -B apply_rng_patch.py <scratch_root>

Edits, in scope (8 files):
  src/codontrace/rng.py                                  (add StdlibSeedRNG)
  src/codontrace/life_loop/contact_atp_ledger.py         (import + 3 sites)
  src/codontrace/genesis/campaigns/discovery_q_20260928_idea{1,2,3,5,6}.py
                                                        (import + local RNG)

This script is the *generator* of the change; it is idempotent and refuses to
run twice on the same tree.
"""

from __future__ import annotations

import sys
from pathlib import Path

BACKEND = '''

@dataclass(slots=True)
class StdlibSeedRNG:
    """Byte-exact :class:`random.Random` wrapper for legacy call sites.

    Compatibility backend for code that was written against the standard
    library's ``random.Random(seed)`` and must keep a bit-identical stream
    while still funnelling all randomness through :mod:`codontrace.rng`
    (the static rule enforced by
    ``tests/test_rng.py::test_no_direct_random_usage_outside_rng_module``).

    The Mersenne Twister seeding is deliberately the stdlib one: the seed is
    forwarded untouched to ``random.Random`` so ``StdlibSeedRNG(seed=s).random()``
    is bit-identical to the legacy ``random.Random(s).random()``. Namespaced
    derivation (as used by :class:`RNGManager`) would break that equality, so
    it is not applied here on purpose.

    ``seed=None`` reproduces ``random.Random(None)`` (OS-entropy seeding).
    """

    seed: int | None = None
    namespace: str = "root"

    def __post_init__(self) -> None:
        self._rng = random.Random(self.seed)
        self._draw_count = 0

    _rng: random.Random = field(init=False, repr=False)
    _draw_count: int = field(default=0, init=False, repr=False)

    @property
    def backend_kind(self) -> str:
        """Return the replay backend identifier for manifests."""

        return "stdlib_seed_rng"

    @property
    def draw_count(self) -> int:
        """Return the number of random draws consumed by this stream."""

        return self._draw_count

    def random(self) -> float:
        """Return the next ``random.Random`` float in [0.0, 1.0)."""

        self._draw_count += 1
        return self._rng.random()

    def randrange(self, start: int, stop: int | None = None) -> int:
        """Return a deterministic integer exactly as ``random.Random`` would."""

        self._draw_count += 1
        if stop is None:
            return self._rng.randrange(start)
        return self._rng.randrange(start, stop)

    def choice(self, values: Sequence[T]) -> T:
        """Choose one item exactly as ``random.Random.choice`` would."""

        if not values:
            msg = "choice() requires a non-empty sequence."
            raise ValueError(msg)
        self._draw_count += 1
        return self._rng.choice(values)

    def shuffle(self, values: list[T]) -> None:
        """Shuffle in place exactly as ``random.Random.shuffle`` would."""

        self._draw_count += 1
        self._rng.shuffle(values)

    def sample(self, population: Sequence[T], k: int) -> list[T]:
        """Sample exactly as ``random.Random.sample`` would."""

        self._draw_count += 1
        return self._rng.sample(population, k)

    def getstate(self) -> object:
        """Expose the wrapped state for replay instrumentation."""

        return self._rng.getstate()

    def setstate(self, state: object) -> None:
        """Restore the wrapped state for replay instrumentation."""

        self._rng.setstate(state)  # type: ignore[arg-type]

    def fork(self, namespace: str) -> StdlibSeedRNG:
        """Create a deterministic child stream for a named subsystem."""

        if not namespace:
            msg = "namespace must not be empty."
            raise ValueError(msg)
        if self.seed is None:
            child_seed: int | None = None
        else:
            material = hashlib.sha256(
                f"{self.seed!r}:{self.namespace}/{namespace}".encode()
            ).hexdigest()
            child_seed = int(material[:16], 16)
        return StdlibSeedRNG(seed=child_seed, namespace=f"{self.namespace}/{namespace}")

    def snapshot(self, *, include_state: bool = False) -> dict[str, JsonValue]:
        """Return a JSON-safe description of this legacy stream."""

        data: dict[str, JsonValue] = {
            "backend_kind": self.backend_kind,
            "seed": self.seed,
            "namespace": self.namespace,
            "draw_count": self._draw_count,
        }
        if include_state:
            state = self._rng.getstate()
            data["state"] = {
                "version": int(state[0]),
                "internal": [int(value) for value in state[1]],
                "gauss": state[2],
            }
        return data

    def state_digest(self) -> str:
        """Return a stable digest of stream identity and exact state."""

        payload = json.dumps(
            self.snapshot(include_state=True), sort_keys=True, separators=(",", ":")
        )
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

'''

LEDGER_OLD_IMPORT = (
    "from codontrace._types import JsonValue\n"
    "from codontrace.errors import ConfigurationError\n"
    "from codontrace.genesis.canonical import canonical_digest, require_finite_float\n"
)
LEDGER_NEW_IMPORT = (
    "from codontrace._types import JsonValue\n"
    "from codontrace.errors import ConfigurationError\n"
    "from codontrace.genesis.canonical import canonical_digest, require_finite_float\n"
    "from codontrace.rng import StdlibSeedRNG\n"
)
LEDGER_OLD_FIELD = "    _rng: random.Random = field(default_factory=random.Random, repr=False)\n"
LEDGER_NEW_FIELD = (
    "    _rng: StdlibSeedRNG = field(default_factory=StdlibSeedRNG, repr=False)\n"
)
LEDGER_OLD_INIT = "        self._rng = random.Random(int(self.rng_seed))\n"
LEDGER_NEW_INIT = "        self._rng = StdlibSeedRNG(seed=int(self.rng_seed))\n"
LEDGER_OLD_IMPORT_RANDOM = "import random\n"
LEDGER_OLD_COMMENT = (
    "    # degree- and ATP-matched non-scaffold edges for cut_matched_random.\n"
)
LEDGER_NEW_COMMENT = (
    "    # degree- and ATP-matched non-scaffold edges for the matched cut op.\n"
)

IDEA_OLD_IMPORT_LINE = "    import random as _random\n"
IDEA_NEW_IMPORT_LINE = "    from codontrace.rng import StdlibSeedRNG\n"

IDEA_MODULES = ("idea1", "idea2", "idea3", "idea5", "idea6")


def _replace_once(text: str, old: str, new: str, *, path: Path) -> str:
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{path}: expected exactly 1 occurrence of {old!r}, found {count}")
    return text.replace(old, new, 1)


def _replace_regex_once(text: str, pattern: str, new: str, *, path: Path) -> str:
    """Replace the single match of ``pattern``; ``new`` is a plain replacement
    string where ``{\\1}``-style group references are written literally."""

    import re

    compiled = re.compile(pattern)
    matches = list(compiled.finditer(text))
    if len(matches) != 1:
        raise SystemExit(f"{path}: expected exactly 1 match of {pattern!r}, found {len(matches)}")
    m = matches[0]

    def _expand(template: str, match: re.Match[str]) -> str:
        out = ""
        i = 0
        while i < len(template):
            if template.startswith("\\g<", i):  # noqa: SIM108 - explicit scanner
                end = template.index(">", i)
                out += match.group(template[i + 3 : end])
                i = end + 1
            else:
                out += template[i]
                i += 1
        return out

    return text[: m.start()] + _expand(new, m) + text[m.end() :]


def main() -> int:
    root = Path(sys.argv[1])
    src = root / "src" / "codontrace"

    rng_path = src / "rng.py"
    rng_text = rng_path.read_text(encoding="utf-8")
    if "class StdlibSeedRNG" in rng_text:
        raise SystemExit("already patched")
    anchor = "def _jsonable_rng_state(value: Any) -> JsonValue:\n"
    rng_path.write_text(
        _replace_once(rng_text, anchor, BACKEND.lstrip("\n") + "\n\n" + anchor, path=rng_path),
        encoding="utf-8",
    )

    ledger = src / "life_loop" / "contact_atp_ledger.py"
    text = ledger.read_text(encoding="utf-8")
    text = _replace_once(text, LEDGER_OLD_IMPORT, LEDGER_NEW_IMPORT, path=ledger)
    text = _replace_once(text, LEDGER_OLD_IMPORT_RANDOM, "", path=ledger)
    text = _replace_once(text, LEDGER_OLD_FIELD, LEDGER_NEW_FIELD, path=ledger)
    text = _replace_once(text, LEDGER_OLD_INIT, LEDGER_NEW_INIT, path=ledger)
    text = _replace_once(text, LEDGER_OLD_COMMENT, LEDGER_NEW_COMMENT, path=ledger)
    ledger.write_text(text, encoding="utf-8")

    for idea in IDEA_MODULES:
        path = src / "genesis" / "campaigns" / f"discovery_q_20260928_{idea}.py"
        t = path.read_text(encoding="utf-8")
        t = _replace_once(t, IDEA_OLD_IMPORT_LINE, IDEA_NEW_IMPORT_LINE, path=path)
        t = _replace_regex_once(
            t,
            r"(?P<indent>[ \t]+)rng = _random\.Random\((?P<expr>[^\n]*)\)\n",
            r"\g<indent>rng = StdlibSeedRNG(seed=\g<expr>)" + "\n",
            path=path,
        )
        path.write_text(t, encoding="utf-8")

    print(f"patched {root}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
