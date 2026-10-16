import json
import time
from pymodbus.client import ModbusTcpClient
import paho.mqtt.client as mqtt

# --- CONFIGURATION ---
# Modbus Configuration
MODBUS_HOST = "192.168.1.100"      # IP address of your Modbus device
MODBUS_PORT = 502                 # Default Modbus TCP port
SLAVE_ID = 1                      # Unit ID / Slave ID
START_REGISTER = 0               # Register address to start reading from
REGISTER_COUNT = 5                # Number of registers to read

# MQTT Configuration
MQTT_BROKER = "://hivemq.com" # Public test broker (Change for production)
MQTT_PORT = 1883                  # Default unencrypted MQTT port
MQTT_TOPIC = "telemetry/modbus/data"
MQTT_CLIENT_ID = "Ubuntu_Modbus_Gateway"

def main():
    # 1. Initialize and connect the MQTT Client
    # Note: Using CallbackAPIVersion.VERSION2 for compatibility with Paho-MQTT v2.x
    mqtt_client = mqtt.Client(callback_api_version=mqtt.CallbackAPIVersion.VERSION2, client_id=MQTT_CLIENT_ID)
    
    print(f"Connecting to MQTT Broker: {MQTT_BROKER}...")
    try:
        mqtt_client.connect(MQTT_BROKER, MQTT_PORT, keepalive=60)
        mqtt_client.loop_start() # Starts a background thread to handle MQTT traffic
        print("Connected to MQTT successfully.")
    except Exception as e:
        print(f"Failed to connect to MQTT broker: {e}")
        return

    # 2. Initialize the Modbus TCP Client
    modbus_client = ModbusTcpClient(MODBUS_HOST, port=MODBUS_PORT)
    print(f"Connecting to Modbus Device: {MODBUS_HOST}:{MODBUS_PORT}...")
    
    if not modbus_client.connect():
        print("Failed to connect to Modbus device.")
        mqtt_client.loop_stop()
        return
    print("Connected to Modbus device successfully.")

    # 3. Main Data Loop
    try:
        while True:
            # Read holding registers
            response = modbus_client.read_holding_registers(
                address=START_REGISTER, 
                count=REGISTER_COUNT, 
                slave=SLAVE_ID
            )
            
            if response.isError():
                print(f"Modbus Error: {response}")
            else:
                # Extract registers list
                register_values = response.registers
                print(f"Read Data: {register_values}")
                
                # Format payload into a clean JSON object
                payload = {
                    "timestamp": time.time(),
                    "device_id": SLAVE_ID,
                    "registers": register_values
                }
                
                # Publish data to MQTT topic
                result = mqtt_client.publish(MQTT_TOPIC, json.dumps(payload), qos=1)
                
                # Verify message was queued
                if result.rc == mqtt.MQTT_ERR_SUCCESS:
                    print(f"Published payload to topic '{MQTT_TOPIC}'")
                else:
                    print("Failed to publish message to MQTT.")

            # Wait 5 seconds before the next poll
            time.sleep(5)

    except KeyboardInterrupt:
        print("\nStopping script gracefully...")
    finally:
        # 4. Clean up connections
        modbus_client.close()
        mqtt_client.loop_stop()
        mqtt_client.disconnect()
        print("Connections closed.")

if __name__ == "__main__":
    main()
