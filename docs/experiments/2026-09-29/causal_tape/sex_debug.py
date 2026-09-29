import sex_arms as S

for cost_ratio, tag in ((1.0, "costless"), (2.0, "costly")):
    row = S.run_arm(6000, mode="sex", parasite=False, cost_ratio=cost_ratio, generations=300)
    print(
        tag,
        "final=%.4f" % row["sexual_final"],
        "auc=%.4f" % row["sexual_auc"],
        "extinct_at=", row["extinction_generation"],
        "rho=%.3f" % row["rho"],
        flush=True,
    )

for gens in (10, 20, 40, 80, 160):
    row = S.run_arm(6000, mode="sex", parasite=False, cost_ratio=1.0, generations=gens)
    print(f"costless {gens:>4} gens -> final={row['sexual_final']:.4f} extinct_at={row['extinction_generation']}", flush=True)
