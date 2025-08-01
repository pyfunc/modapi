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
from .rtu.client import ModbusRTUClient
from .rtu.utils import find_serial_ports, test_modbus_port
from .rtu.protocol import (
    FUNC_READ_COILS, FUNC_READ_DISCRETE_INPUTS,
    FUNC_READ_HOLDING_REGISTERS, FUNC_READ_INPUT_REGISTERS,
    FUNC_WRITE_SINGLE_COIL, FUNC_WRITE_SINGLE_REGISTER,
    FUNC_WRITE_MULTIPLE_COILS, FUNC_WRITE_MULTIPLE_REGISTERS
)

logger = logging.getLogger(__name__)

# For backward compatibility, use ModbusRTUClient as ModbusRTU
ModbusRTU = ModbusRTUClient

# Convenience functions for backward compatibility
def create_rtu_client(port: str = '/dev/ttyACM0', 
                     baudrate: int = 9600,
                     timeout: float = 1.0) -> ModbusRTU:
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

def test_rtu_connection(port: str = '/dev/ttyACM0',
                       baudrate: int = 9600,
                       unit_id: int = 1) -> Tuple[bool, Dict]:
    """
    Test RTU connection quickly
    
    Args:
        port: Serial port path
        baudrate: Baud rate
        unit_id: Unit ID to test
        
    Returns:
        Tuple[bool, Dict]: (success, result_dict)
    """
    result = {
        'port': port,
        'baudrate': baudrate,
        'unit_id': unit_id,
        'success': False,
        'error': None
    }
    
    try:
        client = ModbusRTU(port=port, baudrate=baudrate, timeout=1.0)
        if client.connect():
            # Try to read a register to verify connection
            response = client.read_holding_registers(0, 1, unit_id)
            if response is not None:
                result['success'] = True
            else:
                result['error'] = "No response from device"
            client.disconnect()
        else:
            result['error'] = "Failed to connect to port"
    except Exception as e:
        result['error'] = str(e)
    
    return result['success'], result


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
