"""CLI: python -m codontrace.claimgate audit bundle.json"""

from __future__ import annotations

import json
from pathlib import Path

from codontrace.claimgate.__main__ import main

FIXTURE = Path(__file__).resolve().parent / "fixtures" / "claimgate" / "level0_software_only.json"


def test_cli_audit_prints_json_report(capsys) -> None:
    assert main(["audit", str(FIXTURE)]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["achieved_level"] == 0
    assert payload["public_name"] == "software_capability"
    assert len(payload["digest"]) == 64


def test_cli_missing_file_is_an_error(capsys) -> None:
    assert main(["audit", "does-not-exist.json"]) == 2
    assert "claimgate-audit-error" in capsys.readouterr().err
