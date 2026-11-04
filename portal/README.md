# DELTASTREAM AI – Compliance Portal

Web portal for the DeltaStream AI compliance demo. Separate agents discover the
virtual utility devices in `devices/`, check their compliance and feed the
portal pages. Nothing about the devices is hardcoded.

## Milestones

| Milestone | Scope | Status |
|---|---|---|
| **1. Devices page** | Discovery Agent, global search (sector / location / company), device status, firmware, compliance verdict, standards violated | ✅ Delivered |
| **2. Non-Compliance page** | Full compliance report per device with Compliant, Partially compliant, Needs change control and Non-compliant | 🔎 Ready for review |
| **3. Compliance page (AI)** | AI agent: check version → check firmware repository → apply update → reboot → re-check → report | 🔎 Ready for review |

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

## What the Non-Compliance page does

Same flow: choose Sector, Location and Company, press **Run agent**. The
**Compliance Agent** checks every device and gives it one of four statuses
(the worst condition wins):

| Status | When |
|---|---|
| **Non-compliant** | Device unreachable, or any *critical* finding (e.g. no authentication, reusable passwords) |
| **Needs change control** | Firmware differs from the approved baseline: a controlled firmware update is needed (NERC CIP-010-4) |
| **Partially compliant** | Only *high* or *medium* findings |
| **Compliant** | No findings |

Each device card shows its findings with severity, the standards violated and
the remediation. Click a status count to show only those devices; the global
search also filters the report. The same status appears in the **Compliant**
column of the Devices page.

The approved firmware per device type is in `portal/backend/firmware_repository.json`
(example values: replace them with your vendor's releases).

## What the Compliance page does

Choose Sector, Location and Company, press **Run agent**. The **AI Remediation
Agent** takes every device that is not Compliant and, on its own:

1. **Check version**: reads the firmware the device runs.
2. **Check repository**: finds the approved firmware that fixes its findings.
3. **Apply update**: installs it.
4. **Reboot**: restarts the device and waits until it answers again.
5. **Re-check**: runs the compliance checks again.
6. **Report**: shows each device *before → after*.

Each device's steps light up live while the agent works. Devices that **Need
change control are never remediated**: changing their firmware needs an
approved change request first (NERC CIP-010-4), so the agent only flags them
as *Change approval required*.

Result with the virtual devices: 5 of 6 devices become Compliant; the RTU stays
*Needs change control*. **Undo updates and start again** restores the original
state (so does restarting the portal).

> The virtual devices can't really be re-flashed, so an installed update is
> kept by the portal and applied on every check (the Devices and Non-Compliance
> pages show it too). The reboot check is real. With real devices, the
> "apply update" step calls the vendor's update interface instead.

### Agents

| Agent | Job | Shown on |
|---|---|---|
| **Discovery Agent** | Scans each provisioned site, recognises every device, reads its firmware and checks whether it is online | Devices page |
| **Compliance Agent** | Checks every discovered device against the compliance rules, the approved firmware baseline and the standards it violates | Non-Compliance page; Devices page (Compliant + Standard & Requirement Violated columns) |
| **AI Remediation Agent** | Updates non-compliant devices to approved firmware from the repository, reboots and re-checks them; skips devices that need change control | Compliance page |

The Discovery and Compliance Agents only read what a device reveals; they never log in or send commands.

### Standards violated

From the non-compliance table provided by the client:

| Non-compliance vector | Standard & requirement | Devices |
|---|---|---|
| Plain-Text Telemetry | NERC CIP-012-2 (Data Protection in Transit) | PLC, RTU, terminal server, DER gateway, IoT sensor |
| Hardcoded/Default Credentials | IEC 62443-4-2 (Identification & Access Control) | PDU, DER gateway, IoT sensor |
| Missing Audit Logging | NERC CIP-007 & CIP-015 (Internal Network Monitoring) | PLC |
| Unrestricted Remote Access | NERC CIP-003-9 (Vendor Electronic Access Control) | Terminal server |
| Unapproved Firmware Baseline | NERC CIP-010-4 (Configuration Change Management) | Any device whose firmware differs from the approved baseline |

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
git switch development      # not "git checkout": the repo also has a folder named development

# Already cloned? Update instead:
#   git fetch origin && git switch development && git pull origin development

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
3. Every device shows its compliance status and the standards it violates.
4. Stop one device (e.g. the PLC) and press **Run agent** again → it shows *Offline*.
5. Type `modbus` in Global search → only the PLC and RTU remain.
6. Open **Non-Compliance** and press **Run agent** → 2 Non-compliant (PLC, PDU),
   1 Needs change control (RTU), 3 Partially compliant (terminal server,
   DER gateway, IoT sensor). Click a count to filter the cards.
7. Open **Compliance** and press **Run agent** → each device's steps light up;
   at the end 5 of 6 are Compliant and the RTU shows *Change approval required*.
   **Undo updates and start again** resets the demo.

### Stop

`Ctrl + C` in Terminal 2. In Terminal 1 run `kill %1 %2 %3 %4 %5 %6`
(Windows: close each device terminal).

### Troubleshooting

| Problem | Fix |
|---|---|
| `No module named uvicorn` (or fastapi, pymodbus, paho) | The environment is not active. In `sector-utilities` run `source portal/.venv/bin/activate`, then `python -m uvicorn ...` (not `python3` from `/usr/bin`) |
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
  "mqtt_port": 1883,
  "device_names": { "terminal_server": "Eskom Terminal Server" }
}
```

`device_names` (optional) replaces the name a device reports with your own,
per device type. The sidebar's Environment box shows the selected company and
location.

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
      remediation_agent.py  AI Remediation Agent (update, reboot, re-check)
      store.py              Reports saved as JSON in backend/reports/
    config.py               Scan ports, timings (environment variables)
    sites.json              Provisioned sites
    firmware_repository.json  Approved and latest firmware per device type
    main.py                 API; runs the agents on demand
  frontend/src/
    pages/        DevicesPage, NonCompliancePage, CompliancePage
    components/   GlobalSearch, Dropdown, AgentPanel, Sidebar, badges and cards
    context/      FilterContext (global search shared by all pages)
    hooks/        usePolling, useDevices, useCompliance, useRemediation, useAgent
```

API:

```
GET  /api/devices               Discovery report + compliance verdict and standards violated
GET  /api/filters               Sector / location / company options
GET  /api/compliance            Compliance Agent report
GET  /api/remediation           AI Remediation Agent report
POST /api/remediation/reset     Undo the agent's firmware updates
GET  /api/agents                Status and live activity of every agent
POST /api/agents/{name}/run     Run "discovery", "compliance" or "remediation" now
```

## Configuration

| Variable | Default | Purpose |
|---|---|---|
| `SCAN_PORTS` | `502,4000-4010,5020-5030,8502` | Ports the Discovery Agent checks |
| `LISTEN_SECONDS` | `8` | How long agents listen to MQTT per run |
| `DISCOVERY_INTERVAL` | `0` | Seconds between automatic discovery runs (0 = only when "Run agent" is pressed, plus once at start-up) |
| `COMPLIANCE_INTERVAL` | `0` | Seconds between automatic compliance runs |
| `SITES_FILE` | `backend/sites.json` | Provisioned sites |
| `FIRMWARE_REPOSITORY_FILE` | `backend/firmware_repository.json` | Approved and latest firmware per device type |
| `REMEDIATION_STEP_SECONDS` | `0.8` | Pause per remediation step, so the flow can be followed live |
| `KEEP_REMEDIATION` | `0` | `1` keeps installed updates after a restart |

## Notes

- The PDU only reveals its firmware after login, so it shows "Requires login".
- The IoT sensor reports firmware in a heartbeat every ~20 s; it appears after
  a discovery run that hears one and is remembered afterwards.
- `devices/modbus-to-mqtt.py` is not part of the demo: it targets an external
  device (192.168.1.100) and a public MQTT broker.
