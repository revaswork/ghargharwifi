# import random
# import json
# from pathlib import Path


# DATA_DIR = Path(__file__).resolve().parents[2] / "data"

# class WifiSimulator:
#     def __init__(self):
#         # load initial aps + users from data/
#         with open(DATA_DIR / "aps.json") as f:
#             self.aps = json.load(f)

#         with open(DATA_DIR / "users.json") as f:
#             self.clients = json.load(f)

#     def step(self):
#         """Update AP loads + move users randomly."""

#         # update AP loads
#         for ap in self.aps:
#             ap["load"] = max(0, min(100, ap["load"] + random.randint(-5, 5)))

#         # move users randomly
#         for user in self.clients:
#             user["x"] = (user["x"] + random.randint(-3, 3)) % 200
#             user["y"] = (user["y"] + random.randint(-3, 3)) % 200

#     def get_state(self):
#         """Return the state object expected by main.py"""
#         return {
#             "aps": self.aps,
#             "clients": self.clients
#        }


import json
import math
import random
from pathlib import Path

# Reva's import for MCMF
from algorithms.mcmf import MCMFEngine
from algorithms.greedy_redistribution import GreedyRedistributor


DATA_DIR = Path(__file__).resolve().parents[2] / "data"


class WifiSimulator:

    # ===========================================================
    # INITIALIZATION
    # ===========================================================
    def __init__(self):

        # Load AP + User data
        with open(DATA_DIR / "aps.json") as f:
            self.aps = json.load(f)

        with open(DATA_DIR / "users.json") as f:
            self.clients = json.load(f)

        # MCMF assignments
        self.assignments = {}      # {user_id : ap_id}

        # Initialize AP load values
        for ap in self.aps:
            if "load" not in ap:
                ap["load"] = random.randint(20, 70)

        # Tick counter for periodic MCMF
        self.tick = 0



    # ===========================================================
    # USER MOVEMENT (Advanced — from Niyati)
    # ===========================================================
    def move_users(self):
        """Advanced user movement: drifting + hotspots + boundary bounce."""

        CAMPUS_WIDTH = 1200
        CAMPUS_HEIGHT = 1200
        BASE_SPEED_MIN = 0.5
        BASE_SPEED_MAX = 1.5
        DIRECTION_CHANGE_PROB = 0.05

        HOTSPOTS = [
            {"x": 200, "y": 300, "radius": 40},
            {"x": 800, "y": 500, "radius": 50},
            {"x": 600, "y": 900, "radius": 60},
        ]

        for user in self.clients:

            # initialize velocity fields
            if "vx" not in user:
                user["vx"] = random.uniform(-1.5, 1.5)
            if "vy" not in user:
                user["vy"] = random.uniform(-1.5, 1.5)

            # 5% chance to change direction randomly
            if random.random() < DIRECTION_CHANGE_PROB:
                angle = random.uniform(0, 2 * math.pi)
                speed = random.uniform(BASE_SPEED_MIN, BASE_SPEED_MAX)
                user["vx"] = math.cos(angle) * speed
                user["vy"] = math.sin(angle) * speed

            # hotspot attraction (2% chance)
            if random.random() < 0.02:
                hs = random.choice(HOTSPOTS)
                dx = hs["x"] - user["x"]
                dy = hs["y"] - user["y"]
                dist = math.sqrt(dx * dx + dy * dy)

                if dist > 0:
                    speed = random.uniform(0.5, 1.2)
                    user["vx"] = (dx / dist) * speed
                    user["vy"] = (dy / dist) * speed

            # update position
            new_x = user["x"] + user["vx"]
            new_y = user["y"] + user["vy"]

            # boundary bounce
            if new_x < 0 or new_x > CAMPUS_WIDTH:
                user["vx"] *= -1
                new_x = max(0, min(CAMPUS_WIDTH, new_x))

            if new_y < 0 or new_y > CAMPUS_HEIGHT:
                user["vy"] *= -1
                new_y = max(0, min(CAMPUS_HEIGHT, new_y))

            user["x"] = new_x
            user["y"] = new_y



    # ===========================================================
    # RSSI UPDATE (simple + MCMF-compatible)
    # ===========================================================
    def calc_rssi(self, distance):
        """Basic log-distance RSSI model."""
        if distance <= 0:
            return -30

        rssi = -30 - 20 * math.log10(distance)
        return max(-95, min(-40, rssi))

    def update_rssi(self):
        """Compute single RSSI and nearest AP."""
        for user in self.clients:
            best_rssi = -95
            best_ap = None

            for ap in self.aps:
                dist = math.dist((user["x"], user["y"]), (ap["x"], ap["y"]))

                # skip if out of range
                if dist > ap["coverage_radius"]:
                    continue

                rssi = self.calc_rssi(dist)
                if rssi > best_rssi:
                    best_rssi = rssi
                    best_ap = ap["id"]

            # store simple values (required for cost_function & MCMF)
            user["RSSI"] = best_rssi
            user["nearest_ap"] = best_ap



    # ===========================================================
    # AP LOAD UPDATE (simple + compatible with Greedy & MCMF)
    # ===========================================================
    def update_ap_load(self):
        """Load = sum of airtime_usage of users nearest to AP."""
        for ap in self.aps:
            ap["load"] = 0

        for user in self.clients:
            if user["nearest_ap"] is None:
                continue

            for ap in self.aps:
                if ap["id"] == user["nearest_ap"]:
                    ap["load"] += user.get("airtime_usage", 1)



    # ===========================================================
    # APPLY MCMF (Reva)
    # ===========================================================
    def apply_mcmf(self):

        # recalc RSSI before running MCMF
        self.update_rssi()

        engine = MCMFEngine(self.clients, self.aps)
        try:
            assignments = engine.run()
        except Exception as e:
            print("MCMF error:", e)
            return

        self.assignments = assignments

        # reset AP loads + connected_users
        for ap in self.aps:
            ap["connected_clients"] = []
            ap["load"] = 0

        # assign users to APs
        for user in self.clients:
            uid = user["id"]
            assigned_ap = assignments.get(uid)
            user["assigned_ap"] = assigned_ap

            if assigned_ap:
                for ap in self.aps:
                    if ap["id"] == assigned_ap:
                        ap["connected_clients"].append(uid)
                        ap["load"] += user.get("airtime_usage", 1)



    # ===========================================================
    # GREEDY REDISTRIBUTION (Meet)
    # ===========================================================
    def apply_greedy(self):
        """Local load balancing after MCMF."""
        gr = GreedyRedistributor(self.aps, self.clients)
        gr.redistribute()



    # ===========================================================
    # MAIN STEP LOOP
    # ===========================================================
    def step(self):

        # 1. movement
        self.move_users()

        # 2. RSSI update
        self.update_rssi()

        # 3. load update
        self.update_ap_load()

        # 4. MCMF every 5 ticks
        if self.tick % 5 == 0:
            self.apply_mcmf()

        # 5. Greedy every tick (later)
        self.apply_greedy()

        # increment tick
        self.tick += 1



    # ===========================================================
    # SEND TO FRONTEND
    # ===========================================================
    def get_state(self):
        return {
            "aps": self.aps,
            "clients": self.clients,
            "assignments": self.assignments
        }
