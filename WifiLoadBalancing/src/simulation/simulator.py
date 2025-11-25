import json
import math
import random
from pathlib import Path

from algorithms.mcmf import MCMFEngine
from algorithms.greedy_redistribution import GreedyRedistributor

# ----------------------------------------------------------------------
# PATHS - Correct for your project structure
# ----------------------------------------------------------------------
CURRENT = Path(__file__).resolve()
SIM_DIR = CURRENT.parents[1]
ROOT_DIR = SIM_DIR.parent
DATA_DIR = ROOT_DIR / "data"
LAYOUT_PATH = ROOT_DIR / "frontend" / "data" / "campus_layout.json"

# ----------------------------------------------------------------------
# GLOBAL SIM CONFIG
# ----------------------------------------------------------------------
# Turn this ON only when you want to experiment with MCMF offline / in
# a separate script. For the live websocket viz we keep it OFF to
# guarantee smooth, non-blocking steps.
USE_MCMF = False

# If you ever enable MCMF, we also cap how often and how many users.
MCMF_MAX_USERS = 120         # don't run MCMF above this count
MCMF_EVERY_N_TICKS = 10      # run at most once every N ticks


# ----------------------------------------------------------------------
# SAFE NUM HELPERS (kill NaN/inf before JSON)
# ----------------------------------------------------------------------
def safe_float(v, default=0.0) -> float:
    try:
        if isinstance(v, (int, float)) and math.isfinite(v):
            return float(v)
    except Exception:
        pass
    return float(default)


def safe_int(v, default=0) -> int:
    try:
        if isinstance(v, (int, float)) and math.isfinite(v):
            return int(v)
    except Exception:
        pass
    return int(default)


class WifiSimulator:
    """
    WiFi Load Balancing Simulator - STABLE VERSION (NON-BLOCKING)

    ✅ Ghost-proof user management
    ✅ Safe MCMF with greedy fallback (but disabled in live loop)
    ✅ Floor-restricted assignments
    ✅ NaN-proof movement AND export
    ✅ Clean state management
    ✅ Step() is LIGHT and deterministic → no more freezing
    """

    def __init__(self):
        print(">>> Simulator file active:", __file__)

        # Load data
        with open(DATA_DIR / "aps.json", "r") as f:
            self.aps = json.load(f)

        with open(DATA_DIR / "users.json", "r") as f:
            self.clients = json.load(f)

        with open(LAYOUT_PATH, "r") as f:
            layout = json.load(f)
        self.campus_layout = layout["floors"]

        # State tracking
        self.assignments = {}
        self.ap_alarms = []
        self._ap_alarm_memory = set()
        self.tick = 0
        self.ready = False
        self.current_band = "5"  # default
        
        self.band_coverage = {
            "2.4": 800,   # massive campus coverage
            "5":   320,   # moderate
            "6":   120,   # tiny
        }
        self.band_pathloss = {
            "2.4": 20,
            "5":   22,
            "6":   24,
        }

        # Initialize AP fields
        for ap in self.aps:
            ap.setdefault("load", 0)
            ap.setdefault("connected_clients", [])
            ap.setdefault("max_users", ap.get("max_clients", 30))
            ap.setdefault("coverage_radius", 200)
            ap.setdefault("user_count", 0)

        # Initialize user fields
        for user in self.clients:
            user.setdefault("vx", random.uniform(-1, 1))
            user.setdefault("vy", random.uniform(-1, 1))
            user.setdefault("nearest_ap", None)
            user.setdefault("assigned_ap", user.get("connected_ap"))
            user.setdefault("connected_ap", user.get("assigned_ap"))
            user.setdefault("airtime_usage", user.get("airtime_usage", 1))
            user.setdefault("RSSI", user.get("RSSI", -95))
            
        from .ap_killer import APKiller
        self.ap_killer = APKiller(self)

        print("✅ Simulator initialized")
        print(f"   APs: {len(self.aps)}")
        print(f"   Users: {len(self.clients)}")

    # ====================================================================
    # ROOM BOUNDS HELPERS
    # ====================================================================
    def get_user_room_bounds(self, user):
        """Return safe bounding box for user's current room."""
        floor_level = user.get("floor")
        room_name = user.get("room")

        floor = next(
            (f for f in self.campus_layout if f["level"] == floor_level),
            None
        )
        if not floor:
            return None

        room = next(
            (r for r in floor["rooms"]
             if r["name"].lower() == str(room_name).lower()),
            None
        )
        if not room:
            return None

        return {
            "x1": room["x"],
            "y1": room["y"],
            "x2": room["x"] + room["width"],
            "y2": room["y"] + room["height"],
        }

    # ====================================================================
    # USER MOVEMENT - NaN-proof, room-bounded
    # ====================================================================
    def move_users(self):
        """Move users with full validation and bounce physics."""
        BASE_MIN, BASE_MAX = 1, 2

        for user in self.clients:
            bounds = self.get_user_room_bounds(user)

            # Reset if room invalid
            if not bounds:
                self._reset_user_position(user)
                continue

            # Validate coordinates
            if not self._validate_coordinates(user):
                user["x"] = (bounds["x1"] + bounds["x2"]) / 2
                user["y"] = (bounds["y1"] + bounds["y2"]) / 2

            # Validate velocity
            if not self._validate_velocity(user):
                ang = random.random() * 2 * math.pi
                spd = random.uniform(BASE_MIN, BASE_MAX)
                user["vx"] = math.cos(ang) * spd
                user["vy"] = math.sin(ang) * spd

            # Random direction change (5% chance)
            if random.random() < 0.05:
                ang = random.random() * 2 * math.pi
                spd = random.uniform(BASE_MIN, BASE_MAX)
                user["vx"] = math.cos(ang) * spd
                user["vy"] = math.sin(ang) * spd

            # Calculate next position
            nx = safe_float(user["x"] + user["vx"])
            ny = safe_float(user["y"] + user["vy"])

            # Bounce off walls
            if nx <= bounds["x1"] or nx >= bounds["x2"]:
                user["vx"] *= -1
                nx = max(bounds["x1"] + 1, min(bounds["x2"] - 1, nx))

            if ny <= bounds["y1"] or ny >= bounds["y2"]:
                user["vy"] *= -1
                ny = max(bounds["y1"] + 1, min(bounds["y2"] - 1, ny))

            user["x"], user["y"] = nx, ny

    def _validate_coordinates(self, user):
        """Check if coordinates are valid numbers."""
        x, y = user.get("x"), user.get("y")
        return (
            isinstance(x, (int, float)) and isinstance(y, (int, float))
            and math.isfinite(x) and math.isfinite(y)
        )

    def _validate_velocity(self, user):
        """Check if velocity is valid."""
        vx, vy = user.get("vx", 0), user.get("vy", 0)
        return (
            isinstance(vx, (int, float)) and isinstance(vy, (int, float))
            and math.isfinite(vx) and math.isfinite(vy)
        )

    def _reset_user_position(self, user):
        """Reset user to center of a valid spawnable room on their floor."""
        floor_rooms = [
            r for f in self.campus_layout
            if f["level"] == user.get("floor")
            for r in f["rooms"]
        ]
        if floor_rooms:
            # Prefer non-corridor, non-staircase rooms
            spawnable = self._filter_spawn_rooms(floor_rooms)
            if not spawnable:
                spawnable = floor_rooms

            r = random.choice(spawnable)
            user["x"] = r["x"] + r["width"] / 2
            user["y"] = r["y"] + r["height"] / 2
            user["room"] = r["name"]

    # ====================================================================
    # RSSI CALCULATION
    # ====================================================================
    @staticmethod
    def calc_rssi(distance: float) -> float:
        if distance is None or not isinstance(distance, (int, float)) or distance <= 0 or not math.isfinite(distance):
            return -95
        rssi = -30 - 20 * math.log10(distance)
        if not math.isfinite(rssi):
            return -95
        return max(-95, min(-40, rssi))

    def update_rssi(self):
        """Update RSSI for all users - band-restricted with disconnection."""
        for user in self.clients:
            u_floor = user.get("floor")

            # APs on same floor
            floor_aps = [ap for ap in self.aps if ap["floor"] == u_floor]

            if not floor_aps:
                # 🔥 DISCONNECTION: floor has no APs
                user["nearest_ap"] = None
                user["connected_ap"] = None
                user["assigned_ap"] = None
                user["RSSI"] = -95
                continue

            best_ap = None
            best_rssi = -95

            # --------------------------------------------------------------
            # BAND-DEPENDENT COVERAGE + BAND-DEPENDENT RSSI
            # --------------------------------------------------------------
            for ap in floor_aps:
                try:
                    dist = math.dist(
                        (safe_float(user["x"]), safe_float(user["y"])),
                        (safe_float(ap["x"]), safe_float(ap["y"]))
                    )
                except Exception:
                    continue

                # ❗ Disconnect user if outside CURRENT BAND range
                if dist > self.band_coverage[self.current_band]:
                    continue

                band = ap.get("band", self.current_band)
                loss = self.band_pathloss.get(band, 22)

                rssi = -30 - loss * math.log10(max(dist, 1e-3))
                rssi = max(-95, min(-40, rssi))

                if rssi > best_rssi:
                    best_rssi = rssi
                    best_ap = ap["id"]

            # --------------------------------------------------------------
            # 🛑 DISCONNECTION ZONE
            # If NO AP in band range → user disappears
            # --------------------------------------------------------------
            if best_ap is None:
                user["nearest_ap"] = None
                user["connected_ap"] = None
                user["assigned_ap"] = None
                user["RSSI"] = -95
                continue

            # --------------------------------------------------------------
            # ✅ RECONNECTION ZONE (user visible again)
            # --------------------------------------------------------------
            user["nearest_ap"] = best_ap
            user["assigned_ap"] = best_ap      # ← YOU MUST HAVE THIS
            user["connected_ap"] = best_ap     # ← AND THIS
            user["RSSI"] = int(best_rssi)


    # ====================================================================
    # AP LOAD CALCULATION & ALARMS
    # ====================================================================
    def update_ap_load(self):
        """Calculate AP loads and generate alarms (debounced)."""
        self.ap_alarms = []

        # Reset counts
        for ap in self.aps:
            ap["user_count"] = 0

        # Count only users truly connected under NEW BAND CONDITIONS
        for user in self.clients:
            ap_id = user.get("assigned_ap")      # ← NO FALLBACK
            if not ap_id:
                continue                         # user dropped due to band

            for ap in self.aps:
                if ap["id"] == ap_id:
                    ap["user_count"] += 1
                    break


    # ====================================================================
    # MCMF WITH GREEDY FALLBACK (EXPERIMENTAL, NOT USED IN LIVE LOOP)
    # ====================================================================
    def apply_mcmf(self):
        """
        Run MCMF with safe greedy fallback.
        Includes REAL NETWORK LOAD BEHAVIOR:
        - AP load accumulates over time
        - AP load decays slowly instead of resetting
        - MCMF uses this load to make smarter decisions
        """
        # 1. Update signal + user counts
        self.update_rssi()
        self.update_ap_load()

        # If any AP is already overloaded in raw count, fallback early
        for ap in self.aps:
            if ap["user_count"] > ap["max_users"]:
                print(f"⚠️ AP {ap['id']} overloaded before MCMF, using greedy fallback")
                GreedyRedistributor(self.aps, self.clients).redistribute()
                return

        # 2. Run MCMF
        try:
            assignments = MCMFEngine(self.clients, self.aps).run()
        except Exception as e:
            print(f"⚠️ MCMF failed, using greedy: {e}")
            GreedyRedistributor(self.aps, self.clients).redistribute()
            assignments = {u["id"]: u.get("nearest_ap") for u in self.clients}

        self.assignments = assignments

        # -----------------------------
        # 3. SMOOTH LOAD UPDATE LOGIC
        # -----------------------------
        LOAD_DECAY = 0.82      # load retains 82% of previous value each tick
        LOAD_GAIN_WEIGHT = 0.40  # 40% from new user airtime

        # Reset connected clients list (NOT load)
        for ap in self.aps:
            ap["connected_clients"] = []

        # Compute new raw load
        new_loads = {ap["id"]: 0 for ap in self.aps}

        for user in self.clients:
            uid = user["id"]
            aid = assignments.get(uid)

            user["assigned_ap"] = aid
            user["connected_ap"] = aid

            if not aid:
                continue

            new_loads[aid] += user.get("airtime_usage", 1)

        # Apply load smoothing
        for ap in self.aps:
            ap_id = ap["id"]
            prev_load = ap.get("load", 0)

            # new instantaneous load
            instant_load = new_loads.get(ap_id, 0)

            # smoothed real load (enterprise WiFi-style)
            smoothed = prev_load * LOAD_DECAY + instant_load * LOAD_GAIN_WEIGHT

            # hard clamp to 0–100 range
            ap["load"] = max(0, min(smoothed, 100))

            # update connected clients list
            for user in self.clients:
                if user["assigned_ap"] == ap_id:
                    ap["connected_clients"].append(user["id"])

    def _is_user_in_band(self, user) -> bool:
        """
        A user is considered 'in-band' if update_rssi found at least one AP
        within the current band's coverage.
        """
        return bool(user.get("nearest_ap"))

    # ====================================================================
    # GREEDY REDISTRIBUTION
    # ====================================================================
    def apply_greedy(self):
        """
        Greedy load balancing with REAL NETWORK LOAD BEHAVIOR.
        - Only IN-BAND users (by current_band) are considered
        - Load decays slowly (enterprise-style smoothing)
        """

        # ✅ 1. Restrict to in-band users only
        active_users = [u for u in self.clients if u.get("nearest_ap")]

        # If nobody is in range, just decay loads and bail
        if not active_users:
            LOAD_DECAY = 0.82
            for ap in self.aps:
                ap["load"] = max(0, ap.get("load", 0) * LOAD_DECAY)
                ap["connected_clients"] = []
            return

        # ✅ 2. Run greedy ONLY on in-band users
        GreedyRedistributor(self.aps, active_users).redistribute()

        # After greedy.assignments:
        for user in active_users:
            ap_id = user.get("assigned_ap")
            if ap_id:
                user["connected_ap"] = ap_id

        # ✅ 3. Prepare smoother load logic
        LOAD_DECAY = 0.82          # 82% of previous load kept each tick
        LOAD_GAIN_WEIGHT = 0.40    # 40% from new instantaneous load

        # Count new instantaneous load
        new_loads = {ap["id"]: 0 for ap in self.aps}

        for user in active_users:
            aid = user.get("assigned_ap")
            if not aid:
                continue
            new_loads[aid] += user.get("airtime_usage", 1)

        # Apply smoothing & update lists
        for ap in self.aps:
            ap_id = ap["id"]
            prev_load = ap.get("load", 0)
            instant_load = new_loads.get(ap_id, 0)

            smoothed = prev_load * LOAD_DECAY + instant_load * LOAD_GAIN_WEIGHT

            ap["load"] = max(0, min(smoothed, 100))

            ap["connected_clients"] = [
                u["id"]
                for u in active_users
                if (u.get("assigned_ap") or u.get("nearest_ap")) == ap_id
            ]



    # ====================================================================
    # ADD/REMOVE USERS (FLOOR-SAFE, NO CORRIDOR/STAIRCASE SPAWN)
    # ====================================================================
    def _filter_spawn_rooms(self, rooms):
        """
        Filter out corridors, staircases, tiny rooms etc to avoid weird geometry.
        """
        block_tokens = ["corridor", "stair", "lift", "toilet", "washroom", "wc"]
        valid = []
        for r in rooms:
            name = r["name"].lower()
            if any(tok in name for tok in block_tokens):
                continue
            if r["width"] < 25 or r["height"] < 25:
                continue
            valid.append(r)
        return valid

    def add_user_to_floor(self, floor: int):
        """Add user to specified floor with capacity & spawn-room checks."""
        # All rooms on this floor
        rooms = [
            r for f in self.campus_layout
            if f["level"] == floor
            for r in f["rooms"]
        ]
        if not rooms:
            print(f"⚠️ No rooms on floor {floor}")
            return

        # Filter to spawnable rooms (no corridor/staircase, min size)
        spawn_rooms = self._filter_spawn_rooms(rooms)
        if not spawn_rooms:
            print(f"⚠️ No valid spawn rooms on floor {floor}")
            return

        # Check floor capacity (simple hard cap)
        users_on_floor = sum(1 for u in self.clients if u.get("floor") == floor)
        MAX_FLOOR_CAP = 90
        if users_on_floor >= MAX_FLOOR_CAP:
            print(f"⚠️ Floor {floor} at capacity ({users_on_floor}/{MAX_FLOOR_CAP})")
            return

        room = random.choice(spawn_rooms)

        # Safe position within room
        x1, y1 = room["x"] + 5, room["y"] + 5
        x2 = room["x"] + room["width"] - 5
        y2 = room["y"] + room["height"] - 5

        new_user = {
            "id": f"User_{random.randint(100000, 999999)}",
            "floor": floor,
            "room": room["name"],
            "x": random.uniform(x1, x2),
            "y": random.uniform(y1, y2),
            "vx": random.uniform(-1, 1),
            "vy": random.uniform(-1, 1),
            "airtime_usage": random.randint(1, 5),
            "nearest_ap": None,
            "assigned_ap": None,
            "connected_ap": None,
            "RSSI": -95,
        }

        self.clients.append(new_user)
        print(f"✅ Added user {new_user['id']} in {room['name']} on floor {floor}")

    def remove_user_from_floor(self, floor: int):
        """Remove random user from specified floor."""
        users_on_floor = [u for u in self.clients if u.get("floor") == floor]

        if not users_on_floor:
            print(f"⚠️ No users on floor {floor}")
            return

        user = random.choice(users_on_floor)
        user_id = user["id"]

        # Clean up all references
        try:
            self.clients.remove(user)

            # Remove from assignments
            self.assignments.pop(user_id, None)

            # Remove from AP lists
            for ap in self.aps:
                if user_id in ap.get("connected_clients", []):
                    ap["connected_clients"].remove(user_id)
                    ap["load"] = max(
                        0,
                        ap["load"] - user.get("airtime_usage", 1)
                    )

            print(f"✅ Removed user {user_id} from floor {floor}")

        except ValueError:
            print(f"⚠️ User {user_id} already removed")

    # ====================================================================
    # MAIN TICK LOOP  🔥 NO-BLOCKING VERSION
    # ====================================================================
    def step(self):
        """
        Execute one simulation step.

        IMPORTANT:
        - Always lightweight for the realtime loop.
        - For the live WebSocket viz, we *always* run greedy.
        - MCMF is reserved for offline / controlled use (USE_MCMF flag).
        """
        try:
            # 1. Move users
            self.move_users()

            # 2. Update RSSI & AP loads
            self.update_rssi()
            self.update_ap_load()

            # 3. Load balancing:
            #    For realtime animation → GREEDY ONLY (no blocking).
            #    If you ever want to demo MCMF, flip USE_MCMF = True
            #    at the top and keep user count modest.
            if USE_MCMF and len(self.clients) <= MCMF_MAX_USERS and (self.tick % MCMF_EVERY_N_TICKS == 0):
                self.apply_mcmf()
            else:
                self.apply_greedy()

            self.tick += 1

        except Exception as e:
            print(f"🔥 Error in step(): {e}")
            import traceback
            traceback.print_exc()
        
        # 4. AP-Killer effect
        if self.ap_killer.active:
            rooms = [r for f in self.campus_layout if f["level"] == self.ap_killer.floor for r in f["rooms"]]
            self.ap_killer.update(self.aps, rooms)




    # ====================================================================
    # COORD TRANSFORM (BACKEND VIEW -> FRONTEND GLOBAL)
    # ====================================================================
    def to_global(self, floor, x, y):
        """
        Keep this consistent but we will still sanitize in get_state
        to avoid NaNs hitting JSON.
        """
        floors_sorted = sorted(self.campus_layout, key=lambda f: -f["level"])
        index = next((i for i, f in enumerate(floors_sorted) if f["level"] == floor), None)
        if index is None:
            return x, y

        margin = 20
        floor_height = 350

        top = margin + index * (floor_height + margin)
        return x + margin, top + y

    # ====================================================================
    # STATE EXPORT (FULLY SANITIZED FOR JSON)
    # ====================================================================
    def get_state(self):
        try:
            # --- Pre-compute RSSI lists per AP ---
            aps_out = []
            for ap in self.aps:
                gx, gy = self.to_global(ap.get("floor"), ap.get("x"), ap.get("y"))

                ap_copy = {
                    "id": ap.get("id"),
                    "floor": ap.get("floor"),
                    "room": ap.get("room", "Corridor"),
                    "x": safe_float(ap.get("x", 0.0)),
                    "y": safe_float(ap.get("y", 0.0)),
                    "_gx": safe_float(gx),
                    "_gy": safe_float(gy),
                    "channel": ap.get("channel"),
                    "band": ap.get("band", self.current_band),
                    "interference_score": safe_float(ap.get("interference_score", 0.0)),
                    "airtime_capacity": safe_int(ap.get("airtime_capacity", 100)),
                    "max_clients": safe_int(ap.get("max_clients", ap.get("max_users", 30))),
                    "max_users": safe_int(ap.get("max_users", ap.get("max_clients", 30))),
                    "coverage_radius": safe_float(ap.get("coverage_radius", 200.0)),
                    "client_count": safe_int(ap.get("client_count", 0)),
                    "user_count": safe_int(ap.get("user_count", 0)),
                    "load": safe_float(ap.get("load", 0.0)),
                }

                aps_out.append(ap_copy)



            # --------------------------
            # USER LIST
            # --------------------------
            users_out = []

            visible_users = [
                u for u in self.clients
                if u.get("assigned_ap") is not None or u.get("nearest_ap") is not None
            ]

            for u in visible_users:
                gx, gy = self.to_global(u.get("floor"), u.get("x"), u.get("y"))

                u_copy = {
                    "id": u.get("id"),
                    "floor": u.get("floor"),
                    "room": u.get("room", ""),
                    "x": safe_float(u.get("x", 0.0)),
                    "y": safe_float(u.get("y", 0.0)),
                    "_gx": safe_float(gx),
                    "_gy": safe_float(gy),
                    "vx": safe_float(u.get("vx", 0.0)),
                    "vy": safe_float(u.get("vy", 0.0)),
                    "nearest_ap": u.get("nearest_ap"),
                    "assigned_ap": u.get("assigned_ap"),
                    "connected_ap": u.get("connected_ap"),
                    "airtime_usage": safe_int(u.get("airtime_usage", 1)),
                    "RSSI": safe_int(u.get("RSSI", -95)),
                }

                users_out.append(u_copy)
            # --------------------------
            # AP-KILLER (added ONCE)
            # --------------------------
            if self.ap_killer.active:
                gx, gy = self.to_global(
                    self.ap_killer.floor,
                    self.ap_killer.x,
                    self.ap_killer.y
                )

                users_out.append({
                    "id": "AP-KILLER",
                    "floor": self.ap_killer.floor,
                    "room": "Corridor",
                    "x": self.ap_killer.x,
                    "y": self.ap_killer.y,
                    "_gx": gx,
                    "_gy": gy,
                    "vx": self.ap_killer.vx,
                    "vy": self.ap_killer.vy,
                    "nearest_ap": self.ap_killer.get_nearest_ap_id(self.aps),
                    "assigned_ap": None,
                    "connected_ap": None,
                    "airtime_usage": 10,
                    "RSSI": -20
                })

            # --------------------------
            # FINAL RETURN
            # --------------------------
            return {
                "aps": aps_out,
                "clients": users_out,
                "assignments": self.assignments,
                "alarms": self.ap_alarms,
            }

        except Exception as e:
            print("STATE ERROR:", e)
            import traceback
            traceback.print_exc()
            return {
                "aps": [],
                "clients": [],
                "assignments": {},
                "alarms": [],
            }

