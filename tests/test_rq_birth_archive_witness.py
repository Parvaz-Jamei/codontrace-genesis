"""Scientific parentage evidence must survive serialization without changing evolution."""
import json
from pathlib import Path

from codontrace.genesis.population import LineageRecord
from codontrace.genesis.rq_mechanism_v2_phase5 import birth_archive_witness, run_phase5_history


def record(second='b'):
    return LineageRecord(organism_id='c',parent_id='a',second_parent_id=second,
        generation=1,genome_digest='birth-genome',mutation_count=2,birth_tick=1,
        death_tick=None,reproduction_event_id='repro-1',
        recombination_start_index=2,recombination_end_index=8,recombination_digest='segment')


def test_both_parents_and_birth_genetics_survive_archive():
    witness=birth_archive_witness(record(),{'a':'000000','b':'111111'},{'c':'001111'})
    assert witness['parent_ids']==['a','b']
    assert witness['parent_windows']=={'a':'000000','b':'111111'}
    assert witness['child_window_pre_contact']=='001111'
    assert witness['lineage_record']['mutation_count']==2
    assert witness['lineage_record']['recombination_start_index']==2
    assert witness['lineage_record']['recombination_end_index']==8
    assert witness['parent_windows_complete'] is True


def test_missing_genotype_is_not_an_invented_parent_contribution():
    witness=birth_archive_witness(record(),{'a':'000000'},{})
    assert witness['second_parent_id']=='b'
    assert witness['parent_windows']['b'] is None
    assert witness['parent_windows_complete'] is False
    assert witness['parent_window_sources']['b']=='unmeasured'


def test_asexual_birth_has_one_parent():
    witness=birth_archive_witness(record(None),{'a':'000000'},{'c':'000000'})
    assert witness['parent_ids']==['a']
    assert witness['second_parent_id'] is None


def test_real_history_keeps_new_witness_and_resume_equivalence(tmp_path: Path):
    root=tmp_path/'evidence'
    outcome=run_phase5_history(10501,str(root),3,arms=('coevolve',),compare_one_shot=True)
    assert outcome['failed'] is None
    rows=[json.loads(line) for line in (root/'by_seed/seed10501/archive.jsonl').read_text().splitlines()]
    births=[b for row in rows for b in row['host_births']]
    assert births
    assert all(b['evidence_schema']=='genesis-birth-witness/2' for b in births)
    sexual=[b for b in births if b['second_parent_id'] is not None]
    assert sexual
    assert all(len(b['parent_ids'])==2 for b in sexual)
    assert all(b['lineage_record']['second_parent_id']==b['second_parent_id'] for b in sexual)


def test_completion_rejects_lost_persisted_generation(tmp_path, monkeypatch):
    import codontrace.genesis.rq_mechanism_v2_phase5 as module
    root=tmp_path/'lost-row'
    original=module._first_diff
    truncated=False
    def remove_row(left,right,*args,**kwargs):
        nonlocal truncated
        result=original(left,right,*args,**kwargs)
        if not truncated:
            archive=root/'by_seed/seed10502/archive.jsonl'
            lines=archive.read_text().splitlines()
            archive.write_text('\n'.join(lines[:-1])+'\n')
            truncated=True
        return result
    monkeypatch.setattr(module,'_first_diff',remove_row)
    outcome=module.run_phase5_history(10502,str(root),2,arms=('coevolve',),compare_one_shot=True)
    assert outcome['failed']=='archive-integrity:incomplete-or-duplicated-generation'
    assert not (root/'by_seed/seed10502/COMPLETE').exists()
    assert (root/'STOP').exists()


def test_duplicate_history_is_not_marked_complete(tmp_path):
    root=tmp_path/'duplicate'
    assert run_phase5_history(10503,str(root),2,arms=('coevolve',),compare_one_shot=False)['failed'] is None
    outcome=run_phase5_history(10503,str(root),2,arms=('coevolve',),compare_one_shot=False)
    assert outcome['failed']=='archive-integrity:incomplete-or-duplicated-generation'
    assert not (root/'by_seed/seed10503/COMPLETE').exists()
