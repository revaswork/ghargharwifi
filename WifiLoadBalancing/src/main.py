import asyncio
import json
from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware

from simulation.simulator import WifiSimulator   # ✅ correct path


app = FastAPI()

# -------------------------------------------------------------
# CORS (required because frontend runs on Live Server :5500)
# -------------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],      # allow frontend
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -------------------------------------------------------------
# Initialize simulator
# -------------------------------------------------------------
sim = WifiSimulator()

# Global store of WebSocket connections
websockets = set()

# -------------------------------------------------------------
# Background Task – sends updates every second
# -------------------------------------------------------------
async def simulator_loop():
    while True:
        sim.step()  # update AP loads + move users + update RSSI

        state = sim.get_state()  # { "aps": [...], "clients": [...] }
        message = json.dumps(state)

        # broadcast to all web sockets
        remove_list = []
        for ws in websockets:
            try:
                await ws.send_text(message)
            except:
                remove_list.append(ws)

        for ws in remove_list:
            websockets.remove(ws)

        await asyncio.sleep(1)

# -------------------------------------------------------------
# WebSocket endpoint (frontend subscribes here)
# -------------------------------------------------------------
@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await ws.accept()
    websockets.add(ws)

    try:
        while True:
            await ws.receive_text()  # (not used, keeps connection alive)
    except:
        websockets.remove(ws)

# -------------------------------------------------------------
# Startup event starts simulation loop
# -------------------------------------------------------------
@app.on_event("startup")
async def startup_event():
    asyncio.create_task(simulator_loop())

# -------------------------------------------------------------
# Simple test API endpoint
# -------------------------------------------------------------
@app.get("/status")
def get_status():
    return {"status": "backend running", "clients": len(sim.clients)}
