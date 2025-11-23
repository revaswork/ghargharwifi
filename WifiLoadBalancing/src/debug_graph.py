import json, math
from algorithms.cost_function import compute_cost
from algorithms.graph_model import GraphModel

def load(path):
    with open(path) as f:
        return json.load(f)

def calc_rssi(u, ap):
    dist = math.dist((u["x"], u["y"]), (ap["x"], ap["y"]))
    if dist <= 0:
        return -30
    rssi = -30 - 20 * math.log10(dist)
    return max(-95, min(-40, rssi)), dist

if __name__ == "__main__":
    aps = load("../data/aps.json")
    users = load("../data/users.json")

    print("\n==== AP capacities ====")
    for ap in aps:
        print(ap["id"], "capacity =", ap["airtime_capacity"], "coverage =", ap["coverage_radius"])

    print("\n==== Checking users → nearest AP distance & RSSI ====")
    for u in users[:10]:     # first 10 users only
        best_ap = None
        best_rssi = -99
        best_dist = 99999
        for ap in aps:
            rssi, dist = calc_rssi(u, ap)
            if dist < best_dist:
                best_dist = dist
                best_rssi = rssi
                best_ap = ap["id"]
        print(f"User {u['id']}: nearest AP = {best_ap}, dist = {best_dist:.2f}, rssi = {best_rssi}")

    print("\n==== Checking cost values (users → aps) ====")
    for u in users[:5]:
        for ap in aps[:5]:
            cost = compute_cost(u, ap)
            print(f"u{u['id']} → ap{ap['id']} cost = {cost}")
        print("----")

    print("\n==== Building graph ====")
    model = GraphModel(users, aps)
    G = model.build_graph()

    print("Graph nodes count:", len(G.nodes()))
    print("Graph edges count:", len(G.edges()))

    print("\nEdges from first 5 users:")
    for u in [u["id"] for u in users[:5]]:
        print("User:", u, "edges:", list(G[u].items()))
