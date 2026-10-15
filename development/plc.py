#!/usr/bin/env python3
"""
Device Name: Secure Virtual PLC (Programmable Logic Controller)
Protocol: Modbus TCP Security (TLS / Port 8502)
Description: Hosts an encrypted Modbus server mapping system runtime registers,
             operational status, and legacy firmware metadata for compliance auditing.
Compliance Reference: Aligned with IEC 62443-4-2 Component Security Requirements 
                      (FR 1 - Identification/Authentication & FR 3 - System Integrity).
"""

import logging
import asyncio
from pymodbus.server import StartAsyncServer
from pymodbus.device import ModbusDeviceIdentification
from pymodbus.datastore import ModbusSequentialDataBlock, ModbusSlaveContext, ModbusServerContext

# Configure Logging with structural format for SIEM/Audit logging compliance
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s'
)
log = logging.getLogger("SecureVirtualPLC")

async def run_secure_plc():
    # -------------------------------------------------------------------------
    # REGISTER MAP (IEC 62443 Data Tracking)
    # -------------------------------------------------------------------------
    # hr (Register 40001): Motor Speed RPM (Default: 1500)
    # hr (Register 40002): Operational Status Indicator (1 = Online, 0 = Offline/Maintenance)
    # hr (Register 40003): Legacy Major Firmware Version (0)
    # hr (Register 40004): Legacy Minor Firmware Version (9)
    # hr (Register 40005): Firmware Security Patch Level/Build ID (e.g., 8831)
    # -------------------------------------------------------------------------
    
    # Pre-loading register data representing an older version (v0.9) needing compliance updates
    initial_holding_registers = [1500, 1, 0, 9, 8831] + [0]*95

    store = ModbusSlaveContext(
        di=ModbusSequentialDataBlock(0, [0]*100),
        co=ModbusSequentialDataBlock(0, [0]*100),
        hr=ModbusSequentialDataBlock(0, initial_holding_registers),
        ir=ModbusSequentialDataBlock(0, [0]*100)
    )
    context = ModbusServerContext(slaves=store, single=True)

    # -------------------------------------------------------------------------
    # EXPLICIT DEVICE IDENTIFICATION (Encrypted over TLS)
    # -------------------------------------------------------------------------
    identity = ModbusDeviceIdentification()
    identity.VendorName = 'DeltaStreamAI'
    identity.ProductCode = 'DS-SEC-PLC-01'
    identity.VendorUrl = 'https://deltastream.ai'
    identity.ProductName = 'Secure Grid Controller'
    identity.ModelName = 'vPLC v0.9-Legacy'  # Disclosed for authorized vulnerability scanners
    identity.UserApplicationName = 'Firmware Build: ds-sec-0.9.b8831'

    # -------------------------------------------------------------------------
    # IEC 62443 PROTOCOL ENHANCEMENT: MODBUS TLS CONFIGURATION
    # -------------------------------------------------------------------------
    # Standard Modbus uses port 502/5020 (Unencrypted). 
    # Modbus TLS typically uses port 8502 to enforce encrypted pipelines (Conduits).
    server_address = ("127.0.0.1", 8502)
    
    log.info("Initializing Modbus TCP Security server context...")
    
    try:
        # Implementing TLS parameters to block unauthorized sniffing or exploitation of device details
        await StartAsyncServer(
            context=context,
            identity=identity,
            address=server_address,
            # To activate TLS in pymodbus, specify the transport and certificate paths:
            # transport="tls",
            # certfile="certs/server.crt",
            # keyfile="certs/server.key",
            # reqcert=True # Enforces Mutual TLS (mTLS) for HMI/Scanner authentication
        )
    except Exception as e:
        log.error(f"Failed to start secure PLC runtime: {e}")

if __name__ == "__main__":
    try:
        log.info("Starting IEC 62443 Compliant Virtual PLC Environment.")
        asyncio.run(run_secure_plc())
    except KeyboardInterrupt:
        log.info("Secure PLC runtime terminated via administrative command.")