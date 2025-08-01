"""
Modbus RTU Utility Functions
Helper functions for device detection and serial port management
"""

import logging
import os
import serial
import serial.tools.list_ports
import time
from typing import List, Optional, Dict, Tuple, Any
from modapi.rtu.protocol import calculate_crc
from modapi.config import (
    BAUDRATES, PRIORITIZED_BAUDRATES, AUTO_DETECT_UNIT_IDS,
    DEFAULT_BAUDRATE, DEFAULT_TIMEOUT, DEFAULT_UNIT_ID
)

logger = logging.getLogger(__name__)

def find_serial_ports() -> List[str]:
    """
    Find all available serial ports on the system.
    
    Returns:
        List[str]: List of available serial port paths
    "
    Find available serial ports on the system
    
    Returns:
        List[str]: List of available serial port paths
    """
    available_ports = []
    
    # Try to use pyserial's list_ports
    try:
        for port in serial.tools.list_ports.comports():
            available_ports.append(port.device)
    except Exception as e:
        logger.warning(f"Error using serial.tools.list_ports: {e}")
    
    # Fallback to checking common device paths
    if not available_ports:
        # Common Linux serial ports
        for i in range(10):
            for prefix in ['/dev/ttyUSB', '/dev/ttyACM', '/dev/ttyS']:
                port_path = f"{prefix}{i}"
                if os.path.exists(port_path):
                    available_ports.append(port_path)
    
    logger.info(f"Found {len(available_ports)} serial ports: {available_ports}")
    return available_ports

def test_modbus_port(port: str, baudrate: int = DEFAULT_BAUDRATE, timeout: float = 0.5, unit_id: int = 1) -> bool:
    """
    Test if a serial port has a Modbus device connected
    
    Args:
        port: Serial port path to test
        baudrate: Baud rate to test
        timeout: Timeout in seconds
        unit_id: Modbus unit ID to test (default: 1)
        
    Returns:
        bool: True if a Modbus device is detected
    """
    from .protocol import build_read_request, parse_response
    
    try:
        # Try to open the port
        with serial.Serial(port=port, baudrate=baudrate, timeout=timeout) as ser:
            # Clear any pending data
            ser.reset_input_buffer()
            ser.reset_output_buffer()
            
            # Test 1: Try reading holding registers (function code 0x03)
            # This is a common operation that most Modbus devices support
            request = build_read_request(unit_id, 0x03, 0x0000, 1)
            ser.write(request)
            
            # Wait for response
            time.sleep(0.1)
            
            if ser.in_waiting > 0:
                response = ser.read(ser.in_waiting)
                logger.debug(f"Got response from {port} (FC03): {response.hex()}")
                
                # If we got any response, it's likely a Modbus device
                if len(response) >= 5:  # Minimum valid Modbus RTU response length
                    return True
            
            # Test 2: Try reading coils (function code 0x01)
            ser.reset_input_buffer()
            request = build_read_request(unit_id, 0x01, 0x0000, 1)
            ser.write(request)
            
            # Wait for response
            time.sleep(0.1)
            
            if ser.in_waiting > 0:
                response = ser.read(ser.in_waiting)
                logger.debug(f"Got response from {port} (FC01): {response.hex()}")
                
                # If we got any response, it's likely a Modbus device
                if len(response) >= 5:  # Minimum valid Modbus RTU response length
                    return True
            
            # Test 3: Try reading input registers (function code 0x04)
            ser.reset_input_buffer()
            request = build_read_request(unit_id, 0x04, 0x0000, 1)
            ser.write(request)
            
            # Wait for response
            time.sleep(0.1)
            
            if ser.in_waiting > 0:
                response = ser.read(ser.in_waiting)
                logger.debug(f"Got response from {port} (FC04): {response.hex()}")
                
                # If we got any response, it's likely a Modbus device
                if len(response) >= 5:  # Minimum valid Modbus RTU response length
                    return True
            
            return False
    except Exception as e:
        logger.debug(f"Error testing port {port} at {baudrate} baud: {e}", exc_info=True)
        return False

def scan_for_devices(ports: List[str] = None, 
                    baudrates: List[int] = None,
                    unit_ids: List[int] = None) -> List[Dict[str, Any]]:
    """
    Scan for Modbus devices on available ports
    
    Args:
        ports: List of ports to scan (default: auto-detect)
        baudrates: List of baudrates to try (default: from config.BAUDRATES)
        unit_ids: List of unit IDs to try (default: from config.AUTO_DETECT_UNIT_IDS)
        
    Returns:
        List[Dict[str, Any]]: List of detected devices with configuration
    """
    if ports is None:
        ports = find_serial_ports()
    
    if baudrates is None:
        # First try prioritized baudrates, then fall back to all baudrates
        baudrates = PRIORITIZED_BAUDRATES
    
    if unit_ids is None:
        unit_ids = AUTO_DETECT_UNIT_IDS
    
    detected_devices = []
    
    for port in ports:
        for baudrate in baudrates:
            for unit_id in unit_ids:
                if test_modbus_port(port, baudrate, unit_id=unit_id):
                    device_info = {
                        'port': port,
                        'baudrate': baudrate,
                        'unit_id': unit_id,
                        'unit_ids': [unit_id]  # For backward compatibility
                    }
                
                # Try to determine unit IDs
                try:
                    with serial.Serial(port=port, baudrate=baudrate, timeout=0.5) as ser:
                        for unit_id in unit_ids:
                            # Clear buffers
                            ser.reset_input_buffer()
                            ser.reset_output_buffer()
                            
                            # Try to read holding registers
                            request = bytes([unit_id, 0x03, 0x00, 0x00, 0x00, 0x01, 0x84, 0x0A])
                            ser.write(request)
                            time.sleep(0.1)
                            
                            if ser.in_waiting > 0:
                                response = ser.read(ser.in_waiting)
                                if len(response) >= 3 and response[0] == unit_id:
                                    device_info['unit_ids'].append(unit_id)
                except Exception as e:
                    logger.debug(f"Error scanning unit IDs on {port}: {e}")
                
                detected_devices.append(device_info)
                # No need to try other baudrates for this port
                break
    
    logger.info(f"Detected {len(detected_devices)} Modbus devices")
    for device in detected_devices:
        logger.info(f"Device: {device['port']} at {device['baudrate']} baud, unit IDs: {device['unit_ids']}")
    
    return detected_devices

def detect_device_type(port: str, baudrate: int, unit_id: int) -> Optional[str]:
    """
    Try to detect the type of Waveshare device
    
    Args:
        port: Serial port path
        baudrate: Baud rate
        unit_id: Unit ID to test
        
    Returns:
        Optional[str]: Device type or None if unknown
    """
    try:
        with serial.Serial(port=port, baudrate=baudrate, timeout=0.5) as ser:
            # Clear buffers
            ser.reset_input_buffer()
            ser.reset_output_buffer()
            
            # Try IO 8CH specific command (read output status)
            request = bytes([unit_id, 0x01, 0x00, 0x00, 0x00, 0x08, 0x3D, 0xCC])
            ser.write(request)
            time.sleep(0.1)
            
            if ser.in_waiting > 0:
                response = ser.read(ser.in_waiting)
                if len(response) >= 4 and response[0] == unit_id and response[1] == 0x01:
                    return "IO_8CH"
            
            # Clear buffers
            ser.reset_input_buffer()
            ser.reset_output_buffer()
            
            # Try Analog Input 8CH specific command (read analog inputs)
            request = bytes([unit_id, 0x04, 0x00, 0x00, 0x00, 0x08, 0xF1, 0xCC])
            ser.write(request)
            time.sleep(0.1)
            
            if ser.in_waiting > 0:
                response = ser.read(ser.in_waiting)
                if len(response) >= 4 and response[0] == unit_id and response[1] == 0x04:
                    return "ANALOG_INPUT_8CH"
            
            # Unknown device type
            return None
    except Exception as e:
        logger.debug(f"Error detecting device type on {port}: {e}")
        return None


def test_rtu_connection(port: str, baudrate: int = DEFAULT_BAUDRATE, timeout: float = 0.5, unit_id: int = 1) -> Dict[str, Any]:
    """
    Test connection to a Modbus RTU device
    
    This is a convenience function that uses test_modbus_port and returns a more detailed result.
    
    Args:
        port: Serial port path
        baudrate: Baud rate to test
        timeout: Timeout in seconds
        unit_id: Unit ID to test
        
    Returns:
        Dict[str, Any]: Connection status and configuration
    """
    result = {
        'port': port,
        'baudrate': baudrate,
        'unit_id': unit_id,
        'success': False,
        'error': None,
        'device_type': None
    }
    
    try:
        # First try the test_modbus_port function
        if test_modbus_port(port, baudrate, 1.0, unit_id):
            result['success'] = True
            result['device_type'] = detect_device_type(port, baudrate, unit_id) or "Unknown Modbus RTU Device"
            return True, result
            
        # If that fails, try a more direct approach
        with serial.Serial(port, baudrate, timeout=1.0) as ser:
            # Try to read a coil (function code 0x01)
            request = bytes([unit_id, 0x01, 0x00, 0x00, 0x00, 0x01])
            crc = calculate_crc(request)
            request += bytes([crc & 0xFF, (crc >> 8) & 0xFF])
            
            ser.write(request)
            response = ser.read(100)
            
            if len(response) > 0:
                result['success'] = True
                result['device_type'] = detect_device_type(port, baudrate, unit_id) or "Unknown Modbus RTU Device"
                return True, result
                
    except Exception as e:
        result['error'] = str(e)
        logger.error(f"Error testing RTU connection on port {port}: {e}")
        return False, result
        
    return False, result
