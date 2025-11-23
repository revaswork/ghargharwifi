# src/algorithms/cost_function.py
import math

# ===========================================================
# Tunable weights
# ===========================================================
W = {
    "distance": 0.2,
    "signal": 0.5,
    "airtime": 1.0,
    "sticky": 0.5,
    "interference": 0.2,
}

RSSI_THRESHOLD = -75


# ===========================================================
# Helper functions
# ===========================================================
def euclidean_distance(u, ap):
    return math.dist((u["x"], u["y"]), (ap["x"], ap["y"]))


def signal_penalty(RSSI):
    # convert RSSI to a small non-negative penalty
    # RSSI expected in [-95, -40]
    return max(0.0, (-RSSI - 40.0) / 10.0)


def sticky_penalty(RSSI):
    return 1 if RSSI < RSSI_THRESHOLD else 0


def interference_penalty(ap):
    return float(ap.get("interference_score", 0.0))


# ===========================================================
# MAIN COST FUNCTION
# ===========================================================
def compute_cost(user, ap):
    # distance
    try:
        dist = euclidean_distance(user, ap)
    except Exception:
        dist = 100.0

    sig = signal_penalty(user.get("RSSI", -95))
    air = float(user.get("airtime_usage", 1))
    sticky = sticky_penalty(user.get("RSSI", -95))
    inter = interference_penalty(ap)

    total = (
        W["distance"] * dist +
        W["signal"] * sig +
        W["airtime"] * air +
        W["sticky"] * sticky +
        W["interference"] * inter
    )

    return round(total, 3)
