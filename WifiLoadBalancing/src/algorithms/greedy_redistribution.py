import math
from algorithms.priority_queue import UserPriorityQueue


class GreedyRedistributor:

    def __init__(self, aps, users):
        self.aps = aps
        self.users = users

    # ------------------------------------------------------
    # detect APs whose load > airtime_capacity
    # ------------------------------------------------------
    def get_overloaded_aps(self):
        overloaded = []
        for ap in self.aps:
            if ap["load"] > ap["airtime_capacity"]:
                overloaded.append(ap)
        return overloaded

    # ------------------------------------------------------
    # build a PQ of users connected to a given AP
    # ordered by: weaker RSSI → higher priority to move
    # ------------------------------------------------------
    def build_priority_queue(self, ap):
        pq = UserPriorityQueue()
        ap_id = ap["id"]

        for user in self.users:
            if user.get("assigned_ap") == ap_id:
                # weaker RSSI → higher priority
                priority = abs(user.get("RSSI", -95))
                pq.push(priority, user)


        return pq

    # ------------------------------------------------------
    # find the best alternative AP for a user
    # criteria:
    #  1. must have spare capacity
    #  2. choose AP with strongest RSSI for that user
    # ------------------------------------------------------
    def find_alternative_ap(self, user):
        best_ap = None
        best_rssi = -200

        for ap in self.aps:
            # skip same AP
            if ap["id"] == user.get("assigned_ap"):
                continue

            # check spare capacity
            if ap["load"] >= ap["airtime_capacity"]:
                continue

            # check signal strength
            if math.dist((user["x"], user["y"]), (ap["x"], ap["y"])) > ap["coverage_radius"]:
                continue

            # calculate RSSI
            dx = ap["x"] - user["x"]
            dy = ap["y"] - user["y"]
            dist = math.sqrt(dx*dx + dy*dy)
            if dist <= 0:
                continue
            
            rssi = -30 - 20 * math.log10(dist)
            if rssi > best_rssi:
                best_rssi = rssi
                best_ap = ap
        
        return best_ap

    # ------------------------------------------------------
    # Apply greedy redistribution:
    # Move weakest users from overloaded AP to available AP
    # ------------------------------------------------------
    def redistribute(self):
        overloaded_aps = self.get_overloaded_aps()

        for ap in overloaded_aps:

            pq = self.build_priority_queue(ap)

            # While AP is overloaded, move weak users
            while len(pq) > 0 and ap["load"] > ap["airtime_capacity"]:

                user = pq.pop()

                alternative_ap = self.find_alternative_ap(user)

                if alternative_ap:
                    # reassign user
                    user["assigned_ap"] = alternative_ap["id"]

                    # update loads
                    ap["load"] -= user.get("airtime_usage", 1)
                    alternative_ap["load"] += user.get("airtime_usage", 1)

                else:
                    # no alternative AP found
                    break
