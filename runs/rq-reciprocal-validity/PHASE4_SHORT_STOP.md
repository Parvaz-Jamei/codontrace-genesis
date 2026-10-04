# Short run stop

Seed 9904. Four generations were requested. Coevolve finished four generations. Adaptation-cut generation 1 was written. The next hold raised `intervention energy does not balance`.

Cause. `hold_founder_genotypes` summed every line already on `intervention_ledger`, including earlier calls. The second call's energy account was not the energy of that call. Seed 9904 was not rerun. Its archive stays in `runs/rq-reciprocal-validity/phase4-short/`.

`red_queen_proved` is false. This stop is not a Red Queen result.
