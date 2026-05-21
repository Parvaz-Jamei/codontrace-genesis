import subprocess
import sys
from pathlib import Path

import pytest

from codontrace.errors import ConfigurationError
from codontrace.genesis import RELEASE_LABEL, canonical_digest
from codontrace.genesis.final_release_manifest import FinalClaimManifest, ReleaseEvidencePack


def D(name: str) -> str:
    return canonical_digest({"release_pack": name})


def test_release_evidence_pack_rejects_not_run_replay_index_and_fake_ablation_digest():
    claim = FinalClaimManifest("c", "claim", "level", False, ("e",), (), (), D("r"), D("g"), ())
    with pytest.raises(ConfigurationError):
        ReleaseEvidencePack(RELEASE_LABEL, (claim,), "not_run:index", "fake")


def test_release_evidence_pack_rejects_unvalidated_allowed_claim_manifest():
    claim = FinalClaimManifest("c", "claim", "level", True, ("e",), (), (), D("r"), D("g"), (D("cfg"),))
    assert not claim.allowed
    pack = ReleaseEvidencePack(RELEASE_LABEL, (claim,), D("index"), D("ablation"))
    assert pack.status == "negative_result_pack"
    assert "no_final_claim_allowed" in pack.validation_reasons


def test_release_evidence_pack_with_all_denied_claims_is_negative_result_pack():
    claim = FinalClaimManifest("c", "claim", "level", False, ("e",), (), (), D("r"), D("g"), ())
    pack = ReleaseEvidencePack(RELEASE_LABEL, (claim,), D("index"), D("ablation"))
    assert pack.status == "negative_result_pack"
    assert not pack.validation_passed
    assert pack.validation_result_digest


def test_phase3_final_release_digest_rejects_nan_payload():
    from codontrace.genesis.canonical import canonical_digest

    with pytest.raises(ConfigurationError):
        canonical_digest({"bad": float("nan")})


def test_phase3_campaign_digest_cross_process_stable():
    code = "from codontrace.genesis import canonical_digest; print(canonical_digest({'x': [1,2,3]}))"
    repo_root = Path(__file__).resolve().parents[2]
    env = dict(__import__("os").environ)
    env["PYTHONPATH"] = str(repo_root / "src")
    a = subprocess.check_output([sys.executable, "-c", code], text=True, env=env).strip()
    b = subprocess.check_output([sys.executable, "-c", code], text=True, env=env).strip()
    assert a == b
