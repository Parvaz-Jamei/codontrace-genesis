from sex_arms import run_arm

row = run_arm(1, mode="sex", parasite=False, generations=30)
print({k: (round(v, 4) if isinstance(v, float) else v) for k, v in row.items()})
print("OK")
