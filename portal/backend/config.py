"""
Agent settings. Everything comes from environment variables so the same
agents can scan a local lab or devices on another network.

Sites (sites.json) say which company, sector and location each scanned
network belongs to: every device found there is provisioned to that site.
"""
import json
import os
from pathlib import Path


def _ports(spec):
    """'502,4000-4010' -> [502, 4000, ..., 4010]"""
    ports = []
    for part in spec.split(","):
        part = part.strip()
        if "-" in part:
            start, end = part.split("-")
            ports.extend(range(int(start), int(end) + 1))
        elif part:
            ports.append(int(part))
    return sorted(set(ports))


# Ports the Discovery Agent checks on every site's scan host
SCAN_PORTS = _ports(os.getenv("SCAN_PORTS", "502,4000-4010,5020-5030,8502"))

SITES_FILE = Path(os.getenv("SITES_FILE", Path(__file__).resolve().parent / "sites.json"))


def load_sites():
    """[{company, sector, location, scan_host, mqtt_broker, mqtt_port}, ...]"""
    # utf-8-sig: also accepts files saved by Windows editors that add a BOM
    return json.loads(SITES_FILE.read_text(encoding="utf-8-sig"))

# Probe timing
CONNECT_TIMEOUT = float(os.getenv("CONNECT_TIMEOUT", "1.0"))
BANNER_TIMEOUT = float(os.getenv("BANNER_TIMEOUT", "1.0"))
# DER publishes every 5 s, IoT every 4 s; listen long enough to hear both
LISTEN_SECONDS = float(os.getenv("LISTEN_SECONDS", "8"))

# Automatic runs (seconds between runs; 0 = only when someone presses "Run")
# Discovery runs when someone presses "Run agent" (and once at start-up)
DISCOVERY_INTERVAL = float(os.getenv("DISCOVERY_INTERVAL", "0"))
COMPLIANCE_INTERVAL = float(os.getenv("COMPLIANCE_INTERVAL", "0"))

REPORTS_DIR = Path(os.getenv("REPORTS_DIR", Path(__file__).resolve().parent / "reports"))
