"""
Modbus RTU Client Module
High-level client API for Modbus RTU communication
"""

import logging
import time
from typing import List, Optional, Dict, Any, Tuple, Union

from .base import ModbusRTU
from .protocol import (
    FUNC_READ_COILS, FUNC_READ_DISCRETE_INPUTS,
    FUNC_READ_HOLDING_REGISTERS, FUNC_READ_INPUT_REGISTERS,
    FUNC_WRITE_SINGLE_COIL, FUNC_WRITE_SINGLE_REGISTER,
    FUNC_WRITE_MULTIPLE_COILS, FUNC_WRITE_MULTIPLE_REGISTERS,
    build_read_request, build_write_single_coil_request,
    build_write_single_register_request, build_write_multiple_coils_request,
    build_write_multiple_registers_request, parse_read_coils_response,
    parse_read_registers_response, parse_response
)
from .utils import find_serial_ports, test_modbus_port, scan_for_devices, detect_device_type

logger = logging.getLogger(__name__)

class ModbusRTUClient(ModbusRTU):
    """
    High-level Modbus RTU client with simplified API
    
    This class provides a user-friendly API for Modbus RTU communication
    while handling Waveshare-specific quirks internally.
    """
    
    def __init__(self, port: str = '/dev/ttyACM0', baudrate: int = 9600, timeout: float = 1.0):
        """Initialize Modbus RTU client"""
        super().__init__(port=port, baudrate=baudrate, timeout=timeout)
        logger.info(f"Initialized Modbus RTU client on {port} at {baudrate} baud")
    
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
        response = self._send_request(unit_id, FUNC_READ_COILS, request[2:-2], max_retries=3)
        
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
        response = self._send_request(unit_id, FUNC_READ_DISCRETE_INPUTS, request[2:-2], max_retries=3)
        
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
        response = self._send_request(unit_id, FUNC_READ_HOLDING_REGISTERS, request[2:-2], max_retries=3)
        
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
        response = self._send_request(unit_id, FUNC_READ_INPUT_REGISTERS, request[2:-2], max_retries=3)
        
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
        response = self._send_request(unit_id, FUNC_WRITE_SINGLE_COIL, request[2:-2], max_retries=3)
        
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
        response = self._send_request(unit_id, FUNC_WRITE_SINGLE_REGISTER, request[2:-2], max_retries=3)
        
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
        response = self._send_request(unit_id, FUNC_WRITE_MULTIPLE_COILS, request[2:-2], max_retries=3)
        
        return response is not None
    
    def write_registers(self, address: int, values: List[int], unit_id: int = 1) -> bool:
        """
        Write multiple registers
        
        Args:
            address: Starting address
            values: List of register values
            unit_id: Unit ID
            
        Returns:
            bool: True if successful
        """
        if not self.is_connected() and not self.connect():
            return False
        
        request = build_write_multiple_registers_request(unit_id, address, values)
        response = self._send_request(unit_id, FUNC_WRITE_MULTIPLE_REGISTERS, request[2:-2], max_retries=3)
        
        return response is not None
    
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
        
        # Try each port with common baudrates
        baudrates = [9600, 115200, 19200, 4800, 38400, 57600]
        unit_ids = [1, 2, 3, 0]  # Include broadcast address 0
        
        for port in ports:
            for baudrate in baudrates:
                for unit_id in unit_ids:
                    try:
                        client = cls(port=port, baudrate=baudrate, timeout=0.5)
                        if client.connect():
                            # Try to read a register to verify connection
                            response = client.read_holding_registers(0, 1, unit_id)
                            if response is not None:
                                logger.info(f"Found working configuration: {port}, {baudrate}, unit_id={unit_id}")
                                return {
                                    'port': port,
                                    'baudrate': baudrate,
                                    'unit_id': unit_id
                                }
                            
                            # Try reading coils if registers didn't work
                            response = client.read_coils(0, 8, unit_id)
                            if response is not None:
                                logger.info(f"Found working configuration: {port}, {baudrate}, unit_id={unit_id}")
                                return {
                                    'port': port,
                                    'baudrate': baudrate,
                                    'unit_id': unit_id
                                }
                            
                            client.disconnect()
                    except Exception as e:
                        logger.debug(f"Error testing {port} at {baudrate} with unit_id={unit_id}: {e}")
        
        logger.warning("No working configuration found")
        return None
