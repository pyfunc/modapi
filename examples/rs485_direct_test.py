#!/usr/bin/env python3
"""
Direct RS485 Test Script
Tests specific RS485 parameters for device detection
"""

import os
import sys
import time
import logging
from typing import List, Optional

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from modapi.rtu import ModbusRTU

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,  # Set to DEBUG for more detailed logs
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("rs485_test")

def test_device(port: str, baudrate: int, unit_id: int, parity: str = 'N', 
                stopbits: int = 1, bytesize: int = 8, timeout: float = 1.0):
    """
    Test a specific device with exact parameters
    
    Args:
        port: Serial port path
        baudrate: Baud rate
        unit_id: Modbus unit ID
        parity: Parity (N/E/O)
        stopbits: Stop bits (1 or 2)
        bytesize: Data bits (7 or 8)
        timeout: Communication timeout in seconds
    """
    print(f"\n=== Testing device on {port} ===")
    print(f"Parameters: {baudrate} baud, Unit ID: {unit_id}, Parity: {parity}, "
          f"Stop bits: {stopbits}, Data bits: {bytesize}, Timeout: {timeout}s")
    
    client = None
    try:
        # Create client with specific parameters
        client = ModbusRTU(
            port=port,
            baudrate=baudrate,
            timeout=timeout,
            parity=parity,
            stopbits=stopbits,
            bytesize=bytesize
        )
        
        # Connect to device
        print("Connecting to device...")
        if not client.connect():
            print("Failed to connect!")
            return
        
        print("Connected successfully!")
        
        # Clear buffers before sending commands
        if client.serial_conn:
            client.serial_conn.reset_input_buffer()
            client.serial_conn.reset_output_buffer()
        
        # Test connection
        print(f"Testing connection to unit ID {unit_id}...")
        success, _ = client.test_connection(unit_id=unit_id)
        if success:
            print("✓ Connection test successful!")
        else:
            print("✗ Connection test failed!")
        
        # Try reading coils
        print("\nTrying to read coils...")
        try:
            result = client.read_coils(unit_id=unit_id, address=0, count=1)
            if result is not None:
                print(f"✓ Read coils successful: {result}")
            else:
                print("✗ Read coils failed with None result")
        except Exception as e:
            print(f"✗ Read coils error: {e}")
        
        # Try reading holding registers
        print("\nTrying to read holding registers...")
        try:
            result = client.read_holding_registers(unit_id=unit_id, address=0, count=1)
            if result is not None:
                print(f"✓ Read holding registers successful: {result}")
            else:
                print("✗ Read holding registers failed with None result")
        except Exception as e:
            print(f"✗ Read holding registers error: {e}")
        
        # Try reading discrete inputs
        print("\nTrying to read discrete inputs...")
        try:
            result = client.read_discrete_inputs(unit_id=unit_id, address=0, count=1)
            if result is not None:
                print(f"✓ Read discrete inputs successful: {result}")
            else:
                print("✗ Read discrete inputs failed with None result")
        except Exception as e:
            print(f"✗ Read discrete inputs error: {e}")
        
        # Try reading input registers
        print("\nTrying to read input registers...")
        try:
            result = client.read_input_registers(unit_id=unit_id, address=0, count=1)
            if result is not None:
                print(f"✓ Read input registers successful: {result}")
            else:
                print("✗ Read input registers failed with None result")
        except Exception as e:
            print(f"✗ Read input registers error: {e}")
            
    except Exception as e:
        print(f"Error during test: {e}")
    
    finally:
        # Always disconnect
        if client and client.is_connected():
            print("\nDisconnecting...")
            client.disconnect()
            print("Disconnected")

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Test RS485 Modbus device with specific parameters')
    parser.add_argument('--port', default='/dev/ttyACM0', help='Serial port path')
    parser.add_argument('--baudrate', type=int, default=9600, help='Baud rate')
    parser.add_argument('--unit-id', type=int, default=1, help='Unit ID')
    parser.add_argument('--parity', choices=['N', 'E', 'O'], default='N', help='Parity (N/E/O)')
    parser.add_argument('--stopbits', type=int, choices=[1, 2], default=1, help='Stop bits')
    parser.add_argument('--bytesize', type=int, choices=[7, 8], default=8, help='Data bits')
    parser.add_argument('--timeout', type=float, default=1.0, help='Timeout in seconds')
    
    args = parser.parse_args()
    
    test_device(
        port=args.port,
        baudrate=args.baudrate,
        unit_id=args.unit_id,
        parity=args.parity,
        stopbits=args.stopbits,
        bytesize=args.bytesize,
        timeout=args.timeout
    )
