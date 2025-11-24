import math

# ============================================================
# Tunable Weights
# ============================================================
W = {
    "distance":      0.20,
    "signal":        0.50,
    "airtime":       1.00,
    "sticky":        0.40,
    "interference":  0.20,
    "load":          0.60,   # NEW → AP load penalty
}

RSSI_THRESHOLD = -75
FLOOR_PENALTY = 10_000          # Hard block: cross-floor assignment is illegal


# ============================================================
# 1. Dynamic AP Capacity (Real WiFi Controllers)
# ============================================================
def dynamic_capacity(ap):
    """
    Real enterprise WiFi (Cisco/Aruba) automatically increases
    per-AP effective capacity when user count rises.

    This function implements:
        C_eff = base * (1 + α * log(1 + users))
    """

    base = ap.get("airtime_capacity", 100)
    users = ap.get("user_count", 0)
    alpha = 0.25  # Smooth boosting

    # Safe log
    boosted = base * (1 + alpha * math.log(1 + users))

    return max(base, boosted)


# ============================================================
# 2. Helper Functions
# ============================================================
def euclidean_distance(u, ap):
    try:
        return math.dist((u["x"], u["y"]), (ap["x"], ap["y"]))
    except Exception:
        return 9999.0


def signal_penalty(RSSI):
    """
    Convert RSSI → cost
    RSSI ranges between -40 (best) and -95 (worst)
    """
    return max(0.0, (-RSSI - 40.0) / 10.0)


def sticky_penalty(RSSI):
    """
    If RSSI is weak, discourage handoff.
    """
    return 1.0 if RSSI < RSSI_THRESHOLD else 0.0


def interference_penalty(ap):
    return float(ap.get("interference_score", 0.0))


def load_penalty(ap):
    """
    Cost increases as AP approaches its dynamic effective capacity.
    """
    load = ap.get("load", 0.0)
    cap = dynamic_capacity(ap)

    if cap <= 0:
        return 5.0  # emergency

    t = load / cap              # 0 → 1 range
    t = max(0, min(1.5, t))     # clamp for safety

    return t


# ============================================================
# MAIN COST FUNCTION (Floor-Safe)
# ============================================================
def compute_cost(user, ap):
    """
    Cost for MCMF edges.
    Lower = better.
    """

    # ---------------------------
    # HARD RESTRICTION:
    # No cross-floor connection ever.
    # ---------------------------
    if user.get("floor") != ap.get("floor"):
        return FLOOR_PENALTY

    # ---------------------------
    # Distance
    # ---------------------------
    dist = euclidean_distance(user, ap)

    # ---------------------------
    # RSSI via log-distance model
    # ---------------------------
    try:
        temp_rssi = -30 - 20 * math.log10(max(dist, 1.0))
    except ValueError:
        temp_rssi = -95

    temp_rssi = max(-95, min(-40, temp_rssi))

    # ---------------------------
    # Cost components
    # ---------------------------
    sig = signal_penalty(temp_rssi)
    air = float(user.get("airtime_usage", 1))
    sticky = sticky_penalty(temp_rssi)
    inter = interference_penalty(ap)
    load = load_penalty(ap)  # NEW

    total = (
        W["distance"]      * dist +
        W["signal"]        * sig +
        W["airtime"]       * air +
        W["sticky"]        * sticky +
        W["interference"]  * inter +
        W["load"]          * load       # NEW → makes system self-balancing
    )

    return round(total, 3)
