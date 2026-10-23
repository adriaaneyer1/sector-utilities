"""
Protocol probes: small classes that know how to talk to one kind of device.
Agents use them; they never decide anything themselves.
"""
import asyncio
import json
import logging
import threading
import time

import paho.mqtt.client as mqtt
from pymodbus.client import AsyncModbusTcpClient

logging.getLogger("pymodbus").setLevel(logging.CRITICAL)


class TcpProbe:
    def __init__(self, connect_timeout=1.0):
        self.connect_timeout = connect_timeout

    async def is_open(self, host, port):
        try:
            _, writer = await asyncio.wait_for(asyncio.open_connection(host, port), self.connect_timeout)
        except (OSError, asyncio.TimeoutError):
            return False
        writer.close()
        try:
            await writer.wait_closed()
        except OSError:
            pass
        return True


class ConsoleProbe(TcpProbe):
    """Text consoles (terminal servers, PDUs) greet you with a banner on connect."""

    def __init__(self, connect_timeout=1.0, banner_timeout=1.0):
        super().__init__(connect_timeout)
        self.banner_timeout = banner_timeout

    async def read_banner(self, host, port):
        """None = port closed, "" = open but silent, otherwise the banner text.
        Never sends anything, so no command or credential reaches the device."""
        try:
            reader, writer = await asyncio.wait_for(asyncio.open_connection(host, port), self.connect_timeout)
        except (OSError, asyncio.TimeoutError):
            return None
        try:
            data = await asyncio.wait_for(reader.read(512), self.banner_timeout)
            return data.decode("utf-8", errors="ignore")
        except (OSError, asyncio.TimeoutError):
            return ""
        finally:
            writer.close()
            try:
                await writer.wait_closed()
            except OSError:
                pass


class ModbusProbe:
    """Reads the Modbus device identification and the first holding registers."""

    def __init__(self, connect_timeout=1.0, unit_id=1, register_count=20):
        self.connect_timeout = connect_timeout
        self.unit_id = unit_id
        self.register_count = register_count

    async def read(self, host, port):
        """None if the port does not speak Modbus, else {identity, registers}."""
        client = AsyncModbusTcpClient(host, port=port, timeout=self.connect_timeout, retries=0, reconnect_delay=0)
        try:
            if not await client.connect():
                return None
            identity, registers = {}, []
            try:
                info = await client.read_device_information(read_code=2, object_id=0, slave=self.unit_id)
                if not info.isError():
                    identity = {k: v.decode("utf-8", errors="ignore") for k, v in info.information.items()}
            except Exception:
                pass
            try:
                regs = await client.read_holding_registers(0, self.register_count, slave=self.unit_id)
                if not regs.isError():
                    registers = list(regs.registers)
            except Exception:
                pass
            if not identity and not registers:
                return None
            return {"identity": identity, "registers": registers}
        except Exception:
            return None
        finally:
            client.close()


def extract_telemetry(payload):
    """IoT sends {data, signature}, DER sends {telemetry, firmware_manifest,
    integrity_seal}. Returns (inner telemetry, outer envelope)."""
    if not isinstance(payload, dict):
        return {}, {}
    for key in ("data", "telemetry"):
        if isinstance(payload.get(key), dict):
            return payload[key], payload
    return payload, payload


class MqttListener:
    """Subscribes to every topic on the broker for a fixed window and returns
    what it heard: {topic: {"t": time, "payload": parsed JSON or None}}."""

    def __init__(self, broker, port, topic_filter="#"):
        self.broker = broker
        self.port = port
        self.topic_filter = topic_filter

    async def listen(self, seconds):
        """Returns (connected, messages)."""
        messages = {}
        connected = threading.Event()
        lock = threading.Lock()

        def on_connect(c, userdata, flags, reason_code, properties):
            if not reason_code.is_failure:
                c.subscribe(self.topic_filter)
                connected.set()

        def on_message(c, userdata, msg):
            try:
                payload = json.loads(msg.payload.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError):
                payload = None
            with lock:
                messages[msg.topic] = {"t": time.time(), "payload": payload}

        client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
        client.on_connect = on_connect
        client.on_message = on_message
        try:
            await asyncio.to_thread(client.connect, self.broker, self.port, 30)
        except OSError:
            return False, {}
        client.loop_start()
        try:
            await asyncio.sleep(seconds)
        finally:
            client.loop_stop()
            client.disconnect()
        with lock:
            return connected.is_set(), dict(messages)
