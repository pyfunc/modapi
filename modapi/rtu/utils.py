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
# Removed unused import: calculate_crc
from modapi.config import (
    PRIORITIZED_BAUDRATES, AUTO_DETECT_UNIT_IDS,
    DEFAULT_BAUDRATE, DEFAULT_TIMEOUT, DEFAULT_UNIT_ID
    # Removed unused import: BAUDRATES
)

logger = logging.getLogger(__name__)

def find_serial_ports() -> List[str]:
    """
    Find all available serial ports on the system.
    
    Prioritizes hardware ports (ttyACM, ttyUSB) over virtual ports (ttyS).
    Filters out potentially problematic or inaccessible ports.
    
    Returns:
        List[str]: List of available serial port paths, prioritized by likelihood of being real hardware
    """
    # Lists to store different types of ports
    hardware_ports = []  # Most likely to be real hardware (ttyACM, ttyUSB)
    virtual_ports = []   # Potentially virtual ports (ttyS)
    other_ports = []     # Other port types
    
    # Try to use pyserial's list_ports to get detailed port information
    try:
        for port in serial.tools.list_ports.comports():
            port_path = port.device
            
            # Skip ports that are likely to be problematic
            if any(port_path.startswith(skip) for skip in [
                '/dev/ttyAMA',  # Raspberry Pi GPIO serial port
                '/dev/ttyprintk'  # Kernel print port
            ]):
                logger.debug(f"Skipping problematic port: {port_path}")
                continue
                
            # Categorize ports by type
            if '/dev/ttyACM' in port_path:
                hardware_ports.append(port_path)
            elif '/dev/ttyUSB' in port_path:
                hardware_ports.append(port_path)
            elif '/dev/ttyS' in port_path:
                # Only include ttyS ports with low numbers (0-4) as higher numbers
                # are often virtual and can cause issues
                port_num = int(port_path.replace('/dev/ttyS', ''))
                if port_num <= 4:
                    virtual_ports.append(port_path)
            else:
                other_ports.append(port_path)
    except Exception as e:
        logger.warning(f"Error using serial.tools.list_ports: {e}")
    
    # Fallback to checking common device paths if no ports were found
    if not hardware_ports and not virtual_ports and not other_ports:
        logger.info("No ports found with pyserial, checking common device paths")
        # Check for hardware ports first
        for i in range(10):
            for prefix in ['/dev/ttyACM', '/dev/ttyUSB']:
                port_path = f"{prefix}{i}"
                if os.path.exists(port_path):
                    hardware_ports.append(port_path)
        
        # Only check ttyS0-4 as higher numbers are often virtual
        for i in range(5):
            port_path = f"/dev/ttyS{i}"
            if os.path.exists(port_path):
                virtual_ports.append(port_path)
    
    # Combine the lists with hardware ports first, then virtual, then others
    all_ports = hardware_ports + virtual_ports + other_ports
    
    # Special case: if /dev/ttyACM0 exists, make sure it's first in the list
    # as it's commonly used for USB-to-serial adapters
    if '/dev/ttyACM0' in all_ports:
        all_ports.remove('/dev/ttyACM0')
        all_ports.insert(0, '/dev/ttyACM0')
    
    logger.info(f"Found {len(all_ports)} serial ports: {all_ports}")
    logger.info(f"Hardware ports: {hardware_ports}")
    logger.info(f"Virtual ports: {virtual_ports}")
    logger.info(f"Other ports: {other_ports}")
    
    return all_ports

def test_modbus_port(port: str, baudrate: int = DEFAULT_BAUDRATE, timeout: float = 0.5, unit_id: int = 1, debug: bool = False) -> Tuple[bool, Dict[str, Any]]:
    """
    Test if a serial port has a Modbus device connected
    
    Args:
        port: Serial port path to test
        baudrate: Baud rate to test
        timeout: Timeout in seconds
        unit_id: Modbus unit ID to test (default: 1)
        debug: Enable debug output (default: False)
        
    Returns:
        Tuple[bool, Dict[str, Any]]: Success flag and connection details
    """
    from .protocol import build_read_request, parse_response
    
    try:
        # Try to open the port
        with serial.Serial(port=port, baudrate=baudrate, timeout=timeout) as ser:
            # Clear any pending data
            ser.reset_input_buffer()
            ser.reset_output_buffer()
            
            # Create result dictionary
            result = {
                'port': port,
                'baudrate': baudrate,
                'unit_id': unit_id,
                'success': False,
                'connected': False,
                'error': None,
                'device_type': None
            }
            
            # Test 1: Try reading holding registers (function code 0x03)
            # This is a common operation that most Modbus devices support
            # Ensure all parameters are valid integers
            safe_unit_id = int(unit_id) if unit_id is not None else DEFAULT_UNIT_ID
            request = build_read_request(safe_unit_id, 0x03, 0x0000, 1)
            ser.write(request)
            
            # Wait for response
            time.sleep(0.1)
            
            if ser.in_waiting > 0:
                response = ser.read(ser.in_waiting)
                if debug:
                    logger.debug(f"Got response from {port} (FC03): {response.hex()}")
                
                # If we got any response, it's likely a Modbus device
                if len(response) >= 5:  # Minimum valid Modbus RTU response length
                    result['success'] = True
                    result['connected'] = True
                    return True, result
            
            # Test 2: Try reading coils (function code 0x01)
            ser.reset_input_buffer()
            request = build_read_request(safe_unit_id, 0x01, 0x0000, 1)
            ser.write(request)
            
            # Wait for response
            time.sleep(0.1)
            
            if ser.in_waiting > 0:
                response = ser.read(ser.in_waiting)
                if debug:
                    logger.debug(f"Got response from {port} (FC01): {response.hex()}")
                
                # If we got any response, it's likely a Modbus device
                if len(response) >= 5:  # Minimum valid Modbus RTU response length
                    result['success'] = True
                    result['connected'] = True
                    return True, result
            
            # Test 3: Try reading input registers (function code 0x04)
            ser.reset_input_buffer()
            request = build_read_request(safe_unit_id, 0x04, 0x0000, 1)
            ser.write(request)
            
            # Wait for response
            time.sleep(0.1)
            
            if ser.in_waiting > 0:
                response = ser.read(ser.in_waiting)
                if debug:
                    logger.debug(f"Got response from {port} (FC04): {response.hex()}")
                
                # If we got any response, it's likely a Modbus device
                if len(response) >= 5:  # Minimum valid Modbus RTU response length
                    result['success'] = True
                    result['connected'] = True
                    return True, result
            
            return False, result
    except Exception as e:
        logger.debug(f"Error testing port {port} at {baudrate} baud: {e}", exc_info=True)
        result = {
            'port': port,
            'baudrate': baudrate,
            'unit_id': unit_id,
            'success': False,
            'connected': False,
            'error': str(e),
            'device_type': None
        }
        return False, result

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


def test_rtu_connection(port: str, baudrate: int = DEFAULT_BAUDRATE, timeout: float = DEFAULT_TIMEOUT, unit_id: int = DEFAULT_UNIT_ID) -> Tuple[bool, Dict[str, Any]]:
    """
    Test connection to a Modbus RTU device
    
    This is a convenience function that uses ModbusRTU to test the connection.
    
    Args:
        port: Serial port path
        baudrate: Baud rate to test
        timeout: Timeout in seconds
        unit_id: Unit ID to test
        
    Returns:
        Tuple[bool, Dict[str, Any]]: Success flag and connection status/configuration
    """
    # Import here to avoid circular imports
    import modapi.api.rtu
    
    result = {
        'port': port,
        'baudrate': baudrate,
        'unit_id': unit_id,
        'success': False,
        'connected': False,
        'error': None,
        'device_type': None
    }
    
    try:
        # Create a ModbusRTU instance to test the connection
        with modapi.api.rtu.ModbusRTU(port=port, baudrate=baudrate, timeout=timeout) as rtu:
            # Use the test_connection method of ModbusRTU
            success, test_result = rtu.test_connection(unit_id)
            
            # Update our result with the test_connection result
            result['success'] = success
            result['connected'] = success  # Ensure 'connected' key is set for test compatibility
            
            # If connection was successful, try to detect the device type
            if success:
                result['device_type'] = detect_device_type(port, baudrate, unit_id) or "Unknown Modbus RTU Device"
                
            return success, result
                
    except Exception as e:
        result['error'] = str(e)
        logger.error(f"Error testing RTU connection on port {port}: {e}")
        return False, result
