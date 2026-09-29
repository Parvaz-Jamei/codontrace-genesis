from workers import Cfg, confirm_task

result = confirm_task((Cfg(20260927, 0.4, 40), 1000, ("10:0>1",), 2))
print("fitness", result["fitness"])
print("bits", str(result["bits"])[:40])
print("present", len(result["present"]))
print("counterfactual", result["counterfactual"])
print("order_effects", [round(v, 4) for v in result["order_effects"]])
print("local_effects", [round(v, 4) for v in result["local_effects"]])
print("OK")
