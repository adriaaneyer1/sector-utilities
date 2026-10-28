"""
Discovery Agent: finds every device on each provisioned site and records
whether it is online. Its report is what the Devices page shows.

Nothing about the devices is hardcoded: for every site in sites.json the
agent scans the configured ports and listens on the site's MQTT broker, then
recognises devices by their fingerprints. Each device is tagged with its
site's company, sector and location. Devices found on earlier runs but not
reachable now are reported as offline.

Run once from the command line:  python -m agents.discovery_agent
"""
import asyncio
import time

import config
from agents.base import Agent
from agents.fingerprints import (
    CONSOLE_FINGERPRINTS, MODBUS_FINGERPRINTS, MQTT_FINGERPRINTS, device_id_of, identify,
)
from agents.probes import ConsoleProbe, ModbusProbe, MqttListener, extract_telemetry

SITE_FIELDS = ("company", "sector", "location")


class DiscoveryAgent(Agent):
    name = "discovery"
    title = "Discovery Agent"

    def __init__(self, store):
        super().__init__(store)
        self.console = ConsoleProbe(config.CONNECT_TIMEOUT, config.BANNER_TIMEOUT)
        self.modbus = ModbusProbe(config.CONNECT_TIMEOUT)

    async def execute(self):
        sites = config.load_sites()
        found, brokers_up = {}, {}
        for site in sites:
            tcp_devices, (broker_up, mqtt_devices) = await self._scan_site(site)
            brokers_up[self._broker(site)] = broker_up
            for d in tcp_devices + mqtt_devices:
                d.update({k: site[k] for k in SITE_FIELDS})
                found[d["id"]] = d

        active = len(found)
        devices = self._merge_with_inventory(found, brokers_up)
        summary = self._summarise(devices)
        self.step(f"Found {active} active device(s): {summary['online']} online, "
                  f"{summary['no_stream']} without data, {summary['offline']} offline")
        return {
            "sites": [{k: s[k] for k in SITE_FIELDS} for s in sites],
            "summary": summary,
            "devices": devices,
        }

    async def _scan_site(self, site):
        host, broker = site["scan_host"], self._broker(site)
        self.step(f"Site {site['company']} ({site['sector']}, {site['location']}): scanning {host} "
                  f"({len(config.SCAN_PORTS)} ports) and MQTT {broker} for {config.LISTEN_SECONDS:g}s")
        return await asyncio.gather(self._scan_tcp(host), self._scan_mqtt(site))

    @staticmethod
    def _broker(site):
        return f"{site['mqtt_broker']}:{site['mqtt_port']}"

    # ---------- TCP: consoles and Modbus ----------
    async def _scan_tcp(self, host):
        banners = await asyncio.gather(*(self.console.read_banner(host, p) for p in config.SCAN_PORTS))
        open_ports = [(p, b) for p, b in zip(config.SCAN_PORTS, banners) if b is not None]
        self.step(f"Open TCP ports on {host}: {', '.join(str(p) for p, _ in open_ports) or 'none'}")

        devices = []
        for port, banner in open_ports:
            if banner.strip():
                fp, info = identify(CONSOLE_FINGERPRINTS, banner)
                protocol = "Raw TCP"
            else:
                evidence = await self.modbus.read(host, port)
                if evidence is None:
                    self.step(f"Port {port}: open but not a recognised device, skipped")
                    continue
                fp, info = identify(MODBUS_FINGERPRINTS, evidence)
                protocol = "Modbus TCP"
            device = self._device(f"{protocol.split()[0].lower()}:{host}:{port}", fp, info, protocol,
                                  endpoint=f"{host}:{port}", status="online", host=host, port=port)
            devices.append(device)
            self.step(f"Port {port}: {fp.type_label} '{device['name']}'"
                      + (f", firmware {device['firmware']}" if device["firmware"] else ""))
        return devices

    # ---------- MQTT ----------
    async def _scan_mqtt(self, site):
        listener = MqttListener(site["mqtt_broker"], site["mqtt_port"])
        broker_up, messages = await listener.listen(config.LISTEN_SECONDS)
        if not broker_up:
            self.step(f"MQTT broker {self._broker(site)} unreachable")
            return False, []
        self.step(f"MQTT: heard {len(messages)} topic(s)")

        devices = {}
        for topic, msg in sorted(messages.items()):
            telemetry, envelope = extract_telemetry(msg["payload"])
            device_id = device_id_of(telemetry)
            if not device_id:
                continue  # alerts and other topics without an asset id
            fp, info = identify(MQTT_FINGERPRINTS, {"topic": topic, "telemetry": telemetry, "envelope": envelope})
            key = f"mqtt:{device_id}"
            device = devices.get(key)
            if device is None:
                device = self._device(key, fp, info, "MQTT", endpoint=topic, status="streaming",
                                      topics=[], mqtt_broker=self._broker(site))
                devices[key] = device
            device["topics"].append(topic)
            device["firmware"] = device["firmware"] or info.get("firmware")
            device["last_seen"] = max(device["last_seen"], msg["t"])
            # show the main telemetry topic, not the status/heartbeat one
            if not topic.endswith("/status"):
                device["endpoint"] = topic

        for d in devices.values():
            self.step(f"MQTT: {d['type']} '{d['name']}' on {d['endpoint']}"
                      + (f", firmware {d['firmware']}" if d["firmware"] else ""))
        return True, list(devices.values())

    # ---------- helpers ----------
    @staticmethod
    def _device(device_id, fp, info, protocol, endpoint, status, **extra):
        now = time.time()
        return {
            "id": device_id,
            "name": info.get("name") or device_id,
            "type": fp.type_label,
            "category": fp.category,
            "protocol": protocol,
            "endpoint": endpoint,
            "status": status,
            "vendor": info.get("vendor"),
            "model": info.get("model"),
            "firmware": info.get("firmware"),
            "firmware_note": info.get("firmware_note"),
            "first_seen": now,
            "last_seen": now,
            **extra,
        }

    def _merge_with_inventory(self, found, brokers_up):
        """Keep devices from earlier runs so a device that disappears shows as offline."""
        previous = (self.store.load(self.name) or {}).get("devices", [])
        merged = []
        for old in previous:
            new = found.pop(old["id"], None)
            if new:
                new["first_seen"] = old.get("first_seen", new["first_seen"])
                new["firmware"] = new["firmware"] or old.get("firmware")  # e.g. IoT heartbeat not heard this run
                merged.append(new)
            else:
                broker_up = brokers_up.get(old.get("mqtt_broker"), False)
                old["status"] = "no_stream" if old["protocol"] == "MQTT" and broker_up else "offline"
                merged.append(old)
                self.step(f"'{old['name']}' not found this run: marked {old['status'].replace('_', ' ')}")
        merged.extend(found.values())  # brand new devices
        return merged

    @staticmethod
    def _summarise(devices):
        summary = {"total": len(devices), "online": 0, "no_stream": 0, "offline": 0}
        for d in devices:
            if d["status"] in ("online", "streaming"):
                summary["online"] += 1
            else:
                summary[d["status"]] += 1
        return summary


if __name__ == "__main__":
    import json
    import logging

    from agents.store import ReportStore

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s: %(message)s")
    report = asyncio.run(DiscoveryAgent(ReportStore(config.REPORTS_DIR)).run())
    print(json.dumps(report["summary"], indent=2))
