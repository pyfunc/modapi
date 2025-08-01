#!/usr/bin/env python3
"""
RS485 Modbus Device Finder
Scans for Modbus RTU devices on RS485 ports with configurable parameters
"""

import os
import sys
import time
import logging
from typing import List, Dict, Tuple, Optional

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from modapi.rtu import ModbusRTU, find_serial_ports

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("rs485_finder")

def scan_for_devices(ports: Optional[List[str]] = None, 
                    baudrates: List[int] = [19200, 38400],
                    unit_ids: List[int] = [1, 2, 3, 4, 5],
                    timeout: float = 0.3) -> Dict[str, List[Dict[str, any]]]:
    """
    Scan for Modbus devices on RS485 ports
    
    Args:
        ports: List of ports to scan (None for auto-detection)
        baudrates: List of baudrates to try
        unit_ids: List of unit IDs to scan
        timeout: Communication timeout in seconds
        
    Returns:
        Dictionary mapping ports to lists of device info
    """
    if ports is None:
        ports = find_serial_ports()
        print(f"Auto-detected ports: {', '.join(ports)}")
    
    results = {}
    
    for port in ports:
        print(f"\nScanning port: {port}")
        port_devices = []
        
        for baudrate in baudrates:
            print(f"  Testing baudrate: {baudrate}")
            
            # Create client with current baudrate
            client = None
            try:
                client = ModbusRTU(port=port, baudrate=baudrate, timeout=timeout)
                if not client.connect():
                    print(f"  Could not connect to {port} at {baudrate} baud")
                    continue
                
                # Test each unit ID
                for unit_id in unit_ids:
                    device_info = test_unit_id(client, unit_id)
                    if device_info:
                        device_info['baudrate'] = baudrate
                        port_devices.append(device_info)
                        print(f"  ✓ Found device: Unit ID {unit_id}, Type: {device_info['type']}")
            
            except Exception as e:
                print(f"  Error on {port} at {baudrate} baud: {e}")
            
            finally:
                # Always disconnect when done with this baudrate
                if client and client.is_connected():
                    client.disconnect()
        
        if port_devices:
            results[port] = port_devices
    
    return results

def test_unit_id(client: ModbusRTU, unit_id: int) -> Optional[Dict[str, any]]:
    """Test if a unit ID responds to Modbus requests"""
    
    # Try reading coils (function code 0x01)
    try:
        result = client.read_coils(unit_id=unit_id, address=0, count=1)
        if result is not None:
            return {'unit_id': unit_id, 'type': 'coil', 'supports_coils': True}
    except Exception:
        pass
    
    # Try reading holding registers (function code 0x03)
    try:
        result = client.read_holding_registers(unit_id=unit_id, address=0, count=1)
        if result is not None:
            return {'unit_id': unit_id, 'type': 'holding_register', 'supports_registers': True}
    except Exception:
        pass
    
    # Try reading discrete inputs (function code 0x02)
    try:
        result = client.read_discrete_inputs(unit_id=unit_id, address=0, count=1)
        if result is not None:
            return {'unit_id': unit_id, 'type': 'discrete_input', 'supports_discrete_inputs': True}
    except Exception:
        pass
    
    # Try reading input registers (function code 0x04)
    try:
        result = client.read_input_registers(unit_id=unit_id, address=0, count=1)
        if result is not None:
            return {'unit_id': unit_id, 'type': 'input_register', 'supports_input_registers': True}
    except Exception:
        pass
    
    return None

def print_results(results: Dict[str, List[Dict[str, any]]]):
    """Print scan results in a readable format"""
    print("\n" + "="*50)
    print(" RS485 MODBUS DEVICE SCAN RESULTS")
    print("="*50)
    
    if not results:
        print("\nNo Modbus devices found on any port.")
        return
    
    for port, devices in results.items():
        print(f"\nPort: {port}")
        print("-" * 40)
        
        for device in devices:
            print(f"  Unit ID: {device['unit_id']}")
            print(f"  Baudrate: {device['baudrate']}")
            print(f"  Type: {device['type']}")
            print()

def main():
    """Main function"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Find RS485 Modbus devices')
    parser.add_argument('--ports', nargs='+', help='Serial ports to scan (default: auto-detect)')
    parser.add_argument('--baudrates', type=int, nargs='+', default=[19200, 38400],
                        help='Baudrates to test (default: 9600, 19200, 38400)')
    parser.add_argument('--unit-ids', type=int, nargs='+', default=list(range(1, 6)),
                        help='Unit IDs to scan (default: 1-5)')
    parser.add_argument('--timeout', type=float, default=0.3,
                        help='Timeout for each test in seconds (default: 0.3)')
    
    args = parser.parse_args()
    
    print("Starting RS485 Modbus device scan...")
    results = scan_for_devices(
        ports=args.ports,
        baudrates=args.baudrates,
        unit_ids=args.unit_ids,
        timeout=args.timeout
    )
    
    print_results(results)

if __name__ == "__main__":
    main()
