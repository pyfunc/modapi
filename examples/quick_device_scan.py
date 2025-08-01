#!/usr/bin/env python3
"""
Quick Modbus Device Scanner
Scans for Modbus RTU devices on common serial ports
"""

import os
import sys
import logging
from typing import List, Dict, Tuple

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from modapi.api.rtu import ModbusRTU, find_serial_ports

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("modbus_scanner")

def scan_ports() -> List[str]:
    """Find all available serial ports"""
    ports = find_serial_ports()
    print(f"Found {len(ports)} serial ports: {', '.join(ports)}")
    return ports

def scan_device(port: str, baudrate: int = 9600) -> List[Tuple[int, str]]:
    """
    Scan a single port for Modbus devices
    
    Args:
        port: Serial port to scan
        baudrate: Baudrate to use
        
    Returns:
        List of (unit_id, type) tuples for detected devices
    """
    devices = []
    print(f"Scanning {port} at {baudrate} baud...")
    
    try:
        client = ModbusRTU(port=port, baudrate=baudrate, timeout=0.3)
        if not client.connect():
            print(f"Could not connect to {port}")
            return []
        
        # Scan unit IDs 1-10
        for unit_id in range(1, 11):
            print(f"  Testing Unit ID: {unit_id}...", end="", flush=True)
            
            # Try reading coils first (most common)
            try:
                result = client.read_coils(unit_id=unit_id, address=0, count=1)
                if result is not None:
                    print(f" FOUND! (coils)")
                    devices.append((unit_id, "coils"))
                    continue
            except Exception:
                pass
            
            # Try reading holding registers
            try:
                result = client.read_holding_registers(unit_id=unit_id, address=0, count=1)
                if result is not None:
                    print(f" FOUND! (registers)")
                    devices.append((unit_id, "registers"))
                    continue
            except Exception:
                pass
                
            print(" not found")
            
        client.close()
        
    except Exception as e:
        print(f"Error scanning {port}: {e}")
    
    return devices

def main():
    """Main function"""
    print("=== MODBUS DEVICE SCANNER ===")
    
    # Find all available ports
    ports = scan_ports()
    
    if not ports:
        print("No serial ports found!")
        return
    
    # Scan each port
    results = {}
    for port in ports:
        devices = scan_device(port)
        if devices:
            results[port] = devices
    
    # Print summary
    print("\n=== SCAN RESULTS ===")
    if not results:
        print("No Modbus devices found on any port.")
    else:
        for port, devices in results.items():
            print(f"\nPort: {port}")
            print("-" * 30)
            for unit_id, device_type in devices:
                print(f"  Unit ID: {unit_id}, Type: {device_type}")

if __name__ == "__main__":
    main()
