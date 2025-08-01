"""
Configuration module for Modbus RTU
Loads constants and settings from JSON files and environment variables
"""

import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

# Set up logging
import logging
logger = logging.getLogger(__name__)

# Configuration directory
CONFIG_DIR = Path(__file__).parent.parent / 'config'

# ====== Function Definitions ======

def _load_constants():
    """Load constants from JSON file"""
    try:
        file_path = CONFIG_DIR / 'constants.json'
        if file_path.exists():
            with open(file_path, 'r') as f:
                return json.load(f)
        return {}
    except Exception as e:
        logger.warning(f"Failed to load constants: {e}")
        return {}

def get_modes():
    """Get mode constants"""
    constants = _load_constants()
    return constants.get('modes', {
        "MODE_NORMAL": 0x00,
        "MODE_LINKAGE": 0x01,
        "MODE_SINGLE": 0x02,
        "MODE_LOOP": 0x03
    })

def get_function_codes():
    """Get function code constants"""
    constants = _load_constants()
    return constants.get('function_codes', {
        "READ_COILS": 0x01,
        "READ_DISCRETE_INPUTS": 0x02,
        "READ_HOLDING_REGISTERS": 0x03,
        "READ_INPUT_REGISTERS": 0x04,
        "WRITE_SINGLE_COIL": 0x05,
        "WRITE_SINGLE_REGISTER": 0x06,
        "WRITE_MULTIPLE_COILS": 0x0F,
        "WRITE_MULTIPLE_REGISTERS": 0x10
    })

def get_analog_input_types():
    """Get analog input type constants"""
    constants = _load_constants()
    return constants.get('analog_input_types', {
        "TYPE_0_5V": 0x00,
        "TYPE_0_10V": 0x01,
        "TYPE_0_20MA": 0x02,
        "TYPE_4_20MA": 0x03
    })

def load_json_config(filename: str) -> Dict[str, Any]:
    """Load configuration from a JSON file"""
    try:
        file_path = CONFIG_DIR / filename
        if not file_path.exists():
            logger.warning(f"Config file {filename} not found")
            return {}
            
        with open(file_path, 'r') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Error loading config file {filename}: {e}")
        return {}

def get_baudrates():
    """Get baudrate mapping from JSON config"""
    global _baudrates
    if _baudrates is None:
        _baudrates = load_json_config('baudrates.json')
    return _baudrates

def get_env_value(key: str, default: Any = None) -> Any:
    """Get a value from environment variables"""
    return os.environ.get(key, default)

def get_config_value(key: str, default: Any = None) -> Any:
    """
    Get a configuration value with priority:
    1. Environment variable
    2. JSON config
    3. Default value
    """
    # Try environment variable first
    env_key = f"MODBUS_{key.upper()}"
    value = os.environ.get(env_key)
    if value is not None:
        # Try to convert to appropriate type
        if isinstance(default, bool):
            return value.lower() in ('true', '1', 't', 'y', 'yes')
        elif isinstance(default, int):
            try:
                return int(value)
            except (ValueError, TypeError):
                pass
        elif isinstance(default, float):
            try:
                return float(value)
            except (ValueError, TypeError):
                pass
        return value
    
    # Try JSON config
    config = load_json_config('config.json')
    if key in config:
        return config[key]
        
    # Return default
    return default

def get_baudrates_array():
    """Get list of supported baudrates"""
    constants = _load_constants()
    return constants.get('baudrates', [BAUDRATE_MIN])

def get_prioritized_baudrates():
    """Get prioritized baudrates for auto-detection"""
    constants = _load_constants()
    return constants.get('prioritized_baudrates', [BAUDRATE_MIN])

def get_highest_prioritized_baudrate():
    """Get the highest baudrate from the prioritized baudrates"""
    prioritized = get_prioritized_baudrates()
    if not prioritized:
        return BAUDRATE_MIN  # Default if no prioritized baudrates
    return max(prioritized)

def get_default_settings():
    """Get default settings"""
    constants = _load_constants()
    return constants.get('default_settings', {
        "port": "/dev/ttyACM0",
        "baudrate": BAUDRATE_MIN,
        "timeout": 1.0,
        "unit_id": 1,
        "rs485_delay": 0.1
    })

def get_auto_detect_settings():
    """Get auto-detect settings"""
    constants = _load_constants()
    return constants.get('auto_detect', {
        "ports": ["/dev/ttyACM0", "/dev/ttyUSB0"],
        "baudrates": [57600, 115200],
        "unit_ids": list(range(1, 11))  # 1-10
    })

def get_mock_settings():
    """Get mock settings for testing"""
    constants = _load_constants()
    return constants.get('mock_settings', {
        "port": "mock",
        "baudrate": BAUDRATE_MIN,
        "unit_id": 1,
        "enabled": False
    })

# ====== Module-level Constants ======

# Mode constants
modes = get_modes()
MODE_NORMAL = modes.get("MODE_NORMAL", 0x00)
MODE_LINKAGE = modes.get("MODE_LINKAGE", 0x01)
MODE_SINGLE = modes.get("MODE_SINGLE", 0x02)
MODE_LOOP = modes.get("MODE_LOOP", 0x03)

# Function codes
function_codes = get_function_codes()
READ_COILS = function_codes.get("READ_COILS", 0x01)
READ_DISCRETE_INPUTS = function_codes.get("READ_DISCRETE_INPUTS", 0x02)
READ_HOLDING_REGISTERS = function_codes.get("READ_HOLDING_REGISTERS", 0x03)
READ_INPUT_REGISTERS = function_codes.get("READ_INPUT_REGISTERS", 0x04)
WRITE_SINGLE_COIL = function_codes.get("WRITE_SINGLE_COIL", 0x05)
WRITE_SINGLE_REGISTER = function_codes.get("WRITE_SINGLE_REGISTER", 0x06)
WRITE_MULTIPLE_COILS = function_codes.get("WRITE_MULTIPLE_COILS", 0x0F)
WRITE_MULTIPLE_REGISTERS = function_codes.get("WRITE_MULTIPLE_REGISTERS", 0x10)

# Analog input types
analog_types = get_analog_input_types()
TYPE_0_5V = analog_types.get("TYPE_0_5V", 0x00)
TYPE_0_10V = analog_types.get("TYPE_0_10V", 0x01)
TYPE_0_20MA = analog_types.get("TYPE_0_20MA", 0x02)
TYPE_4_20MA = analog_types.get("TYPE_4_20MA", 0x03)

# Register types
REGISTER_TYPES = {
    'coil': 0,
    'discrete_input': 1,
    'holding_register': 2,
    'input_register': 3
}

# Baudrate settings
_baudrates = None
BAUDRATE_MIN = 19200
BAUDRATES = get_baudrates_array()
PRIORITIZED_BAUDRATES = get_prioritized_baudrates()
HIGHEST_PRIORITIZED_BAUDRATE = get_highest_prioritized_baudrate()

# Default settings
DEFAULT_SETTINGS = get_default_settings()
DEFAULT_PORT = DEFAULT_SETTINGS.get("port", '/dev/ttyACM0')
DEFAULT_BAUDRATE = HIGHEST_PRIORITIZED_BAUDRATE
DEFAULT_TIMEOUT = DEFAULT_SETTINGS.get("timeout", 1.0)
DEFAULT_UNIT_ID = DEFAULT_SETTINGS.get("unit_id", 1)
DEFAULT_RS485_DELAY = DEFAULT_SETTINGS.get("rs485_delay", 0.1)

# Auto-detect settings
AUTO_DETECT = get_auto_detect_settings()
AUTO_DETECT_PORTS = get_env_value('RTU_AUTO_DETECT_PORTS', AUTO_DETECT.get("ports"))
AUTO_DETECT_BAUDRATES = get_env_value('RTU_AUTO_DETECT_BAUDRATES', BAUDRATES)
AUTO_DETECT_UNIT_IDS = get_env_value('RTU_AUTO_DETECT_UNIT_IDS', AUTO_DETECT.get("unit_ids"))

# Mock settings
MOCK_SETTINGS = get_mock_settings()
MOCK_PORT = get_env_value('RTU_MOCK_PORT', MOCK_SETTINGS.get("port"))
MOCK_BAUDRATE = get_env_value('RTU_MOCK_BAUDRATE', MOCK_SETTINGS.get("baudrate"))
MOCK_UNIT_ID = get_env_value('RTU_MOCK_UNIT_ID', MOCK_SETTINGS.get("unit_id"))
MOCK_ENABLED = get_env_value('RTU_MOCK_ENABLED', str(MOCK_SETTINGS.get("enabled", False))).lower() in ('true', '1', 't', 'y', 'yes')

# FUNC_* constants have been removed in favor of standard constant names (READ_COILS, etc.)