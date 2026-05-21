import re
from pathlib import Path

POSITIVE_PATHS = ("examples", "docs")
FORBIDDEN = re.compile(r"claim_gate_decision_digest.*fake|replay_digest.*fake|not_run:.*claim|not_run:.*replay")


def test_examples_do_not_use_fake_evidence_in_positive_claim_paths():
    root = Path(__file__).resolve().parents[2]
    offenders = []
    for folder in POSITIVE_PATHS:
        for path in (root / folder).rglob("*"):
            if path.is_file() and path.suffix in {".py", ".md", ".txt", ".json", ".html"}:
                text = path.read_text(encoding="utf-8", errors="ignore")
                if FORBIDDEN.search(text):
                    offenders.append(str(path.relative_to(root)))
    assert not offenders, offenders


def test_docs_do_not_present_fake_digest_as_valid_final_evidence():
    root = Path(__file__).resolve().parents[2]
    offenders = []
    for path in (root / "docs").rglob("*"):
        if path.is_file() and path.suffix in {".md", ".txt", ".html"}:
            text = path.read_text(encoding="utf-8", errors="ignore")
            if FORBIDDEN.search(text):
                offenders.append(str(path.relative_to(root)))
    assert not offenders, offenders
