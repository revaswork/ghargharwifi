import networkx as nx
from algorithms.cost_function import compute_cost, dynamic_capacity


class GraphModel:
    """
    Min-Cost Max-Flow Graph:

        S → user nodes (capacity=1)
        user → AP edges (capacity=1, weight=cost)
        AP → T (capacity = dynamic airtime capacity)

    Properties:
      • No cross-floor edges
      • Load-aware dynamic AP capacity
      • Smaller graph → faster
      • Fully stable with new cost model
    """

    def __init__(self, users, aps):
        self.users = users
        self.aps = aps

    def build_graph(self):
        G = nx.DiGraph()

        # Source & Sink
        G.add_node("S")
        G.add_node("T")

        # ---------------------------------------------------
        # 1. S → Users
        # ---------------------------------------------------
        for u in self.users:
            uid = u["id"]
            G.add_edge("S", uid, capacity=1, weight=0)

        # ---------------------------------------------------
        # 2. Users → APs (same floor only)
        # ---------------------------------------------------
        for u in self.users:
            uid = u["id"]
            user_floor = u.get("floor")

            # APs only on the same floor (strict rule)
            same_floor_aps = [
                ap for ap in self.aps
                if ap.get("floor") == user_floor
            ]

            for ap in same_floor_aps:
                aid = ap["id"]
                cost = compute_cost(u, ap)

                # Each assignment = 1 unit of flow
                G.add_edge(uid, aid, capacity=1, weight=cost)

        # ---------------------------------------------------
        # 3. APs → T (dynamic capacity)
        # ---------------------------------------------------
        for ap in self.aps:
            aid = ap["id"]

            # REAL CHANGE:
            # Instead of max_clients (static)
            # we use dynamic capacity that grows logarithmically
            cap = dynamic_capacity(ap)

            # Make sure we don't pass floats to networkx
            G.add_edge(aid, "T", capacity=int(cap), weight=0)

        return G
