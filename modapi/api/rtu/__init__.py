"""
Modbus RTU Package
Modular implementation of Modbus RTU protocol with Waveshare device support
"""

# Core classes
from .base import ModbusRTU
from .client import ModbusRTUClient

# Protocol functions
from .protocol import (
    FUNC_READ_COILS, FUNC_READ_DISCRETE_INPUTS,
    FUNC_READ_HOLDING_REGISTERS, FUNC_READ_INPUT_REGISTERS,
    FUNC_WRITE_SINGLE_COIL, FUNC_WRITE_SINGLE_REGISTER,
    FUNC_WRITE_MULTIPLE_COILS, FUNC_WRITE_MULTIPLE_REGISTERS,
    build_request, parse_response,
    build_read_request, parse_read_coils_response, parse_read_registers_response,
    build_write_single_coil_request, build_write_single_register_request,
    build_write_multiple_coils_request, build_write_multiple_registers_request
)

# CRC functions
from .crc import calculate_crc, validate_crc, try_alternative_crcs

# Utility functions
from .utils import find_serial_ports, test_modbus_port, scan_for_devices, detect_device_type

# Device-specific classes
from .devices import WaveshareIO8CH, WaveshareAnalogInput8CH

# For backward compatibility with existing code
__all__ = [
    'ModbusRTU',
    'ModbusRTUClient',
    'FUNC_READ_COILS',
    'FUNC_READ_DISCRETE_INPUTS',
    'FUNC_READ_HOLDING_REGISTERS',
    'FUNC_READ_INPUT_REGISTERS',
    'FUNC_WRITE_SINGLE_COIL',
    'FUNC_WRITE_SINGLE_REGISTER',
    'FUNC_WRITE_MULTIPLE_COILS',
    'FUNC_WRITE_MULTIPLE_REGISTERS',
    'calculate_crc',
    'validate_crc',
    'try_alternative_crcs',
    'find_serial_ports',
    'test_modbus_port',
    'scan_for_devices',
    'detect_device_type',
    'WaveshareIO8CH',
    'WaveshareAnalogInput8CH'
]
