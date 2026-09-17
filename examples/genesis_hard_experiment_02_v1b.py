"""Print locked HE02 v1b contrasts from committed research rows."""

from __future__ import annotations

import json

from codontrace.genesis.he02_contrasts import analyze_committed_research


def main() -> None:
    report = analyze_committed_research()
    json.dumps(report, indent=2, sort_keys=True)


if __name__ == "__main__":
    main()
