#!/usr/bin/env python3
"""
generate_initial_data.py — BAND-NEUTRAL USER SPAWNING EDITION

✔ Users spawn ANYWHERE inside valid rooms (no coverage restrictions)
✔ Band coverage is handled ONLY by simulator.py (band switching makes users disappear)
✔ Balanced per-floor user distribution (using FLOOR_DENSITY)
✔ No AP starts above its user-count capacity (max_clients)
✔ No AP starts above safe airtime utilization
✔ RSSI always valid (-95 to -40)
✔ Perfect compatibility with simulator.py
"""

import json
import random
import math
from pathlib import Path

# ---------------------------------------------------------
# PATH CONFIG
# ---------------------------------------------------------
CURRENT = Path(__file__).resolve()
SIM_DIR = CURRENT.parents[1]              # WifiLoadBalancing/src/simulation
ROOT = SIM_DIR.parent                    # WifiLoadBalancing/
OUT_DIR = ROOT / "data"
LAYOUT_PATH = ROOT / "frontend" / "data" / "campus_layout.json"
CONFIG_PATH = OUT_DIR / "config.json"

OUT_DIR.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------
# LOAD CAMPUS LAYOUT
# ---------------------------------------------------------
with open(LAYOUT_PATH, "r") as f:
    FLOORS = json.load(f)["floors"]

# ---------------------------------------------------------
# GLOBAL SETTINGS
# ---------------------------------------------------------
TOTAL_USERS = 175

CHANNELS_24 = [1, 6, 11]
CHANNELS_5  = [36, 40, 44, 48]
CHANNELS_6  = [5, 21, 37, 53, 69]

CHANNELS_BY_BAND = {
    "2.4": CHANNELS_24,
    "5":   CHANNELS_5,
    "6":   CHANNELS_6,
}

# Coverage IS NOT USED IN GENERATOR ANYMORE
# (Only simulator checks coverage during runtime)
BAND_COVERAGE = {
    "2.4": 600,
    "5":   450,
    "6":   250,
}

BAND_PATHLOSS = {
    "2.4": 20,
    "5":   22,
    "6":   24,
}

def load_config():
    if CONFIG_PATH.exists():
        try:
            with open(CONFIG_PATH, "r") as f:
                return json.load(f)
        except:
            print("⚠️ Failed to read config.json, using defaults")
    return {}

CONFIG = load_config()
DEFAULT_BAND = CONFIG.get("default_band", "5")
if DEFAULT_BAND not in CHANNELS_BY_BAND:
    print(f"⚠️ Invalid default_band '{DEFAULT_BAND}' in config.json, using '5'")
    DEFAULT_BAND = "5"

# Floor population distribution
FLOOR_DENSITY = {
    7: 0.18,
    6: 0.17,
    5: 0.16,
    4: 0.16,
    3: 0.14,
    2: 0.10,
    1: 0.09,
}

AIRTIME_UTILIZATION_SAFETY = 0.80
AVG_AIRTIME_PER_USER = 3.0

# ---------------------------------------------------------
# HELPERS
# ---------------------------------------------------------
def find_floor(level):
    return next(f for f in FLOORS if f["level"] == level)

def rand_point(room):
    pad = 6
    return (
        room["x"] + pad + random.random() * (room["width"] - 2 * pad),
        room["y"] + pad + random.random() * (room["height"] - 2 * pad),
    )

def dist(a, b):
    return math.hypot(a[0] - b[0], a[1] - b[1])

def rssi_from_dist(d, band):
    loss = BAND_PATHLOSS.get(band, 22)
    if d <= 1:
        return -40
    r = -30 - loss * math.log10(max(d, 1e-3))
    return max(-95, min(-40, int(r)))

# AP interference model
def compute_interference(ap, aps):
    score = 0.0
    for other in aps:
        if other["id"] == ap["id"]:
            continue
        if other["band"] != ap["band"]:
            continue
        if other["channel"] == ap["channel"]:
            score += 1.0
        elif abs(other["channel"] - ap["channel"]) <= 5:
            score += 0.5
    return round(score, 2)

# ---------------------------------------------------------
# AP GENERATION
# ---------------------------------------------------------
def generate_aps():
    aps = []

    for floor in FLOORS:
        level = floor["level"]

        for apinfo in floor.get("aps", []):
            ap_id = apinfo["id"]
            x = apinfo["x"]
            y = apinfo["y"]

            airtime_capacity = random.randint(90, 140)
            safe_airtime = airtime_capacity * AIRTIME_UTILIZATION_SAFETY
            derived_max_clients = int(safe_airtime / AVG_AIRTIME_PER_USER)

            max_clients = max(18, min(derived_max_clients, 30))

            ap_band = DEFAULT_BAND

            band_channels = CHANNELS_BY_BAND[ap_band]
            channel = band_channels[len(aps) % len(band_channels)]

            aps.append(
                {
                    "id": ap_id,
                    "floor": level,
                    "room": "Corridor",
                    "x": x,
                    "y": y,
                    "band": ap_band,
                    "channel": channel,
                    "interference_score": 0.0,
                    "airtime_capacity": airtime_capacity,
                    "max_clients": max_clients,
                    "coverage_radius": BAND_COVERAGE[ap_band],   # unused by generator
                    "client_count": 0,
                    "load": 0,
                }
            )

    for ap in aps:
        ap["interference_score"] = compute_interference(ap, aps)

    return aps


# ---------------------------------------------------------
# USER GENERATION (NO COVERAGE LIMITS)
# ---------------------------------------------------------
def compute_floor_targets(aps):
    floor_caps = {}
    for ap in aps:
        lvl = ap["floor"]
        floor_caps.setdefault(lvl, 0)
        floor_caps[lvl] += ap.get("max_clients", 20)

    raw_targets = {
        lvl: int(TOTAL_USERS * FLOOR_DENSITY[lvl])
        for lvl in FLOOR_DENSITY
    }

    diff = TOTAL_USERS - sum(raw_targets.values())
    if diff != 0:
        top = max(FLOOR_DENSITY.keys())
        raw_targets[top] += diff

    targets = {}
    for lvl, t in raw_targets.items():
        cap = floor_caps.get(lvl, 0)
        targets[lvl] = min(t, cap)

    return targets

def pick_best_ap(candidates):
    band_rank = {"6": 3, "5": 2, "2.4": 1}
    candidates.sort(key=lambda t: (-band_rank[t[1]["band"]], t[0]))
    return candidates[0]

def generate_users(aps):
    users = []

    ap_state = {
        ap["id"]: {"ap": ap, "user_count": 0, "airtime_used": 0}
        for ap in aps
    }

    per_floor_target = compute_floor_targets(aps)

    for level, target_count in per_floor_target.items():
        if target_count <= 0:
            continue

        floor = find_floor(level)
        rooms = floor["rooms"]
        aps_here = [ap for ap in aps if ap["floor"] == level]

        placed = 0
        attempts = 0
        max_attempts = target_count * 15

        while placed < target_count and attempts < max_attempts:
            attempts += 1

            room = random.choice(rooms)
            x, y = rand_point(room)

            airtime_usage = random.randint(1, 5)

            # 🔥 NOTICE: NO COVERAGE CHECK ANYMORE 🔥
            candidates = []
            for ap in aps_here:
                st = ap_state[ap["id"]]

                if st["user_count"] >= ap["max_clients"]:
                    continue

                safe_air = ap["airtime_capacity"] * AIRTIME_UTILIZATION_SAFETY
                if st["airtime_used"] + airtime_usage > safe_air:
                    continue

                d = dist((x, y), (ap["x"], ap["y"]))
                candidates.append((d, ap, st))

            if not candidates:
                break

            _, best_ap, best_state = pick_best_ap(candidates)

            d_ap = dist((x, y), (best_ap["x"], best_ap["y"]))
            rssi = rssi_from_dist(d_ap, best_ap["band"])

            new_user = {
                "id": f"User_{len(users)+1}",
                "floor": level,
                "room": room["name"],
                "x": round(x, 2),
                "y": round(y, 2),
                "connected_ap": best_ap["id"],
                "assigned_ap": best_ap["id"],
                "airtime_usage": airtime_usage,
                "RSSI": rssi,
            }

            users.append(new_user)

            best_state["user_count"] += 1
            best_state["airtime_used"] += airtime_usage

            placed += 1

    return users

# ---------------------------------------------------------
# MAIN
# ---------------------------------------------------------
def main():
    print("ROOT:", ROOT)
    print("LAYOUT:", LAYOUT_PATH)

    aps = generate_aps()
    users = generate_users(aps)

    (OUT_DIR / "aps.json").write_text(json.dumps(aps, indent=4))
    (OUT_DIR / "users.json").write_text(json.dumps(users, indent=4))

    print("\n✔ DATA GENERATED SUCCESSFULLY")
    print("AP count:", len(aps))
    print("User count:", len(users))

if __name__ == "__main__":
    main()
