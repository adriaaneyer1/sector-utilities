#!/usr/bin/env python3
"""
Device Name: Secure Virtual PDU (Power Distribution Unit)
Protocol: Raw TCP Socket (Port 4001) with Authentication
Description: Emulates a hardened rack PDU supporting secure role-based controls,
             comprehensive audit logging, and structured firmware metadata 
             aligned with IEC 62443 defensive concepts.
"""

import socket
import logging
import threading
import datetime

# --- IEC 62443 Compliance & Metadata ---
# CR 1.1 & CR 1.2: Identification and Authentication Control
# CR 3.9: Audit Review / Structured Security Event Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] [IEC62443-EVENT]: %(message)s'
)
log = logging.getLogger("SecurePDU")

# Component Requirements (Asset Identification)
FIRMWARE_METADATA = {
    "Vendor": "SecureControls Corp",
    "Model": "PDU-Net-X4",
    "FirmwareVersion": "v5.0.1-Hardened",
    "BuildDate": "2026-10-14",
    "IEC62443_Compliance": "Level 2 Ready"
}

# Simple credential store demonstrating Role-Based Access Control (CR 2.1)
USER_DB = {
    "operator": {"password": "OperatorPassword123!", "role": "operator"}, # Read-only
    "admin": {"password": "AdminSecureCrypto99!", "role": "admin"}        # Read & Write
}

# System State (Protected Resources)
outlets = {"1": "ON", "2": "ON", "3": "OFF", "4": "ON"}

def authenticate_client(client_socket):
    """
    Implements a secure baseline login sequence.
    Removes legacy backdoors/bypass banners completely.
    """
    client_socket.sendall(b"--- Secure PDU Access Portal ---\nUsername: ")
    user_bytes = client_socket.recv(1024)
    if not user_bytes:
        return None, None
    username = user_bytes.decode('utf-8').strip()

    client_socket.sendall(b"Password: ")
    pass_bytes = client_socket.recv(1024)
    if not pass_bytes:
        return None, None
    password = pass_bytes.decode('utf-8').strip()

    if username in USER_DB and USER_DB[username]["password"] == password:
        role = USER_DB[username]["role"]
        return username, role
    
    return None, None

def handle_pdu_client(client_socket, address):
    log.info(f"Connection attempt initiated from network address: {address}")
    
    username, role = authenticate_client(client_socket)
    if not username:
        log.warning(f"UNAUTHORIZED ACCESS ATTEMPT: Failed authentication from {address}")
        client_socket.sendall(b"Access Denied. Terminating session.\n")
        client_socket.close()
        return

    log.info(f"Session established. User: '{username}' authenticated with Role: '{role}' from {address}")
    
    # Session Banner containing required hardware/firmware context
    banner = (
        f"\nConnected to {FIRMWARE_METADATA['Vendor']} {FIRMWARE_METADATA['Model']}\n"
        f"Firmware: {FIRMWARE_METADATA['FirmwareVersion']} ({FIRMWARE_METADATA['IEC62443_Compliance']})\n"
        f"Authorized Session: {username} [{role}]\n"
        f"Available commands: 'read metadata', 'read all', 'switch <outlet_num> <ON/OFF>', 'exit'\n> "
    )
    client_socket.sendall(banner.encode('utf-8'))

    try:
        while True:
            data = client_socket.recv(1024)
            if not data:
                break
            
            command = data.decode('utf-8').strip().lower()
            if not command:
                client_socket.sendall(b"> ")
                continue
                
            resp = ""
            
            # --- Command Handling & Access Enforcement ---
            if command == "read metadata":
                resp = "\n".join([f"{k}: {v}" for k, v in FIRMWARE_METADATA.items()]) + "\n"
                log.info(f"Audit [Read]: User '{username}' retrieved device metadata.")
                
            elif command == "read all":
                # Both roles are authorized to inspect status metrics
                resp = "\n".join([f"Outlet {k}: {v} [Amps: 1.2A]" for k, v in outlets.items()]) + "\n"
                log.info(f"Audit [Read]: User '{username}' requested data metrics.")
                
            elif command.startswith("switch "):
                # CR 2.1 Use Control (Enforcing Role Limits)
                if role != "admin":
                    resp = "ACCESS DENIED: Role 'operator' has read-only restrictions.\n"
                    log.warning(f"Audit [Violation]: User '{username}' attempted restricted outlet switching.")
                else:
                    parts = command.split()
                    if len(parts) == 3 and parts[1] in outlets and parts[2] in ["on", "off"]:
                        old_state = outlets[parts[1]]
                        new_state = parts[2].upper()
                        outlets[parts[1]] = new_state
                        resp = f"SUCCESS: Outlet {parts[1]} changed from {old_state} to {new_state}\n"
                        log.info(f"Audit [Write]: User '{username}' modified Outlet {parts[1]} to {new_state}.")
                    else:
                        resp = "ERROR: Formatting failed. Use 'switch <1-4> <on/off>'\n"
                        
            elif command == "exit":
                log.info(f"Session closed cleanly by user '{username}'.")
                break
            else:
                resp = "Unknown PDU Command.\n"
                
            client_socket.sendall(resp.encode('utf-8') + b"> ")
            
    except Exception as e:
        log.error(f"Session error encountered with client {address}: {str(e)}")
    finally:
        client_socket.close()

def main():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    
    # Binding locally for simulation safety
    server.bind(("127.0.0.1", 4001))
    server.listen(5)
    log.info(f"Hardened Virtual PDU listening securely on port 4001...")
    
    try:
        while True:
            client_sock, addr = server.accept()
            # Spawn a thread isolated per user session
            threading.Thread(target=handle_pdu_client, args=(client_sock, addr), daemon=True).start()
    except KeyboardInterrupt:
        log.info("PDU Engine safely shutting down.")
    finally:
        server.close()

if __name__ == "__main__":
    main()
