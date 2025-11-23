import sys, os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from simulation.simulator import WifiSimulator
from algorithms.greedy_redistribution import GreedyRedistributor


sim = WifiSimulator()

print("=== BEFORE GREEDY ===")

# RESET all AP loads
for ap in sim.aps:
    ap["load"] = 0

# Overload ONLY AP_1
sim.aps[0]["load"] = 483

# Assign ALL users temporarily to AP_1
for user in sim.clients:
    user["assigned_ap"] = sim.aps[0]["id"]
    sim.aps[0]["load"] += user.get("airtime_usage", 1)

print("AP_1 overloaded load:", sim.aps[0]["load"])
print("AP capacities:", [ap["airtime_capacity"] for ap in sim.aps])

# Run greedy
gr = GreedyRedistributor(sim.aps, sim.clients)
gr.redistribute()

print("\n=== AFTER GREEDY ===")
for ap in sim.aps:
    print(ap["id"], "load:", ap["load"])

moved = [u for u in sim.clients if u["assigned_ap"] != sim.aps[0]["id"]]

print("\nUsers moved:", len(moved))
for u in moved[:10]:
    print(u["id"], "->", u["assigned_ap"])
