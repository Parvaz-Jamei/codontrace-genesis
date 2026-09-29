import sex_phase as P

print("critical-cost probe, infection_cost=0.4, parasite_mutation=0.005", flush=True)
for turnover in (1, 6, 12):
    row = []
    for cost in (1.0, 1.1, 1.2, 1.25, 1.5):
        r = P.run_phase(9000, turnover=turnover, infection_cost=0.4, cost_ratio=cost, parasite_mutation=0.005)
        row.append(f"c={cost}:{r['sexual_final']:.3f}{'X' if r['extinct'] else ''}")
    print(f"turnover={turnover:<3} " + "  ".join(row), flush=True)
