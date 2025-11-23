import json
from algorithms.mcmf import MCMFEngine
from simulation.simulator import WifiSimulator   # <-- ADD THIS
import math

def load(path):
    with open(path) as f:
        return json.load(f)

# function to recalc RSSI without using full simulator loop
def calc_rssi(x1, y1, x2, y2):
    dist = math.dist((x1, y1), (x2, y2))
    if dist <= 0:
        return -30
    rssi = -30 - 20 * math.log10(dist)
    return max(-95, min(-40, rssi))

if __name__ == "__main__":
    aps = load("../data/aps.json")
    users = load("../data/users.json")

    # ⭐ Recalculate RSSI for ALL users before MCMF ⭐
    for u in users:
        best_ap = None
        best_rssi = -95
        
        for ap in aps:
            rssi = calc_rssi(u["x"], u["y"], ap["x"], ap["y"])
            if rssi > best_rssi:
                best_rssi = rssi
                best_ap = ap["id"]

        u["RSSI"] = best_rssi
        u["nearest_ap"] = best_ap

    # Now MCMF will have REAL distances and RSSI
    engine = MCMFEngine(users, aps)
    assignments = engine.run()

    print("Assigned users:", len(assignments))
    for uid, aid in list(assignments.items())[:20]:
        print(uid, "->", aid)
