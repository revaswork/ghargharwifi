import networkx as nx
from algorithms.graph_model import GraphModel
from algorithms.cost_function import dynamic_capacity


class MCMFEngine:
    """
    Enhanced Min-Cost-Max-Flow Engine (with dynamic capacity)

    Guarantees:
    --------------------------------------------------------
    • Users connect ONLY to APs on same floor
    • APs expose dynamic load-based capacity
    • Works even when #users > total capacity (partial assignment ok)
    • Stable + safe fallback behaviour
    • Output always includes ALL users (even unassigned ones)
    """

    def __init__(self, users, aps):
        self.users = users
        self.aps = aps

    def run(self):
        """
        Build graph → run MCMF → extract assignments.
        """
        # -------------------------------------------------
        # Step 1: Build graph with dynamic AP capacities
        # -------------------------------------------------
        model = GraphModel(self.users, self.aps)
        G = model.build_graph()

        # -------------------------------------------------
        # Step 2: Update AP → Sink edges to dynamic capacity
        # -------------------------------------------------
        for ap in self.aps:
            aid = ap["id"]
            if G.has_edge(aid, "T"):
                cap = dynamic_capacity(ap)
                # dynamic capacity must be int
                G[aid]["T"]["capacity"] = int(max(1, cap))

        # -------------------------------------------------
        # Step 3: Run MCMF
        # -------------------------------------------------
        try:
            flow_dict = nx.max_flow_min_cost(G, "S", "T")
        except Exception as e:
            raise RuntimeError(f"MCMF failed: {str(e)}")

        # -------------------------------------------------
        # Step 4: Extract assignments
        # -------------------------------------------------
        assignments = {}

        for u in self.users:
            uid = u["id"]
            assigned = None

            if uid in flow_dict:
                for ap in self.aps:
                    aid = ap["id"]

                    # Hard safety — must match same floor
                    if ap["floor"] != u["floor"]:
                        continue

                    if aid in flow_dict[uid] and flow_dict[uid][aid] >= 1:
                        assigned = aid
                        break

            assignments[uid] = assigned

        # -------------------------------------------------
        # Step 5: Ensure ALL users accounted for
        # -------------------------------------------------
        for u in self.users:
            uid = u["id"]
            if uid not in assignments:
                assignments[uid] = None

        return assignments
