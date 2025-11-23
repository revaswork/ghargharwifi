📌 Project Title:

Campus WiFi Load Balancing Using Advanced Algorithms

🏫 Course:

Advanced Algorithms

👥 Team Members:

Reva Shukla — Algorithm Lead (MCMF, Graph Model, Cost Function)

Niyati — Simulation Lead (Movement, RSSI, AP Load)

Meet — Load Balancing Lead (Greedy Redistribution, Priority Queue)

🚀 Project Overview

Large university campuses have multiple WiFi access points (APs).
Students automatically connect to the nearest AP, causing:

Some APs to overload

Other APs to remain underutilized

Poor bandwidth and unstable connectivity

Our system solves this by implementing:

✔ Minimum-Cost Maximum Flow (MCMF)

For globally optimal user → AP assignment.

✔ Greedy Load Redistribution

For fast real-time adjustments when APs overload.

✔ Priority Queue (Min-Heap)

To efficiently select which users to move.

✔ Dynamic Simulation + Live Visualization

Using WebSockets + D3.js to show real-time movement & load changes.


System Architecture

 Users Move → RSSI Changes → AP Load Changes →
     ↓               ↓               ↓
        Simulation Layer (Niyati)
     ↓               ↓               ↓
 Graph & Cost Model (Reva) → MCMF (Optimal Assignment)
     ↓
 Greedy PQ Balancing (Meet) → Fix Overloads
     ↓
 WebSocket Backend (Reva)
     ↓
 D3.js Frontend (Live Visualization)




Core Components
1️⃣ Simulation Layer (Niyati)

Handles real-world WiFi dynamics:

User movement

RSSI calculation (based on distance and path loss formula)

AP airtime and load calculation

State updates every simulation tick

This layer feeds live data into the algorithms.

2️⃣ Algorithm Layer (Reva & Meet)
🔹 Minimum-Cost Maximum Flow (Reva)

Builds a flow network:

Source → Users → APs → Sink


Cost includes:

Distance

RSSI penalty

Airtime usage

Sticky client penalty

Channel interference

MCMF produces globally optimal AP assignments.

🔹 Greedy Load Redistribution (Meet)

Runs between MCMF steps.

Detect overloaded APs

Push affected users into a priority queue

Move weakest users (low RSSI / high usage)

Select nearest alternative AP with free capacity

Fast and efficient for real-time stability.

3️⃣ Frontend Visualization Layer

Interactive dashboard using D3.js:

Live moving users

AP coverage circles

AP colors based on load

Lines from users → assigned AP

Tooltips with RSSI, load, airtime, channel, etc.

WebSocket data every second

Gives a real-time view of network balancing.

🗂️ Folder Structure
WifiLoadBalancing/
│
├── frontend/                 # D3.js Live Visualization UI
│   ├── index.html
│   └── data/
│        ├── aps.json
│        └── users.json
│
├── src/
│   ├── main.py               # WebSocket backend (runs simulation)
│   ├── run_simulation.py     # Offline algorithm testing
│   │
│   ├── simulation/
│   │   ├── simulator.py      # Niyati's simulation engine
│   │   ├── movement_generator.py
│   │   ├── environment_config.py
│   │   └── metrics.py
│   │
│   ├── algorithms/
│   │   ├── graph_model.py            # Reva's flow network
│   │   ├── mcmf.py                   # Reva's MCMF implementation
│   │   ├── cost_function.py          # Joint cost logic
│   │   ├── greedy_redistribution.py  # Meet’s load balancing
│   │   └── priority_queue.py         # Meet’s PQ logic
│   │
│   └── utils/
│       ├── file_loader.py
│       ├── random_data_generator.py
│       └── visualization.py
│
├── data/                     # Initial backend input
│   ├── aps.json
│   ├── users.json
│   └── config.json
│
├── results/                  # Simulation outputs
│
└── README.md

🧪 How to Run the Project
✔ Backend (FastAPI WebSocket)
cd WifiLoadBalancing
source venv/bin/activate  (or venv\Scripts\activate on Windows)
python src/main.py


Backend runs on:

http://127.0.0.1:8000


WebSocket endpoint:

ws://127.0.0.1:8000/ws

✔ Frontend (D3.js Visualization)
cd WifiLoadBalancing/frontend
python -m http.server


Open in browser:

http://127.0.0.1:8000/index.html
