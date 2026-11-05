"""
Compliance Agent: checks every device the Discovery Agent found and writes
the compliance report the Compliance page shows.

It re-checks each device itself (reachability, console banner, latest MQTT
payload) and applies one rule set per device category. Rule texts are
ported from the client's agent (sector-utilities/development/agent/
ai-agent-compliance.py) so both report the same findings.

Run once from the command line:  python -m agents.compliance_agent
"""
import asyncio
import time
from abc import ABC, abstractmethod

import config
from agents.base import Agent
from agents.fingerprints import device_id_of
from agents.probes import ConsoleProbe, MqttListener, TcpProbe, extract_telemetry

CRITICAL = "critical"
HIGH = "high"
MEDIUM = "medium"
TIMESTAMP_DRIFT_SECONDS = 60

# The four compliance statuses, from worst to best
NON_COMPLIANT = "Non-compliant"
NEEDS_CHANGE_CONTROL = "Needs change control"
PARTIALLY_COMPLIANT = "Partially compliant"
COMPLIANT = "Compliant"
STATUSES = (COMPLIANT, PARTIALLY_COMPLIANT, NEEDS_CHANGE_CONTROL, NON_COMPLIANT)


def finding(code, title, severity=CRITICAL):
    """code identifies the issue so a firmware update can say which ones it fixes."""
    return {"code": code, "severity": severity, "title": title}


# ---------- rule sets ----------

class RuleSet(ABC):
    categories = ()

    def applies_to(self, device):
        return device["category"] in self.categories

    @abstractmethod
    def evaluate(self, device, obs) -> tuple[list, str]:
        """Return (findings, remediation) for one device."""


class ModbusRules(RuleSet):
    categories = ("plc", "rtu", "modbus")

    def evaluate(self, device, obs):
        if not obs["reachable"]:
            return [finding("unreachable", "Device is unreachable")], (
                f"Verify network routing to cluster node and ensure the {device['name']} process is active.")
        if device["category"] == "plc":
            return [
                finding("modbus_no_tls", "Unencrypted Modbus TCP protocol exposed without TLS wrapper"),
                finding("modbus_no_auth", "No authentication layer enforced on device registers"),
            ], "Wrap communication in a TLS tunnel (Port 8021/Stunnel) and integrate IEC 62443 secure zone boundaries."
        return [finding("modbus_cleartext", "Cleartext Modbus transport vulnerable to command injection", HIGH)], (
            "Deploy hardware network taps and shift to secure protocol configurations or VPN encapsulations.")


class ConsoleRules(RuleSet):
    categories = ("terminal_server", "pdu", "console")

    def evaluate(self, device, obs):
        if not obs["reachable"]:
            return [finding("unreachable", "Interface dropped connections")], (
                f"Ensure the target service script is listening on port {device['port']}.")
        findings = []
        if "bypass" in (obs.get("banner") or "").lower():
            findings.append(finding("console_auth_bypass", "Active explicit authentication bypass banner flag detected"))
        if device["category"] == "pdu":
            findings.append(finding("console_reusable_passwords", "Cleartext TCP console authenticates with reusable passwords"))
            return findings, ("Implement SSH/RSA keys for shell management, disable raw socket binding, "
                              "and enforce TACACS+ configuration access controls.")
        findings.append(finding("console_topology_leak", "Raw telnet-like terminal session leaks backend operational serial map topology", HIGH))
        return findings, "Migrate endpoints to encrypted network listeners and strictly boundary accessible user interfaces."


class MqttTelemetryRules(RuleSet):
    categories = ("der_gateway", "iot_sensor", "mqtt")

    def evaluate(self, device, obs):
        if obs.get("payload") is None:
            broker = device.get("mqtt_broker", "the MQTT broker")
            return [finding("no_telemetry", "No telemetry packets received within interval frame")], (
                f"Verify the MQTT broker {broker} is running and the edge simulation "
                "device script is executing upstream.")
        telemetry, envelope = extract_telemetry(obs["payload"])
        findings = []
        if "device_id" in telemetry or "sensor_id" in telemetry:
            findings.append(finding("mqtt_cleartext_ids", "Payload transmits unencrypted cleartext asset identifier tags", MEDIUM))
        ts = telemetry.get("timestamp")
        if isinstance(ts, (int, float)) and time.time() - ts > TIMESTAMP_DRIFT_SECONDS:
            findings.append(finding("mqtt_timestamp_drift", "Detected packet transmission drift / legacy timestamp injection potential", HIGH))
        if "signature" not in envelope and "integrity_seal" not in envelope:
            findings.append(finding("mqtt_no_signature", "Telemetry envelope lacks an integrity signature", HIGH))
        remediation = ("Enable TLS on the MQTT broker; keep HMAC seals and avoid exposing raw asset "
                       "identifiers in cleartext fields.") if findings else ""
        return findings, remediation


RULE_SETS = [ModbusRules(), ConsoleRules(), MqttTelemetryRules()]


# ---------- standards violated (client's non-compliance table) ----------

PLAIN_TEXT = {"vector": "Plain-Text Telemetry", "standard": "NERC CIP-012-2",
              "requirement": "Data Protection in Transit"}
DEFAULT_CREDENTIALS = {"vector": "Hardcoded/Default Credentials", "standard": "IEC 62443-4-2",
                       "requirement": "Identification & Access Control"}
AUDIT_LOGGING = {"vector": "Missing Audit Logging", "standard": "NERC CIP-007 & CIP-015",
                 "requirement": "Internal Network Monitoring"}
REMOTE_ACCESS = {"vector": "Unrestricted Remote Access", "standard": "NERC CIP-003-9",
                 "requirement": "Vendor Electronic Access Control"}
CHANGE_CONTROL = {"vector": "Unapproved Firmware Baseline", "standard": "NERC CIP-010-4",
                  "requirement": "Configuration Change Management"}

# Which standards each kind of device breaks when it fails its checks
# (mapping confirmed with the client).
VIOLATIONS_BY_CATEGORY = {
    "plc": [PLAIN_TEXT, AUDIT_LOGGING],
    "rtu": [PLAIN_TEXT],
    "modbus": [PLAIN_TEXT],
    "terminal_server": [PLAIN_TEXT, REMOTE_ACCESS],
    "pdu": [DEFAULT_CREDENTIALS],
    "console": [PLAIN_TEXT],
    "der_gateway": [PLAIN_TEXT, DEFAULT_CREDENTIALS],
    "iot_sensor": [PLAIN_TEXT, DEFAULT_CREDENTIALS],
    "mqtt": [PLAIN_TEXT],
}


def violations_for(device, findings, reachable, off_baseline=False):
    """Standards breached by a failing device. An unreachable device could
    not be inspected, so no standard is attributed to it."""
    if not findings or not reachable:
        return []
    violations = list(VIOLATIONS_BY_CATEGORY.get(device["category"], []))
    if off_baseline:
        violations.append(CHANGE_CONTROL)
    return violations


# ---------- firmware baseline and status ----------

def _version(firmware):
    """'v2.1.0-secure' -> '2.1.0-secure', '2.1.0 (build 1042)' -> '2.1.0'"""
    return firmware.strip().lower().lstrip("v").split(" ")[0]


def baseline_check(device, repository):
    """(approved target version or None, finding or None). Firmware the agent
    can't read (e.g. the PDU before login) is not judged."""
    entry = repository.get(device["category"]) or {}
    approved = entry.get("approved") or []
    firmware = device.get("firmware")
    target = entry.get("latest") or (approved[-1] if approved else None)
    if not approved or not firmware or _version(firmware) in {_version(v) for v in approved}:
        return target, None
    return target, finding("firmware_off_baseline",
                           f"Firmware {firmware} is not an approved baseline version ({', '.join(approved)})", HIGH)


# ---------- firmware installed by the AI Remediation Agent ----------

FIRMWARE_STATE = "firmware_state"   # {device_id: {firmware, previous_firmware, fixes, at}}


def apply_installed_firmware(device, findings, remediation, installed):
    """The virtual devices can't be re-flashed, so updates the AI Remediation
    Agent installs are kept here and applied on every check: the device reports
    the new version and the findings that version fixes are gone."""
    if not installed:
        return device, findings, remediation
    device = {**device, "firmware": installed["firmware"]}
    fixed = set(installed.get("fixes", []))
    findings = [f for f in findings if f["code"] not in fixed]
    return device, findings, remediation if findings else ""


def status_of(reachable, findings, off_baseline):
    """Worst condition wins:
    Non-compliant         unreachable, or any critical finding
    Needs change control  firmware differs from the approved baseline
    Partially compliant   only high / medium findings
    Compliant             no findings"""
    if not reachable or any(f["severity"] == CRITICAL for f in findings):
        return NON_COMPLIANT
    if off_baseline:
        return NEEDS_CHANGE_CONTROL
    if findings:
        return PARTIALLY_COMPLIANT
    return COMPLIANT


# ---------- the agent ----------

class ComplianceAgent(Agent):
    name = "compliance"
    title = "Compliance Agent"
    standard = "IEC 62443"

    def __init__(self, store):
        super().__init__(store)
        self.tcp = TcpProbe(config.CONNECT_TIMEOUT)
        self.console = ConsoleProbe(config.CONNECT_TIMEOUT, config.BANNER_TIMEOUT)

    async def execute(self):
        inventory = (self.store.load("discovery") or {}).get("devices", [])
        if not inventory:
            self.step("No devices in inventory yet: run the Discovery Agent first")
        else:
            self.step(f"Checking {len(inventory)} device(s) from the Discovery Agent's inventory")

        observations = await self._observe(inventory)
        repository = config.load_firmware_repository()
        installed = self.store.load(FIRMWARE_STATE) or {}
        results = []
        for device in inventory:
            rules = next((r for r in RULE_SETS if r.applies_to(device)), None)
            if rules is None:
                self.step(f"'{device['name']}': no rule set for category {device['category']}, skipped")
                continue
            findings, remediation = rules.evaluate(device, observations[device["id"]])
            reachable = observations[device["id"]]["reachable"]
            if reachable:
                device, findings, remediation = apply_installed_firmware(
                    device, findings, remediation, installed.get(device["id"]))
            approved, fw_finding = baseline_check(device, repository) if reachable else (None, None)
            if fw_finding:
                findings.append(fw_finding)
                remediation = " ".join(filter(None, [
                    remediation, f"Raise a change request and update the firmware to {approved}."]))
            status = status_of(reachable, findings, fw_finding is not None)
            result = "pass" if status == COMPLIANT else "fail"
            violations = violations_for(device, findings, reachable, fw_finding is not None)
            results.append({
                "id": device["id"],
                "category": device["category"],
                "name": device["name"],
                "type": device["type"],
                "protocol": device["protocol"],
                "endpoint": device["endpoint"],
                "firmware": device.get("firmware"),
                "firmware_approved": approved,
                "firmware_updated": device["id"] in installed,
                "company": device.get("company"),
                "sector": device.get("sector"),
                "location": device.get("location"),
                "reachable": reachable,
                "result": result,
                "status": status,
                "findings": findings,
                "violations": violations,
                "remediation": remediation,
            })
            self.step(f"'{device['name']}': {status} ({len(findings)} finding(s))"
                      + (f", violates {', '.join(v['standard'] for v in violations)}" if violations else ""))

        return {
            "standard": self.standard,
            "summary": {
                "total": len(results),
                "passing": sum(r["result"] == "pass" for r in results),
                "failing": sum(r["result"] == "fail" for r in results),
                "critical": sum(f["severity"] == CRITICAL for r in results for f in r["findings"]),
                "by_status": {s: sum(r["status"] == s for r in results) for s in STATUSES},
            },
            "devices": results,
        }

    async def _observe(self, inventory):
        """Collect fresh evidence for every device in parallel."""
        tcp = [d for d in inventory if d["protocol"] != "MQTT"]
        mqtt = [d for d in inventory if d["protocol"] == "MQTT"]

        async def observe_tcp(d):
            if d["category"] in ConsoleRules.categories:
                banner = await self.console.read_banner(d["host"], d["port"])
                return {"reachable": banner is not None, "banner": banner}
            return {"reachable": await self.tcp.is_open(d["host"], d["port"])}

        async def listen(broker):
            host, port = broker.rsplit(":", 1)
            _, messages = await MqttListener(host, int(port)).listen(config.LISTEN_SECONDS)
            return messages

        async def observe_mqtt():
            brokers = sorted({d["mqtt_broker"] for d in mqtt if d.get("mqtt_broker")})
            if not brokers:
                return {}
            self.step(f"Listening to MQTT telemetry on {', '.join(brokers)} for {config.LISTEN_SECONDS:g}s")
            latest = {}
            for messages in await asyncio.gather(*(listen(b) for b in brokers)):
                for topic, msg in messages.items():
                    if topic.endswith("/status"):
                        continue
                    telemetry, _ = extract_telemetry(msg["payload"])
                    dev_id = device_id_of(telemetry)
                    if dev_id:
                        latest[f"mqtt:{dev_id}"] = msg["payload"]
            return latest

        tcp_results, mqtt_latest = await asyncio.gather(
            asyncio.gather(*(observe_tcp(d) for d in tcp)), observe_mqtt())
        observations = {d["id"]: obs for d, obs in zip(tcp, tcp_results)}
        for d in mqtt:
            payload = mqtt_latest.get(d["id"])
            observations[d["id"]] = {"reachable": payload is not None, "payload": payload}
        return observations


if __name__ == "__main__":
    import json
    import logging

    from agents.store import ReportStore

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s: %(message)s")
    report = asyncio.run(ComplianceAgent(ReportStore(config.REPORTS_DIR)).run())
    print(json.dumps(report["summary"], indent=2))
