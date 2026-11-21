"""Task B standalone checks (numpy only, 1 core, private seeds 20261121+; no engine, no log_w of engine data).
A. Verify coder's recruit-ATP recurrence and g0 birth counts from locked constants.
B. Discrete WF model: expected w and persistence, current (b<=1, food cap 8) vs proposed (brood b, re-endowed recruits).
"""
import json, math
import numpy as np

# A. constants (codon.py:252-261, closed_loop_hp_arm01.py:734-746, selfing_hold.py:75-80)
EAT, COPY, BASAL, PCOST, FRAC, BOLUS, PATCHES, BIRTH = 0.8, 8.0, 0.05, 1.0, 0.25, 20.0, 8, 48.0
def endow(A, F, eat_first=True):
    Ac = A - BASAL - (EAT if eat_first else 0) + (F if eat_first else 0) - BASAL - COPY
    if not eat_first: Ac = A - BASAL - COPY
    return FRAC * (Ac - PCOST) if Ac - PCOST > 0 else 0.0
out = {}
out["E_max_fed_g0"] = endow(BIRTH, BOLUS)            # 14.525
out["E_unfed_g0"] = endow(BIRTH, 0.0)                # 9.525
out["copy_first_threshold"] = BASAL + COPY + PCOST    # 9.05
out["eat_first_unfed_threshold"] = 2*BASAL + EAT + COPY + PCOST  # 9.9
seq = [out["E_max_fed_g0"]]
for _ in range(6): seq.append(endow(seq[-1], BOLUS))
out["census_recurrence"] = [round(x, 4) for x in seq]
out["fixed_point"] = round(FRAC * (BOLUS - 2*BASAL - EAT - COPY - PCOST) / (1 - FRAC), 4)
out["steady_births_cap_food"] = PATCHES
out["energy_births_cap_divisible"] = round(PATCHES * BOLUS / out["eat_first_unfed_threshold"], 2)
for N in (20, 200):
    asex = N // 5
    out[f"g0_births_expected_N{N}_m0.5"] = asex + (N - asex) * 0.5
    out[f"g0_births_expected_N{N}_m0.25"] = asex + (N - asex) * 0.75

# B. discrete WF with fixed brood b (like-for-like), males sire-only, kill survival S, thin to N
def run(N, m, b, S_fn, G, seed, x0=0.2, food_cap=None):
    rng = np.random.default_rng(seed)
    a = int(round(x0 * N)); s = N - a
    traj = []
    for g in range(G):
        S = S_fn(g)
        a_s = rng.binomial(a, S); s_s = rng.binomial(s, S)
        mothers_s = rng.binomial(s_s, 1 - m) if s_s >= 2 else 0  # need a mate (global pairing)
        if s_s and mothers_s == s_s: mothers_s = s_s - 1 if s_s > 1 else 0  # at least one sire... hermaphrodites can sire; keep simple
        births_a, births_s = b * a_s, b * mothers_s
        if food_cap is not None:  # only fed mothers reproduce
            tot = births_a + births_s
            if tot > food_cap:
                k = rng.hypergeometric(births_a, births_s, food_cap) if tot else 0
                births_a, births_s = k, food_cap - k
        tot = births_a + births_s
        if tot == 0: traj.append((0, 0)); break
        keep = min(N, tot)
        a = rng.hypergeometric(births_a, births_s, keep) if births_s else keep
        s = keep - a
        traj.append((int(a), int(s)))
    return traj
res = {}
for m in (0.5, 0.25):
    for b, label, cap in ((1, "current_b1_tokens_only", None), (1, "current_b1_plus_foodcap8", 8), (6, "proposed_b6", None)):
        for N in (50, 200):
            surv_one = []
            for r in range(200):
                t = run(N, m, b, lambda g: 1.0, 1, 20261121 + r, food_cap=cap)
                a, s = t[-1]
                if a + s and a and s:
                    surv_one.append(math.log((a / s) / (0.2 / 0.8)))
            final = [run(N, m, b, lambda g: 1.0, 20, 20262121 + r, food_cap=cap)[-1] for r in range(200)]
            res[f"m{m}_{label}_N{N}"] = dict(mean_log_w_gen1=round(float(np.mean(surv_one)), 3) if surv_one else None,
                                            theory_log_w=round(-math.log(1 - m), 3),
                                            median_census_g20=float(np.median([a + s for a, s in final])), median_sexual_g20=float(np.median([s for a, s in final])))
# persistence of pure outcross under full-match high kill: survival exp(-c), c=1
for m in (0.5, 0.25):
    for b in (1, 2, 6):
        F = b * (1 - m)
        res[f"outcross_m{m}_b{b}"] = dict(F_adult=F, persists_full_match_high=F * math.exp(-1) >= 1,
                                          window=[round(-math.log(1 - m), 3), round(math.log(F), 3) if F > 0 else None])
out["sim"] = res
out["b_min_for_c1"] = {m: round(math.e / (1 - m), 3) for m in (0.5, 0.25)}
print(json.dumps(out, indent=1))
