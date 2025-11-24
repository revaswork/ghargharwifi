#!/usr/bin/env python3
"""
generate_initial_data.py — OVERLOAD-PROOF EDITION

✔ Balanced per-floor user distribution (using FLOOR_DENSITY)
✔ No AP starts above its user-count capacity (max_clients)
✔ No AP starts above a safe airtime utilization
✔ Users ALWAYS placed inside valid rooms
✔ RSSI always valid (-95 to -40)
✔ Perfect compatibility with simulator.py
"""

import json
import random
import math
from pathlib import Path

# ---------------------------------------------------------
# PATH CONFIG (correct for your project)
# ---------------------------------------------------------
SCRIPT_DIR = Path(__file__).resolve()
ROOT = SCRIPT_DIR.parents[2]            # WifiLoadBalancing/
OUT_DIR = ROOT / "data"
LAYOUT_PATH = ROOT / "frontend" / "data" / "campus_layout.json"

OUT_DIR.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------
# LOAD CAMPUS LAYOUT
# ---------------------------------------------------------
with open(LAYOUT_PATH, "r") as f:
    FLOORS = json.load(f)["floors"]

# ---------------------------------------------------------
# GLOBAL SETTINGS
# ---------------------------------------------------------
TOTAL_USERS = 175               # target total users (will be respected if capacity allows)
CHANNELS = [1, 6, 11]

# Distribution chosen so no floor *logically* overloads its 2 APs
FLOOR_DENSITY = {
    7: 0.18,
    6: 0.17,
    5: 0.16,
    4: 0.16,
    3: 0.14,
    2: 0.10,
    1: 0.09,
}

# Safety factor: we won't fill airtime to 100% at t = 0
AIRTIME_UTILIZATION_SAFETY = 0.80     # 80% of airtime_capacity
AVG_AIRTIME_PER_USER = 3.0           # rough average airtime_usage

# ---------------------------------------------------------
# HELPERS
# ---------------------------------------------------------
def find_floor(level: int):
    return next(f for f in FLOORS if f["level"] == level)


def rand_point(room: dict):
    """Return a point a few px away from walls = never out of bounds."""
    pad = 6
    return (
        room["x"] + pad + random.random() * (room["width"] - 2 * pad),
        room["y"] + pad + random.random() * (room["height"] - 2 * pad),
    )


def dist(a, b) -> float:
    return math.hypot(a[0] - b[0], a[1] - b[1])


def rssi_from_dist(d: float) -> int:
    if d <= 1:
        return -40
    r = -30 - 20 * math.log10(d)
    return max(-95, min(-40, int(r)))


# ---------------------------------------------------------
# AP GENERATION
# ---------------------------------------------------------
def build_ap_positions():
    """
    Place 2 APs per floor in corridor: left & right thirds.
    """
    table = {}

    for floor in FLOORS:
        level = floor["level"]

        corridor = next(
            r for r in floor["rooms"] if r["name"].lower() == "corridor"
        )

        cx, cy = corridor["x"], corridor["y"]
        cw, ch = corridor["width"], corridor["height"]

        mid_y = cy + ch / 2
        left_x = cx + cw * 0.33
        right_x = cx + cw * 0.66

        table[level] = [
            (f"AP_{level}A", left_x, mid_y),
            (f"AP_{level}B", right_x, mid_y),
        ]

    return table


AP_POS = build_ap_positions()


def generate_aps():
    """
    Build APs using the AP coordinates directly from campus_layout.json.
    This ensures perfect alignment with the frontend and removes all drift.
    """
    aps = []

    for floor in FLOORS:
        level = floor["level"]

        # The new layout JSON already has AP coordinates embedded
        for apinfo in floor.get("aps", []):
            ap_id = apinfo["id"]
            x = apinfo["x"]
            y = apinfo["y"]

            # Airtime capacity: rough estimate of airtime
            airtime_capacity = random.randint(90, 140)

            # Safe usable airtime
            safe_airtime = airtime_capacity * AIRTIME_UTILIZATION_SAFETY
            derived_max_clients = int(safe_airtime / AVG_AIRTIME_PER_USER)

            # Clamp range
            max_clients = max(18, min(derived_max_clients, 30))

            aps.append(
                {
                    "id": ap_id,
                    "floor": level,
                    "room": "Corridor",
                    "x": x,
                    "y": y,
                    "channel": random.choice(CHANNELS),
                    "interference_score": round(random.uniform(0.05, 0.4), 2),
                    "airtime_capacity": airtime_capacity,
                    "max_clients": max_clients,
                    "coverage_radius": 200,
                    "client_count": 0,
                    "load": 0,
                }
            )

    return aps


# ---------------------------------------------------------
# USER GENERATION (OVERLOAD-PROOF)
# ---------------------------------------------------------
def compute_floor_targets(aps):
    """
    Compute how many users to *try* to put on each floor, respecting:
      - TOTAL_USERS budget
      - Each floor's total max_clients (user-count capacity)
    """
    # Floor capacity = sum max_clients of APs on that floor
    floor_caps = {}
    for ap in aps:
        lvl = ap["floor"]
        floor_caps.setdefault(lvl, 0)
        floor_caps[lvl] += ap.get("max_clients", 20)

    # Initial targets from FLOOR_DENSITY
    raw_targets = {
        lvl: int(TOTAL_USERS * FLOOR_DENSITY[lvl])
        for lvl in FLOOR_DENSITY
    }

    # Fix rounding to match TOTAL_USERS
    diff = TOTAL_USERS - sum(raw_targets.values())
    if diff != 0:
        # Add/subtract the difference on the highest floor as a simple fix
        top_floor = max(FLOOR_DENSITY.keys())
        raw_targets[top_floor] += diff

    # Clip each floor by its capacity
    targets = {}
    for lvl, t in raw_targets.items():
        cap = floor_caps.get(lvl, 0)
        # Don't try to place more users than physical slots
        targets[lvl] = min(t, cap)

    # If we still have leftover capacity and haven't reached TOTAL_USERS,
    # we can distribute extra users to floors with free slots.
    placed = sum(targets.values())
    leftover = max(0, TOTAL_USERS - placed)

    if leftover > 0:
        # Consider floors that still have spare capacity
        floors_by_spare = sorted(
            FLOOR_DENSITY.keys(),
            key=lambda lvl: floor_caps.get(lvl, 0) - targets.get(lvl, 0),
            reverse=True,
        )
        idx = 0
        while leftover > 0 and floors_by_spare:
            lvl = floors_by_spare[idx % len(floors_by_spare)]
            spare = floor_caps.get(lvl, 0) - targets.get(lvl, 0)
            if spare <= 0:
                idx += 1
                if idx > len(floors_by_spare) * 3:
                    break
                continue
            targets[lvl] += 1
            leftover -= 1
            idx += 1

    # Final check: actual total users we will place
    final_total = sum(targets.values())
    if final_total < TOTAL_USERS:
        print(
            f"⚠️ Capacity-limited: can only place {final_total} users "
            f"(requested {TOTAL_USERS})"
        )

    return targets


def generate_users(aps):
    """
    Generate users such that:
      • No AP exceeds max_clients
      • No AP exceeds ~AIRTIME_UTILIZATION_SAFETY * airtime_capacity
    """
    users = []

    # Track per-AP state while placing users
    ap_state = {
        ap["id"]: {
            "ap": ap,
            "user_count": 0,
            "airtime_used": 0,
        }
        for ap in aps
    }

    # How many users we *aim* to place on each floor
    per_floor_target = compute_floor_targets(aps)

    for level, target_count in per_floor_target.items():
        if target_count <= 0:
            continue

        floor = find_floor(level)
        rooms = floor["rooms"]
        aps_here = [ap for ap in aps if ap["floor"] == level]

        # Filter out floors with no APs (shouldn't happen)
        if not aps_here:
            print(f"⚠️ No APs on floor {level}, skipping users there")
            continue

        placed_on_floor = 0
        attempts = 0
        max_attempts = target_count * 10  # just in case

        while placed_on_floor < target_count and attempts < max_attempts:
            attempts += 1

            room = random.choice(rooms)
            x, y = rand_point(room)

            # Decide user's airtime usage
            airtime_usage = random.randint(1, 5)

            # Among APs on this floor, choose one that:
            #   - Has user_count < max_clients
            #   - airtime_used + new_airtime <= safe_airtime
            # and is closest in distance.
            candidates = []
            for ap in aps_here:
                st = ap_state[ap["id"]]
                max_clients = ap.get("max_clients", 20)

                # User-count capacity check
                if st["user_count"] >= max_clients:
                    continue

                airtime_cap = ap.get("airtime_capacity", 100)
                safe_airtime = airtime_cap * AIRTIME_UTILIZATION_SAFETY

                # Airtime capacity check
                if st["airtime_used"] + airtime_usage > safe_airtime:
                    continue

                d = dist((x, y), (ap["x"], ap["y"]))
                candidates.append((d, ap, st))

            if not candidates:
                # No AP on this floor can safely take more users
                print(
                    f"⚠️ Floor {level}: exhausted AP capacity after "
                    f"{placed_on_floor} users (target {target_count})"
                )
                break

            # Pick closest feasible AP
            candidates.sort(key=lambda t: t[0])
            _, best_ap, best_state = candidates[0]

            d_ap = dist((x, y), (best_ap["x"], best_ap["y"]))
            rssi = rssi_from_dist(d_ap)

            new_user = {
                "id": f"User_{len(users)+1}",
                "floor": level,
                "room": room["name"],
                "x": round(x, 2),
                "y": round(y, 2),
                "connected_ap": best_ap["id"],
                "assigned_ap": best_ap["id"],  # matches simulator expectations
                "airtime_usage": airtime_usage,
                "RSSI": rssi,
            }

            users.append(new_user)

            # Update AP state
            best_state["user_count"] += 1
            best_state["airtime_used"] += airtime_usage
            best_ap["client_count"] += 1

            placed_on_floor += 1

    # Final sanity log
    print("\nPer-AP initial usage:")
    for ap_id, st in ap_state.items():
        ap = st["ap"]
        print(
            f"  {ap_id} (floor {ap['floor']}): "
            f"users={st['user_count']}/{ap['max_clients']}, "
            f"airtime={st['airtime_used']}/"
            f"{int(ap['airtime_capacity'] * AIRTIME_UTILIZATION_SAFETY)} (safe)"
        )

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
    print(
        "Per-floor users:",
        {lvl: sum(1 for u in users if u["floor"] == lvl) for lvl in FLOOR_DENSITY},
    )


if __name__ == "__main__":
    main()
