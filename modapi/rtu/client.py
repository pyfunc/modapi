"""
Modbus RTU Client Module
High-level client API for Modbus RTU communication
"""

import logging
import time
from typing import List, Optional, Dict, Any, Tuple, Union

from .base import ModbusRTU
from modapi.config import (
    DEFAULT_PORT, DEFAULT_BAUDRATE, DEFAULT_TIMEOUT, DEFAULT_UNIT_ID,
    DEFAULT_RS485_DELAY, HIGHEST_PRIORITIZED_BAUDRATE,
    BAUDRATES, AUTO_DETECT_UNIT_IDS,
    READ_COILS, READ_DISCRETE_INPUTS,
    READ_HOLDING_REGISTERS, READ_INPUT_REGISTERS,
    WRITE_SINGLE_COIL, WRITE_SINGLE_REGISTER,
    WRITE_MULTIPLE_COILS, WRITE_MULTIPLE_REGISTERS
)
from .protocol import (
    build_read_request, build_write_single_coil_request,
    build_write_single_register_request, build_write_multiple_coils_request,
    build_write_multiple_registers_request, build_set_baudrate_request,
    parse_read_coils_response, parse_read_registers_response, parse_response
)
from .utils import find_serial_ports, test_modbus_port, scan_for_devices, detect_device_type

logger = logging.getLogger(__name__)

class ModbusRTUClient(ModbusRTU):
    """
    High-level Modbus RTU client with simplified API
    
    This class provides a user-friendly API for Modbus RTU communication
    while handling Waveshare-specific quirks internally.
    """
    
    def __init__(self, port: str = '/dev/ttyACM0', baudrate: int = 57600, 
                 timeout: float = 1.0, rs485_delay: float = DEFAULT_RS485_DELAY):
        """
        Initialize Modbus RTU client
        
        Args:
            port: Serial port path (default: /dev/ttyACM0)
            baudrate: Baud rate (default: 57600)
            timeout: Read timeout in seconds (default: 1.0)
            rs485_delay: Delay between RS485 operations in seconds (default: from config.DEFAULT_RS485_DELAY)
        """
        super().__init__(port=port, baudrate=baudrate, timeout=timeout, rs485_delay=rs485_delay)
        logger.info(f"Initialized Modbus RTU client on {port} at {baudrate} baud with RS485 delay {rs485_delay}s")
    
    def read_coils(self, address: int, count: int, unit_id: int = 1) -> Optional[List[bool]]:
        """
        Read coil states
        
        Args:
            address: Starting address
            count: Number of coils to read
            unit_id: Unit ID
            
        Returns:
            Optional[List[bool]]: List of coil states or None if error
        """
        if not self.is_connected() and not self.connect():
            return None
        
        request = build_read_request(unit_id, FUNC_READ_COILS, address, count)
        response = self.send_request(request, unit_id, FUNC_READ_COILS)
        
        if response is None:
            return None
        
        return parse_read_coils_response(response)
    
    def read_discrete_inputs(self, address: int, count: int, unit_id: int = 1) -> Optional[List[bool]]:
        """
        Read discrete input states
        
        Args:
            address: Starting address
            count: Number of inputs to read
            unit_id: Unit ID
            
        Returns:
            Optional[List[bool]]: List of input states or None if error
        """
        if not self.is_connected() and not self.connect():
            return None
        
        request = build_read_request(unit_id, FUNC_READ_DISCRETE_INPUTS, address, count)
        response = self.send_request(request, unit_id, FUNC_READ_DISCRETE_INPUTS)
        
        if response is None:
            return None
        
        return parse_read_coils_response(response)
    
    def read_holding_registers(self, address: int, count: int, unit_id: int = 1) -> Optional[List[int]]:
        """
        Read holding registers
        
        Args:
            address: Starting address
            count: Number of registers to read
            unit_id: Unit ID
            
        Returns:
            Optional[List[int]]: List of register values or None if error
        """
        if not self.is_connected() and not self.connect():
            return None
        
        request = build_read_request(unit_id, FUNC_READ_HOLDING_REGISTERS, address, count)
        response = self.send_request(request, unit_id, FUNC_READ_HOLDING_REGISTERS)
        
        if response is None:
            return None
        
        return parse_read_registers_response(response)
    
    def read_input_registers(self, address: int, count: int, unit_id: int = 1) -> Optional[List[int]]:
        """
        Read input registers
        
        Args:
            address: Starting address
            count: Number of registers to read
            unit_id: Unit ID
            
        Returns:
            Optional[List[int]]: List of register values or None if error
        """
        if not self.is_connected() and not self.connect():
            return None
        
        request = build_read_request(unit_id, FUNC_READ_INPUT_REGISTERS, address, count)
        response = self.send_request(request, unit_id, FUNC_READ_INPUT_REGISTERS)
        
        if response is None:
            return None
        
        return parse_read_registers_response(response)
    
    def write_coil(self, address: int, value: bool, unit_id: int = 1) -> bool:
        """
        Write single coil
        
        Args:
            address: Coil address
            value: Coil value
            unit_id: Unit ID
            
        Returns:
            bool: True if successful
        """
        if not self.is_connected() and not self.connect():
            return False
        
        request = build_write_single_coil_request(unit_id, address, value)
        response = self.send_request(request, unit_id, FUNC_WRITE_SINGLE_COIL)
        
        return response is not None
    
    def write_register(self, address: int, value: int, unit_id: int = 1) -> bool:
        """
        Write single register
        
        Args:
            address: Register address
            value: Register value
            unit_id: Unit ID
            
        Returns:
            bool: True if successful
        """
        if not self.is_connected() and not self.connect():
            return False
        
        request = build_write_single_register_request(unit_id, address, value)
        response = self.send_request(request, unit_id, FUNC_WRITE_SINGLE_REGISTER)
        
        return response is not None
    
    def write_coils(self, address: int, values: List[bool], unit_id: int = 1) -> bool:
        """
        Write multiple coils
        
        Args:
            address: Starting address
            values: List of coil values
            unit_id: Unit ID
            
        Returns:
            bool: True if successful
        """
        if not self.is_connected() and not self.connect():
            return False
        
        request = build_write_multiple_coils_request(unit_id, address, values)
        response = self.send_request(request, unit_id, FUNC_WRITE_MULTIPLE_COILS)
        
        return response is not None
    
    def write_registers(self, address: int, values: List[int], unit_id: int = 1) -> bool:
        """
        Write multiple register values
        
        Args:
            address: Starting address
            values: List of register values
            unit_id: Unit ID
            
        Returns:
            bool: True if successful, False otherwise
        """
        if not self.is_connected() and not self.connect():
            return False
        
        request = build_write_multiple_registers_request(unit_id, address, values)
        response = self.send_request(request, unit_id, FUNC_WRITE_MULTIPLE_REGISTERS)
        
        return response is not None
        
    def set_device_baudrate(self, baudrate: int = None, unit_id: int = 0) -> bool:
        """
        Set the device's internal baudrate using the Waveshare protocol.
        
        This sends a command to register 0x2000 with the appropriate baudrate code.
        After setting the baudrate, the device will use that baudrate for future
        communications, so the host should reconnect at the new baudrate.
        
        Args:
            baudrate: Baudrate to set (if None, uses the highest prioritized baudrate from config)
            unit_id: Unit ID to set baudrate for (default: 0 for broadcast)
            
        Returns:
            bool: True if successful, False otherwise
        """
        # If no baudrate specified, use the highest prioritized baudrate from config
        if baudrate is None:
            baudrate = HIGHEST_PRIORITIZED_BAUDRATE
            logger.info(f"Using highest prioritized baudrate from config: {baudrate}")
        else:
            logger.info(f"Using specified baudrate: {baudrate}")
            
        # Load baudrate mapping
        import json
        import os
        from modapi.config import CONFIG_DIR
        
        try:
            with open(os.path.join(CONFIG_DIR, 'baudrates.json'), 'r') as f:
                baudrate_map = json.load(f)
        except Exception as e:
            logger.error(f"Failed to load baudrate mapping: {e}")
            return False
            
        # Convert baudrate to string for dictionary lookup
        baudrate_str = str(baudrate)
        
        # Check if our baudrate is in the mapping
        if baudrate_str not in baudrate_map:
            logger.warning(f"Baudrate {baudrate} not found in mapping, cannot set device baudrate")
            return False
            
        # Get the baudrate code from the mapping
        baudrate_code = baudrate_map[baudrate_str]
        
        if not self.is_connected() and not self.connect():
            return False
        
        logger.info(f"Setting device baudrate to {baudrate} (code: {baudrate_code})")
        request = build_set_baudrate_request(unit_id, baudrate_code)
        
        # For broadcast messages (unit_id=0), we don't expect a response
        if unit_id == 0:
            self._enforce_rs485_delay()  # Ensure proper timing
            self.serial_conn.write(request)
            logger.info("Sent broadcast baudrate change command (no response expected)")
            return True
        
        # For directed messages, we expect a response
        response = self.send_request(request, unit_id, FUNC_WRITE_SINGLE_REGISTER)
        success = response is not None
        
        if success:
            logger.info(f"Successfully set device baudrate to {baudrate}")
        else:
            logger.warning(f"Failed to set device baudrate to {baudrate}")
            
        return success
    
    def send_raw_request(self, request: bytes, expected_unit: int, expected_function: int) -> Optional[bytes]:
        """
        Send raw Modbus RTU request
        
        Args:
            request: Raw request bytes
            expected_unit: Expected unit ID in response
            expected_function: Expected function code in response
            
        Returns:
            Optional[bytes]: Raw response bytes or None if error
        """
        if not self.is_connected() and not self.connect():
            return None
        
        # Send request and get raw response
        with self._lock:
            try:
                # Clear input buffer
                self._serial.reset_input_buffer()
                
                # Send request
                logger.debug(f"Sending raw request: {request.hex()}")
                self._serial.write(request)
                
                # Wait for response
                time.sleep(0.1)
                
                # Read response
                if self._serial.in_waiting > 0:
                    response = self._serial.read(self._serial.in_waiting)
                    logger.debug(f"Received raw response: {response.hex()}")
                    
                    # Validate response
                    data = parse_response(response, expected_unit, expected_function)
                    if data is not None:
                        return response
                
                return None
            except Exception as e:
                logger.error(f"Error sending raw request: {e}")
                return None
    
    @classmethod
    def scan_devices(cls) -> List[Dict[str, Any]]:
        """
        Scan for Modbus RTU devices
        
        Returns:
            List[Dict[str, Any]]: List of detected devices
        """
        return scan_for_devices()
    
    @classmethod
    def auto_detect(cls, ports: List[str] = None) -> Dict[str, Any]:
        """
        Auto-detect and connect to first available Modbus RTU device
        
        Args:
            ports: List of ports to try (default: auto-detect)
            
        Returns:
            Dict[str, Any]: Configuration dict or None if no device found
        """
        if ports is None:
            ports = find_serial_ports()
            
        # Log detected ports
        logger.info(f"Auto-detection checking ports: {ports}")
        
        # Use baudrates and unit IDs from config
        baudrates = BAUDRATES
        # Add more common baudrates if the list is too short
        if len(baudrates) < 3:
            baudrates = list(set(baudrates + PRIORITIZED_BAUDRATES))
        
        # Ensure we have a comprehensive list of unit IDs to test
        unit_ids = list(set(AUTO_DETECT_UNIT_IDS + [0, 1, 2, 3, 4, 5, 10, 15, 16, 247]))  # Include broadcast and common addresses
        
        logger.info(f"Auto-detection using baudrates: {baudrates}")
        logger.info(f"Auto-detection using unit IDs: {unit_ids}")
        
        # Prioritize /dev/ttyACM0 if it's in the list
        if '/dev/ttyACM0' in ports:
            ports.remove('/dev/ttyACM0')
            ports.insert(0, '/dev/ttyACM0')  # Put it first
        
        for port in ports:
            logger.info(f"Testing port: {port}")
            for baudrate in baudrates:
                logger.info(f"  Testing baudrate: {baudrate}")
                for unit_id in unit_ids:
                    try:
                        client = cls(port=port, baudrate=baudrate, timeout=1.0)  # Increased timeout for reliability
                        if client.connect():
                            logger.info(f"    Connected to {port} at {baudrate}, testing unit_id={unit_id}")
                            
                            # Try to read a register to verify connection
                            try:
                                response = client.read_holding_registers(0, 1, unit_id)
                                if response is not None:
                                    logger.info(f"✅ Found working configuration: {port}, {baudrate}, unit_id={unit_id} (holding registers)")
                                    return {
                                        'port': port,
                                        'baudrate': baudrate,
                                        'unit_id': unit_id
                                    }
                            except Exception as e:
                                logger.debug(f"      Error reading holding registers: {e}")
                            
                            # Try reading coils if registers didn't work
                            try:
                                response = client.read_coils(0, 8, unit_id)
                                if response is not None:
                                    logger.info(f"✅ Found working configuration: {port}, {baudrate}, unit_id={unit_id} (coils)")
                                    return {
                                        'port': port,
                                        'baudrate': baudrate,
                                        'unit_id': unit_id
                                    }
                            except Exception as e:
                                logger.debug(f"      Error reading coils: {e}")
                                
                            # Try reading input registers
                            try:
                                response = client.read_input_registers(0, 1, unit_id)
                                if response is not None:
                                    logger.info(f"✅ Found working configuration: {port}, {baudrate}, unit_id={unit_id} (input registers)")
                                    return {
                                        'port': port,
                                        'baudrate': baudrate,
                                        'unit_id': unit_id
                                    }
                            except Exception as e:
                                logger.debug(f"      Error reading input registers: {e}")
                            
                            client.disconnect()
                    except Exception as e:
                        logger.debug(f"    Error testing {port} at {baudrate} with unit_id={unit_id}: {e}")
        
        logger.warning("❌ No working configuration found")
        return None
