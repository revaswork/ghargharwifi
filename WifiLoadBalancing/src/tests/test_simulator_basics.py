import sys, os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from simulation.simulator import WifiSimulator
import math

sim = WifiSimulator()

print("=== TEST 1: MOVEMENT ===")
u0 = sim.clients[0]
pos_before = (u0["x"], u0["y"])

sim.move_users()
pos_after = (u0["x"], u0["y"])

print("Before:", pos_before)
print("After:", pos_after)
print("Position changed?", pos_before != pos_after)

# -----------------------------------------------------

print("\n=== TEST 2: RSSI UPDATE ===")
sim.update_rssi()
u0_rssi = sim.clients[0]["RSSI"]
print("RSSI value:", u0_rssi)
print("Nearest AP:", sim.clients[0]["nearest_ap"])

print("RSSI valid?", -100 <= u0_rssi <= -30)

# -----------------------------------------------------

print("\n=== TEST 3: AP LOAD ===")
sim.update_ap_load()

for ap in sim.aps[:5]:     # first 5 APs
    print(ap["id"], "load:", ap["load"])

print("Test complete")
