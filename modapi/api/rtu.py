"""
Direct RTU Modbus Communication Module
Bezpośrednia komunikacja z /dev/ttyACM0 bez PyModbus

This module is maintained for backward compatibility.
New code should use the modular implementation in the rtu/ package.
"""

import logging
import os
import time
from typing import Dict, List, Optional, Tuple, Any

# Import from new modular implementation
from modapi.rtu.client import ModbusRTUClient
from modapi.rtu.utils import find_serial_ports, test_modbus_port
from modapi.config import DEFAULT_PORT, DEFAULT_BAUDRATE, DEFAULT_TIMEOUT, DEFAULT_UNIT_ID
from modapi.rtu.protocol import (
    FUNC_READ_COILS, FUNC_READ_DISCRETE_INPUTS,
    FUNC_READ_HOLDING_REGISTERS, FUNC_READ_INPUT_REGISTERS,
    FUNC_WRITE_SINGLE_COIL, FUNC_WRITE_SINGLE_REGISTER,
    FUNC_WRITE_MULTIPLE_COILS, FUNC_WRITE_MULTIPLE_REGISTERS
)

logger = logging.getLogger(__name__)

# For backward compatibility, use ModbusRTUClient as ModbusRTU
class ModbusRTU(ModbusRTUClient):
    """
    Direct RTU Modbus communication class
    Bezpośrednia komunikacja Modbus RTU przez port szeregowy
    
    This is a compatibility wrapper around ModbusRTUClient
    """
    
    def auto_detect(self, ports: List[str] = None) -> Dict[str, Any]:
        """
        Auto-detect and connect to first available Modbus RTU device
        
        Args:
            ports: List of ports to try (default: auto-detect)
            
        Returns:
            Dict[str, Any]: Configuration dict or None if no device found
        """
        # Call the class method from ModbusRTUClient
        return self.__class__.auto_detect(ports)
        
    def test_connection(self, unit_id: int = 1) -> Tuple[bool, Dict]:
        """
        Test connection to device
        
        Args:
            unit_id: Unit ID to test
            
        Returns:
            Tuple[bool, Dict]: (success, result_dict)
        """
        result = {
            'port': self.port,
            'baudrate': self.baudrate,
            'unit_id': unit_id,
            'success': False,
            'error': None
        }
        
        try:
            # Try to read a register to verify connection
            response = self.read_holding_registers(0, 1, unit_id)
            if response is not None:
                result['success'] = True
            else:
                result['error'] = "No response from device"
                
            # Try reading coils if registers didn't work
            if not result['success']:
                response = self.read_coils(0, 8, unit_id)
                if response is not None:
                    result['success'] = True
                    result['error'] = None
        except Exception as e:
            result['error'] = str(e)
        
        return result['success'], result

# Convenience functions for backward compatibility
def create_rtu_client(port: str = DEFAULT_PORT, 
                     baudrate: int = DEFAULT_BAUDRATE,
                     timeout: float = DEFAULT_TIMEOUT) -> ModbusRTU:
    """
    Create RTU client instance
    
    Args:
        port: Serial port path
        baudrate: Baud rate
        timeout: Timeout in seconds
        
    Returns:
        ModbusRTU: RTU client instance
    """
    client = ModbusRTU(port=port, baudrate=baudrate, timeout=timeout)
    client.connect()
    return client

def test_rtu_connection(port: str = DEFAULT_PORT,
                       baudrate: int = DEFAULT_BAUDRATE,
                       unit_id: int = DEFAULT_UNIT_ID) -> Tuple[bool, Dict]:
    """
    Test RTU connection quickly
    
    Args:
        port: Serial port path
        baudrate: Baud rate
        unit_id: Unit ID to test
        
    Returns:
        Tuple[bool, Dict]: (success, result_dict)
    """
    try:
        # Create a client instance
        client = ModbusRTU(port=port, baudrate=baudrate, timeout=1.0)
        
        # Call the client's test_connection method
        # This allows the test to mock this method
        success, result = client.test_connection(unit_id)
        
        # Ensure the result has the expected format for backward compatibility
        if isinstance(result, dict) and 'connected' not in result:
            result['connected'] = success
        
        return success, result
    except Exception as e:
        # Fallback result in case of error
        result = {
            'port': port,
            'baudrate': baudrate,
            'unit_id': unit_id,
            'success': False,
            'connected': False,
            'error': str(e)
        }
        return False, result


if __name__ == "__main__":
    # Test the RTU module
    logging.basicConfig(level=logging.INFO)
    
    # Find available ports
    ports = find_serial_ports()
    print(f"Available ports: {ports}")
    
    # Test connection
    if ports:
        port = ports[0]
        print(f"Testing connection to {port}...")
        success, result = test_rtu_connection(port)
        print(f"Connection test: {'Success' if success else 'Failed'}")
        
        if success:
            # Create client and test basic operations
            client = create_rtu_client(port)
            
            # Read coils
            print("Reading coils...")
            coils = client.read_coils(0, 8)
            print(f"Coils: {coils}")
            
            # Read registers
            print("Reading registers...")
            registers = client.read_holding_registers(0, 4)
            print(f"Registers: {registers}")
            
            client.disconnect()
