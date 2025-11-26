# 📡 WiFi Congestion Balancing System  
<p align="center"><img alt="HTML" src="https://img.shields.io/badge/HTML5-E34F26?logo=html5&logoColor=white">
<img alt="Python" src="https://img.shields.io/badge/python-3.10+-yellow"> </p>
### Intelligent Multi-Floor AP Load Distribution • Real-time Visualization • Algorithmic Network Simulation

This project simulates and visualizes **WiFi Access Point congestion** across a multi-floor campus using advanced algorithms, live WebSocket updates, and an interactive D3.js interface.

It solves the common problem found in real universities:  
> *“Everyone connects to the closest AP → a few APs explode with load while others sit idle.”*

This system balances users intelligently across APs in real time, visualizes their movement, and evaluates dynamic network health.

---

## 🚀 Features

### **🔧 Backend Simulation**
- Real multi-floor environment with 7 floors & dozens of rooms  
- Intelligent user placement & movement  
- Access Point constraints (band, airtime, load, capacity)  
- RSSI-based AP selection  
- Band-based coverage simulation (2.4 / 5 / 6 GHz)  
- Dynamic AP reassignment  
- Live WebSocket state updates (every 0.2 seconds)

### **📊 Frontend Visualization**
- Full-campus multi-floor SVG visualization  
- Animated WiFi coverage rings  
- Live user movement trails  
- Dotted lines showing user–AP associations  
- Sidebar floor dashboard (load per floor, user count)  
- AP-Killer (test tool) that floods APs with load  
- Heatmap mode for user density  
- WebSocket live status & error panel  
- Glassmorphism UI with glowing AP nodes

### **🧠 Algorithms Integrated**
1. **Minimum-Cost Maximum Flow (MCMF)**  
2. **Greedy Load Redistribution**  
3. **Priority Queue–based Assignment**  
4. **Graph Modeling for AP Selection**

Used to distribute users across APs **optimally and fairly**.

---

## 🧱 Project Architecture
```
Wifi_Congestion_System/
│
├── WifiLoadBalancing
│ ├── data/
│ │ ├── aps.json # Access point definitions
│ │ ├── config.json # Default band, settings
│ │ └── users.json # Generated simulation users
│ │
│ ├── frontend/
│ │ ├── assets/bg.png
│ │ ├── data/campus_layout.json # Rooms, floors, coordinates
│ │ └── index.html # Full interactive visualization
│ │
│ ├── src/
│ │ ├── algorithms/
│ │ │ ├── cost_function.py
│ │ │ ├── graph_model.py
│ │ │ ├── greedy_redistribution.py
│ │ │ ├── mcmf.py
│ │ │ └── priority_queue.py
│ │ │
│ │ ├── simulation/
│ │ │ ├── simulator.py # Core simulation engine
│ │ │ ├── ap_killer.py # Load-attack tool
│ │ │ └── generate_initial_data.py# User & AP initialization script
│ │ │
│ │ └── main.py # FastAPI backend + websocket
│
├── requirements.txt
├── foldertree.py
└── runcode.txt
```
---

## ⚙️ How It Works

### **Backend (FastAPI + Python)**
- Runs a simulation loop (`simulator_loop`)  
- Updates user movement, AP load, connectivity  
- Calculates dynamic RSSI based on band + distance  
- Sends complete state via WebSocket to frontend  
- Exposes REST APIs to add/remove users, change band, move AP-Killer

### **Frontend (D3.js + TailwindCSS)**
- Renders the entire campus floor-by-floor  
- Updates AP load arcs and user movement in real time  
- Shows heatmap overlays for dense rooms  
- Lets you switch WiFi bands and visualize coverage drop  
- Provides debug logs + network status

---

## 🎮 Interaction Controls

| Feature | Control |
|--------|---------|
| Switch WiFi Band | Buttons: **2.4 / 5 / 6 GHz** |
| Move AP-Killer | `W A S D` keys |
| Deploy AP-Killer | Button in sidebar |
| Add user to a floor | Sidebar + button |
| Remove user | Sidebar – button |
| Zoom | + / – buttons |
| Pan | Mouse drag |

---

## 🖼️ Screenshots / Demo 

Floor Overview - Can add/subtract user from here and also check the load on that particular floor + the current number of users on that floor.

<img width="295" height="632" alt="Screenshot 2025-11-26 004702" src="https://github.com/user-attachments/assets/ebf54724-ed40-4eb1-8b9f-b40d9e5f64d5" />

A live status of all Users, Access points, Overloaded AP's, Average Load.

<img width="328" height="152" alt="Screenshot 2025-11-26 004709" src="https://github.com/user-attachments/assets/f3c1fdc1-6891-47e4-8847-0125110be028" />

Legend, Heatmap which shows which room has high or low user commotion, Debug Controls shows the console and has reconnect and Test API buttons for their respective purposes, 
AP-Killer deploy/recall switch, 3 types of Network Bands with their respective features, zoom in and zoom out buttons.

<img width="292" height="999" alt="Screenshot 2025-11-26 004731" src="https://github.com/user-attachments/assets/059ec417-e674-4ffc-a340-b77bc234ff62" />

Heatmap, Red - high commotion, Yellow - medium commotion, Green - low commotion

<img width="548" height="726" alt="image" src="https://github.com/user-attachments/assets/82480ea3-4aa8-4b71-b9d8-c83c1d16e144" />

AP-Killer in action. Its the movable user with a very high load that can be deployed, recalled, traversed to all the floors.

<img width="1143" height="494" alt="Screenshot 2025-11-26 004900" src="https://github.com/user-attachments/assets/6d98c71e-69bb-436d-b881-cdfaa56bc5a9" />

2.4GHz- Large range, low load, slow network flow (less internet speed)

<img width="725" height="960" alt="Screenshot 2025-11-26 005535" src="https://github.com/user-attachments/assets/14677bc5-1e97-4e45-acc1-01054d4200da" />

5GHz- Small range, high network flow (faster internet speed)

<img width="722" height="961" alt="Screenshot 2025-11-26 005542" src="https://github.com/user-attachments/assets/c2886680-8d0d-4566-aa95-5822486c74f4" />

6GHz- Smallest range almost like a 5 feet distance from the AP, Very high network flow (fastest internet speed) 

<img width="719" height="950" alt="Screenshot 2025-11-26 005551" src="https://github.com/user-attachments/assets/bc84fd61-0a41-492c-b2cd-141e1ef07081" />

Full frontend

<img width="1919" height="1079" alt="Screenshot 2025-11-26 004745" src="https://github.com/user-attachments/assets/4e6f0926-eed0-4905-ad92-120893d7e09b" />

## 🛠️ Setup Instructions

### **1. Install dependencies**
pip install -r requirements.txt

### **2. Generate initial data**
python WifiLoadBalancing/src/simulation/generate_initial_data.py


### **3. Run backend**
uvicorn WifiLoadBalancing.src.main:app --reload --port 8000

### **4. Open frontend**
Just open:
WifiLoadBalancing/frontend/index.html
(or serve using Live Server)

---

## 🎯 Future Improvements
- ML-based AP selection  
- Predictive load balancing  
- Building-wide roaming optimization  
- Real AP integration (UniFi / Cisco)  
- Admin dashboard with alerts

---

## 👨‍💻 Authors
**Meet Jain**  (Frontend, AP-Killer and Bandwidth Implementation)
- Email: meetjain1333@gmail.com
  
**Reva Shukla** (Backend, MCMF, Graph Model and Cost Function Implementation)

**Niyati Sardana** (Backend, Greedy Distribution and Priority Queue Implementation)

---

## ⭐ If you like this project…
Consider giving it a **★ star** on GitHub!

---
