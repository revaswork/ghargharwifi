import math
from algorithms.priority_queue import UserPriorityQueue
from algorithms.cost_function import dynamic_capacity


class GreedyRedistributor:
    """
    Greedy load balancer - FULLY STABILIZED WITH DYNAMIC CAPACITY
    
    ✅ Floor-safe (no cross-floor moves)
    ✅ Correct load recalculation
    ✅ RSSI-based eviction order
    ✅ Coverage-aware
    ✅ Uses dynamic_capacity(ap) everywhere
    """

    def __init__(self, aps, users):
        self.aps = aps
        self.users = users

    # ============================================================
    # Overloaded AP detection (dynamic capacity)
    # ============================================================
    def get_overloaded_aps(self):
        overloaded = []
        for ap in self.aps:
            cap = dynamic_capacity(ap)
            if ap["load"] > cap:
                overloaded.append(ap)
        return overloaded

    # ============================================================
    # Build Priority Queue of weakest users on this AP
    # ============================================================
    def build_priority_queue(self, ap):
        pq = UserPriorityQueue()
        for user in self.users:
            if user.get("assigned_ap") == ap["id"]:
                priority = abs(user.get("RSSI", -95))
                pq.push(priority, user)
        return pq

    # ============================================================
    # Find alternative AP (same floor, capacity left, strong RSSI)
    # ============================================================
    def find_alternative_ap(self, user):
        user_floor = user.get("floor")
        best_ap = None
        best_rssi = -200

        for ap in self.aps:
            # Same floor only
            if ap["floor"] != user_floor:
                continue

            # Skip current AP
            if ap["id"] == user.get("assigned_ap"):
                continue

            # AP must have dynamic available capacity
            if ap["load"] >= dynamic_capacity(ap):
                continue

            # Check coverage
            dist = math.dist((user["x"], user["y"]), (ap["x"], ap["y"]))
            if dist > ap.get("coverage_radius", 200):
                continue

            if dist <= 0:
                continue

            # Estimate RSSI
            rssi = -30 - 20 * math.log10(dist)

            # Pick strongest AP
            if rssi > best_rssi:
                best_rssi = rssi
                best_ap = ap

        return best_ap

    # ============================================================
    # Main Redistribution Routine
    # ============================================================
    def redistribute(self):
        # 1. Reset loads & rebuild connected_clients cleanly
        for ap in self.aps:
            ap["load"] = 0
            ap["connected_clients"] = []

        for user in self.users:
            aid = user.get("assigned_ap")
            if aid:
                for ap in self.aps:
                    if ap["id"] == aid:
                        ap["load"] += user.get("airtime_usage", 1)
                        ap["connected_clients"].append(user["id"])
                        break

        # 2. Find overloaded APs using dynamic capacity
        overloaded_aps = self.get_overloaded_aps()

        # 3. Reassign weakest users first
        for ap in overloaded_aps:
            pq = self.build_priority_queue(ap)
            cap = dynamic_capacity(ap)

            while len(pq) > 0 and ap["load"] > cap:
                user = pq.pop()
                alternative_ap = self.find_alternative_ap(user)

                if alternative_ap:
                    old_ap = user["assigned_ap"]
                    load_val = user.get("airtime_usage", 1)

                    # Apply move
                    user["assigned_ap"] = alternative_ap["id"]
                    user["connected_ap"] = alternative_ap["id"]

                    ap["load"] -= load_val
                    alternative_ap["load"] += load_val

                    # Update lists
                    if user["id"] in ap["connected_clients"]:
                        ap["connected_clients"].remove(user["id"])

                    alternative_ap["connected_clients"].append(user["id"])

                    print(f"♻️ Greedy moved {user['id']}   {old_ap} → {alternative_ap['id']}")

                else:
                    break   # no AP available → stop
