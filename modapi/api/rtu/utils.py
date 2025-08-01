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

logger = logging.getLogger(__name__)

def find_serial_ports() -> List[str]:
    """
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

def test_modbus_port(port: str, baudrate: int = 9600, timeout: float = 0.5) -> bool:
    """
    Test if a serial port has a Modbus device connected
    
    Args:
        port: Serial port path to test
        baudrate: Baud rate to test
        timeout: Timeout in seconds
        
    Returns:
        bool: True if a Modbus device is detected
    """
    try:
        # Try to open the port
        with serial.Serial(port=port, baudrate=baudrate, timeout=timeout) as ser:
            # Clear any pending data
            ser.reset_input_buffer()
            ser.reset_output_buffer()
            
            # Send a Modbus request to read device ID (unit 1)
            # This is a standard Modbus request that most devices should respond to
            request = bytes([0x01, 0x03, 0x00, 0x00, 0x00, 0x01, 0x84, 0x0A])
            ser.write(request)
            
            # Wait for response
            time.sleep(0.1)
            
            # Check if we got any response
            if ser.in_waiting > 0:
                response = ser.read(ser.in_waiting)
                logger.debug(f"Got response from {port}: {response.hex()}")
                
                # Even if the response is an exception, it means a Modbus device is present
                if len(response) >= 3 and response[0] == 0x01:
                    return True
            
            # Try a broadcast message to read device address
            request = bytes([0x00, 0x03, 0x40, 0x00, 0x00, 0x01, 0x90, 0x1B])
            ser.write(request)
            
            # Wait for response
            time.sleep(0.2)
            
            # Check if we got any response
            if ser.in_waiting > 0:
                response = ser.read(ser.in_waiting)
                logger.debug(f"Got broadcast response from {port}: {response.hex()}")
                return True
            
            return False
    except Exception as e:
        logger.debug(f"Error testing {port}: {e}")
        return False

def scan_for_devices(ports: List[str] = None, 
                    baudrates: List[int] = None,
                    unit_ids: List[int] = None) -> List[Dict[str, Any]]:
    """
    Scan for Modbus devices on available ports
    
    Args:
        ports: List of ports to scan (default: auto-detect)
        baudrates: List of baudrates to try (default: [9600, 115200, 19200])
        unit_ids: List of unit IDs to try (default: [1, 2, 3])
        
    Returns:
        List[Dict[str, Any]]: List of detected devices with configuration
    """
    if ports is None:
        ports = find_serial_ports()
    
    if baudrates is None:
        baudrates = [9600, 115200, 19200, 4800, 38400, 57600]
    
    if unit_ids is None:
        unit_ids = [1, 2, 3]
    
    detected_devices = []
    
    for port in ports:
        for baudrate in baudrates:
            if test_modbus_port(port, baudrate):
                device_info = {
                    'port': port,
                    'baudrate': baudrate,
                    'unit_ids': []
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
