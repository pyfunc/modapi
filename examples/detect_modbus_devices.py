#!/usr/bin/env python3
"""
Modbus Device Detection Tool
Scans serial ports for Modbus RTU devices and detects their unit IDs
"""

import os
import sys
import time
import logging
from typing import Dict, List, Tuple, Optional

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from modapi.api.rtu import ModbusRTU, find_serial_ports

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("modbus_detector")

def detect_devices(ports: Optional[List[str]] = None, 
                  baudrates: Optional[List[int]] = None,
                  unit_ids: Optional[List[int]] = None,
                  timeout: float = 0.5) -> Dict[str, List[int]]:
    """
    Scan ports for Modbus devices and detect their unit IDs
    
    Args:
        ports: List of ports to scan (default: auto-detect)
        baudrates: List of baudrates to try (default: [9600, 19200, 38400])
        unit_ids: List of unit IDs to scan (default: 1-10)
        timeout: Timeout for each test in seconds
        
    Returns:
        Dict mapping port to list of detected unit IDs
    """
    # Default values
    if ports is None:
        ports = find_serial_ports()
    
    if baudrates is None:
        baudrates = [9600, 19200, 38400]
    
    if unit_ids is None:
        unit_ids = list(range(1, 11))  # Test unit IDs 1-10 by default
    
    results = {}
    
    print(f"Starting scan of {len(ports)} ports with {len(baudrates)} baudrates and {len(unit_ids)} unit IDs")
    print("This may take some time...")
    
    # Scan each port
    for port in ports:
        print(f"\nScanning port: {port}")
        port_results = []
        
        # Try each baudrate
        for baudrate in baudrates:
            print(f"  Testing baudrate: {baudrate}...")
            
            try:
                # Create client with the current baudrate
                client = ModbusRTU(port=port, baudrate=baudrate, timeout=timeout)
                if not client.connect():
                    print(f"  Could not connect to {port} at {baudrate} baud")
                    continue
                
                # Test each unit ID
                for unit_id in unit_ids:
                    try:
                        # Try reading coils (most common)
                        coil_result = client.read_coils(unit_id=unit_id, address=0, count=1)
                        if coil_result is not None:
                            print(f"  ✓ Found Modbus device at {port}, {baudrate} baud, Unit ID: {unit_id} (coils)")
                            if unit_id not in port_results:
                                port_results.append((unit_id, baudrate, "coils"))
                            continue
                    except Exception:
                        pass
                    
                    try:
                        # Try reading holding registers
                        reg_result = client.read_holding_registers(unit_id=unit_id, address=0, count=1)
                        if reg_result is not None:
                            print(f"  ✓ Found Modbus device at {port}, {baudrate} baud, Unit ID: {unit_id} (registers)")
                            if unit_id not in port_results:
                                port_results.append((unit_id, baudrate, "registers"))
                            continue
                    except Exception:
                        pass
                    
                    try:
                        # Try reading discrete inputs
                        di_result = client.read_discrete_inputs(unit_id=unit_id, address=0, count=1)
                        if di_result is not None:
                            print(f"  ✓ Found Modbus device at {port}, {baudrate} baud, Unit ID: {unit_id} (discrete inputs)")
                            if unit_id not in port_results:
                                port_results.append((unit_id, baudrate, "discrete_inputs"))
                            continue
                    except Exception:
                        pass
                    
                    try:
                        # Try reading input registers
                        ir_result = client.read_input_registers(unit_id=unit_id, address=0, count=1)
                        if ir_result is not None:
                            print(f"  ✓ Found Modbus device at {port}, {baudrate} baud, Unit ID: {unit_id} (input registers)")
                            if unit_id not in port_results:
                                port_results.append((unit_id, baudrate, "input_registers"))
                            continue
                    except Exception:
                        pass
                
                # Close the connection
                client.close()
                
            except Exception as e:
                print(f"  Error testing {port} at {baudrate} baud: {e}")
        
        # Store results for this port
        if port_results:
            results[port] = port_results
    
    return results

def print_summary(results: Dict[str, List[Tuple[int, int, str]]]):
    """Print a summary of detected devices"""
    print("\n" + "="*60)
    print("MODBUS DEVICE DETECTION SUMMARY")
    print("="*60)
    
    if not results:
        print("No Modbus devices detected.")
        return
    
    for port, devices in results.items():
        print(f"\nPort: {port}")
        print("-" * 40)
        
        for unit_id, baudrate, device_type in devices:
            print(f"  Unit ID: {unit_id}, Baudrate: {baudrate}, Type: {device_type}")
    
    print("\n" + "="*60)

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Detect Modbus RTU devices')
    parser.add_argument('--ports', nargs='+', help='Serial ports to scan (default: auto-detect)')
    parser.add_argument('--baudrates', type=int, nargs='+', default=[9600, 19200, 38400], 
                        help='Baudrates to test (default: 9600, 19200, 38400)')
    parser.add_argument('--unit-ids', type=int, nargs='+', 
                        help='Unit IDs to scan (default: 1-10)')
    parser.add_argument('--timeout', type=float, default=0.5,
                        help='Timeout for each test in seconds (default: 0.5)')
    
    args = parser.parse_args()
    
    # Convert unit ID range if not specified
    if args.unit_ids is None:
        args.unit_ids = list(range(1, 11))
    
    # Run detection
    print("Starting Modbus device detection...")
    results = detect_devices(
        ports=args.ports,
        baudrates=args.baudrates,
        unit_ids=args.unit_ids,
        timeout=args.timeout
    )
    
    # Print summary
    print_summary(results)
