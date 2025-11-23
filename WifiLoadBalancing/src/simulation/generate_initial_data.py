#!/usr/bin/env python3
"""
generate_initial_data.py — Realistic multi-floor campus generator
Using distribution:
• Floor 1  → 15%
• Floors 2–5 → 60% total (15% each)
• Floors 6–7 → 15% total (7.5% each)
"""

import json
import random
import math
from pathlib import Path

NUM_APS = 8
NUM_USERS = 120

OUT_DIR = Path("data")
OUT_DIR.mkdir(parents=True, exist_ok=True)

CHANNELS = [1, 6, 11]

# Floor distribution (%) → converted to weights
FLOOR_DISTRIBUTION = {
    1: 0.15,      # 15%
    2: 0.15,      # 15%
    3: 0.15,      # 15%
    4: 0.15,      # 15%
    5: 0.15,      # 15%
    6: 0.075,     # 7.5%
    7: 0.075      # 7.5%
}

# Campus layout (same as before)
CAMPUS_LAYOUT = {
    "floors": [
        { "level": 7, "name": "7th Floor - Library",
          "rooms": [
            {"name": "Library", "x": 40, "y": 30, "width": 820, "height": 180},
            {"name": "Study Area", "x": 40, "y": 220, "width": 820, "height": 160}
          ]},
        { "level": 6, "name": "6th Floor - Staff",
          "rooms": [
            {"name":"Staff Room A","x":40,"y":30,"width":470,"height":350},
            {"name":"Staff Room B","x":540,"y":30,"width":470,"height":350}
          ]},
        { "level": 5, "name": "5th Floor - Classrooms",
          "rooms": [
            {"name":"Class 501","x":40,"y":30,"width":300,"height":160},
            {"name":"Class 502","x":360,"y":30,"width":300,"height":160},
            {"name":"Class 503","x":680,"y":30,"width":300,"height":160},
            {"name":"Class 504","x":40,"y":200,"width":300,"height":160},
            {"name":"Class 505","x":360,"y":200,"width":300,"height":160},
            {"name":"Class 506","x":680,"y":200,"width":300,"height":160}
          ]},
        { "level": 4, "name": "4th Floor - Classrooms + Success Centre",
          "rooms": [
            {"name":"Class 401","x":40,"y":30,"width":260,"height":160},
            {"name":"Class 402","x":320,"y":30,"width":260,"height":160},
            {"name":"Class 403","x":600,"y":30,"width":260,"height":160},
            {"name":"Class 404","x":40,"y":210,"width":260,"height":160},
            {"name":"Class 405","x":320,"y":210,"width":260,"height":160},
            {"name":"Success Centre (Right)","x":600,"y":210,"width":260,"height":160}
          ]},
        { "level": 3, "name": "3rd Floor - Classrooms",
          "rooms": [
            {"name":"Class 301","x":40,"y":30,"width":300,"height":160},
            {"name":"Class 302","x":360,"y":30,"width":300,"height":160},
            {"name":"Class 303","x":680,"y":30,"width":300,"height":160},
            {"name":"Class 304","x":40,"y":200,"width":300,"height":160},
            {"name":"Class 305","x":360,"y":200,"width":300,"height":160},
            {"name":"Class 306","x":680,"y":200,"width":300,"height":160}
          ]},
        { "level": 2, "name": "2nd Floor - Classrooms",
          "rooms": [
            {"name":"Class 201","x":40,"y":30,"width":300,"height":160},
            {"name":"Class 202","x":360,"y":30,"width":300,"height":160},
            {"name":"Class 203","x":680,"y":30,"width":300,"height":160},
            {"name":"Class 204","x":40,"y":200,"width":300,"height":160},
            {"name":"Class 205","x":360,"y":200,"width":300,"height":160},
            {"name":"Class 206","x":680,"y":200,"width":300,"height":160}
          ]},
        { "level": 1, "name": "1st Floor - Labs & Canteen",
          "rooms": [
            {"name":"Lab A","x":40,"y":30,"width":420,"height":260},
            {"name":"Lab B","x":480,"y":30,"width":420,"height":260},
            {"name":"Canteen (Right)","x":920,"y":30,"width":240,"height":260},
            {"name":"Corridor (center)","x":40,"y":310,"width":1120,"height":120}
          ]}
    ]
}

# Fixed AP placements
FIXED_AP_PLAN = [
    {"id":"AP_1", "floor":7, "room":"Library"},
    {"id":"AP_2", "floor":6, "room":"Staff Room A"},
    {"id":"AP_3", "floor":5, "room":"Class 501"},
    {"id":"AP_4", "floor":5, "room":"Class 506"},
    {"id":"AP_5", "floor":4, "room":"Success Centre (Right)"},
    {"id":"AP_6", "floor":3, "room":"Class 302"},
    {"id":"AP_7", "floor":2, "room":"Class 203"},
    {"id":"AP_8", "floor":1, "room":"Lab A"}
]


# -------------------------------
# Helpers
# -------------------------------
def find_floor(level):
    return next((f for f in CAMPUS_LAYOUT["floors"] if f["level"] == level), None)

def find_room_on_floor(floor_obj, room_name):
    return next((r for r in floor_obj["rooms"] if r["name"].lower() == room_name.lower()), None)

def place_point_in_room(room):
    pad = 8
    return (
        room["x"] + pad + random.random() * (room["width"] - pad*2),
        room["y"] + pad + random.random() * (room["height"] - pad*2)
    )

def calculate_rssi(distance):
    if distance <= 0.5:
        return -30
    rssi = -30 - 20 * math.log10(distance)
    return max(-95, min(-40, int(rssi)))

def euclid(a, b):
    return math.hypot(a[0] - b[0], a[1] - b[1])


# -------------------------------
# Generate Access Points
# -------------------------------
def generate_access_points():
    aps = []
    for spec in FIXED_AP_PLAN:

        floor_obj = find_floor(spec["floor"])
        room = find_room_on_floor(floor_obj, spec["room"])

        if room:
            x, y = place_point_in_room(room)
        else:
            x, y = 200 + random.random() * 200, 200 + random.random() * 200

        coverage = int((room["width"] + room["height"]) / 4)

        aps.append({
            "id": spec["id"],
            "floor": spec["floor"],
            "room": spec["room"],
            "x": round(x, 2),
            "y": round(y, 2),
            "channel": random.choice(CHANNELS),
            "interference_score": round(random.uniform(0.05, 0.5), 2),
            "airtime_capacity": random.randint(60, 140),
            "max_clients": random.randint(20, 45),
            "coverage_radius": coverage,
            "client_count": 0,
            "load": 0
        })

    return aps


# -------------------------------
# Generate Users
# -------------------------------
def generate_users(aps):
    users = []

    # Convert % distribution → counts
    floor_user_counts = {
        floor: int(NUM_USERS * FLOOR_DISTRIBUTION[floor])
        for floor in FLOOR_DISTRIBUTION
    }

    # Adjust rounding to reach 120 exactly
    total = sum(floor_user_counts.values())
    diff = NUM_USERS - total
    if diff != 0:
        floor_user_counts[1] += diff

    # Now generate users floor by floor
    for floor, count in floor_user_counts.items():

        floor_obj = find_floor(floor)
        rooms = floor_obj["rooms"]

        for _ in range(count):
            room = random.choice(rooms)
            x, y = place_point_in_room(room)

            # Choose nearest AP on the same floor
            aps_on_floor = [ap for ap in aps if ap["floor"] == floor]
            best_ap = min(
                aps_on_floor,
                key=lambda ap: euclid((x, y), (ap["x"], ap["y"]))
            )
            dist = euclid((x, y), (best_ap["x"], best_ap["y"]))
            rssi = calculate_rssi(dist / 10)

            users.append({
                "id": f"User_{len(users)+1}",
                "floor": floor,
                "room": room["name"],
                "x": round(x, 2),
                "y": round(y, 2),
                "connected_ap": best_ap["id"],
                "airtime_usage": random.randint(1, 5),
                "RSSI": rssi
            })

            best_ap["client_count"] += 1

    # Compute load
    for ap in aps:
        base = ap["client_count"] * 100 / ap["max_clients"]
        ap["load"] = int(max(0, min(100, base + random.uniform(-5, 5))))

    return users


# -------------------------------
def save_json(data, path):
    with open(path, "w") as f:
        json.dump(data, f, indent=4)


def main():
    aps = generate_access_points()
    users = generate_users(aps)

    save_json(aps, OUT_DIR / "aps.json")
    save_json(users, OUT_DIR / "users.json")

    print("\n✔ Generated APs & Users with realistic floor distribution\n")
    print("Floor counts:", {f: sum(1 for u in users if u["floor"] == f) for f in FLOOR_DISTRIBUTION})


if __name__ == "__main__":
    main()
