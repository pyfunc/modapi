"""
Modbus Device State Manager
Provides functions to manage device states in the ModbusRTU class
"""

import logging
import os
import time
from datetime import datetime
from typing import Dict, List, Optional, Any, Union

from .device_state import ModbusDeviceState, device_manager
from .protocol import parse_read_coils_response, parse_read_registers_response
from modapi.config import (
    READ_COILS, READ_DISCRETE_INPUTS,
    READ_HOLDING_REGISTERS, READ_INPUT_REGISTERS,
    WRITE_SINGLE_COIL, WRITE_SINGLE_REGISTER,
    WRITE_MULTIPLE_COILS, WRITE_MULTIPLE_REGISTERS
)

logger = logging.getLogger(__name__)

def get_or_create_device_state(rtu_instance, unit_id: int) -> Optional[ModbusDeviceState]:
    """Get or create device state for a unit ID"""
    if not rtu_instance.enable_state_tracking:
        return None
        
    # Check if we already have a state for this device
    device_key = f"{rtu_instance.port}_{unit_id}"
    if device_key not in rtu_instance.device_states:
        # Create new device state
        rtu_instance.device_states[device_key] = ModbusDeviceState(
            unit_id=unit_id,
            port=rtu_instance.port,
            baudrate=rtu_instance.baudrate
        )
        rtu_instance.device_logger.info(f"Created new device state for unit {unit_id} on {rtu_instance.port}")
        
        # Also register with global device manager
        device_manager.add_device(rtu_instance.device_states[device_key])
        
    return rtu_instance.device_states[device_key]

def get_request_type(function_code: int) -> str:
    """Get human-readable request type from function code"""
    function_names = {
        READ_COILS: "READ_COILS",
        READ_DISCRETE_INPUTS: "READ_DISCRETE_INPUTS",
        READ_HOLDING_REGISTERS: "READ_HOLDING_REGISTERS",
        READ_INPUT_REGISTERS: "READ_INPUT_REGISTERS",
        WRITE_SINGLE_COIL: "WRITE_SINGLE_COIL",
        WRITE_SINGLE_REGISTER: "WRITE_SINGLE_REGISTER",
        WRITE_MULTIPLE_COILS: "WRITE_MULTIPLE_COILS",
        WRITE_MULTIPLE_REGISTERS: "WRITE_MULTIPLE_REGISTERS"
    }
    return function_names.get(function_code, f"UNKNOWN({function_code})")

def extract_address_from_request(request: bytes, function_code: int, logger=None) -> int:
    """Extract address from request bytes"""
    try:
        if len(request) >= 4:  # All Modbus requests have at least 4 bytes
            # Address is typically at bytes 2-3 (big-endian)
            return (request[2] << 8) | request[3]
    except Exception as e:
        if logger:
            logger.error(f"Error extracting address: {e}")
        else:
            logger.error(f"Error extracting address: {e}")
    return -1

def update_device_state_from_response(device_state: ModbusDeviceState, 
                                     function_code: int, address: int, 
                                     data: bytes, is_reliable: bool = True,
                                     logger=None) -> None:
    """Update device state based on response data"""
    try:
        if function_code == READ_COILS:
            # Parse coil values
            values = parse_read_coils_response(data)
            if values is not None:
                device_state.update_coils(address, values)
                if logger:
                    logger.debug(f"Updated {len(values)} coils starting at {address}")
                
        elif function_code == READ_DISCRETE_INPUTS:
            # Parse discrete input values
            values = parse_read_coils_response(data)  # Same parsing as coils
            if values is not None:
                device_state.update_discrete_inputs(address, values)
                if logger:
                    logger.debug(f"Updated {len(values)} discrete inputs starting at {address}")
                
        elif function_code == READ_HOLDING_REGISTERS:
            # Parse holding register values
            values = parse_read_registers_response(data)
            if values is not None:
                device_state.update_holding_registers(address, values)
                if logger:
                    logger.debug(f"Updated {len(values)} holding registers starting at {address}")
                
        elif function_code == READ_INPUT_REGISTERS:
            # Parse input register values
            values = parse_read_registers_response(data)
            if values is not None:
                device_state.update_input_registers(address, values)
                if logger:
                    logger.debug(f"Updated {len(values)} input registers starting at {address}")
                
        elif function_code == WRITE_SINGLE_COIL:
            # Extract value from write response
            if len(data) >= 2:
                value = (data[0] << 8 | data[1]) == 0xFF00  # 0xFF00 = ON, 0x0000 = OFF
                device_state.update_coil(address, value)
                if logger:
                    logger.debug(f"Updated coil {address} to {value}")
                
        elif function_code == WRITE_SINGLE_REGISTER:
            # Extract value from write response
            if len(data) >= 2:
                value = data[0] << 8 | data[1]
                device_state.update_holding_register(address, value)
                if logger:
                    logger.debug(f"Updated register {address} to {value}")
                
        # For multiple writes, we don't get the values back, just confirmation
        # So we don't update the device state for those
        
    except Exception as e:
        if logger:
            logger.error(f"Error updating device state: {e}")
        else:
            logger.error(f"Error updating device state: {e}")

def dump_device_states(rtu_instance, directory: str = None) -> None:
    """Dump all device states to JSON files"""
    if not rtu_instance.enable_state_tracking or not rtu_instance.device_states:
        logger.warning("No device states to dump")
        return
        
    if directory is None:
        directory = os.path.join(rtu_instance.log_directory, "device_states")
        
    os.makedirs(directory, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    for key, device in rtu_instance.device_states.items():
        filename = f"{directory}/device_{device.port.replace('/', '_')}_{device.unit_id}_{timestamp}.json"
        device.dump_to_file(filename)
        
    logger.info(f"Dumped {len(rtu_instance.device_states)} device states to {directory}")

def dump_current_device_state(rtu_instance) -> None:
    """Dump current device state to JSON file"""
    if not rtu_instance.enable_state_tracking or rtu_instance.current_unit_id is None:
        logger.warning("No current device state to dump")
        return
        
    device_key = f"{rtu_instance.port}_{rtu_instance.current_unit_id}"
    if device_key in rtu_instance.device_states:
        directory = os.path.join(rtu_instance.log_directory, "device_states")
        os.makedirs(directory, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{directory}/device_{rtu_instance.port.replace('/', '_')}_{rtu_instance.current_unit_id}_{timestamp}.json"
        
        rtu_instance.device_states[device_key].dump_to_file(filename)
        logger.info(f"Dumped current device state to {filename}")
    else:
        logger.warning(f"No state found for current device {rtu_instance.current_unit_id}")

def get_device_state_summary(rtu_instance, unit_id: Optional[int] = None) -> Dict[str, Any]:
    """Get summary of device state(s)"""
    if not rtu_instance.enable_state_tracking:
        return {"error": "Device state tracking is disabled"}
        
    if unit_id is not None:
        # Get specific device state
        device_key = f"{rtu_instance.port}_{unit_id}"
        if device_key in rtu_instance.device_states:
            return rtu_instance.device_states[device_key].to_dict()
        else:
            return {"error": f"No state found for device {unit_id}"}
    else:
        # Get summary of all device states
        return {
            "device_count": len(rtu_instance.device_states),
            "devices": [device.to_dict() for device in rtu_instance.device_states.values()]
        }
