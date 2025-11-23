# src/algorithms/mcmf.py
import networkx as nx
from algorithms.graph_model import GraphModel

class MCMFEngine:
    def __init__(self, users, aps):
        self.users = users
        self.aps = aps

    def run(self):
        """
        Build graph, run a max-flow-with-min-cost, return assignments dict:
          { user_id: ap_id }
        """
        model = GraphModel(self.users, self.aps)
        G = model.build_graph()

        # Run max flow with minimum cost from S to T
        try:
            # networkx provides max_flow_min_cost which takes G, source, sink
            flow_dict = nx.algorithms.flow.max_flow_min_cost(G, "S", "T")
        except Exception as e:
            # fallback: try network_simplex (requires demands) or raise
            raise RuntimeError(f"max_flow_min_cost failed: {e}")

        assignments = {}
        # Extract user -> ap assignments: flow_dict[user_id][ap_id] == 1
        for u in self.users:
            uid = u["id"]
            if uid not in flow_dict:
                continue
            for ap in self.aps:
                aid = ap["id"]
                if aid in flow_dict[uid] and flow_dict[uid][aid] >= 1:
                    assignments[uid] = aid
                    break

        return assignments
