#!/usr/bin/env python3
"""
Multi-Device Modbus RTU Scanner

This script scans for multiple Modbus RTU devices connected to a serial port
via RS485. It tests different unit IDs and function codes to identify all
connected devices.
"""

import sys
import logging
import argparse
from typing import List, Dict, Any, Tuple

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("ModbusScanner")

# Import the ModbusRTU client
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from modapi.api.rtu import ModbusRTU


def scan_device(client: ModbusRTU, unit_id: int) -> Dict[str, Any]:
    """
    Scan a specific unit ID for supported function codes and register ranges
    
    Args:
        client: ModbusRTU client instance
        unit_id: Unit ID to scan
        
    Returns:
        Dict with device information and supported functions
    """
    device_info = {
        "unit_id": unit_id,
        "connected": False,
        "supported_functions": [],
        "coils": None,
        "discrete_inputs": None,
        "holding_registers": None,
        "input_registers": None,
    }
    
    # Test connection by reading first coil
    logger.info(f"Testing connection to unit ID {unit_id}...")
    
    # Test read_coils (function code 0x01)
    try:
        result = client.read_coils(unit_id=unit_id, address=0, count=1)
        if result is not None:
            device_info["connected"] = True
            device_info["supported_functions"].append("read_coils")
            device_info["coils"] = result
            logger.info(f"Unit {unit_id}: read_coils supported, result: {result}")
    except Exception as e:
        logger.debug(f"Unit {unit_id}: read_coils failed: {e}")
    
    # Test read_discrete_inputs (function code 0x02)
    try:
        result = client.read_discrete_inputs(unit_id=unit_id, address=0, count=1)
        if result is not None:
            device_info["connected"] = True
            device_info["supported_functions"].append("read_discrete_inputs")
            device_info["discrete_inputs"] = result
            logger.info(f"Unit {unit_id}: read_discrete_inputs supported, result: {result}")
    except Exception as e:
        logger.debug(f"Unit {unit_id}: read_discrete_inputs failed: {e}")
    
    # Test read_holding_registers (function code 0x03)
    try:
        result = client.read_holding_registers(unit_id=unit_id, address=0, count=1)
        if result is not None:
            device_info["connected"] = True
            device_info["supported_functions"].append("read_holding_registers")
            device_info["holding_registers"] = result
            logger.info(f"Unit {unit_id}: read_holding_registers supported, result: {result}")
    except Exception as e:
        logger.debug(f"Unit {unit_id}: read_holding_registers failed: {e}")
    
    # Test read_input_registers (function code 0x04)
    try:
        result = client.read_input_registers(unit_id=unit_id, address=0, count=1)
        if result is not None:
            device_info["connected"] = True
            device_info["supported_functions"].append("read_input_registers")
            device_info["input_registers"] = result
            logger.info(f"Unit {unit_id}: read_input_registers supported, result: {result}")
    except Exception as e:
        logger.debug(f"Unit {unit_id}: read_input_registers failed: {e}")
    
    return device_info


def scan_unit_id_range(client: ModbusRTU, start_id: int = 1, end_id: int = 10) -> List[Dict[str, Any]]:
    """
    Scan a range of unit IDs for Modbus devices
    
    Args:
        client: ModbusRTU client instance
        start_id: Starting unit ID
        end_id: Ending unit ID
        
    Returns:
        List of dictionaries with device information
    """
    devices = []
    
    for unit_id in range(start_id, end_id + 1):
        logger.info(f"Scanning unit ID {unit_id}...")
        device_info = scan_device(client, unit_id)
        
        if device_info["connected"]:
            devices.append(device_info)
            logger.info(f"Found device at unit ID {unit_id}")
            logger.info(f"Supported functions: {device_info['supported_functions']}")
        else:
            logger.info(f"No device found at unit ID {unit_id}")
    
    return devices


def main():
    """Main function to run the scanner"""
    parser = argparse.ArgumentParser(description='Modbus RTU Multi-Device Scanner')
    parser.add_argument('--port', type=str, default='/dev/ttyACM0',
                        help='Serial port to use (default: /dev/ttyACM0)')
    parser.add_argument('--baudrate', type=int, default=9600,
                        help='Baudrate to use (default: 9600)')
    parser.add_argument('--timeout', type=float, default=1.0,
                        help='Communication timeout in seconds (default: 1.0)')
    parser.add_argument('--start-id', type=int, default=1,
                        help='Starting unit ID to scan (default: 1)')
    parser.add_argument('--end-id', type=int, default=10,
                        help='Ending unit ID to scan (default: 10)')
    parser.add_argument('--debug', action='store_true',
                        help='Enable debug logging')
    
    args = parser.parse_args()
    
    if args.debug:
        logger.setLevel(logging.DEBUG)
    
    logger.info(f"Starting Modbus RTU scanner on {args.port} at {args.baudrate} baud")
    logger.info(f"Scanning unit IDs from {args.start_id} to {args.end_id}")
    
    # Create and connect ModbusRTU client
    client = ModbusRTU(
        port=args.port,
        baudrate=args.baudrate,
        timeout=args.timeout
    )
    
    if not client.connect():
        logger.error(f"Failed to connect to {args.port}")
        return 1
    
    try:
        # Scan for devices
        devices = scan_unit_id_range(client, args.start_id, args.end_id)
        
        # Print results
        logger.info("\n--- SCAN RESULTS ---")
        if devices:
            logger.info(f"Found {len(devices)} Modbus RTU device(s):")
            for device in devices:
                logger.info(f"Unit ID: {device['unit_id']}")
                logger.info(f"  Supported functions: {device['supported_functions']}")
                if 'read_coils' in device['supported_functions']:
                    logger.info(f"  Coils: {device['coils']}")
                if 'read_discrete_inputs' in device['supported_functions']:
                    logger.info(f"  Discrete inputs: {device['discrete_inputs']}")
                if 'read_holding_registers' in device['supported_functions']:
                    logger.info(f"  Holding registers: {device['holding_registers']}")
                if 'read_input_registers' in device['supported_functions']:
                    logger.info(f"  Input registers: {device['input_registers']}")
        else:
            logger.info("No Modbus RTU devices found.")
    
    finally:
        # Disconnect client
        client.disconnect()
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
