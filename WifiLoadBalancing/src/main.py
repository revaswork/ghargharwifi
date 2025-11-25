import asyncio
import json
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from simulation.simulator import WifiSimulator
from pathlib import Path
from fastapi import Request

# ============================================================
# GLOBAL STATE
# ============================================================
sim: WifiSimulator = None
websockets: set[WebSocket] = set()
sim_task: asyncio.Task | None = None
sim_running: bool = False


# ============================================================
# CLEAN & FAST BROADCAST
# ============================================================
async def broadcast(payload: str):
    if not websockets:
        return
    
    dead = []
    coros = []

    for ws in websockets:
        coros.append(_safe_send(ws, payload, dead))

    await asyncio.gather(*coros, return_exceptions=True)

    for ws in dead:
        websockets.discard(ws)
        print("🔌 WS removed; total =", len(websockets))


async def _safe_send(ws: WebSocket, payload: str, dead_list: list):
    try:
        await ws.send_text(payload)
    except:
        dead_list.append(ws)


# ============================================================
# BACKGROUND SIMULATION LOOP
# ============================================================
async def simulator_loop():
    global sim_running

    print("SIM LOOP STARTED")
    sim.ready = False
    loop = asyncio.get_running_loop()

    while sim_running:
        # STEP 1: sim tick off main loop
        try:
            await loop.run_in_executor(None, sim.step)
        except Exception as e:
            print("🔥 Simulator step error:", e)
            await asyncio.sleep(0.5)
            continue

        # STEP 2: serialize safely
        try:
            state = sim.get_state()
            payload = {"type": "state", "data": state}

            state_json = await loop.run_in_executor(
                None, lambda: json.dumps(payload, ensure_ascii=False)
            )
        except Exception as e:
            print("🔥 Serialization error:", e)
            await asyncio.sleep(1)
            continue

        # STEP 3: broadcast
        await broadcast(state_json)

        # ⭐ BEST FIX ⭐
        await asyncio.sleep(0.2)   # <-- make this lighter

    print("SIM LOOP STOPPED")


# ============================================================
# LIFESPAN (startup + shutdown)
# ============================================================
@asynccontextmanager
async def lifespan(app: FastAPI):
    global sim, sim_task, sim_running

    print("\n=== BACKEND STARTING ===")

    sim = WifiSimulator()
    sim.ready = False

    sim_running = True
    sim_task = asyncio.create_task(simulator_loop())

    await asyncio.sleep(0.5)
    sim.ready = True

    print("READY ✓")
    print(f"APs: {len(sim.aps)}, Users: {len(sim.clients)}")
    print("========================\n")

    yield

    # ----- CLEAN SHUTDOWN -----
    print("\n=== BACKEND SHUTTING DOWN ===")
    sim_running = False

    if sim_task:
        sim_task.cancel()
        try:
            await sim_task
        except:
            pass

    for ws in list(websockets):
        try:
            await ws.close()
        except:
            pass

    websockets.clear()

    print("CLEAN SHUTDOWN ✓")
    print("========================\n")


# ============================================================
# FASTAPI APP
# ============================================================
app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


DATA_DIR = Path(__file__).resolve().parents[1] / "data"
CONFIG_PATH = DATA_DIR / "config.json"

@app.post("/set_band")
def set_band(band: str):
    if band not in ["2.4", "5", "6"]:
        return {"error": "Invalid band"}
    CONFIG_PATH.write_text(json.dumps({"default_band": band}, indent=4))
    return {"status": "ok", "band": band}
# ============================================================
# ROUTES
# ============================================================
@app.get("/")
async def root():
    return {"status": "online", "service": "wifi-simulator"}


@app.get("/status")
async def get_status():
    if not sim:
        return {"status": "initializing"}

    return {
        "status": "running" if sim_running else "stopped",
        "ready": sim.ready,
        "aps": len(sim.aps),
        "clients": len(sim.clients),
        "websockets": len(websockets),
        "tick": sim.tick,
    }


@app.get("/state")
async def get_state():
    if not sim.ready:
        return JSONResponse(
            status_code=503,
            content={"error": "Simulator not ready"}
        )
    return sim.get_state()


# ============================================================
# WEBSOCKET ENDPOINT (NON-BLOCKING)
# ============================================================
@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await ws.accept()
    websockets.add(ws)
    print("WS CONNECTED, total =", len(websockets))

    try:
        while True:
            # read ping/keepalive so buffer doesn't fill
            await ws.receive_text()
    except WebSocketDisconnect:
        pass
    except:
        pass
    finally:
        websockets.discard(ws)
        print("WS DISCONNECTED, total =", len(websockets))


# ============================================================
# USER MANAGEMENT
# ============================================================
@app.post("/floor/{floor}/add_user")
async def add_user(floor: int):
    sim.add_user_to_floor(floor)
    return {"status": "ok", "floor": floor}


@app.post("/floor/{floor}/remove_user")
async def remove_user(floor: int):
    sim.remove_user_from_floor(floor)
    return {"status": "ok", "floor": floor}

@app.post("/apkiller/deploy")
async def deploy_apkiller():
    sim.ap_killer.deploy()
    return {"status": "deployed"}

@app.post("/apkiller/withdraw")
async def withdraw_apkiller():
    sim.ap_killer.withdraw()
    return {"status": "removed"}

@app.post("/apkiller/floor/{level}")
async def move_apkiller(level: int):
    sim.ap_killer.set_floor(level)
    return {"status": "moved", "floor": level}

@app.post("/apkiller/move")
async def move_apkiller(data: dict):
    sim.ap_killer.vx = data.get("vx", 0) * 6
    sim.ap_killer.vy = data.get("vy", 0) * 6
    return {"status": "ok"}

@app.post("/setband")
async def setband(request: Request):
    data = await request.json()
    band = data["band"]

    # Set global band
    sim.current_band = band

    # 🔥 FORCE band into every AP
    for ap in sim.aps:
        ap["band"] = band
        ap["coverage_radius"] = sim.band_coverage[band]

    return {"status": "ok", "band": band}

# ============================================================
# DIRECT RUN
# ============================================================
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        log_level="info",
        reload=True
    )
