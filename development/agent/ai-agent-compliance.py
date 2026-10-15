#!/usr/bin/env python3
"""
DeltaStream AI Agent - Telemetry Compliance Monitoring Core
Simultaneously polls Modbus nodes, subscribes to MQTT streams, interacts with raw TCP sockets,
evaluates compliance against security standards, and exports a unified report.
"""

import asyncio
import json
import logging
import socket
import sys
import time
from pymodbus.client import ModbusTcpClient
import paho.mqtt.client as mqtt

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
log = logging.getLogger("DeltaStreamAgent")

# --- CONFIGURATION TARGETS ---
PLC_HOST, PLC_PORT = "127.0.0.1", 5020
RTU_HOST, RTU_PORT = "127.0.0.1", 5021
TS_HOST, TS_PORT = "127.0.0.1", 4000
PDU_HOST, PDU_PORT = "127.0.0.1", 4001
MQTT_BROKER, MQTT_PORT = "127.0.0.1", 1883

TOPICS = ["telemetry/der/solar_01", "telemetry/iot/environment"]

# Global store for live streams
mqtt_data = {
    "telemetry/der/solar_01": None,
    "telemetry/iot/environment": None
}

# --- MQTT HANDLERS ---
def on_message(client, userdata, msg):
    try:
        topic = msg.topic
        payload = json.loads(msg.payload.decode('utf-8'))
        mqtt_data[topic] = {
            "payload": payload,
            "timestamp": time.time()
        }
        log.info(f"Received stream from {topic}")
    except Exception as e:
        log.error(f"Failed to parse MQTT message: {e}")

def run_mqtt_client():
    try:
        client = mqtt.Client(callback_api_version=mqtt.CallbackApiVersion.VERSION2)
        client.on_message = on_message
        client.connect(MQTT_BROKER, MQTT_PORT, 60)
        for topic in TOPICS:
            client.subscribe(topic)
        client.loop_start()
        return client
    except Exception as e:
        log.warning(f"Could not connect to MQTT Broker: {e}")
        return None

# --- TELEMETRY & COMPLIANCE TASKS ---
async def check_modbus_device(name, host, port, expected_unit_id=1):
    log.info(f"Polling {name} Modbus registers at {host}:{port}...")
    status = "OFFLINE"
    compliance = {"status": "FAIL", "issues": ["Device is unreachable"], "remediation": ""}
    
    try:
        client = ModbusTcpClient(host, port=port)
        if client.connect():
            status = "ONLINE"
            compliance["status"] = "FAIL"
            compliance["issues"] = []
            
            # Read Holding Registers 0 to 5
            result = client.read_holding_registers(0, 5, slave=expected_unit_id)
            registers = result.registers if not result.isError() else []
            
            # Read Coils
            coil_result = client.read_coils(0, 5, slave=expected_unit_id)
            coils = coil_result.bits if not coil_result.isError() else []
            
            # Compliance evaluation (Example checks based on insecure configurations)
            if port == 5020: # PLC check
                compliance["issues"].append("Unencrypted Modbus TCP protocol exposed without TLS wrapper")
                compliance["issues"].append("No authentication layer enforced on device registers")
                compliance["remediation"] = "Wrap communication in a TLS tunnel (Port 8021/Stunnel) and integrate IEC 62443 secure zone boundaries."
            else: # RTU check
                compliance["issues"].append("Cleartext Modbus transport vulnerable to command injection")
                compliance["remediation"] = "Deploy hardware network taps and shift to secure protocol configurations or VPN encapsulations."
                
            client.close()
        else:
            compliance["remediation"] = f"Verify network routing to cluster node and ensure the {name} process is active."
    except Exception as e:
        compliance["issues"].append(f"Connection exception: {str(e)}")
        compliance["remediation"] = "Fix active script runtime environments."
        
    return {"status": status, "compliance": compliance}

async def query_socket_device(name, host, port, command):
    log.info(f"Interacting with {name} shell interface at {host}:{port}...")
    status = "OFFLINE"
    compliance = {"status": "FAIL", "issues": ["Interface dropped connections"], "remediation": ""}
    banner = ""
    
    try:
        reader, writer = await asyncio.open_connection(host, port)
        status = "ONLINE"
        compliance["issues"] = []
        
        # Read Initial Shell Banner
        data = await reader.read(1024)
        banner = data.decode('utf-8', errors='ignore')
        
        # Send interactive command
        writer.write(command.encode('utf-8') + b"\n")
        await writer.drain()
        
        # Capture response
        resp_data = await reader.read(1024)
        response = resp_data.decode('utf-8', errors='ignore')
        
        # Security parsing of strings
        if "bypass" in banner.lower() or "bypass" in response.lower():
            compliance["issues"].append("Active explicit authentication bypass banner flag detected")
        if port == 4001: # PDU specific
            compliance["issues"].append("Cleartext unauthenticated TCP console allows remote outlet switching")
            compliance["remediation"] = "Implement SSH/RSA keys for shell management, disable raw socket binding, and enforce TACACS+ configuration access controls."
        elif port == 4000: # Terminal Server specific
            compliance["issues"].append("Raw telnet-like terminal session leaks backend operational serial map topology")
            compliance["remediation"] = "Migrate endpoints to encrypted network listeners and strictly boundary accessible user interfaces."
            
        writer.close()
        await writer.wait_closed()
    except Exception as e:
        compliance["issues"].append(f"Socket interface error: {str(e)}")
        compliance["remediation"] = f"Ensure the target service script is listening on port {port}."
        
    return {"status": status, "compliance": compliance, "banner": banner.strip()}

async def evaluate_mqtt_node(topic):
    log.info(f"Evaluating telemetry compliance on data topic: {topic}...")
    data_entry = mqtt_data.get(topic)
    
    if not data_entry:
        return {
            "status": "NO_STREAM",
            "compliance": {
                "status": "FAIL", 
                "issues": ["No telemetry packets received within interval frame"], 
                "remediation": "Verify local MQTT Broker is running on port 1883 and edge simulation device script is executing upstream."
            }
        }
        
    compliance = {"status": "FAIL", "issues": [], "remediation": ""}
    payload = data_entry["payload"]
    
    # Check payload parameters
    if "device_id" in payload or "sensor_id" in payload:
        compliance["issues"].append("Payload transmits unencrypted cleartext asset identifier tags")
    if "timestamp" in payload and (time.time() - payload["timestamp"]) > 60:
        compliance["issues"].append("Detected packet transmission drift / legacy timestamp injection potential")
        
    compliance["remediation"] = f"Enable TLS transport on MQTT Broker connection context, sign JSON payloads utilizing localized cryptographic keys, and filter asset schemas."
    
    return {"status": "STREAMING", "compliance": compliance, "latest_payload": payload}

# --- GENERATE COMPLIANCE REPORT ---
def output_report(report):
    print("\n" + "="*60)
    print("                DELTASTREAM AI SECURITY COMPLIANCE REPORT")
    print("="*60)
    print(f"Generated: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    for device, details in report.items():
        print(f"Device Node : {device}")
        print(f"Core Status : {details['status']}")
        comp = details["compliance"]
        print(f"Compliance  : {comp['status']}")
        if comp["issues"]:
            print("Discovered Structural Vulnerabilities:")
            for issue in comp["issues"]:
                print(f"  - [CRITICAL] {issue}")
            print(f"Remediation Plan:")
            print(f"    {comp['remediation']}")
        else:
            print("  - No immediate compliance issues found on active profile.")
        print("-" * 60)

async def main():
    print("Initializing DeltaStream AI Compliance Telemetry Engine...")
    mqtt_client = run_mqtt_client()
    
    # Allow small window to parse incoming async streams
    await asyncio.sleep(2)
    
    # Gather simultaneous queries
    plc_task = check_modbus_device("Virtual PLC", PLC_HOST, PLC_PORT)
    rtu_task = check_modbus_device("Virtual RTU", RTU_HOST, RTU_PORT)
    ts_task = query_socket_device("Terminal Server", TS_HOST, TS_PORT, "status")
    pdu_task = query_socket_device("Virtual PDU", PDU_HOST, PDU_PORT, "read all")
    der_task = evaluate_mqtt_node("telemetry/der/solar_01")
    iot_task = evaluate_mqtt_node("telemetry/iot/environment")
    
    results = await asyncio.gather(plc_task, rtu_task, ts_task, pdu_task, der_task, iot_task)
    
    report = {
        "Virtual_PLC (Modbus/5020)": results[0],
        "Virtual_RTU (Modbus/5021)": results[1],
        "Terminal_Server (TCP/4000)": results[2],
        "Virtual_PDU (TCP/4001)": results[3],
        "DER_Gateway (MQTT/Solar)": results[4],
        "IoT_Sensor_Node (MQTT/Env)": results[5]
    }
    
    output_report(report)
    
    if mqtt_client:
        mqtt_client.loop_stop()
        mqtt_client.disconnect()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nCompliance audit aborted by user control.")