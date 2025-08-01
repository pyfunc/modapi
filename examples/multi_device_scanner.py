#!/usr/bin/env python3
"""
Multi-Device Modbus RTU Scanner

This script scans for multiple Modbus RTU devices connected to a serial port
via RS485. It tests different unit IDs and function codes to identify all
connected devices, with special support for Waveshare Modbus RTU modules.
"""

import sys
import logging
import argparse
import time
from typing import List, Dict, Any, Tuple, Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("ModbusScanner")

# Import the ModbusRTU client
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from modapi.rtu import ModbusRTU


# Waveshare Modbus RTU Analog Input 8CH specific register addresses
WAVESHARE_ANALOG_INPUT_REGISTERS = {
    "device_address": 0x0100,  # Register to read/write device address
    "software_version": 0x0101,  # Register to read software version
    "analog_inputs": [0x0000, 0x0001, 0x0002, 0x0003, 0x0004, 0x0005, 0x0006, 0x0007]  # Analog input registers
}

def test_function_with_retries(client: ModbusRTU, unit_id: int, function_name: str, 
                             address: int, count: int, max_retries: int = 2) -> Tuple[bool, Optional[Any]]:
    """
    Test a specific Modbus function with retries
    
    Args:
        client: ModbusRTU client instance
        unit_id: Unit ID to test
        function_name: Name of the function to test (read_coils, etc.)
        address: Register/coil address to read
        count: Number of registers/coils to read
        max_retries: Maximum number of retries
        
    Returns:
        Tuple of (success, result)
    """
    retries = 0
    while retries <= max_retries:
        try:
            # Get the function by name
            func = getattr(client, function_name)
            # Call the function
            result = func(unit_id=unit_id, address=address, count=count)
            
            if result is not None:
                return True, result
            
            logger.debug(f"Unit {unit_id}: {function_name}(address={address}, count={count}) returned None (attempt {retries+1}/{max_retries+1})")
            retries += 1
            time.sleep(0.1)  # Short delay between retries
        except Exception as e:
            logger.debug(f"Unit {unit_id}: {function_name}(address={address}, count={count}) failed: {e} (attempt {retries+1}/{max_retries+1})")
            retries += 1
            time.sleep(0.1)  # Short delay between retries
    
    return False, None

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
        "device_type": "unknown",
        "supported_functions": [],
        "coils": None,
        "discrete_inputs": None,
        "holding_registers": None,
        "input_registers": None,
        "waveshare_info": None
    }
    
    logger.info(f"Scanning unit ID {unit_id}...")
    
    # Test read_coils (function code 0x01)
    success, result = test_function_with_retries(client, unit_id, "read_coils", 0, 1)
    if success:
        device_info["connected"] = True
        device_info["supported_functions"].append("read_coils")
        device_info["coils"] = result
        logger.info(f"Unit {unit_id}: read_coils supported, result: {result}")
    
    # Test read_discrete_inputs (function code 0x02)
    success, result = test_function_with_retries(client, unit_id, "read_discrete_inputs", 0, 1)
    if success:
        device_info["connected"] = True
        device_info["supported_functions"].append("read_discrete_inputs")
        device_info["discrete_inputs"] = result
        logger.info(f"Unit {unit_id}: read_discrete_inputs supported, result: {result}")
    
    # Test read_holding_registers (function code 0x03)
    success, result = test_function_with_retries(client, unit_id, "read_holding_registers", 0, 1)
    if success:
        device_info["connected"] = True
        device_info["supported_functions"].append("read_holding_registers")
        device_info["holding_registers"] = result
        logger.info(f"Unit {unit_id}: read_holding_registers supported, result: {result}")
    
    # Test read_input_registers (function code 0x04)
    success, result = test_function_with_retries(client, unit_id, "read_input_registers", 0, 1)
    if success:
        device_info["connected"] = True
        device_info["supported_functions"].append("read_input_registers")
        device_info["input_registers"] = result
        logger.info(f"Unit {unit_id}: read_input_registers supported, result: {result}")
    
    # If device is connected, try to identify if it's a Waveshare module
    if device_info["connected"]:
        # Check for Waveshare Analog Input 8CH module
        waveshare_info = check_waveshare_device(client, unit_id)
        if waveshare_info:
            device_info["device_type"] = "Waveshare Analog Input 8CH"
            device_info["waveshare_info"] = waveshare_info
            logger.info(f"Unit {unit_id}: Identified as Waveshare Analog Input 8CH module")
            logger.info(f"  Software version: {waveshare_info['software_version']}")
            logger.info(f"  Analog inputs: {waveshare_info['analog_inputs']}")
    
    return device_info

def check_waveshare_device(client: ModbusRTU, unit_id: int) -> Optional[Dict[str, Any]]:
    """
    Check if the device is a Waveshare Analog Input 8CH module
    
    Args:
        client: ModbusRTU client instance
        unit_id: Unit ID to check
        
    Returns:
        Dict with device information or None if not a Waveshare device
    """
    # Try to read software version (register 0x0101)
    success, sw_version = test_function_with_retries(
        client, unit_id, "read_holding_registers", 
        WAVESHARE_ANALOG_INPUT_REGISTERS["software_version"], 1
    )
    
    if not success:
        return None
    
    # Try to read analog inputs (registers 0x0000-0x0007)
    success, analog_values = test_function_with_retries(
        client, unit_id, "read_input_registers", 
        WAVESHARE_ANALOG_INPUT_REGISTERS["analog_inputs"][0], 8
    )
    
    if not success:
        # Try again with individual reads
        analog_values = []
        all_success = True
        for addr in WAVESHARE_ANALOG_INPUT_REGISTERS["analog_inputs"]:
            success, value = test_function_with_retries(
                client, unit_id, "read_input_registers", addr, 1
            )
            if success and value:
                analog_values.extend(value)
            else:
                all_success = False
                analog_values.append(None)
        
        if not all_success and not analog_values:
            return None
    
    return {
        "software_version": sw_version[0] if sw_version else None,
        "analog_inputs": analog_values
    }


def scan_unit_id_range(client: ModbusRTU, start_id: int = 1, end_id: int = 10, 
                       quick_mode: bool = False) -> List[Dict[str, Any]]:
    """
    Scan a range of unit IDs for Modbus devices
    
    Args:
        client: ModbusRTU client instance
        start_id: Starting unit ID
        end_id: Ending unit ID
        quick_mode: If True, stop scanning a unit ID after first successful function
        
    Returns:
        List of dictionaries with device information
    """
    devices = []
    
    # First, try broadcast address (0) to see if any device responds
    logger.info("Testing broadcast address (0)...")
    try:
        # Some devices might respond to broadcast despite Modbus spec
        result = client.read_coils(unit_id=0, address=0, count=1)
        if result is not None:
            logger.warning("Device responding to broadcast address (0) - this is non-standard behavior")
    except Exception:
        pass
    
    # Now scan the specified range
    for unit_id in range(start_id, end_id + 1):
        logger.info(f"Scanning unit ID {unit_id}...")
        device_info = scan_device(client, unit_id)
        
        if device_info["connected"]:
            devices.append(device_info)
            logger.info(f"Found device at unit ID {unit_id}")
            logger.info(f"Device type: {device_info['device_type']}")
            logger.info(f"Supported functions: {device_info['supported_functions']}")
            
            # If we found a device and we're in quick mode, move to next unit ID
            if quick_mode:
                logger.info("Quick mode enabled, skipping additional tests for this unit ID")
                continue
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
    parser.add_argument('--timeout', type=float, default=2.0,
                        help='Communication timeout in seconds (default: 2.0)')
    parser.add_argument('--start-id', type=int, default=1,
                        help='Starting unit ID to scan (default: 1)')
    parser.add_argument('--end-id', type=int, default=10,
                        help='Ending unit ID to scan (default: 10)')
    parser.add_argument('--parity', type=str, default='N', choices=['N', 'E', 'O'],
                        help='Parity setting (N=None, E=Even, O=Odd) (default: N)')
    parser.add_argument('--stopbits', type=int, default=1, choices=[1, 2],
                        help='Number of stop bits (default: 1)')
    parser.add_argument('--bytesize', type=int, default=8, choices=[7, 8],
                        help='Byte size (default: 8)')
    parser.add_argument('--quick', action='store_true',
                        help='Quick scan mode (stop after first successful function)')
    parser.add_argument('--waveshare', action='store_true',
                        help='Optimize scan for Waveshare Modbus RTU modules')
    parser.add_argument('--debug', action='store_true',
                        help='Enable debug logging')
    
    args = parser.parse_args()
    
    if args.debug:
        logger.setLevel(logging.DEBUG)
        # Also set RTU module logger to DEBUG
        rtu_logger = logging.getLogger("modapi.api.rtu")
        rtu_logger.setLevel(logging.DEBUG)
    
    logger.info(f"Starting Modbus RTU scanner on {args.port} at {args.baudrate} baud")
    logger.info(f"Serial settings: {args.bytesize}{args.parity}{args.stopbits}")
    logger.info(f"Scanning unit IDs from {args.start_id} to {args.end_id}")
    
    # Create and connect ModbusRTU client
    client = ModbusRTU(
        port=args.port,
        baudrate=args.baudrate,
        timeout=args.timeout,
        parity=args.parity,
        stopbits=args.stopbits,
        bytesize=args.bytesize
    )
    
    if not client.connect():
        logger.error(f"Failed to connect to {args.port}")
        return 1
    
    try:
        # Clear buffers before starting
        client.serial_conn.reset_input_buffer()
        client.serial_conn.reset_output_buffer()
        time.sleep(0.1)  # Short delay to ensure buffers are cleared
        
        # Scan for devices
        devices = scan_unit_id_range(client, args.start_id, args.end_id, args.quick)
        
        # Print results
        logger.info("\n--- SCAN RESULTS ---")
        if devices:
            logger.info(f"Found {len(devices)} Modbus RTU device(s):")
            for device in devices:
                logger.info(f"Unit ID: {device['unit_id']}")
                logger.info(f"  Device type: {device['device_type']}")
                logger.info(f"  Supported functions: {device['supported_functions']}")
                
                # Print function-specific results
                if 'read_coils' in device['supported_functions']:
                    logger.info(f"  Coils: {device['coils']}")
                if 'read_discrete_inputs' in device['supported_functions']:
                    logger.info(f"  Discrete inputs: {device['discrete_inputs']}")
                if 'read_holding_registers' in device['supported_functions']:
                    logger.info(f"  Holding registers: {device['holding_registers']}")
                if 'read_input_registers' in device['supported_functions']:
                    logger.info(f"  Input registers: {device['input_registers']}")
                
                # Print Waveshare-specific information if available
                if device['waveshare_info']:
                    logger.info("  Waveshare device information:")
                    logger.info(f"    Software version: {device['waveshare_info']['software_version']}")
                    logger.info(f"    Analog inputs: {device['waveshare_info']['analog_inputs']}")
                    
                    # If this is a Waveshare device and we have the --waveshare flag,
                    # perform additional tests specific to Waveshare modules
                    if args.waveshare:
                        logger.info("  Performing additional Waveshare-specific tests...")
                        # Test reading all analog inputs individually
                        for i, addr in enumerate(WAVESHARE_ANALOG_INPUT_REGISTERS["analog_inputs"]):
                            success, value = test_function_with_retries(
                                client, device['unit_id'], "read_input_registers", addr, 1, 3
                            )
                            if success:
                                logger.info(f"    Analog input {i+1}: {value[0]}")
                            else:
                                logger.info(f"    Analog input {i+1}: Failed to read")
        else:
            logger.info("No Modbus RTU devices found.")
            
            # Provide troubleshooting suggestions
            logger.info("\nTroubleshooting suggestions:")
            logger.info("1. Check physical connections and power to the RS485 devices")
            logger.info("2. Verify the correct serial port is being used")
            logger.info("3. Try different serial settings (baud rate, parity, etc.)")
            logger.info("4. Ensure proper RS485 termination resistors are in place")
            logger.info("5. Try a wider range of unit IDs (some devices use non-standard IDs)")
            logger.info("6. Run with --debug flag for more detailed logging")
    
    except KeyboardInterrupt:
        logger.info("Scan interrupted by user")
    
    finally:
        # Disconnect client
        client.disconnect()
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
