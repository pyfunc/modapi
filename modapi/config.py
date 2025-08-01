"""
Configuration module for Modbus RTU
Loads constants and settings from JSON files and environment variables
"""

import os
import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

# Base directory for config files
CONFIG_DIR = Path(__file__).parent

# Load constants from JSON
_constants = None

def _load_constants():
    global _constants
    if _constants is None:
        try:
            with open(CONFIG_DIR / 'constants.json', 'r') as f:
                _constants = json.load(f)
        except Exception as e:
            logger.error(f"Error loading constants.json: {e}")
            _constants = {}
    return _constants

# Mode constants
def get_modes():
    constants = _load_constants()
    modes = constants.get('modes', {
        "MODE_NORMAL": 0,
        "MODE_LINKAGE": 1,
        "MODE_TOGGLE": 2,
        "MODE_EDGE_TRIGGER": 3
    })
    return modes

# Function codes
def get_function_codes():
    constants = _load_constants()
    function_codes = constants.get('function_codes', {
        "READ_COILS": 1,
        "READ_DISCRETE_INPUTS": 2,
        "READ_HOLDING_REGISTERS": 3,
        "READ_INPUT_REGISTERS": 4,
        "WRITE_SINGLE_COIL": 5,
        "WRITE_SINGLE_REGISTER": 6,
        "WRITE_MULTIPLE_COILS": 15,
        "WRITE_MULTIPLE_REGISTERS": 16
    })
    return function_codes

# Create constants as module-level variables for easy import
modes = get_modes()
MODE_NORMAL = modes.get("MODE_NORMAL", 0x00)
MODE_LINKAGE = modes.get("MODE_LINKAGE", 0x01)
MODE_TOGGLE = modes.get("MODE_TOGGLE", 0x02)
MODE_EDGE_TRIGGER = modes.get("MODE_EDGE_TRIGGER", 0x03)

# Analog input types
def get_analog_input_types():
    constants = _load_constants()
    analog_types = constants.get('analog_input_types', {
        "TYPE_0_5V": 0,
        "TYPE_0_10V": 1,
        "TYPE_0_20MA": 2,
        "TYPE_4_20MA": 3
    })
    return analog_types

analog_types = get_analog_input_types()
TYPE_0_5V = analog_types.get("TYPE_0_5V", 0x00)
TYPE_0_10V = analog_types.get("TYPE_0_10V", 0x01)
TYPE_0_20MA = analog_types.get("TYPE_0_20MA", 0x02)
TYPE_4_20MA = analog_types.get("TYPE_4_20MA", 0x03)

function_codes = get_function_codes()
FUNC_READ_COILS = function_codes.get("READ_COILS", 0x01)
FUNC_READ_DISCRETE_INPUTS = function_codes.get("READ_DISCRETE_INPUTS", 0x02)
FUNC_READ_HOLDING_REGISTERS = function_codes.get("READ_HOLDING_REGISTERS", 0x03)
FUNC_READ_INPUT_REGISTERS = function_codes.get("READ_INPUT_REGISTERS", 0x04)
FUNC_WRITE_SINGLE_COIL = function_codes.get("WRITE_SINGLE_COIL", 0x05)
FUNC_WRITE_SINGLE_REGISTER = function_codes.get("WRITE_SINGLE_REGISTER", 0x06)
FUNC_WRITE_MULTIPLE_COILS = function_codes.get("WRITE_MULTIPLE_COILS", 0x0F)
FUNC_WRITE_MULTIPLE_REGISTERS = function_codes.get("WRITE_MULTIPLE_REGISTERS", 0x10)

# Default settings
def get_default_settings():
    constants = _load_constants()
    return constants.get('default_settings', {
        "port": "/dev/ttyACM0",
        "baudrate": 19200,  # Updated default baudrate
        "timeout": 1.0,
        "unit_id": 1,
        "rs485_delay": 0.2  # Default delay between RS485 operations in seconds
    })

DEFAULT_SETTINGS = get_default_settings()
DEFAULT_PORT = DEFAULT_SETTINGS.get("port", '/dev/ttyACM0')
DEFAULT_BAUDRATE = DEFAULT_SETTINGS.get("baudrate", 19200)  # Updated default baudrate
DEFAULT_TIMEOUT = DEFAULT_SETTINGS.get("timeout", 1.0)
DEFAULT_UNIT_ID = DEFAULT_SETTINGS.get("unit_id", 1)
DEFAULT_RS485_DELAY = DEFAULT_SETTINGS.get("rs485_delay", 0.2)  # Default delay between RS485 operations in seconds

# Baudrate mapping
_baudrates = None

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

def get_baudrates() -> Dict[str, int]:
    """Get baudrate mapping from JSON config"""
    global _baudrates
    if _baudrates is None:
        _baudrates = load_json_config('baudrates.json')
        if not _baudrates:
            # Fallback default baudrates
            _baudrates = {
                "57600": 1,  # Updated from 9600 to 57600
                "115200": 5
            }
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
    # Try environment variable (with RTU_ prefix)
    env_key = f"RTU_{key.upper()}"
    env_value = get_env_value(env_key)
    if env_value is not None:
        return env_value
        
    # Try JSON config from constants.json
    constants = _load_constants()
    sections = key.split('.')
    
    # Navigate through nested sections
    current = constants
    for section in sections[:-1]:
        if section in current:
            current = current[section]
        else:
            return default
            
    # Get the final value
    if sections[-1] in current:
        return current[sections[-1]]
    
    # Return default
    return default

# Get baudrates array
def get_baudrates_array():
    constants = _load_constants()
    return constants.get('baudrates', [57600, 115200])  # Updated default baudrates

# Get prioritized baudrates for auto-detection
def get_prioritized_baudrates():
    constants = _load_constants()
    return constants.get('prioritized_baudrates', [57600, 115200])  # Prioritize higher baudrates

BAUDRATES = get_baudrates_array()
PRIORITIZED_BAUDRATES = get_prioritized_baudrates()

# Auto-detection settings
def get_auto_detect_settings():
    constants = _load_constants()
    return constants.get('auto_detect', {
        "ports": ["/dev/ttyACM0", "/dev/ttyUSB0"],
        "unit_ids": [0, 1, 2, 3, 4]
    })

AUTO_DETECT = get_auto_detect_settings()
AUTO_DETECT_PORTS = get_env_value('RTU_AUTO_DETECT_PORTS', AUTO_DETECT.get("ports"))
AUTO_DETECT_BAUDRATES = get_env_value('RTU_AUTO_DETECT_BAUDRATES', BAUDRATES)
AUTO_DETECT_UNIT_IDS = get_env_value('RTU_AUTO_DETECT_UNIT_IDS', AUTO_DETECT.get("unit_ids"))

# Mock mode settings
def get_mock_settings():
    constants = _load_constants()
    return constants.get('mock', {
        "port": "MOCK",
        "baudrate": 57600,  # Updated default baudrate
        "unit_id": 1
    })

MOCK_SETTINGS = get_mock_settings()
MOCK_PORT = get_env_value('RTU_MOCK_PORT', MOCK_SETTINGS.get("port"))
MOCK_BAUDRATE = get_env_value('RTU_MOCK_BAUDRATE', MOCK_SETTINGS.get("baudrate"))
MOCK_UNIT_ID = get_env_value('RTU_MOCK_UNIT_ID', MOCK_SETTINGS.get("unit_id"))
