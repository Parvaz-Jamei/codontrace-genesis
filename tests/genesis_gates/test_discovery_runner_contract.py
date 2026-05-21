from __future__ import annotations

from codontrace.genesis.discovery_runner import (
    D0BaselineRunner,
    DiscoveryDetector,
    MultiSeedProtocol,
)


def test_discovery_runner_contract_never_proves_without_d0() -> None:
    detector = DiscoveryDetector(novelty_threshold=0.2)
    result = detector.evaluate({"novelty_score": 1.0}, observations=(1, 2, 3))
    assert result.status == "review_needed"
    assert "not_proof" in result.reason
    d0 = D0BaselineRunner.from_config({"seed": 1})
    result_with_d0 = detector.evaluate(
        {"novelty_score": 1.0}, d0_digest=d0.digest(), observations=(1, 2, 3)
    )
    assert result_with_d0.status == "review_needed"
    assert MultiSeedProtocol((1, 2, 3)).digest() == MultiSeedProtocol((1, 2, 3)).digest()
