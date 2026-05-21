from codontrace.genesis import canonical_digest
from codontrace.genesis.phase_b_scientific_maturity import CurriculumEnvironmentRecord


def D(name: str) -> str:
    return canonical_digest({"curriculum": name})


def test_environment_curriculum_record_is_seed_deterministic_and_claim_limited():
    first = CurriculumEnvironmentRecord("env", D("parent"), "terrain_mutation", 7, D("task"), 1.0, 0.5, D("transfer"))
    second = CurriculumEnvironmentRecord("env", D("parent"), "terrain_mutation", 7, D("task"), 1.0, 0.5, D("transfer"))
    assert first.digest() == second.digest()
    assert first.claim_eligible


def test_environment_seed_changes_digest():
    first = CurriculumEnvironmentRecord("env", D("parent"), "terrain_mutation", 7, D("task"), 1.0, 0.5, D("transfer"))
    second = CurriculumEnvironmentRecord("env", D("parent"), "terrain_mutation", 8, D("task"), 1.0, 0.5, D("transfer"))
    assert first.digest() != second.digest()


def test_curriculum_without_transfer_is_claim_negative():
    record = CurriculumEnvironmentRecord("env", D("parent"), "terrain_mutation", 7, D("task"), 1.0, 0.5, "not_run:transfer")
    assert not record.claim_eligible
