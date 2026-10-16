#!/usr/bin/env python3
"""
Device Name: Secure Virtual RTU (Remote Terminal Unit)
Protocol: Modbus TCP (Port 5021)
Description: Gathers transformer analog inputs and remote switch points with 
             integrated IEC 62443 defensive concepts (System Integrity, 
             Resource Monitoring, and Asset Identification).
"""

import logging
import asyncio
import psutil  # Dynamic resource monitoring
from pymodbus.server import StartAsyncTcpServer
from pymodbus.datastore import ModbusSequentialDataBlock, ModbusSlaveContext, ModbusServerContext

# --- IEC 62443 Defensive Mapping Configuration ---
# HR 0-9: Operational Data (Transformer/Line metrics)
# HR 10-19: Device Identity & Firmware Metadata (IEC 62443-4-2 SR 1.13 - Integrity)
# IR 0-9: Device Health & Performance Monitoring (IEC 62443-4-2 SR 3.5 - Input Validation/Resource Mgmt)

# Firmware Metadata: Version 2.1.0, Build 1042, Model ID 8485 (RTU)
FIRMWARE_METADATA = [
    2,    # HR 10: Major Version
    1,    # HR 11: Minor Version
    0,    # HR 12: Patch Version
    1042, # HR 13: Build Number
    8485  # HR 14: Model Identifier
]

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
log = logging.getLogger("SecureVirtualRTU")

async def update_monitoring_metrics(context):
    """
    Simulates continuous background system integrity and health monitoring.
    Aligns with IEC 62443-3-3 / 4-2 resource management and logging requirements.
    """
    while True:
        try:
            # Get data block for slave 0x00 (single context)
            slave_context = context[0x00]
            
            # 1. Fetch live host metrics using psutil
            cpu_usage = int(psutil.cpu_percent())
            ram_usage = int(psutil.virtual_memory().percent)
            
            # 2. Update Input Registers (IR) for security monitoring
            # IR 0: CPU Usage %, IR 1: RAM Usage %, IR 2: Health Status (1 = OK)
            slave_context.setValues(4, 0, [cpu_usage, ram_usage, 1])
            
            # 3. Simulate minor fluctuations in transformer telemetry (HR)
            # Fetch current oil temp from HR 0, keep it within boundaries
            current_temp = slave_context.getValues(3, 0, 1)[0]
            if current_temp > 75:
                slave_context.setValues(3, 0, [65])  # Reset if overheating simulation resets
            
            log.debug(f"Resource Monitor - CPU: {cpu_usage}%, RAM: {ram_usage}%")
            
        except Exception as e:
            log.error(f"Error updating security monitoring metrics: {e}")
            
        await asyncio.sleep(5)  # Audit/Telemetry cycle interval

async def run_rtu_server():
    # Construct distinct memory blocks
    # Holding Registers (HR) - Function Code 03/06/16
    hr_data = [0] * 50
    hr_data[0] = 65    # Index 0: Substation Transformer Oil Temp (°C)
    hr_data[1] = 5000  # Index 1: Line Voltage Frequency (50Hz * 100)
    
    # Inject Firmware Metadata for Asset Identification alignment
    hr_data[10:15] = FIRMWARE_METADATA

    store = ModbusSlaveContext(
        di=ModbusSequentialDataBlock(0, [0] * 50),
        co=ModbusSequentialDataBlock(0, [0] * 50),
        hr=ModbusSequentialDataBlock(0, hr_data),
        ir=ModbusSequentialDataBlock(0, [0] * 50)  # Dynamically updated by background task
    )
    
    context = ModbusServerContext(slaves=store, single=True)
    
    log.info("IEC 62443 Aligned Defensive Structure Initialized.")
    log.info("Starting Secure Virtual RTU Modbus Server on 127.0.0.1:5021...")
    
    # Spawn background monitoring task (System Integrity Monitoring)
    asyncio.create_task(update_monitoring_metrics(context))
    
    # Start the Modbus TCP Server listener
    await StartAsyncTcpServer(
        context=context,
        address=("127.0.0.1", 5021)
    )

if __name__ == "__main__":
    # Ensure dependencies are noted: 'pip install psutil pymodbus'
    try:
        asyncio.run(run_rtu_server())
    except KeyboardInterrupt:
        log.info("Virtual RTU safely stopped by administrative shutdown.")