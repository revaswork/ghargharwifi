# src/algorithms/graph_model.py
import networkx as nx
from algorithms.cost_function import compute_cost


class GraphModel:
    """
    Build directed flow graph:
      S -> user nodes (cap=1)
      user -> ap (cap=1, weight=cost)
      ap -> T (cap=airtime_capacity, weight=0)
    """

    def __init__(self, users, aps):
        self.users = users
        self.aps = aps

    def build_graph(self):
        G = nx.DiGraph()

        # add source and sink
        G.add_node("S")
        G.add_node("T")

        # S -> user
        for u in self.users:
            uid = u["id"]
            # Use capacity 1; supply/demand approach will be handled by networkx algorithm
            G.add_edge("S", uid, capacity=1, weight=0)

        # user -> ap
        for u in self.users:
            uid = u["id"]
            for ap in self.aps:
                aid = ap["id"]
                cost = compute_cost(u, ap)
                # weight must be integer for some older algorithms; keep float works with networkx
                G.add_edge(uid, aid, capacity=1, weight=cost)

        # ap -> T
        for ap in self.aps:
            aid = ap["id"]
            # airtime capacity is integer; ensure it's at least 1
            cap = int(max(1, ap.get("airtime_capacity", 1)))
            G.add_edge(aid, "T", capacity=cap, weight=0)

        return G
