# Phase 3 host selection

`red_queen_proved` is false. The no-parasite birth gap was not retuned. Seeds 9881, 9882, and 9883 were not reused from an earlier phase. `runs/rq-mechanism-v2/phase3-frequency/` was read and not rewritten.

## Swaps

One absent generation, seed 9883, parasite roster read from `runs/rq-mechanism-v2/phase3-frequency/by_seed/seed9501/common_a/archive.jsonl`. Output: `runs/rq-reciprocal-validity/phase3-selection/swaps.json`.

Every swap's four births have parent ids `host-A-001`, `host-A-002`, `host-A-003`, `host-A-004`. Id-letter counts stay 4 and 0. Deaths stay 0 and 0. Contacts stay 0.

| Swap | Parent window of the four births |
| --- | --- |
| baseline | `000000` |
| processing_order | `000000` |
| ids | `111111` |
| position | `000000` |
| food_access | `000000` |
| genome_background | `111111` |

`which_swap_moves_id_births.moved` is `[]`. Reversing the organism tuple, exchanging patch coordinates, and putting class B on the even patch indexes do not change the parent ids or the parent window.

The id swap keeps the parent ids and moves the parent window to `111111`, because those names are worn by the seats that had window `111111`. The genome swap keeps the parent ids and moves the parent window to `111111`, because those same names were given window `111111`. The births follow the sorted name. They do not follow the patch, and they do not follow the window the name had at install unless that window is still on that name.

The one-generation pressured arm on the same seed, coevolve passage, has contacts 60, births 4 and 0, deaths 0 and 0. `direction_changed_by_parasites` is false. Contact happened. The birth sign and the death sign did not change.

## Eight generations

Absent seed 9881, passage `absent`. Pressured seed 9882, passage `coevolve`. Both failed null. `runs/rq-reciprocal-validity/phase3-selection/series.json`.

Generation 1, both arms: birth sign 1, death sign null. Absent contacts 0. Pressured contacts 64. Founder-lineage fitness A 2.0 and B 0.0 on both. Current-window fitness is `000000` 2.0 and `111111` 0.0 on both. Pressure did not change generation-1 direction.

Generations where the direction object differs: 5, 6, and 7.

Generation 5 absent: birth sign 1, death sign 1, founder A 1.8823529411764706, B 0.0. Generation 5 pressured: both signs null, founder fitness null because there were no births. That null is not a zero.

Generation 6 absent: both signs null. Generation 6 pressured: birth sign null, death sign 1.

Generation 7 absent: both signs 1, founder A 1.8823529411764706, B 0.0. Generation 7 pressured: birth sign 1, death sign null, founder A 1.9375, B 0.0. Current-window fitness on that pressured generation is not the founder vector: window `111000` is 31.0 and window `000001` is 10.333333333333334, and `000000` is 0.0.

Generation 8, both arms: birth sign 1, death sign -1. Founder B is 0.0 on both. The current-window vector is again not that founder vector.

Founder-lineage fitness was not replaced by current-window fitness. Parasite pressure did not reverse founder class B from 0 to a higher founder fitness in any generation that had births. It did change whether a birth sign or a death sign was a tie at generations 5, 6, and 7. That is the recorded change in direction. It is not a Red Queen result.
