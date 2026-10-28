# DELTASTREAM AI – Compliance Portal

Web portal for the DeltaStream AI compliance demo. Separate agents discover the
virtual utility devices in `devices/`, check their compliance and feed the
portal pages. Nothing about the devices is hardcoded.

## Milestones

| Milestone | Scope | Status |
|---|---|---|
| **1. Devices page** | Discovery Agent, global search (sector / location / company), device status, firmware, compliance verdict, standards violated | ✅ Delivered |
| 2. Non-Compliance page | Full compliance report per device with Compliant, Partially compliant, Needs change control and Non-compliant | Planned |
| 3. Compliance page (AI) | AI agent: check version → check firmware repository → apply update → reboot → re-check → report | Planned |

## What the Devices page does

1. Choose **Sector**, **Location** and **Company** at the top (type to search
   or scroll the list). The page stays empty until all three are chosen.
2. **Run agent** becomes active. Pressing it starts the **Discovery Agent**,
   whose steps appear live.
3. The page then shows the devices provisioned for that site:
   name, type, protocol, endpoint, firmware, **Compliant**,
   **Standard & Requirement Violated**, live status and last seen.
4. Changing a dropdown hides the results until the agent is run again.

Works on desktop, tablet and mobile (devices are shown as cards on smaller screens).

### Agents

| Agent | Job | Shown on |
|---|---|---|
| **Discovery Agent** | Scans each provisioned site, recognises every device, reads its firmware and checks whether it is online | Devices page |
| **Compliance Agent** | Checks every discovered device against the compliance rules and the standards it violates | Devices page (Compliant + Standard & Requirement Violated columns) |

Agents only read what a device reveals; they never log in or send commands.

### Standards violated

From the non-compliance table provided by the client:

| Non-compliance vector | Standard & requirement | Devices |
|---|---|---|
| Plain-Text Telemetry | NERC CIP-012-2 (Data Protection in Transit) | PLC, RTU, terminal server, DER gateway, IoT sensor |
| Hardcoded/Default Credentials | IEC 62443-4-2 (Identification & Access Control) | PDU, DER gateway, IoT sensor |
| Missing Audit Logging | NERC CIP-007 & CIP-015 (Internal Network Monitoring) | PLC |
| Unrestricted Remote Access | NERC CIP-003-9 (Vendor Electronic Access Control) | Terminal server |

## Run it on your machine

### 1. Install (once)

You need **Git**, **Python 3.10+**, **Node.js 20+** and **Mosquitto** (MQTT broker).

Ubuntu / WSL:

```bash
sudo apt update
sudo apt install -y git python3 python3-venv python3-pip mosquitto
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt install -y nodejs
sudo service mosquitto start
```

Windows: install Git, Python 3.12, Node.js 20 LTS and Mosquitto from their
official websites (Mosquitto runs as a Windows service).

### 2. Get the code and dependencies (once)

```bash
git clone https://github.com/adriaaneyer1/sector-utilities.git
cd sector-utilities
git checkout development

python3 -m venv portal/.venv
source portal/.venv/bin/activate   # Windows: portal\.venv\Scripts\activate
pip install -r portal/backend/requirements.txt

cd portal/frontend
npm install
npm run build
cd ../..
```

### 3. Run

In every new terminal, go to `sector-utilities` and activate the environment
first: `source portal/.venv/bin/activate` (Windows: `portal\.venv\Scripts\activate`).

**Terminal 1 – virtual devices:**

```bash
for d in plc rtu pdu terminal-server der-gateway iot; do python devices/$d.py & done
```

Windows: start each in its own terminal, e.g. `python devices\plc.py`.

**Terminal 2 – portal and agents:**

```bash
cd portal/backend
python -m uvicorn main:app --host 127.0.0.1 --port 8000
```

Open **http://localhost:8000/devices**.

### 4. Check it works

1. Select **Utilities**, **South Africa**, **Eskom** → **Run agent** turns orange.
2. Press **Run agent** → the agent's steps appear, then 6 devices, all *Online*
   (DER gateway and IoT sensor show *Streaming*).
3. Every device shows **Non-Compliant** and the standards it violates.
4. Stop one device (e.g. the PLC) and press **Run agent** again → it shows *Offline*.
5. Type `modbus` in Global search → only the PLC and RTU remain.

### Stop

`Ctrl + C` in Terminal 2. In Terminal 1 run `kill %1 %2 %3 %4 %5 %6`
(Windows: close each device terminal).

### Troubleshooting

| Problem | Fix |
|---|---|
| "Address already in use" | An earlier run is still active; stop it and start again |
| DER / IoT show "No data stream" | Check Mosquitto is running (`sudo service mosquitto status`) |
| No devices after Run agent | Check the device scripts are running in Terminal 1 |
| Old page design | Hard refresh the browser (`Ctrl + F5`) |

## Adding companies, locations and sectors

Sites live in `portal/backend/sites.json`. Each entry says which network
belongs to which company, sector and location; every device found there is
provisioned to it. Add an entry and it appears in the dropdowns.

```json
{
  "company": "Eskom",
  "sector": "Utilities",
  "location": "South Africa",
  "scan_host": "127.0.0.1",
  "mqtt_broker": "127.0.0.1",
  "mqtt_port": 1883
}
```

## Project layout

```
portal/
  backend/
    agents/
      base.py               Agent base class: run, live step log, save report
      probes.py             How to talk to devices: console, Modbus, MQTT
      fingerprints.py       How devices are recognised (add a class for a new type)
      discovery_agent.py    Discovery Agent
      compliance_agent.py   Compliance Agent, rule sets and standards violated
      store.py              Reports saved as JSON in backend/reports/
    config.py               Scan ports, timings (environment variables)
    sites.json              Provisioned sites
    main.py                 API; runs the agents on demand
  frontend/src/
    pages/        DevicesPage, NonCompliancePage (M2), CompliancePage (M3)
    components/   GlobalSearch, Dropdown, AgentPanel, Sidebar, badges and cards
    context/      FilterContext (global search shared by all pages)
    hooks/        usePolling, useDevices, useAgent
```

API:

```
GET  /api/devices               Discovery report + compliance verdict and standards violated
GET  /api/filters               Sector / location / company options
GET  /api/compliance            Compliance Agent report
GET  /api/agents                Status and live activity of both agents
POST /api/agents/{name}/run     Run "discovery" or "compliance" now
```

## Configuration

| Variable | Default | Purpose |
|---|---|---|
| `SCAN_PORTS` | `502,4000-4010,5020-5030,8502` | Ports the Discovery Agent checks |
| `LISTEN_SECONDS` | `8` | How long agents listen to MQTT per run |
| `DISCOVERY_INTERVAL` | `0` | Seconds between automatic discovery runs (0 = only when "Run agent" is pressed, plus once at start-up) |
| `COMPLIANCE_INTERVAL` | `0` | Seconds between automatic compliance runs |
| `SITES_FILE` | `backend/sites.json` | Provisioned sites |

## Notes

- The PDU only reveals its firmware after login, so it shows "Requires login".
- The IoT sensor reports firmware in a heartbeat every ~20 s; it appears after
  a discovery run that hears one and is remembered afterwards.
- `devices/modbus-to-mqtt.py` is not part of the demo: it targets an external
  device (192.168.1.100) and a public MQTT broker.
