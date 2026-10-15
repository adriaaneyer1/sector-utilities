#!/usr/bin/env python3
"""
Device Name: Virtual Terminal Server
Protocol: Raw TCP Socket (Port 4000)
Description: Emulates a secure serial port management server accepting commands,
             hardened according to IEC 62443 foundational requirements (FRs).
"""

import socket
import logging
import threading
import sys
from datetime import datetime

# ==============================================================================
# 🛡️ IEC 62443 METADATA & CONFIGURATION
# ==============================================================================
# FR 4 (Data Integrity) & FR 7 (Resource Availability) Reference Parameters
FIRMWARE_METADATA = {
    "device_type": "Virtual Terminal Server",
    "firmware_version": "v2.1.0-secure",
    "build_date": "2026-10-14",
    "security_profile": "IEC-62443-4-2-SL3",
    "integrity_hash": "SHA256:8f43a9d4...e3b1a82c"
}

# Network Zoning (IEC 62443-3-3: Zone & Conduit Model)
# Restricting listening interface strictly to the designated control zone
BIND_HOST = "127.0.0.1"  
BIND_PORT = 4000

# FR 7: Resource Management Protection
MAX_CONNECTIONS = 3  
MAX_BUFFER_SIZE = 512  # Strict input constraint to mitigate buffer overflow vectors
connection_counter = 0
counter_lock = threading.Lock()

# FR 6: Auditing & Security Logs
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [IEC-62443-AUDIT] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
log = logging.getLogger("SecureTerminalServer")

# ==============================================================================
# 🛠️ SECURITY MONITORING & ACCESS FUNCTIONS
# ==============================================================================
def log_security_event(event_id, severity, message):
    """Formats logs to support SIEM ingestion for IEC 62443 compliance."""
    log.info(f"ID={event_id} | SEVERITY={severity} | MSG={message}")

def check_access_control(address):
    """
    Simulates FR 1 (Identification & Authentication Control) 
    and Zone enforcement.
    """
    # Defensive logic: Enforce local zone/conduit boundaries
    if address[0] != "127.0.0.1":
        log_security_event("E1001", "CRITICAL", f"Zone violation attempted from unauthorized conduit: {address[0]}")
        return False
    return True

# ==============================================================================
# 🎮 CLIENT HANDLING PROTOCOL (CONDUIT PIPELINE)
# ==============================================================================
def handle_client(client_socket, address):
    global connection_counter
    
    if not check_access_control(address):
        client_socket.close()
        return

    log_security_event("E1002", "INFO", f"Authenticated connection established from {address}")
    
    # Send secure welcome banner containing firmware metadata (FR 4 / Asset Identification)
    banner = (
        f"--- DeltaStream AI Virtual Terminal Server Console ---\n"
        f"Firmware: {FIRMWARE_METADATA['firmware_version']} | Security Level: {FIRMWARE_METADATA['security_profile']}\n"
        f"Type 'help' for options.\n> "
    )
    try:
        client_socket.sendall(banner.encode('utf-8'))
        
        while True:
            # FR 7: Enforce fixed bounds on stream processing window size
            data = client_socket.recv(MAX_BUFFER_SIZE)
            if not data:
                break
                
            # Treat decoded data with defensive validation layers
            try:
                command = data.decode('utf-8', errors='ignore').strip().lower()
            except Exception:
                log_security_event("E1004", "WARNING", f"Malformed payload rejected from {address}")
                client_socket.sendall(b"Error: Invalid Encoding.\n> ")
                continue

            if not command:
                client_socket.sendall(b"> ")
                continue
                
            # Log command execution for non-repudiation and audit tracks
            log_security_event("E1003", "LOW", f"Command executed by {address}: '{command}'")

            # Command Processor (State Engine)
            if command == "help":
                response = (
                    "Available Commands:\n"
                    " - status : Show active virtual serial bridges\n"
                    " - info   : Display cryptographic firmware metadata\n"
                    " - reset  : Cycle line configuration\n"
                    " - exit   : Terminate stream\n"
                )
            elif command == "info":
                response = (
                    f"Device Type : {FIRMWARE_METADATA['device_type']}\n"
                    f"Build Date  : {FIRMWARE_METADATA['build_date']}\n"
                    f"FW Integrity: {FIRMWARE_METADATA['integrity_hash']}\n"
                )
            elif command == "status":
                response = "LINE 1: Connected (PLC_COM) | LINE 2: Idle | LINE 3: Connected (RTU_TTY)\n"
            elif command == "reset":
                log_security_event("E1005", "MEDIUM", f"Line reset triggered by administrative terminal at {address}")
                response = "Command acknowledged. Purging TX/RX memory lines...\n"
            elif command == "exit":
                client_socket.sendall(b"Goodbye.\n")
                break
            else:
                response = f"Error: Command '{command}' unrecognized by serial firmware.\n"
                log_security_event("E1006", "LOW", f"Invalid command entry attempted by {address}")

            client_socket.sendall(response.encode('utf-8') + b"> ")
            
    except Exception as e:
        log_security_event("E1000", "HIGH", f"Exception during serial communication tracking {address}: {e}")
    finally:
        client_socket.close()
        with counter_lock:
            connection_counter -= 1
        log_security_event("E1007", "INFO", f"Conduit disconnected safely from {address}. Active slots: {connection_counter}")

# ==============================================================================
# 🚀 MAIN INDUSTRIAL RUNTIME ENVIRONMENT
# ==============================================================================
def main():
    global connection_counter
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    
    try:
        server.bind((BIND_HOST, BIND_PORT))
        server.listen(5)
        log_security_event("E0001", "INFO", f"Secure Industrial Terminal Gateway running on {BIND_HOST}:{BIND_PORT}")
        
        while True:
            client_sock, addr = server.accept()
            
            # FR 7: Resource Exhaustion Prevention Strategy
            with counter_lock:
                if connection_counter >= MAX_CONNECTIONS:
                    log_security_event("E7001", "HIGH", f"Connection rejected from {addr}. Max pool threshold reached ({MAX_CONNECTIONS})")
                    client_sock.sendall(b"Server Busy: IEC 62443 Max Connection Cap Exceeded.\n")
                    client_sock.close()
                    continue
                connection_counter += 1
            
            client_thread = threading.Thread(target=handle_client, args=(client_sock, addr))
            client_thread.daemon = True
            client_thread.start()
            
    except KeyboardInterrupt:
        log_security_event("E0002", "INFO", "Graceful system shutdown initiated by control system room operator.")
    except Exception as e:
        log_security_event("E0003", "CRITICAL", f"Fatal runtime failure: {e}")
    finally:
        server.close()

if __name__ == "__main__":
    main()