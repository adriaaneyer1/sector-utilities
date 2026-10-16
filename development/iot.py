#!/usr/bin/env python3
"""
Device Name: Secure Virtual IoT Sensor Node
Protocol: MQTT (Topic: telemetry/iot/environment)
Standard Alignment: IEC 62443-4-2 (Component Security Requirements)
Description: Exposes ambient condition data with integrated integrity checks,
             firmware metadata, and security log telemetry.
"""

import time
import json
import random
import logging
import hmac
import hashlib
import paho.mqtt.client as mqtt

# Configuration
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
log = logging.getLogger("SecureIoT")

MQTT_BROKER = "127.0.0.1"
MQTT_PORT = 1883
TOPIC_TELEMETRY = "telemetry/iot/environment"
TOPIC_STATUS = "telemetry/iot/status"

# IEC 62443 Reference: Firmware Management & Device Identity (SR 1.13 / SR 3.1)
FIRMWARE_METADATA = {
    "firmware_version": "2.1.4-secure",
    "hardware_revision": "REV_B",
    "boot_status": "INTEGRITY_VERIFIED_SECURE_BOOT"
}

# Simulated Shared Secret Key for message integrity verification (HMAC)
# In production, this would be backed by a hardware root of trust / Secure Element
SHARED_INTEGRITY_KEY = b"IEC62443_SECURE_COMM_SECRET_KEY"

def generate_signature(payload_str: str) -> str:
    """Generates an HMAC-SHA256 signature to guarantee message integrity."""
    return hmac.new(SHARED_INTEGRITY_KEY, payload_str.encode('utf-8'), hashlib.sha256).hexdigest()

def publish_heartbeat(client: mqtt.Client):
    """Publishes a health/heartbeat event including current firmware context."""
    status_payload = {
        "sensor_id": "env_floor_03",
        "timestamp": int(time.time()),
        "status": "OPERATIONAL",
        "firmware": FIRMWARE_METADATA
    }
    payload_str = json.dumps(status_payload)
    signature = generate_signature(payload_str)
    
    # Bundle data and cryptographic proof
    secured_packet = {
        "data": status_payload,
        "signature": signature
    }
    
    client.publish(TOPIC_STATUS, json.dumps(secured_packet), qos=1)
    log.info(f"[IEC 62443 Audit] Heartbeat/Firmware state broadcasted to {TOPIC_STATUS}")

def main():
    # Use explicit, clean client configurations
    client = mqtt.Client(callback_api_version=mqtt.CallbackAPIVersion.VERSION2)
    
    try:
        client.connect(MQTT_BROKER, MQTT_PORT, 60)
    except Exception as e:
        log.critical(f"Network Connection Failure: Unable to bind to Broker. Error: {e}")
        return

    client.loop_start()
    log.info("Secure IoT Device streaming active. Core defensive patterns initialized.")
    
    # Broadcast an initial health and firmware status on boot
    publish_heartbeat(client)
    
    loop_counter = 0

    try:
        while True:
            # Core Sensor Telemetry Data
            telemetry_data = {
                "sensor_id": "env_floor_03",
                "timestamp": int(time.time()),  # SR 7.2 Time Synchronization alignment
                "ambient_temp_c": round(random.uniform(21.0, 24.5), 1),
                "humidity_pct": round(random.uniform(40.0, 55.0), 1),
                "vibration_level": round(random.uniform(0.01, 0.05), 4)
            }
            
            # Convert to string and sign payload (Defends against tampering/MITM)
            payload_str = json.dumps(telemetry_data)
            signature = generate_signature(payload_str)
            
            secured_packet = {
                "data": telemetry_data,
                "signature": signature
            }
            
            client.publish(TOPIC_TELEMETRY, json.dumps(secured_packet), qos=1)
            log.info(f"Published secure telemetry: {secured_packet}")
            
            # Periodically broadcast status/heartbeat logs (Every ~20 seconds)
            loop_counter += 1
            if loop_counter >= 5:
                publish_heartbeat(client)
                loop_counter = 0
                
            time.sleep(4)
            
    except KeyboardInterrupt:
        log.warning("[IEC 62443 Audit] Local operator requested service termination.")
    finally:
        log.info("Cleaning connections and stopping telemetry streams...")
        client.loop_stop()
        client.disconnect()

if __name__ == "__main__":
    main()