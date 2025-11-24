import random
import math

class APKiller:
    def __init__(self, sim):
        self.sim = sim
        self.active = False
        self.floor = 1

        # position on floor (local coords)
        self.x = 0
        self.y = 0

        # movement
        self.vx = 0
        self.vy = 0
        self.speed = 4  # fast movement

    def deploy(self):
        self.active = True
        self.vx = 0
        self.vy = 0

    def withdraw(self):
        self.active = False

    def set_floor(self, level):
        self.floor = level

    def get_nearest_ap_id(self, aps):
        best_id = None
        best_dist = float("inf")

        # compute in LOCAL coords (for frontend line)
        for ap in aps:
            if ap["floor"] != self.floor:
                continue

            d = math.dist((self.x, self.y), (ap["x"], ap["y"]))
            if d < best_dist:
                best_dist = d
                best_id = ap["id"]

        return best_id

    def reposition_center(self, aps, rooms, floor):
        """Center inside corridor on selected floor."""
        corridor = None
        for r in rooms:
            if r["name"].lower().startswith("corridor"):
                corridor = r
                break

        if corridor:
            self.x = corridor["x"] + corridor["width"] / 2
            self.y = corridor["y"] + corridor["height"] / 2

    def update(self, aps, rooms):
        if not self.active:
            return

        # movement
        self.x += self.vx * self.speed
        self.y += self.vy * self.speed

        # full floor bounding box (NOT corridor)
        if rooms:
            min_x = min(r["x"] for r in rooms)
            max_x = max(r["x"] + r["width"] for r in rooms)
            min_y = min(r["y"] for r in rooms)
            max_y = max(r["y"] + r["height"] for r in rooms)

            self.x = max(min_x + 8, min(max_x - 8, self.x))
            self.y = max(min_y + 8, min(max_y - 8, self.y))

        # ===================================================
        # 🔥 CORRECT AP IMPACT LOGIC (GLOBAL DISTANCE MATCH)
        # ===================================================
        killer_gx, killer_gy = self.sim.to_global(self.floor, self.x, self.y)

        for ap in aps:
            if ap["floor"] != self.floor:
                continue

            ap_gx, ap_gy = self.sim.to_global(ap["floor"], ap["x"], ap["y"])

            # now both are in GLOBAL space → correct distance
            dist = math.dist((killer_gx, killer_gy), (ap_gx, ap_gy))

            # 180px impact radius
            if dist < 180:
                ap["load"] = min(100, ap["load"] + 10)
