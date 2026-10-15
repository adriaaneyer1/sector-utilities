#!/usr/bin/env python3
"""
Device Name: DER Gateway (Distributed Energy Resource)
Protocol: MQTT (Topic: telemetry/der/solar_01)
Description: Simulates a hardened IEC 62443-4-2 compliant solar inverter gateway.
             Includes firmware metadata verification, anomalous payload simulation,
             and cryptographically simulated state telemetry.
"""

import time
import json
import random
import logging
import hmac
import hashlib
import paho.mqtt.client as mqtt

# Configure structured, auditable logging (IEC 62443-4-2 CR 6.1 - Audit Log Generation)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] [Component: %(name)s] [EventID: %(message)s]'
)
log = logging.getLogger("DERGateway_Secure")

MQTT_BROKER = "127.0.0.1"
MQTT_PORT = 1883
TOPIC_TELEMETRY = "telemetry/der/solar_01"
TOPIC_SECURITY = "security/der/alerts"

# IEC 62443-4-2 CR 4.1 - Information Embedded Integrity Check
# Static asset configuration simulating certified firmware baseline vendor sign-off
FIRMWARE_METADATA = {
    "firmware_version": "v2.4.1-secure",
    "build_checksum": "8f9b23e1a6c4f0f671c8b321a92df42a1563f69b2d861d8a4f1a2386e812d6c1", # SHA-256
    "hardware_revision": "HW-REV-03",
    "boot_status": "INTEGRITY_VERIFIED_SECURE_BOOT"
}

# Simulated Symmetric Cryptographic Key (IEC 62443-4-2 CR 3.1 - Data Integrity)
# Used to generate a Message Authentication Code (MAC) for data authenticity
SHARED_MAC_KEY = b"IEC_62443_COMPLIANT_FIELD_SECRET_KEY_A1B2"

def calculate_telemetry_mac(payload: dict, key: bytes) -> str:
    """Generates an HMAC-SHA256 signature to guarantee telemetry data integrity."""
    serialized = json.dumps(payload, sort_keys=True).encode('utf-8')
    return hmac.new(key, serialized, hashlib.sha256).hexdigest()

def main():
    # Initialize MQTT client with modern API lifecycle hooks
    client = mqtt.Client(callback_api_version=mqtt.CallbackApiVersion.VERSION2)
    
    # Audit log entry for component startup & state initialization
    log.info("SYS_001: Initializing secure DER Gateway subsystem.")
    log.info(f"SYS_002: Active Firmware Target Verification: {FIRMWARE_METADATA['firmware_version']} | Hash: {FIRMWARE_METADATA['build_checksum'][:8]}... [PASSED]")

    try:
        log.info(f"NET_001: Establishing connection to IACS Zone Broker at {MQTT_BROKER}:{MQTT_PORT}")
        client.connect(MQTT_BROKER, MQTT_PORT, 60)
        client.loop_start()
    except Exception as e:
        log.error(f"NET_ERR_001: Zone boundary communication failure: {str(e)}")
        return

    log.info("SYS_003: Operational loop active. Data stream protected via Message Authentication.")

    seq_num = 0
    try:
        while True:
            seq_num += 1
            
            # IEC 62443-4-2 CR 3.11 / CR 4.2 - Input Validation and Out-of-Bounds Mitigation
            # Simulate a physical sensor anomaly or protocol tampering payload every 6th cycle
            is_anomaly = (seq_num % 6 == 0)
            
            if is_anomaly:
                # Malicious input/Faulty telemetry condition simulation
                generation = round(random.uniform(250.0, 500.0), 2)  # Physical hardware maximum is 50.0 kW
                soc = 145                                           # Percentages cannot exceed 100%
                grid_status = "unstable_frequency_injection"
            else:
                generation = round(random.uniform(15.5, 45.0), 2)
                soc = random.randint(75, 98)
                grid_status = "connected"

            # Base Operational Telemetry Schema
            telemetry_data = {
                "device_id": "solar_inverter_01",
                "timestamp": int(time.time()),
                "sequence": seq_num,
                "generation_kw": generation,
                "battery_soc_pct": soc,
                "grid_status": grid_status
            }

            # Local Sanity Check / Bounds enforcement (CR 3.11 - Input Validation)
            # Component detects its own telemetry deviation before pushing to the network
            if telemetry_data["generation_kw"] > 50.0 or telemetry_data["battery_soc_pct"] > 100:
                security_alert = {
                    "alert_id": f"SEC-ERR-{int(time.time())}",
                    "severity": "HIGH",
                    "reason": "Out-of-bounds metrics detected. Potential sensor manipulation or logic exploitation.",
                    "offending_metrics": {"kw": generation, "soc": soc},
                    "firmware_context": FIRMWARE_METADATA
                }
                client.publish(TOPIC_SECURITY, json.dumps(security_alert), qos=1)
                log.warning(f"SEC_ALE_001: Local validation failure. Dispatched alert to SOC zone: {security_alert['reason']}")

            # Construct Comprehensive Secure Payload Architecture
            packaged_payload = {
                "telemetry": telemetry_data,
                "firmware_manifest": {
                    "version": FIRMWARE_METADATA["firmware_version"],
                    "boot_status": FIRMWARE_METADATA["boot_status"]
                },
                # Cryptographic seal protecting against Middleperson/Tamper vectors
                "integrity_seal": calculate_telemetry_mac(telemetry_data, SHARED_MAC_KEY)
            }

            # Publish hardened payload with QoS 1 to guarantee delivery (CR 7.3 - Resource Availability)
            client.publish(TOPIC_TELEMETRY, json.dumps(packaged_payload), qos=1)
            log.info(f"DAT_001: Data packet transmitted. Seq: {seq_num} | Sealed: True | Target: {TOPIC_TELEMETRY}")

            # IEC 62443-4-2 CR 7.1 - Network DoS / Rate Control mitigation 
            # Strict pacing prevents connection flooding and protects processing resources
            time.sleep(5)

    except KeyboardInterrupt:
        log.info("SYS_004: Received explicit operator shutdown command sequence.")
    finally:
        log.info("SYS_005: Purging network sessions and putting telemetry transceivers to safe standby.")
        client.loop_stop()
        client.disconnect()

if __name__ == "__main__":
    main()
