"""
Device fingerprints: how the Discovery Agent recognises what it found.

Like a network scanner, the agent does not need a list of devices; it
matches what each device reveals (banner, Modbus identity, MQTT payload)
against these signatures. Add a class here to teach it a new device type.
"""
import re
from abc import ABC, abstractmethod


class Fingerprint(ABC):
    category = "unknown"
    type_label = "Unknown device"

    @abstractmethod
    def matches(self, evidence) -> bool: ...

    @abstractmethod
    def describe(self, evidence) -> dict:
        """Return name, vendor, firmware for the device."""


# ---------- console devices (evidence: banner text) ----------

def _first_line(banner):
    line = banner.strip().splitlines()[0] if banner.strip() else ""
    return line.strip(" -") or "Console device"


class TerminalServerFingerprint(Fingerprint):
    category = "terminal_server"
    type_label = "Serial console gateway"

    def matches(self, banner):
        return "terminal server" in banner.lower()

    def describe(self, banner):
        fw = re.search(r"Firmware:\s*([^\s|]+)", banner)
        return {"name": _first_line(banner), "firmware": fw.group(1) if fw else None}


class PduFingerprint(Fingerprint):
    category = "pdu"
    type_label = "Rack power distribution unit"

    def matches(self, banner):
        return "pdu" in banner.lower()

    def describe(self, banner):
        # The PDU only reveals firmware after login; the agent never logs in.
        return {"name": _first_line(banner), "firmware": None, "firmware_note": "Requires login"}


class GenericConsoleFingerprint(Fingerprint):
    category = "console"
    type_label = "Text console device"

    def matches(self, banner):
        return bool(banner.strip())

    def describe(self, banner):
        return {"name": _first_line(banner), "firmware": None}


CONSOLE_FINGERPRINTS = [TerminalServerFingerprint(), PduFingerprint(), GenericConsoleFingerprint()]


# ---------- Modbus devices (evidence: {identity, registers}) ----------

class PlcFingerprint(Fingerprint):
    category = "plc"
    type_label = "Programmable logic controller"

    def matches(self, ev):
        ident = ev["identity"]
        return "PLC" in (ident.get(1, "") + ident.get(5, "")).upper()

    def describe(self, ev):
        ident = ev["identity"]
        fw = re.search(r"Firmware Build:\s*(\S+)", ident.get(6, ""))
        return {
            "name": ident.get(4) or ident.get(5) or "Modbus PLC",
            "vendor": ident.get(0),
            "model": ident.get(5),
            "firmware": fw.group(1) if fw else None,
        }


class RtuFingerprint(Fingerprint):
    """Substation RTU: firmware major, minor, patch, build stored right
    before model id 8485 in the holding registers."""
    category = "rtu"
    type_label = "Substation remote terminal unit"
    MODEL_ID = 8485

    def matches(self, ev):
        regs = ev["registers"]
        return self.MODEL_ID in regs and regs.index(self.MODEL_ID) >= 4

    def describe(self, ev):
        regs = ev["registers"]
        i = regs.index(self.MODEL_ID)
        major, minor, patch, build = regs[i - 4:i]
        return {
            "name": f"RTU model {self.MODEL_ID}",
            "model": str(self.MODEL_ID),
            "firmware": f"{major}.{minor}.{patch} (build {build})",
        }


class GenericModbusFingerprint(Fingerprint):
    category = "modbus"
    type_label = "Modbus device"

    def matches(self, ev):
        return True

    def describe(self, ev):
        ident = ev["identity"]
        return {"name": ident.get(4) or ident.get(5) or "Modbus device", "vendor": ident.get(0), "firmware": None}


MODBUS_FINGERPRINTS = [PlcFingerprint(), RtuFingerprint(), GenericModbusFingerprint()]


# ---------- MQTT devices (evidence: {topic, telemetry, envelope}) ----------

class MqttFingerprint(Fingerprint):
    """Matches on the second topic segment: telemetry/<segment>/..."""
    segment = None

    def matches(self, ev):
        parts = ev["topic"].split("/")
        return len(parts) > 1 and parts[1] == self.segment

    def describe(self, ev):
        return {"name": device_id_of(ev["telemetry"]), "firmware": firmware_of(ev["telemetry"], ev["envelope"])}


class DerFingerprint(MqttFingerprint):
    category = "der_gateway"
    type_label = "Solar DER gateway"
    segment = "der"


class IotSensorFingerprint(MqttFingerprint):
    category = "iot_sensor"
    type_label = "Environmental IoT sensor"
    segment = "iot"


class GenericMqttFingerprint(MqttFingerprint):
    category = "mqtt"
    type_label = "MQTT telemetry device"

    def matches(self, ev):
        return True


MQTT_FINGERPRINTS = [DerFingerprint(), IotSensorFingerprint(), GenericMqttFingerprint()]


def device_id_of(telemetry):
    return telemetry.get("device_id") or telemetry.get("sensor_id")


def firmware_of(telemetry, envelope):
    manifest = envelope.get("firmware_manifest")
    if isinstance(manifest, dict) and manifest.get("version"):
        return manifest["version"]
    fw = telemetry.get("firmware")
    if isinstance(fw, dict):
        return fw.get("firmware_version")
    return None


def identify(fingerprints, evidence):
    for fp in fingerprints:
        if fp.matches(evidence):
            return fp, fp.describe(evidence)
    return None, {}
